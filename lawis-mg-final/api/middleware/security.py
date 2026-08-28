import time
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings

_rate_store: dict[str, list[float]] = defaultdict(list)
_auth_rate_store: dict[str, list[float]] = defaultdict(list)

# Routes d'authentification : cible privilégiée du brute-force / bourrage de
# comptes. La limite globale (60/60s) est bien trop permissive pour elles —
# on leur applique en plus une limite dédiée, beaucoup plus stricte.
AUTH_RATE_LIMITED_PATHS = {"/auth/login", "/auth/register", "/auth/forgot-password", "/auth/google", "/auth/resend-verification"}

class RateLimitMiddleware(BaseHTTPMiddleware):
    EXEMPT = {"/health", "/docs", "/redoc", "/openapi.json", "/"}
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXEMPT: return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.time()

        if request.url.path in AUTH_RATE_LIMITED_PATHS:
            auth_window = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
            _auth_rate_store[ip] = [t for t in _auth_rate_store[ip] if now - t < auth_window]
            if len(_auth_rate_store[ip]) >= settings.AUTH_RATE_LIMIT_REQUESTS:
                return JSONResponse(status_code=429, content={"detail": "Trop de tentatives. Réessayez plus tard."}, headers={"Retry-After": str(auth_window)})
            _auth_rate_store[ip].append(now)

        window = settings.RATE_LIMIT_WINDOW_SECONDS
        _rate_store[ip] = [t for t in _rate_store[ip] if now - t < window]
        if len(_rate_store[ip]) >= settings.RATE_LIMIT_REQUESTS:
            return JSONResponse(status_code=429, content={"detail": "Trop de requêtes."}, headers={"Retry-After": str(window)})
        _rate_store[ip].append(now)
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # CSP stricte pour l'API JSON — sauf /docs et /redoc (Swagger/Redoc chargent leurs assets depuis un CDN).
        if request.url.path not in ("/docs", "/redoc"):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        response = await call_next(request)
        ms = (time.time() - start) * 1000
        response.headers["X-Response-Time"] = f"{ms:.1f}ms"
        return response
