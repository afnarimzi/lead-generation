# Lead Generation System Architecture

## High-Level Architecture (Production Deployment)

```
┌─────────────────────────────────────────────────────────────────┐
│                    VERCEL PRODUCTION DEPLOYMENT                 │
│                   https://leadgeneration-dun.vercel.app         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 REACT FRONTEND                          │   │
│  │              TypeScript + Vite + TailwindCSS           │   │
│  │                                                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│  │  │   Search     │  │    Leads     │  │   My Jobs    │ │   │
│  │  │   Page       │  │   Results    │  │  (Favorites) │ │   │
│  │  │              │  │              │  │              │ │   │
│  │  │ • Keywords   │  │ • Star Jobs  │  │ • Starred    │ │   │
│  │  │ • Time Filter│  │ • Expand     │  │   Jobs Only  │ │   │
│  │  │ • Platforms  │  │   Details    │  │ • Persistent │ │   │
│  │  │ • Real-time  │  │ • Quality    │  │ • Export     │ │   │
│  │  │   Status     │  │   Scores     │  │   Options    │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │ HTTP/REST API                     │
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 FASTAPI BACKEND                         │   │
│  │              Python 3.12 + Serverless                  │   │
│  │                                                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│  │  │   Search     │  │    Leads     │  │   Cleanup    │ │   │
│  │  │   Router     │  │   Router     │  │   Router     │ │   │
│  │  │              │  │              │  │              │ │   │
│  │  │ • POST /api/ │  │ • GET /api/  │  │ • POST /api/ │ │   │
│  │  │   search/    │  │   leads      │  │   cleanup    │ │   │
│  │  │   start      │  │ • POST /api/ │  │ • Manual     │ │   │
│  │  │ • GET /api/  │  │   leads/{id}/│  │   Database   │ │   │
│  │  │   search/    │  │   favorite   │  │   Reset      │ │   │
│  │  │   status     │  │ • GET /api/  │  │              │ │   │
│  │  │ • GET /api/  │  │   leads/     │  │              │ │   │
│  │  │   search/    │  │   favorites  │  │              │ │   │
│  │  │   results    │  │              │  │              │ │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR ENGINE                        │
│                   (Workflow Coordinator)                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  0. Auto-Cleanup → 1. Credit Check → 2. Parallel        │ │
│  │  Scraping → 3. AI Processing → 4. Store → 5. Return     │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────────┬──────────────┘
             │                                    │
             ▼                                    ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│   SCRAPING LAYER (Apify)    │    │    AI PROCESSING ENGINES    │
│                              │    │                             │
│  ┌────────────────────────┐ │    │  ┌──────────────────────┐  │
│  │  Upwork Adapter        │ │    │  │ Auto-Cleanup Engine  │  │
│  │  flash_mage~upwork     │ │    │  │ (Clear non-favorites)│  │
│  │  30 results/search     │ │    │  └──────────────────────┘  │
│  └────────────────────────┘ │    │  ┌──────────────────────┐  │
│  ┌────────────────────────┐ │    │  │ Deduplication Engine │  │
│  │  Freelancer Adapter    │ │    │  │ (Levenshtein + URL)  │  │
│  │  janbruinier~jan-      │ │    │  └──────────────────────┘  │
│  │  freelancer-job-scraper│ │    │  ┌──────────────────────┐  │
│  │  30 results/search     │ │    │  │ Quality Scorer       │  │
│  │  ✅ FIXED ACTOR       │ │    │  │ (Budget + Keywords)  │  │
│  └────────────────────────┘ │    │  └──────────────────────┘  │
│  ┌────────────────────────┐ │    │  ┌──────────────────────┐  │
│  │  PeoplePerHour Adapter │ │    │  │ Hybrid Filter Engine │  │
│  │  getdataforme~         │ │    │  │  - Hard Filters      │  │
│  │  peopleperhour-job-    │ │    │  │  - Gemini AI Match   │  │
│  │  scraper               │ │    │  │  - Budget Enrichment │  │
│  │  30 results/search     │ │    │  │  - Final Ranking     │  │
│  │  ✅ WORKING           │ │    │  │  - Threshold: 0.70    │  │
│  └────────────────────────┘ │    │  └──────────────────────┘  │
│  ┌────────────────────────┐ │    │  ┌──────────────────────┐  │
│  │  Fiverr (DISABLED)     │ │    │  │ Gemini Embedding     │  │
│  │  Returns gigs not jobs │ │    │  │ Engine (Cloud API)   │  │
│  │  ❌ NOT BUYER REQUESTS │ │    │  │ 3072 dimensions      │  │
│  └────────────────────────┘ │    │  │ Replaces 7.2GB       │  │
│                              │    │  │ sentence-transformers│  │
│  Max: 90 jobs total          │    │  └──────────────────────┘  │
│  (30 × 3 platforms)          │    │  ┌──────────────────────┐  │
│  Credit Usage: ~0.36/search  │    │  │ Budget Enrichment    │  │
│                              │    │  │ (URL Scraping)       │  │
└──────────────────────────────┘    │  │ BeautifulSoup4       │  │
                                    │  └──────────────────────┘  │
                                    └─────────────┬───────────────┘
                                                  ▼
                                    ┌─────────────────────────────┐
                                    │   NEON POSTGRESQL DATABASE  │
                                    │        (Cloud Hosted)       │
                                    │                             │
                                    │  ┌──────────────────────┐  │
                                    │  │  leads table         │  │
                                    │  │  - id (PRIMARY KEY)  │  │
                                    │  │  - job_title         │  │
                                    │  │  - job_description   │  │
                                    │  │  - platform_name     │  │
                                    │  │  - budget_amount     │  │
                                    │  │  - payment_type      │  │
                                    │  │  - quality_score     │  │
                                    │  │  - posted_datetime   │  │
                                    │  │  - is_favorited ⭐   │  │
                                    │  │  - created_at        │  │
                                    │  │  - updated_at        │  │
                                    │  │  - job_url           │  │
                                    │  │  - client_info       │  │
                                    │  └──────────────────────┘  │
                                    └─────────────────────────────┘
```

## Data Flow: Search Request

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: USER SEARCH                                             │
│ User enters: keywords=["AI"], timeFilter=168h, platforms=all   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 0: AUTO-CLEANUP (NEW)                                     │
│ Clear all non-favorited leads from database                    │
│ Preserve starred jobs permanently                              │
│ Result: Fresh database ready for new results                   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: CREDIT CHECK                                            │
│ Estimate: 0.12 credits × 3 platforms = 0.36 credits            │
│ Available: 5.0 credits → ✓ Proceed                             │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: PARALLEL SCRAPING (3 platforms simultaneously)          │
│                                                                 │
│  Upwork ────────┐                                              │
│  Freelancer ────┼──→ Apify Actors → Raw JSON Data             │
│  PeoplePerHour ─┘                                              │
│                                                                 │
│  Result: 90 jobs (30 + 30 + 30) - INCREASED CAPACITY          │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: NORMALIZATION                                           │
│ Convert platform-specific formats to unified Lead model        │
│ - Parse dates ("2 days ago" → datetime)                        │
│ - Convert currencies (₹50000 → $600 USD)                       │
│ - Extract budgets from text                                    │
│ - Normalize field names (janbruinier actor support)           │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: DEDUPLICATION                                           │
│ Remove duplicate jobs across platforms                         │
│ - Title similarity (Levenshtein distance)                      │
│ - URL matching                                                 │
│ Result: 90 → 85 unique jobs                                    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: QUALITY SCORING                                         │
│ Calculate initial quality score (0-100)                        │
│ - Budget completeness: 0-30 points                            │
│ - Description quality: 0-20 points                            │
│ - Keyword matching: 0-25 points                               │
│ - Recency: 0-25 points                                        │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: HYBRID FILTERING & RANKING (UPDATED WEIGHTS)           │
│                                                                 │
│  7a. HARD FILTERS (Time filter applied)                        │
│      ✓ Date: posted_within_hours (168h = 7 days)              │
│      ✓ Quality: min_quality_score (0.0)                       │
│      ❌ NO budget filtering                                    │
│      ❌ NO keyword filtering (handled by AI)                   │
│      Result: 85 → 82 jobs (3 too old)                         │
│                                                                 │
│  7b. AI EMBEDDING MATCHING (More Permissive)                   │
│      - Generate query embedding: "AI" → [384 dimensions]      │
│      - Generate job embeddings: each job → [384 dimensions]   │
│      - Calculate cosine similarity                            │
│      - Filter by threshold (similarity >= 0.15) - LOWERED     │
│      Result: 82 → 45 relevant jobs                            │
│                                                                 │
│  7c. PRELIMINARY RANKING (NEW WEIGHTS)                         │
│      Score = 0.4×similarity + 0.3×budget + 0.2×quality       │
│              + 0.1×recency                                     │
│      Sort by preliminary score                                │
│                                                                 │
│  7d. BUDGET ENRICHMENT (Top 50 only)                          │
│      - Visit job URLs asynchronously                          │
│      - Scrape missing budget data                             │
│      - Update lead objects                                    │
│      Result: 45 jobs, 28 budgets enriched                     │
│                                                                 │
│  7e. FINAL RANKING (Budget Weight Increased)                  │
│      Recalculate scores with enriched budgets                 │
│      Score = 0.4×similarity + 0.3×budget + 0.2×quality       │
│              + 0.1×recency                                     │
│      Sort by final score - HIGH BUDGET JOBS RANK HIGHER       │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: DATABASE STORAGE (With Favorites Support)              │
│ Store 45 leads in PostgreSQL with embeddings                   │
│ Preserve is_favorited status for existing starred jobs         │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 9: RETURN TO UI (Enhanced Display)                        │
│ Display 45 leads sorted by final score                         │
│ - High budget jobs at top (e.g., $5,000 job = #1)             │
│ - Star system for favorites                                    │
│ - Time filter applied (only jobs within 7 days)               │
│ - Expandable details with full descriptions                    │
│ - PeoplePerHour: 25 leads                                      │
│ - Freelancer: 12 leads (janbruinier actor working)            │
│ - Upwork: 8 leads                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend (React + TypeScript)
```
frontend/
├── src/
│   ├── pages/
│   │   ├── SearchAndResults.tsx  # Main search interface
│   │   ├── Leads.tsx             # Lead list view
│   │   └── LeadDetail.tsx        # Individual lead details
│   ├── api/
│   │   ├── client.ts             # Axios HTTP client
│   │   ├── search.ts             # Search API calls
│   │   └── leads.ts              # Lead API calls
│   └── types/
│       ├── lead.ts               # TypeScript interfaces
│       └── api.ts                # API response types
```

### 2. Backend (FastAPI)
```
api/
├── main.py                       # FastAPI app initialization
├── models.py                     # Pydantic request/response models
└── routers/
    ├── search.py                 # POST /api/search
    ├── leads.py                  # GET /api/leads
    ├── export.py                 # POST /api/export
    └── stats.py                  # GET /api/stats
```

### 3. Core Engine
```
lead_scraper/
├── orchestrator.py               # Main workflow coordinator
├── adapters/                     # Platform-specific scrapers
│   ├── platform_adapter.py       # Base adapter interface
│   ├── upwork_adapter.py         # Upwork scraping
│   ├── freelancer_adapter.py     # Freelancer scraping
│   ├── peopleperhour_adapter.py  # PeoplePerHour scraping
│   └── fiverr_adapter.py         # Fiverr (disabled)
├── engines/                      # Processing engines
│   ├── deduplication_engine.py   # Remove duplicates
│   ├── quality_scorer.py         # Calculate quality scores
│   ├── hybrid_filter_engine.py   # AI filtering & ranking
│   ├── embedding_engine.py       # Sentence transformers
│   ├── budget_enrichment_engine.py # URL scraping for budgets
│   └── credit_monitor.py         # Apify credit tracking
├── models/                       # Data models
│   ├── lead.py                   # Lead data class
│   ├── filter_criteria.py        # Search filters
│   └── system_config.py          # System configuration
└── utils/                        # Utilities
    ├── currency_converter.py     # Multi-currency support
    ├── date_parser.py            # Date parsing
    └── validation.py             # Input validation
```

## Technology Stack

### Backend
- **Python 3.12**: Core language
- **FastAPI**: Web framework
- **PostgreSQL**: Database
- **SQLAlchemy**: ORM
- **Pydantic**: Data validation
- **sentence-transformers**: AI embeddings
- **aiohttp**: Async HTTP client
- **BeautifulSoup4**: HTML parsing

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool
- **TailwindCSS**: Styling
- **Axios**: HTTP client

### Infrastructure
- **Apify**: Web scraping platform
- **Docker**: Containerization (optional)
- **Nginx**: Reverse proxy (production)

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                              │
│                                                                 │
│  ┌──────────────┐                                              │
│  │   Nginx      │  ← HTTPS (443)                               │
│  │  Reverse     │                                              │
│  │   Proxy      │                                              │
│  └──────┬───────┘                                              │
│         │                                                       │
│    ┌────┴────┐                                                 │
│    │         │                                                 │
│    ▼         ▼                                                 │
│  ┌────┐   ┌────────┐                                          │
│  │React│   │FastAPI │                                          │
│  │ App │   │Backend │                                          │
│  │:80  │   │ :8000  │                                          │
│  └─────┘   └───┬────┘                                          │
│                │                                                │
│                ▼                                                │
│         ┌──────────────┐                                       │
│         │ PostgreSQL   │                                       │
│         │   :5432      │                                       │
│         └──────────────┘                                       │
│                                                                 │
│  External Services:                                            │
│  - Apify (scraping)                                           │
│  - HuggingFace (AI models)                                    │
└─────────────────────────────────────────────────────────────────┘
```

