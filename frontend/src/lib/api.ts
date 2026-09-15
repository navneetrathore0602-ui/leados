const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LeadListItem {
  id: string;
  name: string;
  category?: string;
  subcategory?: string;
  website?: string;
  rating?: number;
  review_count?: number;
  lead_score: number;
  verification_score: number;
  status: string;
  city?: string;
  state?: string;
  phone?: string;
  email?: string;
  created_at?: string;
}

export interface LocationItem {
  id?: string;
  address?: string;
  locality?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  latitude?: number;
  longitude?: number;
}

export interface ContactItem {
  id: string;
  type?: string;
  value?: string;
  normalized_value?: string;
  is_verified: boolean;
  confidence?: number;
  source?: string;
  last_verified_at?: string;
}

export interface SourceRecordItem {
  id: string;
  source_name?: string;
  source_url?: string;
  discovered_at?: string;
  confidence?: number;
}

export interface LeadDetail {
  id: string;
  name: string;
  normalized_name?: string;
  category?: string;
  subcategory?: string;
  description?: string;
  website?: string;
  rating?: number;
  review_count?: number;
  employee_count_estimate?: number;
  lead_score: number;
  verification_score: number;
  status: string;
  first_seen_at?: string;
  last_verified_at?: string;
  created_at?: string;
  updated_at?: string;
  locations: LocationItem[];
  contacts: ContactItem[];
  source_records: SourceRecordItem[];
}

