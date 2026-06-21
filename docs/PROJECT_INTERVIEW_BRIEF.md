# Campaign Signal Hub Interview Brief

## 1. Project Positioning

Campaign Signal Hub is a marketing analysis workspace that turns large-scale
Amazon review data into campaign-ready business signals. The project is designed
for a marketing analyst, product manager, or growth team that wants to understand
what customers are actually saying before writing creator briefs, landing page
copy, or paid-social messaging.

The core problem is that raw reviews are too noisy to use directly. A 5,000 or
50,000 comment dataset contains useful market evidence, but the value is hidden
inside repeated complaints, scattered product-level risks, rating differences,
and isolated quotes. Campaign Signal Hub converts that raw evidence into a
structured workflow:

1. Load product review data.
2. Select the dataset, product scope, and analysis depth.
3. Run chunked LLM extraction.
4. Review signals, risks, product health, and evidence.
5. Export a client-safe campaign brief.

## 2. What The Frontend Page Includes

The frontend is a single-page marketing intelligence dashboard. It is not a
generic data table; it is organized around the decisions a campaign team needs
to make.

### Dataset Workspace

The Dataset workspace is the entry point for analysis. It shows:

- Total review rows loaded.
- Number of products represented in the dataset.
- Verified purchase count.
- Rating distribution.
- Available analysis scopes.
- Product-level filtering by product name.
- Extraction plan controls.
- Preview records and topic clusters.

This page answers: "What data am I about to analyze, and how should I frame the
analysis?"

### Dataset Selection

The user can switch between available samples such as:

- `coffee_50`
- `coffee_5000`
- `coffee_50000`

The backend automatically discovers sample files under `data/samples`, so newly
downloaded datasets can appear in the frontend without hardcoding every file.

### Product Filtering

The user can filter analysis by product name. This supports:

- Selecting one product.
- Selecting multiple products.
- Selecting all products.
- Deselecting all products.

When products are selected, the extraction request sends a `parent_asins` scope
to the backend. This means the backend analyzes only the selected products'
comments rather than merely filtering the UI after analysis.

This is important for product managers because many review problems are not
category-wide. A risk might belong to one flavored SKU, one roast level, or one
brand claim.

### Extraction Plan Controls

The page exposes analysis-depth parameters:

- `Reviews/chunk`: how many representative reviews are sent to the LLM in each
  chunk.
- `Max chunks`: the maximum number of chunks analyzed in one run.
- `Chunk threshold`: when the backend switches from one balanced sample to
  multi-chunk analysis.
- `Max signals`: the maximum number of merged business signals returned.

Three presets are provided:

- `Balanced`: default coverage and speed.
- `Broad`: more chunks and more final signals for wider market coverage.
- `Deep`: larger chunks with fewer final signals for more focused synthesis.

The user can also choose custom parameters. These values are sent to the backend
and recorded in the LLM output logs for reproducibility.

### Signal Review

The Signal Review view presents extracted marketing insights as reviewable
business objects. Each signal includes:

- Signal type, such as audience tension, risk flag, message angle, brand fit, or
  next action.
- Title and summary.
- Confidence and severity.
- Recommended action.
- Evidence quotes.
- Source review and product context.
- Approval or dismissal controls.

This turns LLM output into an analyst workflow rather than a one-off chat
response.

### Evidence Panel

The right-side evidence panel lets the user inspect why a signal exists. It
connects a signal back to:

- Original review quote.
- Full source review text.
- Rating.
- ASIN and parent ASIN.
- Product name and store.
- Verification status when available.

This is critical because marketing recommendations must be traceable. The
project treats evidence as a first-class object, not just supporting text.

### Campaign Health

Campaign Health summarizes the current analysis state:

- Total signals.
- Approved signals.
- Risk count.
- Topic concentration.
- Dataset and product coverage.

This gives the analyst a quick sense of whether the campaign is ready for export
or still needs review.

### Product Health

Product Health shows product-level performance and risk:

- Product title and store.
- Review count.
- Average rating.
- Low-rating count.
- Verified review count.
- Top product risks.
- Strongest message angle.
- Representative quote.

This view is especially useful for product managers because it separates product
diagnosis from campaign-level synthesis.

### Risk Queue

The Risk Queue isolates risk signals so that high-severity issues can be
reviewed first. It helps teams avoid scaling campaigns around claims or products
that already show customer distrust.

### Export

The frontend supports:

- JSON export for structured downstream use.
- Markdown brief export for client-safe presentation.

The export includes approved signals, recommended actions, and sanitized
evidence.

## 3. What Goal The Project Achieves

The project turns unstructured review data into a repeatable marketing analysis
pipeline.

Before this system, the workflow would usually be manual:

- Search reviews by keyword.
- Copy quotes into notes.
- Ask an LLM for a summary.
- Manually decide which risks matter.
- Write a brief without strong traceability.

Campaign Signal Hub improves this by adding:

- Dataset loading.
- Product and scope selection.
- Chunked LLM analysis.
- Signal deduplication.
- Evidence linking.
- Product health summaries.
- Logged LLM inputs and outputs.
- Exportable campaign briefs.

The business output is not "sentiment analysis" in a narrow classification
sense. The output is campaign intelligence:

- What should we say?
- What should we avoid saying?
- Which products are risky?
- Which claims need proof?
- Which objections should shape content?
- Which positive hooks can creators use?

## 4. How To Understand The Existing Data

The current project uses Amazon coffee review samples derived from the McAuley
Lab Amazon Reviews 2023 dataset.

Each comment row contains fields such as:

- `rating`
- `title`
- `text`
- `asin`
- `parent_asin`
- `user_id`
- `timestamp`
- `helpful_vote`
- `verified_purchase`
- `product_category`

The product metadata file maps `asin` or `parent_asin` to product context:

- Product title.
- Store or brand.
- Category path.
- Average rating.
- Rating count.
- Price.
- Product features and description.

The most important identifiers are:

- `asin`: the specific Amazon item identifier.
- `parent_asin`: the parent product family identifier.

The project uses `parent_asin` as the main product-level grouping key because
reviews often need to be analyzed at the product family level rather than at one
listing variation.

## 5. How The Analysis Pipeline Works

### Step 1: Dataset Discovery

The backend scans sample files and exposes available datasets to the frontend.
This lets the user download new samples and then select them in the UI.

### Step 2: Data Loading

When the user chooses a dataset, comments are loaded into internal source record
models. Product metadata is loaded separately and joined by `parent_asin`.

### Step 3: Scope Selection

The user can analyze:

- All products.
- Low-rating reviews.
- Verified purchases.
- One brand or store.
- One product.
- Multiple selected products.

This scope is applied before extraction, so the LLM only sees the relevant
records.

### Step 4: Chunk Planning

For large datasets, the backend does not send all comments into one prompt.
Instead, it creates business-relevant chunks:

- Topic chunks, such as weak flavor, bitterness, freshness, machine fit, and
  price/value.
- Product-risk chunks for products with concentrated low-rating pressure.
- Low-rating objection chunks.
- Positive message-hook chunks.

Each chunk sends representative reviews to the LLM while retaining metadata
about the broader sample.

### Step 5: LLM Extraction

The LLM receives structured prompts asking it to produce business signals, not
generic summaries. The expected output includes:

- Signal type.
- Title.
- Summary.
- Severity.
- Confidence.
- Recommended action.
- Evidence quotes.

The project supports local LLM inference through sglang and can also be
configured for OpenAI-compatible cloud APIs.

### Step 6: Signal Merge And Strength Scoring

Chunk-level outputs are merged and deduplicated. The backend attaches strength
metadata such as:

- Supporting review count.
- Affected product count.
- Average rating.
- Helpful votes.
- Evidence count.
- Source chunk count.

This is what makes a 50,000-review run produce more defensible business results
than a small sample.

### Step 7: Logging And Traceability

Every LLM run is written to `data/processed/llm_outputs/`. The filename starts
with execution time, followed by dataset id and short identifiers.

