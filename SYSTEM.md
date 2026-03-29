# Proof of Humanity — System Overview

## What It Does

Proof of Humanity (PoH) is a multi-agent pipeline that verifies the authenticity of a resume by cross-referencing its claims against publicly available digital footprints on the web. The end result is a **Trust Index** score (0–100) with a per-category breakdown.

---

## Pipeline Steps (Start to Finish)

### Step 0 — User Uploads a Resume

- The user opens the web UI at `http://localhost:8000` and uploads a PDF or DOCX file.
- The frontend (`upload.js`) sends the file as `multipart/form-data` to `POST /api/upload`.
- The backend validates the MIME type, generates an `analysis_id`, and immediately returns it.
- A background `asyncio.Task` is spawned to run the full pipeline.
- The user is redirected to `/progress/{analysis_id}`, which connects to an **SSE** (Server-Sent Events) stream at `GET /api/progress/{analysis_id}` for real-time step updates.

**Files involved:**
- `app/api/routes/upload.py` — upload endpoint, background task, SSE progress stream
- `app/templates/index.html` — upload form UI
- `app/static/js/upload.js` — file selection, drag-and-drop, form submit
- `app/templates/progress.html` + `app/static/js/progress.js` — real-time progress page

---

### Step 1 — Parsing Resume (Resume Resolver Agent)

**Agent:** `ResumeResolverAgent`
**AI used:** None (pure extraction)

1. The agent receives the raw file bytes and MIME type.
2. It iterates over registered `ResumeParser` implementations to find one that supports the MIME type.
3. The matching parser extracts plain text:
   - **PDF** → `PdfParser` uses `pdfplumber` to extract text page by page.
   - **DOCX** → `DocxParser` uses `python-docx` to read paragraphs.
4. The extracted text is returned as a single string.

**Output:** Plain text of the resume (e.g. 3,000 characters).

**Files involved:**
- `app/agents/resume_resolver.py`
- `app/providers/parsers/pdf_parser.py`
- `app/providers/parsers/docx_parser.py`
- `app/core/interfaces/resume_parser.py` — abstract interface

---

### Step 2 — Classifying Profile (Classifier Agent)

**Agent:** `ClassifierAgent`
**AI used:** Gemini (`MEDIUM` tier — `gemini-2.5-flash`)

1. The agent receives the plain text from Step 1.
2. It builds a prompt asking the AI to extract structured information.
3. The AI returns a JSON object matching a predefined schema.
4. The JSON is validated into a `PersonProfile` Pydantic model.

**Extracted fields:**
| Field | Description |
|---|---|
| `full_name` | Person's name |
| `title` | Job title |
| `email` | Email address |
| `phone` | Phone number |
| `location` | City/state/country |
| `summary` | Brief professional summary |
| `skills` | List of technical/soft skills |
| `experience` | List of jobs (company, title, duration, description) |
| `education` | List of degrees (institution, degree, field, year) |
| `links` | URLs found in the resume (LinkedIn, GitHub, portfolio) |
| `certifications` | Professional certifications |

**Output:** A structured `PersonProfile` object.

**Files involved:**
- `app/agents/classifier.py`
- `app/core/models/resume.py` — `PersonProfile`, `Experience`, `Education`
- `app/services/ai_service.py` — provider-agnostic AI wrapper
- `app/providers/ai/gemini_provider.py` — Gemini API implementation

---

### Step 3 — Searching the Web (Footprint Collector Agent)

**Agent:** `FootprintCollectorAgent`
**AI used:** Gemini (`LOW` tier — `gemini-2.5-flash-lite`) for query generation, (`MEDIUM` tier — `gemini-2.5-flash`) for page analysis

This is the most complex step. It has three sub-phases:

#### 3a — Generate Search Queries (AI-Powered)

1. The full `PersonProfile` is serialized to JSON and sent to the AI (LOW tier).
2. The AI is prompted to act as an OSINT research assistant and generate 6–10 diverse search queries.
3. The AI considers: name, email, job titles, companies, skills, education, links, usernames — everything available.
4. If AI query generation fails, a hardcoded fallback generates basic queries from name/title/email/company.

#### 3b — Extract Direct URLs from Resume

- Any URLs in `profile.links` are added directly to the scrape list (no search needed).
- The email username is tried as a GitHub profile URL (e.g. `john@gmail.com` → `github.com/john`).

#### 3c — Search & Scrape

