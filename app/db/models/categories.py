from typing import Optional
from sqlmodel import Field, Relationship

from .base import BaseModelDB
from .colors import Color

class Category(BaseModelDB, table=True):
    """Catégories associées à une couleur existante."""

    name: str = Field(index=True, unique=True, description="Nom de la catégorie (ex: 'Urgent', 'Info', etc.)")
    color_id: Optional[int] = Field(default=None, foreign_key="color.id", description="Référence vers la couleur associée")

    # Relation ORM
    color: Optional[Color] = Relationship(back_populates="categories")
