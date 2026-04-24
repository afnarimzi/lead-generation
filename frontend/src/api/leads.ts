import { fetchApi } from './client';
import { DashboardStats, LeadsListResponse } from '../types/api';
import { LeadDetail, SearchFilters } from '../types/lead';

export async function getStats(): Promise<DashboardStats> {
  return fetchApi<DashboardStats>('/api/stats');
}

export async function getLeads(
  filters: SearchFilters,
  page: number = 1,
  pageSize: number = 20
): Promise<LeadsListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  if (filters.keywords && filters.keywords.length > 0) {
    params.append('keywords', filters.keywords.join(','));
  }
  if (filters.platforms && filters.platforms.length > 0) {
    params.append('platforms', filters.platforms.join(','));
  }
  if (filters.minBudget !== undefined) {
    params.append('min_budget', filters.minBudget.toString());
  }
  if (filters.maxBudget !== undefined) {
    params.append('max_budget', filters.maxBudget.toString());
  }
  if (filters.postedWithinHours !== undefined) {
    // Calculate the date threshold
    const hoursAgo = new Date();
    hoursAgo.setHours(hoursAgo.getHours() - filters.postedWithinHours);
    params.append('posted_after', hoursAgo.toISOString());
  }
  if (filters.recentOnly) {
    params.append('recent_only', 'true');
  }

  return fetchApi<LeadsListResponse>(`/api/leads?${params}`);
}

export async function getLeadById(id: number): Promise<LeadDetail> {
  return fetchApi<LeadDetail>(`/api/leads/${id}`);
}

export async function exportLeads(format: 'csv' | 'json', filters: SearchFilters): Promise<Blob> {
  const params = new URLSearchParams({ format });

  if (filters.keywords && filters.keywords.length > 0) {
    params.append('keywords', filters.keywords.join(','));
  }
  if (filters.platforms && filters.platforms.length > 0) {
    params.append('platforms', filters.platforms.join(','));
  }
  if (filters.minBudget !== undefined) {
    params.append('min_budget', filters.minBudget.toString());
  }
  if (filters.maxBudget !== undefined) {
    params.append('max_budget', filters.maxBudget.toString());
  }

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
    (import.meta.env.PROD ? 'https://leadgeneration-dun.vercel.app' : 'http://localhost:8000');
  
  const response = await fetch(`${API_BASE_URL}/api/export?${params}`);
  if (!response.ok) {
    throw new Error('Export failed');
  }
  return response.blob();
}


export async function toggleFavorite(leadId: number): Promise<{ id: number; is_favorited: boolean; message: string }> {
  return fetchApi(`/api/leads/${leadId}/favorite`, {
    method: 'POST',
  });
}

export async function getFavoriteLeads(page: number = 1, pageSize: number = 20): Promise<LeadsListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  return fetchApi<LeadsListResponse>(`/api/leads/favorites/list?${params}`);
}
