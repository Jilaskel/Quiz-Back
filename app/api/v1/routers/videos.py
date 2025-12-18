from fastapi import APIRouter, Depends, File, UploadFile, status
from typing import Optional

from app.api.v1.dependencies import (
    get_auth_service,
    get_access_token_from_bearer,
    get_video_service,
    get_video_access_service,
)
from app.features.authentication.services import AuthService
from app.features.media.schemas import VideoOut, SignedUrlOut
from app.features.media.services import VideoService, VideoAccessService

router = APIRouter(
    prefix="/videos",
    tags=["videos"],
    responses={404: {"description": "Not Found"}},
)

@router.post(
    "/upload",
    summary="Uploader une vidéo (Back → MinIO → SQLite)",
    description="Reçoit un fichier vidéo, le charge dans MinIO et enregistre ses métadonnées.",
    status_code=status.HTTP_201_CREATED,
    response_model=VideoOut,
)
async def upload_video(
    file: UploadFile = File(...),
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    video_svc: VideoService = Depends(get_video_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    data = await video_svc.upload(file, owner_id=user.id)
    return VideoOut(**data)

@router.get(
    "/{video_id}/signed",
    summary="Obtenir une URL GET signée (temporaire)",
    response_model=SignedUrlOut,
)
def get_signed_video_url(
    video_id: str,
    access_token: Optional[str] = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    video_access: VideoAccessService = Depends(get_video_access_service),
):
    user_ctx = None
    if access_token:
        u = auth_svc.get_current_user(access_token=access_token)
        user_ctx = (u.id, getattr(u, "admin", False))

    data = video_access.signed_get_authorized(video_id, user_ctx)
    return SignedUrlOut(**data)

@router.delete(
    "/{video_id}",
    summary="Supprimer une vidéo (objet MinIO + ligne DB)",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Supprimée"},
        401: {"description": "Non authentifié"},
        403: {"description": "Interdit"},
        404: {"description": "Introuvable"},
    },
)
def delete_video(
    video_id: str,
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    video_access: VideoAccessService = Depends(get_video_access_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    user_ctx = (user.id, getattr(user, "admin", False))

    video_access.delete_authorized(video_id, user_ctx)
    return None
