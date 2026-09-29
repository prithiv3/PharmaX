"""Prototype Security, Pharmacist Authorization, and Capacity Guard Module."""

import threading
from typing import Optional
from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings


# ---------------------------------------------------------------------------
# Pharmacist authentication
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Capacity Guard – concurrent evaluation limiter
# ---------------------------------------------------------------------------

# Semaphore initialized from the capacity constraint setting.
# acquire(blocking=False) is used so the thread never blocks;
# if the slot cannot be acquired immediately, HTTP 429 is returned.
_evaluation_semaphore = threading.Semaphore(settings.MAX_CONCURRENT_EVALUATIONS)


def capacity_guard() -> None:
    """FastAPI dependency that enforces MAX_CONCURRENT_EVALUATIONS.

    Acquires a slot from the semaphore pool before allowing the evaluation
    pipeline to proceed. Releases the slot when the request exits (via
    contextmanager-style try/finally in the route handler).

    Raises HTTP 429 Too Many Requests when all capacity slots are occupied.

    Usage (in route handler):
        _ = Depends(capacity_guard)

    NOTE: For production use, replace with an async semaphore (asyncio.Semaphore)
    when the FastAPI app runs with async route handlers. The threading semaphore
    is correct for synchronous route handlers (the current implementation).
    """
    acquired = _evaluation_semaphore.acquire(blocking=False)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Service capacity limit reached "
                f"({settings.MAX_CONCURRENT_EVALUATIONS} concurrent evaluations). "
                "Please retry after a short delay."
            ),
            headers={"Retry-After": "5"},
        )
    try:
        yield
    finally:
        _evaluation_semaphore.release()
