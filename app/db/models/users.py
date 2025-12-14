"""
➡️ But : Définir la structure des tables de la base (ORM).

Contient les classes héritant de SQLModel (ou Base de SQLAlchemy).

Représente les objets persistés. Ici on représente les tables ayant un rapport avec les users.

Chaque champ = une colonne SQL (avec type, index, clé primaire...).

🔹 Avantages :

Tu manipules des objets Python, pas du SQL brut.

Facile à migrer vers PostgreSQL ou MySQL plus tard.
"""

from sqlmodel import Field

from .base import BaseModelDB

class User(BaseModelDB, table=True):
    username: str = Field(index=True, unique=True)
    hashed_password: str
    admin: bool = Field(default=False)