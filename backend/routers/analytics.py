from fastapi import APIRouter

from schemas.analytics import WellnessScoreResponse

router = APIRouter()

@router.get("/wellness-score", response_model=WellnessScoreResponse)
def get_wellness_score():
    return WellnessScoreResponse(
        score=0,
        components={},
        trend="flat",
        top_driver=None,
    )
