from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.config.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """Validate API key."""
    if not settings.ai_service_api_key:
        # If no key configured, allow access (dev mode or misconfiguration fallback)
        # In production, this should be strictly enforced.
        return None
        
    if api_key_header == settings.ai_service_api_key:
        return api_key_header
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )
