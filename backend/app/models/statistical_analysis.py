from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StatisticalAnalysis(Base):
    __tablename__ = "statistical_analyses"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "companies.id",
            name="fk_statistical_analyses_company",
        ),
        nullable=False,
    )

    dataset_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "datasets.id",
            name="fk_statistical_analyses_dataset",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    analysis_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="completed",
    )

    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_statistical_analyses_created_by",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )