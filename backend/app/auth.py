"""
Auth module - JWT verification for Supabase tokens
Validates the Supabase JWT and extracts user_id for multi-tenant isolation
"""
import os
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# JWKS client for ES256 tokens (Supabase signs user tokens with ES256)
_jwks_client: Optional[PyJWKClient] = None
if SUPABASE_URL:
    _jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")

security = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict:
    """Decode and verify a Supabase JWT token (supports both ES256 and HS256)"""
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "ES256":
            if not _jwks_client:
                raise HTTPException(
                    status_code=503,
                    detail="Validação JWT indisponível: configure SUPABASE_URL",
                )
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        elif alg == "HS256":
            if not SUPABASE_JWT_SECRET:
                raise HTTPException(
                    status_code=503,
                    detail="Validação JWT indisponível: configure SUPABASE_JWT_SECRET",
                )
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            raise HTTPException(status_code=401, detail="Algoritmo de token não suportado")
        return payload
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except (jwt.InvalidTokenError, jwt.exceptions.DecodeError):
        raise HTTPException(status_code=401, detail="Token inválido")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    FastAPI dependency that extracts and validates the user from the JWT.
    Returns dict with 'sub' (user_id), 'email', 'role', etc.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Autenticação necessária")
    
    token = credentials.credentials
    payload = _decode_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sem user_id")
    
    return {
        "user_id": user_id,
        "email": payload.get("email", ""),
        "role": payload.get("role", "authenticated"),
        "token": token,  # pass through for Supabase RLS calls
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Like get_current_user but returns None if no token provided (for public endpoints)"""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
