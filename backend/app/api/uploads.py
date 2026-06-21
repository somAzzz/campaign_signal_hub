from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services import ingestion
from app.services.repository import repo

router = APIRouter()


@router.post("/{campaign_id}/uploads")
async def upload_source_file(
    campaign_id: str,
    source_type: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")

    content = (await file.read()).decode("utf-8")
    filename = file.filename or "upload"

    if source_type == "brief":
        records = ingestion.parse_brief(campaign_id, filename, content)
    elif source_type == "community_comments":
        records = ingestion.parse_comments_csv(campaign_id, filename, content)
    elif source_type == "creator_profiles":
        records = ingestion.parse_creator_csv(campaign_id, filename, content)
    elif source_type == "product_context":
        records = ingestion.parse_products_csv(campaign_id, filename, content)
    elif source_type == "performance_metrics":
        records = ingestion.parse_performance_csv(campaign_id, filename, content)
    else:
        raise HTTPException(status_code=400, detail="Unsupported source_type")

    return {"source_type": source_type, "records_ingested": len(records)}
