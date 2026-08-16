"""Shared file helpers — photo uploads."""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def save_photo(file: UploadFile) -> str:
    """Save an uploaded image under uploads/ and return its URL path."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Unsupported image type"
        )
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / filename
    path.write_bytes(file.file.read())
    return f"/uploads/{filename}"
