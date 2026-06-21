#!/usr/bin/env python3
"""List product ASINs and download more reviews for existing products."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.data_loader import (  # noqa: E402
    AmazonReviewSampleConfig,
    sample_hf_reviews_for_asins,
    write_comments_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="Grocery_and_Gourmet_Food")
    parser.add_argument("--products", default="data/samples/coffee_50_products.csv")
    parser.add_argument("--output", default="data/samples/coffee_5000_comments.csv")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--min-length", type=int, default=30)
    parser.add_argument("--max-length", type=int, default=1200)
    parser.add_argument("--max-scan-rows", type=int, default=2_000_000)
    parser.add_argument("--list-asins", action="store_true")
    return parser.parse_args()


def read_product_asins(products_path: Path) -> set[str]:
    with products_path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        asins: set[str] = set()
        for row in rows:
            if row.get("parent_asin"):
                asins.add(row["parent_asin"])
            if row.get("asin"):
                asins.add(row["asin"])
    return asins


def main() -> None:
    args = parse_args()
    products_path = Path(args.products)
    asins = read_product_asins(products_path)

    print(f"Loaded {len(asins)} product ASINs from {products_path}")

    if args.list_asins:
        for asin in sorted(asins):
            print(asin)
        return

    config = AmazonReviewSampleConfig(
        category=args.category,
        limit=args.limit,
        min_length=args.min_length,
        max_length=args.max_length,
        max_scan_rows=args.max_scan_rows,
    )
    rows = sample_hf_reviews_for_asins(config, asins)
    output = write_comments_csv(rows, Path(args.output))
    print(f"Wrote {len(rows)} reviews to {output}")


if __name__ == "__main__":
    main()
