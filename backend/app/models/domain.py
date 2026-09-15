import uuid
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, Text, Numeric, UUID, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models.base import Base

class Business(Base):
    __tablename__ = "businesses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    normalized_name = Column(Text)
    category = Column(Text)
    subcategory = Column(Text)
    description = Column(Text)
    website = Column(Text)
    rating = Column(Numeric(2, 1))
    review_count = Column(Integer)
    employee_count_estimate = Column(Integer)
    lead_score = Column(Integer, default=0)
    verification_score = Column(Integer, default=0)
    status = Column(Text, default='new')
    lifecycle_status = Column(Text, default='NEW')  # NEW, ENRICHED, QUALIFIED, SALES_READY, DISQUALIFIED
    first_seen_at = Column(DateTime)
    last_verified_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    locations = relationship("BusinessLocation", back_populates="business", cascade="all, delete-orphan")
    contacts = relationship("BusinessContact", back_populates="business", cascade="all, delete-orphan")
    source_records = relationship("SourceRecord", back_populates="business", cascade="all, delete-orphan")
    enrichment_jobs = relationship("EnrichmentJob", back_populates="business", cascade="all, delete-orphan")
    socials = relationship("BusinessSocial", back_populates="business", cascade="all, delete-orphan")
    candidate_fields = relationship("BusinessCandidateField", back_populates="business", cascade="all, delete-orphan")
    scores = relationship("LeadScore", back_populates="business", cascade="all, delete-orphan")


class LeadScore(Base):
    __tablename__ = "lead_scores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)

    total_score = Column(Integer, nullable=False, default=0)
    tier = Column(Text, nullable=False, default="LOW")  # HOT, WARM, COOL, LOW
    lifecycle_status = Column(Text, nullable=False, default="NEW")  # NEW, ENRICHED, QUALIFIED, SALES_READY, DISQUALIFIED

    business_fit_score = Column(Integer, default=0)  # 0-30
    location_fit_score = Column(Integer, default=0)  # 0-20
    contactability_score = Column(Integer, default=0)  # 0-20
    digital_presence_score = Column(Integer, default=0)  # 0-15
    data_quality_score = Column(Integer, default=0)  # 0-15

    scoring_version = Column(Text, default="v1")
    scoring_ruleset = Column(Text, default="default_v1")

    positive_signals = Column(JSON().with_variant(JSONB, "postgresql"))
    negative_signals = Column(JSON().with_variant(JSONB, "postgresql"))
    reasons = Column(JSON().with_variant(JSONB, "postgresql"))

    is_qualified = Column(Boolean, default=True)
    disqualified = Column(Boolean, default=False)
    disqualification_reason = Column(Text)
    disqualified_rule = Column(Text)

    scored_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

    business = relationship("Business", back_populates="scores")


class BusinessLocation(Base):
    __tablename__ = "business_locations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    address = Column(Text)
    locality = Column(Text)
    city = Column(Text)
    state = Column(Text)
    country = Column(Text)
    postal_code = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=func.now())

    business = relationship("Business", back_populates="locations")

class BusinessContact(Base):
    __tablename__ = "business_contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    type = Column(Text)  # phone, mobile, whatsapp, email
    value = Column(Text)
    normalized_value = Column(Text)
    is_verified = Column(Boolean, default=False)
    confidence = Column(Numeric(5, 2))
    source = Column(Text)
    first_seen_at = Column(DateTime)
    last_verified_at = Column(DateTime)

    business = relationship("Business", back_populates="contacts")

class SourceRecord(Base):
    __tablename__ = "source_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    source_name = Column(Text)
    source_url = Column(Text)
    raw_data = Column(JSON().with_variant(JSONB, "postgresql"))
    discovered_at = Column(DateTime)
    confidence = Column(Numeric(5, 2))

    business = relationship("Business", back_populates="source_records")

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(Text)
    keywords = Column(JSON().with_variant(JSONB, "postgresql"))
    locations = Column(JSON().with_variant(JSONB, "postgresql"))
    target_leads = Column(Integer, default=100)
    min_rating = Column(Numeric(2, 1), default=0.0)
    min_reviews = Column(Integer, default=0)
    require_phone = Column(Boolean, default=False)
    require_website = Column(Boolean, default=False)
    require_email = Column(Boolean, default=False)
    provider = Column(Text, default="mock")
    status = Column(Text, default='draft')  # draft, queued, running, paused, completed, failed, cancelled
    
    discovered_count = Column(Integer, default=0)
    unique_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    jobs = relationship("DiscoveryJob", back_populates="campaign", cascade="all, delete-orphan")
    pipeline_jobs = relationship("PipelineJob", back_populates="campaign", cascade="all, delete-orphan")
    exports = relationship("ExportHistory", back_populates="campaign", cascade="all, delete-orphan")

