"""Authentication and user administration."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.user import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


# ─────────────────────────────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────────────────────────────
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
        subject = payload.get("sub")
        if subject is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user_id = int(subject)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Administrator-only guard."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return current_user


def require_officer(current_user: User = Depends(get_current_user)) -> User:
    """Inspection guard: officers and administrators may run inspections."""
    if current_user.role not in (UserRole.ADMIN, UserRole.OFFICER):
        raise HTTPException(
            status_code=403,
            detail="Officer or administrator access required to run inspections",
        )
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a user account.

    Restricted to administrators — a public sign-up endpoint on an enforcement
    system would let anyone mint an admin account. Bootstrap the first admin
    with `python seed.py`.
    """
    existing = db.execute(select(User).where(User.email == user_data.email)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        department=user_data.department,
        employee_id=user_data.employee_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == credentials.email)).scalars().first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# User administration (admin only)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/users", response_model=list[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    statement = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    if role is not None:
        statement = statement.where(User.role == role)
    return db.execute(statement).scalars().all()


@router.get("/users/count")
def count_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.scalar(select(func.count()).select_from(User)) or 0
    active = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    return {"total": int(total), "active": int(active)}


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if password:
        user.hashed_password = get_password_hash(password)
    for field, value in data.items():
        setattr(user, field, value)

    if user.id == current_user.id and data.get("is_active") is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return None
