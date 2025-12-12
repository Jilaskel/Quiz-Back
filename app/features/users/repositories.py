"""
➡️ But : Encapsuler toutes les opérations de base de données.

UserRepository : CRUD (create, read, update, delete) sur la table User.

Ne contient aucune logique métier, juste de la persistance.

🔹 Avantages :

Réutilisable (les services n’ont pas à savoir comment la DB fonctionne).

Testable indépendamment (mock du repo sans base réelle).
"""

from typing import Sequence
from sqlmodel import Session, select, func
from app.models.users import User

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def list(self, offset: int, limit: int) -> Sequence[User]:
        return self.session.exec(select(User).offset(offset).limit(limit)).all()

    def count(self) -> int:
        return self.session.exec(select(func.count(User.id))).one()

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def create(self, *, username: str, hashed_password: str) -> User:
        user = User(
            username=username,
            hashed_password=hashed_password,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(self, user: User, **changes) -> User:
        for k, v in changes.items():
            setattr(user, k, v)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.session.delete(user)
        self.session.commit()
