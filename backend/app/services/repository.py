from app.models.campaign import Campaign
from app.models.signal import (
    CampaignSignal,
    LLMExtractionRun,
    QualityEvent,
    SignalStatus,
)
from app.models.source import SourceFile, SourceRecord


class InMemoryRepository:
    def __init__(self) -> None:
        self.campaigns: dict[str, Campaign] = {}
        self.source_files: dict[str, SourceFile] = {}
        self.source_records: dict[str, SourceRecord] = {}
        self.signals: dict[str, CampaignSignal] = {}
        self.quality_events: dict[str, QualityEvent] = {}
        self.llm_runs: dict[str, LLMExtractionRun] = {}

    def reset(self) -> None:
        self.__init__()

    def add_campaign(self, campaign: Campaign) -> Campaign:
        self.campaigns[campaign.id] = campaign
        return campaign

    def add_source_file(self, source_file: SourceFile) -> SourceFile:
        self.source_files[source_file.id] = source_file
        return source_file

    def add_source_records(self, records: list[SourceRecord]) -> list[SourceRecord]:
        for record in records:
            self.source_records[record.id] = record
        return records

    def add_signals(self, signals: list[CampaignSignal]) -> list[CampaignSignal]:
        for signal in signals:
            self.signals[signal.id] = signal
        return signals

    def clear_campaign_signals(self, campaign_id: str) -> None:
        self.signals = {
            signal_id: signal
            for signal_id, signal in self.signals.items()
            if signal.campaign_id != campaign_id
        }

    def clear_campaign_records_by_type(
        self, campaign_id: str, record_type: str
    ) -> None:
        self.source_records = {
            record_id: record
            for record_id, record in self.source_records.items()
            if not (
                record.campaign_id == campaign_id and record.record_type == record_type
            )
        }

    def add_quality_event(self, event: QualityEvent) -> QualityEvent:
        self.quality_events[event.id] = event
        return event

    def add_llm_run(self, run: LLMExtractionRun) -> LLMExtractionRun:
        self.llm_runs[run.id] = run
        return run

    def campaign_records(self, campaign_id: str) -> list[SourceRecord]:
        return [
            record
            for record in self.source_records.values()
            if record.campaign_id == campaign_id
        ]

    def campaign_files(self, campaign_id: str) -> list[SourceFile]:
        return [
            source_file
            for source_file in self.source_files.values()
            if source_file.campaign_id == campaign_id
        ]

    def campaign_signals(self, campaign_id: str) -> list[CampaignSignal]:
        return [
            signal
            for signal in self.signals.values()
            if signal.campaign_id == campaign_id
        ]

    def campaign_quality_events(self, campaign_id: str) -> list[QualityEvent]:
        return [
            event
            for event in self.quality_events.values()
            if event.campaign_id == campaign_id
        ]

    def campaign_llm_runs(self, campaign_id: str) -> list[LLMExtractionRun]:
        return [run for run in self.llm_runs.values() if run.campaign_id == campaign_id]

    def approved_signal_count(self, campaign_id: str) -> int:
        return sum(
            1
            for signal in self.campaign_signals(campaign_id)
            if signal.status == SignalStatus.approved
        )


repo = InMemoryRepository()
