"""
➡️ But : Encapsuler toutes les opérations de base de données.

TodoRepository : CRUD (create, read, update, delete) sur la table Todo.

Ne contient aucune logique métier, juste de la persistance.

🔹 Avantages :

Réutilisable (les services n’ont pas à savoir comment la DB fonctionne).

Testable indépendamment (mock du repo sans base réelle).
"""

from typing import Sequence
from sqlmodel import Session, select, func
from app.domain.models import Todo

class TodoRepository:
    def __init__(self, session: Session):
        self.session = session

    def list(self, offset: int, limit: int) -> Sequence[Todo]:
        return self.session.exec(select(Todo).offset(offset).limit(limit)).all()

    def count(self) -> int:
        # return self.session.exec(select(func.count("*")).select_from(Todo))
        return self.session.exec(select(func.count(Todo.id))).one()

    def get(self, todo_id: int) -> Todo | None:
        return self.session.get(Todo, todo_id)

    def create(self, *, title: str) -> Todo:
        todo = Todo(title=title)
        self.session.add(todo)
        self.session.commit()
        self.session.refresh(todo)
        return todo

    def update(self, todo: Todo, **changes) -> Todo:
        for k, v in changes.items():
            setattr(todo, k, v)
        self.session.add(todo)
        self.session.commit()
        self.session.refresh(todo)
        return todo

    def delete(self, todo: Todo) -> None:
        self.session.delete(todo)
        self.session.commit()
