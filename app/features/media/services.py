from typing import Optional, Callable
from fastapi import UploadFile, HTTPException, status
import io

from app.core.config import settings
from app.db.repositories.images import ImageRepository
from app.utils.s3 import make_s3_client, presign_get_url
from app.utils.images import read_and_validate, build_object_key

class ImageService:
    """
    Service Images : orchestre repository + S3/MinIO.
    Aucune logique SQL directe ici, erreurs en HTTPException propres.
    """

    def __init__(
        self,
        *,
        repo: ImageRepository,
        s3_client_factory: Callable[[], object] = make_s3_client,
    ):
        self.repo = repo
        self._s3_factory = s3_client_factory
        self.settings = settings

    async def upload(self, file: UploadFile, *, owner_id: Optional[int]) -> dict:
        raw = await file.read()
        try:
            mime, ext, size, sha = read_and_validate(raw, max_mb=self.settings.MAX_UPLOAD_MB)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        key = build_object_key(owner_id, ext)
        s3 = self._s3_factory()
        try:
            s3.upload_fileobj(
                Fileobj=io.BytesIO(raw),
                Bucket=self.settings.S3_BUCKET,
                Key=key,
                ExtraArgs={"ContentType": mime, "Metadata": {"sha256": sha}},
            )
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erreur upload MinIO: {e}")

        img = self.repo.create(
            object_key=key,
            bucket=self.settings.S3_BUCKET,
            mime_type=mime,
            bytes=size,
            sha256=sha,
            status="ready",
            owner_id=owner_id,
        )
        return {"id": img.id, "key": key, "bytes": size, "mime": mime}

    def signed_get(self, image_id: str) -> dict:
        img = self.repo.get(image_id)
        if not img:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image introuvable")
        s3 = self._s3_factory()
        url = presign_get_url(
            s3,
            bucket=img.bucket,
            key=img.object_key,
            content_type=img.mime_type,
            ttl=self.settings.PRESIGN_TTL_SECONDS,
        )
        return {"id": image_id, "url": url, "expires_in": self.settings.PRESIGN_TTL_SECONDS}

    def delete(self, image_id: str) -> None:
        img = self.repo.get(image_id)
        if not img:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image introuvable")
        s3 = self._s3_factory()
        try:
            s3.delete_object(Bucket=img.bucket, Key=img.object_key)
        except Exception as e:
            # On tente tout de même de supprimer la ligne si l'objet n'existe plus
            self.repo.delete(img)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erreur MinIO: {e}")
        self.repo.delete(img)
