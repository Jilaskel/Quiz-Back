"""
➡️ But : Contenir la logique métier : orchestrer les repos, appliquer des règles, gérer les erreurs.

UserService : applique les validations logiques (ex : vérifier si un élément existe avant suppression).

Lève les exceptions HTTP (HTTPException) pour informer proprement le client.

🔹 Avantages :

Code métier découplé du web.

Test unitaire possible sans passer par FastAPI.
"""

from datetime import datetime
from fastapi import HTTPException, status
from app.features.users.repositories import UserRepository
from app.models.users import User

from app.security.password import hash_password

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def list(self, offset: int, limit: int):
        items = self.repo.list(offset, limit)
        total = self.repo.count()
        return {"items": items, "total": total}

    def get(self, user_id: int) -> User:
        user = self.repo.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def create(self, username: str, password: str) -> User:
        return self.repo.create(
            username=username,
            hashed_password=hash_password(password)
        )

    def update(self, user_id: int, *, username: str | None, password: str | None) -> User:
        user = self.get(user_id)
        changes = {}
        if username is not None:
            changes["username"] = username
        if password is not None:
            changes["password"] = hash_password(password)
        changes["updated_at"] = datetime.utcnow()
        return self.repo.update(user, **changes)

    def delete(self, user_id: int) -> None:
        user = self.get(user_id)
        self.repo.delete(user)
