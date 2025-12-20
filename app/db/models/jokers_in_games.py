from sqlmodel import Field
from sqlalchemy import UniqueConstraint

from app.db.models.base import BaseModelDB

class JokerInGame(BaseModelDB, table=True):
    __tablename__ = "joker_in_game"
    __table_args__ = (
        UniqueConstraint("joker_id", "game_id", name="uq_joker_in_game"),
    )

    joker_id: int = Field(foreign_key="joker.id", index=True)
    game_id: int = Field(foreign_key="game.id", index=True)