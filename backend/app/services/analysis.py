import csv
from collections import Counter, defaultdict
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from statistics import mean

from pydantic import BaseModel

from app.models.signal import CampaignSignal
from app.models.source import CommunityComment, ProductContext
from app.services.datasets import DATASET_CATALOG, SAMPLE_DIR
from app.services.repository import repo


class DatasetScope(BaseModel):
    mode: str = "all"
    value: str | None = None


class DatasetPreviewItem(BaseModel):
    bucket: str
    rating: float | None = None
    title: str | None = None
    text: str
    asin: str | None = None
    parent_asin: str | None = None
    verified_purchase: bool | None = None


class DatasetProfile(BaseModel):
    dataset_id: str
    row_count: int
    unique_products: int
    rating_distribution: dict[str, int]
    verified_purchase_count: int
    date_range: dict[str, str | None]
    top_brands: list[dict[str, int | str]]
    top_parent_asins: list[dict[str, int | str]]
    preview: list[DatasetPreviewItem]
    scopes: list[dict[str, str | int]]


class TopicCluster(BaseModel):
    id: str
    label: str
    description: str
    review_count: int
    affected_products: int
    average_rating: float | None = None
    helpful_votes: int = 0
    representative_quotes: list[str]


class ProductHealth(BaseModel):
    parent_asin: str
    asin: str | None = None
    title: str
    store: str | None = None
    sample_review_count: int
    sample_average_rating: float | None = None
    low_rating_count: int
    verified_review_count: int
    top_risks: list[str]
    strongest_message_angle: str | None = None
    representative_quotes: list[str]


TOPIC_DEFINITIONS = {
    "weak_flavor": {
        "label": "Weak flavor",
        "description": (
            "Reviews describe the coffee as watery, weak, thin, or lacking aroma."
        ),
        "terms": ("weak", "watery", "watered", "no flavor", "no taste", "bland"),
    },
    "bitter_taste": {
        "label": "Bitter taste",
        "description": (
            "Taste complaints center on bitterness, harshness, or burnt notes."
        ),
        "terms": ("bitter", "burnt", "harsh", "acidic", "sour"),
    },
    "freshness": {
        "label": "Freshness",
        "description": (
            "Customers mention stale product, old pods, or freshness concerns."
        ),
        "terms": ("stale", "old", "expired", "freshness", "fresh"),
    },
    "misleading_claims": {
        "label": "Misleading claims",
        "description": (
            "Reviews say flavor, roast level, quantity, or product claims feel "
            "inaccurate."
        ),
        "terms": (
            "not coffee",
            "not as described",
            "misleading",
            "doesn't taste",
            "not my flavor",
        ),
    },
    "machine_fit": {
        "label": "Machine fit",
        "description": "Single-serve use and machine compatibility shape satisfaction.",
        "terms": ("keurig", "k-cup", "k cup", "pods", "machine", "brew"),
    },
    "price_value": {
        "label": "Price/value",
        "description": (
            "Value, quantity, and price language affect purchase confidence."
        ),
        "terms": ("expensive", "price", "value", "worth", "money", "cheap"),
    },
}

POSITIVE_ANGLE_TERMS = {
    "smooth": "Smooth taste",
    "bold": "Bold flavor",
    "fresh": "Freshness",
    "keurig": "Single-serve convenience",
    "espresso": "Espresso use case",
    "flavor": "Flavor variety",
}


def get_dataset_profile(dataset_id: str) -> DatasetProfile:
    path = _dataset_path(dataset_id)
    rows = _read_dataset_rows(path)
    products = _product_store_lookup()
    parent_counts = Counter(row.get("parent_asin") or row.get("asin") for row in rows)
    parent_counts.pop("", None)
    rating_distribution = Counter(
        _rating_bucket(_as_float(row.get("rating"))) for row in rows
    )
    verified_count = sum(1 for row in rows if _as_bool(row.get("verified_purchase")))
    timestamps = [
        date
        for row in rows
        if (
            date := _timestamp_to_date(
                row.get("timestamp") or row.get("unixReviewTime")
            )
        )
    ]
    brand_counts = Counter(
        products.get(row.get("parent_asin") or row.get("asin") or "", "Unknown")
        for row in rows
    )
    brand_counts.pop("Unknown", None)

    return DatasetProfile(
        dataset_id=dataset_id,
        row_count=len(rows),
        unique_products=len(parent_counts),
        rating_distribution={
            str(key): rating_distribution[str(key)] for key in range(1, 6)
        },
        verified_purchase_count=verified_count,
        date_range={
            "start": min(timestamps).isoformat() if timestamps else None,
            "end": max(timestamps).isoformat() if timestamps else None,
        },
        top_brands=[
            {"brand": brand, "count": count}
            for brand, count in brand_counts.most_common(8)
        ],
        top_parent_asins=[
            {"parent_asin": asin, "count": count}
            for asin, count in parent_counts.most_common(10)
            if asin
        ],
        preview=_preview_rows(rows),
        scopes=_scope_options(rows, products),
    )


