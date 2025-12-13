from datetime import datetime, timezone
from typing import Optional, Sequence
from sqlmodel import select

from app.db.repositories.base import BaseRepository
from app.db.models.refresh_tokens import RefreshToken

class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_by_jti(self, jti: str) -> Optional[RefreshToken]:
        return self.session.exec(
            select(self.model).where(self.model.jti == jti)
        ).first()

    def list_active_for_user(self, user_id: int) -> Sequence[RefreshToken]:
        now = datetime.now(timezone.utc)
        return self.session.exec(
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.revoked_at.is_(None))
            .where(self.model.expires_at > now)
            .order_by(self.model.expires_at.desc())
        ).all()

    def revoke(self, jti: str) -> None:
        token = self.get_by_jti(jti)
        if not token or token.revoked_at:
            return
        token.revoked_at = datetime.now(timezone.utc)
        self.session.add(token)
        self.session.commit()

    def revoke_all_for_user(self, user_id: int) -> int:
        tokens = self.list_active_for_user(user_id)
        if not tokens:
            return 0
        now = datetime.now(timezone.utc)
        for token in tokens:
            token.revoked_at = now
            self.session.add(token)
        self.session.commit()
        return len(tokens)

    def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = self.session.exec(
            select(self.model).where(self.model.expires_at <= now)
        ).all()
        for token in expired:
            self.session.delete(token)
        self.session.commit()
        return len(expired)
