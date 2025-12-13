"""
➡️ But : Centraliser tous les paramètres configurables (nom d’app, chemin DB, secrets, etc.)

Utilise pydantic-settings pour charger automatiquement les variables d’environnement (.env, variables système…).

Fournit un objet settings unique, que tu importes ailleurs :

from app.core.config import settings
print(settings.APP_NAME)


🔹 Avantages :

Plus propre que des constantes éparpillées dans le code.

Facilite le passage entre environnements (dev / prod / test).
"""

from datetime import timedelta
from typing import Optional

from pydantic_settings import BaseSettings
from app.security.tokens import JWTSettings


class Settings(BaseSettings):
    # -----------------------------
    # App
    # -----------------------------
    APP_NAME: str = "Quiz-Back"
    ENV: str = "dev"  # dev | prod | test

    # -----------------------------
    # DB
    # -----------------------------
    SQLITE_PATH: str = "app.db"  # fichier SQLite
    # Si tu veux forcer une URL différente (ex: Postgres), définis DATABASE_URL dans l'env.
    DATABASE_URL: Optional[str] = None

    # -----------------------------
    # JWT / Auth
    # -----------------------------
    JWT_SECRET_KEY: str = "CHANGE_ME"     # ⚠️ change en prod
    JWT_ISSUER: str = "todo-api"
    JWT_ALGORITHM: str = "HS256"

    ACCESS_TTL_MINUTES: int = 15          # access token court
    REFRESH_TTL_DAYS: int = 30            # refresh token long

    # Cookies (refresh)
    AUTH_REFRESH_COOKIE_NAME: str = "refresh_token"
    AUTH_COOKIE_SAMESITE: str = "lax"     # "lax" | "strict" | "none"
    AUTH_COOKIE_PATH: str = "/auth"
    AUTH_COOKIE_SECURE: Optional[bool] = None   # auto selon ENV si None
    AUTH_COOKIE_MAX_AGE: Optional[int] = None   # auto depuis REFRESH_TTL si None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    # -----------------------------
    # Post-process values
    # -----------------------------
    def model_post_init(self, __context): # appelée automatiquement
        # DATABASE_URL par défaut depuis SQLITE_PATH si non fourni
        if not self.DATABASE_URL:
            object.__setattr__(self, "DATABASE_URL", f"sqlite:///{self.SQLITE_PATH}")

        # Cookie secure auto: true en prod si non spécifié
        if self.AUTH_COOKIE_SECURE is None:
            object.__setattr__(self, "AUTH_COOKIE_SECURE", self.ENV == "prod")

        # max_age auto depuis REFRESH_TTL
        if self.AUTH_COOKIE_MAX_AGE is None:
            max_age = self.REFRESH_TTL_DAYS * 24 * 60 * 60
            object.__setattr__(self, "AUTH_COOKIE_MAX_AGE", max_age)


# Instance globale importable partout
settings = Settings()

# Objet JWT prêt à l'emploi pour les services
jwt_settings = JWTSettings(
    secret=settings.JWT_SECRET_KEY,
    issuer=settings.JWT_ISSUER,
    algorithm=settings.JWT_ALGORITHM,
    access_ttl=timedelta(minutes=settings.ACCESS_TTL_MINUTES),
    refresh_ttl=timedelta(days=settings.REFRESH_TTL_DAYS),
)