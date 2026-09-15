'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { 
  Building2, 
  Flame, 
  Zap, 
  Snowflake, 
  ShieldCheck, 
  Search, 
  Filter, 
  Star, 
  Phone, 
  Globe, 
  MapPin, 
  ChevronLeft, 
  ChevronRight, 
  RefreshCw, 
  LogIn, 
  ArrowUpRight,
  ExternalLink,
  Layers
} from 'lucide-react';
import { fetchStats, fetchLeads, LeadStats, PaginatedLeads, LeadListItem } from '@/lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState<LeadStats | null>(null);
  const [leadsData, setLeadsData] = useState<PaginatedLeads | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter parameters
  const [search, setSearch] = useState<string>('');
  const [category, setCategory] = useState<string>('');
  const [minScore, setMinScore] = useState<number>(0);
  const [status, setStatus] = useState<string>('');
  const [page, setPage] = useState<number>(1);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, leadsRes] = await Promise.all([
        fetchStats(),
        fetchLeads({
          page,
          page_size: 10,
          search: search.trim() || undefined,
          category: category || undefined,
          status: status || undefined,
          minimum_score: minScore > 0 ? minScore : undefined,
        })
      ]);
      setStats(statsRes);
      setLeadsData(leadsRes);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to connect to LeadOS API';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [page, search, category, status, minScore]);

  useEffect(() => {
    let active = true;
    async function fetchData() {
      try {
        const [statsRes, leadsRes] = await Promise.all([
          fetchStats(),
          fetchLeads({
            page,
            page_size: 10,
            search: search.trim() || undefined,
            category: category || undefined,
            status: status || undefined,
            minimum_score: minScore > 0 ? minScore : undefined,
          })
        ]);
        if (active) {
          setStats(statsRes);
          setLeadsData(leadsRes);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (active) {
          const message = err instanceof Error ? err.message : 'Failed to connect to LeadOS API';
          setError(message);
          setLoading(false);
        }
      }
    }
    fetchData();
    return () => {
      active = false;
    };
  }, [page, search, category, status, minScore]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const getScoreBadge = (score: number) => {
    if (score >= 80) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <Flame className="w-3.5 h-3.5 text-rose-500 fill-rose-500" />
          HOT ({score})
        </span>
      );
    } else if (score >= 50) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Zap className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
          WARM ({score})
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
        <Snowflake className="w-3.5 h-3.5 text-sky-400" />
        COLD ({score})
      </span>
    );
  };

  const getStatusBadge = (st: string) => {
    switch (st.toLowerCase()) {
      case 'qualified':
        return <span className="px-2 py-0.5 text-xs font-medium rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Qualified</span>;
      case 'contacted':
        return <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">Contacted</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-medium rounded bg-slate-500/10 text-slate-400 border border-slate-500/20">New</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
                  LeadOS
                </span>
                <span className="ml-2 text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  v2.0
                </span>
              </div>
            </div>

            <nav className="hidden md:flex items-center gap-4 text-sm font-medium">
              <Link href="/" className="text-blue-400 font-semibold bg-blue-500/10 px-3 py-1.5 rounded-lg border border-blue-500/20">
                Dashboard
              </Link>
              <Link href="/find-businesses" className="text-slate-300 hover:text-white font-semibold px-3 py-1.5 rounded-lg hover:bg-slate-800 transition-colors flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-blue-400" />
                Find Businesses
              </Link>
              <Link href="/campaigns" className="text-slate-400 hover:text-white transition-colors px-3 py-1.5">
                Campaigns
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/find-businesses"
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-lg shadow-md shadow-blue-500/20 transition-all"
            >
              <Search className="w-3.5 h-3.5" />
              FIND BUSINESSES
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Metric Cards Section */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 shadow-xl relative overflow-hidden group hover:border-slate-700 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-slate-400">Total Businesses</span>
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Building2 className="w-5 h-5" />
              </div>
            </div>
            <p className="text-3xl font-extrabold mt-3 text-white">
              {stats ? stats.total_businesses.toLocaleString() : '—'}
            </p>
            <p className="text-xs text-slate-400 mt-1">Discovered in database</p>
          </div>

          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 shadow-xl relative overflow-hidden group hover:border-rose-500/30 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-rose-400">Hot Leads</span>
              <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
                <Flame className="w-5 h-5 fill-rose-500" />
              </div>
            </div>
            <p className="text-3xl font-extrabold mt-3 text-rose-400">
              {stats ? stats.hot_leads.toLocaleString() : '—'}
            </p>
            <p className="text-xs text-slate-400 mt-1">Score 80+</p>
          </div>

          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 shadow-xl relative overflow-hidden group hover:border-amber-500/30 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-amber-400">Warm Leads</span>
              <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Zap className="w-5 h-5 fill-amber-500" />
              </div>
            </div>
            <p className="text-3xl font-extrabold mt-3 text-amber-400">
              {stats ? stats.warm_leads.toLocaleString() : '—'}
            </p>
            <p className="text-xs text-slate-400 mt-1">Score 50-79</p>
          </div>

          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 shadow-xl relative overflow-hidden group hover:border-sky-500/30 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-sky-400">Cold Leads</span>
              <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
                <Snowflake className="w-5 h-5" />
              </div>
            </div>
            <p className="text-3xl font-extrabold mt-3 text-sky-400">
              {stats ? stats.cold_leads.toLocaleString() : '—'}
            </p>
            <p className="text-xs text-slate-400 mt-1">Score &lt; 50</p>
          </div>

          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 shadow-xl relative overflow-hidden group hover:border-emerald-500/30 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-emerald-400">Verified Contacts</span>
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="w-5 h-5" />
              </div>
            </div>
            <p className="text-3xl font-extrabold mt-3 text-emerald-400">
              {stats ? stats.verified_contacts.toLocaleString() : '—'}
            </p>
            <p className="text-xs text-slate-400 mt-1">High confidence</p>
          </div>
        </section>

        {/* Filter Controls Bar */}
        <section className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4 sm:p-5 shadow-lg space-y-4">
          <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search business name, category, or city..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div className="flex flex-wrap sm:flex-nowrap gap-3">
              <select
                value={category}
                onChange={(e) => { setCategory(e.target.value); setPage(1); }}
                className="px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="">All Categories</option>
                {stats?.businesses_by_category && Object.keys(stats.businesses_by_category).map((cat) => (
                  <option key={cat} value={cat}>{cat} ({stats.businesses_by_category[cat]})</option>
                ))}
              </select>

              <select
                value={status}
                onChange={(e) => { setStatus(e.target.value); setPage(1); }}
                className="px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="">All Statuses</option>
                <option value="new">New</option>
                <option value="qualified">Qualified</option>
                <option value="contacted">Contacted</option>
              </select>

              <select
                value={minScore}
                onChange={(e) => { setMinScore(Number(e.target.value)); setPage(1); }}
                className="px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value={0}>All Lead Scores</option>
                <option value={80}>🔥 Hot Only (80+)</option>
                <option value={50}>⚡ Warm+ (50+)</option>
              </select>

              <button
                type="submit"
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl transition-all shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2"
              >
                <Filter className="w-4 h-4" />
                Filter
              </button>
            </div>
          </form>
        </section>

        {/* Lead Table Container */}
        <section className="bg-slate-900/80 border border-slate-800/80 rounded-2xl shadow-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Discovered Lead Intelligence</h2>
                <p className="text-xs text-slate-400">
                  {leadsData ? `Showing ${leadsData.items.length} of ${leadsData.total} leads` : 'Loading database...'}
                </p>
              </div>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-6 bg-rose-500/10 border-b border-rose-500/20 text-rose-300 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-rose-400">API Error:</span>
                <span>{error}</span>
              </div>
              <button
                onClick={() => loadData()}
                className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium rounded-lg transition-colors"
              >
                Retry Request
              </button>
            </div>
          )}

          {/* Table Element */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-xs tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">Business</th>
                  <th className="py-3.5 px-4">Category</th>
                  <th className="py-3.5 px-4">Location</th>
                  <th className="py-3.5 px-4">Phone</th>
                  <th className="py-3.5 px-4">Website</th>
                  <th className="py-3.5 px-4">Rating</th>
                  <th className="py-3.5 px-4 text-center">Lead Score</th>
                  <th className="py-3.5 px-4 text-center">Verification</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  // Loading Skeleton Rows
                  Array.from({ length: 5 }).map((_, idx) => (
                    <tr key={idx} className="animate-pulse">
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-32"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-24"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-20"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-24"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-28"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-12"></div></td>
                      <td className="py-4 px-4 text-center"><div className="h-6 bg-slate-800 rounded-full w-20 mx-auto"></div></td>
                      <td className="py-4 px-4 text-center"><div className="h-4 bg-slate-800 rounded w-16 mx-auto"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-16"></div></td>
                      <td className="py-4 px-4 text-right"><div className="h-4 bg-slate-800 rounded w-12 ml-auto"></div></td>
                    </tr>
                  ))
                ) : leadsData && leadsData.items.length > 0 ? (
                  leadsData.items.map((lead: LeadListItem) => (
                    <tr key={lead.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-4 px-4 font-medium text-slate-100">
                        <div className="font-semibold text-white">{lead.name}</div>
                        {lead.subcategory && <div className="text-xs text-slate-400">{lead.subcategory}</div>}
                      </td>
                      <td className="py-4 px-4 text-slate-300">
                        <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 text-xs border border-slate-700">
                          {lead.category || 'N/A'}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-slate-300">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-slate-500" />
                          <span>{lead.city ? `${lead.city}, ${lead.state || ''}` : 'N/A'}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4 text-slate-300 font-mono text-xs">
                        {lead.phone ? (
                          <div className="flex items-center gap-1.5 text-slate-300">
                            <Phone className="w-3.5 h-3.5 text-slate-500" />
                            {lead.phone}
                          </div>
                        ) : '—'}
                      </td>
                      <td className="py-4 px-4 text-slate-300">
                        {lead.website ? (
                          <a
                            href={lead.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 hover:underline text-xs"
                          >
                            <Globe className="w-3.5 h-3.5" />
                            Website
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : '—'}
                      </td>
                      <td className="py-4 px-4">
                        {lead.rating ? (
                          <div className="flex items-center gap-1">
                            <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                            <span className="font-semibold text-slate-100">{lead.rating}</span>
                            <span className="text-xs text-slate-500">({lead.review_count || 0})</span>
                          </div>
                        ) : '—'}
                      </td>
                      <td className="py-4 px-4 text-center">
                        {getScoreBadge(lead.lead_score)}
                      </td>
                      <td className="py-4 px-4 text-center">
                        <div className="inline-flex items-center gap-1 font-mono text-xs font-semibold text-emerald-400">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          {lead.verification_score}%
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        {getStatusBadge(lead.status)}
                      </td>
                      <td className="py-4 px-4 text-right">
                        <Link
                          href={`/leads/${lead.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-indigo-400 hover:text-white bg-indigo-500/10 hover:bg-indigo-600 rounded-lg border border-indigo-500/20 transition-all"
                        >
                          View
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={10} className="py-12 text-center text-slate-400">
                      <Building2 className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                      <p className="text-base font-medium">No lead records found</p>
                      <p className="text-xs text-slate-500 mt-1">Try resetting your filter parameters or search queries.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {leadsData && leadsData.total_pages > 1 && (
            <div className="p-4 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Page <span className="font-semibold text-slate-200">{leadsData.page}</span> of{' '}
                <span className="font-semibold text-slate-200">{leadsData.total_pages}</span>
              </span>

              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-medium text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <button
                  disabled={page >= leadsData.total_pages}
                  onClick={() => setPage(page + 1)}
                  className="px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-medium text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
