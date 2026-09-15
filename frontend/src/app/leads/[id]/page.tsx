'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Flame, 
  Zap, 
  Snowflake, 
  ShieldCheck, 
  MapPin, 
  Phone, 
  Mail, 
  Globe, 
  Star, 
  Calendar, 
  Users, 
  ExternalLink,
  Database,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Award,
  Sparkles,
  Check,
  X
} from 'lucide-react';
import { fetchLeadById, fetchLeadScore, LeadDetail, LeadScoreDetail } from '@/lib/api';

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const leadId = resolvedParams.id;

  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [scoreDetail, setScoreDetail] = useState<LeadScoreDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadLeadData() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchLeadById(leadId);
        setLead(data);
        const scoreData = await fetchLeadScore(leadId).catch(() => null);
        setScoreDetail(scoreData);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to fetch lead details';
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    loadLeadData();
  }, [leadId]);

  const getTierBadge = (tier?: string, score?: number) => {
    const t = tier?.toUpperCase() || (score && score >= 80 ? 'HOT' : score && score >= 60 ? 'WARM' : score && score >= 40 ? 'COOL' : 'LOW');
    if (t === 'HOT') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <Flame className="w-4 h-4 text-rose-500 fill-rose-500" />
          HOT LEAD ({score || 0}/100)
        </span>
      );
    } else if (t === 'WARM') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Zap className="w-4 h-4 text-amber-500 fill-amber-500" />
          WARM LEAD ({score || 0}/100)
        </span>
      );
    } else if (t === 'COOL') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold bg-sky-500/10 text-sky-400 border border-sky-500/20">
          <Snowflake className="w-4 h-4 text-sky-400" />
          COOL LEAD ({score || 0}/100)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold bg-slate-500/10 text-slate-400 border border-slate-500/20">
        LOW TIER ({score || 0}/100)
      </span>
    );
  };

  const getStatusBadge = (status?: string) => {
    const st = status?.toUpperCase() || 'NEW';
    if (st === 'SALES_READY') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5" /> SALES READY
        </span>
      );
    } else if (st === 'QUALIFIED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          <ShieldCheck className="w-3.5 h-3.5" /> QUALIFIED
        </span>
      );
    } else if (st === 'DISQUALIFIED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <AlertCircle className="w-3.5 h-3.5" /> DISQUALIFIED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700 uppercase">
        {st}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
          <p className="text-sm font-medium text-slate-400">Loading Lead Intelligence Record...</p>
        </div>
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 p-6 flex flex-col items-center justify-center">
        <div className="max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center space-y-4 shadow-xl">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-white">Lead Record Not Found</h2>
          <p className="text-xs text-slate-400">{error || 'The requested business lead does not exist in the database.'}</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const score = scoreDetail ? scoreDetail.total_score : lead.lead_score;
  const tier = scoreDetail ? scoreDetail.tier : (score >= 80 ? 'HOT' : score >= 60 ? 'WARM' : score >= 40 ? 'COOL' : 'LOW');
  const lifecycleStatus = scoreDetail ? scoreDetail.lifecycle_status : (lead.status || 'NEW');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans flex flex-col">
      {/* Navbar Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-400">ID: {lead.id}</span>
          </div>
        </div>
      </header>

      {/* Main Detail Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header Hero Section */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  {lead.category || 'General Business'}
                </span>
                {lead.subcategory && (
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                    {lead.subcategory}
                  </span>
                )}
                {getStatusBadge(lifecycleStatus)}
              </div>

              <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                {lead.name}
              </h1>

              {lead.description && (
                <p className="text-sm text-slate-300 max-w-3xl leading-relaxed">
                  {lead.description}
                </p>
              )}
            </div>

            <div className="flex flex-col items-start md:items-end gap-3">
              {getTierBadge(tier, score)}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold">
                <ShieldCheck className="w-4 h-4" />
                Verification Score: {lead.verification_score}%
              </div>
            </div>
          </div>
        </div>

        {/* Phase 5 Explainable Scoring Breakdown Section */}
        {scoreDetail && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-indigo-400" />
                Explainable Score Breakdown ({scoreDetail.total_score}/100)
              </h2>
              <span className="text-xs font-mono text-slate-400">Ruleset: {scoreDetail.scoring_ruleset} ({scoreDetail.scoring_version})</span>
            </div>

            {/* 5 Component Score Bars */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Business Fit</span>
                  <span className="text-indigo-400 font-bold">{scoreDetail.business_fit_score}/30</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${(scoreDetail.business_fit_score / 30) * 100}%` }}></div>
                </div>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Location Fit</span>
                  <span className="text-purple-400 font-bold">{scoreDetail.location_fit_score}/20</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-purple-500 h-full rounded-full" style={{ width: `${(scoreDetail.location_fit_score / 20) * 100}%` }}></div>
                </div>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Contactability</span>
                  <span className="text-emerald-400 font-bold">{scoreDetail.contactability_score}/20</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${(scoreDetail.contactability_score / 20) * 100}%` }}></div>
                </div>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Digital Presence</span>
                  <span className="text-sky-400 font-bold">{scoreDetail.digital_presence_score}/15</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-sky-500 h-full rounded-full" style={{ width: `${(scoreDetail.digital_presence_score / 15) * 100}%` }}></div>
                </div>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Data Quality</span>
                  <span className="text-amber-400 font-bold">{scoreDetail.data_quality_score}/15</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-amber-500 h-full rounded-full" style={{ width: `${(scoreDetail.data_quality_score / 15) * 100}%` }}></div>
                </div>
              </div>
            </div>

            {/* WHY THIS LEAD? Positive & Negative Signals */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                Why This Lead? (Scoring Signals & Reasons)
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Positive Signals */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                  <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                    <Check className="w-4 h-4" /> Positive Key Signals
                  </span>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {scoreDetail.positive_signals && scoreDetail.positive_signals.length > 0 ? (
                      scoreDetail.positive_signals.map((sig, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-emerald-500 font-bold">•</span> {sig}
                        </li>
                      ))
                    ) : (
                      <li className="text-slate-500 italic">No positive signals recorded</li>
                    )}
                  </ul>
                </div>

                {/* Negative Signals / Warnings */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                  <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                    <X className="w-4 h-4" /> Risk Factors / Disqualification
                  </span>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {scoreDetail.disqualified && (
                      <li className="text-rose-400 font-semibold flex items-start gap-2 bg-rose-500/10 p-2 rounded border border-rose-500/20">
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        Disqualified: {scoreDetail.disqualification_reason}
                      </li>
                    )}
                    {scoreDetail.negative_signals && scoreDetail.negative_signals.length > 0 ? (
                      scoreDetail.negative_signals.map((sig, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-amber-500 font-bold">•</span> {sig}
                        </li>
                      ))
                    ) : (
                      <li className="text-slate-500 italic">Zero negative risk factors detected</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Business Overview & Contacts */}
          <div className="lg:col-span-2 space-y-6">
            {/* Contact Details Card */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-lg space-y-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Phone className="w-5 h-5 text-indigo-400" />
                Contact Intelligence ({lead.contacts.length})
              </h2>

              <div className="divide-y divide-slate-800">
                {lead.contacts.length > 0 ? (
                  lead.contacts.map((contact) => (
                    <div key={contact.id} className="py-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-slate-800 text-slate-400">
                          {contact.type === 'email' ? <Mail className="w-4 h-4" /> : <Phone className="w-4 h-4" />}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-100">{contact.value}</p>
                          <p className="text-xs text-slate-400 capitalize">Type: {contact.type} • Source: {contact.source || 'Scraper'}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {contact.is_verified ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-md">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Verified ({contact.confidence || 90}%)
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                            Unverified
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 py-2">No contact channels recorded yet.</p>
                )}
              </div>
            </div>

            {/* Location Details Card */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-lg space-y-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <MapPin className="w-5 h-5 text-indigo-400" />
                Physical Location ({lead.locations.length})
              </h2>

              <div className="space-y-3">
                {lead.locations.length > 0 ? (
                  lead.locations.map((loc, idx) => (
                    <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                      <p className="text-sm font-medium text-slate-200">{loc.address}</p>
                      <p className="text-xs text-slate-400">
                        {loc.locality ? `${loc.locality}, ` : ''}{loc.city}, {loc.state} {loc.postal_code}, {loc.country}
                      </p>
                      {loc.latitude && loc.longitude && (
                        <p className="text-xs font-mono text-slate-500">
                          Geo Coordinates: {loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)}
                        </p>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">No physical location available.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Metadata Sidebar */}
          <div className="space-y-6">
            {/* Quick Metrics Card */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-lg space-y-4">
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Business Signals</h3>
              
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400 flex items-center gap-2">
                    <Globe className="w-4 h-4 text-slate-500" />
                    Website
                  </span>
                  {lead.website ? (
                    <a href={lead.website} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline inline-flex items-center gap-1 text-xs">
                      Visit <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-slate-500 text-xs">N/A</span>
                  )}
                </div>

                <div className="flex items-center justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400 flex items-center gap-2">
                    <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                    Rating
                  </span>
                  <span className="font-semibold text-slate-100">
                    {lead.rating ? `${lead.rating} (${lead.review_count || 0} reviews)` : 'N/A'}
                  </span>
                </div>

                <div className="flex items-center justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400 flex items-center gap-2">
                    <Users className="w-4 h-4 text-slate-500" />
                    Est. Employees
                  </span>
                  <span className="font-semibold text-slate-100">
                    {lead.employee_count_estimate ? `${lead.employee_count_estimate} staff` : 'N/A'}
                  </span>
                </div>

                <div className="flex items-center justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-500" />
                    First Discovered
                  </span>
                  <span className="text-xs text-slate-300">
                    {lead.first_seen_at ? new Date(lead.first_seen_at).toLocaleDateString() : 'Recent'}
                  </span>
                </div>
              </div>
            </div>

            {/* Source Information Card */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-lg space-y-4">
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Source Provenance</h3>

              <div className="space-y-3">
                {lead.source_records.length > 0 ? (
                  lead.source_records.map((src) => (
                    <div key={src.id} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-indigo-400">{src.source_name}</span>
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                          {src.confidence || 90}% confidence
                        </span>
                      </div>
                      {src.source_url && (
                        <p className="text-[11px] text-slate-400 truncate">
                          URL: {src.source_url}
                        </p>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500">Seed Database Provider</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

