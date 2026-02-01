from pydantic import BaseModel


class TimelinePoint(BaseModel):
    ts: str  # ISO string
    metrics: dict[str, float]


class TimelineResponse(BaseModel):
    points: list[TimelinePoint]
