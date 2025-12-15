from typing import Optional
from sqlmodel import Field

from .base import BaseModelDB
# from .image import Image           # si tu veux activer les relations
# from .category import Category
# from .user import User


class Theme(BaseModelDB, table=True):
    """Thèmes créés par des utilisateurs, rattachés à une image et à une catégorie."""

    # Métadonnées
    name: str = Field(index=True, description="Nom du thème")
    description: Optional[str] = Field(default=None, description="Description du thème")

    # Visibilité / statut
    is_public: bool = Field(default=False, description="Le thème est-il public ?")
    is_ready: bool = Field(default=False, description="Le thème est prêt à l'usage")
    valid_admin: bool = Field(default=False, description="Validation par un administrateur")

    # Clés étrangères
    image_id: Optional[int] = Field(default=None, foreign_key="image.id")
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    owner_id: int = Field(foreign_key="user.id")

    # Relations ORM éventuelles (décommente si tu as les modèles et back_populates)
    # image: Optional[Image] = Relationship(back_populates="themes")
    # category: Optional[Category] = Relationship(back_populates="themes")
    # owner: User = Relationship(back_populates="themes")
