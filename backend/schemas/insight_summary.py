from typing import Any

from pydantic import BaseModel


class InsightSummaryResponse(BaseModel):
    text: str
    confidence: float
    signals_used: dict[str, Any]
