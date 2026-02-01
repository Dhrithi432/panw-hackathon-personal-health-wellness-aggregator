"""
Deterministic wellness score from HealthMetric daily buckets.
No DB writes; explainable component scores and trend.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.health_metric import HealthMetric
from schemas.analytics import WellnessScoreResponse




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


def _component_score(
    baseline_values: list[float],
    recent_values: list[float],
    higher_is_better: bool,
) -> int | None:
    """Return 0–100 component score, or None if insufficient data."""
    if len(baseline_values) + len(recent_values) < MIN_DAYS:
        return None
    if not baseline_values or not recent_values:
        return None
    baseline_mean = sum(baseline_values) / len(baseline_values)
    recent_mean = sum(recent_values) / len(recent_values)
    delta = recent_mean - baseline_mean
    denom = max(abs(baseline_mean), 1e-6)
    rel = delta / denom
    adj = rel if higher_is_better else -rel
    raw = 50 + 200 * adj
    return max(0, min(100, round(raw)))


def _score_for_window_end(
    by_metric: dict[str, dict[date, float]],
    window_end: date,
) -> tuple[int, dict[str, int]]:
    """
    Compute overall score (0–100) and components for 30-day window ending at window_end.
    Baseline [window_end-30, window_end-8] (23 days), recent [window_end-7, window_end] (7 days).
    Returns (overall_score, components).
    """
    baseline_start = window_end - timedelta(days=WINDOW_DAYS)
    baseline_end = window_end - timedelta(days=RECENT_DAYS + 1)
    recent_start = window_end - timedelta(days=RECENT_DAYS - 1)  # 7 days: end-6 .. end
    baseline_dates = [
        baseline_start + timedelta(days=i)
        for i in range((baseline_end - baseline_start).days + 1)
    ]
    recent_dates = [
        recent_start + timedelta(days=i)
        for i in range((window_end - recent_start).days + 1)
    ]

    components: dict[str, int] = {}
    for metric_name in ALL_METRICS:
        series = by_metric.get(metric_name)
        if not series:
            continue
        b_vals = [series[d] for d in baseline_dates if d in series]
        r_vals = [series[d] for d in recent_dates if d in series]
        higher = metric_name in METRICS_HIGHER_BETTER
        score = _component_score(b_vals, r_vals, higher)
        if score is not None:
            components[metric_name] = score

    if not components:
        return 0, {}
    overall = round(sum(components.values()) / len(components))
    return max(0, min(100, overall)), components


def compute_wellness_score(
    db: Session,
    start_date: date,
    end_date: date,
    user_id: str | None = None,
) -> WellnessScoreResponse:
    """
    Compute wellness score from daily-bucketed metrics in 30-day window ending at end_date.
    Trend compares overall score at end_date vs end_date-7. Deterministic.
    """
    query_start = end_date - timedelta(days=WINDOW_DAYS + QUERY_PAD_DAYS)
    start_dt = datetime.combine(query_start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc)
    end_dt += timedelta(days=1)

    by_metric = _daily_buckets(db, start_dt, end_dt, user_id)

    score_recent7, components = _score_for_window_end(by_metric, end_date)
    score_prev7, _ = _score_for_window_end(by_metric, end_date - timedelta(days=RECENT_DAYS))

    diff = score_recent7 - score_prev7
    if diff >= TREND_UP_THRESHOLD:
        trend = "up"
    elif diff <= TREND_DOWN_THRESHOLD:
        trend = "down"
    else:
        trend = "flat"

    if not components:
        top_driver = None
    else:
        top_driver = max(components.keys(), key=lambda m: abs(components[m] - 50))

    return WellnessScoreResponse(
        score=score_recent7,
        components=components,
        trend=trend,
        top_driver=top_driver,
    )
