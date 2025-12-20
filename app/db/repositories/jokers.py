from typing import Any, Sequence

from sqlmodel import select

from app.db.repositories.base import BaseRepository

from app.db.models.jokers import Joker

class JokerRepository(BaseRepository[Joker]):
    model = Joker

    def list_name_description(self) -> Sequence[Any]:
        stmt = select(Joker.id, Joker.name, Joker.description).order_by(Joker.name.asc())
        return self.session.exec(stmt).all()