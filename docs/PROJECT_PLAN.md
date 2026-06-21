# Campaign Signal Hub Project Plan

## 1. Positioning

Campaign Signal Hub is an internal AI product for agency campaign teams. Its
job is to convert messy campaign material into validated, reusable signals that
help strategists, community managers, and paid-media teams decide what to do
next.

The project should demonstrate:

- production-ready LLM workflow design
- marketing automation use-case thinking
- API and data-flow implementation
- React/FastAPI product delivery
- reliability: validation, retries, quality checks, and explainable outputs

## 2. Target User

Primary user: campaign strategist or account team member at a marketing agency.

They need to answer:

- What is the audience saying?
- Which creator/content angle fits the brand brief?
- What risks or objections are emerging?
- What should the team do next this week?
- Which signals are strong enough to show to a client?

## 3. Core Workflow

1. Create campaign workspace
2. Import campaign material
3. Normalize inputs into typed records
4. Run LLM signal extraction with Pydantic validation
5. Score and group signals by usefulness
6. Review signals in a React dashboard
7. Export action notes or send them to an internal tool

Visualization is the final layer. The core project is the campaign-data
pipeline and AI workflow behind it.

## 4. MVP Scope

### MVP Input

- one campaign brief as Markdown or text
- one creator shortlist CSV
- one comments/captions CSV
- one performance snapshot CSV

### MVP Output

- campaign signal cards
- creator-brand fit summary
- audience tension summary
- risk flags
- recommended next actions
- evidence snippets linked to source rows

### MVP UI

Use a work-focused dashboard, not a landing page.

Primary screens:

- campaign list
- campaign workspace
- signal review
- creator fit matrix
- evidence drawer
- export summary

## 5. Product Features

### Campaign Workspace

Stores campaign-level context:

- client
- brand
- campaign objective
- target audience
- tone constraints
- required platforms
- campaign dates

### Ingestion Pipeline

Accepts uploaded CSV/text files and turns them into typed records:

- `BriefDocument`
- `CreatorProfile`
- `ContentPost`
- `CommunityComment`
- `PerformanceMetric`

The ingestion layer should keep source provenance for every row.

### LLM Signal Extraction

For each source group, the backend asks the LLM for structured outputs:

- `audience_tension`
- `brand_fit`
- `message_angle`
- `risk_flag`
- `content_opportunity`
- `next_action`

Every response must pass Pydantic validation before entering the database.

### Quality Checks

The system should reject or flag:

- empty evidence
- unsupported claims
- duplicate recommendations
- sentiment without source text
- creator fit without brief criteria
- malformed JSON

### Review Dashboard

The dashboard should let a team member:

- filter signals by type
- inspect evidence
- approve or dismiss suggestions
- compare creator fit
- export a client-safe summary

## 6. Backend Plan

### FastAPI Modules

```text
backend/app/
  main.py
  api/
    campaigns.py
    uploads.py
    signals.py
    exports.py
  core/
    config.py
    database.py
    logging.py
  models/
    campaign.py
    source.py
    signal.py
  services/
    ingestion.py
    llm_client.py
    signal_extractor.py
    quality_checks.py
    export_builder.py
```

### API Endpoints

```text
POST   /api/campaigns
GET    /api/campaigns
GET    /api/campaigns/{campaign_id}
POST   /api/campaigns/{campaign_id}/uploads
POST   /api/campaigns/{campaign_id}/extract-signals
GET    /api/campaigns/{campaign_id}/signals
PATCH  /api/signals/{signal_id}
GET    /api/campaigns/{campaign_id}/export
```

### Database Tables

```text
campaigns
source_files
source_records
creator_profiles
campaign_signals
signal_evidence
quality_events
exports
```

## 7. Frontend Plan

### React Screens

```text
frontend/src/
  routes/
    CampaignList.tsx
    CampaignWorkspace.tsx
    SignalReview.tsx
  components/
    CampaignHeader.tsx
    SignalCard.tsx
    EvidenceDrawer.tsx
    CreatorFitMatrix.tsx
    RiskQueue.tsx
    ExportPanel.tsx
```

### Visual Direction

Subject: internal agency operating room for campaign signals.

Design tone:

- dense, useful, fast to scan
- not a glossy AI landing page
- evidence-first, with source snippets and review states

Palette:

- Ink `#15171A`
- Workbench `#F6F3EA`
- Signal green `#19A974`
- Warning amber `#D98C21`
- Review blue `#2F6FED`
- Muted graphite `#697077`

Typography:

- UI/body: Inter or IBM Plex Sans
- data/codes: JetBrains Mono

Signature element:

- signal cards look like campaign-room sticky notes, but with strict evidence
  metadata and review states.

## 8. LLM Output Contract

Example Pydantic model:

```python
class CampaignSignal(BaseModel):
    signal_type: Literal[
        "audience_tension",
        "brand_fit",
        "message_angle",
        "risk_flag",
        "content_opportunity",
        "next_action",
    ]
    title: str
    summary: str
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str]
    recommended_action: str | None = None
    client_safe: bool
```

## 9. Demo Dataset

Create a small synthetic campaign:

- brand: iced coffee product
- objective: Gen Z awareness campaign
- platforms: TikTok, Instagram Reels
- creators: 12 synthetic creator profiles
- comments: 200 synthetic community comments
- performance: 30 rows of synthetic metrics

The dataset should be fake but realistic enough to demonstrate the workflow.

## 10. Portfolio Story

The project should be presented as:

> An internal AI workflow for campaign teams that turns briefs, creator data,
> community feedback, and performance exports into validated campaign signals.

What it proves:

- I can translate a business workflow into software.
- I can build LLM integrations with robust outputs.
- I can design APIs and data flows.
- I can build a React interface around review and decision-making.
- I can make automation useful for non-technical teams.

## 11. Build Phases

### Phase 1: Product Skeleton

- FastAPI app
- React app
- shared local demo dataset
- campaign list and workspace shell

### Phase 2: Data Pipeline

- CSV/text upload
- source normalization
- source provenance
- typed database records

### Phase 3: LLM Workflow

- OpenAI-compatible LLM client
- structured prompt templates
- Pydantic validation
- retry and quality-event logging

### Phase 4: Review UI

- signal cards
- evidence drawer
- risk queue
- creator fit matrix
- approve/dismiss workflow

### Phase 5: Automation Layer

- export campaign summary
- webhook-style integration stub
- Slack/Notion style adapter design

### Phase 6: Portfolio Polish

- seeded demo data
- screenshots
- architecture diagram
- short case-study README

## 12. Success Criteria

The MVP is successful when a reviewer can:

- create a campaign
- import demo data
- run signal extraction
- review validated AI outputs
- inspect evidence
- export a client-safe summary
- understand the API/data/LLM architecture from the README

