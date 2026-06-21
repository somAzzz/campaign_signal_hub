# Next Optimization Plan

## Product Positioning

Campaign Signal Hub should become a decision workspace for marketing teams, not
a generic LLM summarizer. The strongest product promise is:

> Convert customer language into campaign actions that are evidence-backed,
> reviewable, and safe to use in planning.

The current coffee demo has completed the 0-to-1 loop:

- dataset discovery and loading
- product metadata joining
- dataset/profile preview
- product-name filtering
- configurable extraction plans
- local or cloud LLM provider abstraction
- chunked extraction
- evidence-linked signal review
- product health view
- risk queue
- JSON and Markdown export
- LLM output logging
- GitHub Pages frontend demo

The next stage should make the system credible under senior AI engineering or
senior architecture interview scrutiny. The main gaps are not UI polish anymore;
they are evaluation, long-running task reliability, caching, algorithmic
explainability, incremental updates, and product-value forecasting.

## 1. Add A Real Evaluation Pipeline

Current state:

- The system validates LLM output format with structured parsing and Pydantic
  models.
- Signals contain `confidence`, `severity`, and evidence references.
- Evidence can be inspected in the frontend.

Gap:

- Format validation only proves that the model returned the expected schema. It
  does not prove that the extracted signal is faithful to the source review
  text.
- The model can still hallucinate a conclusion that is only loosely supported by
  the selected evidence.

Next improvements:

- Add an `evaluation_runs` concept to the backend.
- Randomly sample 5% of extracted signals after each run.
- Use an LLM-as-a-judge or a smaller verifier model to check:
  - whether each evidence quote exists in the original source text
  - whether the signal title is supported by the evidence
  - whether the summary overgeneralizes beyond the selected records
  - whether the recommended action follows from the evidence
- Store evaluation results with fields such as:
  - `faithfulness_score`
  - `evidence_support_score`
  - `overclaim_risk`
  - `judge_model`
  - `reviewed_signal_id`
  - `failure_reason`
- Add a frontend quality badge:
  - `Verified`
  - `Weak evidence`
  - `Needs human review`

Engineering value:

- This turns LLM quality from a subjective demo claim into a measurable
  evaluation pipeline.

Interview talking point:

> I separated schema validation from semantic evaluation. Pydantic proves the
> output is parseable; the judge pipeline tests whether the answer is grounded in
> the source evidence.

## 2. Move Extraction Into Long-Running Background Jobs

Current state:

- The frontend calls `Run extraction`.
- The backend performs extraction and returns signals when the request finishes.
- This is acceptable for small samples and early demos.

Gap:

- A 50,000-comment run can require many LLM chunk calls.
- Direct request/response extraction is fragile:
  - browser timeout
  - network interruption
  - local sglang restart
  - cloud LLM rate limit
  - FastAPI worker blocked by long-running work

Next improvements:

- Introduce an `ExtractionJob` model:
  - `job_id`
  - `campaign_id`
  - `dataset_id`
  - `scope`
  - `plan`
  - `status`
  - `current_chunk`
  - `total_chunks`
  - `started_at`
  - `ended_at`
  - `error`
  - `result_signal_ids`
- Add API endpoints:
  - `POST /api/campaigns/{id}/extraction-jobs`
  - `GET /api/campaigns/{id}/extraction-jobs/{job_id}`
  - `GET /api/campaigns/{id}/extraction-jobs/{job_id}/events`
- Start with FastAPI `BackgroundTasks` or `asyncio.create_task` for a lightweight
  implementation.
- Upgrade path:
  - Celery + Redis for multi-worker production
  - RQ or Dramatiq as a simpler queue alternative
  - Postgres-backed job table for persistence
- Add frontend progress display:
  - "Preparing chunks"
  - "Analyzing chunk 12/50"
  - "Merging signals"
  - "Running evaluation"
  - "Export ready"
- Use SSE or WebSocket for status updates. Long polling is acceptable as the
  first implementation.

Engineering value:

- The UI no longer depends on one long HTTP request.
- The backend can survive slow LLM calls and provide meaningful progress.

Interview talking point:

> The first MVP used synchronous extraction for simplicity. The production
> version moves extraction into resumable jobs with progress reporting, because
> LLM workflows are latency-heavy and failure-prone.

## 3. Add Chunk-Level Caching And Idempotency

Current state:

- LLM runs are logged after execution.
- The filename includes execution time, dataset id, and run identifiers.

Gap:

- If a run fails at chunk 40 of 50, the system may need to recompute the first
  39 chunks.
- This wastes time, money, and GPU capacity.
- Re-running the same dataset/scope/plan can produce unnecessary duplicate LLM
  calls.

Next improvements:

- Compute a deterministic hash for each planned chunk:
  - dataset id
  - scope
  - analysis mode
  - extraction plan
  - sorted source record ids
  - normalized prompt template version
  - model name/provider
