export interface LeadSummary {
  id: number;
  job_title: string;
  platform: string;
  quality_score: number;
  budget_amount?: number;
  payment_type?: string;
  posted_datetime: string;
  is_favorited?: boolean;
}

export interface LeadDetail extends LeadSummary {
  job_description: string;
  client_info?: {
    name?: string;
    rating?: number;
    total_spent?: number;
    location?: string;
  };
  job_url: string;
  skills_tags: string[];
  is_potential_duplicate: boolean;
  created_at: string;
}

export interface SearchFilters {
  keywords?: string[];
  platforms?: string[];
  minBudget?: number;
  maxBudget?: number;
  postedWithinHours?: number;
  minQualityScore?: number;
  maxResultsPerPlatform?: number;
  recentOnly?: boolean;
}
