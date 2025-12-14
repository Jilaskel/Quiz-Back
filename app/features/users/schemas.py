"""
➡️ But : Définir les formats d’entrée/sortie de l’API (couche validation).

Contient les modèles Pydantic utilisés par FastAPI :

UserCreate → corps de requête POST

UserUpdate → corps PATCH

UserOut → réponse de l’API

Sépare les modèles "de stockage" (ORM) de ceux "de transfert" (I/O API).

🔹 Avantages :

Validation automatique.

Documente les champs dans Swagger (types, exemples...).

Empêche d’exposer par erreur des infos sensibles (ex: hash de mot de passe).
"""

from sqlmodel import SQLModel

class UserCreate(SQLModel):
    username: str
    password: str

class UserUpdate(SQLModel):
    username: str | None
    password: str | None

class UserOut(SQLModel):
    id: int
    username: str
    # hashed_password: str
    admin: bool