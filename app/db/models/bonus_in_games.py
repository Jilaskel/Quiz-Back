
from sqlmodel import Field
from sqlalchemy import UniqueConstraint

from app.db.models.base import BaseModelDB

class BonusInGame(BaseModelDB, table=True):
    __tablename__ = "bonus_in_game"
    __table_args__ = (
        UniqueConstraint("bonus_id", "game_id", name="uq_bonus_in_game"),
    )

    bonus_id: int = Field(foreign_key="bonus.id", index=True)
    game_id: int = Field(foreign_key="game.id", index=True)