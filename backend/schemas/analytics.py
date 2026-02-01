from typing import Literal

from pydantic import BaseModel


class WellnessScoreResponse(BaseModel):
    score: int
    components: dict[str, int]
    trend: Literal["up", "down", "flat"]
    top_driver: str | None
