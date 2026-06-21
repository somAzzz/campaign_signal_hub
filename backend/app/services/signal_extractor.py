import json
from collections import Counter
from pathlib import Path

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
from app.services.analysis import cluster_comments
from app.services.llm_client import get_llm_client
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


def extract_signals(campaign_id: str) -> list[CampaignSignal]:
    repo.clear_campaign_signals(campaign_id)
    records = repo.campaign_records(campaign_id)
    briefs = [record for record in records if isinstance(record, BriefDocument)]
    comments = [record for record in records if isinstance(record, CommunityComment)]
    products = [record for record in records if isinstance(record, ProductContext)]
    creators = [record for record in records if isinstance(record, CreatorProfile)]
    metrics = [record for record in records if isinstance(record, PerformanceMetric)]

    signals = _extract_llm_comment_signals(campaign_id, briefs, comments, products)
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
) -> list[CampaignSignal]:
    if not comments:
        return []

    prompt = _build_signal_prompt(
        campaign_id,
        briefs,
        _select_comments_for_llm(comments, settings.llm_batch_comments),
        products,
    )
    try:
        payload = get_llm_client().complete_json(prompt)
        run = _store_llm_output(campaign_id, prompt, payload, 0)
        signals = _signals_from_llm_payload(campaign_id, payload, comments)
        run.parsed_signal_count = len(signals)
        _write_llm_run(run)
        return signals
    except Exception as exc:
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
    payload: dict,
    parsed_signal_count: int,
) -> LLMExtractionRun:
    run = LLMExtractionRun(
        campaign_id=campaign_id,
        provider=settings.llm_provider,
        model=settings.sglang_model if settings.llm_provider == "sglang" else None,
        prompt=prompt,
        raw_output=payload,
        parsed_signal_count=parsed_signal_count,
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


def _build_signal_prompt(
    campaign_id: str,
    briefs: list[BriefDocument],
    comments: list[CommunityComment],
    products: list[ProductContext],
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
        "Create 4 to 7 evidence-backed signals for a marketing campaign team.\n"
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
        f"Topic clusters:\n{json.dumps(topic_rows, ensure_ascii=False)}\n\n"
        f"Required JSON schema example:\n{json.dumps(schema)}\n\n"
        f"Source rows:\n{json.dumps(source_rows, ensure_ascii=False)}"
    )


def _signals_from_llm_payload(
    campaign_id: str,
    payload: dict,
    comments: list[CommunityComment],
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
        signals.append(
            CampaignSignal(
                campaign_id=campaign_id,
                signal_type=SignalType(raw.get("signal_type")),
                title=str(raw.get("title") or "Untitled signal")[:140],
                summary=str(raw.get("summary") or "")[:900],
                confidence=float(raw.get("confidence") or 0.5),
                severity=str(raw.get("severity") or "medium").lower(),
                recommended_action=str(raw.get("recommended_action") or "")[:900],
                evidence=evidence,
            )
        )
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
        signals.append(
            CampaignSignal(
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
        )

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
