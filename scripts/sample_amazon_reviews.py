#!/usr/bin/env python3
"""Create a small CSV sample from McAuley Lab Amazon Reviews 2023."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.data_loader import (  # noqa: E402
    AmazonReviewSampleConfig,
    sample_hf_amazon_reviews,
    write_comments_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="All_Beauty")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output", default="data/samples/beauty_50_comments.csv")
    parser.add_argument(
        "--keywords",
        default="",
        help="Comma-separated keyword filter applied to review title and text.",
    )
    parser.add_argument("--min-length", type=int, default=30)
    parser.add_argument("--max-length", type=int, default=800)
    parser.add_argument("--max-scan-rows", type=int, default=25_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AmazonReviewSampleConfig(
        category=args.category,
        limit=args.limit,
        keywords=tuple(
            keyword.strip() for keyword in args.keywords.split(",") if keyword.strip()
        ),
        min_length=args.min_length,
        max_length=args.max_length,
        max_scan_rows=args.max_scan_rows,
    )

    rows = sample_hf_amazon_reviews(config)
    output = write_comments_csv(rows, Path(args.output))

    print(f"Wrote {len(rows)} reviews to {output}")


if __name__ == "__main__":
    main()
