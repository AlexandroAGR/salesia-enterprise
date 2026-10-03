from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BayesAnalysis(Base):
    __tablename__ = "bayes_analyses"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "statistical_analyses.id",
            name="fk_bayes_analyses_analysis",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    probability_a: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    probability_b_given_a: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    probability_b: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    posterior_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )