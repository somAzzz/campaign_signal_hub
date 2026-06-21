# Data Implementation Plan

## 1. Purpose

This document defines the data plan for the Campaign Signal Hub MVP.

The project should not be a generic sentiment-analysis demo. It should show how
a campaign team can turn messy source material into validated, evidence-backed
campaign signals.

The MVP data strategy is:

- Use real Amazon review data for audience voice, objections, and risk signals.
- Use small synthetic fixtures for campaign briefs, creator shortlists, and
  performance snapshots.
- Preserve source provenance for every imported row.
- Keep the first dataset small enough for local development and portfolio demos.

## 2. Data Sources

### 2.1 Primary Source: Amazon Reviews 2023

Dataset:

- Name: `McAuley-Lab/Amazon-Reviews-2023`
- Provider: UCSD McAuley Lab
- Hugging Face: <https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023>
- Project site: <https://amazon-reviews-2023.github.io/>

This is the preferred real-world data source for the MVP. It contains Amazon
reviews grouped by category, plus product metadata.

Relevant review fields in the 2023 version:

```text
rating
title
text
images
asin
parent_asin
user_id
timestamp
helpful_vote
verified_purchase
```

The older Amazon review datasets often use fields such as `reviewText`,
`overall`, `reviewerID`, and `asin`. The ingestion layer should support the
2023 field names first, while keeping the mapping flexible enough to handle
older or Kaggle-derived CSVs later.

Recommended MVP category:

- `All_Beauty`

Good follow-up categories:

- `Amazon_Fashion`
- `Electronics`
- `Grocery_and_Gourmet_Food`
- `Health_and_Household`

Why `All_Beauty` first:

- It fits a creator and paid-social campaign scenario naturally.
- Reviews often contain objections about scent, texture, packaging, price,
  trust, claims, sensitivity, and effectiveness.
- Those objections map well to `audience_tension` and `risk_flag` outputs.

### 2.2 Secondary Source: Amazon Sentiment Subsets

Dataset example:

- Name: `yassiracharki/Amazon_Reviews_Binary_for_Sentiment_Analysis`
- Hugging Face:
  <https://huggingface.co/datasets/yassiracharki/Amazon_Reviews_Binary_for_Sentiment_Analysis>

This data is useful for fast sentiment-oriented tests, but it should not be the
main product demo source.

Use it for:

- Quick positive/negative classification tests.
- Prompt smoke tests.
- Baseline comparison against the LLM signal extractor.

Do not rely on it for:

- Product-specific evidence trails.
- Creator fit.
- Campaign context.
- Rich audience tension analysis.

### 2.3 Synthetic Fixture Data

Amazon reviews do not include campaign briefs, creator information, or campaign
performance metrics. The MVP should use synthetic fixtures for those inputs.

Synthetic files:

```text
data/fixtures/demo_campaign_brief.md
data/fixtures/creator_shortlist.csv
data/fixtures/performance_snapshot.csv
```

These fixtures should be realistic enough to exercise the full workflow, but
small and stable enough to commit to the repository.

## 3. Directory Layout

Recommended local data layout:

```text
data/
  raw/
    amazon_reviews/
  processed/
    demo_comments.csv
    demo_products.csv
  fixtures/
    demo_campaign_brief.md
    creator_shortlist.csv
    performance_snapshot.csv
  samples/
    beauty_500_comments.csv
    beauty_5k_comments.csv
    beauty_20k_comments.csv
```

Repository policy:

- Commit `data/fixtures/`.
- Commit small samples only if they are appropriate for the repository size.
- Do not commit large raw downloads.
- Keep `data/raw/` ignored by Git.
- Prefer reproducible scripts over manually edited sample files.

## 4. Demo Campaign

The first seeded campaign should be a clean beauty campaign.

Example:

```text
Client: GlowNest
Brand: Clean beauty hair and body care
Objective: Identify consumer objections before launching a paid creator campaign
Target audience: Ingredient-conscious shoppers, sensitive-skin buyers, value seekers
Tone constraints: Transparent, practical, not overclaiming
Platforms: TikTok, Instagram Reels, Amazon product detail pages
Campaign dates: Simulated 6-week launch window
```

This lets the product demonstrate realistic campaign questions:

- What is the audience worried about?
- Which product claims may trigger skepticism?
- What should creators address directly?
- Which objections should paid-media copy avoid or clarify?
- Which comments are strong enough to show as evidence?

## 5. Source Model Mapping

### 5.1 Amazon Review to CommunityComment

Map Amazon review fields into the internal `CommunityComment` model:

```text
rating              -> source_rating
title               -> source_title
text                -> text
asin                -> product_id
parent_asin         -> parent_product_id
user_id             -> author_id
timestamp           -> source_timestamp
helpful_vote        -> helpful_vote
verified_purchase   -> verified_purchase
```

Recommended `CommunityComment` fields:

```text
id
campaign_id
source_file_id
source_row_id
platform
author_id
text
source_title
source_rating
product_id
parent_product_id
product_category
source_timestamp
verified_purchase
helpful_vote
raw_payload
```

`raw_payload` should store the original row as JSON. This keeps the ingestion
pipeline flexible and makes later debugging easier.

### 5.2 Product Metadata to ContentPost or ProductContext

Amazon product metadata can be used as optional product context.

Relevant metadata fields:

```text
main_category
title
average_rating
rating_number
features
description
price
store
categories
details
parent_asin
```

For MVP, product metadata can be normalized into a lightweight context record:

```text
product_id
parent_product_id
title
brand_or_store
main_category
average_rating
rating_number
features
description
price
raw_payload
```

This does not need to be a first-class UI surface immediately. It can be passed
to the signal extractor as extra context when available.

## 6. Sampling Strategy

The project should not process the full Amazon dataset during MVP development.
Create reproducible samples.

Recommended sample sizes:

```text
beauty_500_comments.csv     local unit tests and parser checks
beauty_5k_comments.csv      seeded dashboard demo
beauty_20k_comments.csv     extraction stress test and quality evaluation
```

Sampling rules:

- Keep only rows with non-empty `text`.
- Prefer review text between 30 and 800 characters.
- Include a useful distribution of ratings:
  - 1-2 stars: negative objections and risk signals
  - 3 stars: mixed or ambiguous tension
  - 4-5 stars: positive language and message angles
- Prefer `verified_purchase = true` when possible.
- Avoid letting one product dominate the sample.
- Preserve `source_row_id`.
- Preserve the original rating and timestamp.

Initial ratio target:

```text
1-2 stars: 35%
3 stars:   15%
4-5 stars: 50%
```

This ratio is intentionally more negative than typical review distributions so
the MVP has enough material for risk and objection extraction.

## 7. Fixture Schemas

### 7.1 Campaign Brief

File:

```text
data/fixtures/demo_campaign_brief.md
```

Suggested sections:

```text
# Campaign Brief

## Client
## Brand
## Objective
## Target Audience
## Product Context
## Required Platforms
## Tone Constraints
## Claims To Avoid
## Campaign Questions
```

### 7.2 Creator Shortlist CSV

File:

```text
data/fixtures/creator_shortlist.csv
```

Columns:

```text
creator_id
name
platform
niche
audience_profile
avg_views
engagement_rate
content_style
brand_safety_notes
past_brand_categories
sample_caption
```

Use 8-12 synthetic creators for the MVP.

The creator data should support:

- `brand_fit`
- `message_angle`
- creator fit matrix
- creator-specific next actions

### 7.3 Performance Snapshot CSV

File:

```text
data/fixtures/performance_snapshot.csv
```

Columns:

```text
date
platform
campaign_phase
content_id
creator_id
impressions
clicks
ctr
spend
cpc
conversions
conversion_rate
sentiment_positive
sentiment_negative
comment_volume
```

The performance fixture should include patterns worth detecting:

- High CTR but high negative-comment rate.
- Strong engagement but weak conversion.
- One creator with unusually strong audience trust.
- One content angle that creates repeated objections.

## 8. Ingestion Workflow

The ingestion service should accept CSV and text files, then normalize them into
typed records.

MVP input types:

```text
BriefDocument
CreatorProfile
ContentPost
CommunityComment
PerformanceMetric
```

Ingestion requirements:

- Validate required columns.
- Normalize known aliases, such as `text`, `reviewText`, and `review_text`.
- Preserve row-level provenance.
- Store source file metadata.
- Store the raw row payload.
- Emit quality events for malformed rows.
- Do not silently drop records without logging why.

Recommended source provenance fields:

```text
source_file_id
source_filename
source_type
source_row_id
source_column_map
ingested_at
raw_payload
```

## 9. Signal Extraction Workflow

