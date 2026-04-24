import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getLeads, exportLeads, toggleFavorite } from '../api/leads';
import { LeadSummary, SearchFilters } from '../types/lead';

export default function Leads() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [leads, setLeads] = useState<LeadSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const page = parseInt(searchParams.get('page') || '1');
  const keywords = searchParams.get('keywords') || '';
  const platforms = searchParams.get('platforms') || '';

  const filters: SearchFilters = {
    keywords: keywords ? keywords.split(',') : undefined,
    platforms: platforms ? platforms.split(',') : undefined,
  };

  useEffect(() => {
    loadLeads();
  }, [page, keywords, platforms]);

  async function loadLeads() {
    try {
      setLoading(true);
      const data = await getLeads(filters, page, 20);
      setLeads(data.leads);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leads');
    } finally {
      setLoading(false);
    }
  }

  async function handleExport(format: 'csv' | 'json') {
    try {
      setExporting(true);
      const blob = await exportLeads(format, filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `leads_export.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Export failed: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setExporting(false);
    }
  }

  async function handleToggleFavorite(leadId: number, event: React.MouseEvent) {
    event.preventDefault(); // Prevent navigation
    event.stopPropagation();
    try {
      const result = await toggleFavorite(leadId);
      // Update the lead in the list
      setLeads(leads.map(lead => 
        lead.id === leadId ? { ...lead, is_favorited: result.is_favorited } : lead
      ));
    } catch (err) {
      alert('Failed to update favorite: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  }

  function formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }

  if (loading) {
    return <div className="text-center py-12">Loading leads...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <button onClick={loadLeads} className="mt-2 text-red-600 hover:text-red-800 underline">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Leads</h1>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            disabled={exporting}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
          >
            Export CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={exporting}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            Export JSON
          </button>
        </div>
      </div>

      <div className="text-gray-600">
        Showing {leads.length} of {total} leads
      </div>

      {/* Leads List */}
      <div className="space-y-4">
        {leads.map((lead) => (
          <div key={lead.id} className="block bg-white rounded-lg shadow hover:shadow-md transition p-6">
            <div className="flex justify-between items-start">
              <Link to={`/leads/${lead.id}`} className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 hover:text-blue-600">{lead.job_title}</h3>
                <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                  <span className="font-medium">{lead.platform}</span>
                  <span>⭐ {lead.quality_score.toFixed(1)}</span>
                  {lead.budget_amount && (
                    <span>💰 ${lead.budget_amount.toLocaleString()}</span>
                  )}
                  <span>📅 {formatDate(lead.posted_datetime)}</span>
                </div>
              </Link>
              <button
                onClick={(e) => handleToggleFavorite(lead.id, e)}
                className="ml-4 text-2xl hover:scale-110 transition"
                title={lead.is_favorited ? "Remove from favorites" : "Add to favorites"}
              >
                {lead.is_favorited ? '⭐' : '☆'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setSearchParams({ ...Object.fromEntries(searchParams), page: String(page - 1) })}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button
            onClick={() => setSearchParams({ ...Object.fromEntries(searchParams), page: String(page + 1) })}
            disabled={page >= Math.ceil(total / 20)}
            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
