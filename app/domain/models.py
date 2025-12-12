"""
➡️ But : Définir la structure des tables de la base (ORM).

Contient les classes héritant de SQLModel (ou Base de SQLAlchemy).

Représente les objets persistés (ici : Todo).

Chaque champ = une colonne SQL (avec type, index, clé primaire...).

🔹 Avantages :

Tu manipules des objets Python, pas du SQL brut.

Facile à migrer vers PostgreSQL ou MySQL plus tard.
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    done: bool = False
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
