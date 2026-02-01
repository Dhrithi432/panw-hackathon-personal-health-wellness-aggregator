from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Anomaly(Base):
    __tablename__ = "anomaly"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    start_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    end_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    severity: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    __table_args__ = (
        Index("ix_anomaly_metric_start", "metric_name", "start_ts"),
    )
