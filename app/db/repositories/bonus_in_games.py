from typing import Sequence, Any

from sqlmodel import select

from app.db.repositories.base import BaseRepository

from app.db.models.bonus_in_games import BonusInGame
from app.db.models.bonus import Bonus

class BonusInGameRepository(BaseRepository[BonusInGame]):
    model = BonusInGame

    def list_for_game(self, game_id: int) -> Sequence[Any]:
        stmt = (
            select(
                BonusInGame.id.label("bonus_in_game_id"),
                Bonus.id.label("bonus_id"),
                Bonus.name,
                Bonus.description,
            )
            .join(Bonus, Bonus.id == BonusInGame.bonus_id)
            .where(BonusInGame.game_id == game_id)
            .order_by(Bonus.name.asc())
        )
        return self.session.exec(stmt).all()