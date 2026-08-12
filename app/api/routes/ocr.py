from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/ocr", tags=["items"])


@router.get("")
def list_items() -> dict[str, str]:
    """Placeholder so the router shows up in the OpenAPI docs."""
    return {"detail": "items endpoints not implemented yet"}
