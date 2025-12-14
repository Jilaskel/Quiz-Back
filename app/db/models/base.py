"""
➡️ But : Définir la structure des tables de la base (ORM).

Contient les classes héritant de SQLModel (ou Base de SQLAlchemy).

Représente les objets persistés. Ici on représente les propriétés communes de toutes les tables.

Chaque champ = une colonne SQL (avec type, index, clé primaire...).

🔹 Avantages :

Tu manipules des objets Python, pas du SQL brut.

Facile à migrer vers PostgreSQL ou MySQL plus tard.
"""

from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class BaseModelDB(SQLModel, table=False):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # created_at = Column(DateTime(timezone=True), server_default=func.now())