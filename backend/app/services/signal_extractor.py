import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

from app.core.config import settings
from app.models.signal import (
    CampaignSignal,
    EvidenceItem,
    LLMExtractionRun,
    QualityEvent,
    SignalType,
)
from app.models.source import (
    BriefDocument,
    CommunityComment,
    CreatorProfile,
    PerformanceMetric,
    ProductContext,
    SourceRecord,
)
from app.services.analysis import TOPIC_DEFINITIONS, cluster_comments
from app.services.datasets import get_comment_dataset
from app.services.llm_client import LLMCompletionResult, get_llm_client
from app.services.quality_checks import validate_signal
from app.services.repository import repo

LLM_OUTPUT_DIR = (
    Path(__file__).resolve().parents[3] / "data" / "processed" / "llm_outputs"
)

RISK_TERMS = {
    "leak": "Packaging leakage shows up as a launch risk.",
    "broken": "Packaging or delivery damage may shape early perception.",
    "irritat": "Sensitive-skin concerns need careful claim language.",
    "rash": "Skin reaction comments require conservative messaging.",
    "strong": "Scent strength may polarize buyers.",
    "expensive": "Price-value skepticism may affect conversion.",
    "sticky": "Texture concerns may weaken product trial.",
    "watery": "Weak brew complaints may undermine roast positioning.",
    "bitter": "Bitterness complaints may create taste-quality concerns.",
    "stale": "Freshness complaints can damage trust in coffee quality.",
    "weak": "Weak flavor language may conflict with bold coffee messaging.",
    "gross": "Strong rejection language should be monitored before scaling.",
    "not coffee": "Authenticity concerns can hurt flavored coffee positioning.",
    "negative_review": "Low-rating reviews reveal campaign friction to investigate.",
}

POSITIVE_TERMS = {
    "soft": "Softness and feel are credible message angles.",
    "gentle": "Gentle-use language fits ingredient-conscious buyers.",
    "smell": "Scent can be a creator-led sensory hook.",
    "works": "Effectiveness claims have review evidence.",
    "moistur": "Moisture benefit is a likely content opportunity.",
    "smooth": "Smoothness can support a taste-led message angle.",
    "bold": "Bold flavor language can support roast-strength positioning.",
    "fresh": "Freshness language can support quality messaging.",
    "keurig": "Single-serve convenience is a usable campaign angle.",
    "espresso": "Espresso use cases can support product-specific content.",
}

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


@dataclass
class CommentChunk:
    id: str
    label: str
    description: str
    chunk_type: str
    comments: list[CommunityComment]
    metadata: dict = field(default_factory=dict)


def extract_signals(
    campaign_id: str,
    dataset_id: str | None = None,
    scope: dict | None = None,
    analysis_mode: str = "full",
) -> list[CampaignSignal]:
    repo.clear_campaign_signals(campaign_id)
    records = repo.campaign_records(campaign_id)
    briefs = [record for record in records if isinstance(record, BriefDocument)]
    comments = [record for record in records if isinstance(record, CommunityComment)]
    products = [record for record in records if isinstance(record, ProductContext)]
    creators = [record for record in records if isinstance(record, CreatorProfile)]
    metrics = [record for record in records if isinstance(record, PerformanceMetric)]

    signals = _extract_llm_comment_signals(
        campaign_id,
        briefs,
        comments,
        products,
        creators,
        metrics,
        dataset_id=dataset_id,
        scope=scope,
        analysis_mode=analysis_mode,
    )
    if not signals:
        signals = _extract_comment_signals(campaign_id, comments)
    signals.extend(_extract_creator_signals(campaign_id, creators))
    signals.extend(_extract_performance_signals(campaign_id, metrics))

    valid_signals: list[CampaignSignal] = []
    for signal in signals:
        events = validate_signal(signal, records)
        for event in events:
            repo.add_quality_event(event)
        if not any(event.level == "error" for event in events):
            valid_signals.append(signal)

    repo.add_signals(valid_signals)
    return valid_signals


def _extract_llm_comment_signals(
    campaign_id: str,
    briefs: list[BriefDocument],
    comments: list[CommunityComment],
    products: list[ProductContext],
    creators: list[CreatorProfile],
    metrics: list[PerformanceMetric],
    dataset_id: str | None = None,
    scope: dict | None = None,
    analysis_mode: str = "full",
) -> list[CampaignSignal]:
    if not comments:
        return []

    chunks = _plan_comment_chunks(comments, products, analysis_mode=analysis_mode)
    client = get_llm_client()
    signals: list[CampaignSignal] = []
    for chunk in chunks:
        signals.extend(
            _extract_llm_chunk_signals(
                client=client,
                campaign_id=campaign_id,
                briefs=briefs,
                comments=comments,
                products=products,
                creators=creators,
                metrics=metrics,
                chunk=chunk,
                dataset_id=dataset_id,
                scope=scope,
                analysis_mode=analysis_mode,
            )
        )

    return _merge_similar_signals(signals, comments)[: settings.llm_max_comment_signals]


