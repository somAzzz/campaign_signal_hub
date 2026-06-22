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
type DemoSnapshot = {
  campaigns: Campaign[];
  signals: CampaignSignal[];
  records: SourceRecord[];
  export: ExportSummary;
  datasets: DatasetOption[];
  dataset_profiles: Record<string, DatasetProfile>;
  topics: TopicCluster[];
  product_health: ProductHealth[];
  markdown: string;
};

const fallbackDemoSnapshot: DemoSnapshot = {
  campaigns: [demoCampaign],
  signals: demoSignals,
  records: demoRecords,
  export: demoExport,
  datasets: demoDatasets,
  dataset_profiles: {
    [demoDatasetProfile.dataset_id]: demoDatasetProfile,
  },
  topics: demoTopics,
  product_health: demoProductHealth,
  markdown: demoMarkdown,
};

let demoSnapshotPromise: Promise<DemoSnapshot> | null = null;
let demoSignalState: CampaignSignal[] | null = null;

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

async function loadDemoSnapshot(): Promise<DemoSnapshot> {
  if (!demoSnapshotPromise) {
    demoSnapshotPromise = fetch(`${import.meta.env.BASE_URL}demo-snapshot.json`)
      .then((response) => {
        if (!response.ok) throw new Error("Static demo snapshot unavailable.");
        return response.json() as Promise<DemoSnapshot>;
      })
      .catch(() => fallbackDemoSnapshot);
  }
  return demoSnapshotPromise;
}

async function getDemoSignalState(): Promise<CampaignSignal[]> {
  if (!demoSignalState) {
    const snapshot = await loadDemoSnapshot();
    demoSignalState = structuredClone(snapshot.signals);
  }
  return demoSignalState;
}

export function listCampaigns() {
  if (DEMO_MODE) {
    return loadDemoSnapshot().then((snapshot) =>
      demoResponse<Campaign[]>(snapshot.campaigns),
    );
  }
  return request<Campaign[]>("/api/campaigns");
}

export function listSignals(campaignId: string) {
  if (DEMO_MODE) {
    return getDemoSignalState().then((signals) =>
      demoResponse<CampaignSignal[]>(signals),
    );
  }
  return request<CampaignSignal[]>(`/api/campaigns/${campaignId}/signals`);
}

export function updateSignal(signalId: string, status: "approved" | "dismissed") {
  if (DEMO_MODE) {
    return getDemoSignalState().then((signals) => {
      demoSignalState = signals.map((signal) =>
        signal.id === signalId ? { ...signal, status } : signal,
      );
      const updated = demoSignalState.find((signal) => signal.id === signalId);
      return demoResponse<CampaignSignal>(updated ?? demoSignalState[0]);
    });
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
  if (DEMO_MODE) {
    return getDemoSignalState().then((signals) =>
      demoResponse<CampaignSignal[]>(signals),
    );
  }
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
    return loadDemoSnapshot().then((snapshot) => {
      const records = recordType
        ? snapshot.records.filter((record) => record.record_type === recordType)
        : snapshot.records;
      return demoResponse<{ records: SourceRecord[] }>({ records });
    });
  }
  const query = recordType ? `?record_type=${recordType}` : "";
  return request<{ records: SourceRecord[] }>(
    `/api/campaigns/${campaignId}/records${query}`,
  );
}

export function getExport(campaignId: string) {
  if (DEMO_MODE) {
    return loadDemoSnapshot().then((snapshot) =>
      demoResponse<ExportSummary>(snapshot.export),
    );
  }
  return request<ExportSummary>(`/api/campaigns/${campaignId}/export`);
}

export function listDatasets(campaignId: string) {
  if (DEMO_MODE) {
    return loadDemoSnapshot().then((snapshot) =>
      demoResponse<{ datasets: DatasetOption[] }>({ datasets: snapshot.datasets }),
    );
  }
  return request<{ datasets: DatasetOption[] }>(`/api/campaigns/${campaignId}/datasets`);
}

export function getDatasetProfile(campaignId: string, datasetId: string) {
  if (DEMO_MODE) {
    return loadDemoSnapshot().then((snapshot) => {
      const profile = snapshot.dataset_profiles[datasetId] ?? demoDatasetProfile;
      return demoResponse<DatasetProfile>(profile);
    });
  }
  return request<DatasetProfile>(
    `/api/campaigns/${campaignId}/datasets/${datasetId}/profile`,
  );
}

export function listTopics(campaignId: string) {
  if (DEMO_MODE) {
    return loadDemoSnapshot().then((snapshot) =>
      demoResponse<{ topics: TopicCluster[] }>({ topics: snapshot.topics }),
    );
  }
  return request<{ topics: TopicCluster[] }>(`/api/campaigns/${campaignId}/topics`);
}

export function listProductHealth(campaignId: string) {
  if (DEMO_MODE) {
    return loadDemoSnapshot().then((snapshot) =>
      demoResponse<{ products: ProductHealth[] }>({
        products: snapshot.product_health,
      }),
    );
  }
  return request<{ products: ProductHealth[] }>(
    `/api/campaigns/${campaignId}/product-health`,
  );
}

export async function getMarkdownExport(campaignId: string) {
  if (DEMO_MODE) {
    const snapshot = await loadDemoSnapshot();
    return snapshot.markdown;
  }
  const response = await fetch(`${API_BASE}/api/campaigns/${campaignId}/export.md`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.text();
}
