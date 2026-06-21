#!/usr/bin/env python3
"""Look up Amazon Reviews 2023 product metadata for sampled reviews."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.data_loader import (  # noqa: E402
    lookup_product_metadata,
    write_products_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True)
    parser.add_argument("--comments", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-scan-rows", type=int, default=None)
    return parser.parse_args()


def read_asins(comments_path: Path) -> set[str]:
    with comments_path.open(encoding="utf-8", newline="") as handle:
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
    asins = read_asins(Path(args.comments))
    products = lookup_product_metadata(
        category=args.category,
        asins=asins,
        max_scan_rows=args.max_scan_rows,
    )
    output = write_products_csv(products, Path(args.output))
    print(f"Wrote {len(products)} products to {output}")


if __name__ == "__main__":
    main()
