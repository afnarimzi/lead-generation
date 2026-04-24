import { fetchApi } from './client';
import { SearchFilters } from '../types/lead';

export interface SearchStatusResponse {
  is_running: boolean;
  message: string;
  started_at?: string;
  completed_at?: string;
}

export async function startSearch(filters: SearchFilters): Promise<{ status: string; message: string }> {
  return fetchApi('/api/search/start', {
    method: 'POST',
    body: JSON.stringify({
      keywords: filters.keywords || [],
      platforms: filters.platforms || ['Upwork', 'Freelancer', 'PeoplePerHour'],
      posted_within_hours: filters.postedWithinHours || 168,
      min_quality_score: filters.minQualityScore || 0,
      max_results_per_platform: filters.maxResultsPerPlatform || 20,
    }),
  });
}

export async function getSearchStatus(): Promise<SearchStatusResponse> {
  return fetchApi<SearchStatusResponse>('/api/search/status');
}

export async function getSearchResults(
  page: number = 1,
  pageSize: number = 20,
  keywords?: string
): Promise<{
  leads: any[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  search_timestamp: string;
  message: string;
}> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  
  if (keywords) {
    params.append('keywords', keywords);
  }
  
  return fetchApi(`/api/search/results?${params.toString()}`);
}
