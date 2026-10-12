from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Insight(Base):
    __tablename__ = "insights"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "fingerprint",
            name="uq_insights_company_fingerprint",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "companies.id",
            name="fk_insights_company",
        ),
        nullable=False,
    )

    analysis_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "statistical_analyses.id",
            name="fk_insights_analysis",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    dataset_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "datasets.id",
            name="fk_insights_dataset",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    rule_code: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    evidence: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="info",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )