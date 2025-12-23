from typing import Sequence, Dict, Set, Optional, List
from dataclasses import dataclass

from sqlmodel import select

from app.db.repositories.base import BaseRepository

from app.db.models.jokers_used_in_games import JokerUsedInGame
from app.db.models.jokers_in_games import JokerInGame
from app.db.models.jokers import Joker
from app.db.models.rounds import Round
from app.db.models.players import Player


@dataclass(frozen=True)
class JokerUsedForScoringRow:
    round_id: int
    using_player_id: int
    joker_name: str
    target_player_id: Optional[int]
    target_grid_id: Optional[int]


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

    def list_used_joker_in_game_ids_grouped_by_player_for_game(self, game_id: int) -> Dict[int, Set[int]]:
        """
        Retourne {player_id -> set(joker_in_game_id)} pour une partie.
        On déduit le player via JokerUsedInGame.round_id -> Round.player_id,
        et on filtre la partie via JokerUsedInGame.joker_in_game_id -> JokerInGame.game_id.
        """
        stmt = (
            select(Round.player_id, JokerUsedInGame.joker_in_game_id)
            .join(Round, Round.id == JokerUsedInGame.round_id)
            .join(JokerInGame, JokerInGame.id == JokerUsedInGame.joker_in_game_id)
            .where(JokerInGame.game_id == game_id)
        )

        rows = self.session.exec(stmt).all()

        used: Dict[int, Set[int]] = {}
        for player_id, joker_in_game_id in rows:
            used.setdefault(player_id, set()).add(joker_in_game_id)
        return used

    # ------------------------------------------------------------------
    # NEW: pour scoring (avec Joker.name + using_player_id + targets)
    # ------------------------------------------------------------------

    def list_used_for_game_for_scoring(self, game_id: int) -> List[JokerUsedForScoringRow]:
        """
        Retourne les jokers utilisés dans une partie, enrichis pour le scoring :
        - round_id : round où le joker a été utilisé
        - using_player_id : joueur de ce round
        - joker_name : Joker.name (doit correspondre au YAML.name)
        - target_player_id / target_grid_id : cibles éventuelles
        """
        stmt = (
            select(
                JokerUsedInGame.round_id,
                Round.player_id,
                Joker.name,
                JokerUsedInGame.target_player_id,
                JokerUsedInGame.target_grid_id,
            )
            .join(Round, Round.id == JokerUsedInGame.round_id)
            .join(JokerInGame, JokerInGame.id == JokerUsedInGame.joker_in_game_id)
            .join(Joker, Joker.id == JokerInGame.joker_id)
            .where(JokerInGame.game_id == game_id)
        )

        rows = self.session.exec(stmt).all()

        return [
            JokerUsedForScoringRow(
                round_id=round_id,
                using_player_id=using_player_id,
                joker_name=joker_name,
                target_player_id=target_player_id,
                target_grid_id=target_grid_id,
            )
            for (round_id, using_player_id, joker_name, target_player_id, target_grid_id) in rows
        ]

    def list_used_joker_in_game_ids_for_player_before_round(
        self, game_id: int, player_id: int, round_id: int
    ) -> Sequence[int]:
        """
        Jokers utilisés dans les tours précédents PAR CE JOUEUR (round.id < round_id).
        """
        stmt = (
            select(JokerUsedInGame.joker_in_game_id)
            .join(Round, Round.id == JokerUsedInGame.round_id)
            .join(Player, Player.id == Round.player_id)
            .join(JokerInGame, JokerInGame.id == JokerUsedInGame.joker_in_game_id)
            .where(
                JokerInGame.game_id == game_id,
                Round.player_id == player_id,
                Round.id < round_id,
            )
        )
        return self.session.exec(stmt).all()