from typing import Optional
from sqlmodel import select

from app.db.repositories.base import BaseRepository
from app.db.models.videos import Video


class VideoRepository(BaseRepository[Video]):
    """CRUD Vidéos + requêtes spécifiques."""
    model = Video

    def get_by_key(self, object_key: str) -> Optional[Video]:
        return self.session.exec(
            select(self.model).where(self.model.object_key == object_key)
        ).first()

    def get_by_sha(self, sha256: str) -> Optional[Video]:
        return self.session.exec(
            select(self.model).where(self.model.sha256 == sha256)
        ).first()
