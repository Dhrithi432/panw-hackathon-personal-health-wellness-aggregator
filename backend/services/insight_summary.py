"""
AI insight synthesis from computed signals only. Deterministic fallback when no API key.
No DB writes; no writes to Insight table.
"""
from datetime import date

from sqlalchemy.orm import Session

from core.llm import FALLBACK_INSIGHT, generate_insight_text
from schemas.insight_summary import InsightSummaryResponse
from services.anomalies import detect_anomalies
from services.correlations import compute_correlations
from services.wellness import compute_wellness_score

TOP_ANOMALIES = 3
TOP_CORRELATIONS = 3


def _deterministic_summary(
    wellness_score: int,
    trend: str,
    top_driver: str | None,
    anomaly_count: int,
    correlation_count: int,
) -> str:
    """Fallback text: trend, top_driver, counts; no medical diagnosis."""
    parts = []
    if wellness_score >= 0 or trend != "flat" or top_driver:
        parts.append(f"Wellness score is {wellness_score} with trend {trend}.")
        if top_driver:
            parts.append(f"Largest contributor in this window: {top_driver.replace('_', ' ')}.")
    if anomaly_count > 0:
        parts.append(f"{anomaly_count} anomaly window(s) were detected.")
    if correlation_count > 0:
        parts.append(f"{correlation_count} notable correlation(s) were found.")
    if not parts:
        return "No notable signals in this window; data may be insufficient."
    return " ".join(parts)


def generate_insight_summary(
    db: Session,
    start_date: date,
    end_date: date,
    user_id: str | None = None,
) -> InsightSummaryResponse:
    """
    Synthesize insight text from anomalies, correlations, and wellness score.
    Uses core.llm.generate_insight_text when API key is set; otherwise deterministic text.
    """
    anomalies = detect_anomalies(db, start_date, end_date, user_id=user_id)
    correlations = compute_correlations(db, start_date, end_date, user_id=user_id)
    wellness = compute_wellness_score(db, start_date, end_date, user_id=user_id)

    top_anomalies = sorted(anomalies, key=lambda a: a.score, reverse=True)[:TOP_ANOMALIES]
    top_correlations = correlations[:TOP_CORRELATIONS]

    payload = {
        "window": {"start_date": str(start_date), "end_date": str(end_date)},
        "wellness": {
            "score": wellness.score,
            "trend": wellness.trend,
            "top_driver": wellness.top_driver,
        },
        "anomalies": [
            {
                "metric_name": a.metric_name,
                "start_ts": a.start_ts,
                "end_ts": a.end_ts,
                "severity": a.severity,
                "score": a.score,
            }
            for a in top_anomalies
        ],
        "correlations": [
            {
                "metric_a": c.metric_a,
                "metric_b": c.metric_b,
                "lag_days": c.lag_days,
                "correlation": c.correlation,
            }
            for c in top_correlations
        ],
    }

    try:
        text = generate_insight_text(payload)
        if text.strip() == FALLBACK_INSIGHT.strip():
            text = _deterministic_summary(
                wellness.score,
                wellness.trend,
                wellness.top_driver,
                len(anomalies),
                len(correlations),
            )
    except Exception:
        text = _deterministic_summary(
            wellness.score,
            wellness.trend,
            wellness.top_driver,
            len(anomalies),
            len(correlations),
        )

    # Confidence: 0.0 if no signals; else average of max anomaly conf, max correlation conf, score/100
    has_wellness = bool(wellness.components)
    max_anom_conf = max((a.confidence for a in anomalies), default=0.0)
    max_corr_conf = max((c.confidence for c in correlations), default=0.0)
    wellness_norm = wellness.score / 100.0 if has_wellness else 0.0
    if not anomalies and not correlations and not has_wellness:
        confidence = 0.0
    else:
        confidence = (max_anom_conf + max_corr_conf + wellness_norm) / 3.0
    confidence = round(min(1.0, max(0.0, confidence)), 4)

    signals_used = {
        "wellness": {
            "score": wellness.score,
            "trend": wellness.trend,
            "top_driver": wellness.top_driver,
        },
        "anomaly_count": len(anomalies),
        "correlation_count": len(correlations),
        "top_anomalies": [
            {
                "metric_name": a.metric_name,
                "start_ts": a.start_ts,
                "end_ts": a.end_ts,
                "severity": a.severity,
                "score": a.score,
            }
            for a in top_anomalies
        ],
        "top_correlations": [
            {
                "metric_a": c.metric_a,
                "metric_b": c.metric_b,
                "lag_days": c.lag_days,
                "correlation": c.correlation,
            }
            for c in top_correlations
        ],
    }

    return InsightSummaryResponse(
        text=text,
        confidence=confidence,
        signals_used=signals_used,
    )