Signal extraction should operate on batches of comments plus campaign context.

Recommended batch size:

```text
20-50 comments per LLM call
```

Input context:

```text
campaign brief summary
comment batch
optional product metadata
optional performance context
```

Target signal types:

```text
audience_tension
brand_fit
message_angle
risk_flag
content_opportunity
next_action
```

Every extracted signal should include:

```text
signal_type
title
summary
confidence
severity
recommended_action
evidence
```

Every evidence item should include:

```text
source_record_id
quote
reason
```

The model should only use evidence from source rows included in the current
batch or explicitly provided campaign context.

## 10. Quality Checks

The quality layer should reject or flag signals when:

- Evidence is empty.
- Evidence quotes do not appear in the source text.
- A sentiment claim has no source text.
- A risk flag has no severity.
- A creator fit claim ignores the brief criteria.
- A recommendation duplicates another recommendation.
- The model returns malformed JSON.
- The signal is too generic to act on.

Example low-quality signal:

```text
Consumers care about quality.
```

Example acceptable signal:

```text
Risk: scent strength may polarize sensitive buyers.
Evidence: three verified-purchase reviews mention the fragrance being too strong
or lingering longer than expected.
Action: creators should describe scent strength plainly instead of calling it
"subtle" in all launch scripts.
```

## 11. MVP Execution Checklist

### Phase A: Data Foundation

- [ ] Add `data/` directory structure.
- [ ] Add `.gitignore` rules for raw and large processed data.
- [ ] Create `data/fixtures/demo_campaign_brief.md`.
- [ ] Create `data/fixtures/creator_shortlist.csv`.
- [ ] Create `data/fixtures/performance_snapshot.csv`.
- [ ] Document external data download instructions.

### Phase B: Sampling

- [x] Add script to load `McAuley-Lab/Amazon-Reviews-2023`.
- [x] Support category selection, starting with `All_Beauty`.
- [ ] Filter empty and very short review text.
- [ ] Apply rating-balanced sampling.
- [x] Write `beauty_50_comments.csv`.
- [ ] Write `beauty_500_comments.csv`.
- [ ] Write `beauty_5k_comments.csv`.
- [ ] Preserve original source fields in the sample.

### Phase C: Ingestion

- [ ] Define Pydantic models for all MVP input types.
- [ ] Implement brief text parsing.
- [ ] Implement creator CSV parsing.
- [ ] Implement comments CSV parsing.
- [ ] Implement performance CSV parsing.
- [ ] Persist source provenance for every row.
- [ ] Log malformed rows as quality events.

### Phase D: Signal Extraction

- [ ] Add OpenAI-compatible LLM client.
- [ ] Write structured extraction prompt.
- [ ] Validate model output with Pydantic.
- [ ] Add retry behavior for malformed JSON.
- [ ] Add evidence quote verification.
- [ ] Store validated campaign signals.

### Phase E: Review UI

- [ ] Seed the demo campaign.
- [ ] Show signal cards grouped by type.
- [ ] Add evidence drawer.
- [ ] Add risk queue.
- [ ] Add creator fit matrix.
- [ ] Add approve and dismiss states.
- [ ] Add export summary.

## 12. Portfolio Demo Narrative

The portfolio case study should frame the work as a campaign signal pipeline,
not as a classifier.

Example case study:

```text
Case Study: Clean Beauty Campaign Risk Scan

Input:
- Simulated clean beauty campaign brief
- 5,000 Amazon beauty reviews
- Synthetic creator shortlist
- Synthetic performance snapshot

Output:
- Validated campaign signal cards
- Audience tension summary
- Risk flags with source evidence
- Creator-brand fit recommendations
- Client-safe action summary
```

Example metrics to report:

```text
source records ingested
signals extracted
signals rejected by quality checks
average evidence count per signal
approved vs dismissed signals
```

These metrics show production-minded workflow design: ingestion, validation,
quality checks, evidence tracking, and review state.

## 13. Implementation Notes

Prefer reproducible data scripts over manually prepared CSVs.

The first implementation should optimize for:

- small local samples
- deterministic demo fixtures
- traceable evidence
- clear schema boundaries
- easy replacement of Amazon data with another review or social-comment source

Avoid building the first version around:

- full dataset downloads
- training a custom sentiment model
- unsupported creator inference from Amazon reviews
- dashboard visuals before source provenance works