def _extract_llm_chunk_signals(
    client,
    campaign_id: str,
    briefs: list[BriefDocument],
    comments: list[CommunityComment],
    products: list[ProductContext],
    creators: list[CreatorProfile],
    metrics: list[PerformanceMetric],
    chunk: CommentChunk,
    dataset_id: str | None,
    scope: dict | None,
    analysis_mode: str,
) -> list[CampaignSignal]:
    selected_comments = chunk.comments
    prompt = _build_signal_prompt(
        campaign_id,
        briefs,
        selected_comments,
        products,
        chunk=chunk,
    )
    started_at = datetime.now(UTC)
    result: LLMCompletionResult | None = None
    try:
        result = client.complete_json(prompt)
        ended_at = datetime.now(UTC)
        payload = result.parsed_json
        signals = _signals_from_llm_payload(
            campaign_id,
            payload,
            comments,
            support_comments=chunk.comments,
            chunk=chunk,
        )
        _store_llm_output(
            campaign_id=campaign_id,
            prompt=prompt,
            result=result,
            parsed_signal_count=len(signals),
            started_at=started_at,
            ended_at=ended_at,
            dataset_id=dataset_id,
            scope=scope,
            selected_comments=selected_comments,
            input_summary=_input_summary(
                briefs=briefs,
                comments=comments,
                products=products,
                creators=creators,
                metrics=metrics,
                selected_comments=selected_comments,
                chunk=chunk,
                analysis_mode=analysis_mode,
            ),
        )
        return signals
    except Exception as exc:
        ended_at = datetime.now(UTC)
        _store_failed_llm_output(
            campaign_id=campaign_id,
            prompt=prompt,
            error=str(exc),
            started_at=started_at,
            ended_at=ended_at,
            dataset_id=dataset_id,
            scope=scope,
            selected_comments=selected_comments,
            result=result,
            input_summary=_input_summary(
                briefs=briefs,
                comments=comments,
                products=products,
                creators=creators,
                metrics=metrics,
                selected_comments=selected_comments,
                chunk=chunk,
                analysis_mode=analysis_mode,
            ),
        )
        repo.add_quality_event(
            QualityEvent(
                campaign_id=campaign_id,
                level="warning",
                message="LLM extraction failed; falling back to deterministic rules.",
                details={"error": str(exc)},
            )
        )
        return []


def _store_llm_output(
    campaign_id: str,
    prompt: str,
    result: LLMCompletionResult,
    parsed_signal_count: int,
    started_at: datetime,
    ended_at: datetime,
    dataset_id: str | None,
    scope: dict | None,
    selected_comments: list[CommunityComment],
    input_summary: dict,
) -> LLMExtractionRun:
    run = LLMExtractionRun(
        campaign_id=campaign_id,
        provider=settings.llm_provider,
        model=_active_model_name(),
        endpoint=result.endpoint,
        status="succeeded",
        dataset_id=dataset_id,
        dataset=_dataset_metadata(dataset_id, len(selected_comments), input_summary),
        scope=scope,
        source_files=_source_file_metadata(campaign_id),
        input_summary=input_summary,
        selected_source_record_ids=[comment.id for comment in selected_comments],
        prompt=prompt,
        raw_output=result.parsed_json,
        raw_response=result.raw_response,
        request_metadata=result.request_metadata,
        response_metadata=result.response_metadata,
        parsed_signal_count=parsed_signal_count,
        created_at=ended_at,
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=_duration_ms(started_at, ended_at),
    )
    return repo.add_llm_run(_write_llm_run(run))


def _store_failed_llm_output(
    campaign_id: str,
    prompt: str,
    error: str,
    started_at: datetime,
    ended_at: datetime,
    dataset_id: str | None,
    scope: dict | None,
    selected_comments: list[CommunityComment],
    result: LLMCompletionResult | None,
    input_summary: dict,
) -> LLMExtractionRun:
    run = LLMExtractionRun(
        campaign_id=campaign_id,
        provider=settings.llm_provider,
        model=_active_model_name(),
        endpoint=result.endpoint if result else _active_endpoint(),
        status="failed",
        dataset_id=dataset_id,
        dataset=_dataset_metadata(dataset_id, len(selected_comments), input_summary),
        scope=scope,
        source_files=_source_file_metadata(campaign_id),
        input_summary=input_summary,
        selected_source_record_ids=[comment.id for comment in selected_comments],
        prompt=prompt,
        raw_output=result.parsed_json if result else {},
        raw_response=result.raw_response if result else {},
        request_metadata=result.request_metadata if result else {},
        response_metadata=result.response_metadata if result else {},
        parsed_signal_count=0,
        error=error,
        created_at=ended_at,
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=_duration_ms(started_at, ended_at),
    )
    return repo.add_llm_run(_write_llm_run(run))


