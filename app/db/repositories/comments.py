from typing import Optional, Sequence, Tuple, Any

from sqlmodel import select, func

from app.db.repositories.base import BaseRepository
from app.db.models.comments import ThemeComment
from app.db.models.games import Game
from app.db.models.users import User


class ThemeCommentRepository(BaseRepository[ThemeComment]):
    model = ThemeComment

    def get_by_game_and_theme(self, game_id: int, theme_id: int) -> Optional[ThemeComment]:
        stmt = select(ThemeComment).where(
            ThemeComment.game_id == game_id,
            ThemeComment.theme_id == theme_id,
        )
        return self.session.exec(stmt).first()

    def list_by_theme_with_owner(
        self,
        theme_id: int,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Tuple[ThemeComment, int, str]]:
        """List comments for a theme with owning game owner info."""
        stmt = (
            select(
                ThemeComment,
                Game.owner_id.label("owner_id"),
                User.username.label("owner_username"),
            )
            .join(Game, Game.id == ThemeComment.game_id)
            .join(User, User.id == Game.owner_id)
            .where(ThemeComment.theme_id == theme_id)
            .order_by(ThemeComment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(stmt).all()

    def count_by_theme(self, theme_id: int) -> int:
        stmt = select(func.count(ThemeComment.id)).where(ThemeComment.theme_id == theme_id)
        return int(self.session.exec(stmt).one())

    def avg_and_count_for_theme(self, theme_id: int) -> Tuple[float, int]:
        stmt = select(func.avg(ThemeComment.score), func.count(ThemeComment.id)).where(
            ThemeComment.theme_id == theme_id
        )
        avg_val, count_val = self.session.exec(stmt).one()
        avg_val = float(avg_val) if avg_val is not None else 0.0
        count_val = int(count_val or 0)
        return avg_val, count_val