class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    status = Column(Text, default="QUEUED", index=True)  # QUEUED, RUNNING, PAUSED, COMPLETED, PARTIAL, FAILED, CANCELLED
    current_stage = Column(Text, default="DISCOVERY")  # DISCOVERY, NORMALIZATION, DEDUPLICATION, ENRICHMENT, SCORING, EXPORT
    
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    successful_records = Column(Integer, default=0)
    partial_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)
    
    batch_size = Column(Integer, default=100)
    stage_progress = Column(JSON().with_variant(JSONB, "postgresql"))
    error_summary = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    campaign = relationship("Campaign", back_populates="pipeline_jobs")

class ExportHistory(Base):
    __tablename__ = "export_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    format = Column(Text, nullable=False, default="xlsx")  # xlsx, csv
    filters = Column(JSON().with_variant(JSONB, "postgresql"))
    record_count = Column(Integer, default=0)
    filename = Column(Text, nullable=False)
    file_path = Column(Text)
    created_at = Column(DateTime, default=func.now())

    campaign = relationship("Campaign", back_populates="exports")


class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"))
    provider = Column(Text, default="mock")
    status = Column(Text, default="queued")  # queued, running, paused, completed, failed, cancelled
    target_count = Column(Integer, default=0)
    discovered_count = Column(Integer, default=0)
    unique_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    campaign = relationship("Campaign", back_populates="jobs")

class BusinessSocial(Base):
    __tablename__ = "business_socials"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    platform = Column(Text, nullable=False)  # instagram, facebook, linkedin, youtube, x, github
    profile_url = Column(Text, nullable=False)
    username = Column(Text)
    source = Column(Text)
    confidence = Column(Numeric(5, 2), default=0.90)
    discovered_at = Column(DateTime, default=func.now())

    business = relationship("Business", back_populates="socials")

class BusinessCandidateField(Base):
    __tablename__ = "business_candidate_fields"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    field_name = Column(Text, nullable=False)  # phone, email, website, etc.
    value = Column(Text, nullable=False)
    normalized_value = Column(Text)
    source = Column(Text)
    source_url = Column(Text)
    confidence = Column(Numeric(5, 2), default=0.70)
    status = Column(Text, default="candidate")  # verified, candidate, conflicting
    discovered_at = Column(DateTime, default=func.now())

    business = relationship("Business", back_populates="candidate_fields")

class EnrichmentJob(Base):
    __tablename__ = "enrichment_jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    provider = Column(Text, default="website")
    status = Column(Text, default="queued")  # queued, running, completed, partial, failed, cancelled
    reachability_state = Column(Text, default="SUCCESS")  # SUCCESS, PARTIAL, UNREACHABLE, FAILED
    pages_attempted = Column(Integer, default=0)
    pages_successful = Column(Integer, default=0)
    pages_failed = Column(Integer, default=0)
    total_http_requests = Column(Integer, default=0)
    telemetry_logs = Column(JSON().with_variant(JSONB, "postgresql"))
    avg_duration_ms = Column(Float)
    median_duration_ms = Column(Float)
    p95_duration_ms = Column(Float)
    phone_found_count = Column(Integer, default=0)
    email_found_count = Column(Integer, default=0)
    social_found_count = Column(Integer, default=0)
    fields_attempted = Column(JSON().with_variant(JSONB, "postgresql"))
    fields_found = Column(JSON().with_variant(JSONB, "postgresql"))
    fields_verified = Column(JSON().with_variant(JSONB, "postgresql"))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration = Column(Numeric(10, 2))
    error_code = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    business = relationship("Business", back_populates="enrichment_jobs")



