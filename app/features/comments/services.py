from typing import Optional, Tuple

from app.db.repositories.comments import ThemeCommentRepository
from app.db.repositories.games import GameRepository
from app.db.repositories.players import PlayerRepository
from app.db.repositories.themes import ThemeRepository
from app.db.repositories.users import UserRepository

from app.features.comments.schemas import (
    ThemeCommentCreateIn,
    ThemeCommentUpdateIn,
    ThemeCommentOut,
    ThemeCommentListOut,
)


class PermissionError(Exception):
    pass


class ConflictError(Exception):
    pass


class CommentService:
    def __init__(
        self,
        *,
        comment_repo: ThemeCommentRepository,
        game_repo: GameRepository,
        player_repo: PlayerRepository,
        theme_repo: ThemeRepository,
        user_repo: UserRepository,
    ):
        self.comments = comment_repo
        self.games = game_repo
        self.players = player_repo
        self.themes = theme_repo
        self.users = user_repo

    # --------------- Helpers ---------------
    def _ensure_theme_exists(self, theme_id: int) -> None:
        if not self.themes.get(theme_id):
            raise LookupError("Theme not found.")

    def _ensure_game_owner_or_admin(self, game, *, user_id: int, is_admin: bool) -> None:
        if game.owner_id != user_id and not is_admin:
            raise PermissionError("Forbidden")

    def _ensure_game_finished(self, game) -> None:
        if not getattr(game, "finished", False):
            raise ConflictError("Game not finished")

    def _ensure_theme_played_in_game(self, game_id: int, theme_id: int) -> None:
        if not self.players.exists_for_game_and_theme(game_id, theme_id):
            raise ConflictError("Theme not played in this game")

    def _get_owner_username(self, owner_id: int) -> Optional[str]:
        user = self.users.get(owner_id)
        return getattr(user, "username", None) if user else None

    def _to_out(self, entity, owner_id: int, owner_username: Optional[str]) -> ThemeCommentOut:
        return ThemeCommentOut(
            id=entity.id,
            game_id=entity.game_id,
            theme_id=entity.theme_id,
            score=entity.score,
            comment=entity.comment,
            created_at=getattr(entity, "created_at", None),
            updated_at=getattr(entity, "updated_at", None),
            game_owner_id=owner_id,
            game_owner_username=owner_username,
        )

    # --------------- Commands ---------------
    def create(self, payload: ThemeCommentCreateIn, *, user_id: int, is_admin: bool) -> ThemeCommentOut:
        self._ensure_theme_exists(payload.theme_id)
        game = self.games.get(payload.game_id)
        if not game:
            raise LookupError("Game not found.")

        self._ensure_game_owner_or_admin(game, user_id=user_id, is_admin=is_admin)
        self._ensure_game_finished(game)
        self._ensure_theme_played_in_game(payload.game_id, payload.theme_id)

        existing = self.comments.get_by_game_and_theme(payload.game_id, payload.theme_id)
        if existing:
            raise ConflictError("Comment already exists for this game and theme")

        entity = self.comments.create(
            game_id=payload.game_id,
            theme_id=payload.theme_id,
            score=payload.score,
            comment=payload.comment,
        )
        owner_username = self._get_owner_username(game.owner_id)
        return self._to_out(entity, game.owner_id, owner_username)

    def update(self, comment_id: int, payload: ThemeCommentUpdateIn, *, user_id: int, is_admin: bool) -> ThemeCommentOut:
        entity = self.comments.get(comment_id)
        if not entity:
            raise LookupError("Comment not found.")

        game = self.games.get(entity.game_id)
        if not game:
            raise LookupError("Game not found.")

        self._ensure_game_owner_or_admin(game, user_id=user_id, is_admin=is_admin)

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return self._to_out(entity, game.owner_id, self._get_owner_username(game.owner_id))

        updated = self.comments.update(entity, **changes)
        owner_username = self._get_owner_username(game.owner_id)
        return self._to_out(updated, game.owner_id, owner_username)

    def delete(self, comment_id: int, *, user_id: int, is_admin: bool) -> None:
        entity = self.comments.get(comment_id)
        if not entity:
            return
        game = self.games.get(entity.game_id)
        if not game:
            return
        self._ensure_game_owner_or_admin(game, user_id=user_id, is_admin=is_admin)
        self.comments.delete(entity)

    # --------------- Queries ---------------
    def list_for_theme_with_stats(
        self,
        theme_id: int,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Tuple[ThemeCommentListOut, float, int]:
        self._ensure_theme_exists(theme_id)
        rows = self.comments.list_by_theme_with_owner(theme_id, offset=offset, limit=limit)
        total = self.comments.count_by_theme(theme_id)
        avg, count = self.comments.avg_and_count_for_theme(theme_id)

        items = [self._to_out(row[0], row[1], row[2]) for row in rows]
        return ThemeCommentListOut(items=items, total=total), avg, count
