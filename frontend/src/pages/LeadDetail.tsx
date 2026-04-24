import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getLeadById } from '../api/leads';
import { LeadDetail as LeadDetailType } from '../types/lead';

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const [lead, setLead] = useState<LeadDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadLead(parseInt(id));
    }
  }, [id]);

  async function loadLead(leadId: number) {
    try {
      setLoading(true);
      const data = await getLeadById(leadId);
      setLead(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lead');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading lead details...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <Link to="/leads" className="mt-2 text-blue-600 hover:text-blue-800 underline">
          Back to Leads
        </Link>
      </div>
    );
  }

  if (!lead) return null;

  return (
    <div className="space-y-6">
      <Link to="/leads" className="text-blue-600 hover:text-blue-800">
        ← Back to Leads
      </Link>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{lead.job_title}</h1>
          <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
            <span className="font-medium">{lead.platform}</span>
            <span>⭐ Quality Score: {lead.quality_score.toFixed(1)}/100</span>
          </div>
        </div>

        {/* Budget & Details */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {lead.budget_amount && (
            <div>
              <div className="text-sm text-gray-600">Budget</div>
              <div className="text-lg font-semibold text-gray-900">
                ${lead.budget_amount.toLocaleString()}
              </div>
            </div>
          )}
          {lead.payment_type && (
            <div>
              <div className="text-sm text-gray-600">Payment Type</div>
              <div className="text-lg font-semibold text-gray-900">{lead.payment_type}</div>
            </div>
          )}
          <div>
            <div className="text-sm text-gray-600">Posted</div>
            <div className="text-lg font-semibold text-gray-900">
              {new Date(lead.posted_datetime).toLocaleDateString()}
            </div>
          </div>
        </div>

        {/* Description */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Description</h2>
          <p className="text-gray-700 whitespace-pre-wrap">{lead.job_description}</p>
        </div>

        {/* Skills */}
        {lead.skills_tags && lead.skills_tags.length > 0 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Required Skills</h2>
            <div className="flex flex-wrap gap-2">
              {lead.skills_tags.map((skill, index) => (
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
        {lead.client_info && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Client Information</h2>
            <div className="text-gray-700">
              {lead.client_info.name && <div>Name: {lead.client_info.name}</div>}
              {lead.client_info.rating && <div>Rating: {lead.client_info.rating}/5</div>}
              {lead.client_info.location && <div>Location: {lead.client_info.location}</div>}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4">
          <a
            href={lead.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
          >
            View on {lead.platform} →
          </a>
        </div>
      </div>
    </div>
  );
}
