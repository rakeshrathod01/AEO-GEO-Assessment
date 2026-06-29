"""BYO credential management.

Secrets are encrypted at rest (Fernet); plaintext is never returned — only a
masked preview. URL-kind values (Ahrefs MCP URL) are returned in full.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.setting import ApiKey
from app.providers import PROVIDERS, SUPPORTED_PROVIDERS, get_provider
from app.schemas.settings import ApiKeyIn, ApiKeyOut, ProviderOut

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_out(key: ApiKey) -> ApiKeyOut:
    meta = get_provider(key.provider)
    kind = meta.kind if meta else "secret"
    return ApiKeyOut(
        id=key.id,
        provider=key.provider,
        kind=kind,
        label=key.label,
        masked_value=key.masked,
        value=key.value if kind == "url" else None,
        created_at=key.created_at,
        updated_at=key.updated_at,
    )


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(db: Session = Depends(get_db)) -> list[ProviderOut]:
    """Catalog of every BYO provider plus whether it is configured."""
    configured = {row[0] for row in db.query(ApiKey.provider).all()}
    return [
        ProviderOut(**p.model_dump(), configured=p.key in configured) for p in PROVIDERS
    ]


@router.get("/keys", response_model=list[ApiKeyOut])
def list_keys(db: Session = Depends(get_db)) -> list[ApiKeyOut]:
    return [_to_out(k) for k in db.query(ApiKey).order_by(ApiKey.provider).all()]


@router.put("/keys", response_model=ApiKeyOut)
def upsert_key(payload: ApiKeyIn, db: Session = Depends(get_db)) -> ApiKeyOut:
    """Create or replace the stored value for a provider (one per provider)."""
    provider = payload.provider.lower().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported provider '{provider}'. Allowed: {sorted(SUPPORTED_PROVIDERS)}",
        )
    if not payload.value.strip():
        raise HTTPException(status_code=422, detail="Value must not be empty")

    key = db.query(ApiKey).filter(ApiKey.provider == provider).one_or_none()
    if key is None:
        key = ApiKey.from_plaintext(provider, payload.value, payload.label)
        db.add(key)
    else:
        key.set_value(payload.value)
        if payload.label is not None:
            key.label = payload.label
    db.commit()
    db.refresh(key)
    return _to_out(key)


@router.delete("/keys/{provider}", status_code=204, response_class=Response)
def delete_key(provider: str, db: Session = Depends(get_db)) -> Response:
    key = db.query(ApiKey).filter(ApiKey.provider == provider.lower()).one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="Key not found")
    db.delete(key)
    db.commit()
    return Response(status_code=204)
