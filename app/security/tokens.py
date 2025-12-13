import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from jose import jwt, JWTError

# ==========================================================
# 🔧 Configuration : paramètres de génération/validation JWT
# ==========================================================

@dataclass(frozen=True)
class JWTSettings:
    """
    Configuration des tokens JWT.

    - `secret` : clé secrète pour signer/valider les tokens
    - `issuer` : émetteur (utilisé dans le payload)
    - `algorithm` : algo de signature (HS256 recommandé)
    - `access_ttl` : durée de vie d’un access token
    - `refresh_ttl` : durée de vie d’un refresh token
    """
    secret: str
    issuer: str = "my-app"
    algorithm: str = "HS256"
    access_ttl: timedelta = timedelta(minutes=15)
    refresh_ttl: timedelta = timedelta(days=30)


# ==========================================================
# 🧱 Types
# ==========================================================

class TokenPair(TypedDict):
    access_token: str
    refresh_token: str
    token_type: str     # "bearer"
    expires_in: int     # durée de vie de l'access token (en secondes)

class DecodedToken(TypedDict, total=False):
    iss: str
    sub: str            # identifiant utilisateur
    username: str
    typ: str            # "access" | "refresh"
    jti: str
    iat: int
    exp: int


# ==========================================================
# 🧩 Fonctions utilitaires
# ==========================================================

def _now() -> datetime:
    """Renvoie l'heure UTC actuelle."""
    return datetime.now(timezone.utc)

def new_jti() -> str:
    """Crée un identifiant unique pour un token."""
    return str(uuid.uuid4())


# ==========================================================
# 🎟️ Génération des tokens
# ==========================================================

def create_access_token(*, user_id: int, username: str, settings: JWTSettings) -> str:
    """
    Crée un access token JWT court (par défaut 15 min).
    """
    now = _now()
    payload: DecodedToken = {
        "iss": settings.issuer,
        "sub": str(user_id),
        "username": username,
        "typ": "access",
        "jti": new_jti(),
        "iat": int(now.timestamp()),
        "exp": int((now + settings.access_ttl).timestamp()),
    }
    return jwt.encode(payload, settings.secret, algorithm=settings.algorithm)


def create_refresh_token(*, user_id: int, username: str, jti: str, settings: JWTSettings) -> str:
    """
    Crée un refresh token JWT long (par défaut 30 jours).
    Le JTI est fourni pour être stocké côté serveur.
    """
    now = _now()
    payload: DecodedToken = {
        "iss": settings.issuer,
        "sub": str(user_id),
        "username": username,
        "typ": "refresh",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + settings.refresh_ttl).timestamp()),
    }
    return jwt.encode(payload, settings.secret, algorithm=settings.algorithm)


# ==========================================================
# 🔍 Décodage / Validation
# ==========================================================

def decode_token(token: str, settings: JWTSettings) -> DecodedToken:
    """
    Décode et valide un token JWT (signature + expiration).
    Lève JWTError en cas de signature invalide ou expirée.
    """
    try:
        decoded = jwt.decode(
            token,
            settings.secret,
            algorithms=[settings.algorithm],
            options={"verify_aud": False},
        )
    except JWTError as e:
        raise e
    return decoded  # type: ignore[return-value]


# ==========================================================
# 🪙 Utilitaire pratique pour générer un couple complet
# ==========================================================

def mint_token_pair(*, user_id: int, username: str, settings: JWTSettings) -> TokenPair:
    """
    Génère un couple (access_token + refresh_token) cohérent.

    ⚠️ Le refresh_token est émis avec un nouveau JTI aléatoire
       (non enregistré — à stocker via le repository côté serveur).
    """
    access_token = create_access_token(
        user_id=user_id,
        username=username,
        settings=settings,
    )
    jti = new_jti()
    refresh_token = create_refresh_token(
        user_id=user_id,
        username=username,
        jti=jti,
        settings=settings,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(settings.access_ttl.total_seconds()),
    }
