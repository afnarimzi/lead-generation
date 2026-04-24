-- Freelance Lead Scraper Database Schema
-- This schema defines the leads table with all required fields and indexes

-- Enable pg_trgm extension for similarity searches
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create leads table
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    job_title VARCHAR(500) NOT NULL,
    job_description TEXT NOT NULL,
    platform_name VARCHAR(50) NOT NULL,
    budget_amount DECIMAL(10, 2),
    payment_type VARCHAR(20),
    client_info JSONB,
    job_url VARCHAR(1000) UNIQUE NOT NULL,
    posted_datetime TIMESTAMP NOT NULL,
    skills_tags TEXT[],
    quality_score DECIMAL(5, 2) DEFAULT 0.0,
    is_potential_duplicate BOOLEAN DEFAULT FALSE,
    is_favorited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index on platform_name for filtering by platform
CREATE INDEX IF NOT EXISTS idx_leads_platform ON leads(platform_name);

-- Index on posted_datetime for date range queries and sorting by recency
CREATE INDEX IF NOT EXISTS idx_leads_posted_datetime ON leads(posted_datetime DESC);

-- Index on budget_amount for budget range filtering
CREATE INDEX IF NOT EXISTS idx_leads_budget ON leads(budget_amount);

-- Index on quality_score for sorting by quality
CREATE INDEX IF NOT EXISTS idx_leads_quality_score ON leads(quality_score DESC);

-- Index on job_url for duplicate detection
CREATE INDEX IF NOT EXISTS idx_leads_job_url ON leads(job_url);

-- Full-text search index on job_title and job_description for keyword searches
CREATE INDEX IF NOT EXISTS idx_leads_fulltext ON leads 
    USING GIN(to_tsvector('english', job_title || ' ' || job_description));

-- Similarity search index on job_title for cross-platform duplicate detection
CREATE INDEX IF NOT EXISTS idx_leads_title_similarity ON leads 
    USING GIN(job_title gin_trgm_ops);

-- Index on is_favorited for filtering favorite leads
CREATE INDEX IF NOT EXISTS idx_leads_is_favorited ON leads(is_favorited) WHERE is_favorited = TRUE;
