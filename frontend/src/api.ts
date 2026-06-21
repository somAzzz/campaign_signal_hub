import type {
  Campaign,
  CampaignSignal,
  DatasetProfile,
  DatasetOption,
  ExtractionPlan,
  ExportSummary,
  ProductHealth,
  SourceRecord,
  TopicCluster,
} from "./types";
import {
  demoCampaign,
  demoDatasetProfile,
  demoDatasets,
  demoExport,
  demoMarkdown,
  demoProductHealth,
  demoRecords,
  demoSignals,
  demoTopics,
} from "./demoData";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";
let demoSignalState = [...demoSignals];

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

function demoResponse<T>(value: T): Promise<T> {
  return Promise.resolve(structuredClone(value) as T);
}

export function listCampaigns() {
  if (DEMO_MODE) return demoResponse<Campaign[]>([demoCampaign]);
  return request<Campaign[]>("/api/campaigns");
}

export function listSignals(campaignId: string) {
  if (DEMO_MODE) return demoResponse<CampaignSignal[]>(demoSignalState);
  return request<CampaignSignal[]>(`/api/campaigns/${campaignId}/signals`);
}

export function updateSignal(signalId: string, status: "approved" | "dismissed") {
  if (DEMO_MODE) {
    demoSignalState = demoSignalState.map((signal) =>
      signal.id === signalId ? { ...signal, status } : signal,
    );
    const updated = demoSignalState.find((signal) => signal.id === signalId);
    return demoResponse<CampaignSignal>(updated ?? demoSignalState[0]);
  }
  return request<CampaignSignal>(`/api/signals/${signalId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function extractSignals(
  campaignId: string,
  datasetId?: string,
  scope?: { mode: string; value?: string; values?: string[] },
  analysisMode = "full",
  plan?: ExtractionPlan,
) {
  if (DEMO_MODE) return demoResponse<CampaignSignal[]>(demoSignalState);
  return request<CampaignSignal[]>(`/api/campaigns/${campaignId}/extract-signals`, {
    method: "POST",
    body: JSON.stringify({
      dataset_id: datasetId,
      scope,
      analysis_mode: analysisMode,
      plan,
    }),
  });
}

export function listRecords(campaignId: string, recordType?: string) {
  if (DEMO_MODE) {
    const records = recordType
      ? demoRecords.filter((record) => record.record_type === recordType)
      : demoRecords;
    return demoResponse<{ records: SourceRecord[] }>({ records });
  }
  const query = recordType ? `?record_type=${recordType}` : "";
  return request<{ records: SourceRecord[] }>(
    `/api/campaigns/${campaignId}/records${query}`,
  );
}

export function getExport(campaignId: string) {
  if (DEMO_MODE) return demoResponse<ExportSummary>(demoExport);
  return request<ExportSummary>(`/api/campaigns/${campaignId}/export`);
}

export function listDatasets(campaignId: string) {
  if (DEMO_MODE) {
    return demoResponse<{ datasets: DatasetOption[] }>({ datasets: demoDatasets });
  }
  return request<{ datasets: DatasetOption[] }>(`/api/campaigns/${campaignId}/datasets`);
}

export function getDatasetProfile(campaignId: string, datasetId: string) {
  if (DEMO_MODE) {
    return demoResponse<DatasetProfile>({
      ...demoDatasetProfile,
      dataset_id: datasetId,
      row_count:
        demoDatasets.find((dataset) => dataset.id === datasetId)?.record_count ??
        demoDatasetProfile.row_count,
    });
  }
  return request<DatasetProfile>(
    `/api/campaigns/${campaignId}/datasets/${datasetId}/profile`,
  );
}

export function listTopics(campaignId: string) {
  if (DEMO_MODE) return demoResponse<{ topics: TopicCluster[] }>({ topics: demoTopics });
  return request<{ topics: TopicCluster[] }>(`/api/campaigns/${campaignId}/topics`);
}

export function listProductHealth(campaignId: string) {
  if (DEMO_MODE) {
    return demoResponse<{ products: ProductHealth[] }>({
      products: demoProductHealth,
    });
  }
  return request<{ products: ProductHealth[] }>(
    `/api/campaigns/${campaignId}/product-health`,
  );
}

export async function getMarkdownExport(campaignId: string) {
  if (DEMO_MODE) return demoMarkdown;
  const response = await fetch(`${API_BASE}/api/campaigns/${campaignId}/export.md`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.text();
}
