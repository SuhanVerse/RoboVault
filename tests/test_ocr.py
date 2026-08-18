"""Tests for the OCR bill-parsing endpoint.

All OCR calls are mocked so the tests run without the tesseract binary.
"""

from io import BytesIO
from unittest.mock import patch

from PIL import Image


def _make_image_bytes() -> BytesIO:
    """Create a minimal PNG in memory (no file on disk)."""
    img = Image.new("RGB", (200, 50), color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ── Happy path ────────────────────────────────────────────────────────


def test_parse_bill_returns_suggestions(client, admin_user, auth_header):
    """ADMIN uploads a bill image → 200 with parsed suggestions."""
    fake_ocr_text = "Widget 3 x 25.00 rs\nGadget 10 5.50"
    img_buf = _make_image_bytes()

    with (
        patch("app.api.routes.ocr.preprocess_image") as mock_preprocess,
        patch(
            "app.api.routes.ocr.pytesseract.image_to_string", return_value=fake_ocr_text
        ),
    ):
        mock_preprocess.return_value = Image.new("L", (200, 50))
        resp = client.post(
            "/api/v1/ocr/parse-bill",
            files={"file": ("bill.png", img_buf, "image/png")},
            headers=auth_header(admin_user),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PROCESSED"
    assert len(data["suggestions"]) == 2
    assert data["suggestions"][0]["name"] == "Widget"
    assert data["suggestions"][0]["quantity"] == 3
    assert data["suggestions"][0]["price"] == 25.0


# ── Failure paths ─────────────────────────────────────────────────────


def test_parse_bill_blank_image_returns_422(client, admin_user, auth_header):
    """OCR returns no suggestions → 422."""
    img_buf = _make_image_bytes()

    with (
        patch("app.api.routes.ocr.preprocess_image") as mock_preprocess,
        patch("app.api.routes.ocr.pytesseract.image_to_string", return_value=""),
    ):
        mock_preprocess.return_value = Image.new("L", (200, 50))
        resp = client.post(
            "/api/v1/ocr/parse-bill",
            files={"file": ("blank.png", img_buf, "image/png")},
            headers=auth_header(admin_user),
        )

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Could not read the bill image"


def test_parse_bill_tesseract_error_returns_422(client, admin_user, auth_header):
    """Tesseract raises an exception → 422, no crash."""
    img_buf = _make_image_bytes()

    with (
        patch("app.api.routes.ocr.preprocess_image") as mock_preprocess,
        patch(
            "app.api.routes.ocr.pytesseract.image_to_string",
            side_effect=RuntimeError("tesseract not found"),
        ),
    ):
        mock_preprocess.return_value = Image.new("L", (200, 50))
        resp = client.post(
            "/api/v1/ocr/parse-bill",
            files={"file": ("corrupt.png", img_buf, "image/png")},
            headers=auth_header(admin_user),
        )

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Could not read the bill image"


# ── RBAC ──────────────────────────────────────────────────────────────


def test_member_cannot_call_ocr(client, member_user, auth_header):
    """MEMBER role → 403 on /ocr/parse-bill."""
    img_buf = _make_image_bytes()
    resp = client.post(
        "/api/v1/ocr/parse-bill",
        files={"file": ("bill.png", img_buf, "image/png")},
        headers=auth_header(member_user),
    )
    assert resp.status_code == 403


def test_unauthenticated_cannot_call_ocr(client):
    """No token → 401 on /ocr/parse-bill."""
    img_buf = _make_image_bytes()
    resp = client.post(
        "/api/v1/ocr/parse-bill",
        files={"file": ("bill.png", img_buf, "image/png")},
    )
    assert resp.status_code == 401
