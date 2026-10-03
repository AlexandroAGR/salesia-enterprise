from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "datasets.id",
            name="fk_observations_dataset",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    variable_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "dataset_variables.id",
            name="fk_observations_variable",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    numeric_value: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    text_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )