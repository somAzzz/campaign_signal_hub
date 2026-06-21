export type SignalType =
  | "audience_tension"
  | "brand_fit"
  | "message_angle"
  | "risk_flag"
  | "content_opportunity"
  | "next_action";

export type SignalStatus = "pending" | "approved" | "dismissed";

export interface Campaign {
  id: string;
  client: string;
  brand: string;
  objective: string;
  target_audience: string;
  tone_constraints: string;
  required_platforms: string[];
  status: string;
  source_file_count: number;
  source_record_count: number;
  signal_count: number;
  approved_signal_count: number;
  risk_count: number;
}

export interface EvidenceItem {
  source_record_id?: string;
  quote: string;
  reason: string;
}

export interface CampaignSignal {
  id: string;
  campaign_id: string;
  signal_type: SignalType;
  title: string;
  summary: string;
  confidence: number;
  severity: string;
  recommended_action: string;
  evidence: EvidenceItem[];
  strength?: Record<string, number | string | null>;
  source_chunks?: string[];
  status: SignalStatus;
}

export interface SourceRecord {
  id: string;
  source_row_id?: string;
  record_type: string;
  text?: string;
  source_title?: string;
  source_rating?: number;
  product_id?: string;
  parent_product_id?: string;
  product_category?: string;
  source_timestamp?: string | number;
  verified_purchase?: boolean;
  helpful_vote?: number;
  name?: string;
  platform?: string;
  creator_id?: string;
  engagement_rate?: number;
  content_style?: string;
  sample_caption?: string;
  parent_asin?: string;
  asin?: string;
  title?: string;
  store?: string;
  average_rating?: number;
  rating_number?: number;
  price?: number;
  date?: string;
  content_id?: string;
  impressions?: number;
  ctr?: number;
  cpc?: number;
  conversions?: number;
  sentiment_negative?: number;
  comment_volume?: number;
}

export interface DatasetOption {
  id: string;
  label: string;
  filename: string;
  path: string;
  record_count: number;
  description: string;
}

export interface DatasetScopeOption {
  mode: string;
  label: string;
  value?: string;
  count: number;
}

export interface ExtractionPlan {
  chunk_comments: number;
  max_chunks: number;
  min_comments_for_chunking: number;
  max_comment_signals: number;
}

export interface DatasetProfile {
  dataset_id: string;
  row_count: number;
  unique_products: number;
  rating_distribution: Record<string, number>;
  verified_purchase_count: number;
  date_range: {
    start?: string | null;
    end?: string | null;
  };
  top_brands: Array<{ brand: string; count: number }>;
  top_parent_asins: Array<{ parent_asin: string; count: number }>;
  preview: Array<{
    bucket: string;
    rating?: number | null;
    title?: string | null;
    text: string;
    asin?: string | null;
    parent_asin?: string | null;
    verified_purchase?: boolean | null;
  }>;
  scopes: DatasetScopeOption[];
}

export interface TopicCluster {
  id: string;
  label: string;
  description: string;
  review_count: number;
  affected_products: number;
  average_rating?: number | null;
  helpful_votes: number;
  representative_quotes: string[];
}

export interface ProductHealth {
  parent_asin: string;
  asin?: string | null;
  title: string;
  store?: string | null;
  sample_review_count: number;
  sample_average_rating?: number | null;
  low_rating_count: number;
  verified_review_count: number;
  top_risks: string[];
  strongest_message_angle?: string | null;
  representative_quotes: string[];
}

export interface ExportSummary {
  campaign: {
    client: string;
    brand: string;
    objective: string;
  };
  summary: string;
  signals: Array<{
    type: SignalType;
    title: string;
    summary: string;
    recommended_action: string;
    evidence: EvidenceItem[];
  }>;
}
