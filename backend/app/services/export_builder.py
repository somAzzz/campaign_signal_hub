from app.models.signal import SignalStatus
from app.models.source import CommunityComment
from app.services.analysis import campaign_topic_clusters, signal_strength
from app.services.repository import repo


def _active_signals(campaign_id: str):
    return [
        signal
        for signal in repo.campaign_signals(campaign_id)
        if signal.status != SignalStatus.dismissed
    ]


def build_campaign_export(campaign_id: str, client_safe: bool = True) -> dict:
    campaign = repo.campaigns[campaign_id]
    signals = _active_signals(campaign_id)
    risks = [signal for signal in signals if signal.signal_type == "risk_flag"]
    actions = [signal for signal in signals if signal.signal_type == "next_action"]
    tensions = [
        signal for signal in signals if signal.signal_type == "audience_tension"
    ]

    return {
        "campaign": {
            "client": campaign.client,
            "brand": campaign.brand,
            "objective": campaign.objective,
        },
        "summary": (
            f"{campaign.brand} has {len(signals)} active signals, including "
            f"{len(risks)} risk flags and {len(actions)} next actions."
        ),
        "top_audience_tensions": [_signal_summary(signal) for signal in tensions[:3]],
        "top_risks": [_signal_summary(signal) for signal in risks[:3]],
        "recommended_next_actions": [_signal_summary(signal) for signal in actions[:3]],
        "topic_clusters": [
            cluster.model_dump() for cluster in campaign_topic_clusters(campaign_id)[:6]
        ],
        "signals": [
            {
                "type": signal.signal_type,
                "title": signal.title,
                "summary": signal.summary,
                "recommended_action": signal.recommended_action,
                "strength": signal_strength(signal),
                "evidence": [
                    _safe_evidence(item.model_dump(), client_safe)
                    for item in signal.evidence
                ],
            }
            for signal in signals
        ],
    }


def build_markdown_export(campaign_id: str, client_safe: bool = True) -> str:
    export = build_campaign_export(campaign_id, client_safe=client_safe)
    campaign = export["campaign"]
    lines = [
        f"# {campaign['brand']} Campaign Signal Brief",
        "",
        f"Client: {campaign['client']}",
        f"Objective: {campaign['objective']}",
        "",
        "## Executive Summary",
        "",
        export["summary"],
        "",
        "## Top Audience Tensions",
        "",
        *_signal_lines(export["top_audience_tensions"]),
        "## Top Risks",
        "",
        *_signal_lines(export["top_risks"]),
        "## Recommended Next Actions",
        "",
        *_signal_lines(export["recommended_next_actions"]),
        "## Topic Clusters",
        "",
    ]
    for cluster in export["topic_clusters"]:
        lines.extend(
            [
                f"- **{cluster['label']}**: {cluster['review_count']} reviews across "
                f"{cluster['affected_products']} products. Avg rating "
                f"{cluster['average_rating'] or 'n/a'}.",
            ]
        )

    lines.extend(["", "## Evidence Appendix", ""])
    for signal in export["signals"]:
        lines.extend([f"### {signal['title']}", "", signal["summary"], ""])
        lines.append(f"Recommended action: {signal['recommended_action']}")
        lines.append("")
        for evidence in signal["evidence"]:
            lines.append(f'- "{evidence["quote"]}"')
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _signal_summary(signal) -> dict:
    return {
        "title": signal.title,
        "summary": signal.summary,
        "recommended_action": signal.recommended_action,
        "severity": signal.severity,
        "strength": signal_strength(signal),
    }


def _signal_lines(signals: list[dict]) -> list[str]:
    if not signals:
        return ["- No active signal in this category.", ""]
    lines: list[str] = []
    for signal in signals:
        lines.extend(
            [
                f"- **{signal['title']}** ({signal['severity']}): {signal['summary']}",
                f"  Action: {signal['recommended_action']}",
            ]
        )
    lines.append("")
    return lines


def _safe_evidence(evidence: dict, client_safe: bool) -> dict:
    if not client_safe:
        return evidence
    record = repo.source_records.get(evidence["source_record_id"])
    source = {}
    if isinstance(record, CommunityComment):
        source = {
            "rating": record.source_rating,
            "product_id": record.product_id,
            "parent_product_id": record.parent_product_id,
            "verified_purchase": record.verified_purchase,
        }
    return {
        "quote": evidence["quote"],
        "reason": evidence["reason"],
        "source": source,
    }
