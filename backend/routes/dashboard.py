import json
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import DashboardSummary, MonthlyReportResponse
from backend.services.report_service import calculate_dashboard_data, get_or_generate_monthly_report
from backend.auth import get_optional_current_user

router = APIRouter(prefix="/api", tags=["Dashboard & Analytics"])


@router.get("/dashboard/{month}", response_model=DashboardSummary)
def get_dashboard_summary(
    month: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Fetch analytics dashboard totals and category breakdowns for a given YYYY-MM month."""
    try:
        user_id = current_user.id if current_user else None
        data = calculate_dashboard_data(db, month, user_id=user_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch dashboard: {str(e)}")


@router.get("/reports/{month}", response_model=MonthlyReportResponse)
def get_monthly_report(
    month: str,
    refresh: bool = Query(False, description="Force regenerate AI narrative summary"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieve monthly AI narrative report (cached or generated)."""
    try:
        user_id = current_user.id if current_user else None
        report = get_or_generate_monthly_report(db, month, force_refresh=refresh, user_id=user_id)
        breakdown_dict = {}
        if report.category_breakdown_json:
            try:
                breakdown_dict = json.loads(report.category_breakdown_json)
            except Exception:
                breakdown_dict = {}

        return MonthlyReportResponse(
            id=report.id,
            month=report.month,
            total_amount=report.total_amount,
            category_breakdown=breakdown_dict,
            ai_summary=report.ai_summary or "No summary generated.",
            generated_at=report.generated_at.isoformat() if report.generated_at else ""
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load monthly report: {str(e)}")
