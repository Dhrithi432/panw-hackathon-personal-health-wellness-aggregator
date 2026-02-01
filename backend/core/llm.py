"""
Minimal LangChain wrapper for insight text generation.
LLM receives only structured inputs; constrained to avoid diagnosis and invented metrics.
"""
import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = """You write short, factual insight summaries from structured health data only.
Rules:
- Do NOT use medical diagnosis language (e.g. "you have", "diagnosis", "condition").
- Include uncertainty phrasing (e.g. "may suggest", "could indicate", "appears to").
- Use ONLY metrics and facts provided in the input; never invent metrics or numbers.
- Keep the response to 1-3 sentences. Output plain text only."""

FALLBACK_INSIGHT = (
    "Based on the provided data, some patterns may be worth noting; "
    "consider reviewing with your care team if you have questions."
)


def generate_insight_text(payload: dict) -> str:
    """
    Generate insight text from structured payload (baseline deviations,
    anomaly summaries, correlation summaries). Returns deterministic fallback
    if OPENAI_API_KEY is not set.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return FALLBACK_INSIGHT

    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=api_key,
        )
        # Only pass structured data as JSON; no free-form user text
        body = json.dumps(payload, default=str)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Summarize this structured data in one short insight.\n\n{body}"),
        ]
        message = llm.invoke(messages)
        if message and hasattr(message, "content") and message.content:
            return message.content.strip()
    except Exception:
        pass
    return FALLBACK_INSIGHT
