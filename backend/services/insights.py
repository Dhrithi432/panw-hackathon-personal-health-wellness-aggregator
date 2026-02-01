"""
Small usage example of core.llm for insight text generation.
Builds a structured payload and calls generate_insight_text.
"""
from core.llm import generate_insight_text


def example_insight_from_structured_data(
    baseline_deviations: dict[str, float] | None = None,
    anomaly_summaries: list[str] | None = None,
    correlation_summaries: list[str] | None = None,
) -> str:
    """
    Example: build payload from baseline deviations, anomaly summaries,
    and correlation summaries, then generate constrained insight text.
    """
    payload: dict = {}
    if baseline_deviations:
        payload["baseline_deviations"] = baseline_deviations
    if anomaly_summaries:
        payload["anomaly_summaries"] = anomaly_summaries
    if correlation_summaries:
        payload["correlation_summaries"] = correlation_summaries
    if not payload:
        payload["note"] = "No structured data provided."
    return generate_insight_text(payload)
