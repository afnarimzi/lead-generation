# Lead Generation - AI-Powered Freelance Lead Generator

An intelligent lead generation system that scrapes freelance platforms and uses AI semantic matching to find the most relevant opportunities.

##  Key Features

- **Multi-Platform Scraping**: Upwork, Freelancer, PeoplePerHour (3 active platforms)
- **AI Semantic Matching**: Understands meaning, not just keywords (sentence-transformers)
- **Smart Ranking**: 40% relevance + 30% budget + 20% quality + 10% recency
- **Budget Enrichment**: Automatically scrapes missing budgets from job URLs
- **Favorites System**: Star jobs to save permanently across searches
- **Auto-Cleanup**: Fresh results every search, starred jobs preserved
- **Time Filters**: 24h, 3d, 7d, 14d, 30d, 90d posting timeframes
- **Real-time Search**: Live scraping with progress updates
- **Export Options**: CSV and JSON export

##  Quick Start

### Prerequisites
```bash
Python 3.12+, Node.js 16+, PostgreSQL 13+, Apify Account
```

### Installation
```bash
# Clone repository
git clone https://github.com/afnarimzi/lead-generation.git
cd lead-generation

# Backend setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
python backend/scripts/init_database.py

# Configure environment
cd backend
cp .env.example .env
# Edit .env with your credentials
cd ..

# Frontend setup
cd frontend
npm install
cp .env.example .env
cd ..
```

### Run
```bash
# Terminal 1: Backend
cd backend
bash start.sh

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Access
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs

##  How It Works

### 1. Search Flow
```
User Query → Auto-Cleanup → Credit Check → Parallel Scraping (3 platforms)
→ Normalize → Deduplicate → Quality Score → AI Filter
→ Rank → Budget Enrichment → Final Rank → Display
```

### 2. AI Semantic Matching
- **Model**: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
- **Threshold**: 0.15 similarity score (more permissive)
- **Process**: Query + Jobs → Embeddings → Cosine Similarity → Filter

### 3. Hybrid Scoring (Updated Weights)
```python
final_score = (
    0.4 × embedding_similarity +  # How relevant?
    0.3 × budget_score +          # Budget importance increased
    0.2 × quality_score +         # How good?
    0.1 × recency_score           # How recent?
)
```

### 4. Budget Enrichment
- Visits job URLs for top 50 results
- Scrapes missing budget data
- Updates scores with real budget info
- Caches results to avoid re-scraping

### 5. Favorites System
- **Star jobs** to save permanently
- **Auto-cleanup** removes non-starred jobs before each search
- **My Jobs** page shows all starred jobs
- **Persistent storage** across sessions

##  Architecture

```
React UI → FastAPI → Orchestrator → [Upwork, Freelancer, PeoplePerHour]
                                  → AI Engines → PostgreSQL
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed diagrams.


##  Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/leadgen

# Apify
APIFY_TOKEN=your_token
APIFY_UPWORK_ACTOR_ID=flash_mage~upwork
APIFY_FREELANCER_ACTOR_ID=janbruinier~jan-freelancer-job-scraper
APIFY_PEOPLEPERHOUR_ACTOR_ID=getdataforme~peopleperhour-job-scraper

# Scraping Defaults
DEFAULT_MAX_RESULTS=30

# AI (Optional)
HF_TOKEN=your_huggingface_token
```

### AI Model Settings
```python
# Updated scoring weights
similarity_threshold=0.15         # More permissive filtering
embedding_weight=0.4              # 40% weight on relevance
budget_weight=0.3                 # 30% weight on budget (increased)
quality_weight=0.2                # 20% weight on quality
recency_weight=0.1                # 10% weight on recency
```

##  User Interface

### Search Page
- **Keywords**: Comma-separated search terms
- **Time Filter**: 24h, 3d, 7d, 14d, 30d, 90d options
- **Platform Selection**: Choose Upwork, Freelancer, PeoplePerHour
- **Real-time Status**: Live search progress updates

### Results Display
- **Smart Ranking**: AI-powered relevance scoring
- **Star System**: Click ☆/⭐ to favorite jobs
- **Expandable Details**: Click for full job description
- **Budget Display**: Shows estimated or actual budgets
- **Time Display**: Relative time (2h ago, 3d ago)

### My Jobs Page
- **Starred Jobs**: All favorited jobs across searches
- **Persistent Storage**: Jobs saved permanently
- **Same Interface**: Expandable details and direct links

##  Project Structure

```
lead-generation/
├── backend/              # Python backend
│   ├── api/             # FastAPI routes
│   │   ├── main.py      # App initialization
│   │   ├── models.py    # Pydantic models
│   │   └── routers/     # API endpoints
│   ├── lead_scraper/    # Core engine
│   │   ├── orchestrator.py      # Main workflow
│   │   ├── adapters/            # Platform scrapers
│   │   ├── engines/             # Processing engines
│   │   ├── models/              # Data models
│   │   └── utils/               # Utilities
│   ├── scripts/         # Database & utility scripts
│   ├── tests/           # Backend tests
│   └── start.sh         # Start script
├── frontend/            # React frontend
│   ├── src/
│   │   ├── pages/       # UI components
│   │   │   ├── Search.tsx       # Search interface
│   │   │   ├── Leads.tsx        # Results display
│   │   │   └── MyJobs.tsx       # Favorites page
│   │   ├── api/         # API clients
│   │   └── types/       # TypeScript types
│   └── package.json
├── docs/                # Documentation
│   ├── ARCHITECTURE.md  # System design
│   └── DOCUMENTATION.md # Technical guide
├── .gitignore
└── README.md
```

##  Recent Updates

### Version 2.0 Features
- ✅ **Favorites System**: Star jobs to save permanently
- ✅ **Auto-Cleanup**: Fresh results every search
- ✅ **Time Filters**: Flexible posting date filters
- ✅ **Improved Scoring**: Budget weight increased to 30%
- ✅ **Better Freelancer Support**: Fixed janbruinier actor integration
- ✅ **Enhanced UI**: My Jobs page, expandable details
- ✅ **Increased Capacity**: 30 results per platform (90 total)

##  Use Cases

- **Freelancers**: Find relevant projects matching your skills
- **Agencies**: Monitor market opportunities and trends  
- **Researchers**: Collect data for market analysis
- **Job Seekers**: Track high-budget opportunities with favorites
