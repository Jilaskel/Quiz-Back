from sqlmodel import Field
from sqlalchemy import UniqueConstraint

from app.db.models.base import BaseModelDB

class Round(BaseModelDB, table=True):
    __table_args__ = (
        UniqueConstraint("player_id", "round_number", name="uq_rounds_player_round_number"),
    )

    player_id: int = Field(foreign_key="player.id", index=True)
    round_number: int = Field(nullable=False)