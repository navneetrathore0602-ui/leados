from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import uuid

from app.core.database import SessionLocal
from app.models.domain import ExportHistory
from app.schemas.pipeline import ExportRequest, ExportHistoryResponse
from app.services.export_excel import generate_campaign_leads_xlsx
from app.services.export import generate_campaign_leads_csv

router = APIRouter()


@router.post("/campaigns/{campaign_id}/export/xlsx")
def export_campaign_xlsx(campaign_id: str, request: Optional[ExportRequest] = None):
    """
    Generates and downloads a multi-sheet Excel (.xlsx) workbook for campaign leads.
    Supports tier, qualification, and contactability filters.
    """
    filters = request.model_dump() if request else {}
    try:
        xlsx_bytes = generate_campaign_leads_xlsx(campaign_id, filters=filters)
        
        headers = {
            "Content-Disposition": f"attachment; filename=LeadOS_Campaign_{campaign_id[:8]}.xlsx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        return Response(content=xlsx_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/export/csv")
def export_campaign_csv_filtered(campaign_id: str, request: Optional[ExportRequest] = None):
    """
    Generates and downloads a CSV export file for campaign leads with filters.
    """
    filters = request.model_dump() if request else {}
    try:
        csv_str = generate_campaign_leads_csv(campaign_id, filters=filters)
        headers = {
            "Content-Disposition": f"attachment; filename=LeadOS_Campaign_{campaign_id[:8]}.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
        return Response(content=csv_str, media_type="text/csv", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/{campaign_id}/exports", response_model=List[Dict[str, Any]])
def get_campaign_export_history(campaign_id: str):
    """
    Returns export history log for a campaign.
    """
    db = SessionLocal()
    try:
        if isinstance(campaign_id, str):
            c_uuid = uuid.UUID(campaign_id)
        else:
            c_uuid = campaign_id

        records = db.query(ExportHistory).filter(ExportHistory.campaign_id == c_uuid).order_by(ExportHistory.created_at.desc()).all()
        return [
            {
                "id": str(r.id),
                "campaign_id": str(r.campaign_id),
                "format": r.format,
                "filters": r.filters or {},
                "record_count": r.record_count,
                "filename": r.filename,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]
    finally:
        db.close()
