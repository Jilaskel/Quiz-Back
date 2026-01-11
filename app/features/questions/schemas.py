from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field as PydField


class QuestionCreateIn(BaseModel):
    question: str = PydField(..., description="Intitulé de la question")
    answer: str = PydField(..., description="Réponse attendue")
    points: int = PydField(1, ge=0, description="Points attribués à la question")

    theme_id: int = PydField(..., ge=1, description="ID du thème associé")

    question_image_id: Optional[int] = None
    answer_image_id: Optional[int] = None

    question_audio_id: Optional[int] = None
    answer_audio_id: Optional[int] = None

    question_video_id: Optional[int] = None
    answer_video_id: Optional[int] = None


class QuestionUpdateIn(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    points: Optional[int] = PydField(None, ge=0)

    question_image_id: Optional[int] = None
    answer_image_id: Optional[int] = None

    question_audio_id: Optional[int] = None
    answer_audio_id: Optional[int] = None

    question_video_id: Optional[int] = None
    answer_video_id: Optional[int] = None


class QuestionOut(BaseModel):
    id: int
    theme_id: int

    question: str
    answer: str
    points: int

    question_image_id: Optional[int]
    answer_image_id: Optional[int]

    question_audio_id: Optional[int]
    answer_audio_id: Optional[int]

    question_video_id: Optional[int]
    answer_video_id: Optional[int]

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class QuestionJoinWithSignedUrlOut(QuestionOut):
    question_image_signed_url: Optional[str] = None
    question_image_signed_expires_in: Optional[int] = None
    answer_image_signed_url: Optional[str] = None
    answer_image_signed_expires_in: Optional[int] = None

    question_audio_signed_url: Optional[str] = None
    question_audio_signed_expires_in: Optional[int] = None
    answer_audio_signed_url: Optional[str] = None
    answer_audio_signed_expires_in: Optional[int] = None

    question_video_signed_url: Optional[str] = None
    question_video_signed_expires_in: Optional[int] = None
    answer_video_signed_url: Optional[str] = None
    answer_video_signed_expires_in: Optional[int] = None

    # Statistiques d'usage pour cette question
    positive_answers_count: int = 0
    negative_answers_count: int = 0
    cancelled_answers_count: int = 0