'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Building2, 
  Target, 
  Plus, 
  Play, 
  Pause, 
  XCircle, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  ChevronRight 
} from 'lucide-react';
import { fetchCampaigns, CampaignItem, startCampaign, pauseCampaign } from '@/lib/api';

export default function CampaignsDashboard() {
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadCampaigns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCampaigns();
      setCampaigns(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch discovery campaigns';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    async function fetchData() {
      try {
        const data = await fetchCampaigns();
        if (active) {
          setCampaigns(data);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (active) {
          const msg = err instanceof Error ? err.message : 'Failed to fetch discovery campaigns';
          setError(msg);
          setLoading(false);
        }
      }
    }
    fetchData();
    return () => {
      active = false;
    };
  }, []);

  const handleStart = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await startCampaign(id);
      loadCampaigns();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to start campaign');
    }
  };

  const handlePause = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await pauseCampaign(id);
      loadCampaigns();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to pause campaign');
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st.toLowerCase()) {
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            RUNNING
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            COMPLETED
          </span>
        );
      case 'paused':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Pause className="w-3.5 h-3.5" />
            PAUSED
          </span>
        );
      case 'cancelled':
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" />
            {st.toUpperCase()}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <Clock className="w-3.5 h-3.5" />
            DRAFT
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight text-white">LeadOS</span>
            </Link>

            <nav className="hidden md:flex items-center gap-4 text-sm font-medium">
              <Link href="/" className="text-slate-400 hover:text-white transition-colors">
                Leads
              </Link>
              <Link href="/campaigns" className="text-indigo-400 font-semibold flex items-center gap-1">
                Campaigns
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => loadCampaigns()}
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <Link
              href="/campaigns/new"
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-lg shadow-indigo-600/25 transition-all"
            >
              <Plus className="w-4 h-4" />
              CREATE CAMPAIGN
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Discovery Campaigns</h1>
            <p className="text-xs text-slate-400 mt-1">
              Configure and run automated lead acquisition discovery workflows.
            </p>
          </div>

          <Link
            href="/campaigns/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md"
          >
            <Plus className="w-4 h-4" />
            New Campaign
          </Link>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-400" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => loadCampaigns()}
              className="px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white text-xs rounded-lg"
            >
              Retry
            </button>
          </div>
        )}

        {/* Campaigns Grid / List */}
        <div className="space-y-4">
          {loading ? (
            Array.from({ length: 3 }).map((_, idx) => (
              <div key={idx} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 animate-pulse h-32"></div>
            ))
          ) : campaigns.length > 0 ? (
            campaigns.map((camp) => (
              <div
                key={camp.id}
                className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 shadow-xl transition-all group relative"
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                  {/* Info */}
                  <div className="space-y-2 max-w-2xl">
                    <div className="flex items-center gap-3">
                      {getStatusBadge(camp.status)}
                      <span className="text-xs font-mono text-slate-400">Target: {camp.target_leads} leads</span>
                      {camp.category && (
                        <span className="px-2.5 py-0.5 rounded-md bg-slate-800 text-slate-300 text-xs border border-slate-700">
                          {camp.category}
                        </span>
                      )}
                    </div>

                    <h2 className="text-xl font-bold text-white group-hover:text-indigo-400 transition-colors">
                      <Link href={`/campaigns/${camp.id}`} className="hover:underline">
                        {camp.name}
                      </Link>
                    </h2>

                    {camp.description && (
                      <p className="text-xs text-slate-400 line-clamp-1">{camp.description}</p>
                    )}

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                      {camp.keywords && camp.keywords.length > 0 && (
                        <div>
                          <span className="text-slate-500">Keywords:</span> {camp.keywords.join(', ')}
                        </div>
                      )}
                      {camp.locations && camp.locations.length > 0 && (
                        <div>
                          <span className="text-slate-500">Locations:</span> {camp.locations.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Progress Metrics & Actions */}
                  <div className="flex items-center gap-6">
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 min-w-[70px]">
                        <span className="text-xs text-slate-500 block">Discovered</span>
                        <span className="text-lg font-bold text-white">{camp.discovered_count}</span>
                      </div>
                      <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 min-w-[70px]">
                        <span className="text-xs text-slate-500 block">Unique</span>
                        <span className="text-lg font-bold text-emerald-400">{camp.unique_count}</span>
                      </div>
                      <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 min-w-[70px]">
                        <span className="text-xs text-slate-500 block">Duplicates</span>
                        <span className="text-lg font-bold text-amber-400">{camp.duplicate_count}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {camp.status === 'draft' || camp.status === 'paused' ? (
                        <button
                          onClick={(e) => handleStart(camp.id, e)}
                          className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-all shadow-md"
                          title="Start Discovery Job"
                        >
                          <Play className="w-4 h-4 fill-white" />
                        </button>
                      ) : camp.status === 'running' ? (
                        <button
                          onClick={(e) => handlePause(camp.id, e)}
                          className="p-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium transition-all shadow-md"
                          title="Pause Job"
                        >
                          <Pause className="w-4 h-4 fill-white" />
                        </button>
                      ) : null}

                      <Link
                        href={`/campaigns/${camp.id}`}
                        className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white transition-all"
                        title="View Details"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-4">
              <Target className="w-12 h-12 text-indigo-500/60 mx-auto" />
              <h2 className="text-lg font-semibold text-slate-200">No Discovery Campaigns Found</h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Create a campaign to define target keywords, locations, ratings, and start automated lead discovery.
              </p>
              <Link
                href="/campaigns/new"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all shadow-lg"
              >
                <Plus className="w-4 h-4" />
                CREATE YOUR FIRST CAMPAIGN
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
