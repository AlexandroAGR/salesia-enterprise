from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DatasetVariable(Base):
    __tablename__ = "dataset_variables"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    dataset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "datasets.id",
            name="fk_dataset_variables_dataset",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    data_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    variable_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )