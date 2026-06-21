from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from app.services.ingestion import parse_comments_csv

AMAZON_REVIEWS_REPO = "McAuley-Lab/Amazon-Reviews-2023"
HF_REPO_TYPE = "dataset"
COMMENT_FIELDS = [
    "rating",
    "title",
    "text",
    "asin",
    "parent_asin",
    "user_id",
    "timestamp",
    "helpful_vote",
    "verified_purchase",
    "product_category",
    "source_row_id",
    "source_dataset",
    "source_path",
]
PRODUCT_FIELDS = [
    "parent_asin",
    "asin",
    "title",
    "store",
    "main_category",
    "average_rating",
    "rating_number",
    "price",
    "categories",
    "features",
    "description",
    "source_dataset",
    "source_path",
]


@dataclass(frozen=True)
class AmazonReviewSampleConfig:
    category: str = "All_Beauty"
    limit: int = 50
    keywords: tuple[str, ...] = ()
    min_length: int = 30
    max_length: int = 800
    max_scan_rows: int = 25_000
    negative_ratio: float = 0.35
    mixed_ratio: float = 0.15
    positive_ratio: float = 0.50

    @property
    def hf_path(self) -> str:
        return f"raw/review_categories/{self.category}.jsonl"

    @property
    def hf_meta_path(self) -> str:
        return f"raw/meta_categories/meta_{self.category}.jsonl"


def hf_jsonl_url(path: str) -> str:
    try:
        from huggingface_hub import hf_hub_url
    except ImportError as exc:
        raise RuntimeError(
            "Install data dependencies first: uv run --extra data ..."
        ) from exc

    return hf_hub_url(AMAZON_REVIEWS_REPO, path, repo_type=HF_REPO_TYPE)


def iter_hf_amazon_reviews(config: AmazonReviewSampleConfig):
    url = hf_jsonl_url(config.hf_path)
    request = Request(url, headers={"User-Agent": "campaign-signal-hub/0.1"})

    with urlopen(request, timeout=60) as response:
        for line_number, raw_line in enumerate(response, start=1):
            if line_number > config.max_scan_rows:
                break
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            row["source_row_id"] = str(line_number)
            row["source_dataset"] = AMAZON_REVIEWS_REPO
            row["source_path"] = config.hf_path
            row["product_category"] = config.category
            yield row


def iter_hf_amazon_product_metadata(config: AmazonReviewSampleConfig):
    url = hf_jsonl_url(config.hf_meta_path)
    request = Request(url, headers={"User-Agent": "campaign-signal-hub/0.1"})

    with urlopen(request, timeout=60) as response:
        for line_number, raw_line in enumerate(response, start=1):
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            row["source_row_id"] = str(line_number)
            row["source_dataset"] = AMAZON_REVIEWS_REPO
            row["source_path"] = config.hf_meta_path
            yield row


def sample_hf_amazon_reviews(config: AmazonReviewSampleConfig) -> list[dict]:
    buckets: dict[str, list[dict]] = {"negative": [], "mixed": [], "positive": []}
    targets = _bucket_targets(config)
    seen_parent_asins: set[str] = set()

    for row in iter_hf_amazon_reviews(config):
        normalized = normalize_amazon_review(row)
        if not _passes_text_filter(normalized, config):
            continue
        if not _passes_keyword_filter(normalized, config):
            continue

        bucket = rating_bucket(float(normalized["rating"]))
        if len(buckets[bucket]) >= targets[bucket]:
            continue

        parent_asin = normalized.get("parent_asin") or normalized.get("asin")
        dedupe_key = f"{bucket}:{parent_asin}"
        if dedupe_key in seen_parent_asins:
            continue

        seen_parent_asins.add(dedupe_key)
        buckets[bucket].append(normalized)

        if sum(len(items) for items in buckets.values()) >= config.limit:
            break

    return [
        row for bucket in ("negative", "mixed", "positive") for row in buckets[bucket]
    ]


def sample_hf_reviews_for_asins(
    config: AmazonReviewSampleConfig,
    asins: set[str],
) -> list[dict]:
    wanted = {asin for asin in asins if asin}
    rows: list[dict] = []

    for row in iter_hf_amazon_reviews(config):
        normalized = normalize_amazon_review(row)
        if not _passes_text_filter(normalized, config):
            continue
        if not _matches_asin(normalized, wanted):
            continue

        rows.append(normalized)
        if len(rows) >= config.limit:
            break

    return rows


def write_comments_csv(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=COMMENT_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def lookup_product_metadata(
    category: str, asins: set[str], max_scan_rows: int | None = None
) -> list[dict]:
    config = AmazonReviewSampleConfig(category=category)
    wanted = {asin for asin in asins if asin}
    products: dict[str, dict] = {}

    for index, row in enumerate(iter_hf_amazon_product_metadata(config), start=1):
        if max_scan_rows is not None and index > max_scan_rows:
            break

        asin = str(row.get("asin") or "")
        parent_asin = str(row.get("parent_asin") or "")
        matched_key = ""
        if parent_asin in wanted:
            matched_key = parent_asin
        elif asin in wanted:
            matched_key = asin
        if not matched_key:
            continue

        products[matched_key] = normalize_product_metadata(row)
        if wanted.issubset(products.keys()):
            break

    return [products[key] for key in sorted(products)]


def write_products_csv(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=PRODUCT_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def load_hf_sample_into_campaign(
    campaign_id: str,
    config: AmazonReviewSampleConfig,
    output_path: Path | None = None,
):
    rows = sample_hf_amazon_reviews(config)
    if output_path is not None:
        write_comments_csv(rows, output_path)

    csv_buffer = _rows_to_csv(rows)
    filename = output_path.name if output_path else f"{config.category}_hf_sample.csv"
    return parse_comments_csv(campaign_id, filename, csv_buffer)


def normalize_amazon_review(row: dict) -> dict:
    return {
        "rating": row.get("rating"),
        "title": row.get("title") or "",
        "text": row.get("text") or "",
        "asin": row.get("asin") or "",
        "parent_asin": row.get("parent_asin") or row.get("asin") or "",
        "user_id": row.get("user_id") or "",
        "timestamp": row.get("timestamp") or "",
        "helpful_vote": row.get("helpful_vote") or 0,
        "verified_purchase": row.get("verified_purchase"),
        "product_category": row.get("product_category") or "",
        "source_row_id": row.get("source_row_id") or "",
        "source_dataset": row.get("source_dataset") or AMAZON_REVIEWS_REPO,
        "source_path": row.get("source_path") or "",
    }


def normalize_product_metadata(row: dict) -> dict:
    return {
        "parent_asin": row.get("parent_asin") or row.get("asin") or "",
        "asin": row.get("asin") or "",
        "title": row.get("title") or "",
        "store": row.get("store") or "",
        "main_category": row.get("main_category") or "",
        "average_rating": row.get("average_rating") or "",
        "rating_number": row.get("rating_number") or "",
        "price": row.get("price") or "",
        "categories": json.dumps(row.get("categories") or [], ensure_ascii=False),
        "features": json.dumps(row.get("features") or [], ensure_ascii=False),
        "description": json.dumps(row.get("description") or [], ensure_ascii=False),
        "source_dataset": row.get("source_dataset") or AMAZON_REVIEWS_REPO,
        "source_path": row.get("source_path") or "",
    }


def rating_bucket(rating: float) -> str:
    if rating <= 2:
        return "negative"
    if rating == 3:
        return "mixed"
    return "positive"


def _bucket_targets(config: AmazonReviewSampleConfig) -> dict[str, int]:
    positive = int(config.limit * config.positive_ratio)
    negative = int(config.limit * config.negative_ratio)
    mixed = max(0, config.limit - positive - negative)
    return {
        "negative": max(1, negative),
        "mixed": max(1, mixed),
        "positive": max(1, positive),
    }


def _passes_text_filter(row: dict, config: AmazonReviewSampleConfig) -> bool:
    text = str(row.get("text") or "").strip()
    if not config.min_length <= len(text) <= config.max_length:
        return False
    try:
        float(row.get("rating") or 0)
    except (TypeError, ValueError):
        return False
    return True


def _passes_keyword_filter(row: dict, config: AmazonReviewSampleConfig) -> bool:
    if not config.keywords:
        return True

    haystack = " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("text") or ""),
            str(row.get("product_category") or ""),
        ]
    ).lower()
    return any(keyword.lower() in haystack for keyword in config.keywords)


def _matches_asin(row: dict, asins: set[str]) -> bool:
    return bool({str(row.get("asin") or ""), str(row.get("parent_asin") or "")} & asins)


def _rows_to_csv(rows: list[dict]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COMMENT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
