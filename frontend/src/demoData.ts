import type {
  Campaign,
  CampaignSignal,
  DatasetOption,
  DatasetProfile,
  ExportSummary,
  ProductHealth,
  SourceRecord,
  TopicCluster,
} from "./types";

export const demoCampaign: Campaign = {
  id: "demo-campaign",
  client: "Portfolio demo",
  brand: "Coffee Launch Intelligence",
  objective:
    "Find product-level risks, audience tensions, and message angles from Amazon coffee reviews before campaign scaling.",
  target_audience: "Coffee shoppers comparing single-serve pods and flavored roasts.",
  tone_constraints:
    "Use evidence-backed recommendations and avoid unverifiable taste or origin claims.",
  required_platforms: ["Amazon", "Creator briefs", "Paid social"],
  status: "active",
  source_file_count: 3,
  source_record_count: 50000,
  signal_count: 6,
  approved_signal_count: 2,
  risk_count: 2,
};

export const demoDatasets: DatasetOption[] = [
  {
    id: "coffee_50",
    label: "Coffee 50 sample",
    filename: "coffee_50_comments.csv",
    path: "data/samples/coffee_50_comments.csv",
    record_count: 50,
    description: "Small coffee review sample for quick prompt checks.",
  },
  {
    id: "coffee_5000",
    label: "Coffee 5,000 sample",
    filename: "coffee_5000_comments.csv",
    path: "data/samples/coffee_5000_comments.csv",
    record_count: 5000,
    description: "Expanded product-matched review sample for richer analysis.",
  },
  {
    id: "coffee_50000",
    label: "Coffee 50,000 sample",
    filename: "coffee_50000_comments.csv",
    path: "data/samples/coffee_50000_comments.csv",
    record_count: 50000,
    description: "Large sample for chunked market analysis.",
  },
];

export const demoRecords: SourceRecord[] = [
  {
    id: "product-breakfast",
    record_type: "product_context",
    parent_asin: "B09XCRMYVV",
    asin: "B076WT9J3X",
    title: "Green Mountain Breakfast Blend Coffee K-Cups",
    store: "Green Mountain Coffee Roasters",
    average_rating: 4.4,
    rating_number: 2300,
    product_category: "Grocery_and_Gourmet_Food",
  },
  {
    id: "product-kona",
    record_type: "product_context",
    parent_asin: "B004QM0XLO",
    asin: "B004QM0XLO",
    title: "Aloha Island Kona Hawaiian Coffee Blend",
    store: "Aloha Island Coffee",
    average_rating: 4.0,
    rating_number: 329,
    product_category: "Grocery_and_Gourmet_Food",
  },
  {
    id: "product-spice",
    record_type: "product_context",
    parent_asin: "B083XDH8K8",
    asin: "B083XDH8K8",
    title: "Seasonal Pumpkin Spice Flavored Coffee Pods",
    store: "Seasonal Roast Co.",
    average_rating: 3.7,
    rating_number: 880,
    product_category: "Grocery_and_Gourmet_Food",
  },
  {
    id: "review-weak",
    source_row_id: "230",
    record_type: "community_comment",
    source_title: "If you like coffee, keep looking.",
    text:
      "The blend is listed as light roast but tasted like browned water. It hardly produced aroma and felt much weaker than expected.",
    source_rating: 2,
    product_id: "B076WT9J3X",
    parent_product_id: "B09XCRMYVV",
    verified_purchase: true,
    helpful_vote: 0,
  },
  {
    id: "review-kona",
    source_row_id: "1104",
    record_type: "community_comment",
    source_title: "Not Kona coffee",
    text:
      "This is not Kona coffee, it is a blend. The product page made me expect something more authentic and premium.",
    source_rating: 1,
    product_id: "B004QM0XLO",
    parent_product_id: "B004QM0XLO",
    verified_purchase: true,
    helpful_vote: 7,
  },
  {
    id: "review-spice",
    source_row_id: "812",
    record_type: "community_comment",
    source_title: "Pumpkin spice was faint",
    text:
      "You can smell the pumpkin spice faintly, but when brewed it tasted like watery pumpkin spice.",
    source_rating: 2,
    product_id: "B083XDH8K8",
    parent_product_id: "B083XDH8K8",
    verified_purchase: true,
    helpful_vote: 3,
  },
];

export const demoSignals: CampaignSignal[] = [
  {
    id: "signal-weak-flavor",
    campaign_id: demoCampaign.id,
    signal_type: "audience_tension",
    title: "Flavor strength expectations are higher than product delivery",
    summary:
      "Low-rating reviews repeatedly describe weak, watery, or low-aroma coffee. The campaign should avoid broad strength claims unless the product has review evidence for boldness.",
    confidence: 0.91,
    severity: "high",
    recommended_action:
      "Split messaging by roast strength and use conservative taste language for light or flavored products.",
    evidence: [
      {
        source_record_id: "review-weak",
        quote: "tasted like browned water",
        reason: "Shows a direct mismatch between roast positioning and sensory experience.",
      },
      {
        source_record_id: "review-spice",
        quote: "watery pumpkin spice",
        reason: "The flavored SKU creates disappointment when taste notes are too subtle.",
      },
    ],
    strength: {
      supporting_review_count: 1248,
      affected_products: 37,
      average_rating: 2.1,
      source_chunk_count: 8,
    },
    source_chunks: ["topic_weak_flavor", "rating_low"],
    status: "pending",
  },
  {
    id: "signal-origin-claim",
    campaign_id: demoCampaign.id,
    signal_type: "risk_flag",
    title: "Origin and blend claims create trust risk",
    summary:
      "Customers react strongly when a coffee blend appears to imply a premium origin. This can become a campaign risk if creator scripts overstate provenance.",
    confidence: 0.95,
    severity: "critical",
    recommended_action:
      "Audit product titles, landing page copy, and creator talking points for clear blend language.",
    evidence: [
      {
        source_record_id: "review-kona",
        quote: "This is not Kona coffee, it is a blend.",
        reason: "Direct evidence that perceived origin ambiguity triggers distrust.",
      },
    ],
    strength: {
      supporting_review_count: 431,
      affected_products: 9,
      average_rating: 1.8,
      source_chunk_count: 4,
    },
    source_chunks: ["topic_misleading_claims", "product_B004QM0XLO"],
    status: "approved",
  },
  {
    id: "signal-seasonal",
    campaign_id: demoCampaign.id,
    signal_type: "message_angle",
    title: "Seasonal flavors need subtlety framing",
    summary:
      "Pumpkin spice and cinnamon reviews show that shoppers want recognizable flavor but will reject language that promises a bold seasonal profile.",
    confidence: 0.86,
    severity: "medium",
    recommended_action:
      "Position seasonal SKUs as mild, cozy, and low-sweetness rather than intense flavor experiences.",
    evidence: [
      {
        source_record_id: "review-spice",
        quote: "smell the pumpkin spice faintly",
        reason: "Aroma exists, but the brewed taste does not meet flavor expectations.",
      },
    ],
    strength: {
      supporting_review_count: 762,
      affected_products: 14,
      average_rating: 2.7,
      source_chunk_count: 5,
    },
    source_chunks: ["topic_weak_flavor", "product_B083XDH8K8"],
    status: "pending",
  },
  {
    id: "signal-compatible",
    campaign_id: demoCampaign.id,
    signal_type: "content_opportunity",
    title: "Machine compatibility is a practical trust hook",
    summary:
      "Even in negative reviews, shoppers often confirm that pods work with their brewer. This can support low-friction trial messaging.",
    confidence: 0.78,
    severity: "low",
    recommended_action:
      "Use creator demos that show the product working in common single-serve machines before taste claims.",
    evidence: [
      {
        source_record_id: "review-weak",
        quote: "works fine in the keurig maker",
        reason: "Functional fit can still be a positive proof point.",
      },
    ],
    strength: {
      supporting_review_count: 980,
      affected_products: 42,
      average_rating: 3.6,
      source_chunk_count: 6,
    },
    source_chunks: ["topic_machine_fit"],
    status: "pending",
  },
];

