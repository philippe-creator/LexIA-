from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from core.database import get_db, User
from core.security import decode_access_token

security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Session = Depends(get_db),
) -> User:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié.", headers={"WWW-Authenticate": "Bearer"})
    if not credentials: raise exc
    payload = decode_access_token(credentials.credentials)
    if not payload: raise exc
    user_id = payload.get("sub")
    if not user_id: raise exc
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user: raise exc
    return user

def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not credentials: return None
    try: return get_current_user(credentials, db)
    except HTTPException: return None

CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]

def require_role(*roles: str):
    def dependency(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Accès réservé aux rôles : {', '.join(roles)}.")
        return current_user
    return dependency

def require_owner(current_user: CurrentUser) -> User:
    """Distinct de require_role("admin") : réservé à la gestion des comptes
    (promouvoir/rétrograder un admin) — un admin normal ne doit pas pouvoir
    créer d'autres admins, seul le propriétaire le peut."""
    if not current_user.is_owner:
        raise HTTPException(status_code=403, detail="Accès réservé au propriétaire du compte.")
    return current_user
