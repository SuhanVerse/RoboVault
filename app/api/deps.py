"""Reusable FastAPI dependencies: current user and role checks."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.db.session import get_db
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the bearer token to a real user, or raise 401."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = security.decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )
    return user


def require_role(role: UserRole):
    """Return a dependency that only lets users with the given role through."""

    def checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role is not role:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return checker


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
