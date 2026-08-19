"""OCR routes — parse bill/demand-form images into suggestions (ADMIN only)."""

from typing import Annotated

import pytesseract
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import AdminUser
from app.db.session import get_db
from app.models.bill import BillStatus, BillUpload
from app.ocr.parser import parse_line_items
from app.ocr.preprocess import preprocess_image
from app.services.files import save_photo

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


@router.post("/parse-bill")
def parse_bill(
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> dict:
    """Extract line items from a bill image → suggestions (never creates items)."""
    # 1. Save the image (same helper as item photos, from Step 16)
    image_url = save_photo(file)

    # 2. Record the upload as PENDING
    upload = BillUpload(image_url=image_url, uploaded_by=admin.id)
    db.add(upload)
    db.commit()
    db.refresh(upload)

    # 3. Run the OCR pipeline: preprocess → tesseract → parser
    try:
        image = preprocess_image(image_url.lstrip("/"))
        text = pytesseract.image_to_string(image)
        suggestions = parse_line_items(text)
    except Exception:  # noqa: BLE001 — any OCR failure → 422, never a 500
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read the bill image",
        ) from None

    # 4. An empty parse is also a failure — the endpoint must never crash
    if not suggestions:
        upload.status = BillStatus.FAILED
        db.commit()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read the bill image",
        )
    upload.status = BillStatus.PROCESSED
    upload.parsed_json = suggestions
    db.commit()

    # 5. Return suggestions only — the manual form must confirm them
    return {"id": upload.id, "status": upload.status.value, "suggestions": suggestions}
