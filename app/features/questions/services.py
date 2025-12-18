from typing import Optional, Sequence

from app.db.repositories.questions import QuestionRepository
from app.db.models.questions import Question
from app.features.questions.schemas import QuestionCreateIn, QuestionUpdateIn


class QuestionService:
    """
    Service métier Questions.
    Pour l’instant minimal (les endpoints arriveront plus tard).
    """

    def __init__(self, repo: QuestionRepository):
        self.repo = repo

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
