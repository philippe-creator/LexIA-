from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from core.config import settings
from core.database import get_db
from api.core.dependencies import CurrentUser
from core.security import create_access_token
from api.repositories.user_repo import UserRepository
from api.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse, UpdateProfileRequest

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

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user, error = repo.create(email=payload.email, username=payload.username, password=payload.password, full_name=payload.full_name, role=payload.role, profession=payload.profession, legal_level=payload.legal_level, sector=payload.sector, preferred_language=payload.preferred_language)
    if error: raise HTTPException(400, error)
    return _tokens(user, repo, response)

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.authenticate(payload.email, payload.password)
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect.")
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