export const demoDatasetProfile: DatasetProfile = {
  dataset_id: "coffee_50000",
  row_count: 50000,
  unique_products: 3820,
  rating_distribution: {
    "1": 8200,
    "2": 6100,
    "3": 7200,
    "4": 11800,
    "5": 16700,
  },
  verified_purchase_count: 42100,
  date_range: {
    start: "2018-01-04",
    end: "2023-09-12",
  },
  top_brands: [
    { brand: "Green Mountain Coffee Roasters", count: 5400 },
    { brand: "Starbucks", count: 4100 },
    { brand: "Aloha Island Coffee", count: 1150 },
  ],
  top_parent_asins: [
    { parent_asin: "B09XCRMYVV", count: 980 },
    { parent_asin: "B004QM0XLO", count: 329 },
    { parent_asin: "B083XDH8K8", count: 275 },
  ],
  product_options: [
    {
      parent_asin: "B09XCRMYVV",
      title: "Green Mountain Breakfast Blend Coffee K-Cups",
      store: "Green Mountain Coffee Roasters",
      count: 980,
    },
    {
      parent_asin: "B004QM0XLO",
      title: "Aloha Island Kona Hawaiian Coffee Blend",
      store: "Aloha Island Coffee",
      count: 329,
    },
    {
      parent_asin: "B083XDH8K8",
      title: "Seasonal Pumpkin Spice Flavored Coffee Pods",
      store: "Seasonal Roast Co.",
      count: 275,
    },
  ],
  preview: [
    {
      bucket: "risk",
      rating: 2,
      title: "If you like coffee, keep looking.",
      text:
        "The blend is listed as light roast but tasted like browned water.",
      asin: "B076WT9J3X",
      parent_asin: "B09XCRMYVV",
      verified_purchase: true,
    },
    {
      bucket: "claim",
      rating: 1,
      title: "Not Kona coffee",
      text: "This is not Kona coffee, it is a blend.",
      asin: "B004QM0XLO",
      parent_asin: "B004QM0XLO",
      verified_purchase: true,
    },
  ],
  scopes: [
    { mode: "all", label: "All products", count: 50000 },
    { mode: "low_rating", label: "Low-rating reviews only", count: 14300 },
    { mode: "verified_only", label: "Verified purchases only", count: 42100 },
    {
      mode: "brand",
      label: "Brand/store: Green Mountain Coffee Roasters",
      value: "Green Mountain Coffee Roasters",
      count: 5400,
    },
    {
      mode: "parent_asin",
      label: "Product: Green Mountain Breakfast Blend Coffee K-Cups",
      value: "B09XCRMYVV",
      count: 980,
    },
  ],
};

export const demoTopics: TopicCluster[] = [
  {
    id: "weak_flavor",
    label: "Weak flavor",
    description: "Reviews describe the coffee as watery, weak, thin, or low aroma.",
    review_count: 1248,
    affected_products: 37,
    average_rating: 2.1,
    helpful_votes: 830,
    representative_quotes: ["tasted like browned water", "watery pumpkin spice"],
  },
  {
    id: "misleading_claims",
    label: "Misleading claims",
    description: "Reviews say origin, flavor, or roast claims feel inaccurate.",
    review_count: 431,
    affected_products: 9,
    average_rating: 1.8,
    helpful_votes: 512,
    representative_quotes: ["This is not Kona coffee, it is a blend."],
  },
  {
    id: "machine_fit",
    label: "Machine fit",
    description: "Single-serve use and brewer compatibility shape satisfaction.",
    review_count: 980,
    affected_products: 42,
    average_rating: 3.6,
    helpful_votes: 290,
    representative_quotes: ["works fine in the keurig maker"],
  },
];

export const demoProductHealth: ProductHealth[] = [
  {
    parent_asin: "B09XCRMYVV",
    asin: "B076WT9J3X",
    title: "Green Mountain Breakfast Blend Coffee K-Cups",
    store: "Green Mountain Coffee Roasters",
    sample_review_count: 980,
    sample_average_rating: 3.2,
    low_rating_count: 214,
    verified_review_count: 902,
    top_risks: ["Weak flavor", "Light roast mismatch"],
    strongest_message_angle: "Single-serve convenience",
    representative_quotes: ["works fine in the keurig maker"],
  },
  {
    parent_asin: "B004QM0XLO",
    asin: "B004QM0XLO",
    title: "Aloha Island Kona Hawaiian Coffee Blend",
    store: "Aloha Island Coffee",
    sample_review_count: 329,
    sample_average_rating: 2.8,
    low_rating_count: 119,
    verified_review_count: 301,
    top_risks: ["Origin claim risk", "Blend transparency"],
    strongest_message_angle: "Smooth medium roast when blend is clear",
    representative_quotes: ["This is not Kona coffee, it is a blend."],
  },
];

export const demoExport: ExportSummary = {
  campaign: {
    client: demoCampaign.client,
    brand: demoCampaign.brand,
    objective: demoCampaign.objective,
  },
  summary:
    "Coffee Launch Intelligence has 4 active signals, including 1 critical claim risk and 2 message opportunities.",
  signals: demoSignals.map((signal) => ({
    type: signal.signal_type,
    title: signal.title,
    summary: signal.summary,
    recommended_action: signal.recommended_action,
    evidence: signal.evidence,
  })),
};

export const demoMarkdown = `# Coffee Launch Intelligence Campaign Signal Brief

Client: Portfolio demo
Objective: Find product-level risks, audience tensions, and message angles from Amazon coffee reviews before campaign scaling.

## Executive Summary

Coffee reviews show that campaign messaging should separate taste strength, origin transparency, and machine compatibility. The most important risk is overstating origin or blend claims.

## Recommended Next Actions

- Audit product copy and creator scripts for blend/origin clarity.
- Segment seasonal flavor messaging around subtle taste expectations.
- Use machine compatibility demos as a low-friction trust hook.
`;
