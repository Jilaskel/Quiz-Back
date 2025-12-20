from typing import Optional
from sqlmodel import Field

from app.db.models.base import BaseModelDB

class JokerUsedInGame(BaseModelDB, table=True):
    __tablename__ = "joker_used_in_game"

    joker_in_game_id: int = Field(foreign_key="joker_in_game.id", index=True)
    round_id: int = Field(foreign_key="round.id", index=True)

    # qui est ciblé par le joker (si pertinent)
    target_player_id: Optional[int] = Field(default=None, foreign_key="player.id", index=True)

    # case de grille ciblée (si pertinent)
    target_grid_id: Optional[int] = Field(default=None, foreign_key="grid.id", index=True)