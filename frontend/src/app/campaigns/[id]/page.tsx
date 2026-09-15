'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Play, 
  Pause, 
  XCircle, 
  CheckCircle2, 
  RefreshCw, 
  AlertCircle, 
  Clock,
  Layers,
  ArrowUpRight,
  ShieldCheck,
  Globe,
  Phone,
  MapPin,
  Star,
  Sparkles,
  Award,
  Download,
  Flame,
  Zap,
  Snowflake,
  Filter,
  FileSpreadsheet,
  FileText
} from 'lucide-react';
import { 
  fetchCampaignById, 
  startCampaign, 
  pauseCampaign, 
  cancelCampaign, 
  fetchLeads, 
  enrichCampaign, 
  triggerCampaignScore,
  fetchCampaignScoreMetrics,
  fetchQualifiedLeads,
  getCampaignCsvExportUrl,
  runPipeline,
  fetchJobStatus,
  cancelJob,
  resumeJob,
  triggerCampaignExportXlsx,
  triggerCampaignExportCsv,
  CampaignItem, 
  LeadListItem,
  CampaignScoreMetrics,
  QualifiedLeadItem,
  PipelineJobStatus
} from '@/lib/api';

export default function CampaignDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const campaignId = resolvedParams.id;

  const [campaign, setCampaign] = useState<CampaignItem | null>(null);
  const [leads, setLeads] = useState<QualifiedLeadItem[]>([]);
  const [metrics, setMetrics] = useState<CampaignScoreMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pipelineJob, setPipelineJob] = useState<PipelineJobStatus | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);
  const [exportFilter, setExportFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('highest_score');
  const [tierFilter, setTierFilter] = useState<string>('ALL');

  const loadData = async () => {
    try {
      const campData = await fetchCampaignById(campaignId);
      setCampaign(campData);

      const metricsData = await fetchCampaignScoreMetrics(campaignId).catch(() => null);
      setMetrics(metricsData);

      const qualRes = await fetchQualifiedLeads(campaignId, {
        page: 1,
        page_size: 20,
        sort_by: sortBy,
        tier: tierFilter === 'ALL' ? undefined : tierFilter
      }).catch(() => null);

      if (qualRes && qualRes.items) {
        setLeads(qualRes.items);
      } else {
        const leadsRes = await fetchLeads({
          page: 1,
          page_size: 20,
          category: campData.category || undefined,
        });
        setLeads(leadsRes.items.map(l => ({
          id: l.id,
          name: l.name,
          category: l.category,
          city: l.city,
          state: l.state,
          phone: l.phone,
          email: l.email,
          website: l.website,
          total_score: l.lead_score,
          tier: l.lead_score >= 80 ? 'HOT' : l.lead_score >= 60 ? 'WARM' : l.lead_score >= 40 ? 'COOL' : 'LOW',
          lifecycle_status: l.status || 'NEW',
          is_qualified: true
        })));
      }
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch campaign details';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const checkJobProgress = async () => {
    if (!pipelineJob?.job_id) return;
    try {
      const updated = await fetchJobStatus(pipelineJob.job_id);
      setPipelineJob(updated);
      if (updated.job_status === 'COMPLETED' || updated.job_status === 'FAILED' || updated.job_status === 'CANCELLED') {
        setPipelineRunning(false);
        loadData();
      }
    } catch (err) {
      console.error('Failed to poll job status:', err);
    }
  };

  useEffect(() => {
    loadData();
  }, [campaignId, sortBy, tierFilter]);

  useEffect(() => {
    if (!pipelineRunning || !pipelineJob?.job_id) return;
    const interval = setInterval(checkJobProgress, 2000);
    return () => clearInterval(interval);
  }, [pipelineRunning, pipelineJob?.job_id]);

  const handleRunPipeline = async () => {
    setPipelineRunning(true);
    try {
      const res = await runPipeline(campaignId, 100);
      setPipelineJob(res);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to launch lead pipeline');
      setPipelineRunning(false);
    }
  };

  const handleCancelPipeline = async () => {
    if (!pipelineJob?.job_id) return;
    try {
      await cancelJob(pipelineJob.job_id);
      setPipelineRunning(false);
      loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to cancel pipeline job');
    }
  };

  const handleResumePipeline = async () => {
    if (!pipelineJob?.job_id) return;
    setPipelineRunning(true);
    try {
      await resumeJob(pipelineJob.job_id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to resume pipeline job');
      setPipelineRunning(false);
    }
  };

  const handleExportXlsx = async () => {
    setExporting(true);
    try {
      const filters: Record<string, any> = {};
      if (exportFilter === 'qualified') filters.qualified_only = true;
      if (exportFilter === 'hot') filters.tier = 'HOT';
      if (exportFilter === 'contactable') filters.contactable_only = true;

      const blob = await triggerCampaignExportXlsx(campaignId, filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const dateStr = new Date().toISOString().slice(0, 10);
      const safeName = (campaign?.name || 'Campaign').replace(/[^a-zA-Z0-9]/g, '_');
      a.download = `LeadOS_${safeName}_${exportFilter.toUpperCase()}_${dateStr}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to download Excel file');
    } finally {
      setExporting(false);
    }
  };

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const filters: Record<string, any> = {};
      if (exportFilter === 'qualified') filters.qualified_only = true;
      if (exportFilter === 'hot') filters.tier = 'HOT';
      if (exportFilter === 'contactable') filters.contactable_only = true;

      const blob = await triggerCampaignExportCsv(campaignId, filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const dateStr = new Date().toISOString().slice(0, 10);
      const safeName = (campaign?.name || 'Campaign').replace(/[^a-zA-Z0-9]/g, '_');
      a.download = `LeadOS_${safeName}_${exportFilter.toUpperCase()}_${dateStr}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to download CSV file');
    } finally {
      setExporting(false);
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st.toLowerCase()) {
      case 'running':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <RefreshCw className="w-4 h-4 animate-spin" />
            RUNNING
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-4 h-4" />
            COMPLETED
          </span>
        );
      case 'paused':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Pause className="w-4 h-4" />
            PAUSED
          </span>
        );
      case 'cancelled':
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-4 h-4" />
            {st.toUpperCase()}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <Clock className="w-4 h-4" />
            DRAFT
          </span>
        );
    }
  };

  const getTierPill = (tier: string) => {
    const t = tier.toUpperCase();
    if (t === 'HOT') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Flame className="w-3 h-3 fill-emerald-400" />
          HOT
        </span>
      );
    }
    if (t === 'WARM') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
          <Zap className="w-3 h-3" />
          WARM
        </span>
      );
    }
    if (t === 'COOL') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Snowflake className="w-3 h-3" />
          COOL
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
        LOW
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
          <p className="text-slate-400 text-sm font-medium">Loading Campaign Workspace...</p>
        </div>
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4">
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl p-6 text-center">
          <AlertCircle className="w-12 h-12 text-rose-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-rose-300 mb-1">Campaign Not Found</h3>
          <p className="text-rose-400/80 text-sm mb-6">{error || 'Could not load campaign data.'}</p>
          <Link
            href="/campaigns"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-sm font-medium hover:bg-slate-700 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Campaigns
          </Link>
        </div>
      </div>
    );
  }

  const stages = [
    { name: 'DISCOVERY', label: 'Discovery' },
    { name: 'NORMALIZATION', label: 'Normalization' },
    { name: 'DEDUPLICATION', label: 'Deduplication' },
    { name: 'ENRICHMENT', label: 'Enrichment' },
    { name: 'SCORING', label: 'Scoring' },
    { name: 'EXPORT', label: 'Excel Export' }
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link
            href="/campaigns"
            className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition mb-3"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Campaign Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">{campaign.name}</h1>
            {getStatusBadge(campaign.status)}
          </div>
          <p className="text-slate-400 text-sm mt-1">{campaign.description || 'Campaign Target Discovery & Excel Lead Export'}</p>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={handleRunPipeline}
            disabled={pipelineRunning}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-sm shadow-lg shadow-emerald-500/20 transition disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-white" />
            {pipelineRunning ? 'Pipeline Running...' : 'RUN PIPELINE'}
          </button>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-xl">
            <select
              value={exportFilter}
              onChange={(e) => setExportFilter(e.target.value)}
              className="bg-transparent text-xs text-slate-300 font-medium px-2 py-1 focus:outline-none"
            >
              <option value="all">All Leads</option>
              <option value="qualified">Qualified Only</option>
              <option value="hot">HOT Tier Only</option>
              <option value="contactable">Contactable Only</option>
            </select>

            <button
              onClick={handleExportXlsx}
              disabled={exporting}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20 font-semibold text-xs transition disabled:opacity-50"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              EXPORT XLSX
            </button>

            <button
              onClick={handleExportCsv}
              disabled={exporting}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs transition disabled:opacity-50"
            >
              <FileText className="w-3.5 h-3.5" />
              CSV
            </button>
          </div>
        </div>
      </div>

      {/* Live Pipeline Progress Card */}
      {pipelineJob && (
        <div className="bg-slate-900/80 border border-emerald-500/30 rounded-2xl p-6 shadow-xl space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-emerald-400 animate-pulse" />
              <h3 className="text-base font-bold text-white">LeadOS Production Pipeline Execution</h3>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {pipelineJob.job_status || 'RUNNING'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold text-slate-300">{pipelineJob.progress_percent || 0}% Complete</span>
              {pipelineRunning && (
                <button
                  onClick={handleCancelPipeline}
                  className="px-3 py-1 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 text-xs font-semibold"
                >
                  Cancel
                </button>
              )}
              {pipelineJob.job_status === 'CANCELLED' && (
                <button
                  onClick={handleResumePipeline}
                  className="px-3 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20 text-xs font-semibold"
                >
                  Resume
                </button>
              )}
            </div>
          </div>

          {/* Master Progress Bar */}
          <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full transition-all duration-500"
              style={{ width: `${pipelineJob.progress_percent || 0}%` }}
            />
          </div>

          {/* 6 Stage Progress Indicators */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 pt-2">
            {stages.map((st) => {
              const pct = pipelineJob.stage_progress?.[st.name] ?? 0;
              const isCurrent = pipelineJob.current_stage === st.name;
              return (
                <div key={st.name} className={`p-3 rounded-xl border ${isCurrent ? 'bg-indigo-500/10 border-indigo-500/40' : 'bg-slate-800/40 border-slate-800'}`}>
                  <div className="flex items-center justify-between text-xs font-bold mb-1">
                    <span className={isCurrent ? 'text-indigo-300' : 'text-slate-400'}>{st.label}</span>
                    <span className={pct === 100 ? 'text-emerald-400' : 'text-slate-400'}>{pct}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${pct === 100 ? 'bg-emerald-400' : isCurrent ? 'bg-indigo-400 animate-pulse' : 'bg-slate-600'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Campaign Tier Metrics Summary */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400">Total Scored</span>
              <Award className="w-4 h-4 text-indigo-400" />
            </div>
            <p className="text-2xl font-bold text-white">{metrics.total_scored}</p>
            <p className="text-xs text-slate-400 mt-1">{metrics.qualified_count} Qualified</p>
          </div>

          <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-emerald-400">HOT Leads</span>
              <Flame className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-emerald-300">{metrics.tier_counts.HOT || 0}</p>
            <p className="text-xs text-emerald-400/80 mt-1">Score 80–100</p>
          </div>

          <div className="bg-blue-500/5 border border-blue-500/20 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-blue-400">WARM Leads</span>
              <Zap className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-blue-300">{metrics.tier_counts.WARM || 0}</p>
            <p className="text-xs text-blue-400/80 mt-1">Score 60–79</p>
          </div>

          <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-amber-400">COOL Leads</span>
              <Snowflake className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-2xl font-bold text-amber-300">{metrics.tier_counts.COOL || 0}</p>
            <p className="text-xs text-amber-400/80 mt-1">Score 40–59</p>
          </div>

          <div className="bg-rose-500/5 border border-rose-500/20 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-rose-400">Disqualified</span>
              <XCircle className="w-4 h-4 text-rose-400" />
            </div>
            <p className="text-2xl font-bold text-rose-300">{metrics.disqualified_count}</p>
            <p className="text-xs text-rose-400/80 mt-1">Failed Criteria</p>
          </div>
        </div>
      )}

      {/* Leads Table Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-bold text-white">Campaign Lead Intelligence</h3>
            <span className="text-xs px-2.5 py-1 rounded-full font-semibold bg-slate-800 text-slate-400">
              {leads.length} Records
            </span>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* Qualification Filter Tabs */}
            <div className="flex items-center bg-slate-800/80 p-1 rounded-xl">
              {['ALL', 'HOT', 'WARM', 'COOL', 'LOW'].map((t) => (
                <button
                  key={t}
                  onClick={() => setTierFilter(t)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    tierFilter === t
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Sort Dropdown */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-xs font-medium text-slate-200 rounded-xl px-3 py-1.5 focus:outline-none"
            >
              <option value="highest_score">Highest Lead Score</option>
              <option value="newest">Recently Discovered</option>
              <option value="name">Alphabetical</option>
            </select>
          </div>
        </div>

        {/* Lead Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800/50 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-5 py-3.5">Business Name</th>
                <th className="px-5 py-3.5">Category</th>
                <th className="px-5 py-3.5">Location</th>
                <th className="px-5 py-3.5">Contact Channels</th>
                <th className="px-5 py-3.5">Lead Score</th>
                <th className="px-5 py-3.5">Tier</th>
                <th className="px-5 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {leads.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-400">
                    No leads found for this campaign filter. Click <strong>RUN PIPELINE</strong> to execute discovery, enrichment, and scoring.
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-5 py-4 font-semibold text-white">
                      <Link href={`/leads/${lead.id}`} className="hover:text-indigo-400 transition">
                        {lead.name}
                      </Link>
                    </td>
                    <td className="px-5 py-4 text-xs text-slate-400">{lead.category || 'N/A'}</td>
                    <td className="px-5 py-4 text-xs text-slate-400">
                      {lead.city ? `${lead.city}, ${lead.state || ''}` : 'Location N/A'}
                    </td>
                    <td className="px-5 py-4 text-xs space-y-1">
                      {lead.phone && (
                        <div className="flex items-center gap-1.5 text-slate-300">
                          <Phone className="w-3 h-3 text-emerald-400" />
                          {lead.phone}
                        </div>
                      )}
                      {lead.website && (
                        <div className="flex items-center gap-1.5 text-indigo-400 truncate max-w-[180px]">
                          <Globe className="w-3 h-3" />
                          <a href={lead.website} target="_blank" rel="noreferrer" className="hover:underline">
                            {lead.website.replace(/^https?:\/\//, '')}
                          </a>
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-white">{lead.total_score}</span>
                        <div className="w-16 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              lead.total_score >= 80
                                ? 'bg-emerald-400'
                                : lead.total_score >= 60
                                ? 'bg-blue-400'
                                : lead.total_score >= 40
                                ? 'bg-amber-400'
                                : 'bg-slate-500'
                            }`}
                            style={{ width: `${lead.total_score}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4">{getTierPill(lead.tier)}</td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        href={`/leads/${lead.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-slate-800 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
                      >
                        View Lead
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
