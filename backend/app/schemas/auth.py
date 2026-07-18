"""Authentication request and response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["admin", "analyst", "visitor"]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    role: UserRole
    platform_scope: str = "all"
    is_active: bool

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserResponse


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    username: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)


class UserUpdateRequest(BaseModel):
    role: UserRole | None = None
    platform_scope: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
