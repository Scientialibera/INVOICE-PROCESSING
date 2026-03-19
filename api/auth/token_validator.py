from __future__ import annotations

import os
import logging
from functools import lru_cache
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Request
from jwt.algorithms import RSAAlgorithm

logger = logging.getLogger(__name__)

_TENANT_ID = os.environ.get("ENTRA_TENANT_ID", "")
_API_CLIENT_ID = os.environ.get("ENTRA_API_CLIENT_ID", "")

_JWKS_URL = f"https://login.microsoftonline.com/{_TENANT_ID}/discovery/v2.0/keys"
_ISSUER = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"


@lru_cache(maxsize=1)
def _get_signing_keys() -> dict[str, Any]:
    resp = httpx.get(_JWKS_URL, timeout=10)
    resp.raise_for_status()
    keys = {}
    for key_data in resp.json().get("keys", []):
        kid = key_data.get("kid")
        if kid:
            keys[kid] = RSAAlgorithm.from_jwk(key_data)
    return keys


def _decode_token(token: str) -> dict[str, Any]:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid", "")

    keys = _get_signing_keys()
    public_key = keys.get(kid)
    if not public_key:
        _get_signing_keys.cache_clear()
        keys = _get_signing_keys()
        public_key = keys.get(kid)

    if not public_key:
        raise jwt.InvalidTokenError(f"Key {kid} not found in JWKS")

    return jwt.decode(
        token,
        key=public_key,
        algorithms=["RS256"],
        audience=_API_CLIENT_ID,
        issuer=_ISSUER,
    )


async def get_current_user(request: Request) -> dict[str, Any]:
    if not _TENANT_ID or not _API_CLIENT_ID:
        return {"oid": "dev-user", "name": "Dev User", "preferred_username": "dev@local"}

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = auth[7:]
    try:
        claims = _decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    return {
        "oid": claims.get("oid", ""),
        "name": claims.get("name", ""),
        "preferred_username": claims.get("preferred_username", ""),
    }
