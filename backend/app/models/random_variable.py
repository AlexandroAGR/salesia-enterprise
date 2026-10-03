from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RandomVariable(Base):
    __tablename__ = "random_variables"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "datasets.id",
            name="fk_random_variables_dataset",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    variable_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "dataset_variables.id",
            name="fk_random_variables_variable",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    distribution_name: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )