"""
➡️ But : Encapsuler toutes les opérations de base de données.

UserRepository : CRUD (create, read, update, delete) sur la table User.

Ne contient aucune logique métier, juste de la persistance.

🔹 Avantages :

Réutilisable (les services n’ont pas à savoir comment la DB fonctionne).

Testable indépendamment (mock du repo sans base réelle).
"""

# app/db/repositories/users.py
from __future__ import annotations

from typing import Optional
from sqlmodel import select

from app.db.repositories.base import BaseRepository
from app.db.models.users import User

class UserRepository(BaseRepository[User]):
    """
    Repository pour la table User.
    Hérite du CRUD générique de BaseRepository.
    Contient uniquement les requêtes spécifiques à User.
    """
    model = User

    def get_by_username(self, username: str) -> Optional[User]:
        """Retourne un utilisateur par son nom d'utilisateur."""
        return self.session.exec(
            select(self.model).where(self.model.username == username)
        ).first()
