from typing import Any, Optional, Sequence

from sqlmodel import select
from sqlalchemy import func

from app.db.repositories.base import BaseRepository

from app.db.models.players import Player
from app.db.models.rounds import Round
from app.db.models.grids import Grid

class RoundRepository(BaseRepository[Round]):
    model = Round

    def list_by_game(self, game_id: int) -> Sequence[Any]:
        """
        Lignes plates (Round + Player) utile pour état.
        """
        stmt = (
            select(
                Round.id.label("round_id"),
                Round.round_number,
                Round.player_id,
                Player.order.label("player_order"),
                Player.name.label("player_name"),
            )
            .join(Player, Player.id == Round.player_id)
            .where(Player.game_id == game_id)
            .order_by(Round.round_number.asc(), Round.id.asc())
        )
        return self.session.exec(stmt).all()

    def get_last_round_not_in_grid(self, game_id: int) -> Optional[Any]:
        """
        Dernier tour ajouté à rounds qui n'est pas encore utilisé dans grids de la partie.
        """
        subq_used_round_ids = (
            select(func.distinct(Grid.round_id))
            .where(Grid.game_id == game_id, Grid.round_id.is_not(None))
            .subquery()
        )

        stmt = (
            select(
                Round.id.label("round_id"),
                Round.round_number,
                Round.player_id,
                Player.order.label("player_order"),
                Player.name.label("player_name"),
                Player.theme_id.label("player_theme_id"),
            )
            .join(Player, Player.id == Round.player_id)
            .where(
                Player.game_id == game_id,
                Round.id.not_in(select(subq_used_round_ids.c.round_id)),
            )
            .order_by(Round.round_number.desc(), Round.id.desc())
        )
        return self.session.exec(stmt).first()
    
    def get_round_context(self, round_id: int) -> Optional[Any]:
        """
        Retourne un objet "plat" avec :
        - round_id, round_number
        - player_id, player_order, player_name, player_theme_id
        - game_id
        Permet :
        - vérifier round ∈ game
        - calculer next round
        - fournir infos state si besoin
        """
        stmt = (
            select(
                Round.id.label("round_id"),
                Round.round_number.label("round_number"),
                Player.id.label("player_id"),
                Player.order.label("player_order"),
                Player.name.label("player_name"),
                Player.theme_id.label("player_theme_id"),
                Player.game_id.label("game_id"),
            )
            .join(Player, Player.id == Round.player_id)
            .where(Round.id == round_id)
            .limit(1)
        )
        return self.session.exec(stmt).first()

    def exists_for_player_round_number(self, player_id: int, round_number: int) -> bool:
        """
        True si un round existe déjà pour (player_id, round_number).
        """
        stmt = (
            select(func.count(Round.id))
            .where(Round.player_id == player_id, Round.round_number == round_number)
        )
        return int(self.session.exec(stmt).one()) > 0