export interface PaginatedLeads {
  items: LeadListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LeadStats {
  total_businesses: number;
  total_leads: number;
  hot_leads: number;
  warm_leads: number;
  cold_leads: number;
  verified_contacts: number;
  businesses_by_category: Record<string, number>;
  businesses_by_city: Record<string, number>;
}

export interface FetchLeadsParams {
  page?: number;
  page_size?: number;
  search?: string;
  category?: string;
  city?: string;
  state?: string;
  status?: string;
  minimum_score?: number;
}

export interface DiscoveryJobItem {
  id: string;
  campaign_id: string;
  provider: string;
  status: string;
  target_count: number;
  discovered_count: number;
  unique_count: number;
  duplicate_count: number;
  failed_count: number;
  error_message?: string;
  duration_seconds?: number;
  started_at?: string;
  completed_at?: string;
  created_at?: string;
}

export interface DataQualityMetrics {
  name_coverage: number;
  phone_coverage: number;
  website_coverage: number;
  email_coverage?: number;
  social_coverage?: number;
  description_coverage?: number;
  services_coverage?: number;
  address_coverage: number;
  rating_coverage: number;
  reviews_coverage: number;
}

export interface CampaignItem {
  id: string;
  name: string;
  description?: string;
  category?: string;
  keywords?: string[];
  locations?: string[];
  target_leads: number;
  min_rating?: number;
  min_reviews?: number;
  require_phone: boolean;
  require_website: boolean;
  require_email: boolean;
  provider: string;
  status: string;
  discovered_count: number;
  unique_count: number;
  duplicate_count: number;
  failed_count: number;
  duration_seconds?: number;
  data_quality?: DataQualityMetrics;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  jobs: DiscoveryJobItem[];
}

export interface CreateCampaignPayload {
  name: string;
  description?: string;
  category?: string;
  keywords?: string[];
  locations?: string[];
  target_leads?: number;
  min_rating?: number;
  min_reviews?: number;
  require_phone?: boolean;
  require_website?: boolean;
  require_email?: boolean;
  provider?: string;
}

export interface ProviderHealthInfo {
  provider: string;
  name: string;
  enabled: boolean;
  healthy: boolean;
  last_checked: string;
  error?: string;
}

// Phase 4 Enrichment Types

export interface BusinessSocialItem {
  id: string;
  platform: string;
  profile_url: string;
  username?: string;
  source?: string;
  confidence?: number;
  discovered_at?: string;
}

export interface BusinessCandidateFieldItem {
  id: string;
  field_name: string;
  value: string;
  normalized_value?: string;
  source?: string;
  source_url?: string;
  confidence?: number;
  status?: string;
  discovered_at?: string;
}

export interface TelemetryLogItem {
  url: string;
  http_status: number | null;
  duration_ms: number;
  failure_category: string | null;
  response_bytes: number;
  attempts: number;
}

export interface EnrichmentJobItem {
  id: string;
  business_id?: string;
  campaign_id?: string;
  provider: string;
  status: string;
  reachability_state?: string;
  pages_attempted?: number;
  pages_successful?: number;
  pages_failed?: number;
  total_http_requests?: number;
  telemetry_logs?: TelemetryLogItem[];
  avg_duration_ms?: number;
  median_duration_ms?: number;
  p95_duration_ms?: number;
  phone_found_count?: number;
  email_found_count?: number;
  social_found_count?: number;
  fields_attempted?: string[];
  fields_found?: string[];
  fields_verified?: string[];
  started_at?: string;
  completed_at?: string;
  duration?: number;
  error_code?: string;
  error_message?: string;
  created_at?: string;
}

export interface BusinessEnrichmentDetail {
  business_id: string;
  name: string;
  website?: string;
  description?: string;
  socials: BusinessSocialItem[];
  candidates: BusinessCandidateFieldItem[];
  jobs: EnrichmentJobItem[];
  quality_score: Record<string, number>;
}

// API Functions

export async function fetchStats(): Promise<LeadStats> {
  const response = await fetch(`${API_BASE_URL}/api/stats`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchLeads(params: FetchLeadsParams = {}): Promise<PaginatedLeads> {
  const query = new URLSearchParams();
  if (params.page) query.append("page", params.page.toString());
  if (params.page_size) query.append("page_size", params.page_size.toString());
  if (params.search) query.append("search", params.search);
  if (params.category) query.append("category", params.category);
  if (params.city) query.append("city", params.city);
  if (params.state) query.append("state", params.state);
  if (params.status) query.append("status", params.status);
  if (params.minimum_score !== undefined && params.minimum_score !== null) {
    query.append("minimum_score", params.minimum_score.toString());
  }

  const url = `${API_BASE_URL}/api/leads?${query.toString()}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch leads: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchLeadById(id: string): Promise<LeadDetail> {
  const response = await fetch(`${API_BASE_URL}/api/leads/${id}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch lead ${id}: ${response.statusText}`);
  }
  return response.json();
}

// Campaign & Provider API Client Functions

export async function fetchProviders(): Promise<ProviderHealthInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/providers`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch providers: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchCampaigns(): Promise<CampaignItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch campaigns: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchCampaignById(id: string): Promise<CampaignItem> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${id}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch campaign ${id}: ${response.statusText}`);
  }
  return response.json();
}

export async function createCampaign(payload: CreateCampaignPayload): Promise<CampaignItem> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errData.detail || "Failed to create campaign");
  }
  return response.json();
}

export async function startCampaign(id: string): Promise<CampaignItem> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${id}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errData.detail || "Failed to start campaign");
  }
  return response.json();
}

export async function pauseCampaign(id: string): Promise<CampaignItem> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${id}/pause`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errData.detail || "Failed to pause campaign");
  }
  return response.json();
}

export async function cancelCampaign(id: string): Promise<CampaignItem> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${id}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errData.detail || "Failed to cancel campaign");
  }
  return response.json();
}

// Enrichment API Client Functions

export async function enrichBusiness(id: string, provider: string = "website"): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/businesses/${id}/enrich?provider=${encodeURIComponent(provider)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to enrich business ${id}: ${response.statusText}`);
  }
  return response.json();
}

export async function getBusinessEnrichment(id: string): Promise<BusinessEnrichmentDetail> {
  const response = await fetch(`${API_BASE_URL}/api/businesses/${id}/enrichment`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch enrichment detail for ${id}: ${response.statusText}`);
  }
  return response.json();
}

