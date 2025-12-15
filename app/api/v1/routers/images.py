# app/api/v1/routers/images.py
from fastapi import APIRouter, Depends, File, UploadFile, status
from typing import Optional

from app.api.v1.dependencies import (
    get_image_service,
    get_auth_service,
    get_access_token_from_bearer,
    get_image_access_service
)
from app.features.authentication.services import AuthService
from app.features.media.schemas import ImageOut, SignedUrlOut
from app.features.media.services import ImageService, ImageAccessService

router = APIRouter(
    prefix="/images",
    tags=["images"],
    responses={404: {"description": "Not Found"}},
)

# -----------------------------
# Upload (création)
# -----------------------------
@router.post(
    "/upload",
    summary="Uploader une image (Back → MinIO → SQLite)",
    description="Reçoit un fichier, le charge dans MinIO et enregistre ses métadonnées.",
    status_code=status.HTTP_201_CREATED,
    response_model=ImageOut,
)
async def upload_image(
    file: UploadFile = File(...),
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    img_svc: ImageService = Depends(get_image_service),
):
    # Identifie l'utilisateur via le bearer (même pattern que /auth/me)
    user = auth_svc.get_current_user(access_token=access_token)
    data = await img_svc.upload(file, owner_id=user.id)
    return ImageOut(**data)

# -----------------------------
# URL signée (lecture)
# -----------------------------
@router.get(
    "/{image_id}/signed",
    summary="Obtenir une URL GET signée (temporaire)",
    response_model=SignedUrlOut,
)
def get_signed_url(
    image_id: str,
    access_token: Optional[str] = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    img_access: ImageAccessService = Depends(get_image_access_service),
):
    user_ctx = None
    if access_token:
        u = auth_svc.get_current_user(access_token=access_token)
        user_ctx = (u.id, getattr(u, "admin", False))

    data = img_access.signed_get_authorized(image_id, user_ctx)
    return SignedUrlOut(**data)

# -----------------------------
# Suppression
# -----------------------------
@router.delete(
    "/{image_id}",
    summary="Supprimer une image (objet MinIO + ligne DB)",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Supprimée"},
        401: {"description": "Non authentifié"},
        403: {"description": "Interdit"},
        404: {"description": "Introuvable"},
        409: {"description": "Image utilisée par un thème public validé"},
    },
)
def delete_image(
    image_id: str,
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    img_access: ImageAccessService = Depends(get_image_access_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    user_ctx = (user.id, getattr(user, "admin", False))

    img_access.delete_authorized(image_id, user_ctx)
    return None
