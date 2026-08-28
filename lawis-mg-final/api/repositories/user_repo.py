import re
import secrets
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from core.database import User, RefreshToken, PasswordResetToken, EmailVerificationToken, AuditLog
from core.security import (
    hash_password, verify_password, validate_password_strength,
    create_refresh_token, hash_refresh_token, refresh_token_expires_at,
    create_password_reset_token, hash_password_reset_token, password_reset_token_expires_at,
    create_email_verification_token, hash_email_verification_token, email_verification_token_expires_at,
)

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

    def log_action(self, user_id, action, resource=None, details=None, ip=None):
        # NB : AuditLog n'a pas de colonne user_agent (core/database.py) — un
        # paramètre `ua` avait déjà été prévu ici mais n'existe pas côté modèle.
        log = AuditLog(user_id=user_id, action=action, resource=resource, details=details or {}, ip_address=ip)
        self.db.add(log); self.db.commit()

    def create_password_reset_token(self, user: User) -> str:
        raw, token_hash = create_password_reset_token()
        prt = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=password_reset_token_expires_at())
        self.db.add(prt); self.db.commit()
        return raw

    def reset_password(self, raw_token: str, new_password: str) -> tuple[bool, str]:
        """Vérifie le token (hash, non expiré, non utilisé), change le mot de
        passe et révoque toutes les sessions existantes (comme change_password)."""
        token_hash = hash_password_reset_token(raw_token)
        now = datetime.now(timezone.utc)
        prt = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > now,
        ).first()
        if not prt: return False, "Lien de réinitialisation invalide ou expiré."
        ok, msg = validate_password_strength(new_password)
        if not ok: return False, msg
        user = self.db.query(User).filter(User.id == prt.user_id).first()
        if not user or not user.is_active: return False, "Compte introuvable."
        user.hashed_password = hash_password(new_password)
        prt.used = True
        self.db.commit()
        self.revoke_all_tokens(user)
        return True, "Mot de passe réinitialisé."

    def create_email_verification_token(self, user: User) -> str:
        raw, token_hash = create_email_verification_token()
        evt = EmailVerificationToken(user_id=user.id, token_hash=token_hash, expires_at=email_verification_token_expires_at())
        self.db.add(evt); self.db.commit()
        return raw

    def verify_email(self, raw_token: str) -> tuple[bool, str]:
        token_hash = hash_email_verification_token(raw_token)
        now = datetime.now(timezone.utc)
        evt = self.db.query(EmailVerificationToken).filter(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used == False,
            EmailVerificationToken.expires_at > now,
        ).first()
        if not evt: return False, "Lien de confirmation invalide ou expiré."
        user = self.db.query(User).filter(User.id == evt.user_id).first()
        if not user: return False, "Compte introuvable."
        user.email_verified = True
        evt.used = True
        self.db.commit()
        return True, "Email confirmé — vous pouvez vous connecter."

    def get_or_create_google_user(self, email: str, full_name: str | None) -> User:
        """Connexion "Se connecter avec Google" : si un compte existe déjà pour
        cet email (créé au clavier ou via un Google précédent), on s'y connecte
        directement — un email vérifié par Google est un lien de compte fiable.
        Sinon on crée un compte. Le mot de passe est un secret aléatoire que
        l'utilisateur ne connaîtra jamais (hashed_password est NOT NULL) : ce
        compte ne se connecte qu'via Google tant qu'il ne passe pas par
        "mot de passe oublié" pour s'en fixer un lui-même."""
        user = self.get_by_email(email)
        if user:
            user.last_login_at = datetime.now(timezone.utc); self.db.commit()
            return user
        base_username = re.sub(r"[^a-zA-Z0-9_-]", "", email.split("@")[0]).lower()[:40] or "utilisateur"
        username = base_username
        suffix = 0
        while self.get_by_username(username):
            suffix += 1
            username = f"{base_username}{suffix}"
        user = User(
            email=email.lower().strip(), username=username,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            full_name=full_name, role="particulier",
            # Google a déjà vérifié cet email (voir la vérification
            # claims["email_verified"] dans /auth/google) — inutile de
            # redemander une confirmation par email pour ce compte.
            email_verified=True,
        )
        self.db.add(user); self.db.commit(); self.db.refresh(user)
        return user
