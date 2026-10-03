from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StatisticalResult(Base):
    __tablename__ = "statistical_results"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "statistical_analyses.id",
            name="fk_statistical_results_analysis",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    metric_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    numeric_result: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    result_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )