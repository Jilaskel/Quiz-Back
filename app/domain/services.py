"""
➡️ But : Contenir la logique métier : orchestrer les repos, appliquer des règles, gérer les erreurs.

TodoService : applique les validations logiques (ex : vérifier si un élément existe avant suppression).

Lève les exceptions HTTP (HTTPException) pour informer proprement le client.

🔹 Avantages :

Code métier découplé du web.

Test unitaire possible sans passer par FastAPI.
"""

from datetime import datetime
from fastapi import HTTPException, status
from app.domain.repositories import TodoRepository
from app.domain.models import Todo

class TodoService:
    def __init__(self, repo: TodoRepository):
        self.repo = repo

    def list(self, offset: int, limit: int):
        items = self.repo.list(offset, limit)
        total = self.repo.count()
        return {"items": items, "total": total}

    def get(self, todo_id: int) -> Todo:
        todo = self.repo.get(todo_id)
        if not todo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
        return todo

    def create(self, title: str) -> Todo:
        return self.repo.create(title=title)

    def update(self, todo_id: int, *, title: str | None, done: bool | None) -> Todo:
        todo = self.get(todo_id)
        changes = {}
        if title is not None:
            changes["title"] = title
        if done is not None:
            changes["done"] = done
        changes["updated_at"] = datetime.utcnow()
        return self.repo.update(todo, **changes)

    def delete(self, todo_id: int) -> None:
        todo = self.get(todo_id)
        self.repo.delete(todo)
