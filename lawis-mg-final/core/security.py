import hashlib, secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from core.config import settings

# bcrypt ne prend en compte que les 72 premiers octets du mot de passe (limite de
# l'algorithme) — on tronque explicitement, exactement comme le faisait passlib,
# pour que les hashs restent compatibles avec les comptes déjà enregistrés.
def _pw_bytes(p: str) -> bytes: return p.encode("utf-8")[:72]

def hash_password(p: str) -> str:
    return bcrypt.hashpw(_pw_bytes(p), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
def validate_password_strength(p: str) -> tuple[bool, str]:
    if len(p) < 8: return False, "Minimum 8 caractères."
    if not any(c.isupper() for c in p): return False, "Minimum une majuscule."
    if not any(c.isdigit() for c in p): return False, "Minimum un chiffre."
    return True, "ok"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload if payload.get("type") == "access" else None
    except JWTError: return None

def create_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(64)
    return raw, hashlib.sha256(raw.encode()).hexdigest()

def hash_refresh_token(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()
def refresh_token_expires_at() -> datetime: return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
