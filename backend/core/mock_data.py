"""
Deterministic mock data for demo mode.

- 90 days of data for 5 metrics: sleep_hours, steps, calories, resting_hr, weight.
- Known anomaly: resting_hr spike for exactly 3 consecutive days (days 45–47).
- Known correlation: sleep_hours negatively correlates with calories with 1-day lag
  (formula: calories[d] = 2000 - 80 * (sleep_hours[d-1] - 6.5)).
"""
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import Anomaly, HealthMetric

DEMO_USER_ID = "demo-user"
DEMO_SOURCE = "demo"
START_DATE = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
NUM_DAYS = 90
ANOMALY_START_DAY = 45  # 3-day resting_hr spike: days 45, 46, 47


def _ts(day_offset: int) -> datetime:
    return START_DATE + timedelta(days=day_offset)


def _sleep_hours(day: int) -> float:
    """Deterministic: weekly pattern 5.5–8 h."""
    return 5.5 + 2.5 * math.sin(2 * math.pi * day / 7)


def _steps(day: int) -> float:
    """Deterministic: ~4k–8k steps."""
    return 6000.0 + 2000.0 * math.sin(2 * math.pi * day / 5)


def _resting_hr(day: int) -> float:
    """Deterministic: ~60–65 bpm, spike +15 on days 45–47."""
    base = 62.0 + 3.0 * math.sin(day / 10.0)
    if ANOMALY_START_DAY <= day < ANOMALY_START_DAY + 3:
        return base + 15.0
    return base


def _weight(day: int) -> float:
    """Deterministic: ~69.6–70.4 kg."""
    return 70.0 + 0.4 * math.sin(2 * math.pi * day / 14)


def _calories(day: int, sleep_prev: float) -> float:
    """Negative correlation with previous day's sleep (1-day lag)."""
    return 2000.0 - 80.0 * (sleep_prev - 6.5)


def seed_demo_data(db: Session) -> None:
    """Insert deterministic 90-day metrics and one anomaly. Idempotent only if table empty."""
    sleep_prev = 6.5  # for day 0 calories
    for day in range(NUM_DAYS):
        ts = _ts(day)
        sleep = _sleep_hours(day)
        steps = _steps(day)
        resting_hr = _resting_hr(day)
        weight = _weight(day)
        calories = _calories(day, sleep_prev)
        sleep_prev = sleep

        for metric_name, value, unit in [
            ("sleep_hours", round(sleep, 2), "hours"),
            ("steps", round(steps, 0), "count"),
            ("calories", round(calories, 0), "kcal"),
            ("resting_hr", round(resting_hr, 1), "bpm"),
            ("weight", round(weight, 2), "kg"),
        ]:
            db.add(
                HealthMetric(
                    user_id=DEMO_USER_ID,
                    source=DEMO_SOURCE,
                    metric_name=metric_name,
                    value=value,
                    unit=unit,
                    ts=ts,
                    metadata_=None,
                )
            )

    anomaly_start = _ts(ANOMALY_START_DAY)
    anomaly_end = _ts(ANOMALY_START_DAY + 3)
    db.add(
        Anomaly(
            metric_name="resting_hr",
            start_ts=anomaly_start,
            end_ts=anomaly_end,
            severity="medium",
            score=0.85,
            signals={"spike_days": 3, "note": "Known demo anomaly"},
            created_at=START_DATE,
        )
    )
    db.commit()
