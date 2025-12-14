from typing import Optional
from sqlmodel import Field, Relationship
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, ForeignKey, Integer

from .base import BaseModelDB
from .users import User

class Image(BaseModelDB, table=True):
    """Images stockées dans MinIO, référencées dans la base."""

    object_key: str = Field(index=True, unique=True, description="Chemin de l'objet dans le bucket S3/MinIO")
    bucket: str = Field(default="media", description="Nom du bucket")
    mime_type: str = Field(description="Type MIME (image/jpeg, image/png, etc.)")
    bytes: int = Field(description="Taille en octets")
    sha256: Optional[str] = Field(default=None, description="Hash pour la déduplication")
    status: str = Field(default="ready", description="Statut du traitement (ready, pending, failed)")

    # owner_id: Optional[int] = Field(default=None, foreign_key="user.id", description="Propriétaire de l'image")
    owner_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("user.id", ondelete="CASCADE"),  # optionnel : cascade côté DB
            nullable=False,
            index=True,
        ),
        description="Propriétaire de l'image",
    )

    # Relation ORM
    # owner: Optional[User] = Relationship(back_populates="images")
