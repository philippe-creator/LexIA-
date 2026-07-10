from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from api.core.database import User, RefreshToken, AuditLog
from api.core.security import hash_password, verify_password, validate_password_strength, create_refresh_token, hash_refresh_token, refresh_token_expires_at

class UserRepository:
    def __init__(self, db: Session): self.db = db

    def create(self, email: str, username: str, password: str, **kwargs) -> tuple:
        ok, msg = validate_password_strength(password)
        if not ok: return None, msg
        if self.get_by_email(email): return None, "Email déjà utilisé."
        if self.get_by_username(username): return None, "Nom d'utilisateur déjà pris."
        user = User(email=email.lower().strip(), username=username.strip(), hashed_password=hash_password(password), **kwargs)
        self.db.add(user); self.db.commit(); self.db.refresh(user)
        return user, None

    def get_by_id(self, uid: str) -> Optional[User]: return self.db.query(User).filter(User.id == uid, User.is_active == True).first()
    def get_by_email(self, email: str) -> Optional[User]: return self.db.query(User).filter(User.email == email.lower().strip()).first()
    def get_by_username(self, username: str) -> Optional[User]: return self.db.query(User).filter(User.username == username.strip()).first()

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password) or not user.is_active: return None
        user.last_login_at = datetime.now(timezone.utc); self.db.commit()
        return user

    def update_profile(self, user: User, data: dict) -> User:
        for k, v in data.items():
            if v is not None and hasattr(user, k): setattr(user, k, v)
        user.updated_at = datetime.now(timezone.utc); self.db.commit(); self.db.refresh(user)
        return user

    def change_password(self, user: User, current: str, new: str) -> tuple[bool, str]:
        if not verify_password(current, user.hashed_password): return False, "Mot de passe actuel incorrect."
        ok, msg = validate_password_strength(new)
        if not ok: return False, msg
        user.hashed_password = hash_password(new); self.db.commit()
        return True, "Mot de passe modifié."

    def create_refresh_token(self, user: User) -> str:
        raw, token_hash = create_refresh_token()
        rt = RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=refresh_token_expires_at())
        self.db.add(rt); self.db.commit()
        return raw

    def verify_refresh_token(self, raw: str) -> Optional[User]:
        token_hash = hash_refresh_token(raw)
        now = datetime.now(timezone.utc)
        rt = self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False, RefreshToken.expires_at > now).first()
        return self.get_by_id(rt.user_id) if rt else None

    def revoke_refresh_token(self, raw: str):
        rt = self.db.query(RefreshToken).filter(RefreshToken.token_hash == hash_refresh_token(raw)).first()
        if rt: rt.revoked = True; self.db.commit()

    def revoke_all_tokens(self, user: User):
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({"revoked": True}); self.db.commit()

    def log_action(self, user_id, action, resource=None, details=None, ip=None, ua=None):
        log = AuditLog(user_id=user_id, action=action, resource=resource, details=details or {}, ip_address=ip, user_agent=ua)
        self.db.add(log); self.db.commit()
