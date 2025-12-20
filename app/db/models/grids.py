from typing import Optional
from sqlmodel import Field
from sqlalchemy import UniqueConstraint

from app.db.models.base import BaseModelDB

class Grid(BaseModelDB, table=True):
    __table_args__ = (
        UniqueConstraint("game_id", "row", "column", name="uq_grids_game_cell"),
    )

    game_id: int = Field(foreign_key="game.id", index=True)

    # round_id peut rester nullable si la case n’est pas encore jouée
    round_id: Optional[int] = Field(default=None, foreign_key="round.id", index=True)

    question_id: int = Field(foreign_key="question.id", index=True)

    correct_answer: bool = Field(default=False, nullable=False)
    skip_answer: bool = Field(default=False, nullable=False)

    row: int = Field(nullable=False)
    column: int = Field(nullable=False)