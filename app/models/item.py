from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.loan import Loan


class ItemSource(str, Enum):

    BILL = "BILL"
    DEMAND_FORM = "DEMAND_FORM"
    MANUAL = "MANUAL"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    quantity_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    condition: Mapped[str | None] = mapped_column(String(100))
    photo_url: Mapped[str | None] = mapped_column(String(255))
    unit_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    source: Mapped[ItemSource] = mapped_column(
        SAEnum(ItemSource, name="item_source"),
        default=ItemSource.MANUAL,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    loans: Mapped[list["Loan"]] = relationship(back_populates="item")
