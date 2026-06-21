from app.models.signal import CampaignSignal, QualityEvent
from app.models.source import CommunityComment, SourceRecord


def validate_signal(
    signal: CampaignSignal, source_records: list[SourceRecord]
) -> list[QualityEvent]:
    events: list[QualityEvent] = []
    record_map = {record.id: record for record in source_records}

    if not signal.evidence:
        events.append(
            QualityEvent(
                campaign_id=signal.campaign_id,
                signal_id=signal.id,
                level="error",
                message="Signal has no evidence.",
            )
        )

    for evidence in signal.evidence:
        source = record_map.get(evidence.source_record_id)
        if source is None:
            events.append(
                QualityEvent(
                    campaign_id=signal.campaign_id,
                    signal_id=signal.id,
                    source_record_id=evidence.source_record_id,
                    level="error",
                    message="Evidence references an unknown source record.",
                )
            )
            continue

        source_text = getattr(source, "text", "")
        if isinstance(source, CommunityComment) and evidence.quote not in source_text:
            events.append(
                QualityEvent(
                    campaign_id=signal.campaign_id,
                    signal_id=signal.id,
                    source_record_id=source.id,
                    level="error",
                    message="Evidence quote does not appear in source text.",
                    details={"quote": evidence.quote},
                )
            )

    if signal.signal_type == "risk_flag" and signal.severity not in {
        "low",
        "medium",
        "high",
    }:
        events.append(
            QualityEvent(
                campaign_id=signal.campaign_id,
                signal_id=signal.id,
                level="error",
                message="Risk flag has invalid severity.",
                details={"severity": signal.severity},
            )
        )

    if len(signal.summary.split()) < 5:
        events.append(
            QualityEvent(
                campaign_id=signal.campaign_id,
                signal_id=signal.id,
                level="warning",
                message="Signal summary is too short to be useful.",
            )
        )

    return events
