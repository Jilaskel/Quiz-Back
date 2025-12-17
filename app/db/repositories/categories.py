"""
➡️ But : Encapsuler toutes les opérations de base de données.

UserRepository : CRUD (create, read, update, delete) sur la table User.

Ne contient aucune logique métier, juste de la persistance.

🔹 Avantages :

Réutilisable (les services n’ont pas à savoir comment la DB fonctionne).

Testable indépendamment (mock du repo sans base réelle).
"""

from typing import Optional, List, Tuple
from sqlmodel import select

from app.db.repositories.base import BaseRepository
from app.db.models.categories import Category
from app.db.models.colors import Color

class CategoryRepository(BaseRepository[Category]):
    model = Category

    def list_with_colors(self, order_by_name: bool = True) -> List[Tuple[int, str, str]]:
        """
        Jointure Category ↔ Color et renvoie une projection simple:
          (category_id, category_name, color_hex_code)

        Pas de logique métier ici : juste data access.
        """
        statement = (
            select(Category.id, Category.name, Color.hex_code)
            .join(Color, Category.color_id == Color.id)
        )
        if order_by_name:
            statement = statement.order_by(Category.name.asc())

        return self.session.exec(statement).all()