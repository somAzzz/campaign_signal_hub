# Campaign Signal Hub

Campaign Signal Hub is a marketing-analysis workspace for turning noisy customer
feedback into evidence-backed campaign decisions.

The current demo focuses on coffee products. It combines Amazon review data,
product metadata, a campaign brief, creator profiles, and performance snapshots
to extract signals a brand or agency team can actually use.

## What It Does

Marketing teams often have plenty of data but not enough structured judgment:
reviews, ratings, product pages, creator ideas, and paid-media results all live
in separate places. Campaign Signal Hub connects those inputs and produces a
small reviewable signal board.

The system extracts:

- audience tensions
- campaign risks
- message angles
- content opportunities
- creator/brand fit signals
- recommended next actions

Every signal includes evidence snippets and source provenance so a strategist
can inspect the original review before approving it.

## Current Demo Scenario

Brand: `RoastHouse Coffee`

Use case:

> Identify taste, freshness, and positioning risks before scaling creator and
> paid social campaigns for coffee pods, cold brew, and flavored coffee.

Primary questions:

- Are customers reacting negatively to roast strength, flavor, bitterness, or
  freshness?
- Which claims should creators avoid or clarify?
- Which review phrases can become credible campaign hooks?
- Which signals are strong enough to include in a client-safe summary?

## Data Inputs

The project currently uses Amazon Reviews 2023 from McAuley Lab via Hugging
Face Hub.

Local samples:

```text
data/samples/coffee_50_comments.csv       small prompt/UI sample
data/samples/coffee_5000_comments.csv     expanded product-matched review set
data/samples/coffee_50_products.csv       product metadata for current ASINs
```

Fixtures:

```text
data/fixtures/coffee_campaign_brief.md
data/fixtures/coffee_creator_shortlist.csv
data/fixtures/coffee_performance_snapshot.csv
```

The frontend lets you choose which comment sample to use before running
extraction.

## Analysis Flow

```text
Amazon reviews + product metadata
        ↓
Ingestion and source provenance
        ↓
Local or cloud LLM extraction
        ↓
Pydantic validation and quality checks
        ↓
Signal review dashboard
        ↓
Evidence inspection and client-safe export
```

The frontend only shows reviewed campaign signals and evidence. Raw LLM outputs
are stored separately for debugging and audit.

## LLM Runtime

The backend defaults to a local sglang OpenAI-compatible server:

```text
http://localhost:30000
```

Default environment values:

```bash
CSH_LLM_PROVIDER=sglang
CSH_SGLANG_BASE_URL=http://localhost:30000
CSH_SGLANG_MODEL=Qwen/Qwen3.5-35B-A3B
```

Cloud APIs can be used without code changes when they expose an
OpenAI-compatible `/v1/chat/completions` endpoint:

```bash
CSH_LLM_PROVIDER=openai_compatible
CSH_CLOUD_LLM_BASE_URL=https://api.openai.com
CSH_CLOUD_LLM_MODEL=gpt-4.1-mini
CSH_CLOUD_LLM_API_KEY=<api-key>
```

The same provider switch works for other compatible vendors by changing
`CSH_CLOUD_LLM_BASE_URL`, `CSH_CLOUD_LLM_MODEL`, and `CSH_CLOUD_LLM_API_KEY`.

The extractor uses structured JSON output, validates it with Pydantic, and falls
back to deterministic rules if model output fails validation.

Raw LLM runs are written to:

```text
data/processed/llm_outputs/
```

Each run file includes audit metadata: start/end time, duration, status,
provider, model, endpoint, selected dataset and scope, source files, record
counts, selected source record IDs, request metadata, response usage, parsed
signal count, and any error that caused fallback. The processed sample is
available in the top-level `dataset` object, while all ingested files for the
campaign are listed in `source_files`.

They can also be inspected through:

```bash
curl http://localhost:8000/api/campaigns/<campaign_id>/llm-outputs
```

## Run Locally

Backend:

```bash
uv run --extra data uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run build
npm run preview -- --host 0.0.0.0 --port 5173
```

Open:

```text
http://localhost:5173
```

API:

```text
http://localhost:8000
```

To run without sglang:

```bash
CSH_LLM_PROVIDER=stub uv run --extra data uvicorn app.main:app --app-dir backend
```

## Data Scripts

Download a small keyword-filtered coffee sample:

```bash
uv run --extra data python scripts/sample_amazon_reviews.py \
  --category Grocery_and_Gourmet_Food \
  --keywords coffee,espresso,cold brew,latte,cappuccino,arabica,k-cup,kcup,keurig,kona,sumatra \
  --limit 50 \
  --max-scan-rows 250000 \
  --output data/samples/coffee_50_comments.csv
```

Look up product metadata from ASIN / parent ASIN:

```bash
uv run --extra data python scripts/lookup_amazon_products.py \
  --category Grocery_and_Gourmet_Food \
  --comments data/samples/coffee_50_comments.csv \
  --output data/samples/coffee_50_products.csv
```

List current product ASINs:

```bash
uv run --extra data python scripts/expand_reviews_for_products.py \
  --products data/samples/coffee_50_products.csv \
  --list-asins
```

Download more reviews for the current product set:

```bash
uv run --extra data python scripts/expand_reviews_for_products.py \
  --category Grocery_and_Gourmet_Food \
  --products data/samples/coffee_50_products.csv \
  --limit 5000 \
  --output data/samples/coffee_5000_comments.csv
```

## Frontend Views

- `Signal review`: review extracted signals and inspect evidence
- `Campaign health`: inspect data coverage, signal mix, products, and metrics
- `Risk queue`: focus only on campaign risks

Run extraction from the header after choosing a dataset:

```text
Coffee reviews / 50 rows
Coffee reviews / 5,000 rows
```

## Project Structure

```text
backend/app/
  api/            FastAPI routes
  core/           settings
  models/         Pydantic domain models
  services/       ingestion, dataloading, LLM extraction, quality checks

frontend/src/
  App.tsx         dashboard workspace
  api.ts          API client
  styles.css     product UI styling

scripts/
  sample_amazon_reviews.py
  lookup_amazon_products.py
  expand_reviews_for_products.py
  format_python.sh
```

## Quality Checks

Signals are rejected or flagged when:

- evidence is missing
- evidence quotes do not match source reviews
- malformed JSON is returned
- a risk lacks severity
- output is too generic to support a campaign action

## Development

Format and lint Python:

```bash
./scripts/format_python.sh
```

Check frontend:

```bash
cd frontend
npm run build
npm audit --audit-level=moderate
```
