from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.deps import get_db
from schemas.health import TimelineResponse
from services.timeline import get_timeline

router = APIRouter()

_DATE_FORMAT = "%Y-%m-%d"


def _parse_date(value: str) -> date:
    try:
        dt = datetime.strptime(value, _DATE_FORMAT)
        return dt.date()
    except ValueError:
        raise HTTPException(400, detail="Invalid date format. Use YYYY-MM-DD.")


@router.get("/timeline", response_model=TimelineResponse)
def timeline(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    user_id: str | None = Query(None, description="Filter by user ID (optional)"),
    db: Session = Depends(get_db),
):
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise HTTPException(400, detail="start_date must be <= end_date.")
    return get_timeline(db, start, end, user_id=user_id)
