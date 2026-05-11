import hmac
from fastapi import Header, HTTPException, status

from app.config import settings


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server zonder API_KEY gestart - configureer API_KEY in .env",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ongeldige of ontbrekende API key",
        )
