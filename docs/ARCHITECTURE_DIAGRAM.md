# Visual Architecture Diagrams

## System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    LEAD GENERATION SYSTEM                       │
│                  https://leadgeneration-dun.vercel.app          │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│                     React + TypeScript                          │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Search    │  │    Leads    │  │   My Jobs   │            │
│  │    Page     │  │   Results   │  │ (Favorites) │            │
│  │             │  │             │  │             │            │
│  │ • Keywords  │  │ • Quality   │  │ • Starred   │            │
│  │ • Filters   │  │   Scores    │  │   Jobs      │            │
│  │ • Real-time │  │ • Star      │  │ • Export    │            │
│  │   Status    │  │   System    │  │   Options   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
│                   Serverless Functions                          │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Search    │  │    Leads    │  │   Cleanup   │            │
│  │   Router    │  │   Router    │  │   Router    │            │
│  │             │  │             │  │             │            │
│  │ • Start     │  │ • List      │  │ • Manual    │            │
│  │ • Status    │  │ • Favorite  │  │   Reset     │            │
│  │ • Results   │  │ • Export    │  │ • Auto      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR ENGINE                          │
│                  Workflow Coordinator                           │
│                                                                 │
│  Step 0: Auto-Cleanup → Step 1: Credit Check                   │
│  Step 2: Parallel Scraping → Step 3: AI Processing             │
│  Step 4: Database Storage → Step 5: Return Results             │
└─────────────────────────────────────────────────────────────────┘