"""Inventory routes — reads for any authenticated user, writes for ADMIN."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, CurrentUser
from app.db.session import get_db
from app.models.item import Item, ItemSource
from app.models.loan import Loan
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.services.files import save_photo

router = APIRouter(prefix="/api/v1/items", tags=["items"])


def _get_item_or_404(item_id: int, db: Annotated[Session, Depends(get_db)]) -> Item:
    """Fetch an item by id, or raise 404."""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.get("", response_model=list[ItemRead])
def list_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Item]:
    """List inventory with ?page= and ?limit= pagination."""
    stmt = select(Item).order_by(Item.id).offset((page - 1) * limit).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item: Annotated[Item, Depends(_get_item_or_404)],
    current_user: CurrentUser,
) -> Item:
    """Retrieve a single item."""
    return item


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str, Form(min_length=1, max_length=200)],
    quantity_total: Annotated[int, Form(ge=0)] = 0,
    category: Annotated[str | None, Form(max_length=100)] = None,
    description: Annotated[str | None, Form()] = None,
    condition: Annotated[str | None, Form(max_length=100)] = None,
    unit_price: Annotated[float | None, Form()] = None,
    source: Annotated[ItemSource, Form()] = ItemSource.MANUAL,
    photo: Annotated[UploadFile | None, File()] = None,
) -> Item:
    """Create an item (ADMIN only). Stock starts full: available = total."""
    data = ItemCreate(
        name=name,
        category=category,
        description=description,
        quantity_total=quantity_total,
        condition=condition,
        unit_price=unit_price,
        source=source,
    )
    item = Item(
        **data.model_dump(),
        quantity_available=data.quantity_total,  # the critical line — see below
        photo_url=save_photo(photo) if photo is not None else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=ItemRead)
def update_item(
    admin: AdminUser,
    item: Annotated[Item, Depends(_get_item_or_404)],
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str | None, Form(min_length=1, max_length=200)] = None,
    category: Annotated[str | None, Form(max_length=100)] = None,
    description: Annotated[str | None, Form()] = None,
    quantity_total: Annotated[int | None, Form(ge=0)] = None,
    condition: Annotated[str | None, Form(max_length=100)] = None,
    unit_price: Annotated[float | None, Form()] = None,
    source: Annotated[ItemSource | None, Form()] = None,
    photo: Annotated[UploadFile | None, File()] = None,
) -> Item:
    """Update an item (ADMIN only). All fields optional."""
    data = ItemUpdate(
        name=name,
        category=category,
        description=description,
        quantity_total=quantity_total,
        condition=condition,
        unit_price=unit_price,
        source=source,
    )
    for field, value in data.model_dump().items():
        if value is not None:
            setattr(item, field, value)
    if photo is not None:
        item.photo_url = save_photo(photo)
    # invariant: you can never lend out more than the total
    item.quantity_available = min(item.quantity_available, item.quantity_total)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    admin: AdminUser,
    item: Annotated[Item, Depends(_get_item_or_404)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete an item (ADMIN only). Refused if it has loan history."""
    has_loans = db.scalar(select(Loan).where(Loan.item_id == item.id).limit(1))
    if has_loans is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Item has loan history and cannot be deleted",
        )
    db.delete(item)
    db.commit()
