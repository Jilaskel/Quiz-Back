from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import HTTPException, status

from app.db.repositories.users import UserRepository
from app.db.repositories.refresh_tokens import RefreshTokenRepository
from app.security.password import verify_password, hash_password
from app.security.tokens import (
    JWTSettings,
    create_access_token,
    create_refresh_token,
    decode_token,
    new_jti,
)
from app.features.authentication.schemas import (
    SignUpIn,
    SignInIn,
    TokenPairOut,
    RefreshIn,
    LogoutIn,
    ChangePasswordIn,
)

class AuthService:
    """
    Service d'authentification : orchestre les repositories + tokens.
    Ne contient pas d'accès SQL direct et lève des HTTPException propres.
    """

    def __init__(
        self,
        *,
        user_repo: UserRepository,
        refresh_repo: RefreshTokenRepository,
        jwt_settings: JWTSettings,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.user_repo = user_repo
        self.refresh_repo = refresh_repo
        self.jwt = jwt_settings
        self.now_fn = now_fn

    # ---------- Sign up ----------
    def sign_up(self, payload: SignUpIn):
        if self.user_repo.get_by_username(payload.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )
        user = self.user_repo.create(
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )
        return user

    # ---------- Sign in ----------
    def sign_in(self, payload: SignInIn, *, ip: Optional[str] = None, user_agent: Optional[str] = None) -> TokenPairOut:
        user = self.user_repo.get_by_username(payload.username)
        if not user or not verify_password(payload.password, user.hashed_password):
            # Ne pas révéler si l'utilisateur existe
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        access = create_access_token(user_id=user.id, username=user.username, settings=self.jwt)
        jti = new_jti()
        refresh = create_refresh_token(user_id=user.id, username=user.username, jti=jti, settings=self.jwt)

        # Persist refresh (révocable)
        self.refresh_repo.create(
            jti=jti,
            user_id=user.id,
            expires_at=self.now_fn() + self.jwt.refresh_ttl,
            user_agent=user_agent,
            ip=ip,
        )

        return TokenPairOut(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=int(self.jwt.access_ttl.total_seconds()),
        )

    # ---------- Refresh (rotation) ----------
    def refresh(self, payload: RefreshIn, *, ip: Optional[str] = None, user_agent: Optional[str] = None) -> TokenPairOut:
        # 1) Décoder et valider type
        try:
            decoded = decode_token(payload.refresh_token, self.jwt)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if decoded.get("typ") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        jti = decoded.get("jti")
        if not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # 2) Vérifier en base (existe, non révoqué, non expiré)
        rec = self.refresh_repo.get_by_jti(jti)
        if not rec or rec.revoked_at is not None or rec.expires_at <= self.now_fn():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid")

        # 3) Vérifier l'utilisateur
        user_id = int(decoded["sub"])
        user = self.user_repo.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # 4) Rotation : révoquer l'ancien et émettre un nouveau couple
        self.refresh_repo.revoke(jti)

        new_access = create_access_token(user_id=user.id, username=user.username, settings=self.jwt)
        new_jti = new_jti()
        new_refresh = create_refresh_token(user_id=user.id, username=user.username, jti=new_jti, settings=self.jwt)

        self.refresh_repo.create_token(
            jti=new_jti,
            user_id=user.id,
            expires_at=self.now_fn() + self.jwt.refresh_ttl,
            user_agent=user_agent,
            ip=ip,
        )

        return TokenPairOut(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=int(self.jwt.access_ttl.total_seconds()),
        )

    # ---------- Logout ----------
    def log_out(self, payload: LogoutIn) -> None:
        try:
            decoded = decode_token(payload.refresh_token, self.jwt)
        except Exception:
            # Logout idempotent : silencieux si token illisible
            return

        if decoded.get("typ") != "refresh":
            return

        jti = decoded.get("jti")
        if not jti:
            return

        self.refresh_repo.revoke(jti)

    # ---------- Current user depuis access token ----------
    def get_current_user(self, *, access_token: str):
        try:
            decoded = decode_token(access_token, self.jwt)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if decoded.get("typ") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user = self.user_repo.get(int(decoded["sub"]))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    # ---------- Changement de mot de passe ----------
    def change_password(self, *, user_id: int, payload: ChangePasswordIn) -> None:
        user = self.user_repo.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(payload.old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        self.user_repo.update(
            user,
            hashed_password=hash_password(payload.new_password),
            updated_at=self.now_fn(),
        )
