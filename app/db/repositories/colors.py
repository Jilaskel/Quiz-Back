# app/db/repositories/colors.py
from typing import Any, Sequence

from sqlmodel import select

from app.db.repositories.base import BaseRepository
from app.db.models.colors import Color


class ColorRepository(BaseRepository[Color]):
    model = Color

    def list_public(self, offset: int = 0, limit: int = 500) -> Sequence[Any]:
        """
        Retourne des lignes (id, name, hex_code) triées par name.
        (On renvoie des tuples/rows légers, le service mappe en dict/schéma.)
        """
        stmt = (
            select(Color.id, Color.name, Color.hex_code)
            .order_by(Color.name.asc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(stmt).all()