The log records:

- Start and end time.
- Duration.
- Dataset id.
- Scope.
- Source files.
- Selected source record ids.
- Extraction plan parameters.
- Prompt.
- Raw model output.
- Parsed signal count.
- Error state when applicable.

This makes the analysis reproducible and auditable.

## 6. How LLMs Are Used

The LLM is not used as a black-box dashboard. It is used in a controlled
extraction role.

The backend decides:

- Which comments are selected.
- How comments are chunked.
- Which metadata is sent.
- What output schema is expected.
- How results are validated.
- How similar results are merged.

The LLM contributes:

- Language understanding.
- Synthesis of customer objections.
- Business-friendly signal titles.
- Recommended marketing actions.
- Evidence-based reasoning.

This division is important. The deterministic system controls data selection and
traceability; the LLM handles interpretation and synthesis.

## 7. How I Would Explain The Project To An Interviewer

I built Campaign Signal Hub as a marketing intelligence system that uses real
customer reviews to support campaign strategy. The project starts from a common
business problem: teams have thousands of reviews, but they struggle to turn that
data into specific campaign decisions.

The system loads Amazon review data, joins it with product metadata, lets the
user choose the dataset and product scope, then runs a chunked LLM extraction
pipeline. Instead of asking the model for one generic summary, the backend
creates targeted chunks around topics, product risks, low-rating objections, and
positive hooks. The LLM returns structured signals with evidence and recommended
actions.

On the frontend, I designed the workflow around how a marketing analyst would
actually work. The user can inspect dataset health, filter by product name,
choose analysis depth, review signals, inspect evidence, check product health,
prioritize risks, and export a client-safe brief.

The important engineering decision was to keep the LLM inside a controlled
pipeline. The backend handles sampling, chunking, scope filtering, logging, and
deduplication. The LLM handles semantic synthesis. This makes the output more
traceable and more useful than a simple chat prompt.

The project also supports local sglang inference and OpenAI-compatible cloud
APIs. That means it can be used in a privacy-conscious local setup or connected
to a hosted model depending on the deployment environment.

## 8. Technical Highlights

- FastAPI backend with typed Pydantic models.
- React and Vite frontend.
- Dataset discovery from local sample files.
- Amazon review and product metadata ingestion.
- Product-level filtering by `parent_asin`.
- Multi-product analysis scope.
- Configurable extraction plans from the frontend.
- Chunked LLM pipeline for large datasets.
- LLM output logs with execution-time filenames.
- Signal review workflow with approve and dismiss states.
- Client-safe Markdown and JSON exports.
- GitHub Pages demo mode for public frontend review.

## 9. Product And Marketing Value

For a marketing team, the project helps answer:

- Which product claims are risky?
- Which audience tensions appear most often?
- Which objections should content address?
- Which products should not be grouped together in one campaign message?
- Which positive hooks are already supported by review evidence?
- What should be included in a creator brief?

For a product manager, it helps answer:

- Which products have concentrated low-rating pressure?
- Are complaints tied to taste, freshness, packaging, origin claims, or value?
- Which issues are product-specific versus category-wide?
- Which SKUs should be analyzed separately before campaign investment?

## 10. Current Limitations

- GitHub Pages only hosts the static frontend demo. The full LLM workflow still
  requires the local FastAPI backend and local or cloud LLM configuration.
- The current taxonomy is coffee-oriented and should be generalized for more
  categories.
- The product matching depends on available metadata quality.
- The LLM quality depends on model capability and prompt stability.
- The dashboard currently focuses on analysis and export, not user management or
  production deployment.

## 11. Next Improvements

The next iteration should focus on:

- Adding saved analysis runs and run comparison.
- Showing cost and latency estimates before extraction.
- Adding stronger product search in the product filter panel.
- Supporting category-specific topic taxonomies.
- Adding quantitative trend charts over time.
- Improving signal merge evaluation with human feedback.
- Deploying the backend separately so the public frontend can run live
  extraction rather than demo data.

