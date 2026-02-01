from fastapi import APIRouter

from schemas.insights import AnomaliesResponse, CorrelationsResponse

router = APIRouter()


@router.get("/correlations", response_model=CorrelationsResponse)
def get_correlations():
    return CorrelationsResponse(items=[])


@router.get("/anomalies", response_model=AnomaliesResponse)
def get_anomalies():
    return AnomaliesResponse(items=[])