1. Each AI-generated query is sent to **DuckDuckGo** via the `SearchEngine` interface.
2. Up to 5 results per query are collected (URLs, titles, snippets).
3. All URLs are de-duplicated and capped at 15.
4. Each URL is scraped concurrently using `httpx` + `BeautifulSoup`:
   - HTML is fetched, scripts/styles/nav/footer stripped.
   - Plain text and page title are extracted.
5. For each successfully scraped page, the AI (MEDIUM tier) analyzes the content against the person's profile:
   - Identifies the platform (GitHub, LinkedIn, etc.)
   - Summarizes relevant content
   - Lists matched claims from the resume
   - Assigns a relevance score (0.0–1.0)

**Output:** `CollectorResult` containing:
- `queries` — the search queries used
- `search_results` — raw search results (title, URL, snippet)
- `footprints` — analyzed `DigitalFootprint` objects

**Files involved:**
- `app/agents/footprint_collector.py`
- `app/providers/search/duckduckgo_engine.py` — DuckDuckGo search
- `app/providers/scraper/bs4_scraper.py` — web page scraper
- `app/core/interfaces/search_engine.py` — abstract interface
- `app/core/interfaces/web_scraper.py` — abstract interface
- `app/core/models/footprint.py` — `SearchResult`, `ScrapedPage`, `DigitalFootprint`

---

### Step 4 — Evaluating Trust (Trust Evaluator Agent)

**Agent:** `TrustEvaluatorAgent`
**AI used:** Gemini (`HIGH` tier — `gemini-2.5-pro`)

1. The agent receives the `PersonProfile` and all `DigitalFootprint` objects.
2. It builds a detailed prompt containing:
   - The full resume profile (name, title, skills, experience, education, links)
   - All digital footprint summaries (source URL, platform, summary, matched claims, relevance)
3. The AI is instructed to act as a trust verification analyst and:
   - Compare resume claims against online evidence
   - Score 5 categories: **identity**, **employment**, **skills**, **education**, **online_presence**
   - Flag discrepancies or red flags
   - Compute a weighted overall trust score (0–100)
   - Provide reasoning for each score

**Output:** A `TrustIndex` containing:
- `overall_score` — 0 to 100
- `categories` — list of `{name, score, evidence}`
- `flags` — list of warning strings
- `reasoning` — full AI explanation

**Files involved:**
- `app/agents/trust_evaluator.py`
- `app/core/models/trust.py` — `TrustIndex`, `TrustCategory`

---

### Step 5 — Display Results

1. Pipeline completes → result is stored in memory keyed by `analysis_id`.
2. The SSE stream sends a `complete` event → frontend redirects to `/result/{analysis_id}`.
3. The result page fetches `GET /api/analysis/{analysis_id}` which returns all data as JSON.
4. JavaScript renders the report with collapsible accordion sections:
   - **Trust Score Gauge** — circular SVG ring (always visible)
   - **Flags** — red alert box (always visible if flags exist)
   - **Parsed Resume Text** — raw extracted text (collapsed)
   - **Extracted Profile** — structured profile with skills, experience, education (collapsed)
   - **Search Queries Used** — numbered list of AI-generated queries (collapsed)
   - **Web Search Results** — de-duplicated search results with URLs and snippets (collapsed)
   - **Digital Footprints** — analyzed pages with relevance scores (collapsed)
   - **Category Breakdown** — score bars per category (collapsed)
   - **AI Reasoning** — full written explanation (collapsed)

**Files involved:**
- `app/api/routes/analysis.py` — JSON API for results
- `app/templates/result.html` — result page shell
- `app/static/js/result.js` — renders all sections dynamically

---

## Architecture & SOLID Principles

### Abstractions (Easy Swapping)

Every external dependency is behind an abstract interface:

| Interface | Current Implementation | Swap Example |
|---|---|---|
| `AIProvider` | `GeminiProvider` | `OpenAIProvider`, `ClaudeProvider` |
| `SearchEngine` | `DuckDuckGoEngine` | `GoogleSearchEngine`, `BingEngine` |
| `WebScraper` | `BS4Scraper` | `PlaywrightScraper`, `SeleniumScraper` |
| `ResumeParser` | `PdfParser`, `DocxParser` | `TesseractParser` (OCR) |

To swap a provider, only `app/dependencies.py` needs to change.

### AI Configuration

