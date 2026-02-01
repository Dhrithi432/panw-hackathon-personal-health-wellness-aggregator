from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from core.config import DEMO_MODE
from db.base import Base
from db.session import SessionLocal, engine
from models import HealthMetric
from routers.health import router as health_router
from routers.insights import router as insights_router
from routers.analytics import router as analytics_router

app = FastAPI(title="Smart Health API")


@app.on_event("startup")
def startup() -> None:
    if not DEMO_MODE:
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(HealthMetric.id).limit(1)) is None:
            from core.mock_data import seed_demo_data

            seed_demo_data(db)
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/health")
app.include_router(insights_router, prefix="/insights")
app.include_router(analytics_router, prefix="/analytics")


@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
