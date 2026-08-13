"""Authentication routes: register and login."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import security
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    """Create a new user account (default role: GUEST)."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=security.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: dict[str, str], db: Annotated[Session, Depends(get_db)]) -> Token:
    """Verify credentials and return a JWT bearer token."""
    email = payload.get("email", "")
    password = payload.get("password", "")
    user = db.query(User).filter(User.email == email).first()
    if user is None or not security.verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return Token(access_token=security.create_access_token(str(user.id)))
