from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/items", tags=["items"])


@router.get("")
def list_items() -> dict[str, str]:
    return {"detail": "items endpoints not implemented yet"}
