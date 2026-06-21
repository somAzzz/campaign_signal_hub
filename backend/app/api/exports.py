from fastapi import APIRouter, HTTPException, Response

from app.services.export_builder import build_campaign_export, build_markdown_export
from app.services.repository import repo

router = APIRouter()


@router.get("/{campaign_id}/export")
def export_campaign(campaign_id: str) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return build_campaign_export(campaign_id)


@router.get("/{campaign_id}/export.md")
def export_campaign_markdown(campaign_id: str) -> Response:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return Response(
        content=build_markdown_export(campaign_id),
        media_type="text/markdown; charset=utf-8",
    )
