"""
Authentication API routes.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.core.database import get_db
from app.core.security import create_access_token, create_reset_token, hash_password, hash_reset_token, verify_password
from app.models import AuditLog, PasswordResetToken, User
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.schemas.common import UnifiedResponse
from app.services.audit_service import write_audit_log

router = APIRouter()
RESET_TOKEN_EXPIRE_MINUTES = 30


def _to_user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def _create_session(user: User) -> TokenResponse:
    token, expires_at = create_access_token(
        {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "platform_scope": user.platform_scope,
        }
    )
    return TokenResponse(
        access_token=token,
        expires_at=expires_at.isoformat(),
        user=_to_user_response(user),
    )


@router.post("/register", response_model=UnifiedResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a user. The first registered account becomes the admin."""
    query = db.query(User).filter(User.username == payload.username)
    if payload.email:
        query = db.query(User).filter((User.username == payload.username) | (User.email == payload.email))
    existing = query.first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    role = "admin" if db.query(User).count() == 0 else "analyst"
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=role,
        platform_scope="all",
        is_active=True,
    )
    db.add(user)
    write_audit_log(
        db,
        operator=user.username,
        action="register",
        target_type="user",
        target_id=user.username,
        after={"username": user.username, "role": role, "platform_scope": user.platform_scope},
    )
    db.commit()
    db.refresh(user)

    return {
        "code": 201,
        "data": _create_session(user),
        "message": "registered",
    }


@router.post("/login", response_model=UnifiedResponse[TokenResponse])
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login with username and password."""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")

    user.last_login_at = datetime.now()
    write_audit_log(
        db,
        operator=user.username,
        action="login",
        target_type="user",
        target_id=user.id,
        note="User logged in",
    )
    db.commit()
    db.refresh(user)

    return {
        "code": 200,
        "data": _create_session(user),
        "message": "success",
    }


@router.get("/me", response_model=UnifiedResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user."""
    return {
        "code": 200,
        "data": _to_user_response(current_user),
        "message": "success",
    }


@router.post("/password", response_model=UnifiedResponse[dict])
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password after verifying the old password."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    write_audit_log(
        db,
        operator=current_user.username,
        action="change_password",
        target_type="user",
        target_id=current_user.id,
    )
    db.commit()
    return {
        "code": 200,
        "data": {"id": current_user.id},
        "message": "password updated",
    }


@router.post("/password/reset/request", response_model=UnifiedResponse[dict])
async def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Create a one-time password reset token for local delivery."""
    if not payload.username and not payload.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email is required")

    query = db.query(User)
    if payload.username:
        query = query.filter(User.username == payload.username)
    if payload.email:
        query = query.filter(User.email == payload.email)
    user = query.first()

    if not user or not user.is_active:
        return {
            "code": 200,
            "data": {"reset_token": None, "expires_at": None},
            "message": "If the account exists, a reset token has been generated",
        }

    token = create_reset_token()
    expires_at = datetime.now() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(token),
        expires_at=expires_at,
    )
    db.add(reset_token)
    write_audit_log(
        db,
        operator=user.username,
        action="request_password_reset",
        target_type="user",
        target_id=user.id,
        note="Password reset token generated",
    )
    db.commit()

    return {
        "code": 200,
        "data": {"reset_token": token, "expires_at": expires_at.isoformat()},
        "message": "reset token generated",
    }


@router.post("/password/reset/confirm", response_model=UnifiedResponse[dict])
async def confirm_password_reset(payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    """Reset password using a one-time token."""
    token_hash = hash_reset_token(payload.token)
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    if not reset_token or reset_token.used_at is not None or reset_token.expires_at < datetime.now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")

    user.password_hash = hash_password(payload.new_password)
    reset_token.used_at = datetime.now()
    write_audit_log(
        db,
        operator=user.username,
        action="reset_password",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    return {
        "code": 200,
        "data": {"id": user.id},
        "message": "password reset",
    }


@router.get("/audit-logs", response_model=UnifiedResponse[dict])
async def list_my_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return current user's audit log records."""
    query = db.query(AuditLog).filter(AuditLog.operator == current_user.username)
    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size
    return {
        "code": 200,
        "data": {
            "items": [
                {
                    "id": log.id,
                    "operator": log.operator,
                    "action": log.action,
                    "target_type": log.target_type,
                    "target_id": log.target_id,
                    "before_json": log.before_json,
                    "after_json": log.after_json,
                    "note": log.note,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
        "message": "success",
    }


@router.get("/users", response_model=UnifiedResponse[dict])
async def list_users(
    role: str = None,
    is_active: bool = None,
    keyword: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List users for administrator management."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if keyword:
        query = query.filter(User.username.contains(keyword))

    total = query.count()
    users = query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size
    return {
        "code": 200,
        "data": {
            "items": [_to_user_response(user) for user in users],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
        "message": "success",
    }


@router.patch("/users/{user_id}", response_model=UnifiedResponse[UserResponse])
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a user's role, platform scope, or active status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    before = {
        "role": user.role,
        "platform_scope": user.platform_scope,
        "is_active": user.is_active,
    }
    if payload.role is not None:
        user.role = payload.role
    if payload.platform_scope is not None:
        user.platform_scope = payload.platform_scope.strip() or "all"
    if payload.is_active is not None:
        if user.id == current_user.id and payload.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable current user")
        user.is_active = payload.is_active

    after = {
        "role": user.role,
        "platform_scope": user.platform_scope,
        "is_active": user.is_active,
    }
    write_audit_log(
        db,
        operator=current_user.username,
        action="update_user",
        target_type="user",
        target_id=user.id,
        before=before,
        after=after,
    )
    db.commit()
    db.refresh(user)
    return {
        "code": 200,
        "data": _to_user_response(user),
        "message": "user updated",
    }
