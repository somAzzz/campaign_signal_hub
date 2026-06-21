import {
  AlertTriangle,
  BarChart3,
  Check,
  ChevronRight,
  Coffee,
  Database,
  Download,
  FileDown,
  FileSearch,
  Gauge,
  Layers3,
  LoaderCircle,
  MessageSquareText,
  PackageCheck,
  RefreshCcw,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  extractSignals,
  getDatasetProfile,
  getExport,
  getMarkdownExport,
  listProductHealth,
  listCampaigns,
  listDatasets,
  listRecords,
  listSignals,
  listTopics,
  updateSignal,
} from "./api";
import type {
  Campaign,
  CampaignSignal,
  DatasetProfile,
  DatasetOption,
  DatasetScopeOption,
  ExportSummary,
  ProductHealth,
  SourceRecord,
  SignalType,
  TopicCluster,
} from "./types";

const signalLabels: Record<SignalType, string> = {
  audience_tension: "Audience tension",
  brand_fit: "Brand fit",
  message_angle: "Message angle",
  risk_flag: "Risk flag",
  content_opportunity: "Content opportunity",
  next_action: "Next action",
};

const filters: Array<"all" | SignalType> = [
  "all",
  "risk_flag",
  "audience_tension",
  "message_angle",
  "brand_fit",
  "next_action",
];

type ActiveView = "dataset" | "signals" | "health" | "products" | "risks";

