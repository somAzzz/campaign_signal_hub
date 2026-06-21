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


DATASET_OVERRIDES = {
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
    return sorted(
        [_dataset_option_from_path(path) for path in SAMPLE_DIR.glob("*_comments.csv")],
        key=lambda dataset: (dataset.id.split("_")[0], dataset.record_count),
    )


def get_comment_dataset(dataset_id: str) -> DatasetOption:
    path = SAMPLE_DIR / f"{dataset_id}_comments.csv"
    if not path.exists():
        raise KeyError(dataset_id)
    return _dataset_option_from_path(path)


def load_comment_dataset(
    campaign_id: str,
    dataset_id: str,
    row_filter: Callable[[dict[str, str]], bool] | None = None,
) -> int:
    try:
        dataset = get_comment_dataset(dataset_id)
    except KeyError as exc:
        raise KeyError(dataset_id) from exc

    path = Path(dataset.path)
    repo.clear_campaign_records_by_type(campaign_id, "community_comment")
    content = path.read_text(encoding="utf-8")
    if row_filter is not None:
        content = _filter_csv_content(content, row_filter)

    records = parse_comments_csv(
        campaign_id=campaign_id,
        filename=dataset.filename,
        content=content,
    )
    return len(records)


def _dataset_option_from_path(path: Path) -> DatasetOption:
    dataset_id = path.name.removesuffix("_comments.csv")
    override = DATASET_OVERRIDES.get(dataset_id, {})
    record_count = _count_csv_records(path)
    return DatasetOption(
        id=dataset_id,
        label=override.get("label") or _label_from_dataset_id(dataset_id, record_count),
        filename=path.name,
        path=str(path),
        record_count=record_count,
        description=override.get("description") or "Auto-discovered sample CSV.",
    )


def _label_from_dataset_id(dataset_id: str, record_count: int) -> str:
    parts = dataset_id.split("_")
    family = parts[0].replace("-", " ").title()
    return f"{family} reviews / {record_count:,} rows"


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
