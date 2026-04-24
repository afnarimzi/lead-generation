import { useEffect, useState } from 'react';
import { getFavoriteLeads, toggleFavorite, getLeadById } from '../api/leads';
import { LeadSummary, LeadDetail } from '../types/lead';

export default function MyJobs() {
  const [leads, setLeads] = useState<LeadSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  
  // Expanded lead detail
  const [expandedLeadId, setExpandedLeadId] = useState<number | null>(null);
  const [expandedLead, setExpandedLead] = useState<LeadDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    loadFavorites();
  }, [page]);

  async function loadFavorites() {
    try {
      setLoading(true);
      const data = await getFavoriteLeads(page, 20);
      setLeads(data.leads);
      setTotal(data.total);
      setTotalPages(data.total_pages);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load favorites');
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleFavorite(leadId: number) {
    try {
      await toggleFavorite(leadId);
      // Remove from list after unfavoriting
      setLeads(leads.filter(lead => lead.id !== leadId));
      setTotal(total - 1);
      if (expandedLeadId === leadId) {
        setExpandedLeadId(null);
        setExpandedLead(null);
      }
    } catch (err) {
      alert('Failed to update favorite: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  }

  async function toggleLeadDetail(leadId: number) {
    if (expandedLeadId === leadId) {
      setExpandedLeadId(null);
      setExpandedLead(null);
      return;
    }

    try {
      setLoadingDetail(true);
      setExpandedLeadId(leadId);
      const detail = await getLeadById(leadId);
      setExpandedLead(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lead details');
      setExpandedLeadId(null);
    } finally {
      setLoadingDetail(false);
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
    const diffWeeks = Math.floor(diffDays / 7);
    if (diffDays < 30) return `${diffWeeks}w ago`;
    return date.toLocaleDateString();
  }

  if (loading) {
    return <div className="text-center py-12">Loading your favorite jobs...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <button onClick={loadFavorites} className="mt-2 text-red-600 hover:text-red-800 underline">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">⭐ My Jobs</h1>
          <p className="text-gray-600 mt-2">Your favorited job opportunities</p>
        </div>
      </div>

      {leads.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-6xl mb-4">⭐</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No favorites yet</h2>
          <p className="text-gray-600 mb-6">
            Start adding jobs to your favorites by clicking the star icon on any lead
          </p>
        </div>
      ) : (
        <>
          <div className="text-gray-600">
            {total} favorite {total === 1 ? 'job' : 'jobs'}
          </div>

          {/* Leads List */}
          <div className="space-y-3">
            {leads.map((lead) => (
              <div key={lead.id} className="border border-gray-200 rounded-lg bg-white">
                {/* Lead Summary */}
                <div
                  onClick={() => toggleLeadDetail(lead.id)}
                  className="p-4 cursor-pointer hover:bg-gray-50 transition"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900">{lead.job_title}</h3>
                      <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                        <span className="font-medium">{lead.platform}</span>
                        <span>⭐ {lead.quality_score.toFixed(1)}</span>
                        {lead.budget_amount && (
                          <span>💰 ${lead.budget_amount.toLocaleString()}</span>
                        )}
                        <span>📅 {formatDate(lead.posted_datetime)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleFavorite(lead.id);
                        }}
                        className="text-2xl hover:scale-110 transition"
                        title="Remove from favorites"
                      >
                        ⭐
                      </button>
                      <button className="text-blue-600 hover:text-blue-800">
                        {expandedLeadId === lead.id ? '▼ Hide' : '▶ Details'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Lead Detail */}
                {expandedLeadId === lead.id && (
                  <div className="border-t border-gray-200 p-4 bg-gray-50">
                    {loadingDetail && (
                      <div className="text-center py-4 text-gray-600">Loading details...</div>
                    )}

                    {expandedLead && (
                      <div className="space-y-4">
                        {/* Description */}
                        <div>
                          <h4 className="font-semibold text-gray-900 mb-2">Description</h4>
                          <p className="text-gray-700 whitespace-pre-wrap">{expandedLead.job_description}</p>
                        </div>

                        {/* Skills */}
                        {expandedLead.skills_tags && expandedLead.skills_tags.length > 0 && (
                          <div>
                            <h4 className="font-semibold text-gray-900 mb-2">Required Skills</h4>
                            <div className="flex flex-wrap gap-2">
                              {expandedLead.skills_tags.map((skill, index) => (
                                <span
                                  key={index}
                                  className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Client Info */}
                        {expandedLead.client_info && (
                          <div>
                            <h4 className="font-semibold text-gray-900 mb-2">Client Information</h4>
                            <div className="text-gray-700 text-sm">
                              {expandedLead.client_info.name && <div>Name: {expandedLead.client_info.name}</div>}
                              {expandedLead.client_info.rating && <div>Rating: {expandedLead.client_info.rating}/5</div>}
                              {expandedLead.client_info.location && <div>Location: {expandedLead.client_info.location}</div>}
                            </div>
                          </div>
                        )}

                        {/* Action Button */}
                        <div>
                          <a
                            href={expandedLead.job_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
                          >
                            View on {expandedLead.platform} →
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-6">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
              >
                Previous
              </button>
              <span className="px-4 py-2">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