export function App() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [signals, setSignals] = useState<CampaignSignal[]>([]);
  const [records, setRecords] = useState<SourceRecord[]>([]);
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const [datasetProfile, setDatasetProfile] = useState<DatasetProfile | null>(null);
  const [topics, setTopics] = useState<TopicCluster[]>([]);
  const [productHealth, setProductHealth] = useState<ProductHealth[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("coffee_50");
  const [selectedScope, setSelectedScope] = useState<DatasetScopeOption | null>(null);
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>("dataset");
  const [filter, setFilter] = useState<"all" | SignalType>("all");
  const [exportSummary, setExportSummary] = useState<ExportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const campaign = campaigns[0];
  const selectedSignal =
    signals.find((signal) => signal.id === selectedSignalId) ?? signals[0];

  const evidenceRecords = useMemo(() => {
    const map = new Map(records.map((record) => [record.id, record]));
    const products = new Map(
      records
        .filter((record) => record.record_type === "product_context")
        .map((record) => [record.parent_asin, record]),
    );
    return selectedSignal?.evidence.map((item) => ({
      evidence: item,
      record: item.source_record_id ? map.get(item.source_record_id) : undefined,
      product: item.source_record_id
        ? products.get(map.get(item.source_record_id)?.parent_product_id)
        : undefined,
    })) ?? [];
  }, [records, selectedSignal]);

  const selectedEvidence =
    evidenceRecords.find(
      (item) => item.evidence.source_record_id === selectedEvidenceId,
    ) ??
    evidenceRecords[0];

  const visibleSignals = useMemo(() => {
    return signals.filter((signal) => filter === "all" || signal.signal_type === filter);
  }, [filter, signals]);

  const productCount = useMemo(() => {
    return records.filter((record) => record.record_type === "product_context").length;
  }, [records]);

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!campaign || !selectedDatasetId) return;
    void loadDatasetProfile(campaign.id, selectedDatasetId);
  }, [campaign?.id, selectedDatasetId]);

  useEffect(() => {
    setSelectedEvidenceId(selectedSignal?.evidence[0]?.source_record_id ?? null);
  }, [selectedSignal?.id]);

  async function load() {
    try {
      setLoading(true);
      const campaignList = await listCampaigns();
      setCampaigns(campaignList);
      if (campaignList[0]) {
        const [signalList, recordResult, summary, topicResult, productResult] =
          await Promise.all([
          listSignals(campaignList[0].id),
          listRecords(campaignList[0].id),
          getExport(campaignList[0].id),
          listTopics(campaignList[0].id),
          listProductHealth(campaignList[0].id),
        ]);
        const datasetResult = await listDatasets(campaignList[0].id);
        setSignals(signalList);
        setRecords(recordResult.records);
        setExportSummary(summary);
        setDatasets(datasetResult.datasets);
        setTopics(topicResult.topics);
        setProductHealth(productResult.products);
        setSelectedSignalId(signalList[0]?.id ?? null);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load campaign data.");
    } finally {
      setLoading(false);
    }
  }

  async function loadDatasetProfile(campaignId: string, datasetId: string) {
    try {
      const profile = await getDatasetProfile(campaignId, datasetId);
      setDatasetProfile(profile);
      setSelectedScope((current) => {
        if (current) {
          const match = profile.scopes.find(
            (scope) => scope.mode === current.mode && scope.value === current.value,
          );
          if (match) return match;
        }
        return profile.scopes[0] ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dataset profile.");
    }
  }

  async function rerunExtraction() {
    if (!campaign) return;
    try {
      setExtracting(true);
      const dataset = datasets.find((item) => item.id === selectedDatasetId);
      setNotice(
        `Running local sglang extraction on ${dataset?.label ?? "selected data"} / ${
          selectedScope?.label ?? "all products"
        }...`,
      );
      const signalList = await extractSignals(campaign.id, selectedDatasetId, {
        mode: selectedScope?.mode ?? "all",
        value: selectedScope?.value,
      });
      const [recordResult, summary, topicResult, productResult] = await Promise.all([
        listRecords(campaign.id),
        getExport(campaign.id),
        listTopics(campaign.id),
        listProductHealth(campaign.id),
      ]);
      setSignals(signalList);
      setRecords(recordResult.records);
      setExportSummary(summary);
      setTopics(topicResult.topics);
      setProductHealth(productResult.products);
      setSelectedSignalId(signalList[0]?.id ?? null);
      setNotice(
        `Extraction finished: ${signalList.length} signals generated from ${
          dataset?.label ?? selectedDatasetId
        }.`,
      );
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extraction failed.");
    } finally {
      setExtracting(false);
    }
  }

  async function downloadMarkdownExport() {
    if (!campaign) return;
    try {
      setExporting(true);
      const markdown = await getMarkdownExport(campaign.id);
      const blob = new Blob([markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${campaign.brand.toLowerCase().replace(/\s+/g, "-")}-brief.md`;
      link.click();
      URL.revokeObjectURL(url);
      setNotice("Markdown brief downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Markdown export failed.");
    } finally {
      setExporting(false);
    }
  }

  async function setStatus(signal: CampaignSignal, status: "approved" | "dismissed") {
    const updated = await updateSignal(signal.id, status);
    setSignals((current) =>
      current.map((item) => (item.id === updated.id ? updated : item)),
    );
    if (campaign) {
      setExportSummary(await getExport(campaign.id));
    }
  }

  async function downloadExport() {
    if (!campaign) return;
    try {
      setExporting(true);
      const summary = await getExport(campaign.id);
      setExportSummary(summary);
      const blob = new Blob([JSON.stringify(summary, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${campaign.brand.toLowerCase().replace(/\s+/g, "-")}-signals.json`;
      link.click();
      URL.revokeObjectURL(url);
      setNotice("Export downloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  if (loading) {
    return <main className="loading">Loading signal workspace...</main>;
  }

  if (error || !campaign) {
    return (
      <main className="loading error">
        <AlertTriangle aria-hidden="true" />
        <span>{error ?? "No campaign available."}</span>
      </main>
    );
  }

  const riskSignals = signals.filter((signal) => signal.signal_type === "risk_flag");
  const approved = signals.filter((signal) => signal.status === "approved").length;
  const reviewSignals = activeView === "risks" ? riskSignals : visibleSignals;

  function switchView(view: ActiveView) {
    setActiveView(view);
    if (view === "risks" && riskSignals[0]) {
      setSelectedSignalId(riskSignals[0].id);
      setFilter("risk_flag");
    }
  }

  return (
    <main className="app-shell">
      <aside className="rail">
        <div className="brand-mark">
          <Coffee aria-hidden="true" />
        </div>
        <button
          className={`icon-button ${activeView === "dataset" ? "active" : ""}`}
          title="Dataset scope"
          onClick={() => switchView("dataset")}
        >
          <Database aria-hidden="true" />
        </button>
        <button
          className={`icon-button ${activeView === "signals" ? "active" : ""}`}
          title="Signal review"
          onClick={() => switchView("signals")}
        >
          <FileSearch aria-hidden="true" />
        </button>
        <button
          className={`icon-button ${activeView === "health" ? "active" : ""}`}
          title="Campaign health"
          onClick={() => switchView("health")}
        >
          <Gauge aria-hidden="true" />
        </button>
        <button
          className={`icon-button ${activeView === "products" ? "active" : ""}`}
          title="Product health"
          onClick={() => switchView("products")}
        >
          <PackageCheck aria-hidden="true" />
        </button>
        <button
          className={`icon-button ${activeView === "risks" ? "active" : ""}`}
          title="Risk queue"
          onClick={() => switchView("risks")}
        >
          <ShieldAlert aria-hidden="true" />
        </button>
      </aside>

      <section className="workspace">
        <header className="campaign-header">
          <div>
            <p className="eyebrow">{campaign.client} / local sglang</p>
            <h1>{campaign.brand}</h1>
            <p className="objective">{campaign.objective}</p>
          </div>
          <div className="header-actions">
            <label className="dataset-picker">
              <span>Dataset</span>
              <select
                value={selectedDatasetId}
                onChange={(event) => setSelectedDatasetId(event.target.value)}
                disabled={extracting}
              >
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="dataset-picker scope-picker">
              <span>Scope</span>
              <select
                value={`${selectedScope?.mode ?? "all"}:${selectedScope?.value ?? ""}`}
                onChange={(event) => {
                  const scope = datasetProfile?.scopes.find(
                    (item) => `${item.mode}:${item.value ?? ""}` === event.target.value,
                  );
                  setSelectedScope(scope ?? null);
                }}
                disabled={extracting || !datasetProfile}
              >
                {(datasetProfile?.scopes ?? [{ mode: "all", label: "All products", count: 0 }]).map(
                  (scope) => (
                    <option
                      key={`${scope.mode}:${scope.value ?? ""}`}
                      value={`${scope.mode}:${scope.value ?? ""}`}
                    >
                      {scope.label} ({scope.count})
                    </option>
                  ),
                )}
              </select>
            </label>
            <button
              onClick={rerunExtraction}
              className="secondary-action"
              disabled={extracting}
            >
              {extracting ? (
                <LoaderCircle className="spin" aria-hidden="true" />
              ) : (
                <RefreshCcw aria-hidden="true" />
              )}
              {extracting ? "Extracting" : "Run extraction"}
            </button>
            <button
              className="primary-action"
              onClick={downloadExport}
              disabled={exporting}
            >
              {exporting ? (
                <LoaderCircle className="spin" aria-hidden="true" />
              ) : (
                <Download aria-hidden="true" />
              )}
              {exporting ? "Exporting" : "Export"}
            </button>
            <button
              className="secondary-action"
              onClick={downloadMarkdownExport}
              disabled={exporting}
              title="Download client-safe Markdown brief"
            >
              <FileDown aria-hidden="true" />
              Brief
            </button>
          </div>
        </header>

        {(notice || error) && (
          <div className={`status-banner ${error ? "error" : ""}`}>
            {error ? <AlertTriangle aria-hidden="true" /> : <Sparkles aria-hidden="true" />}
            <span>{error ?? notice}</span>
          </div>
        )}

        <section className="metrics-strip" aria-label="Campaign metrics">
          <Metric label="Records" value={campaign.source_record_count} />
          <Metric label="Products" value={productCount} />
          <Metric label="Signals" value={signals.length} />
          <Metric label="Risks" value={riskSignals.length} tone="risk" />
        </section>

        {activeView === "dataset" ? (
          <DatasetWorkspace
            profile={datasetProfile}
            topics={topics}
            selectedScope={selectedScope}
            onSelectScope={setSelectedScope}
          />
        ) : activeView === "health" ? (
          <CampaignHealth
            campaign={campaign}
            records={records}
            signals={signals}
            approved={approved}
            topics={topics}
          />
        ) : activeView === "products" ? (
          <ProductHealthView products={productHealth} />
        ) : (
          <section className="main-grid">
            <section className="signal-review" aria-label="Signal review">
            <div className="toolbar">
              <div>
                <p className="eyebrow">
                  {activeView === "risks" ? "Escalation queue" : "Review queue"}
                </p>
                <h2>{activeView === "risks" ? "Risk queue" : "Campaign signals"}</h2>
              </div>
              {activeView === "signals" ? (
                <div className="segmented" role="tablist" aria-label="Signal filters">
                  {filters.map((item) => (
                    <button
                      key={item}
                      className={filter === item ? "selected" : ""}
                      onClick={() => setFilter(item)}
                    >
                      {item === "all" ? "All" : signalLabels[item]}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>

            {activeView === "risks" ? (
              <RiskLanes
                signals={riskSignals}
                selectedSignalId={selectedSignal?.id}
                onSelect={setSelectedSignalId}
              />
            ) : (
              <div className="signal-list">
                {reviewSignals.map((signal) => (
                  <SignalCard
                    key={signal.id}
                    signal={signal}
                    selected={selectedSignal?.id === signal.id}
                    onSelect={setSelectedSignalId}
                  />
                ))}
              </div>
            )}
          </section>

          <aside className="detail-pane" aria-label="Signal details">
            {selectedSignal ? (
              <>
                <div className="pane-block">
                  <div className="detail-title">
                    <Sparkles aria-hidden="true" />
                    <div>
                      <p className="eyebrow">{signalLabels[selectedSignal.signal_type]}</p>
                      <h2>{selectedSignal.title}</h2>
                    </div>
                  </div>
                  <p className="detail-summary">{selectedSignal.recommended_action}</p>
                  <div className="approval-row">
                    <button onClick={() => setStatus(selectedSignal, "approved")}>
                      <Check aria-hidden="true" />
                      Approve
                    </button>
                    <button onClick={() => setStatus(selectedSignal, "dismissed")}>
                      <X aria-hidden="true" />
                      Dismiss
                    </button>
                  </div>
                </div>

                <div className="pane-block">
                  <div className="block-heading">
                    <MessageSquareText aria-hidden="true" />
                    <h2>Evidence</h2>
                  </div>
                  <div className="evidence-list">
                    {evidenceRecords.map(({ evidence, record, product }) => (
                      <button
                        key={`${selectedSignal.id}-${evidence.source_record_id ?? evidence.quote}`}
                        className={`evidence-item ${
                          selectedEvidence?.evidence.source_record_id ===
                          evidence.source_record_id
                            ? "selected"
                            : ""
                        }`}
                        onClick={() =>
                          setSelectedEvidenceId(evidence.source_record_id ?? null)
                        }
                      >
                        <blockquote>{evidence.quote}</blockquote>
                        <p>{evidence.reason}</p>
                        {product?.title ? (
                          <div className="product-source">
                            <strong>{product.title}</strong>
                            <span>{product.store}</span>
                          </div>
                        ) : null}
                        {record?.source_rating ? (
                          <span>Rating {record.source_rating} / 5</span>
                        ) : null}
                      </button>
                    ))}
                  </div>
                </div>

                {selectedEvidence ? (
                  <div className="pane-block source-record">
                    <div className="block-heading">
                      <FileSearch aria-hidden="true" />
                      <h2>Source record</h2>
                    </div>
                    <dl className="source-grid">
                      <div>
                        <dt>Row</dt>
                        <dd>{selectedEvidence.record?.source_row_id ?? "Unknown"}</dd>
                      </div>
                      <div>
                        <dt>ASIN</dt>
                        <dd>{selectedEvidence.record?.product_id ?? "Unknown"}</dd>
                      </div>
                      <div>
                        <dt>Parent</dt>
                        <dd>{selectedEvidence.record?.parent_product_id ?? "Unknown"}</dd>
                      </div>
                      <div>
                        <dt>Verified</dt>
                        <dd>
                          {selectedEvidence.record?.verified_purchase === undefined
                            ? "Unknown"
                            : selectedEvidence.record.verified_purchase
                              ? "Yes"
                              : "No"}
                        </dd>
                      </div>
                    </dl>
                    {selectedEvidence.product?.title ? (
                      <div className="source-product">
                        <span>Product</span>
                        <strong>{selectedEvidence.product.title}</strong>
                        <p>
                          {selectedEvidence.product.store}
                          {selectedEvidence.product.average_rating
                            ? ` / ${selectedEvidence.product.average_rating} avg rating`
                            : ""}
                        </p>
                      </div>
                    ) : null}
                    <div className="source-text">
                      <span>Full review</span>
                      <p>{selectedEvidence.record?.text ?? selectedEvidence.evidence.quote}</p>
                    </div>
                  </div>
                ) : null}

                <div className="pane-block export-panel">
                  <div className="block-heading">
                    <Download aria-hidden="true" />
                    <h2>Client-safe export</h2>
                  </div>
                  <p>{exportSummary?.summary}</p>
                  <span>{approved} approved signals included</span>
                </div>
              </>
            ) : null}
          </aside>
          </section>
        )}
      </section>
    </main>
  );
}

function Metric({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number;
  tone?: "default" | "risk";
}) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DatasetWorkspace({
  profile,
  topics,
  selectedScope,
  onSelectScope,
}: {
  profile: DatasetProfile | null;
  topics: TopicCluster[];
  selectedScope: DatasetScopeOption | null;
  onSelectScope: (scope: DatasetScopeOption) => void;
}) {
  if (!profile) {
    return <section className="health-panel workspace-panel">Loading dataset...</section>;
  }
  const totalRatings = Object.values(profile.rating_distribution).reduce(
    (total, count) => total + count,
    0,
  );

  return (
    <section className="dataset-grid" aria-label="Dataset scope">
      <div className="health-panel wide">
        <p className="eyebrow">Dataset profile</p>
        <h2>{profile.row_count.toLocaleString()} reviews ready for analysis</h2>
        <div className="coverage-grid">
          <HealthStat label="Rows" value={profile.row_count} />
          <HealthStat label="Products" value={profile.unique_products} />
          <HealthStat label="Verified" value={profile.verified_purchase_count} />
          <HealthStat label="Scopes" value={profile.scopes.length} />
        </div>
        <div className="rating-bars" aria-label="Rating distribution">
          {Object.entries(profile.rating_distribution).map(([rating, count]) => (
            <div key={rating}>
              <span>{rating} star</span>
              <meter value={count} max={totalRatings || 1} />
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="health-panel">
        <p className="eyebrow">Analysis scope</p>
        <h2>Choose the frame</h2>
        <div className="scope-list">
          {profile.scopes.map((scope) => (
            <button
              key={`${scope.mode}:${scope.value ?? ""}`}
              className={
                selectedScope?.mode === scope.mode && selectedScope?.value === scope.value
                  ? "selected"
                  : ""
              }
              onClick={() => onSelectScope(scope)}
            >
              <span>{scope.label}</span>
              <strong>{scope.count}</strong>
            </button>
          ))}
        </div>
      </div>

      <div className="health-panel">
        <p className="eyebrow">Top brands</p>
        <h2>Store concentration</h2>
        <div className="product-mini-list">
          {profile.top_brands.slice(0, 6).map((brand) => (
            <article key={brand.brand}>
              <strong>{brand.brand}</strong>
              <span>{brand.count} reviews in sample</span>
            </article>
          ))}
        </div>
      </div>

      <div className="health-panel wide">
        <p className="eyebrow">Review preview</p>
        <h2>Representative language</h2>
        <div className="preview-grid">
          {profile.preview.map((item) => (
            <article key={`${item.bucket}-${item.parent_asin}`}>
              <span>{item.bucket} / {item.rating ?? "n/a"} star</span>
              <strong>{item.title ?? "Untitled review"}</strong>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="health-panel wide">
        <p className="eyebrow">Current extraction topics</p>
        <h2>What the active records cluster around</h2>
        <TopicList topics={topics} />
      </div>
    </section>
  );
}

function CampaignHealth({
  campaign,
  records,
  signals,
  approved,
  topics,
}: {
  campaign: Campaign;
  records: SourceRecord[];
  signals: CampaignSignal[];
  approved: number;
  topics: TopicCluster[];
}) {
  const comments = records.filter((record) => record.record_type === "community_comment");
  const products = records.filter((record) => record.record_type === "product_context");
  const creators = records.filter((record) => record.record_type === "creator_profile");
  const performance = records.filter(
    (record) => record.record_type === "performance_metric",
  );
  const evidenceCount = signals.reduce(
    (total, signal) => total + signal.evidence.length,
    0,
  );

  return (
    <section className="health-grid" aria-label="Campaign health">
      <div className="health-panel wide">
        <p className="eyebrow">Data coverage</p>
        <h2>{campaign.brand} operating snapshot</h2>
        <div className="coverage-grid">
          <HealthStat label="Comments" value={comments.length} />
          <HealthStat label="Products" value={products.length} />
          <HealthStat label="Creators" value={creators.length} />
          <HealthStat label="Performance rows" value={performance.length} />
          <HealthStat label="Evidence links" value={evidenceCount} />
          <HealthStat label="Approved" value={approved} />
        </div>
      </div>

      <div className="health-panel">
        <p className="eyebrow">Signal mix</p>
        <h2>What the model produced</h2>
        <div className="mix-list">
          {Object.entries(
            signals.reduce<Record<string, number>>((counts, signal) => {
              counts[signal.signal_type] = (counts[signal.signal_type] ?? 0) + 1;
              return counts;
            }, {}),
          ).map(([type, count]) => (
            <div key={type}>
              <span>{signalLabels[type as SignalType] ?? type}</span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="health-panel wide">
        <p className="eyebrow">Topic strength</p>
        <h2>Repeated customer language</h2>
        <TopicList topics={topics} />
      </div>

      <div className="health-panel">
        <p className="eyebrow">Product context</p>
        <h2>Sample products</h2>
        <div className="product-mini-list">
          {products.slice(0, 5).map((product) => (
            <article key={product.id}>
              <strong>{product.title}</strong>
              <span>
                {product.store}
                {product.average_rating ? ` / ${product.average_rating} avg` : ""}
              </span>
            </article>
          ))}
        </div>
      </div>

      <div className="health-panel wide">
        <p className="eyebrow">Paid-media pulse</p>
        <h2>Performance rows</h2>
        <div className="performance-table">
          {performance.map((row) => (
            <article key={row.id}>
              <span>{row.content_id}</span>
              <strong>{row.ctr ? `${Math.round(row.ctr * 1000) / 10}% CTR` : "CTR n/a"}</strong>
              <span>
                {row.comment_volume ?? 0} comments / negative{" "}
                {row.sentiment_negative ?? 0}
              </span>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function HealthStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ProductHealthView({ products }: { products: ProductHealth[] }) {
  return (
    <section className="product-health-grid" aria-label="Product health">
      {products.map((product) => (
        <article key={product.parent_asin} className="product-health-card">
          <div>
            <p className="eyebrow">{product.store ?? "Unknown store"}</p>
            <h2>{product.title}</h2>
          </div>
          <dl className="product-metrics">
            <div>
              <dt>Reviews</dt>
              <dd>{product.sample_review_count}</dd>
            </div>
            <div>
              <dt>Avg</dt>
              <dd>{product.sample_average_rating ?? "n/a"}</dd>
            </div>
            <div>
              <dt>Low</dt>
              <dd>{product.low_rating_count}</dd>
            </div>
            <div>
              <dt>Verified</dt>
              <dd>{product.verified_review_count}</dd>
            </div>
          </dl>
          <div className="risk-tags">
            {(product.top_risks.length ? product.top_risks : ["No dominant risk"]).map(
              (risk) => (
                <span key={risk}>{risk}</span>
              ),
            )}
          </div>
          {product.strongest_message_angle ? (
            <p className="product-angle">
              <BarChart3 aria-hidden="true" />
              {product.strongest_message_angle}
            </p>
          ) : null}
          <blockquote>{product.representative_quotes[0] ?? "No quote available."}</blockquote>
        </article>
      ))}
    </section>
  );
}

function TopicList({ topics }: { topics: TopicCluster[] }) {
  if (!topics.length) {
    return <p className="muted-copy">Run extraction to populate topic clusters.</p>;
  }
  return (
    <div className="topic-list">
      {topics.slice(0, 6).map((topic) => (
        <article key={topic.id}>
          <Layers3 aria-hidden="true" />
          <div>
            <strong>{topic.label}</strong>
            <p>{topic.description}</p>
          </div>
          <span>
            {topic.review_count} reviews / {topic.affected_products} products
          </span>
        </article>
      ))}
    </div>
  );
}

function RiskLanes({
  signals,
  selectedSignalId,
  onSelect,
}: {
  signals: CampaignSignal[];
  selectedSignalId?: string;
  onSelect: (id: string) => void;
}) {
  const lanes = ["high", "medium", "low"];
  return (
    <div className="risk-lanes">
      {lanes.map((lane) => (
        <section key={lane} className={`risk-lane ${lane}`}>
          <p className="eyebrow">{lane} severity</p>
          {signals
            .filter((signal) => signal.severity === lane)
            .map((signal) => (
              <SignalCard
                key={signal.id}
                signal={signal}
                selected={selectedSignalId === signal.id}
                onSelect={onSelect}
              />
            ))}
        </section>
      ))}
    </div>
  );
}

function SignalCard({
  signal,
  selected,
  onSelect,
}: {
  signal: CampaignSignal;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <article
      className={`signal-card ${selected ? "selected" : ""}`}
      onClick={() => onSelect(signal.id)}
    >
      <div className="signal-topline">
        <span className={`type-pill ${signal.signal_type}`}>
          {signalLabels[signal.signal_type]}
        </span>
        <span className={`status-pill ${signal.status}`}>{signal.status}</span>
      </div>
      <h3>{signal.title}</h3>
      <p>{signal.summary}</p>
      <div className="signal-footer">
        <span>{Math.round(signal.confidence * 100)}% confidence</span>
        <span>
          {signal.strength?.supporting_review_count ?? signal.evidence.length} support
        </span>
        <span>{signal.source_chunks?.length ?? 0} chunks</span>
        <span>{signal.severity} severity</span>
        <ChevronRight aria-hidden="true" />
      </div>
    </article>
  );
}
