from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.v1.dependencies import (
    get_access_token_from_bearer,
    get_auth_service,
    get_comment_service,
)
from app.features.authentication.services import AuthService
from app.features.comments.schemas import (
    ThemeCommentCreateIn,
    ThemeCommentUpdateIn,
    ThemeCommentOut,
)
from app.features.comments.services import CommentService, PermissionError, ConflictError

router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    responses={404: {"description": "Not Found"}},
)


@router.post(
    "",
    summary="Ajouter un commentaire sur un thème joué",
    response_model=ThemeCommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    payload: ThemeCommentCreateIn,
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    svc: CommentService = Depends(get_comment_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    try:
        return svc.create(payload, user_id=user.id, is_admin=getattr(user, "admin", False))
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{comment_id}",
    summary="Mettre à jour un commentaire",
    response_model=ThemeCommentOut,
)
def update_comment(
    payload: ThemeCommentUpdateIn,
    comment_id: int = Path(..., ge=1),
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    svc: CommentService = Depends(get_comment_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    try:
        return svc.update(comment_id, payload, user_id=user.id, is_admin=getattr(user, "admin", False))
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{comment_id}",
    summary="Supprimer un commentaire",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_comment(
    comment_id: int = Path(..., ge=1),
    access_token: str = Depends(get_access_token_from_bearer),
    auth_svc: AuthService = Depends(get_auth_service),
    svc: CommentService = Depends(get_comment_service),
):
    user = auth_svc.get_current_user(access_token=access_token)
    try:
        svc.delete(comment_id, user_id=user.id, is_admin=getattr(user, "admin", False))
        return None
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
