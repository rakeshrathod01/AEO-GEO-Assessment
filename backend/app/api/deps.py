"""Auth + tenant-resolution dependencies.

``get_current_tenant`` is the isolation boundary used by every data route:
  * AUTH_REQUIRED=True  -> a valid Bearer JWT is required; resolves to its tenant.
  * AUTH_REQUIRED=False -> requests resolve to a shared "default" tenant (local-first
    convenience), so the app runs without logging in.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import decode_token
from app.core.config import settings
from app.db.session import get_db
from app.models.project import Project
from app.models.tenant import DEFAULT_TENANT_SLUG, Tenant, User


def get_default_tenant(db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.slug == DEFAULT_TENANT_SLUG).one_or_none()
    if tenant is None:
        tenant = Tenant(name="Default", slug=DEFAULT_TENANT_SLUG)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return tenant


def _user_from_token(db: Session, authorization: str | None) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    if not payload:
        return None
    user = db.get(User, int(payload.get("sub", 0)))
    if user is None or user.tenant_id != payload.get("tid"):
        return None
    return user


def get_current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User | None:
    return _user_from_token(db, authorization)


def get_current_tenant(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> Tenant:
    if settings.AUTH_REQUIRED:
        user = _user_from_token(db, authorization)
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return db.get(Tenant, user.tenant_id)
    return get_default_tenant(db)


def owned_project(db: Session, project_id: int, tenant: Tenant) -> Project:
    """Fetch a project, enforcing tenant ownership (404 if it isn't the caller's)."""
    project = db.get(Project, project_id)
    if project is None or (project.tenant_id is not None and project.tenant_id != tenant.id):
        raise HTTPException(status_code=404, detail="Project not found")
    return project
