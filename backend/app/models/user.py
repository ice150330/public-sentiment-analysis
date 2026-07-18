"""
User account model for SQLite-backed authentication.
"""

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, func

from app.core.database import Base


class User(Base):
    """Application user with a simple role and optional platform scope."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default="analyst")
    platform_scope = Column(String(255), nullable=False, default="all")
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_users_role_active", "role", "is_active"),
        Index("idx_users_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