def _write_llm_run(run: LLMExtractionRun) -> LLMExtractionRun:
    LLM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = LLM_OUTPUT_DIR / f"{run.campaign_id}_{run.id}.json"
    run.output_path = str(output_path)
    output_path.write_text(
        json.dumps(run.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return run


def _input_summary(
    briefs: list[BriefDocument],
    comments: list[CommunityComment],
    products: list[ProductContext],
    creators: list[CreatorProfile],
    metrics: list[PerformanceMetric],
    selected_comments: list[CommunityComment],
    chunk: CommentChunk | None = None,
    analysis_mode: str = "full",
) -> dict:
    summary = {
        "analysis_mode": analysis_mode,
        "brief_count": len(briefs),
        "comment_count": len(comments),
        "product_count": len(products),
        "creator_count": len(creators),
        "performance_metric_count": len(metrics),
        "selected_comment_count": len(selected_comments),
        "selected_comment_rating_distribution": dict(
            Counter(str(comment.source_rating) for comment in selected_comments)
        ),
        "selected_parent_asins": sorted(
            {
                comment.parent_product_id
                for comment in selected_comments
                if comment.parent_product_id
            }
        ),
    }
    if chunk is not None:
        summary["chunk"] = {
            "id": chunk.id,
            "label": chunk.label,
            "type": chunk.chunk_type,
            "description": chunk.description,
            "source_comment_count": chunk.metadata.get("source_comment_count"),
            "metadata": chunk.metadata,
        }
    return summary


def _source_file_metadata(campaign_id: str) -> list[dict]:
    return [
        {
            "id": source_file.id,
            "filename": source_file.filename,
            "source_type": source_file.source_type,
            "row_count": source_file.row_count,
            "ingested_at": source_file.ingested_at.isoformat(),
        }
        for source_file in repo.campaign_files(campaign_id)
    ]


def _dataset_metadata(
    dataset_id: str | None,
    selected_comment_count: int,
    input_summary: dict,
) -> dict | None:
    if dataset_id is None:
        return None
    try:
        dataset = get_comment_dataset(dataset_id)
    except KeyError:
        return {"id": dataset_id, "selected_comment_count": selected_comment_count}
    return {
        "id": dataset.id,
        "label": dataset.label,
        "filename": dataset.filename,
        "path": dataset.path,
        "catalog_record_count": dataset.record_count,
        "loaded_comment_count": input_summary.get("comment_count"),
        "selected_comment_count": selected_comment_count,
        "description": dataset.description,
    }


def _duration_ms(started_at: datetime, ended_at: datetime) -> int:
    return int((ended_at - started_at).total_seconds() * 1000)


def _active_model_name() -> str | None:
    if settings.llm_provider == "sglang":
        return settings.sglang_model
    if settings.llm_provider in {"openai", "cloud", "openai_compatible"}:
        return settings.cloud_llm_model
    return None


def _active_endpoint() -> str | None:
    if settings.llm_provider == "sglang":
        return f"{settings.sglang_base_url.rstrip('/')}/v1/chat/completions"
    if settings.llm_provider in {"openai", "cloud", "openai_compatible"}:
        return f"{settings.cloud_llm_base_url.rstrip('/')}/v1/chat/completions"
    return None


def _plan_comment_chunks(
    comments: list[CommunityComment],
    products: list[ProductContext],
    analysis_mode: str = "full",
) -> list[CommentChunk]:
    if (
        analysis_mode == "sample"
        or len(comments) < settings.llm_min_comments_for_chunking
    ):
        selected = _select_comments_for_llm(comments, settings.llm_batch_comments)
        return [
            _make_chunk(
                chunk_id="balanced_sample",
                label="Balanced review sample",
                description=(
                    "Fast balanced low, mixed, and high-rating review sample."
                ),
                chunk_type="balanced_sample",
                comments=selected,
                source_comments=comments,
            )
        ]

    chunks: list[CommentChunk] = []
    chunks.extend(_topic_chunks(comments))
    chunks.extend(_product_risk_chunks(comments, products))
    chunks.extend(_rating_chunks(comments))
    return _dedupe_chunks(chunks)[: settings.llm_max_chunks]


def _topic_chunks(comments: list[CommunityComment]) -> list[CommentChunk]:
    chunks: list[CommentChunk] = []
    for cluster in cluster_comments(comments):
        definition = TOPIC_DEFINITIONS.get(cluster.id)
        if not definition:
            continue
        hits = [
            comment
            for comment in comments
            if any(term in comment.text.lower() for term in definition["terms"])
        ]
        if len(hits) < 3:
            continue
        selected = _select_representative_comments(hits, settings.llm_chunk_comments)
        chunks.append(
            _make_chunk(
                chunk_id=f"topic_{cluster.id}",
                label=cluster.label,
                description=cluster.description,
                chunk_type="topic",
                comments=selected,
                source_comments=hits,
            )
        )
    return chunks


def _product_risk_chunks(
    comments: list[CommunityComment],
    products: list[ProductContext],
) -> list[CommentChunk]:
    product_map = {product.parent_asin: product for product in products}
    grouped: dict[str, list[CommunityComment]] = defaultdict(list)
    for comment in comments:
        if comment.parent_product_id:
            grouped[comment.parent_product_id].append(comment)

    scored = []
    for parent_asin, product_comments in grouped.items():
        low_count = sum(
            1
            for comment in product_comments
            if comment.source_rating is not None and comment.source_rating <= 2
        )
        if low_count < 2:
            continue
        scored.append((low_count, len(product_comments), parent_asin, product_comments))

    chunks: list[CommentChunk] = []
    for low_count, _, parent_asin, product_comments in sorted(scored, reverse=True)[:3]:
        product = product_map.get(parent_asin)
        selected = _select_representative_comments(
            product_comments,
            settings.llm_chunk_comments,
        )
        chunks.append(
            _make_chunk(
                chunk_id=f"product_{parent_asin}",
                label=f"Product risk / {product.title if product else parent_asin}",
                description=(
                    f"Product-level risk analysis for {parent_asin}; "
                    f"{low_count} low-rating reviews in the loaded sample."
                ),
                chunk_type="product_risk",
                comments=selected,
                source_comments=product_comments,
                metadata={"parent_asin": parent_asin},
            )
        )
    return chunks


def _rating_chunks(comments: list[CommunityComment]) -> list[CommentChunk]:
    low_rating = [
        comment
        for comment in comments
        if comment.source_rating is not None and comment.source_rating <= 2
    ]
    positive = [
        comment
        for comment in comments
        if comment.source_rating is not None and comment.source_rating >= 4
    ]
    chunks: list[CommentChunk] = []
    if low_rating:
        chunks.append(
            _make_chunk(
                chunk_id="rating_low_helpful",
                label="Low-rating objection pressure",
                description=(
                    "Most useful low-rating reviews, used to identify objections "
                    "that could scale into paid-media risk."
                ),
                chunk_type="rating_low",
                comments=_select_representative_comments(
                    low_rating, settings.llm_chunk_comments
                ),
                source_comments=low_rating,
            )
        )
    if positive:
        chunks.append(
            _make_chunk(
                chunk_id="rating_positive_hooks",
                label="High-rating message hooks",
                description=(
                    "Positive reviews, used to identify defensible message angles "
                    "and creator hooks."
                ),
                chunk_type="rating_positive",
                comments=_select_representative_comments(
                    positive, settings.llm_chunk_comments
                ),
                source_comments=positive,
            )
        )
    return chunks


def _make_chunk(
    chunk_id: str,
    label: str,
    description: str,
    chunk_type: str,
    comments: list[CommunityComment],
    source_comments: list[CommunityComment],
    metadata: dict | None = None,
) -> CommentChunk:
    ratings = [
        comment.source_rating
        for comment in source_comments
        if comment.source_rating is not None
    ]
    affected_products = {
        comment.parent_product_id or comment.product_id
        for comment in source_comments
        if comment.parent_product_id or comment.product_id
    }
    chunk_metadata = {
        "source_comment_count": len(source_comments),
        "selected_comment_count": len(comments),
        "affected_products": len(affected_products),
        "average_rating": round(mean(ratings), 2) if ratings else None,
        "low_rating_count": sum(1 for rating in ratings if rating <= 2),
        "high_rating_count": sum(1 for rating in ratings if rating >= 4),
        "helpful_votes": sum(comment.helpful_vote or 0 for comment in source_comments),
        **(metadata or {}),
    }
    return CommentChunk(
        id=chunk_id,
        label=label,
        description=description,
        chunk_type=chunk_type,
        comments=comments,
        metadata=chunk_metadata,
    )


def _dedupe_chunks(chunks: list[CommentChunk]) -> list[CommentChunk]:
    deduped: list[CommentChunk] = []
    seen: set[str] = set()
    for chunk in chunks:
        comment_key = tuple(sorted(comment.id for comment in chunk.comments))
        key = f"{chunk.id}:{comment_key}"
        if key in seen or not chunk.comments:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def _select_representative_comments(
    comments: list[CommunityComment],
    limit: int,
) -> list[CommunityComment]:
    def score(comment: CommunityComment) -> tuple:
        rating = comment.source_rating or 0
        low_rating_bonus = 5 if rating <= 2 else 0
        helpful = comment.helpful_vote or 0
        text_length = min(len(comment.text), 1200)
        return (low_rating_bonus, helpful, text_length)

    ranked = sorted(comments, key=score, reverse=True)
    return _select_comments_for_llm(ranked, limit)


def _build_signal_prompt(
    campaign_id: str,
    briefs: list[BriefDocument],
    comments: list[CommunityComment],
    products: list[ProductContext],
    chunk: CommentChunk | None = None,
) -> str:
    product_map = {
        product.parent_asin: product for product in products if product.parent_asin
    }
    brief_text = "\n\n".join(brief.text for brief in briefs)[:2000]
    source_rows = []
    for comment in comments:
        product = product_map.get(comment.parent_product_id or "")
        source_rows.append(
            {
                "source_record_id": comment.id,
                "rating": comment.source_rating,
                "title": comment.source_title,
                "text": comment.text,
                "verified_purchase": comment.verified_purchase,
                "helpful_vote": comment.helpful_vote,
                "asin": comment.product_id,
                "parent_asin": comment.parent_product_id,
                "product": {
                    "title": product.title if product else None,
                    "store": product.store if product else None,
                    "average_rating": product.average_rating if product else None,
                    "categories": product.categories if product else None,
                },
            }
        )

    topic_rows = [cluster.model_dump() for cluster in cluster_comments(comments)[:6]]
    chunk_context = {}
    if chunk is not None:
        chunk_context = {
            "id": chunk.id,
            "label": chunk.label,
            "type": chunk.chunk_type,
            "description": chunk.description,
            "source_comment_count": chunk.metadata.get("source_comment_count"),
            "affected_products": chunk.metadata.get("affected_products"),
            "average_rating": chunk.metadata.get("average_rating"),
            "helpful_votes": chunk.metadata.get("helpful_votes"),
        }
    schema = {
        "signals": [
            {
                "signal_type": "risk_flag",
                "title": "short actionable title",
                "summary": "2 sentence interpretation tied to campaign decisions",
                "confidence": 0.0,
                "severity": "low|medium|high",
                "recommended_action": "specific action for campaign team",
                "evidence": [
                    {
                        "source_record_id": "must match an input source_record_id",
                        "quote": "exact substring copied from text",
                        "reason": "why this quote supports the signal",
                    }
                ],
            }
        ]
    }

    return (
        "/no_think\n"
        "Analyze these Amazon coffee reviews as campaign intelligence.\n"
        "Return one JSON object only. Do not include markdown.\n"
        "Create 3 to 5 evidence-backed signals for this analysis chunk.\n"
        "Use the topic clusters as directional context, then cite exact source rows.\n"
        "Allowed signal_type values: audience_tension, risk_flag, message_angle, "
        "content_opportunity, next_action.\n"
        "Rules:\n"
        "- Every signal must include at least one evidence item.\n"
        "- evidence.source_record_id must exactly match one input source_record_id.\n"
        "- evidence.quote should be an exact substring copied from that comment text.\n"
        "- Prefer actionable campaign decisions over generic sentiment labels.\n"
        "- confidence must be between 0 and 1.\n"
        "- severity must be low, medium, or high.\n\n"
        f"Campaign id: {campaign_id}\n"
        f"Campaign brief:\n{brief_text}\n\n"
        f"Analysis chunk:\n{json.dumps(chunk_context, ensure_ascii=False)}\n\n"
        f"Topic clusters:\n{json.dumps(topic_rows, ensure_ascii=False)}\n\n"
        f"Required JSON schema example:\n{json.dumps(schema)}\n\n"
        f"Source rows:\n{json.dumps(source_rows, ensure_ascii=False)}"
    )


def _signals_from_llm_payload(
    campaign_id: str,
    payload: dict,
    comments: list[CommunityComment],
    support_comments: list[CommunityComment] | None = None,
    chunk: CommentChunk | None = None,
) -> list[CampaignSignal]:
    source_map: dict[str, SourceRecord] = {comment.id: comment for comment in comments}
    raw_signals = payload.get("signals")
    if not isinstance(raw_signals, list):
        raise ValueError("LLM JSON must contain a signals list.")

    signals: list[CampaignSignal] = []
    for raw in raw_signals[:8]:
        if not isinstance(raw, dict):
            continue
        evidence = _coerce_evidence(raw.get("evidence"), source_map)
        if not evidence:
            continue
        signal = CampaignSignal(
            campaign_id=campaign_id,
            signal_type=SignalType(raw.get("signal_type")),
            title=str(raw.get("title") or "Untitled signal")[:140],
            summary=str(raw.get("summary") or "")[:900],
            confidence=float(raw.get("confidence") or 0.5),
            severity=str(raw.get("severity") or "medium").lower(),
            recommended_action=str(raw.get("recommended_action") or "")[:900],
            evidence=evidence,
            source_chunks=[chunk.id] if chunk else [],
        )
        _apply_signal_strength(signal, support_comments or comments)
        signals.append(signal)
    return signals


def _coerce_evidence(
    raw_evidence: object, source_map: dict[str, SourceRecord]
) -> list[EvidenceItem]:
    if not isinstance(raw_evidence, list):
        return []

    evidence_items: list[EvidenceItem] = []
    for raw in raw_evidence[:4]:
        if not isinstance(raw, dict):
            continue
        source_record_id = str(raw.get("source_record_id") or "")
        source = source_map.get(source_record_id)
        if source is None or not isinstance(source, CommunityComment):
            continue

        quote = str(raw.get("quote") or "").strip()
        if quote not in source.text:
            quote = source.text[:180]

        evidence_items.append(
            EvidenceItem(
                source_record_id=source.id,
                quote=quote,
                reason=str(raw.get("reason") or "LLM-selected source evidence.")[:500],
            )
        )

    return evidence_items


def _merge_similar_signals(
    signals: list[CampaignSignal],
    comments: list[CommunityComment],
) -> list[CampaignSignal]:
    merged: list[CampaignSignal] = []
    for signal in sorted(signals, key=_signal_sort_key, reverse=True):
        match = _find_merge_target(merged, signal)
        if match is None:
            merged.append(signal)
            continue
        _merge_signal_into(match, signal)

    for signal in merged:
        if signal.strength:
            signal.strength["evidence_count"] = len(signal.evidence)
            signal.strength["source_chunk_count"] = len(signal.source_chunks)
            continue
        if evidence_comments := _evidence_comments(signal, comments):
            _apply_signal_strength(signal, evidence_comments)

    return sorted(merged, key=_signal_sort_key, reverse=True)


def _find_merge_target(
    existing_signals: list[CampaignSignal],
    signal: CampaignSignal,
) -> CampaignSignal | None:
    signal_tokens = _signal_tokens(signal)
    for existing in existing_signals:
        if existing.signal_type != signal.signal_type:
            continue
        existing_tokens = _signal_tokens(existing)
        if _jaccard(existing_tokens, signal_tokens) >= 0.35:
            return existing
    return None


def _merge_signal_into(target: CampaignSignal, source: CampaignSignal) -> None:
    target.confidence = max(target.confidence, source.confidence)
    target.severity = _higher_severity(target.severity, source.severity)
    if len(source.summary) > len(target.summary):
        target.summary = source.summary
    if len(source.recommended_action) > len(target.recommended_action):
        target.recommended_action = source.recommended_action

    existing_evidence_ids = {item.source_record_id for item in target.evidence}
    for item in source.evidence:
        if item.source_record_id not in existing_evidence_ids:
            target.evidence.append(item)
            existing_evidence_ids.add(item.source_record_id)
    target.evidence = target.evidence[:8]
    target.source_chunks = sorted(set(target.source_chunks + source.source_chunks))
    target.strength = _combine_strength(target.strength, source.strength)
    target.strength["source_chunk_count"] = len(target.source_chunks)


def _apply_signal_strength(
    signal: CampaignSignal,
    support_comments: list[CommunityComment],
) -> None:
    ratings = [
        comment.source_rating
        for comment in support_comments
        if comment.source_rating is not None
    ]
    affected_products = {
        comment.parent_product_id or comment.product_id
        for comment in support_comments
        if comment.parent_product_id or comment.product_id
    }
    low_count = sum(1 for rating in ratings if rating <= 2)
    high_count = sum(1 for rating in ratings if rating >= 4)
    signal.strength = {
        "supporting_review_count": len(support_comments),
        "evidence_count": len(signal.evidence),
        "affected_products": len(affected_products),
        "average_rating": round(mean(ratings), 2) if ratings else None,
        "low_rating_count": low_count,
        "high_rating_count": high_count,
        "rating_skew": round(low_count / len(ratings), 3) if ratings else None,
        "helpful_votes": sum(comment.helpful_vote or 0 for comment in support_comments),
        "source_chunk_count": len(signal.source_chunks),
    }


def _combine_strength(left: dict, right: dict) -> dict:
    return {
        "supporting_review_count": max(
            left.get("supporting_review_count", 0),
            right.get("supporting_review_count", 0),
        ),
        "evidence_count": left.get("evidence_count", 0)
        + right.get("evidence_count", 0),
        "affected_products": max(
            left.get("affected_products", 0),
            right.get("affected_products", 0),
        ),
        "average_rating": left.get("average_rating") or right.get("average_rating"),
        "low_rating_count": max(
            left.get("low_rating_count", 0), right.get("low_rating_count", 0)
        ),
        "high_rating_count": max(
            left.get("high_rating_count", 0), right.get("high_rating_count", 0)
        ),
        "rating_skew": left.get("rating_skew") or right.get("rating_skew"),
        "helpful_votes": left.get("helpful_votes", 0) + right.get("helpful_votes", 0),
        "source_chunk_count": max(
            left.get("source_chunk_count", 0),
            right.get("source_chunk_count", 0),
        ),
    }


def _evidence_comments(
    signal: CampaignSignal,
    comments: list[CommunityComment],
) -> list[CommunityComment]:
    source_map = {comment.id: comment for comment in comments}
    return [
        source_map[item.source_record_id]
        for item in signal.evidence
        if item.source_record_id in source_map
    ]


def _signal_sort_key(signal: CampaignSignal) -> tuple:
    strength = signal.strength or {}
    return (
        SEVERITY_RANK.get(signal.severity, 0),
        strength.get("supporting_review_count", 0),
        strength.get("affected_products", 0),
        signal.confidence,
        len(signal.evidence),
    )


def _signal_tokens(signal: CampaignSignal) -> set[str]:
    text = f"{signal.title} {signal.summary}".lower()
    words = re.findall(r"[a-z0-9]+", text)
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "coffee",
        "product",
        "review",
        "reviews",
        "campaign",
    }
    return {word for word in words if len(word) > 3 and word not in stopwords}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0
    return len(left & right) / len(left | right)


def _higher_severity(left: str, right: str) -> str:
    return left if SEVERITY_RANK.get(left, 0) >= SEVERITY_RANK.get(right, 0) else right


def _select_comments_for_llm(
    comments: list[CommunityComment], limit: int
) -> list[CommunityComment]:
    negative = [
        comment
        for comment in comments
        if comment.source_rating is not None and comment.source_rating <= 2
    ]
    mixed = [
        comment
        for comment in comments
        if comment.source_rating is not None and comment.source_rating == 3
    ]
    positive = [
        comment
        for comment in comments
        if comment.source_rating is not None and comment.source_rating >= 4
    ]
    buckets = [negative, mixed, positive]
    selected: list[CommunityComment] = []

    while len(selected) < limit and any(buckets):
        for bucket in buckets:
            if bucket and len(selected) < limit:
                selected.append(bucket.pop(0))

    if len(selected) < limit:
        seen = {comment.id for comment in selected}
        selected.extend(comment for comment in comments if comment.id not in seen)

    return selected[:limit]


def _quote(text: str, term: str) -> str:
    lower_text = text.lower()
    lower_term = term.lower()
    index = lower_text.find(lower_term)
    if index < 0:
        return text[:160]
    start = max(index - 70, 0)
    end = min(index + len(term) + 90, len(text))
    return text[start:end].strip()


def _extract_comment_signals(
    campaign_id: str, comments: list[CommunityComment]
) -> list[CampaignSignal]:
    signals: list[CampaignSignal] = []
    risk_hits: dict[str, list[CommunityComment]] = {term: [] for term in RISK_TERMS}
    positive_hits: dict[str, list[CommunityComment]] = {
        term: [] for term in POSITIVE_TERMS
    }

    for comment in comments:
        text = comment.text.lower()
        matched_risk = False
        for term in RISK_TERMS:
            if term in text:
                risk_hits[term].append(comment)
                matched_risk = True
                break
        if (
            not matched_risk
            and comment.source_rating is not None
            and comment.source_rating <= 2
        ):
            risk_hits.setdefault("negative_review", []).append(comment)
        for term in POSITIVE_TERMS:
            if term in text:
                positive_hits[term].append(comment)

    for term, hits in risk_hits.items():
        if not hits:
            continue
        signal = CampaignSignal(
            campaign_id=campaign_id,
            signal_type=SignalType.risk_flag,
            title=_risk_title(term),
            summary=RISK_TERMS[term],
            confidence=min(0.95, 0.55 + len(hits) * 0.08),
            severity="high" if len(hits) >= 3 else "medium",
            recommended_action=_risk_action(term),
            evidence=[
                EvidenceItem(
                    source_record_id=hit.id,
                    quote=_quote(hit.text, term),
                    reason="Review language points to a buyer objection.",
                )
                for hit in hits[:3]
            ],
        )
        _apply_signal_strength(signal, hits)
        signals.append(signal)

    for term, hits in positive_hits.items():
        if not hits:
            continue
        signal = CampaignSignal(
            campaign_id=campaign_id,
            signal_type=SignalType.message_angle,
            title=_positive_title(term),
            summary=POSITIVE_TERMS[term],
            confidence=min(0.92, 0.52 + len(hits) * 0.07),
            severity="low",
            recommended_action=_positive_action(term),
            evidence=[
                EvidenceItem(
                    source_record_id=hit.id,
                    quote=_quote(hit.text, term),
                    reason="Positive review language can support campaign copy.",
                )
                for hit in hits[:3]
            ],
        )
        _apply_signal_strength(signal, hits)
        signals.append(signal)

    rating_buckets = Counter(
        "low" if (comment.source_rating or 0) <= 2 else "high"
        for comment in comments
        if comment.source_rating
    )
    if rating_buckets["low"] and rating_buckets["high"]:
        low = next(
            comment
            for comment in comments
            if comment.source_rating and comment.source_rating <= 2
        )
        high = next(
            comment
            for comment in comments
            if comment.source_rating and comment.source_rating >= 4
        )
        tension = CampaignSignal(
            campaign_id=campaign_id,
            signal_type=SignalType.audience_tension,
            title="Product love is split by expectation gaps",
            summary=(
                "The review set contains both enthusiastic benefit language and "
                "low-rating objections, so campaign copy should set expectations "
                "plainly instead of overpromising."
            ),
            confidence=0.78,
            severity="medium",
            recommended_action=(
                "Pair creator praise with concrete usage details, especially "
                "scent, texture, package handling, and value."
            ),
            evidence=[
                EvidenceItem(
                    source_record_id=low.id,
                    quote=low.text[:160],
                    reason="Low-rating evidence shows friction.",
                ),
                EvidenceItem(
                    source_record_id=high.id,
                    quote=high.text[:160],
                    reason="High-rating evidence shows usable message language.",
                ),
            ],
        )
        _apply_signal_strength(tension, comments)
        signals.append(tension)

    return signals[:8]


def _extract_creator_signals(
    campaign_id: str, creators: list[CreatorProfile]
) -> list[CampaignSignal]:
    if not creators:
        return []

    best = max(creators, key=lambda creator: creator.engagement_rate)
    return [
        CampaignSignal(
            campaign_id=campaign_id,
            signal_type=SignalType.brand_fit,
            title=f"{best.name} is the strongest fit for trust-building content",
            summary=(
                f"{best.name}'s {best.niche} positioning and "
                f"{best.engagement_rate:.1f}% engagement rate make them a useful "
                "fit for objection-handling content."
            ),
            confidence=0.74,
            severity="low",
            recommended_action=(
                "Use this creator for a practical product test script that names "
                "scent, texture, and value tradeoffs directly."
            ),
            evidence=[
                EvidenceItem(
                    source_record_id=best.id,
                    quote=best.sample_caption,
                    reason="Sample caption shows creator voice and fit.",
                )
            ],
        )
    ]


def _extract_performance_signals(
    campaign_id: str, metrics: list[PerformanceMetric]
) -> list[CampaignSignal]:
    if not metrics:
        return []

    risky = max(metrics, key=lambda metric: metric.sentiment_negative)
    efficient = min(metrics, key=lambda metric: metric.cpc)

    return [
        CampaignSignal(
            campaign_id=campaign_id,
            signal_type=SignalType.next_action,
            title="Separate efficient traffic from negative comment pressure",
            summary=(
                f"{efficient.content_id} has the lowest CPC, while "
                f"{risky.content_id} carries the highest negative-comment share. "
                "The next review should compare their hooks before scaling spend."
            ),
            confidence=0.72,
            severity="medium",
            recommended_action=(
                "Keep spend live on the efficient content, but rewrite or pause "
                "the hook with the highest negative-comment rate."
            ),
            evidence=[
                EvidenceItem(
                    source_record_id=efficient.id,
                    quote=(
                        f"{efficient.content_id}: CPC {efficient.cpc}, CTR "
                        f"{efficient.ctr}, conversions {efficient.conversions}"
                    ),
                    reason="Performance row shows efficient traffic.",
                ),
                EvidenceItem(
                    source_record_id=risky.id,
                    quote=(
                        f"{risky.content_id}: negative sentiment "
                        f"{risky.sentiment_negative}, comments {risky.comment_volume}"
                    ),
                    reason="Performance row shows comment risk.",
                ),
            ],
        )
    ]


def _risk_title(term: str) -> str:
    return {
        "leak": "Packaging leakage could derail first impressions",
        "broken": "Delivery damage needs a response path",
        "irritat": "Sensitive-skin claims need careful wording",
        "rash": "Skin reaction comments require escalation rules",
        "strong": "Scent strength may polarize the audience",
        "expensive": "Price-value skepticism should be handled upfront",
        "sticky": "Texture objections need creator demonstration",
        "watery": "Weak brew language threatens roast positioning",
        "bitter": "Bitterness complaints may hurt taste-quality perception",
        "stale": "Freshness concerns need a trust response",
        "weak": "Weak flavor complaints may limit bold claims",
        "gross": "Strong rejection language should be monitored",
        "not coffee": "Authenticity concerns may hurt flavored coffee claims",
        "negative_review": "Low-rating coffee reviews show campaign friction",
    }.get(term, "Review language indicates a campaign risk")


def _risk_action(term: str) -> str:
    return {
        "leak": "Add packaging expectations and customer-care escalation notes.",
        "broken": (
            "Prepare a delivery-damage response and avoid fragile-premium claims."
        ),
        "irritat": (
            "Avoid broad sensitivity claims and direct viewers to patch-test language."
        ),
        "rash": "Keep medical-adjacent claims out of creator scripts.",
        "strong": "Have creators describe scent intensity in plain language.",
        "expensive": "Anchor copy around usage occasions and value per use.",
        "sticky": "Show texture on skin or hair before making comfort claims.",
        "watery": "Avoid boldness claims unless the SKU has matching review support.",
        "bitter": "Ask creators to describe taste profile and brew method plainly.",
        "stale": "Monitor freshness complaints and prepare customer-care responses.",
        "weak": "Clarify roast strength and recommended brew settings.",
        "gross": "Review negative comments before scaling flavored-coffee ads.",
        "not coffee": "Avoid flavor claims that imply a classic coffee taste.",
        "negative_review": "Group low-rating comments by cause before scaling spend.",
    }.get(term, "Turn the objection into a specific creator talking point.")


def _positive_title(term: str) -> str:
    return {
        "soft": "Softness language is a credible benefit angle",
        "gentle": "Gentle-use proof can support clean beauty positioning",
        "smell": "Scent can carry sensory creator content",
        "works": "Effectiveness language can support conversion copy",
        "moistur": "Moisture benefit is a natural content opportunity",
        "smooth": "Smoothness language can support a taste-led angle",
        "bold": "Bold flavor is a useful coffee claim when evidence supports it",
        "fresh": "Freshness language can support quality messaging",
        "keurig": "Keurig convenience can anchor single-serve content",
        "espresso": "Espresso use cases can support product-specific content",
    }.get(term, "Positive review language can become campaign copy")


def _positive_action(term: str) -> str:
    return {
        "soft": "Ask creators to show before-and-after feel, not just final results.",
        "gentle": (
            "Pair gentle language with usage caveats and ingredient transparency."
        ),
        "smell": "Let creators describe scent notes and strength in their own words.",
        "works": "Use specific use cases instead of broad performance claims.",
        "moistur": "Build a demo around routine timing and visible texture.",
        "smooth": "Use taste-test clips that compare smoothness and bitterness.",
        "bold": "Reserve boldness claims for SKUs with strong review support.",
        "fresh": "Have creators show package condition and brew freshness cues.",
        "keurig": "Show the exact machine and cup size used in the demo.",
        "espresso": "Separate espresso messaging from regular coffee-pod messaging.",
    }.get(term, "Turn the phrase into a tested message angle.")
