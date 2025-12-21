from typing import List, Optional, Sequence
from sqlmodel import select
from sqlalchemy import func

from app.db.repositories.base import BaseRepository
from app.db.models.questions import Question


class QuestionRepository(BaseRepository[Question]):
    """CRUD Questions + requêtes spécifiques."""
    model = Question

    def create_many(self, items: List[Question], *, commit: bool = True) -> List[Question]:
        """
        Insert en masse.
        Si commit=False, l'appelant doit commit() lui-même (transaction globale).
        """
        self.session.add_all(items)
        if commit:
            self.session.commit()
            for q in items:
                self.session.refresh(q)
        return items

    def list_by_theme(
        self,
        theme_id: int,
        *,
        offset: int = 0,
        limit: int = 100,
        newest_first: bool = True,
    ) -> Sequence[Question]:
        stmt = select(self.model).where(self.model.theme_id == theme_id)
        stmt = stmt.order_by(self.model.id.desc() if newest_first else self.model.id.asc())
        stmt = stmt.offset(offset).limit(limit)
        return self.session.exec(stmt).all()

    def delete_by_theme(self, theme_id: int, *, commit: bool = True) -> int:
        """
        Supprime toutes les questions d'un thème.
        Retourne un compte approximatif (nb d'objets chargés/supprimés).
        """
        rows = self.session.exec(select(self.model).where(self.model.theme_id == theme_id)).all()
        for r in rows:
            self.session.delete(r)
        if commit:
            self.session.commit()
        return len(rows)

    def count_by_theme(self, theme_id: int) -> int:
        stmt = select(func.count(self.model.id)).where(self.model.theme_id == theme_id)
        return int(self.session.exec(stmt).one())