export async function enrichCampaign(id: string, provider: string = "website"): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${id}/enrich?provider=${encodeURIComponent(provider)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to enrich campaign leads ${id}: ${response.statusText}`);
  }
  return response.json();
}

export async function getCampaignEnrichment(id: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${id}/enrichment`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch campaign enrichment status ${id}: ${response.statusText}`);
  }
  return response.json();
}

// Phase 5 Lead Intelligence & Scoring Types

export interface LeadScoreDetail {
  id: string;
  business_id: string;
  campaign_id?: string;
  total_score: number;
  tier: string;
  lifecycle_status: string;
  business_fit_score: number;
  location_fit_score: number;
  contactability_score: number;
  digital_presence_score: number;
  data_quality_score: number;
  scoring_version: string;
  scoring_ruleset: string;
  positive_signals?: string[];
  negative_signals?: string[];
  reasons?: string[];
  is_qualified: boolean;
  disqualified: boolean;
  disqualification_reason?: string;
  disqualified_rule?: string;
  scored_at?: string;
}

export interface CampaignScoreMetrics {
  campaign_id: string;
  total_scored: number;
  qualified_count: number;
  disqualified_count: number;
  avg_score: number;
  avg_data_quality: number;
  contactable_percentage: number;
  email_availability_percentage: number;
  phone_availability_percentage: number;
  website_availability_percentage: number;
  tier_counts: Record<string, number>;
  lifecycle_counts: Record<string, number>;
}

export interface QualifiedLeadItem {
  id: string;
  name: string;
  category?: string;
  city?: string;
  state?: string;
  phone?: string;
  email?: string;
  website?: string;
  total_score: number;
  tier: string;
  lifecycle_status: string;
  is_qualified: boolean;
  positive_signals?: string[];
  reasons?: string[];
}

export interface QualifiedLeadsResponse {
  items: QualifiedLeadItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Phase 5 Scoring API Client Functions

export async function fetchLeadScore(id: string, campaignId?: string): Promise<LeadScoreDetail> {
  const query = campaignId ? `?campaign_id=${encodeURIComponent(campaignId)}` : "";
  const response = await fetch(`${API_BASE_URL}/api/businesses/${id}/score${query}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch score for business ${id}: ${response.statusText}`);
  }
  return response.json();
}

export async function triggerLeadScore(id: string, campaignId?: string): Promise<LeadScoreDetail> {
  const query = campaignId ? `?campaign_id=${encodeURIComponent(campaignId)}` : "";
  const response = await fetch(`${API_BASE_URL}/api/businesses/${id}/score${query}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to calculate score for business ${id}: ${response.statusText}`);
  }
  return response.json();
}

export async function triggerCampaignScore(id: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${id}/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to trigger campaign scoring for ${id}: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchCampaignScoreMetrics(id: string): Promise<CampaignScoreMetrics> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${id}/scores`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch score metrics for campaign ${id}: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchQualifiedLeads(campaignId: string, params: Record<string, any> = {}): Promise<QualifiedLeadsResponse> {
  const query = new URLSearchParams();
  if (params.page) query.append("page", params.page.toString());
  if (params.page_size) query.append("page_size", params.page_size.toString());
  if (params.search) query.append("search", params.search);
  if (params.tier) query.append("tier", params.tier);
  if (params.status) query.append("status", params.status);
  if (params.sort_by) query.append("sort_by", params.sort_by);
  if (params.minimum_score !== undefined && params.minimum_score !== null) {
    query.append("minimum_score", params.minimum_score.toString());
  }

  const response = await fetch(`${API_BASE_URL}/api/campaigns/${campaignId}/qualified-leads?${query.toString()}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch qualified leads for campaign ${campaignId}: ${response.statusText}`);
  }
  return response.json();
}

