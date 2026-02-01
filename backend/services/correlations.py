"""
Lagged Pearson correlation on HealthMetric daily buckets.
No DB writes; deterministic math only.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.health_metric import HealthMetric
from schemas.insights import CorrelationOut

LAGS = [-3, -2, -1, 0, 1, 2, 3]
MIN_OVERLAP_DAYS = 14
MIN_ABS_CORRELATION = 0.4
TOP_N = 5
QUERY_PAD_DAYS = 3


def _daily_buckets(
    db: Session,
    start_dt: datetime,
    end_dt: datetime,
    user_id: str | None,
) -> dict[str, dict[date, float]]:
    """Return metric_name -> {date -> avg_value} for [start_dt, end_dt)."""
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

    by_metric: dict[str, dict[date, float]] = defaultdict(dict)
    for row in rows:
        day_ts = row.day
        if hasattr(day_ts, "date"):
            d = day_ts.date()
        else:
            d = (
                day_ts
                if isinstance(day_ts, date)
                else datetime.combine(day_ts, time.min, tzinfo=timezone.utc).date()
            )
        by_metric[row.metric_name][d] = float(row.avg_value)
    return dict(by_metric)


def _pearson(x: list[float], y: list[float]) -> float | None:
    """Pearson r. Returns None if undefined (e.g. zero variance)."""
    n = len(x)
    if n != len(y) or n < 2:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    dx = [xi - mx for xi in x]
    dy = [yi - my for yi in y]
    ss_xx = sum(d * d for d in dx)
    ss_yy = sum(d * d for d in dy)
    if ss_xx == 0 or ss_yy == 0:
        return None
    ss_xy = sum(dx[i] * dy[i] for i in range(n))
    r = ss_xy / (ss_xx * ss_yy) ** 0.5
    return r


def compute_correlations(
    db: Session,
    start_date: date,
    end_date: date,
    user_id: str | None = None,
) -> list[CorrelationOut]:
    """
    Compute lagged Pearson correlation for metric pairs from daily-bucketed data.
    Returns top 5 by |correlation|, only |r| >= 0.4 and >= 14 overlapping days.
    """
    query_start = start_date - timedelta(days=QUERY_PAD_DAYS)
    query_end = end_date + timedelta(days=QUERY_PAD_DAYS)
    start_dt = datetime.combine(query_start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(query_end, time.min, tzinfo=timezone.utc)
    end_dt += timedelta(days=1)

    by_metric = _daily_buckets(db, start_dt, end_dt, user_id)
    metric_names = sorted(by_metric.keys())
    results: list[CorrelationOut] = []

    for i, metric_a in enumerate(metric_names):
        for metric_b in metric_names[i + 1 :]:  # no self, no duplicate pair
            series_a = by_metric[metric_a]
            series_b = by_metric[metric_b]
            best_r: float | None = None
            best_lag: int | None = None

            for lag in LAGS:
                # Align: days d where we have metric_a[d] and metric_b[d + lag]
                overlap_dates = [
                    d
                    for d in series_a
                    if (d + timedelta(days=lag)) in series_b
                ]
                if len(overlap_dates) < MIN_OVERLAP_DAYS:
                    continue
                x = [series_a[d] for d in overlap_dates]
                y = [series_b[d + timedelta(days=lag)] for d in overlap_dates]
                r = _pearson(x, y)
                if r is None:
                    continue
                if best_r is None or abs(r) > abs(best_r):
                    best_r = r
                    best_lag = lag


            if best_r is not None and best_lag is not None and abs(best_r) >= MIN_ABS_CORRELATION:
                results.append(
                    CorrelationOut(
                        metric_a=metric_a,
                        metric_b=metric_b,
                        lag_days=best_lag,
                        correlation=round(best_r, 3),
                        p_value=None,
                        confidence=round(min(1.0, abs(best_r)), 4),
                    )
                )

    results.sort(key=lambda c: abs(c.correlation), reverse=True)
    return results[:TOP_N]