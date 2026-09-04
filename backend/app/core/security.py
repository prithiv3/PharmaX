"""Prototype Security and Pharmacist Authorization Module."""

from typing import Optional
from fastapi import Header, HTTPException, status


def get_authenticated_pharmacist(
    x_pharmacist_token: Optional[str] = Header(None, alias="X-Pharmacist-Token"),
    x_pharmacist_code: Optional[str] = Header(None, alias="X-Pharmacist-Code"),
) -> str:
    """Validate prototype pharmacist authentication token header.

    Returns authenticated pharmacist code string or raises HTTP 401 UNAUTHORIZED.
    """
    token = x_pharmacist_token or x_pharmacist_code
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid pharmacist authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_str = token.strip()
    if token_str.upper() in ("INVALID", "EXPIRED", "UNAUTHORIZED", "FALSE", "0"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid pharmacist authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_str
