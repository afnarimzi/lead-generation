import { useState, useEffect } from 'react';
import { startSearch, getSearchStatus } from '../api/search';
import { toggleFavorite, getLeadById } from '../api/leads';
import { SearchFilters, LeadSummary, LeadDetail } from '../types/lead';

export default function Search() {
  const [keywords, setKeywords] = useState('');
  const [platforms, setPlatforms] = useState<string[]>(['Upwork', 'Freelancer', 'PeoplePerHour']);
  const [timeFilter, setTimeFilter] = useState<number>(168); // Default: 7 days (168 hours)
  const [searching, setSearching] = useState(false);
  const [status, setStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [leads, setLeads] = useState<LeadSummary[]>(() => {
    // Restore search results from sessionStorage
    const saved = sessionStorage.getItem('searchResults');
    return saved ? JSON.parse(saved) : [];
  });
  const [showResults, setShowResults] = useState(() => {
    // Show results if we have saved results
    const saved = sessionStorage.getItem('searchResults');
    return saved ? JSON.parse(saved).length > 0 : false;
  });
  
  // Expanded lead detail
  const [expandedLeadId, setExpandedLeadId] = useState<number | null>(null);
  const [expandedLead, setExpandedLead] = useState<LeadDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    let interval: number;
    if (searching) {
      interval = window.setInterval(async () => {
        try {
          console.log('Checking search status...');
          const statusData = await getSearchStatus();
          console.log('Status:', statusData);
          
          if (!statusData.is_running) {
            // Search finished - load results FIRST, then update UI
            console.log('Search finished, loading results...');
            
            // Check if search failed due to credits BEFORE loading results
            if (statusData.message && (
              statusData.message.includes('credit') || 
              statusData.message.includes('limit') || 
              statusData.message.includes('exhausted')
            )) {
              setSearching(false);  // Re-enable button
              setStatus(statusData.message);
              setError('Apify credits exhausted! Please update your APIFY_TOKEN with a new account or wait for monthly reset.');
              return;
            }
            
            // Load results FIRST - showResults will be set inside loadResults()
            try {
              await loadResults();
              // Only disable searching AFTER results are loaded successfully
              setSearching(false);  // This re-enables the button
            } catch (err) {
              // If loading results fails, still disable searching but show error
              setSearching(false);
              setError('Failed to load search results. Please try again.');
            }
          } else {
            // Search still running - show progress message with platform info
            // IMPORTANT: Do NOT set showResults=true here!
            if (statusData.message) {
              // Enhance the status message to be more informative
              let enhancedMessage = statusData.message;
              if (statusData.message.includes('Starting')) {
                enhancedMessage = '🔍 Scraping platforms: Upwork, Freelancer, PeoplePerHour...';
              } else if (statusData.message.includes('platform')) {
                enhancedMessage = `🔍 ${statusData.message}`;
              } else {
                enhancedMessage = `🔍 Scraping in progress: ${statusData.message}`;
              }
              setStatus(enhancedMessage);
            } else {
              setStatus('🔍 Scraping platforms for fresh leads...');
            }
          }
        } catch (err) {
          console.error('Failed to get status:', err);
          setSearching(false);  // Re-enable button on error
          setError('Failed to check search status. Please try again.');
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [searching]);

  async function loadResults() {
    try {
      console.log('Loading search results...');
      
      // Debug: Log the API URL being used
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://leadgeneration-dun.vercel.app';
      const apiUrl = `${API_BASE_URL}/api/search/results?page=1&page_size=50&posted_within_hours=${timeFilter}`;
      console.log('API URL:', apiUrl);
      console.log('Environment:', import.meta.env.MODE);
      console.log('VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL);
      console.log('Time filter:', timeFilter, 'hours');
      
      // RETRY LOGIC: Try multiple times to handle database timing issues
      let attempts = 0;
      const maxAttempts = 3;
      let data = null;
      
      while (attempts < maxAttempts) {
        attempts++;
        console.log(`Loading results attempt ${attempts}/${maxAttempts}...`);
        
        // Add small delay for database transaction to complete
        if (attempts > 1) {
          await new Promise(resolve => setTimeout(resolve, 2000)); // 2 second delay
        }
        
        const response = await fetch(apiUrl);
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Response error:', errorText);
          throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
        }
        
        data = await response.json();
        console.log(`Attempt ${attempts} - Found leads:`, data.leads?.length || 0);
        
        // If we found results, break out of retry loop
        if (data.leads && data.leads.length > 0) {
          console.log('✅ Found results, stopping retry loop');
          break;
        }
        
        // If this is the last attempt, accept whatever we got (even 0 results)
        if (attempts === maxAttempts) {
          console.log('⚠️ Max attempts reached, using final result');
          break;
        }
        
        console.log(`No results on attempt ${attempts}, retrying...`);
      }
      
      if (data && data.leads && Array.isArray(data.leads)) {
        console.log('Final result - Found leads:', data.leads.length);
        setLeads(data.leads);
        setShowResults(true);
        
        if (data.leads.length > 0) {
          setStatus(`✅ Search completed! Found ${data.leads.length} fresh leads.`);
          sessionStorage.setItem('searchResults', JSON.stringify(data.leads));
        } else {
          setStatus('⚠️ Search completed but no leads found. Try different keywords or platforms.');
          sessionStorage.removeItem('searchResults');
        }
      } else {
        console.error('Invalid response format:', data);
        throw new Error('Invalid response format - no leads array found');
      }
      
    } catch (err) {
      console.error('Failed to load results:', err);
      setError('Failed to load results: ' + (err instanceof Error ? err.message : 'Unknown error'));
      setStatus('❌ Failed to load search results.');
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    
    // IMMEDIATELY clear everything and prevent any "no results" messages
    setShowResults(false);  // Hide results section completely
    setLeads([]);           // Clear leads array
    setStatus('');          // Clear any previous status
    
    // Clear sessionStorage
    sessionStorage.removeItem('searchResults');

    const filters: SearchFilters = {
      keywords: keywords.split(',').map(k => k.trim()).filter(Boolean),
      platforms: platforms.length > 0 ? platforms : undefined,
      postedWithinHours: timeFilter,
      minQualityScore: 50,  // LOWERED: Allow basic filtering results (was 70)
      maxResultsPerPlatform: 20,
    };

    try {
      // Set searching FIRST - this prevents any "no results" from showing
      setSearching(true);
      setStatus('🚀 Starting search - scraping platforms...');
      
      // Start the search
      await startSearch(filters);
      // Polling will handle the rest
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start search');
      setSearching(false);  // Re-enable button only on error
      setStatus(''); // Clear status on error
    }
  }

  async function handleToggleFavorite(leadId: number, event: React.MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    try {
      const result = await toggleFavorite(leadId);
      const updatedLeads = leads.map(lead => 
        lead.id === leadId ? { ...lead, is_favorited: result.is_favorited } : lead
      );
      setLeads(updatedLeads);
      
      // Update sessionStorage with new favorite status
      sessionStorage.setItem('searchResults', JSON.stringify(updatedLeads));
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

  function togglePlatform(platform: string) {
    setPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Search for Leads</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* Keywords */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Keywords (comma-separated)
          </label>
          <input
            type="text"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter keywords (e.g., AI, Python, machine learning)"
            disabled={searching}
          />
        </div>

        {/* Time Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Posted Within
          </label>
          <select
            value={timeFilter}
            onChange={(e) => setTimeFilter(Number(e.target.value))}
            disabled={searching}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value={24}>Last 24 hours</option>
            <option value={72}>Last 3 days</option>
            <option value={168}>Last 7 days</option>
            <option value={336}>Last 14 days</option>
            <option value={720}>Last 30 days</option>
            <option value={2160}>Last 90 days</option>
          </select>
        </div>

        {/* Platforms */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Platforms
          </label>
          <div className="space-y-2">
            {['Upwork', 'Freelancer', 'PeoplePerHour'].map(platform => (
              <label key={platform} className="flex items-center">
                <input
                  type="checkbox"
                  checked={platforms.includes(platform)}
                  onChange={() => togglePlatform(platform)}
                  disabled={searching}
                  className="mr-2"
                />
                <span className="text-gray-700">{platform}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={searching}
          className={`w-full py-3 rounded-lg transition-all duration-200 ${
            searching 
              ? 'bg-gray-400 text-gray-600 cursor-not-allowed opacity-75 blur-sm' 
              : 'bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg'
          }`}
        >
          {searching ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-3"></div>
              Scraping Platforms...
            </div>
          ) : (
            'Start Search'
          )}
        </button>

        {/* Status Messages */}
        {status && (
          <div className={`rounded-lg p-4 ${
            status.includes('error') || status.includes('failed') 
              ? 'bg-red-50 border border-red-200' 
              : status.includes('complete') || status.includes('Found')
              ? 'bg-green-50 border border-green-200'
              : 'bg-blue-50 border border-blue-200'
          }`}>
            {searching && (
              <div className="flex items-center mb-2">
                <div className="animate-spin inline-block w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full mr-3"></div>
                <span className="text-blue-800 font-medium">Scraping in progress...</span>
              </div>
            )}
            <p className={
              status.includes('error') || status.includes('failed')
                ? 'text-red-800'
                : status.includes('complete') || status.includes('Found')
                ? 'text-green-800'
                : 'text-blue-800'
            }>{status}</p>
          </div>
        )}

        {/* Show "Ready to search" ONLY when no status, not searching, and no previous results */}
        {!status && !searching && !showResults && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-gray-600">Ready to search for leads. Enter keywords and click "Start Search".</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}
      </form>

      {/* Search Results - ONLY show when search is COMPLETELY finished and we have results */}
      {!searching && showResults && leads.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-gray-900">
            Search Results ({leads.length} leads)
          </h2>
          
          <div className="space-y-3">
            {leads.map((lead) => (
              <div key={lead.id} className="bg-white rounded-lg shadow hover:shadow-md transition p-4">
                <div className="flex justify-between items-start">
                  <div 
                    className="flex-1 cursor-pointer"
                    onClick={() => toggleLeadDetail(lead.id)}
                  >
                    <h3 className="text-lg font-semibold text-gray-900 hover:text-blue-600">
                      {lead.job_title}
                    </h3>
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
                      onClick={(e) => handleToggleFavorite(lead.id, e)}
                      className="text-2xl hover:scale-110 transition"
                      title={lead.is_favorited ? "Remove from favorites" : "Add to favorites"}
                    >
                      {lead.is_favorited ? '⭐' : '☆'}
                    </button>
                    <button
                      onClick={() => toggleLeadDetail(lead.id)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      {expandedLeadId === lead.id ? '▼ Hide' : '▶ Details'}
                    </button>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedLeadId === lead.id && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
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
        </div>
      )}

      {/* No results message - ONLY show when search is COMPLETELY finished, not searching, and no results */}
      {!searching && showResults && leads.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800">Search completed but no leads found. Try different keywords or platforms.</p>
        </div>
      )}
    </div>
  );
}
