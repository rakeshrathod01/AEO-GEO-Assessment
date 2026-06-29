"""Authentication: register a tenant + admin user, log in, and identify self."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.auth import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.tenant import ROLE_ADMIN, Tenant, User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str
    password: str
    tenant_name: str


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: int
    email: str


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "tenant"
    return base


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    # Unique slug for the new tenant.
    slug = _slug(payload.tenant_name)
    n = 1
    while db.query(Tenant).filter(Tenant.slug == slug).first():
        n += 1
        slug = f"{_slug(payload.tenant_name)}-{n}"

    tenant = Tenant(name=payload.tenant_name, slug=slug)
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id, email=payload.email,
        hashed_password=hash_password(payload.password), role=ROLE_ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(
        access_token=create_access_token(user.id, tenant.id),
        tenant_id=tenant.id, email=user.email,
    )


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenOut(
        access_token=create_access_token(user.id, user.tenant_id),
        tenant_id=user.tenant_id, email=user.email,
    )


@router.get("/me")
def me(user: User | None = Depends(get_current_user)) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user.id, "email": user.email, "tenant_id": user.tenant_id, "role": user.role}
