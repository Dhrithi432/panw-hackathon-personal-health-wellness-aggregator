from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.deps import get_db
from schemas.insight_summary import InsightSummaryResponse
from schemas.insights import AnomalyOut, CorrelationOut
from services.anomalies import detect_anomalies
from services.correlations import compute_correlations
from services.insight_summary import generate_insight_summary

router = APIRouter()

_DATE_FORMAT = "%Y-%m-%d"


def _parse_date(value: str) -> date:
    try:
        dt = datetime.strptime(value, _DATE_FORMAT)
        return dt.date()
    except ValueError:
        raise HTTPException(400, detail="Invalid date format. Use YYYY-MM-DD.")


@router.get("/correlations", response_model=list[CorrelationOut])
def get_correlations(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: str | None = Query(None, description="Filter by user ID (optional)"),
    db: Session = Depends(get_db),
):
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise HTTPException(400, detail="start_date must be <= end_date.")
    return compute_correlations(db, start, end, user_id=user_id)


@router.get("/anomalies", response_model=list[AnomalyOut])
def get_anomalies(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: str | None = Query(None, description="Filter by user ID (optional)"),
    db: Session = Depends(get_db),
):
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise HTTPException(400, detail="start_date must be <= end_date.")
    return detect_anomalies(db, start, end, user_id=user_id)


@router.get("/summary", response_model=InsightSummaryResponse)
def get_summary(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: str | None = Query(None, description="Filter by user ID (optional)"),
    db: Session = Depends(get_db),
):
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise HTTPException(400, detail="start_date must be <= end_date.")
    return generate_insight_summary(db, start, end, user_id=user_id)
