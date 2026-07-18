"""Helpers for authenticated API tests."""

from app.core.database import Base, SessionLocal, engine
from app.core.security import create_access_token, hash_password
from app.models import User

TEST_PASSWORD = "TestPass123!"


def ensure_test_user(
    username: str = "pytest_admin",
    role: str = "admin",
    platform_scope: str = "all",
) -> User:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@example.test",
                password_hash=hash_password(TEST_PASSWORD),
                role=role,
                platform_scope=platform_scope,
                is_active=True,
            )
            db.add(user)
        else:
            user.role = role
            user.platform_scope = platform_scope
            user.is_active = True
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def make_auth_headers(
    username: str = "pytest_admin",
    role: str = "admin",
    platform_scope: str = "all",
) -> dict[str, str]:
    user = ensure_test_user(username=username, role=role, platform_scope=platform_scope)
    token, _ = create_access_token(
        {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "platform_scope": user.platform_scope,
        }
    )
    return {"Authorization": f"Bearer {token}"}
