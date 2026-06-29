"""BYO API-key management. Keys are encrypted at rest; plaintext is never returned."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.setting import ApiKey
from app.schemas.settings import ApiKeyIn, ApiKeyOut

router = APIRouter(prefix="/settings", tags=["settings"])

SUPPORTED_PROVIDERS = {"anthropic", "firecrawl", "ahrefs"}


def _to_out(key: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=key.id,
        provider=key.provider,
        label=key.label,
        masked_value=key.masked,
        created_at=key.created_at,
        updated_at=key.updated_at,
    )


@router.get("/keys", response_model=list[ApiKeyOut])
def list_keys(db: Session = Depends(get_db)) -> list[ApiKeyOut]:
    return [_to_out(k) for k in db.query(ApiKey).order_by(ApiKey.provider).all()]


@router.put("/keys", response_model=ApiKeyOut)
def upsert_key(payload: ApiKeyIn, db: Session = Depends(get_db)) -> ApiKeyOut:
    """Create or replace the key for a provider (one key per provider)."""
    provider = payload.provider.lower().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported provider '{provider}'. Allowed: {sorted(SUPPORTED_PROVIDERS)}",
        )
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
