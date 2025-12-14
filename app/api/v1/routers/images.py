# app/api/v1/routers/images.py
from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.v1.dependencies import (
    get_image_service,
    get_auth_service,
    get_access_token_from_bearer,
)
from app.features.authentication.services import AuthService
from app.features.media.schemas import ImageOut, SignedUrlOut
from app.features.media.services import ImageService

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
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    img_svc: ImageService = Depends(get_image_service),
):
    # Auth cohérente avec le reste (on peut aussi vérifier que l'image appartient à l'user ici)
    _ = auth_svc.get_current_user(access_token=access_token)
    return SignedUrlOut(**img_svc.signed_get(image_id))

# -----------------------------
# Suppression
# -----------------------------
@router.delete(
    "/{image_id}",
    summary="Supprimer une image (objet MinIO + ligne DB)",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Supprimée"}, 404: {"description": "Introuvable"}},
)
def delete_image(
    image_id: str,
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    img_svc: ImageService = Depends(get_image_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    # (Optionnel) vérifier ownership ici si nécessaire, ex. img.owner_id == user.id
    img_svc.delete(image_id)
    return None
