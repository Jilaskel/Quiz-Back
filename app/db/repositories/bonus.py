from typing import Any, Sequence

from sqlmodel import select

from app.db.repositories.base import BaseRepository

from app.db.models.bonus import Bonus

class BonusRepository(BaseRepository[Bonus]):
    model = Bonus

    def list_name_description(self) -> Sequence[Any]:
        stmt = select(Bonus.id, Bonus.name, Bonus.description).order_by(Bonus.name.asc())
        return self.session.exec(stmt).all()