- Model tiers are defined in `model_presets.json`:
  - **LOW** (`gemini-2.5-flash-lite`) — fast, cheap, for simple tasks like query generation
  - **MEDIUM** (`gemini-2.5-flash`) — balanced, for classification and page analysis
  - **HIGH** (`gemini-2.5-pro`) — most capable, for trust evaluation
- `AIServiceConfig.from_tier(ModelTier.MEDIUM, system_prompt="...")` loads the preset and allows overrides.
- The `AIService` wraps any `AIProvider` and provides `complete()` and `complete_structured()` methods.

### Dependency Injection

`app/dependencies.py` is the **composition root** — the only file that knows about concrete classes. It assembles parsers → agents → pipeline service. All other code depends only on abstractions.

---

## Project Structure

```
backend/
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── app/
│   ├── main.py               # FastAPI app, routes, logging setup
│   ├── config.py             # Settings (loads from .env)
│   ├── dependencies.py       # Composition root (DI wiring)
│   ├── model_presets.json    # AI model tier definitions
│   │
│   ├── core/
│   │   ├── interfaces/       # Abstract base classes
│   │   │   ├── ai_provider.py
│   │   │   ├── search_engine.py
│   │   │   ├── web_scraper.py
│   │   │   └── resume_parser.py
│   │   └── models/           # Pydantic data models
│   │       ├── ai_config.py  # AIServiceConfig, ModelTier
│   │       ├── resume.py     # PersonProfile, Experience, Education
│   │       ├── footprint.py  # SearchResult, ScrapedPage, DigitalFootprint
│   │       └── trust.py      # TrustIndex, TrustCategory
│   │
│   ├── services/
│   │   ├── ai_service.py     # Provider-agnostic AI wrapper
│   │   └── pipeline_service.py # Orchestrates the 4-agent chain
│   │
│   ├── agents/
│   │   ├── base_agent.py     # Abstract BaseAgent
│   │   ├── resume_resolver.py
│   │   ├── classifier.py
│   │   ├── footprint_collector.py
│   │   └── trust_evaluator.py
│   │
│   ├── providers/
│   │   ├── ai/
│   │   │   └── gemini_provider.py
│   │   ├── parsers/
│   │   │   ├── pdf_parser.py
│   │   │   └── docx_parser.py
│   │   ├── search/
│   │   │   └── duckduckgo_engine.py
│   │   └── scraper/
│   │       └── bs4_scraper.py
│   │
│   ├── api/routes/
│   │   ├── upload.py         # POST /api/upload, GET /api/progress/{id}
│   │   └── analysis.py       # GET /api/analysis/{id}
│   │
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── progress.html
│   │   └── result.html
│   │
│   └── static/js/            # Frontend JavaScript
│       ├── upload.js
│       ├── progress.js
│       └── result.js
│
└── tests/
```

---

## How to Run

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000` in your browser.

---

## Data Flow Diagram

```
User uploads PDF/DOCX
        │
        ▼
┌─────────────────────┐
│  Resume Resolver     │  No AI — pure text extraction
│  (PdfParser/DocxParser)
└────────┬────────────┘
         │ plain text
         ▼
┌─────────────────────┐
│  Classifier Agent    │  AI: MEDIUM tier (gemini-2.5-flash)
│  Extracts structured │  Prompt: "Extract profile from resume"
│  PersonProfile       │  Output: JSON → PersonProfile
└────────┬────────────┘
         │ PersonProfile
         ▼
┌─────────────────────────────────────────────────┐
│  Footprint Collector Agent                       │
│                                                  │
│  1. AI (LOW tier): Generate search queries       │
│  2. Extract direct URLs from resume links        │
│  3. DuckDuckGo: Run each query (5 results each) │
│  4. httpx+BS4: Scrape up to 15 pages             │
│  5. AI (MEDIUM tier): Analyze each page          │
│     against the profile                          │
└────────┬────────────────────────────────────────┘
         │ queries, search_results, footprints
         ▼
┌─────────────────────┐
│  Trust Evaluator     │  AI: HIGH tier (gemini-2.5-pro)
│  Compares resume     │  Prompt: "Compare profile vs footprints"
│  claims vs evidence  │  Output: JSON → TrustIndex
│  Scores 5 categories │  (overall_score, categories, flags, reasoning)
└────────┬────────────┘
         │ TrustIndex
         ▼
┌─────────────────────┐
│  Result Page         │  Collapsible sections showing everything:
│  (Browser)           │  score, flags, resume text, profile,
│                      │  queries, search results, footprints,
│                      │  category breakdown, AI reasoning
└─────────────────────┘
```
