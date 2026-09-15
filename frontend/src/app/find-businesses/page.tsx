'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { 
  Building2, 
  Search, 
  MapPin, 
  Download, 
  RefreshCw, 
  Filter, 
  Phone, 
  Globe, 
  Mail, 
  Star, 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Layers,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { 
  findBusinesses, 
  fetchSearchResults, 
  fetchJobStatus, 
  triggerCampaignExportXlsx,
  SearchResultsResponse,
  PipelineJobStatus 
} from '@/lib/api';

const CATEGORY_SUGGESTIONS = ['Restaurants', 'Dentists', 'Hotels', 'Gyms', 'Real Estate Agencies', 'Salons', 'Clinics'];
const LOCATION_SUGGESTIONS = ['Mumbai', 'Delhi', 'Bangalore', 'Pune', 'Hyderabad', 'Chennai'];
const QUANTITY_OPTIONS = [100, 500, 1000, 5000, 10000];

export default function FindBusinessesPage() {
  const [what, setWhat] = useState('Restaurants');
  const [where, setWhere] = useState('Mumbai');
  const [quantity, setQuantity] = useState(100);
  const [provider, setProvider] = useState('osm');

  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<PipelineJobStatus | null>(null);
  const [results, setResults] = useState<SearchResultsResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Table State
  const [tableSearch, setTableSearch] = useState('');
  const [contactableOnly, setContactableOnly] = useState(false);
  const [page, setPage] = useState(1);

  const handleStartSearch = async () => {
    if (!what.trim() || !where.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    setCampaignId(null);
    setJobId(null);

    try {
      const res = await findBusinesses({
        category: what.trim(),
        location: where.trim(),
        quantity: quantity,
        provider: provider
      });

      setCampaignId(res.campaign_id);
      setJobId(res.job_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Search failed to initialize');
      setLoading(false);
    }
  };

  // Poll Job Status
  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const statusData = await fetchJobStatus(jobId);
        setJobStatus(statusData);

        const isGoogle = ['google', 'google_places'].includes((provider || '').toLowerCase());
        const discoveryDone = isGoogle && statusData.stage_progress?.DEDUPLICATION === 100;

        if (statusData.job_status === 'COMPLETED' || statusData.job_status === 'FAILED' || statusData.job_status === 'CANCELLED' || discoveryDone) {
          clearInterval(interval);
          setLoading(false);
          if (campaignId) {
            loadResults(campaignId, 1);
          }
        }
      } catch (e) {
        console.error('Job polling error:', e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [jobId, campaignId, provider]);

  const loadResults = useCallback(async (cId: string, pageNum: number) => {
    try {
      const data = await fetchSearchResults(cId, {
        page: pageNum,
        limit: 50,
        search: tableSearch.trim() || undefined,
        contactable_only: contactableOnly
      });
      setResults(data);
    } catch (err: unknown) {
      console.error('Failed to load results:', err);
    }
  }, [tableSearch, contactableOnly]);

  useEffect(() => {
    if (campaignId && !loading) {
      loadResults(campaignId, page);
    }
  }, [campaignId, page, loading, loadResults]);

  const handleExportXlsx = async () => {
    if (!campaignId) return;
    setExporting(true);
    try {
      const blob = await triggerCampaignExportXlsx(campaignId, { contactable_only: contactableOnly });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LeadOS_${what}_in_${where}_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: unknown) {
      alert('Export failed: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header Navigation */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center space-x-3">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
                <Building2 className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-slate-400">
                LEAD<span className="text-blue-500 font-extrabold">os</span>
              </span>
            </Link>

            <nav className="hidden md:flex items-center space-x-1">
              <Link href="/" className="px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800/50 transition">
                Dashboard
              </Link>
              <Link href="/find-businesses" className="px-3 py-2 rounded-lg text-sm font-medium bg-blue-600/10 text-blue-400 border border-blue-500/20">
                Find Businesses
              </Link>
              <Link href="/campaigns" className="px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800/50 transition">
                Campaigns
              </Link>
            </nav>
          </div>

          <div className="flex items-center space-x-3">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>
              Live Data Finder Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Search Hero Card */}
        <div className="relative rounded-2xl bg-gradient-to-b from-slate-900 via-slate-900/90 to-slate-950 border border-slate-800/80 p-6 sm:p-8 shadow-2xl overflow-hidden">
          <div className="absolute top-0 right-0 -mt-12 -mr-12 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>
          
          <div className="relative z-10 space-y-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs font-semibold text-blue-400 mb-3">
                <Sparkles className="h-3.5 w-3.5" />
                AUTOMATED BUSINESS DATA COLLECTION
              </div>
              <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
                Find Real Business Leads Fast
              </h1>
              <p className="text-slate-400 text-sm sm:text-base mt-1 max-w-2xl">
                Enter your target industry and location to collect clean, deduplicated business contacts, websites, ratings, and locations.
              </p>
            </div>

            {/* Quick Search Inputs */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 bg-slate-950/80 p-4 rounded-xl border border-slate-800">
              {/* WHAT */}
              <div className="md:col-span-4 space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5 text-blue-400" /> What Businesses?
                </label>
                <input 
                  type="text"
                  value={what}
                  onChange={(e) => setWhat(e.target.value)}
                  placeholder="e.g. Restaurants, Dentists, Hotels..."
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3.5 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition text-sm font-medium"
                />
              </div>

              {/* WHERE */}
              <div className="md:col-span-4 space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-emerald-400" /> Where?
                </label>
                <input 
                  type="text"
                  value={where}
                  onChange={(e) => setWhere(e.target.value)}
                  placeholder="e.g. Mumbai, Delhi, Bandra..."
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3.5 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition text-sm font-medium"
                />
              </div>

              {/* HOW MANY */}
              <div className="md:col-span-4 space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-purple-400" /> How Many Leads?
                </label>
                <div className="flex items-center gap-1 bg-slate-900 p-1 border border-slate-700/80 rounded-lg">
                  {QUANTITY_OPTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => setQuantity(q)}
                      className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition ${
                        quantity === q
                          ? 'bg-blue-600 text-white shadow-sm'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      {q >= 1000 ? `${q / 1000}k` : q}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Quick Suggestions & Submit */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-500 font-medium">Try searching:</span>
                {CATEGORY_SUGGESTIONS.slice(0, 4).map((c) => (
                  <button
                    key={c}
                    onClick={() => setWhat(c)}
                    className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800/80 text-slate-300 hover:bg-slate-700 hover:text-white transition border border-slate-700/50"
                  >
                    {c}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg px-3 py-2.5 font-medium focus:outline-none"
                >
                  <option value="google">Google Places API (Official)</option>
                  <option value="osm">OpenStreetMap Places API (Live)</option>
                  <option value="mock">Mock Provider (Offline Test)</option>
                </select>

                <button
                  onClick={handleStartSearch}
                  disabled={loading || !what.trim() || !where.trim()}
                  className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-blue-600/30 flex items-center justify-center gap-2 transition disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      Collecting Data...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4" />
                      GET BUSINESS DATA
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Progress Tracker Card */}
        {loading && (
          <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4 shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-blue-400" />
                  Collecting Business Data ({what} in {where})
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Current Stage: <span className="font-semibold text-blue-400">{jobStatus?.current_stage || 'DISCOVERY'}</span>
                </p>
              </div>
              <span className="text-xl font-bold text-blue-400">
                {Math.round(jobStatus?.progress_percent || 15)}%
              </span>
            </div>

            {/* Multi-Bar Progress */}
            <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
              <div 
                className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full transition-all duration-500 rounded-full"
                style={{ width: `${Math.max(10, Math.min(100, jobStatus?.progress_percent || 15))}%` }}
              ></div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center pt-2">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                <div className="text-xs text-slate-400 font-medium">Requested</div>
                <div className="text-lg font-bold text-white mt-0.5">{quantity}</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                <div className="text-xs text-slate-400 font-medium">Discovered</div>
                <div className="text-lg font-bold text-blue-400 mt-0.5">{jobStatus?.processed_records || 0}</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                <div className="text-xs text-slate-400 font-medium">Successful</div>
                <div className="text-lg font-bold text-emerald-400 mt-0.5">{jobStatus?.successful_records || 0}</div>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                <div className="text-xs text-slate-400 font-medium">Duplicates Removed</div>
                <div className="text-lg font-bold text-purple-400 mt-0.5">{jobStatus?.failed_records || 0}</div>
              </div>
            </div>
          </div>
        )}

        {/* Results Overview & Table */}
        {results && (
          <div className="space-y-6">
            
            {/* Data Quality Header Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs text-slate-400 font-medium">Total Unique Leads</div>
                <div className="text-2xl font-extrabold text-white mt-1">{results.metrics.unique}</div>
                <div className="text-[11px] text-slate-500 mt-1">Requested: {results.metrics.requested}</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs text-slate-400 font-medium flex items-center gap-1">
                  <Phone className="h-3.5 w-3.5 text-emerald-400" /> Phone Available
                </div>
                <div className="text-2xl font-extrabold text-emerald-400 mt-1">{results.metrics.phone_available}</div>
                <div className="text-[11px] text-emerald-500/80 mt-1 font-semibold">{results.metrics.phone_pct}% Coverage</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs text-slate-400 font-medium flex items-center gap-1">
                  <Globe className="h-3.5 w-3.5 text-blue-400" /> Website Available
                </div>
                <div className="text-2xl font-extrabold text-blue-400 mt-1">{results.metrics.website_available}</div>
                <div className="text-[11px] text-blue-500/80 mt-1 font-semibold">{results.metrics.website_pct}% Coverage</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs text-slate-400 font-medium flex items-center gap-1">
                  <Mail className="h-3.5 w-3.5 text-purple-400" /> Email Available
                </div>
                <div className="text-2xl font-extrabold text-purple-400 mt-1">{results.metrics.email_available}</div>
                <div className="text-[11px] text-purple-500/80 mt-1 font-semibold">{results.metrics.email_pct}% Coverage</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs text-slate-400 font-medium flex items-center gap-1">
                  <ShieldCheck className="h-3.5 w-3.5 text-amber-400" /> Social Profiles
                </div>
                <div className="text-2xl font-extrabold text-amber-400 mt-1">{results.metrics.social_available}</div>
                <div className="text-[11px] text-amber-500/80 mt-1 font-semibold">{results.metrics.social_pct}% Coverage</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs text-slate-400 font-medium flex items-center gap-1">
                  <Star className="h-3.5 w-3.5 text-yellow-400" /> Ratings Listed
                </div>
                <div className="text-2xl font-extrabold text-yellow-400 mt-1">{results.metrics.rating_available}</div>
                <div className="text-[11px] text-slate-500 mt-1">Provider Rating</div>
              </div>
            </div>

            {/* Filter & Export Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900 p-4 rounded-xl border border-slate-800">
              <div className="flex items-center gap-3 w-full sm:w-auto">
                <div className="relative flex-1 sm:w-64">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={tableSearch}
                    onChange={(e) => setTableSearch(e.target.value)}
                    placeholder="Search results..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>

                <label className="flex items-center gap-2 text-xs font-medium text-slate-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={contactableOnly}
                    onChange={(e) => setContactableOnly(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-800 text-blue-600 focus:ring-0"
                  />
                  Phone/Email Only
                </label>
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                <span className="text-xs text-slate-400 font-medium">
                  Showing {results.pagination.total} leads
                </span>

                <button
                  onClick={handleExportXlsx}
                  disabled={exporting || results.pagination.total === 0}
                  className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-lg shadow-emerald-600/20 flex items-center gap-2 transition disabled:opacity-50"
                >
                  {exporting ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  EXPORT EXCEL (.xlsx)
                </button>
              </div>
            </div>

            {/* Results Table */}
            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-950 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                      <th className="py-3 px-4">Business Name</th>
                      <th className="py-3 px-4">Address</th>
                      <th className="py-3 px-4">Phone</th>
                      <th className="py-3 px-4">Website</th>
                      <th className="py-3 px-4">Rating</th>
                      <th className="py-3 px-4">Reviews</th>
                      <th className="py-3 px-4">Place ID</th>
                      <th className="py-3 px-4">Google Maps URL</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {results.leads.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-12 text-center text-slate-500">
                          No business leads match your filter parameters.
                        </td>
                      </tr>
                    ) : (
                      results.leads.map((lead) => (
                        <tr key={lead.id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3.5 px-4 font-semibold text-white flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-blue-500"></span>
                            {lead.name}
                          </td>
                          <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate">
                            {lead.address || `${lead.city}, ${lead.state}`}
                          </td>
                          <td className="py-3.5 px-4 font-mono text-emerald-400 font-medium">
                            {lead.phone || <span className="text-slate-600">—</span>}
                          </td>
                          <td className="py-3.5 px-4 max-w-xs truncate">
                            {lead.website ? (
                              <a href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline flex items-center gap-1">
                                {lead.website.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            {lead.rating ? (
                              <span className="inline-flex items-center gap-1 text-yellow-400 font-semibold">
                                <Star className="h-3 w-3 fill-yellow-400" />
                                {lead.rating}
                              </span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 font-mono text-slate-300">
                            {lead.review_count ? lead.review_count.toLocaleString() : '0'}
                          </td>
                          <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px] max-w-[120px] truncate" title={lead.place_id || 'N/A'}>
                            {lead.place_id || 'N/A'}
                          </td>
                          <td className="py-3.5 px-4 text-[11px]">
                            {lead.google_maps_url ? (
                              <a href={lead.google_maps_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline flex items-center gap-1">
                                Maps Link
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Table Pagination */}
              <div className="bg-slate-950 px-4 py-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Page {results.pagination.page} of {results.pagination.pages} ({results.pagination.total} total)
                </span>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="p-1.5 rounded-lg bg-slate-900 text-slate-400 hover:text-white disabled:opacity-40"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(results.pagination.pages, p + 1))}
                    disabled={page >= results.pagination.pages}
                    className="p-1.5 rounded-lg bg-slate-900 text-slate-400 hover:text-white disabled:opacity-40"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
