from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: str = "particulier"
    profession: Optional[str] = None
    legal_level: str = "intermediaire"
    sector: Optional[str] = None
    preferred_language: str = "fr"
    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        # "admin" est délibérément exclu : ce schéma sert l'inscription PUBLIQUE
        # (/auth/register). Un compte admin ne se crée que via scripts/promote_admin.py.
        allowed = {"juriste","avocat","entreprise","etudiant","particulier"}
        if v not in allowed: raise ValueError(f"Rôle invalide.")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    profession: Optional[str] = None
    legal_level: Optional[str] = None
    sector: Optional[str] = None
    preferred_language: Optional[str] = None
    preferences: Optional[dict] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class GoogleAuthRequest(BaseModel):
    id_token: str

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr
