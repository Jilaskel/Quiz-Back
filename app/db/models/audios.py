from typing import Optional
from sqlmodel import Field
from sqlalchemy import Column, ForeignKey, Integer

from .base import BaseModelDB


class Audio(BaseModelDB, table=True):
    """Audios stockés dans MinIO, référencés en DB."""

    object_key: str = Field(index=True, unique=True, description="Chemin de l'objet dans le bucket S3/MinIO")
    bucket: str = Field(default="media", description="Nom du bucket")
    mime_type: str = Field(description="Type MIME (audio/mpeg, audio/wav, etc.)")
    bytes: int = Field(description="Taille en octets")
    sha256: Optional[str] = Field(default=None, description="Hash pour la déduplication")
    status: str = Field(default="ready", description="Statut du traitement (ready, pending, failed)")

    owner_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("user.id"),
            nullable=False,
            index=True,
        ),
        description="Propriétaire de l'audio",
    )
