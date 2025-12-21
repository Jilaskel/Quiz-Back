from typing import Optional, Sequence, Tuple, Any, Dict

from app.db.repositories.questions import QuestionRepository
from app.db.repositories.themes import ThemeRepository

from app.db.models.questions import Question

from app.features.questions.schemas import (
    QuestionCreateIn,
    QuestionUpdateIn,
    QuestionJoinWithSignedUrlOut,
)

from app.features.media.services import ImageService, AudioService, VideoService


class QuestionService:
    """
    Service métier Questions.
    """

    def __init__(
        self,
        repo: QuestionRepository,
        theme_repo: ThemeRepository,
        image_svc: ImageService,
        audio_svc: AudioService,
        video_svc: VideoService,
    ):
        self.repo = repo
        self.theme_repo = theme_repo
        self.image_svc = image_svc
        self.audio_svc = audio_svc
        self.video_svc = video_svc

    def create(self, payload: QuestionCreateIn) -> Question:
        return self.repo.create(**payload.model_dump())

    def get_one(self, question_id: int) -> Optional[Question]:
        return self.repo.get(question_id)

    def list_by_theme(
        self,
        theme_id: int,
        *,
        offset: int = 0,
        limit: int = 100,
        newest_first: bool = True,
    ) -> Sequence[Question]:
        return self.repo.list_by_theme(theme_id, offset=offset, limit=limit, newest_first=newest_first)

    def update(self, question_id: int, payload: QuestionUpdateIn) -> Question:
        q = self.repo.get(question_id)
        if not q:
            raise LookupError("Question not found.")
        changes = payload.model_dump(exclude_unset=True)
        return self.repo.update(q, **changes)

    def delete(self, question_id: int) -> None:
        q = self.repo.get(question_id)
        if not q:
            return
        self.repo.delete(q)

    # ---------------------------------------------------------------------
    # Détails enrichis + signed URLs
    # ---------------------------------------------------------------------

    def _assert_can_view(self, user_ctx: Optional[Tuple[int, bool]], theme: Any) -> None:
        """
        IMPORTANT: adapte cette logique à celle déjà utilisée côté ThemeService.
        Ici version "safe" : si thème privé => owner/admin.
        """
        # si ton modèle Theme n'a pas ces champs, remplace par tes règles existantes
        is_public = getattr(theme, "is_public", True)
        if is_public:
            return

        if not user_ctx:
            raise PermissionError("UNAUTHENTICATED")

        user_id, is_admin = user_ctx
        if is_admin:
            return

        owner_id = getattr(theme, "owner_id", None)
        if owner_id != user_id:
            raise PermissionError("FORBIDDEN")

    def _can_sign_media_for_theme(self, theme: Any, user_ctx: Optional[Tuple[int, bool]]) -> bool:
        """
        IMPORTANT: adapte à ThemeService._can_sign_media_for_theme si tu l'as déjà.
        """
        if not user_ctx:
            return False
        user_id, is_admin = user_ctx
        if is_admin:
            return True
        owner_id = getattr(theme, "owner_id", None)
        return owner_id == user_id

    def get_one_detail(
        self,
        question_id: int,
        user_ctx: Optional[Tuple[int, bool]],
        *,
        with_signed_url: bool,
    ) -> QuestionJoinWithSignedUrlOut:
        # 1) question
        q = self.repo.get(question_id)
        if not q:
            raise LookupError("Question not found.")

        # 2) theme pour permissions
        theme = self.theme_repo.get(q.theme_id)
        if not theme:
            raise LookupError("Theme not found.")
        self._assert_can_view(user_ctx, theme)

        # 3) autorisation de signer
        allow_sign = with_signed_url and self._can_sign_media_for_theme(theme, user_ctx)

        # 4) signed urls (si demandé et autorisé)
        # images
        qi_url = qi_exp = ai_url = ai_exp = None
        if allow_sign and q.question_image_id:
            d: Dict[str, Any] = self.image_svc.signed_get(str(q.question_image_id))
            qi_url, qi_exp = d.get("url"), d.get("expires_in")
        if allow_sign and q.answer_image_id:
            d = self.image_svc.signed_get(str(q.answer_image_id))
            ai_url, ai_exp = d.get("url"), d.get("expires_in")

        # audios
        qa_url = qa_exp = aa_url = aa_exp = None
        if allow_sign and q.question_audio_id:
            d = self.audio_svc.signed_get(str(q.question_audio_id))
            qa_url, qa_exp = d.get("url"), d.get("expires_in")
        if allow_sign and q.answer_audio_id:
            d = self.audio_svc.signed_get(str(q.answer_audio_id))
            aa_url, aa_exp = d.get("url"), d.get("expires_in")

        # videos
        qv_url = qv_exp = av_url = av_exp = None
        if allow_sign and q.question_video_id:
            d = self.video_svc.signed_get(str(q.question_video_id))
            qv_url, qv_exp = d.get("url"), d.get("expires_in")
        if allow_sign and q.answer_video_id:
            d = self.video_svc.signed_get(str(q.answer_video_id))
            av_url, av_exp = d.get("url"), d.get("expires_in")

        return QuestionJoinWithSignedUrlOut(
            id=q.id,
            theme_id=q.theme_id,
            question=q.question,
            answer=q.answer,
            points=q.points,

            question_image_id=q.question_image_id,
            answer_image_id=q.answer_image_id,
            question_audio_id=q.question_audio_id,
            answer_audio_id=q.answer_audio_id,
            question_video_id=q.question_video_id,
            answer_video_id=q.answer_video_id,

            question_image_signed_url=qi_url,
            question_image_signed_expires_in=qi_exp,
            answer_image_signed_url=ai_url,
            answer_image_signed_expires_in=ai_exp,

            question_audio_signed_url=qa_url,
            question_audio_signed_expires_in=qa_exp,
            answer_audio_signed_url=aa_url,
            answer_audio_signed_expires_in=aa_exp,

            question_video_signed_url=qv_url,
            question_video_signed_expires_in=qv_exp,
            answer_video_signed_url=av_url,
            answer_video_signed_expires_in=av_exp,

            created_at=getattr(q, "created_at", None),
            updated_at=getattr(q, "updated_at", None),
        )
