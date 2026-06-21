from datetime import date, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    client: str
    brand: str
    objective: str
    target_audience: str
    tone_constraints: str = ""
    required_platforms: list[str] = Field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None


class Campaign(CampaignCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"


class CampaignDetail(Campaign):
    source_file_count: int = 0
    source_record_count: int = 0
    signal_count: int = 0
    approved_signal_count: int = 0
    risk_count: int = 0
