import csv
from collections.abc import Iterable
from io import StringIO

from app.models.signal import QualityEvent
from app.models.source import (
    BriefDocument,
    CommunityComment,
    CreatorProfile,
    PerformanceMetric,
    ProductContext,
    SourceFile,
)
from app.services.repository import repo

COMMENT_ALIASES = {
    "text": ["text", "reviewText", "review_text", "comment", "body"],
    "source_title": ["title", "review_title", "summary"],
    "source_rating": ["rating", "overall", "score", "stars"],
    "author_id": ["user_id", "reviewerID", "reviewer_id", "author_id"],
    "product_id": ["asin", "product_id"],
    "parent_product_id": ["parent_asin", "parent_product_id"],
    "source_timestamp": ["timestamp", "unixReviewTime", "review_time"],
    "verified_purchase": ["verified_purchase", "verified"],
    "helpful_vote": ["helpful_vote", "helpful"],
}


def _first(row: dict[str, str], aliases: Iterable[str]) -> str | None:
    for key in aliases:
        if key in row and str(row[key]).strip():
            return str(row[key]).strip()
    return None


def _as_int(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def _as_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _as_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return value.strip().lower() in {"1", "true", "yes", "y"}


def parse_brief(campaign_id: str, filename: str, text: str) -> list[BriefDocument]:
    source_file = repo.add_source_file(
        SourceFile(
            campaign_id=campaign_id,
            filename=filename,
            source_type="brief",
            row_count=1,
        )
    )
    record = BriefDocument(
        campaign_id=campaign_id,
        source_file_id=source_file.id,
        source_row_id="1",
        title=filename,
        text=text,
        raw_payload={"text": text},
    )
    repo.add_source_records([record])
    return [record]


def parse_comments_csv(
    campaign_id: str, filename: str, content: str
) -> list[CommunityComment]:
    rows = list(csv.DictReader(StringIO(content)))
    source_file = repo.add_source_file(
        SourceFile(
            campaign_id=campaign_id,
            filename=filename,
            source_type="community_comments",
            row_count=len(rows),
        )
    )

    records: list[CommunityComment] = []
    for index, row in enumerate(rows, start=1):
        source_row_id = row.get("source_row_id") or str(index)
        text = _first(row, COMMENT_ALIASES["text"])
        if not text:
            repo.add_quality_event(
                QualityEvent(
                    campaign_id=campaign_id,
                    message="Skipped comment row without text.",
                    details={"filename": filename, "source_row_id": source_row_id},
                )
            )
            continue

        record = CommunityComment(
            campaign_id=campaign_id,
            source_file_id=source_file.id,
            source_row_id=source_row_id,
            platform=row.get("platform", "amazon"),
            author_id=_first(row, COMMENT_ALIASES["author_id"]),
            text=text,
            source_title=_first(row, COMMENT_ALIASES["source_title"]),
            source_rating=_as_float(_first(row, COMMENT_ALIASES["source_rating"])),
            product_id=_first(row, COMMENT_ALIASES["product_id"]),
            parent_product_id=_first(row, COMMENT_ALIASES["parent_product_id"]),
            product_category=row.get("product_category") or row.get("category"),
            source_timestamp=_first(row, COMMENT_ALIASES["source_timestamp"]),
            verified_purchase=_as_bool(
                _first(row, COMMENT_ALIASES["verified_purchase"])
            ),
            helpful_vote=_as_int(_first(row, COMMENT_ALIASES["helpful_vote"])),
            raw_payload=row,
        )
        records.append(record)

    repo.add_source_records(records)
    return records


def parse_creator_csv(
    campaign_id: str, filename: str, content: str
) -> list[CreatorProfile]:
    rows = list(csv.DictReader(StringIO(content)))
    source_file = repo.add_source_file(
        SourceFile(
            campaign_id=campaign_id,
            filename=filename,
            source_type="creator_profiles",
            row_count=len(rows),
        )
    )

    records: list[CreatorProfile] = []
    for index, row in enumerate(rows, start=1):
        records.append(
            CreatorProfile(
                campaign_id=campaign_id,
                source_file_id=source_file.id,
                source_row_id=str(index),
                creator_id=row["creator_id"],
                name=row["name"],
                platform=row["platform"],
                niche=row["niche"],
                audience_profile=row["audience_profile"],
                avg_views=_as_int(row.get("avg_views")),
                engagement_rate=_as_float(row.get("engagement_rate")),
                content_style=row["content_style"],
                brand_safety_notes=row["brand_safety_notes"],
                past_brand_categories=row["past_brand_categories"],
                sample_caption=row["sample_caption"],
                raw_payload=row,
            )
        )

    repo.add_source_records(records)
    return records


def parse_products_csv(
    campaign_id: str, filename: str, content: str
) -> list[ProductContext]:
    rows = list(csv.DictReader(StringIO(content)))
    source_file = repo.add_source_file(
        SourceFile(
            campaign_id=campaign_id,
            filename=filename,
            source_type="product_context",
            row_count=len(rows),
        )
    )

    records: list[ProductContext] = []
    for index, row in enumerate(rows, start=1):
        parent_asin = row.get("parent_asin") or row.get("asin")
        title = row.get("title")
        if not parent_asin or not title:
            repo.add_quality_event(
                QualityEvent(
                    campaign_id=campaign_id,
                    message="Skipped product row without parent_asin or title.",
                    details={"filename": filename, "source_row_id": str(index)},
                )
            )
            continue

        records.append(
            ProductContext(
                campaign_id=campaign_id,
                source_file_id=source_file.id,
                source_row_id=str(index),
                parent_asin=parent_asin,
                asin=row.get("asin") or None,
                title=title,
                store=row.get("store") or None,
                main_category=row.get("main_category") or None,
                average_rating=_as_float(row.get("average_rating")),
                rating_number=_as_int(row.get("rating_number")),
                price=_as_float(row.get("price")) if row.get("price") else None,
                categories=row.get("categories") or None,
                features=row.get("features") or None,
                description=row.get("description") or None,
                raw_payload=row,
            )
        )

    repo.add_source_records(records)
    return records


def parse_performance_csv(
    campaign_id: str, filename: str, content: str
) -> list[PerformanceMetric]:
    rows = list(csv.DictReader(StringIO(content)))
    source_file = repo.add_source_file(
        SourceFile(
            campaign_id=campaign_id,
            filename=filename,
            source_type="performance_metrics",
            row_count=len(rows),
        )
    )

    records: list[PerformanceMetric] = []
    for index, row in enumerate(rows, start=1):
        records.append(
            PerformanceMetric(
                campaign_id=campaign_id,
                source_file_id=source_file.id,
                source_row_id=str(index),
                date=row["date"],
                platform=row["platform"],
                campaign_phase=row["campaign_phase"],
                content_id=row["content_id"],
                creator_id=row["creator_id"],
                impressions=_as_int(row.get("impressions")),
                clicks=_as_int(row.get("clicks")),
                ctr=_as_float(row.get("ctr")),
                spend=_as_float(row.get("spend")),
                cpc=_as_float(row.get("cpc")),
                conversions=_as_int(row.get("conversions")),
                conversion_rate=_as_float(row.get("conversion_rate")),
                sentiment_positive=_as_float(row.get("sentiment_positive")),
                sentiment_negative=_as_float(row.get("sentiment_negative")),
                comment_volume=_as_int(row.get("comment_volume")),
                raw_payload=row,
            )
        )

    repo.add_source_records(records)
    return records
