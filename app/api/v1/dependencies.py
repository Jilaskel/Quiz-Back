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
from app.db.repositories.audios import AudioRepository
from app.db.repositories.videos import VideoRepository
from app.features.media.services import (
    ImageService, ImageAccessService, 
    AudioService, AudioAccessService, 
    VideoService, VideoAccessService
)

from app.db.repositories.themes import ThemeRepository
from app.features.themes.services import ThemeService, CategoryService

from app.db.repositories.categories import CategoryRepository

from app.db.repositories.questions import QuestionRepository
from app.features.questions.services import QuestionService

from app.db.repositories.games import GameRepository
from app.db.repositories.players import PlayerRepository
from app.db.repositories.rounds import RoundRepository
from app.db.repositories.grids import GridRepository
from app.db.repositories.jokers import JokerRepository
from app.db.repositories.jokers_in_games import JokerInGameRepository
from app.db.repositories.jokers_used_in_games import JokerUsedInGameRepository
from app.db.repositories.bonus import BonusRepository
from app.db.repositories.bonus_in_games import BonusInGameRepository
from app.db.repositories.colors import ColorRepository

from app.features.games.services import GameService


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

def get_audio_repository(session: Session = Depends(get_session)) -> AudioRepository:
    return AudioRepository(session)

def get_video_repository(session: Session = Depends(get_session)) -> VideoRepository:
    return VideoRepository(session)

def get_question_repository(session: Session = Depends(get_session)) -> QuestionRepository:
    return QuestionRepository(session)

def get_game_repository(session: Session = Depends(get_session)) -> GameRepository:
    return GameRepository(session)

def get_player_repository(session: Session = Depends(get_session)) -> PlayerRepository:
    return PlayerRepository(session)

def get_round_repository(session: Session = Depends(get_session)) -> RoundRepository:
    return RoundRepository(session)

def get_grid_repository(session: Session = Depends(get_session)) -> GridRepository:
    return GridRepository(session)

def get_joker_repository(session: Session = Depends(get_session)) -> JokerRepository:
    return JokerRepository(session)

def get_joker_in_game_repository(session: Session = Depends(get_session)) -> JokerInGameRepository:
    return JokerInGameRepository(session)

def get_joker_used_in_game_repository(session: Session = Depends(get_session)) -> JokerUsedInGameRepository:
    return JokerUsedInGameRepository(session)

def get_bonus_repository(session: Session = Depends(get_session)) -> BonusRepository:
    return BonusRepository(session)

def get_bonus_in_game_repository(session: Session = Depends(get_session)) -> BonusInGameRepository:
    return BonusInGameRepository(session)

def get_color_repository(session: Session = Depends(get_session)) -> ColorRepository:
    return ColorRepository(session)
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

def get_audio_service(
    audio_repo: AudioRepository = Depends(get_audio_repository),
) -> AudioService:
    return AudioService(repo=audio_repo)

def get_audio_access_service(
    audio_svc: AudioService = Depends(get_audio_service),
    audio_repo: AudioRepository = Depends(get_audio_repository),
) -> AudioAccessService:
    return AudioAccessService(audio_svc=audio_svc, audio_repo=audio_repo)

def get_video_service(
    video_repo: VideoRepository = Depends(get_video_repository),
) -> VideoService:
    return VideoService(repo=video_repo)

def get_video_access_service(
    video_svc: VideoService = Depends(get_video_service),
    video_repo: VideoRepository = Depends(get_video_repository),
) -> VideoAccessService:
    return VideoAccessService(video_svc=video_svc, video_repo=video_repo)

# -----------------------------
# Question service
# -----------------------------
def get_question_service(
    question_repo: QuestionRepository = Depends(get_question_repository),
    theme_repo: ThemeRepository = Depends(get_theme_repository),
    image_svc: ImageService = Depends(get_image_service),
    audio_svc: AudioService = Depends(get_audio_service),
    video_svc: VideoService = Depends(get_video_service),
) -> QuestionService:
    return QuestionService(
        repo=question_repo,
        theme_repo=theme_repo,
        image_svc=image_svc,
        audio_svc=audio_svc,
        video_svc=video_svc,
    )
# -----------------------------
# Theme service
# -----------------------------
def get_theme_service(
    theme_repo: ThemeRepository = Depends(get_theme_repository),
    image_repo: ImageRepository = Depends(get_image_repository),
    image_svc: ImageService = Depends(get_image_service),
    audio_svc: AudioService = Depends(get_audio_service),
    video_svc: VideoService = Depends(get_video_service),
    question_repo: QuestionRepository = Depends(get_question_repository),
) -> ThemeService:
    # ✅ toutes les dépendances injectées via la signature (FastAPI les résout)
    return ThemeService(
        repo=theme_repo, 
        image_repo=image_repo, 
        image_svc=image_svc,
        audio_svc=audio_svc,
        video_svc=video_svc,
        question_repo=question_repo,
    )

# -----------------------------
# Game service
# -----------------------------
def get_game_service(
    session: Session = Depends(get_session),
    game_repo: GameRepository = Depends(get_game_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
    round_repo: RoundRepository = Depends(get_round_repository),
    grid_repo: GridRepository = Depends(get_grid_repository),
    joker_repo: JokerRepository = Depends(get_joker_repository),
    joker_in_game_repo: JokerInGameRepository = Depends(get_joker_in_game_repository),
    jokers_used: JokerUsedInGameRepository = Depends(get_joker_used_in_game_repository),
    bonus_repo: BonusRepository = Depends(get_bonus_repository),
    bonus_in_game_repo: BonusInGameRepository = Depends(get_bonus_in_game_repository),
    color_repo: ColorRepository = Depends(get_color_repository),
    question_repo: QuestionRepository = Depends(get_question_repository),
) -> GameService:
    """
    Fournit une instance de GameService avec tous ses repositories injectés.
    Pattern identique à ThemeService :
    - aucune logique dans la route
    - dépendances résolues par FastAPI
    """
    return GameService(
        session=session,
        game_repo=game_repo,
        player_repo=player_repo,
        round_repo=round_repo,
        grid_repo=grid_repo,
        joker_repo=joker_repo,
        joker_in_game_repo=joker_in_game_repo,
        joker_used_repo=jokers_used,
        bonus_repo=bonus_repo,
        bonus_in_game_repo=bonus_in_game_repo,
        color_repo=color_repo,
        question_repo=question_repo,
    )

# -----------------------------
# Category service
# -----------------------------
def get_category_service(db: Session = Depends(get_session)) -> CategoryService:
    repo = CategoryRepository(db)
    return CategoryService(repo)

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