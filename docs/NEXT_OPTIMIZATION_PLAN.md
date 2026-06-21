# Next Optimization Plan

## Product Positioning

Campaign Signal Hub should become a decision workspace for marketing teams, not
a generic LLM summarizer. The strongest product promise is:

> Convert customer language into campaign actions that are evidence-backed,
> reviewable, and safe to use in planning.

The coffee demo already proves the basic loop. The next work should improve
decision quality, dataset control, and review workflow.

## 1. Make Dataset Choice a First-Class Workflow

Current state:

- The frontend can choose between 50-row and 5,000-row coffee samples.
- The backend reloads comments from the selected sample before extraction.

Next improvements:

- Show dataset metadata before extraction: row count, unique products, rating
  distribution, date range, and top brands.
- Add a dataset preview panel with representative positive, mixed, and negative
  reviews.
- Let users choose analysis scope:
  - all products
  - one brand/store
  - one parent ASIN
  - low-rating reviews only
  - verified purchases only

Marketing value:

- Strategists can define the analysis frame before asking the model for
  conclusions.

## 2. Improve Signal Quality

Current state:

- The LLM receives a balanced subset of comments and product context.
- Signals are validated for evidence and structure.

Next improvements:

- Add clustering before LLM extraction so 5,000 reviews become topic groups:
  weak flavor, bitter taste, stale product, misleading claims, machine
  compatibility, price/value.
- Extract signals per cluster, then merge duplicates.
- Track signal strength using:
  - evidence count
  - number of products affected
  - rating skew
  - helpful votes
  - repeated language similarity

Marketing value:

- Signals become more defensible: not just "the model noticed this," but "this
  theme appears across X reviews and Y products."

## 3. Add Product-Level Analysis

Current state:

- Product metadata is visible inside evidence detail.

Next improvements:

- Add a Product Health view:
  - product title
  - average rating
  - review count in sample
  - top risks
  - strongest message angle
  - representative quotes
- Add comparison between products:
  - K-Cups vs instant coffee
  - cold brew vs pods
  - flavored vs unflavored

Marketing value:

- Teams can decide which products are safe to scale and which need messaging
  fixes first.

## 4. Improve Risk Queue

Current state:

- Risk queue filters `risk_flag` signals.

Next improvements:

- Add risk severity lanes: high, medium, low.
- Add owner and status fields:
  - new
  - reviewing
  - actioned
  - ignored
- Add risk playbooks:
  - update PDP copy
  - brief creator talking point
  - customer-care escalation
  - paid-media pause/watch

Marketing value:

- Risk output becomes operational, not just analytical.

## 5. Build a Client-Safe Export

Current state:

- Export returns a JSON summary.

Next improvements:

- Add Markdown export for account teams.
- Add separate internal and client-safe versions.
- Strip raw customer IDs from client exports.
- Include:
  - executive summary
  - top 3 audience tensions
  - top 3 risks
  - recommended next actions
  - evidence appendix

Marketing value:

- The tool can move from analysis into weekly planning and client reporting.

## 6. Add Human Review Memory

Current state:

- Signals can be approved or dismissed in memory.

Next improvements:

- Persist approved/dismissed state.
- Record reviewer notes.
- Use reviewer decisions to guide future extraction prompts.
- Add duplicate detection for signals across runs.

Marketing value:

- The system learns the agency team's standards and avoids repeated cleanup.

## 7. Prepare for Production Architecture

Current state:

- In-memory repository and local CSV files.

Next improvements:

- Add Postgres or SQLite persistence.
- Store source records, product context, signal runs, and review states.
- Move extraction to background jobs for large samples.
- Add progress updates for long-running extraction.

Marketing value:

- Larger datasets can be analyzed without blocking the UI.

## Recommended Next Sprint

1. Add dataset preview and rating/product distribution.
2. Add product-level health view.
3. Add topic clustering before LLM extraction.
4. Add Markdown export.
5. Persist campaign state in SQLite.

This sequence improves the product as a marketing workflow while keeping the
current coffee demo intact.
