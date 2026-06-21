# MVP Tasks

## Phase 1: Skeleton

- [x] Create FastAPI app with health endpoint
- [x] Create React TypeScript app
- [x] Add local development scripts
- [x] Add shared demo campaign fixture
- [x] Render campaign list and workspace

## Phase 2: Data Ingestion

- [x] Define Pydantic models for campaign inputs
- [x] Parse campaign brief text
- [x] Parse creator CSV
- [x] Parse content/comment CSV
- [x] Parse performance CSV
- [x] Persist source provenance for every row
- [x] Add Hugging Face Amazon Reviews dataloader
- [x] Download small `All_Beauty` sample

## Phase 3: LLM Workflow

- [x] Add local sglang-compatible client boundary
- [x] Write signal extraction prompt
- [x] Validate output with Pydantic
- [x] Add fallback behavior for LLM JSON failures
- [x] Store validated campaign signals

## Phase 4: Review UI

- [x] Show signal cards grouped by type
- [x] Add evidence drawer
- [x] Add approve/dismiss state
- [ ] Add creator fit matrix
- [x] Add risk queue

## Phase 5: Export and Automation

- [ ] Generate client-safe campaign summary
- [ ] Add export endpoint
- [ ] Add webhook-style integration stub
- [ ] Document how Slack/Notion/Drive adapters would plug in

## Phase 6: Portfolio Polish

- [ ] Add seeded demo data
- [ ] Add screenshots
- [ ] Add architecture diagram
- [ ] Add short case-study section to README
