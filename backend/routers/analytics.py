from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.deps import get_db
from schemas.analytics import WellnessScoreResponse
from services.wellness import compute_wellness_score

router = APIRouter()

_DATE_FORMAT = "%Y-%m-%d"


def _parse_date(value: str) -> date:
    try:
        dt = datetime.strptime(value, _DATE_FORMAT)
        return dt.date()
    except ValueError:
        raise HTTPException(400, detail="Invalid date format. Use YYYY-MM-DD.")


@router.get("/wellness-score", response_model=WellnessScoreResponse)
def get_wellness_score(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: str | None = Query(None, description="Filter by user ID (optional)"),
    db: Session = Depends(get_db),
):
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise HTTPException(400, detail="start_date must be <= end_date.")
    return compute_wellness_score(db, start, end, user_id=user_id)
