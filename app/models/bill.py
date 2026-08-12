from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BillStatus(str, Enum):

    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class BillUpload(Base):

    __tablename__ = "bill_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    image_url: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False)
    status: Mapped[BillStatus] = mapped_column(
        SAEnum(BillStatus, name="bill_status"),
        default=BillStatus.PENDING,
        nullable=False,
    )
    parsed_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
