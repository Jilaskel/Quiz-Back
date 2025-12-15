"""
➡️ But : Centraliser les dépendances réutilisables des routes.

Exemples :

get_user_service() : crée un UserService à partir d’une session DB.

pagination() : paramètres communs page et size.

🔹 Avantages :

Routes plus propres (pas de code dupliqué).

Facile à injecter dans plusieurs endpoints (Depends()).
"""

from typing import Optional
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Query, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.db.session import get_session

from app.db.repositories.users import UserRepository
from app.features.users.services import UserService

from app.db.repositories.refresh_tokens import RefreshTokenRepository
from app.features.authentication.services import AuthService

from app.db.repositories.images import ImageRepository
from app.features.media.services import ImageService, ImageAccessService

from app.db.repositories.themes import ThemeRepository
from app.features.themes.services import ThemeService

from app.security.tokens import JWTSettings
from app.core.config import jwt_settings

def pagination(
    page: int = Query(1, ge=1, description="Numéro de page", examples=[1]),
    size: int = Query(20, ge=1, le=100, description="Taille de page", examples=[20]),
):
    offset = (page - 1) * size
    return {"offset": offset, "limit": size}


# -----------------------------
# Users
# -----------------------------
def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session))


# -----------------------------
# Auth
# -----------------------------
def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(
        user_repo=UserRepository(session),
        refresh_repo=RefreshTokenRepository(session),
        jwt_settings=jwt_settings if isinstance(jwt_settings, JWTSettings) else JWTSettings(secret=str(jwt_settings)),
    )


# -----------------------------
# Repositories
# -----------------------------
def get_image_repository(session: Session = Depends(get_session)) -> ImageRepository:
    return ImageRepository(session)

def get_theme_repository(session: Session = Depends(get_session)) -> ThemeRepository:
    return ThemeRepository(session)


# -----------------------------
# Media services
# -----------------------------
def get_image_service(
    image_repo: ImageRepository = Depends(get_image_repository),
) -> ImageService:
    # ✅ retourne une instance d'ImageService, pas de tuple, pas de Depends dans le corps
    return ImageService(repo=image_repo)

def get_image_access_service(
    img_svc: ImageService = Depends(get_image_service),
    image_repo: ImageRepository = Depends(get_image_repository),
    theme_repo: ThemeRepository = Depends(get_theme_repository),
) -> ImageAccessService:
    # ✅ wrapper “policy-aware” Option A
    return ImageAccessService(image_svc=img_svc, image_repo=image_repo, theme_repo=theme_repo)


# -----------------------------
# Theme service
# -----------------------------
def get_theme_service(
    theme_repo: ThemeRepository = Depends(get_theme_repository),
    image_repo: ImageRepository = Depends(get_image_repository),
    image_svc: ImageService = Depends(get_image_service),
) -> ThemeService:
    # ✅ toutes les dépendances injectées via la signature (FastAPI les résout)
    return ThemeService(repo=theme_repo, image_repo=image_repo, image_svc=image_svc)


# -----------------------------
# Authentication data
# -----------------------------
bearer_scheme = HTTPBearer(auto_error=True)

def get_access_token_from_bearer(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    return credentials.credentials


@dataclass
class ClientContext:
    ip: Optional[str]
    user_agent: Optional[str]

def get_client_ip_and_ua(
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    x_real_ip: Optional[str] = Header(default=None, alias="X-Real-IP"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> ClientContext:
    """
    Récupère l'IP depuis X-Forwarded-For > X-Real-IP (si derrière un proxy),
    et le User-Agent (utile pour audit des refresh tokens).
    """
    ip = None
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    elif x_real_ip:
        ip = x_real_ip
    return ClientContext(ip=ip, user_agent=user_agent)