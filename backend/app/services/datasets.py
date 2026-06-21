import csv
from collections.abc import Callable
from io import StringIO
from pathlib import Path

from pydantic import BaseModel

from app.services.ingestion import parse_comments_csv
from app.services.repository import repo

SAMPLE_DIR = Path(__file__).resolve().parents[3] / "data" / "samples"


class DatasetOption(BaseModel):
    id: str
    label: str
    filename: str
    path: str
    record_count: int
    description: str


DATASET_CATALOG = {
    "coffee_50": {
        "label": "Coffee reviews / 50 rows",
        "filename": "coffee_50_comments.csv",
        "description": "Small fast sample for prompt and UI checks.",
    },
    "coffee_5000": {
        "label": "Coffee reviews / 5,000 rows",
        "filename": "coffee_5000_comments.csv",
        "description": "Expanded product-matched sample for richer analysis.",
    },
}


def list_comment_datasets() -> list[DatasetOption]:
    datasets: list[DatasetOption] = []
    for dataset_id, config in DATASET_CATALOG.items():
        path = SAMPLE_DIR / config["filename"]
        datasets.append(
            DatasetOption(
                id=dataset_id,
                label=config["label"],
                filename=config["filename"],
                path=str(path),
                record_count=_count_csv_records(path),
                description=config["description"],
            )
        )
    return datasets


def load_comment_dataset(
    campaign_id: str,
    dataset_id: str,
    row_filter: Callable[[dict[str, str]], bool] | None = None,
) -> int:
    if dataset_id not in DATASET_CATALOG:
        raise KeyError(dataset_id)

    config = DATASET_CATALOG[dataset_id]
    path = SAMPLE_DIR / config["filename"]
    repo.clear_campaign_records_by_type(campaign_id, "community_comment")
    content = path.read_text(encoding="utf-8")
    if row_filter is not None:
        content = _filter_csv_content(content, row_filter)

    records = parse_comments_csv(
        campaign_id=campaign_id,
        filename=config["filename"],
        content=content,
    )
    return len(records)


def _count_csv_records(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def _filter_csv_content(
    content: str, row_filter: Callable[[dict[str, str]], bool]
) -> str:
    reader = csv.DictReader(StringIO(content))
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames or [])
    writer.writeheader()
    for row in reader:
        if row_filter(row):
            writer.writerow(row)
    return output.getvalue()
