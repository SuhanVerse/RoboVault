"""Item CRUD happy-path tests.

Writes (POST/PUT/DELETE) are ADMIN-only — the 401/403 sides of that live in
tests/test_rbac.py. These cover the success paths and the stock invariant.
"""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.loan import Loan
from app.models.user import User

ITEMS_URL = "/api/v1/items"


def _create_item(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
    name: str = "ESP32-CAM",
    quantity_total: str = "5",
) -> dict:
    response = client.post(
        ITEMS_URL,
        data={"name": name, "quantity_total": quantity_total},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 201
    return response.json()


def test_admin_creates_item_with_full_stock(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Creating an item initializes available stock to the total."""
    body = _create_item(client, admin_user, auth_header)
    assert body["name"] == "ESP32-CAM"
    assert body["quantity_total"] == 5
    assert body["quantity_available"] == 5
    assert body["source"] == "MANUAL"


def test_admin_can_list_and_fetch_items(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """List returns the created item, and GET by id returns it too."""
    body = _create_item(client, admin_user, auth_header)

    response = client.get(ITEMS_URL, headers=auth_header(admin_user))
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(f"{ITEMS_URL}/{body['id']}", headers=auth_header(admin_user))
    assert response.status_code == 200
    assert response.json()["name"] == "ESP32-CAM"


def test_admin_can_update_item_and_clamps_available_stock(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Updating quantity_total never leaves available above the new total."""
    body = _create_item(client, admin_user, auth_header, quantity_total="5")

    response = client.put(
        f"{ITEMS_URL}/{body['id']}",
        data={"name": "Raspberry Pi 5", "quantity_total": "2"},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Raspberry Pi 5"
    assert updated["quantity_total"] == 2
    assert updated["quantity_available"] == 2  # clamped: never more than total


def test_admin_can_delete_item(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Deleting an item returns 204 and the item is gone afterwards."""
    body = _create_item(client, admin_user, auth_header)

    response = client.delete(
        f"{ITEMS_URL}/{body['id']}", headers=auth_header(admin_user)
    )
    assert response.status_code == 204

    response = client.get(f"{ITEMS_URL}/{body['id']}", headers=auth_header(admin_user))
    assert response.status_code == 404


def test_delete_item_with_loan_history_returns_409(
    client: TestClient,
    db: Session,
    admin_user: User,
    member_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """An item with loan history cannot be deleted (409)."""
    item = Item(name="Sensor Kit", quantity_total=2, quantity_available=2)
    db.add(item)
    db.commit()

    db.add(Loan(item_id=item.id, borrower_id=member_user.id, quantity=1))
    db.commit()

    response = client.delete(f"{ITEMS_URL}/{item.id}", headers=auth_header(admin_user))
    assert response.status_code == 409
    assert response.json() == {"detail": "Item has loan history and cannot be deleted"}


def test_photo_upload_returns_photo_url(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """A valid image upload is saved and its URL is returned."""
    response = client.post(
        ITEMS_URL,
        data={"name": "Rover"},
        files={"photo": ("rover.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 201
    photo_url = response.json()["photo_url"]
    assert photo_url is not None
    assert photo_url.endswith(".jpg")


def test_create_item_rejects_unsupported_image(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """A non-image upload is rejected with 400."""
    response = client.post(
        ITEMS_URL,
        data={"name": "Rover"},
        files={"photo": ("notes.txt", b"hello", "text/plain")},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported image type"}


def test_admin_can_update_item_with_photo(
    client: TestClient,
    admin_user: User,
    auth_header: Callable[[User], dict[str, str]],
) -> None:
    """Updating an item with a photo replaces its photo_url."""
    body = _create_item(client, admin_user, auth_header)

    response = client.put(
        f"{ITEMS_URL}/{body['id']}",
        data={"name": "Rover v2"},
        files={"photo": ("rover2.jpg", b"new-image-bytes", "image/jpeg")},
        headers=auth_header(admin_user),
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Rover v2"
    assert updated["photo_url"] is not None
    assert updated["photo_url"].endswith(".jpg")
