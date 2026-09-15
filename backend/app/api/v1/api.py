from fastapi import APIRouter
from app.api.v1 import leads, stats, campaigns, providers, enrichment, scoring, pipeline, export, search

api_router = APIRouter()
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(enrichment.router, tags=["enrichment"])
api_router.include_router(scoring.router, tags=["scoring"])
api_router.include_router(pipeline.router, tags=["pipeline"])
api_router.include_router(export.router, tags=["export"])
