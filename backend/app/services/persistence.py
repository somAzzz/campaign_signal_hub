import json
import sqlite3
from pathlib import Path

from app.models.campaign import Campaign
from app.models.signal import CampaignSignal, LLMExtractionRun, QualityEvent
from app.models.source import (
    BriefDocument,
    CommunityComment,
    CreatorProfile,
    PerformanceMetric,
    ProductContext,
    SourceFile,
    SourceRecord,
)
from app.services.repository import repo

STATE_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "state" / "campaign_state.sqlite"
)

RECORD_MODELS = {
    "brief": BriefDocument,
    "community_comment": CommunityComment,
    "product_context": ProductContext,
    "creator_profile": CreatorProfile,
    "performance_metric": PerformanceMetric,
}


def load_snapshot() -> bool:
    payload = _read_payload()
    if payload is None:
        return False

    repo.reset()
    repo.campaigns = {
        item["id"]: Campaign.model_validate(item)
        for item in payload.get("campaigns", [])
    }
    repo.source_files = {
        item["id"]: SourceFile.model_validate(item)
        for item in payload.get("source_files", [])
    }
    repo.source_records = {
        item["id"]: _source_record_from_payload(item)
        for item in payload.get("source_records", [])
    }
    repo.signals = {
        item["id"]: CampaignSignal.model_validate(item)
        for item in payload.get("signals", [])
    }
    repo.quality_events = {
        item["id"]: QualityEvent.model_validate(item)
        for item in payload.get("quality_events", [])
    }
    repo.llm_runs = {
        item["id"]: LLMExtractionRun.model_validate(item)
        for item in payload.get("llm_runs", [])
    }
    return bool(repo.campaigns)


def save_snapshot() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "campaigns": [item.model_dump(mode="json") for item in repo.campaigns.values()],
        "source_files": [
            item.model_dump(mode="json") for item in repo.source_files.values()
        ],
        "source_records": [
            item.model_dump(mode="json") for item in repo.source_records.values()
        ],
        "signals": [item.model_dump(mode="json") for item in repo.signals.values()],
        "quality_events": [
            item.model_dump(mode="json") for item in repo.quality_events.values()
        ],
        "llm_runs": [item.model_dump(mode="json") for item in repo.llm_runs.values()],
    }
    with sqlite3.connect(STATE_PATH) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS snapshots "
            "(key TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO snapshots (key, payload) VALUES (?, ?)",
            ("repo", json.dumps(payload)),
        )
        connection.commit()


def _read_payload() -> dict | None:
    if not STATE_PATH.exists():
        return None
    with sqlite3.connect(STATE_PATH) as connection:
        row = connection.execute(
            "SELECT payload FROM snapshots WHERE key = ?", ("repo",)
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def _source_record_from_payload(payload: dict) -> SourceRecord:
    model = RECORD_MODELS.get(payload.get("record_type"), SourceRecord)
    return model.model_validate(payload)
