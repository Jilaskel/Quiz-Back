from typing import Any, Sequence

from sqlmodel import select

from app.db.repositories.base import BaseRepository

from app.db.models.jokers_in_games import JokerInGame
from app.db.models.jokers import Joker

class JokerInGameRepository(BaseRepository[JokerInGame]):
    model = JokerInGame

    def list_for_game(self, game_id: int) -> Sequence[Any]:
        stmt = (
            select(
                JokerInGame.id.label("joker_in_game_id"),
                Joker.id.label("joker_id"),
                Joker.name,
                Joker.description,
            )
            .join(Joker, Joker.id == JokerInGame.joker_id)
            .where(JokerInGame.game_id == game_id)
            .order_by(Joker.name.asc())
        )
        return self.session.exec(stmt).all()