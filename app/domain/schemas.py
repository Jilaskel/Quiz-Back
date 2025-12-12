"""
➡️ But : Définir les formats d’entrée/sortie de l’API (couche validation).

Contient les modèles Pydantic utilisés par FastAPI :

TodoCreate → corps de requête POST

TodoUpdate → corps PATCH

TodoOut → réponse de l’API

Sépare les modèles "de stockage" (ORM) de ceux "de transfert" (I/O API).

🔹 Avantages :

Validation automatique.

Documente les champs dans Swagger (types, exemples...).

Empêche d’exposer par erreur des infos sensibles (ex: hash de mot de passe).
"""

from datetime import datetime
from pydantic import BaseModel, Field

class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, examples=["Acheter du lait"])

class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, examples=["Aller courir"])
    done: bool | None = Field(None, examples=[True])

class TodoOut(BaseModel):
    id: int
    title: str
    done: bool
    description: str
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
