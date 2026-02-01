"""
Rolling-baseline anomaly detection on HealthMetric daily buckets.
No DB writes; compute on read. Deterministic.
"""
import statistics
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.health_metric import HealthMetric
from schemas.insights import AnomalyOut

MIN_BASELINE_DAYS = 7
Z_THRESHOLD = 2.5
ROLLING_DAYS = 30


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
            d = day_ts if isinstance(day_ts, date) else datetime.combine(day_ts, time.min, tzinfo=timezone.utc).date()
        by_metric[row.metric_name][d] = float(row.avg_value)
    return dict(by_metric)


def _z_severity(z: float) -> str:
    abs_z = abs(z)
    if abs_z >= 4:
        return "high"
    if abs_z >= 3:
        return "medium"
    return "low"


def _summary(metric_name: str) -> str:
    label = metric_name.replace("_", " ").title()
    return f"{label} deviated significantly from recent baseline"

def _merge_consecutive(
    metric_name: str,
    anomalous_days: list[tuple[date, float]],
) -> list[AnomalyOut]:
    """Merge consecutive anomalous days into one window per run. Sorted by start_ts desc."""
    if not anomalous_days:
        return []
    anomalous_days.sort(key=lambda x: x[0])
    windows: list[tuple[date, date, float]] = []  # start, end, max_abs_z
    cur_start = anomalous_days[0][0]
    cur_end = cur_start
    max_z = abs(anomalous_days[0][1])
    for d, z in anomalous_days[1:]:
        if (d - cur_end).days == 1:
            cur_end = d
            max_z = max(max_z, abs(z))
        else:
            windows.append((cur_start, cur_end, max_z))
            cur_start = cur_end = d
            max_z = abs(z)
    windows.append((cur_start, cur_end, max_z))

    out = []
    for start_d, end_d, score in windows:
        confidence = min(1.0, score / 4.0)
        severity = _z_severity(score)
        start_ts = f"{start_d.isoformat()}T00:00:00Z"
        end_ts = f"{end_d.isoformat()}T00:00:00Z"
        out.append(
            AnomalyOut(
                metric_name=metric_name,
                start_ts=start_ts,
                end_ts=end_ts,
                severity=severity,
                score=round(score, 4),
                confidence=round(confidence, 4),
                summary=_summary(metric_name),
            )
        )
    return out


def detect_anomalies(
    db: Session,
    start_date: date,
    end_date: date,
    user_id: str | None = None,
) -> list[AnomalyOut]:
    """
    Detect anomalies using rolling 30-day baseline (mean, std). Previous days only.
    Merge consecutive anomalous days into one window. No DB writes.
    """
    query_start = start_date - timedelta(days=ROLLING_DAYS)
    start_dt = datetime.combine(query_start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc)
    end_dt += timedelta(days=1)

    by_metric = _daily_buckets(db, start_dt, end_dt, user_id)
    all_anomalies: list[AnomalyOut] = []

    for metric_name, day_values in by_metric.items():
        sorted_dates = sorted(day_values.keys())
        anomalous: list[tuple[date, float]] = []
        for d in sorted_dates:
            if d < start_date or d > end_date:
                continue
            value = day_values.get(d)
            if value is None:
                continue
            baseline_dates = [d - timedelta(days=i) for i in range(1, ROLLING_DAYS + 1)]
            baseline_values = [day_values.get(bd) for bd in baseline_dates if day_values.get(bd) is not None]
            if len(baseline_values) < MIN_BASELINE_DAYS:
                continue
            mean = statistics.mean(baseline_values)
            try:
                std = statistics.stdev(baseline_values)
            except statistics.StatisticsError:
                continue
            if std == 0:
                continue
            z = (value - mean) / std
            if abs(z) >= Z_THRESHOLD:
                anomalous.append((d, z))
        all_anomalies.extend(_merge_consecutive(metric_name, anomalous))

    all_anomalies.sort(key=lambda a: a.start_ts, reverse=True)
    return all_anomalies
