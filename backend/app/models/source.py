from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceFile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    filename: str
    source_type: str
    row_count: int = 0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class SourceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    source_file_id: str
    source_row_id: str
    record_type: str
    raw_payload: dict


class BriefDocument(SourceRecord):
    record_type: str = "brief"
    title: str = "Campaign Brief"
    text: str


class CommunityComment(SourceRecord):
    record_type: str = "community_comment"
    platform: str = "amazon"
    author_id: str | None = None
    text: str
    source_title: str | None = None
    source_rating: float | None = None
    product_id: str | None = None
    parent_product_id: str | None = None
    product_category: str | None = None
    source_timestamp: str | int | None = None
    verified_purchase: bool | None = None
    helpful_vote: int | None = None


class ProductContext(SourceRecord):
    record_type: str = "product_context"
    parent_asin: str
    asin: str | None = None
    title: str
    store: str | None = None
    main_category: str | None = None
    average_rating: float | None = None
    rating_number: int | None = None
    price: float | None = None
    categories: str | None = None
    features: str | None = None
    description: str | None = None


class CreatorProfile(SourceRecord):
    record_type: str = "creator_profile"
    creator_id: str
    name: str
    platform: str
    niche: str
    audience_profile: str
    avg_views: int
    engagement_rate: float
    content_style: str
    brand_safety_notes: str
    past_brand_categories: str
    sample_caption: str


class PerformanceMetric(SourceRecord):
    record_type: str = "performance_metric"
    date: str
    platform: str
    campaign_phase: str
    content_id: str
    creator_id: str
    impressions: int
    clicks: int
    ctr: float
    spend: float
    cpc: float
    conversions: int
    conversion_rate: float
    sentiment_positive: float
    sentiment_negative: float
    comment_volume: int
