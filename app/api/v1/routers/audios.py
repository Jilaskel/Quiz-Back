from fastapi import APIRouter, Depends, File, UploadFile, status
from typing import Optional

from app.api.v1.dependencies import (
    get_auth_service,
    get_access_token_from_bearer,
    get_audio_service,
    get_audio_access_service,
)
from app.features.authentication.services import AuthService
from app.features.media.schemas import AudioOut, SignedUrlOut
from app.features.media.services import AudioService, AudioAccessService

router = APIRouter(
    prefix="/audios",
    tags=["audios"],
    responses={404: {"description": "Not Found"}},
)

@router.post(
    "/upload",
    summary="Uploader un audio (Back → MinIO → SQLite)",
    description="Reçoit un fichier audio, le charge dans MinIO et enregistre ses métadonnées.",
    status_code=status.HTTP_201_CREATED,
    response_model=AudioOut,
)
async def upload_audio(
    file: UploadFile = File(...),
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    audio_svc: AudioService = Depends(get_audio_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    data = await audio_svc.upload(file, owner_id=user.id)
    return AudioOut(**data)

@router.get(
    "/{audio_id}/signed",
    summary="Obtenir une URL GET signée (temporaire)",
    response_model=SignedUrlOut,
)
def get_signed_audio_url(
    audio_id: str,
    access_token: Optional[str] = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    audio_access: AudioAccessService = Depends(get_audio_access_service),
):
    user_ctx = None
    if access_token:
        u = auth_svc.get_current_user(access_token=access_token)
        user_ctx = (u.id, getattr(u, "admin", False))

    data = audio_access.signed_get_authorized(audio_id, user_ctx)
    return SignedUrlOut(**data)

@router.delete(
    "/{audio_id}",
    summary="Supprimer un audio (objet MinIO + ligne DB)",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Supprimé"},
        401: {"description": "Non authentifié"},
        403: {"description": "Interdit"},
        404: {"description": "Introuvable"},
    },
)
def delete_audio(
    audio_id: str,
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    audio_access: AudioAccessService = Depends(get_audio_access_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    user_ctx = (user.id, getattr(user, "admin", False))

    audio_access.delete_authorized(audio_id, user_ctx)
    return None