- Store chunk outputs in a cache table or local cache directory:
  - `chunk_hash`
  - `prompt_hash`
  - `model`
  - `status`
  - `raw_output`
  - `parsed_signals`
  - `created_at`
  - `expires_at`
- Before calling the LLM, check whether a successful cache entry exists.
- If a job fails midway, resume from the first missing or failed chunk.
- Add a `force_refresh` option for users who intentionally want a fresh run.

Engineering value:

- The extraction pipeline becomes idempotent.
- Long runs become recoverable.
- Cloud API cost and local GPU time are reduced.

Interview talking point:

> I would treat each chunk as a deterministic unit of work. With a stable chunk
> hash and prompt version, we can skip completed work and resume failed runs.

## 4. Make Signal Merge And Deduplication Explainable

Current state:

- Chunk-level signals are merged and deduplicated.
- Signal strength metadata is attached after merging.

Gap:

- "Merged and deduplicated" is too vague for a senior engineering interview.
- If deduplication is purely heuristic or one large LLM prompt, it can suffer
  from lost-in-the-middle effects and weak reproducibility.

Next improvements:

- Introduce a two-stage merge algorithm.

Stage 1: semantic clustering

- Generate embeddings for each chunk-level signal using a lightweight embedding
  model.
- Embed fields such as:
  - title
  - summary
  - signal type
  - recommended action
- Cluster signals with DBSCAN, HDBSCAN, or agglomerative clustering.
- Keep metadata:
  - cluster id
  - member signal ids
  - cosine similarity range
  - source chunk ids
  - affected product ids

Stage 2: cluster-level synthesis

- For each semantic cluster, call the LLM with only the member signals and their
  evidence.
- Ask the model to produce one canonical signal:
  - tighter title
  - consolidated summary
  - merged recommended action
  - strongest evidence
  - confidence derived from support count and agreement

Fallback for small systems:

- Use deterministic text similarity and keyword overlap first.
- Add embeddings once the pipeline is ready for production.

Engineering value:

- Deduplication becomes inspectable.
- The model does not need to reason over all signals at once.
- Merge behavior can be evaluated and tuned.

Interview talking point:

> I would not ask one LLM prompt to dedupe all chunk outputs. I would first use
> embedding-based clustering, then call the LLM only inside each cluster for
> focused synthesis.

## 5. Support Incremental Updates

Current state:

- The system assumes datasets are static CSV samples.
- A user can download new samples and run extraction again.

Gap:

- Real ecommerce review streams are incremental.
- New reviews arrive daily.
- Re-running the whole dataset every time is inefficient and makes trend
  analysis difficult.

Next improvements:

- Add `ingestion_batch_id` to source records.
- Store a stable source fingerprint for each review:
  - dataset source
  - asin
  - parent_asin
  - user id
  - timestamp
  - text hash
- During import, insert only new records.
- Run extraction only on the new batch.
- Merge new signals into existing historical signals:
  - attach new evidence to existing signals if semantically similar
  - create a new signal if no existing cluster matches
  - mark stale signals if no longer supported by recent reviews
- Add time-window analysis:
  - last 7 days
  - last 30 days
  - current launch period
  - pre/post campaign comparison

Engineering value:

- The system becomes useful for ongoing monitoring, not just one-off analysis.

Interview talking point:

> I would model review ingestion as append-only batches, then run incremental
> extraction against new records and merge into a historical signal store.

## 6. Add Token, Cost, And Time Estimation

Current state:

- The frontend lets users set `Reviews/chunk`, `Max chunks`,
  `Chunk threshold`, and `Max signals`.
- Users can choose sample or full-chunk mode.

Gap:

- Users cannot estimate cost or latency before running extraction.
- Increasing `Max chunks` can multiply runtime and cloud API cost.

Next improvements:

- Add a frontend estimate under the Analysis Plan panel:
  - selected products
  - estimated chunk count
  - estimated input tokens
  - estimated output tokens
  - estimated runtime
  - estimated cost for cloud models
- Backend should expose an estimator endpoint:
  - `POST /api/campaigns/{id}/estimate-extraction`
- Estimate from:
  - number of selected records
  - average review length
  - product context size
  - prompt template overhead
  - plan settings
  - model throughput/cost config
- Example frontend copy:

```text
Based on 12 selected products and the Broad preset, this run will analyze about
16 chunks, use roughly 180k tokens, and take about 45-90 seconds on the current
LLM provider.
```

Product value:

- Users understand the tradeoff between depth, time, and cost before clicking
  Run extraction.

Interview talking point:

> I would expose estimation before execution because LLM workflows have real
> cost and latency. A good AI product should make those tradeoffs visible.

## 7. Add Competitor Contrast And Brand-Level Comparison

Current state:

- The system supports brand/store scopes and product-name filtering.
- Product Health helps inspect one dataset's products.

Gap:

- Marketing teams often need to compare their product against competitors.
- Current analysis focuses on one selected dataset or product group.

Next improvements:

- Add a Brand/Competitor selector:
  - own brand
  - competitor brand
  - multiple brands
- Let users compare:
  - top risks by brand
  - top positive hooks by brand
  - rating skew
  - weak-flavor complaints
  - freshness complaints
  - claim-trust complaints
  - price/value sensitivity
- Add `Competitor Signal Matrix`:

```text
Signal Theme           Own Brand     Competitor A     Competitor B
Weak flavor            High          Medium           Low
Origin claim risk      Low           High             Medium
Machine fit            Strong        Strong           Unknown
Price/value concern    Medium        Low              High
```

- Add export section:
  - "Where we are safer than competitors"
  - "Where competitors own the message"
  - "Claims we should avoid"
  - "Claims we can credibly attack"

Product value:

- The tool becomes a strategic positioning workspace, not only a review
  summarizer.

Interview talking point:

> Marketing analysis is comparative. I would extend scope from product filtering
> to competitor contrast, then use the same signal pipeline to produce a
> brand-level matrix.

## 8. Improve Persistence And Data Modeling

Current state:

- The MVP uses in-memory repository patterns and local files.
- Some state is snapshotted locally.

Gap:

- In-memory state is not sufficient for production.
- Large extraction jobs, cached chunks, evaluation runs, and human review memory
  require durable storage.

Next improvements:

- Add SQLite for local development and Postgres for production.
- Persist:
  - campaigns
  - source records
  - product context
  - ingestion batches
  - extraction jobs
  - chunk cache entries
  - LLM runs
  - extracted signals
  - evaluation results
  - human review actions
- Add migrations with Alembic.
- Keep repository interfaces so storage can be swapped without rewriting service
  logic.

Engineering value:

- This turns the project from a local prototype into a production-shaped system.

## 9. Improve Human Review Memory

Current state:

- Signals can be approved or dismissed.

Gap:

- Reviewer decisions are not yet used deeply in future extraction.

Next improvements:

- Persist approval, dismissal, reviewer, timestamp, and notes.
- Use dismissed-signal patterns as negative examples in prompts.
- Use approved-signal patterns as preferred style examples.
- Add duplicate detection across runs.
- Add a "why dismissed" taxonomy:
  - weak evidence
  - duplicate
  - not actionable
  - not marketing relevant
  - model overclaim

Product value:

- The system starts learning the team's judgment standards.

## 10. Recommended Roadmap

### Sprint 1: Reliability For Large Runs

1. Add extraction job model and status endpoint.
2. Add frontend progress panel with long polling.
3. Add chunk-level cache with deterministic chunk hashes.
4. Add resumable extraction from failed chunks.

Why first:

- This solves the biggest production risk: long-running LLM calls.

### Sprint 2: Quality And Evaluation

1. Add LLM-as-a-judge evaluation for sampled signals.
2. Store evaluation results.
3. Add quality badges in the signal review UI.
4. Add evidence-support score to exports.

Why second:

- This directly addresses hallucination and trustworthiness.

### Sprint 3: Explainable Merge

1. Add signal embedding generation.
2. Cluster chunk-level signals with DBSCAN or agglomerative clustering.
3. Add cluster-level LLM synthesis.
4. Expose merge cluster metadata in logs.

Why third:

- This makes the core algorithm defensible under technical questioning.

### Sprint 4: Product Value Expansion

1. Add token/cost/time estimator.
2. Add competitor/brand comparison scope.
3. Add Competitor Signal Matrix.
4. Add comparison export section.

Why fourth:

- This moves the product from internal analysis to strategic marketing planning.

### Sprint 5: Incremental And Production Storage

1. Add ingestion batches and source fingerprints.
2. Add SQLite/Postgres persistence.
3. Add incremental extraction for new reviews.
4. Merge new signals into historical signal clusters.

Why fifth:

- This turns the system into a monitoring platform, not just a one-shot tool.

## Final Architecture Target

The production-shaped architecture should look like this:

```text
Review sources / product metadata
        ↓
Ingestion batches + source fingerprints
        ↓
Durable source store
        ↓
Scope planner + extraction estimator
        ↓
Background extraction job
        ↓
Chunk planner
        ↓
Chunk hash cache
        ↓
LLM extraction
        ↓
LLM-as-judge evaluation
        ↓
Embedding clustering + cluster-level merge
        ↓
Signal store + human review memory
        ↓
Dashboard + product health + competitor matrix + exports
```

The key improvement is that every expensive or subjective step becomes
observable:

- chunk planning is logged
- LLM prompts are logged
- outputs are cached
- evidence is traceable
- evaluations are scored
- merges are explainable
- reviewer decisions are persisted

That is the difference between a convincing MVP and a senior-level AI
engineering system.
