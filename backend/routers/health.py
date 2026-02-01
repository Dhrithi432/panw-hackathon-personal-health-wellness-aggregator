from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from schemas.health import TimelineResponse

router = APIRouter()

_DATE_FORMAT = "%Y-%m-%d"


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, _DATE_FORMAT)
    except ValueError:
        raise HTTPException(400, detail="Invalid date format. Use YYYY-MM-DD.")


@router.get("/timeline", response_model=TimelineResponse)
def get_timeline(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    _parse_date(start_date)
    _parse_date(end_date)
    return TimelineResponse(points=[])
