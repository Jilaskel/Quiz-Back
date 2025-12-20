from typing import Sequence

from sqlmodel import select

from app.db.repositories.base import BaseRepository

from app.db.models.jokers_used_in_games import JokerUsedInGame
from app.db.models.rounds import Round
from app.db.models.players import Player

class JokerUsedInGameRepository(BaseRepository[JokerUsedInGame]):
    model = JokerUsedInGame

    def list_used_joker_in_game_ids_for_game(self, game_id: int) -> Sequence[int]:
        """
        Tous les jokers utilisés dans la partie (via round -> player -> game).
        """
        stmt = (
            select(JokerUsedInGame.joker_in_game_id)
            .join(Round, Round.id == JokerUsedInGame.round_id)
            .join(Player, Player.id == Round.player_id)
            .where(Player.game_id == game_id)
        )
        return self.session.exec(stmt).all()
    
    def list_used_joker_in_game_ids_for_game_before_round(self, game_id: int, round_id: int) -> Sequence[int]:
        """
        Jokers utilisés dans les tours précédents (round.id < round_id).
        """
        stmt = (
            select(JokerUsedInGame.joker_in_game_id)
            .join(Round, Round.id == JokerUsedInGame.round_id)
            .join(Player, Player.id == Round.player_id)
            .where(Player.game_id == game_id, Round.id < round_id)
        )
        return self.session.exec(stmt).all()

    def list_used_for_round(self, round_id: int) -> Sequence[JokerUsedInGame]:
        stmt = select(JokerUsedInGame).where(JokerUsedInGame.round_id == round_id)
        return self.session.exec(stmt).all()