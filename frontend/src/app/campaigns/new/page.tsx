'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Target, 
  Play, 
  Save, 
  AlertCircle, 
  Sparkles,
  Tag,
  Star,
  Layers,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import { createCampaign, startCampaign, fetchProviders, ProviderHealthInfo } from '@/lib/api';

export default function NewCampaignPage() {
  const router = useRouter();

  const [name, setName] = useState('Mumbai Marble Dealers');
  const [description, setDescription] = useState('Discovery campaign targeting high-rated marble and granite dealers across Mumbai MMR region.');
  const [category, setCategory] = useState('Marble & Granite');
  const [keywordsText, setKeywordsText] = useState('marble dealer, granite dealer, Italian marble, natural stone');
  const [locationsText, setLocationsText] = useState('Mumbai, Thane, Navi Mumbai');
  const [targetLeads, setTargetLeads] = useState<number>(100);
  const [minRating, setMinRating] = useState<number>(4.0);
  const [minReviews, setMinReviews] = useState<number>(25);

  const [requirePhone, setRequirePhone] = useState<boolean>(true);
  const [requireWebsite, setRequireWebsite] = useState<boolean>(false);
  const [requireEmail, setRequireEmail] = useState<boolean>(false);
  const [provider, setProvider] = useState<string>('mock');

  const [providers, setProviders] = useState<ProviderHealthInfo[]>([]);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProviders() {
      try {
        const list = await fetchProviders();
        setProviders(list.filter((p) => p.enabled));
      } catch (err: unknown) {
        // Fallback default
        setProviders([
          { provider: 'mock', name: 'Mock Discovery Provider (Development)', enabled: true, healthy: true, last_checked: '' },
          { provider: 'openstreetmap', name: 'OpenStreetMap Places API (Real)', enabled: true, healthy: true, last_checked: '' }
        ]);
      }
    }
    loadProviders();
  }, []);

  const parseLists = () => {
    const keywords = keywordsText
      .split(',')
      .map((k) => k.trim())
      .filter((k) => k.length > 0);
    const locations = locationsText
      .split(',')
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    return { keywords, locations };
  };

  const handleSave = async (autoStart: boolean = false) => {
    setError(null);
    if (!name.trim()) {
      setError('Campaign name is required');
      return;
    }

    const { keywords, locations } = parseLists();
    if (!category.trim() && keywords.length === 0) {
      setError('Please provide at least one category or keyword');
      return;
    }

    if (targetLeads <= 0) {
      setError('Target leads must be a positive number');
      return;
    }

    if (minRating < 0 || minRating > 5) {
      setError('Minimum rating must be between 0 and 5');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || undefined,
        category: category.trim() || undefined,
        keywords,
        locations,
        target_leads: targetLeads,
        min_rating: minRating,
        min_reviews: minReviews,
        require_phone: requirePhone,
        require_website: requireWebsite,
        require_email: requireEmail,
        provider: provider,
      };

      const campaign = await createCampaign(payload);

      if (autoStart) {
        await startCampaign(campaign.id);
      }

      router.push(`/campaigns/${campaign.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save campaign';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/campaigns" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            Back to Campaigns
          </Link>

          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            Campaign Builder
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <Target className="w-8 h-8 text-indigo-400" />
            Configure New Discovery Campaign
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Define discovery provider, keywords, geographical regions, filter criteria, and discovery targets.
          </p>
        </div>

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-300 flex items-center gap-2 text-sm">
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={(e) => { e.preventDefault(); handleSave(false); }} className="space-y-6">
          {/* Card 1: Basic Information & Provider Selection */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <h2 className="text-base font-semibold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              1. Campaign & Provider Selection
            </h2>

            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-xs font-medium text-slate-300">Campaign Name *</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Mumbai Marble Dealers"
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>

                {/* Provider Selector Dropdown */}
                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-indigo-400" />
                    Discovery Provider *
                  </label>
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                  >
                    {providers.map((p) => (
                      <option key={p.provider} value={p.provider}>
                        {p.name} {p.healthy ? '✓ (Healthy)' : '⚠ (Check Health)'}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-400">
                    Select <span className="font-semibold text-indigo-400">Mock Discovery Provider</span> for offline testing or <span className="font-semibold text-indigo-400">OpenStreetMap Places API</span> for live real business discovery.
                  </p>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Description</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Campaign objective notes..."
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                />
              </div>
            </div>
          </div>

          {/* Card 2: Discovery Parameters */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <h2 className="text-base font-semibold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
              <Tag className="w-4 h-4 text-indigo-400" />
              2. Discovery Parameters & Targeting
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Business Category</label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="e.g. Marble & Granite"
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Target Lead Quantity</label>
                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={targetLeads}
                  onChange={(e) => setTargetLeads(Number(e.target.value))}
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-medium text-slate-300">Keywords (Comma-separated)</label>
                <input
                  type="text"
                  value={keywordsText}
                  onChange={(e) => setKeywordsText(e.target.value)}
                  placeholder="marble dealer, granite dealer, Italian marble"
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-medium text-slate-300">Target Locations (Comma-separated)</label>
                <input
                  type="text"
                  value={locationsText}
                  onChange={(e) => setLocationsText(e.target.value)}
                  placeholder="Mumbai, Thane, Navi Mumbai"
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>
          </div>

          {/* Card 3: Quality & Requirements Filters */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <h2 className="text-base font-semibold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
              <Star className="w-4 h-4 text-indigo-400" />
              3. Quality & Lead Thresholds
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Minimum Rating (0 to 5)</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  max={5}
                  value={minRating}
                  onChange={(e) => setMinRating(Number(e.target.value))}
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Minimum Reviews Count</label>
                <input
                  type="number"
                  min={0}
                  value={minReviews}
                  onChange={(e) => setMinReviews(Number(e.target.value))}
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            <div className="pt-2 space-y-3">
              <span className="text-xs font-medium text-slate-300 block">Required Data Channels:</span>
              
              <div className="flex flex-wrap gap-6 text-sm">
                <label className="flex items-center gap-2 cursor-pointer select-none text-slate-200">
                  <input
                    type="checkbox"
                    checked={requirePhone}
                    onChange={(e) => setRequirePhone(e.target.checked)}
                    className="w-4 h-4 accent-indigo-600 rounded"
                  />
                  <span>Require Phone Number</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer select-none text-slate-200">
                  <input
                    type="checkbox"
                    checked={requireWebsite}
                    onChange={(e) => setRequireWebsite(e.target.checked)}
                    className="w-4 h-4 accent-indigo-600 rounded"
                  />
                  <span>Require Website URL</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer select-none text-slate-200">
                  <input
                    type="checkbox"
                    checked={requireEmail}
                    onChange={(e) => setRequireEmail(e.target.checked)}
                    className="w-4 h-4 accent-indigo-600 rounded"
                  />
                  <span>Require Email Address</span>
                </label>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-4 pt-4 border-t border-slate-800">
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSave(false)}
              className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold rounded-xl transition-all border border-slate-700 flex items-center gap-2 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              SAVE DRAFT
            </button>

            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSave(true)}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-indigo-600/25 flex items-center gap-2 disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-white" />
              START CAMPAIGN
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
