"""Table des couleurs stockées en format hexadécimal pour usage web. Utilisation pour les joueurs in-game et pour les tags de thèmes"""

from sqlmodel import Field, Relationship
from pydantic import validator
from typing import List

from .base import BaseModelDB

class Color(BaseModelDB, table=True):
    name: str = Field(index=True, unique=True, description="Nom lisible de la couleur (ex: 'rouge vif')")
    hex_code: str = Field(
        regex=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
        max_length=7,
        description="Code couleur hexadécimal au format #RRGGBB ou #RGB",
    )

    categories: List["Category"] = Relationship(back_populates="color")

    # Validator Pydantic pour uniformiser le format
    @validator("hex_code", pre=True)
    def normalize_hex_code(cls, value: str) -> str:
        """Convertit le code hexadécimal en majuscules (#ff5733 → #FF5733)."""
        if not isinstance(value, str):
            raise ValueError("Le code hexadécimal doit être une chaîne de caractères.")
        return value.upper()