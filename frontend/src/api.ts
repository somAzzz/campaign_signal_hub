import type {
  Campaign,
  CampaignSignal,
  DatasetProfile,
  DatasetOption,
  ExportSummary,
  ProductHealth,
  SourceRecord,
  TopicCluster,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

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

export function listCampaigns() {
  return request<Campaign[]>("/api/campaigns");
}

export function listSignals(campaignId: string) {
  return request<CampaignSignal[]>(`/api/campaigns/${campaignId}/signals`);
}

export function updateSignal(signalId: string, status: "approved" | "dismissed") {
  return request<CampaignSignal>(`/api/signals/${signalId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function extractSignals(
  campaignId: string,
  datasetId?: string,
  scope?: { mode: string; value?: string },
  analysisMode = "full",
) {
  return request<CampaignSignal[]>(`/api/campaigns/${campaignId}/extract-signals`, {
    method: "POST",
    body: JSON.stringify({
      dataset_id: datasetId,
      scope,
      analysis_mode: analysisMode,
    }),
  });
}

export function listRecords(campaignId: string, recordType?: string) {
  const query = recordType ? `?record_type=${recordType}` : "";
  return request<{ records: SourceRecord[] }>(
    `/api/campaigns/${campaignId}/records${query}`,
  );
}

export function getExport(campaignId: string) {
  return request<ExportSummary>(`/api/campaigns/${campaignId}/export`);
}

export function listDatasets(campaignId: string) {
  return request<{ datasets: DatasetOption[] }>(`/api/campaigns/${campaignId}/datasets`);
}

export function getDatasetProfile(campaignId: string, datasetId: string) {
  return request<DatasetProfile>(
    `/api/campaigns/${campaignId}/datasets/${datasetId}/profile`,
  );
}

export function listTopics(campaignId: string) {
  return request<{ topics: TopicCluster[] }>(`/api/campaigns/${campaignId}/topics`);
}

export function listProductHealth(campaignId: string) {
  return request<{ products: ProductHealth[] }>(
    `/api/campaigns/${campaignId}/product-health`,
  );
}

export async function getMarkdownExport(campaignId: string) {
  const response = await fetch(`${API_BASE}/api/campaigns/${campaignId}/export.md`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.text();
}
