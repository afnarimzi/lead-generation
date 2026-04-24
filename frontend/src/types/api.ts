import { LeadSummary } from './lead';

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface DashboardStats {
  total_leads: number;
  leads_by_platform: Record<string, number>;
  leads_last_24h: number;
  leads_last_7d: number;
}

export interface LeadsListResponse {
  leads: LeadSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SearchStatus {
  is_running: boolean;
  current_platform?: string;
  progress?: number;
  message?: string;
}

export interface ConfigData {
  apify_token: string;
  platforms: string[];
  has_auth: Record<string, boolean>;
}