def build_scope_filter(scope: DatasetScope | None):
    if scope is None or scope.mode == "all":
        return None

    def row_filter(row: dict[str, str]) -> bool:
        rating = _as_float(row.get("rating"))
        parent_asin = row.get("parent_asin") or row.get("asin") or ""
        if scope.mode == "low_rating":
            return rating is not None and rating <= 2
        if scope.mode == "verified_only":
            return _as_bool(row.get("verified_purchase")) is True
        if scope.mode == "parent_asin":
            return bool(scope.value) and parent_asin == scope.value
        if scope.mode == "brand":
            store = _product_store_lookup().get(parent_asin, "")
            return bool(scope.value) and store == scope.value
        return True

    return row_filter


def cluster_comments(comments: list[CommunityComment]) -> list[TopicCluster]:
    clusters: list[TopicCluster] = []
    for topic_id, definition in TOPIC_DEFINITIONS.items():
        hits = [
            comment
            for comment in comments
            if any(term in comment.text.lower() for term in definition["terms"])
        ]
        if not hits:
            continue
        ratings = [
            comment.source_rating
            for comment in hits
            if comment.source_rating is not None
        ]
        clusters.append(
            TopicCluster(
                id=topic_id,
                label=str(definition["label"]),
                description=str(definition["description"]),
                review_count=len(hits),
                affected_products=len(
                    {
                        comment.parent_product_id or comment.product_id
                        for comment in hits
                    }
                ),
                average_rating=round(mean(ratings), 2) if ratings else None,
                helpful_votes=sum(comment.helpful_vote or 0 for comment in hits),
                representative_quotes=[comment.text[:220] for comment in hits[:3]],
            )
        )
    return sorted(clusters, key=lambda item: item.review_count, reverse=True)


def campaign_topic_clusters(campaign_id: str) -> list[TopicCluster]:
    comments = [
        record
        for record in repo.campaign_records(campaign_id)
        if isinstance(record, CommunityComment)
    ]
    return cluster_comments(comments)


def campaign_product_health(campaign_id: str) -> list[ProductHealth]:
    records = repo.campaign_records(campaign_id)
    comments = [record for record in records if isinstance(record, CommunityComment)]
    products = [record for record in records if isinstance(record, ProductContext)]
    product_map = {product.parent_asin: product for product in products}
    comments_by_parent: dict[str, list[CommunityComment]] = defaultdict(list)
    for comment in comments:
        if comment.parent_product_id:
            comments_by_parent[comment.parent_product_id].append(comment)

    health_rows: list[ProductHealth] = []
    for parent_asin, grouped_comments in comments_by_parent.items():
        product = product_map.get(parent_asin)
        ratings = [
            comment.source_rating
            for comment in grouped_comments
            if comment.source_rating is not None
        ]
        clusters = cluster_comments(grouped_comments)
        health_rows.append(
            ProductHealth(
                parent_asin=parent_asin,
                asin=product.asin if product else None,
                title=product.title if product else parent_asin,
                store=product.store if product else None,
                sample_review_count=len(grouped_comments),
                sample_average_rating=round(mean(ratings), 2) if ratings else None,
                low_rating_count=sum(
                    1
                    for comment in grouped_comments
                    if comment.source_rating is not None and comment.source_rating <= 2
                ),
                verified_review_count=sum(
                    1 for comment in grouped_comments if comment.verified_purchase
                ),
                top_risks=[cluster.label for cluster in clusters[:3]],
                strongest_message_angle=_strongest_message_angle(grouped_comments),
                representative_quotes=[
                    comment.text[:220] for comment in grouped_comments[:3]
                ],
            )
        )
    return sorted(
        health_rows,
        key=lambda item: (item.low_rating_count, item.sample_review_count),
        reverse=True,
    )


