from typing import Optional
from sqlmodel import Field
from sqlalchemy import Column, ForeignKey, Integer

from .base import BaseModelDB


class Question(BaseModelDB, table=True):
    """
    Questions associées à un thème.
    Les médias (image/audio/video) sont optionnels et séparés par table.
    """

    question: str = Field(description="Intitulé de la question")
    answer: str = Field(description="Réponse attendue")

    points: int = Field(default=1, ge=0, description="Points attribués à la question")

    # FK obligatoire vers Theme
    theme_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("theme.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="Thème associé",
    )

    # Images optionnelles
    question_image_id: Optional[int] = Field(default=None, foreign_key="image.id")
    answer_image_id: Optional[int] = Field(default=None, foreign_key="image.id")

    # Audios optionnels
    question_audio_id: Optional[int] = Field(default=None, foreign_key="audio.id")
    answer_audio_id: Optional[int] = Field(default=None, foreign_key="audio.id")

    # Videos optionnelles
    question_video_id: Optional[int] = Field(default=None, foreign_key="video.id")
    answer_video_id: Optional[int] = Field(default=None, foreign_key="video.id")
