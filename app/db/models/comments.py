from typing import Optional
from sqlmodel import Field
from sqlalchemy import UniqueConstraint

from app.db.models.base import BaseModelDB


class ThemeComment(BaseModelDB, table=True):
    __table_args__ = (
        UniqueConstraint("game_id", "theme_id", name="uq_theme_comment_game_theme"),
    )

    game_id: int = Field(foreign_key="game.id", index=True, nullable=False)
    theme_id: int = Field(foreign_key="theme.id", index=True, nullable=False)

    score: int = Field(ge=0, le=5, nullable=False)
    comment: Optional[str] = Field(default=None)
