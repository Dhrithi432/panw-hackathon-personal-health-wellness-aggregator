from collections import defaultdict
from datetime import date, datetime, timedelta, time, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.health_metric import HealthMetric
from schemas.health import TimelinePoint, TimelineResponse


def get_timeline(
    db: Session,
    start_date: date,
    end_date: date,
    user_id: str | None = None,
) -> TimelineResponse:
    """
    Return daily-bucketed, time-aligned timeline points from HealthMetric.
    Multiple rows per (day, metric_name) are averaged. Date range inclusive.
    """
    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc)
    end_dt += timedelta(days=1)  # exclusive upper bound

    day_col = func.date_trunc("day", HealthMetric.ts).label("day")
    stmt = (
        select(
            day_col,
            HealthMetric.metric_name,
            func.avg(HealthMetric.value).label("avg_value"),
        )
        .where(HealthMetric.ts >= start_dt, HealthMetric.ts < end_dt)
        .group_by(day_col, HealthMetric.metric_name)
        .order_by(day_col)
    )
    if user_id is not None:
        stmt = stmt.where(HealthMetric.user_id == user_id)

    rows = db.execute(stmt).all()

    by_day: dict[datetime, dict[str, float]] = defaultdict(dict)
    for row in rows:
        day_ts = row.day
        if isinstance(day_ts, datetime):
            key = day_ts
        else:
            key = datetime.combine(day_ts, time.min, tzinfo=timezone.utc)
        by_day[key][row.metric_name] = float(row.avg_value)

    points = [
        TimelinePoint(
            ts=f"{day_ts.date()}T00:00:00Z",
            metrics=dict(metrics),
        )
        for day_ts, metrics in sorted(by_day.items())
    ]
    return TimelineResponse(points=points)