export function getCampaignCsvExportUrl(campaignId: string, qualifiedOnly: boolean = false): string {
  return `${API_BASE_URL}/api/campaigns/${campaignId}/export/csv?qualified_only=${qualifiedOnly}`;
}

export interface PipelineJobStatus {
  status: string;
  job_id: string;
  campaign_id?: string;
  job_status?: string;
  current_stage?: string;
  total_records?: number;
  processed_records?: number;
  successful_records?: number;
  partial_records?: number;
  failed_records?: number;
  progress_percent?: number;
  stage_progress?: Record<string, number>;
  batch_size?: number;
  error_summary?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

export async function runPipeline(campaignId: string, batchSize: number = 100): Promise<PipelineJobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${campaignId}/run-pipeline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ batch_size: batchSize }),
  });
  if (!response.ok) {
    throw new Error(`Failed to start pipeline job: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchJobStatus(jobId: string): Promise<PipelineJobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch job status: ${response.statusText}`);
  }
  return response.json();
}

export async function cancelJob(jobId: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to cancel job: ${response.statusText}`);
  }
  return response.json();
}

export async function resumeJob(jobId: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to resume job: ${response.statusText}`);
  }
  return response.json();
}

export async function triggerCampaignExportXlsx(campaignId: string, filters: Record<string, any> = {}): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${campaignId}/export/xlsx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters),
  });
  if (!response.ok) {
    throw new Error(`Failed to generate XLSX export: ${response.statusText}`);
  }
  return response.blob();
}

export async function triggerCampaignExportCsv(campaignId: string, filters: Record<string, any> = {}): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/campaigns/${campaignId}/export/csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters),
  });
  if (!response.ok) {
    throw new Error(`Failed to generate CSV export: ${response.statusText}`);
  }
  return response.blob();
}
export interface FindBusinessesPayload {
  query?: string;
  category?: string;
  location?: string;
  quantity?: number;
  provider?: string;
}

export interface QuickSearchResponse {
  status: string;
  campaign_id: string;
  job_id: string;
  search_name: string;
  category: string;
  location: string;
  requested_quantity: number;
  provider: string;
  message: string;
}

export interface SearchResultsResponse {
  status: string;
  campaign_id: string;
  campaign_name: string;
  requested_quantity: number;
  metrics: {
    requested: number;
    discovered: number;
    unique: number;
    duplicates: number;
    phone_available: number;
    phone_pct: number;
    email_available: number;
    email_pct: number;
    website_available: number;
    website_pct: number;
    social_available: number;
    social_pct: number;
    rating_available: number;
  };
  pagination: {
    total: number;
    page: number;
    limit: number;
    pages: number;
  };
  leads: Array<{
    id: string;
    name: string;
    category: string;
    address: string;
    city: string;
    state: string;
    country: string;
    postal_code: string;
    phone: string;
    email: string;
    website: string;
    rating: number | null;
    review_count: number;
    place_id?: string;
    google_maps_url?: string;
    instagram: string;
    facebook: string;
    linkedin: string;
    youtube: string;
    x: string;
    score: number;
    tier: string;
    source: string;
    discovered_at: string | null;
  }>;
}

export async function findBusinesses(payload: FindBusinessesPayload): Promise<QuickSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/search/find-businesses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errData.detail || "Failed to start business data search");
  }
  return response.json();
}

export async function fetchSearchResults(
  campaignId: string,
  params: { page?: number; limit?: number; search?: string; contactable_only?: boolean } = {}
): Promise<SearchResultsResponse> {
  const query = new URLSearchParams();
  if (params.page) query.append("page", params.page.toString());
  if (params.limit) query.append("limit", params.limit.toString());
  if (params.search) query.append("search", params.search);
  if (params.contactable_only) query.append("contactable_only", "true");

  const response = await fetch(`${API_BASE_URL}/api/search/results/${campaignId}?${query.toString()}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch search results: ${response.statusText}`);
  }
  return response.json();
}


