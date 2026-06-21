from fastapi import APIRouter, HTTPException

from app.models.campaign import Campaign, CampaignCreate, CampaignDetail
from app.models.signal import SignalType
from app.services.analysis import (
    campaign_product_health,
    campaign_topic_clusters,
    get_dataset_profile,
)
from app.services.datasets import list_comment_datasets
from app.services.repository import repo

router = APIRouter()


@router.post("", response_model=Campaign)
def create_campaign(payload: CampaignCreate) -> Campaign:
    return repo.add_campaign(Campaign(**payload.model_dump()))


@router.get("", response_model=list[CampaignDetail])
def list_campaigns() -> list[CampaignDetail]:
    return [_campaign_detail(campaign) for campaign in repo.campaigns.values()]


@router.get("/{campaign_id}", response_model=CampaignDetail)
def get_campaign(campaign_id: str) -> CampaignDetail:
    campaign = repo.campaigns.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_detail(campaign)


@router.get("/{campaign_id}/records")
def list_records(campaign_id: str, record_type: str | None = None) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    records = repo.campaign_records(campaign_id)
    if record_type:
        records = [record for record in records if record.record_type == record_type]
    return {"records": [record.model_dump() for record in records]}


@router.get("/{campaign_id}/datasets")
def list_datasets(campaign_id: str) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"datasets": [dataset.model_dump() for dataset in list_comment_datasets()]}


@router.get("/{campaign_id}/datasets/{dataset_id}/profile")
def get_dataset_preview(campaign_id: str, dataset_id: str) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        return get_dataset_profile(dataset_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc


@router.get("/{campaign_id}/topics")
def list_topic_clusters(campaign_id: str) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {
        "topics": [topic.model_dump() for topic in campaign_topic_clusters(campaign_id)]
    }


@router.get("/{campaign_id}/product-health")
def list_product_health(campaign_id: str) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {
        "products": [
            product.model_dump() for product in campaign_product_health(campaign_id)
        ]
    }


def _campaign_detail(campaign: Campaign) -> CampaignDetail:
    signals = repo.campaign_signals(campaign.id)
    return CampaignDetail(
        **campaign.model_dump(),
        source_file_count=len(repo.campaign_files(campaign.id)),
        source_record_count=len(repo.campaign_records(campaign.id)),
        signal_count=len(signals),
        approved_signal_count=repo.approved_signal_count(campaign.id),
        risk_count=sum(
            1 for signal in signals if signal.signal_type == SignalType.risk_flag
        ),
    )
