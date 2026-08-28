from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from core.config import settings
from core.database import get_db
from api.core.dependencies import CurrentUser
from core.security import create_access_token, verify_google_id_token
from api.repositories.user_repo import UserRepository
from api.schemas.auth import ChangePasswordRequest, ForgotPasswordRequest, GoogleAuthRequest, LoginRequest, RegisterRequest, ResendVerificationRequest, ResetPasswordRequest, TokenResponse, UpdateProfileRequest, VerifyEmailRequest
from services.notifications.email import send_email

router = APIRouter(prefix="/auth", tags=["Authentification"])

REFRESH_COOKIE = "refresh_token"
_COOKIE_SECURE = settings.ENVIRONMENT == "production"

def _set_refresh_cookie(response: Response, token: str):
    # httpOnly : inaccessible à JavaScript, donc pas volable par un XSS côté frontend.
    response.set_cookie(REFRESH_COOKIE, token, max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, httponly=True, secure=_COOKIE_SECURE, samesite="lax", path="/auth")

def _clear_refresh_cookie(response: Response):
    response.delete_cookie(REFRESH_COOKIE, path="/auth")

def _tokens(user, repo, response: Response) -> TokenResponse:
    access = create_access_token({"sub": user.id, "role": user.role}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh = repo.create_refresh_token(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES*60, user=user.to_dict())

def _send_verification_email(user, repo):
    raw_token = repo.create_email_verification_token(user)
    link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
    html = (
        f"<p>Bonjour {user.full_name or user.username},</p>"
        f"<p>Bienvenue sur LexIA Maroc ! Confirmez votre adresse email pour activer votre compte :</p>"
        f'<p><a href="{link}">Confirmer mon email</a></p>'
        f"<p>Ce lien expire dans {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES // 60} heures. "
        f"Si vous n'êtes pas à l'origine de cette inscription, ignorez cet email.</p>"
    )
    send_email(user.email, "[LexIA Maroc] Confirmez votre adresse email", html)

@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user, error = repo.create(email=payload.email, username=payload.username, password=payload.password, full_name=payload.full_name, role=payload.role, profession=payload.profession, legal_level=payload.legal_level, sector=payload.sector, preferred_language=payload.preferred_language)
    if error: raise HTTPException(400, error)
    # Trace minimale du consentement CGU/politique de confidentialité donné à
    # l'inscription (le frontend n'affiche le bouton que si la case est cochée).
    repo.log_action(user.id, "consent_signup", details={"cgu": True, "politique_confidentialite": True}, ip=request.client.host if request.client else None)
    # Pas de connexion automatique : le compte doit d'abord être confirmé par
    # email (voir /auth/verify-email) avant de pouvoir se connecter — c'est le
    # comportement demandé, comme la plupart des sites modernes.
    _send_verification_email(user, repo)
    return {"message": "Compte créé. Consultez votre email pour confirmer votre adresse avant de vous connecter.", "email": user.email}

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.authenticate(payload.email, payload.password)
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect.")
    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Adresse email non confirmée. Vérifiez votre boîte de réception (ou demandez un nouvel envoi).")
    return _tokens(user, repo, response)

@router.post("/google", response_model=TokenResponse)
async def google_auth(payload: GoogleAuthRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Connexion/inscription via le bouton "Se connecter avec Google" du
    frontend (Google Identity Services). Le frontend n'envoie que l'ID token
    signé par Google — jamais de mot de passe, jamais le client secret."""
    try:
        claims = verify_google_id_token(payload.id_token)
    except ValueError as e:
        raise HTTPException(401, f"Jeton Google invalide : {e}")
    if not claims.get("email_verified"):
        raise HTTPException(401, "Email Google non vérifié.")
    repo = UserRepository(db)
    user = repo.get_or_create_google_user(claims["email"], claims.get("name"))
    if not user.is_active:
        raise HTTPException(403, "Compte désactivé.")
    return _tokens(user, repo, response)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, refresh_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if not refresh_token: raise HTTPException(401, "Refresh token manquant.")
    repo = UserRepository(db)
    user = repo.verify_refresh_token(refresh_token)
    if not user: raise HTTPException(401, "Refresh token invalide ou expiré.")
    repo.revoke_refresh_token(refresh_token)
    return _tokens(user, repo, response)

@router.post("/logout")
async def logout(response: Response, current_user: CurrentUser, refresh_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if refresh_token: UserRepository(db).revoke_refresh_token(refresh_token)
    _clear_refresh_cookie(response)
    return {"message": "Déconnexion réussie."}

@router.get("/me")
async def me(current_user: CurrentUser): return current_user.to_dict()

@router.patch("/me")
async def update_profile(payload: UpdateProfileRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    return UserRepository(db).update_profile(current_user, payload.model_dump(exclude_none=True)).to_dict()

@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    ok, msg = repo.change_password(current_user, payload.current_password, payload.new_password)
    if not ok: raise HTTPException(400, msg)
    repo.revoke_all_tokens(current_user)
    return {"message": msg}

_FORGOT_PASSWORD_GENERIC_MESSAGE = "Si un compte existe pour cet email, un lien de réinitialisation vient d'être envoyé."

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Toujours la même réponse, que le compte existe ou non — évite de
    laisser deviner quels emails sont inscrits (énumération de comptes)."""
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)
    if user:
        raw_token = repo.create_password_reset_token(user)
        link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        html = (
            f"<p>Bonjour {user.full_name or user.username},</p>"
            f"<p>Une réinitialisation de mot de passe a été demandée pour votre compte LexIA Maroc.</p>"
            f'<p><a href="{link}">Réinitialiser mon mot de passe</a></p>'
            f"<p>Ce lien expire dans {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes. "
            f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.</p>"
        )
        send_email(user.email, "[LexIA Maroc] Réinitialisation de votre mot de passe", html)
    return {"message": _FORGOT_PASSWORD_GENERIC_MESSAGE}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    ok, msg = repo.reset_password(payload.token, payload.new_password)
    if not ok: raise HTTPException(400, msg)
    return {"message": msg}

@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    ok, msg = repo.verify_email(payload.token)
    if not ok: raise HTTPException(400, msg)
    return {"message": msg}

_RESEND_VERIFICATION_GENERIC_MESSAGE = "Si un compte non confirmé existe pour cet email, un nouveau lien vient d'être envoyé."

@router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Même principe que /forgot-password : réponse générique identique que le
    compte existe ou non (anti-énumération)."""
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)
    if user and not user.email_verified:
        _send_verification_email(user, repo)
    return {"message": _RESEND_VERIFICATION_GENERIC_MESSAGE}
