from typing import Optional, Callable, Tuple
from fastapi import UploadFile, HTTPException, status
import io

from app.core.config import settings
from app.db.repositories.images import ImageRepository
from app.db.repositories.themes import ThemeRepository
from app.utils.s3 import make_s3_internal, make_s3_public, presign_get_url
from app.utils.images import read_and_validate, build_object_key

UserCtx = Optional[Tuple[int, bool]]  # (user_id, is_admin)

class ImageService:
    """
    Service Images : orchestre repository + S3/MinIO.
    Aucune logique SQL directe ici, erreurs en HTTPException propres.
    """

    def __init__(
        self,
        *,
        repo: ImageRepository,
        s3_client_internal_factory: Callable[[], object] = make_s3_internal,
        s3_client_public_factory: Callable[[], object] = make_s3_public,
    ):
        self.repo = repo
        self._s3_internal_factory = s3_client_internal_factory
        self._s3_public_factory = s3_client_public_factory
        self.settings = settings

    async def upload(self, file: UploadFile, *, owner_id: Optional[int]) -> dict:
        raw = await file.read()
        try:
            mime, ext, size, sha = read_and_validate(raw, max_mb=self.settings.MAX_UPLOAD_MB)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        key = build_object_key(owner_id, ext)
        s3 = self._s3_internal_factory()
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
        s3 = self._s3_public_factory()
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
        s3 = self._s3_internal_factory()
        try:
            s3.delete_object(Bucket=img.bucket, Key=img.object_key)
        except Exception as e:
            # On tente tout de même de supprimer la ligne si l'objet n'existe plus
            self.repo.delete(img)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erreur MinIO: {e}")
        self.repo.delete(img)

class ImageAccessService:
    """
    Applique la policy d'accès aux images:
    - Autorisé sans token si image liée à >=1 thème public & validé
    - Sinon: token requis et (owner ou admin)
    """
    def __init__(self, image_svc: ImageService, image_repo: ImageRepository, theme_repo: ThemeRepository):
        self.image_svc = image_svc
        self.image_repo = image_repo
        self.theme_repo = theme_repo

    def signed_get_authorized(self, image_id: str, user_ctx: UserCtx) -> dict:
        # 1) public exposable ?
        try:
            if self.theme_repo.image_is_publicly_exposable(int(image_id)):
                return self.image_svc.signed_get(image_id)
        except ValueError:
            pass  # image_id non entier -> on laissera 404 si pas trouvé

        # 2) sinon auth requise: owner ou admin
        if user_ctx is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

        user_id, is_admin = user_ctx
        img = self.image_repo.get(image_id)  # str accepté par repo.get
        if not img:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image introuvable")

        if not is_admin and getattr(img, "owner_id", None) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return self.image_svc.signed_get(image_id)
    
    def delete_authorized(self, image_id: str, user_ctx: UserCtx) -> None:
        """
        Règles:
          - Auth obligatoire.
          - Seul le propriétaire ou un admin peut supprimer.
          - Interdit si l'image est exposée publiquement (>=1 thème public & validé) -> 409.
        """
        if user_ctx is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

        user_id, is_admin = user_ctx

        img = self.image_repo.get(image_id)
        if not img:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image introuvable")

        if not is_admin and getattr(img, "owner_id", None) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        # Bloque la suppression si l'image est référencée par un thème public + validé
        try:
            if self.theme_repo.image_is_publicly_exposable(int(image_id)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Image liée à au moins un thème public validé",
                )
        except ValueError:
            # image_id non entier : on considère qu'il n'y a pas de thème référent public/validé
            pass

        # OK -> suppression via ImageService
        self.image_svc.delete(image_id)