"""
FastAPI authentication dependencies and role guards.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenError, decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

ROLE_ORDER = {
    "visitor": 1,
    "analyst": 2,
    "admin": 3,
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    return user


def require_role(min_role: str):
    min_level = ROLE_ORDER[min_role]

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if ROLE_ORDER.get(current_user.role, 0) < min_level:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


require_admin = require_role("admin")
require_analyst = require_role("analyst")


def get_allowed_platforms(user: User) -> list[str] | None:
    if user.role == "admin" or user.platform_scope == "all":
        return None
    return [item.strip() for item in user.platform_scope.split(",") if item.strip()]