def signal_strength(signal: CampaignSignal) -> dict:
    records = {
        record.id: record
        for record in repo.campaign_records(signal.campaign_id)
        if isinstance(record, CommunityComment)
    }
    evidence_comments = [
        records[item.source_record_id]
        for item in signal.evidence
        if item.source_record_id in records
    ]
    ratings = [
        comment.source_rating
        for comment in evidence_comments
        if comment.source_rating is not None
    ]
    return {
        "evidence_count": len(signal.evidence),
        "affected_products": len(
            {
                comment.parent_product_id or comment.product_id
                for comment in evidence_comments
            }
        ),
        "average_rating": round(mean(ratings), 2) if ratings else None,
        "helpful_votes": sum(
            comment.helpful_vote or 0 for comment in evidence_comments
        ),
    }


def _dataset_path(dataset_id: str) -> Path:
    if dataset_id not in DATASET_CATALOG:
        raise KeyError(dataset_id)
    return SAMPLE_DIR / DATASET_CATALOG[dataset_id]["filename"]


def _read_dataset_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return list(csv.DictReader(StringIO(path.read_text(encoding="utf-8"))))


def _product_store_lookup() -> dict[str, str]:
    return {
        record.parent_asin: record.store or "Unknown"
        for record in repo.source_records.values()
        if isinstance(record, ProductContext)
    }


def _scope_options(
    rows: list[dict[str, str]],
    products: dict[str, str],
) -> list[dict[str, str | int]]:
    parent_counts = Counter(
        row.get("parent_asin") or row.get("asin") or "" for row in rows
    )
    brand_counts = Counter(
        products.get(row.get("parent_asin") or row.get("asin") or "", "Unknown")
        for row in rows
    )
    options: list[dict[str, str | int]] = [
        {"mode": "all", "label": "All products", "count": len(rows)},
        {
            "mode": "low_rating",
            "label": "Low-rating reviews only",
            "count": sum(1 for row in rows if (_as_float(row.get("rating")) or 0) <= 2),
        },
        {
            "mode": "verified_only",
            "label": "Verified purchases only",
            "count": sum(1 for row in rows if _as_bool(row.get("verified_purchase"))),
        },
    ]
    options.extend(
        {
            "mode": "brand",
            "label": f"Brand/store: {brand}",
            "value": brand,
            "count": count,
        }
        for brand, count in brand_counts.most_common(5)
        if brand != "Unknown"
    )
    options.extend(
        {
            "mode": "parent_asin",
            "label": f"Parent ASIN: {parent_asin}",
            "value": parent_asin,
            "count": count,
        }
        for parent_asin, count in parent_counts.most_common(5)
        if parent_asin
    )
    return options


def _preview_rows(rows: list[dict[str, str]]) -> list[DatasetPreviewItem]:
    buckets = {
        "positive": lambda rating: rating is not None and rating >= 4,
        "mixed": lambda rating: rating == 3,
        "negative": lambda rating: rating is not None and rating <= 2,
    }
    preview: list[DatasetPreviewItem] = []
    for bucket, predicate in buckets.items():
        row = next(
            (item for item in rows if predicate(_as_float(item.get("rating")))),
            None,
        )
        if row is None:
            continue
        preview.append(
            DatasetPreviewItem(
                bucket=bucket,
                rating=_as_float(row.get("rating")),
                title=row.get("title") or None,
                text=(row.get("text") or "")[:320],
                asin=row.get("asin") or None,
                parent_asin=row.get("parent_asin") or None,
                verified_purchase=_as_bool(row.get("verified_purchase")),
            )
        )
    return preview


def _rating_bucket(value: float | None) -> str:
    if value is None:
        return "0"
    return str(max(1, min(5, int(round(value)))))


def _as_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _as_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _timestamp_to_date(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        timestamp = float(value)
    except ValueError:
        return None
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000
    return datetime.fromtimestamp(timestamp, UTC)


def _strongest_message_angle(comments: list[CommunityComment]) -> str | None:
    counts = Counter()
    for comment in comments:
        text = comment.text.lower()
        for term, angle in POSITIVE_ANGLE_TERMS.items():
            if term in text and (comment.source_rating or 0) >= 4:
                counts[angle] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]
