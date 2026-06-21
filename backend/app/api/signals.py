from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.signal import CampaignSignal, SignalUpdate
from app.services.analysis import DatasetScope, build_scope_filter
from app.services.datasets import load_comment_dataset
from app.services.persistence import save_snapshot
from app.services.repository import repo
from app.services.signal_extractor import extract_signals

router = APIRouter()


class ExtractionRequest(BaseModel):
    dataset_id: str | None = None
    scope: DatasetScope | None = None
    analysis_mode: str = "full"


@router.post(
    "/campaigns/{campaign_id}/extract-signals",
    response_model=list[CampaignSignal],
)
def run_extraction(
    campaign_id: str, payload: ExtractionRequest | None = None
) -> list[CampaignSignal]:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if payload and payload.dataset_id:
        try:
            load_comment_dataset(
                campaign_id,
                payload.dataset_id,
                row_filter=build_scope_filter(payload.scope),
            )
        except KeyError as exc:
            raise HTTPException(status_code=400, detail="Unknown dataset_id") from exc
    signals = extract_signals(
        campaign_id,
        dataset_id=payload.dataset_id if payload else None,
        scope=payload.scope.model_dump() if payload and payload.scope else None,
        analysis_mode=payload.analysis_mode if payload else "full",
    )
    save_snapshot()
    return signals


@router.get(
    "/campaigns/{campaign_id}/signals",
    response_model=list[CampaignSignal],
)
def list_signals(
    campaign_id: str, signal_type: str | None = None
) -> list[CampaignSignal]:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    signals = repo.campaign_signals(campaign_id)
    if signal_type:
        signals = [signal for signal in signals if signal.signal_type == signal_type]
    return signals


@router.patch("/signals/{signal_id}", response_model=CampaignSignal)
def update_signal(signal_id: str, payload: SignalUpdate) -> CampaignSignal:
    signal = repo.signals.get(signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    signal.status = payload.status
    repo.signals[signal.id] = signal
    save_snapshot()
    return signal


@router.get("/campaigns/{campaign_id}/quality-events")
def list_quality_events(campaign_id: str) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {
        "events": [
            event.model_dump() for event in repo.campaign_quality_events(campaign_id)
        ]
    }


@router.get("/campaigns/{campaign_id}/llm-outputs")
def list_llm_outputs(campaign_id: str) -> dict:
    if campaign_id not in repo.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {
        "runs": [
            run.model_dump(mode="json") for run in repo.campaign_llm_runs(campaign_id)
        ]
    }
