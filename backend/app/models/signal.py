from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class SignalType(StrEnum):
    audience_tension = "audience_tension"
    brand_fit = "brand_fit"
    message_angle = "message_angle"
    risk_flag = "risk_flag"
    content_opportunity = "content_opportunity"
    next_action = "next_action"


class SignalStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    dismissed = "dismissed"


class EvidenceItem(BaseModel):
    source_record_id: str
    quote: str
    reason: str


class CampaignSignal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    signal_type: SignalType
    title: str
    summary: str
    confidence: float = Field(ge=0, le=1)
    severity: str = "medium"
    recommended_action: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    status: SignalStatus = SignalStatus.pending


class SignalUpdate(BaseModel):
    status: SignalStatus


class QualityEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    source_record_id: str | None = None
    signal_id: str | None = None
    level: str = "warning"
    message: str
    details: dict = Field(default_factory=dict)


class LLMExtractionRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    provider: str = "sglang"
    model: str | None = None
    endpoint: str | None = None
    status: str = "succeeded"
    dataset_id: str | None = None
    dataset: dict | None = None
    scope: dict | None = None
    source_files: list[dict] = Field(default_factory=list)
    input_summary: dict = Field(default_factory=dict)
    selected_source_record_ids: list[str] = Field(default_factory=list)
    prompt: str
    raw_output: dict
    raw_response: dict = Field(default_factory=dict)
    request_metadata: dict = Field(default_factory=dict)
    response_metadata: dict = Field(default_factory=dict)
    parsed_signal_count: int = 0
    error: str | None = None
    output_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
