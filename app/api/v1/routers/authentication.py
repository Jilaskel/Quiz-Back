from fastapi import APIRouter, Depends, Header, Cookie, Response, status, HTTPException
from typing import Optional

from app.api.v1.dependencies import (
    get_auth_service,
    get_access_token_from_bearer,
    get_client_ip_and_ua,
)
from app.features.authentication.services import AuthService
from app.features.authentication.schemas import (
    SignUpIn,
    SignInIn,
    TokenPairOut,
    RefreshIn,
    LogoutIn,
    ChangePasswordIn,
)
from app.features.users.schemas import UserOut  # pour /me & sign-up

from app.core.config import settings

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not Found"}},
)

# -----------------------------
# Sign-up
# -----------------------------
@router.post(
    "/sign-up",
    summary="Créer un compte",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
)
def sign_up(payload: SignUpIn, svc: AuthService = Depends(get_auth_service)):
    return svc.sign_up(payload)

# -----------------------------
# Sign-in
# -----------------------------
@router.post(
    "/sign-in",
    summary="Se connecter",
    description="Retourne un couple access/refresh. Le refresh est aussi posé en cookie httpOnly.",
    response_model=TokenPairOut,
)
def sign_in(
    payload: SignInIn,
    response: Response,
    svc: AuthService = Depends(get_auth_service),
    client_ctx=Depends(get_client_ip_and_ua),
):
    pair = svc.sign_in(payload, ip=client_ctx.ip, user_agent=client_ctx.user_agent)
    # Place le refresh token en cookie httpOnly (recommandé)
    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value=pair.refresh_token,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        secure=settings.AUTH_COOKIE_SECURE,
        max_age=settings.AUTH_COOKIE_MAX_AGE,
        path=settings.AUTH_COOKIE_PATH,
    )
    return pair

# -----------------------------
# # Refresh (rotation)
# # -----------------------------
# @router.post(
#     "/refresh",
#     summary="Renouveler les tokens (rotation)",
#     description="Lit le refresh dans le body **ou** dans le cookie httpOnly.",
#     response_model=TokenPairOut,
# )
# def refresh(
#     payload: Optional[RefreshIn] = None,
#     refresh_cookie: Optional[str] = Cookie(default=None, alias=settings.AUTH_REFRESH_COOKIE_NAME),
#     response: Response = None,  # type: ignore[assignment]
#     svc: AuthService = Depends(get_auth_service),
#     client_ctx=Depends(get_client_ip_and_ua),
# ):
#     # Priorité payload > cookie (permet aussi d'appeler depuis un client non-navigateur)
#     refresh_token = (payload.refresh_token if payload else None) or refresh_cookie
#     if not refresh_token:
#         # On s'aligne avec le service : 401 sera renvoyé s'il est invalide, ici on renvoie 401 si absent
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

#     pair = svc.refresh(
#         RefreshIn(refresh_token=refresh_token),
#         ip=client_ctx.ip,
#         user_agent=client_ctx.user_agent,
#     )
#     # Met à jour le cookie httpOnly (rotation)
#     response.set_cookie(
#         key=settings.AUTH_REFRESH_COOKIE_NAME,
#         value=pair.refresh_token,
#         httponly=True,
#         samesite=settings.AUTH_COOKIE_SAMESITE,
#         secure=settings.AUTH_COOKIE_SECURE,
#         max_age=settings.AUTH_COOKIE_MAX_AGE,
#         path=settings.AUTH_COOKIE_PATH,
#     )
#     return pair

# -----------------------------
# Logout
# -----------------------------
@router.post(
    "/logout",
    summary="Se déconnecter (révocation du refresh)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    payload: Optional[LogoutIn] = None,
    refresh_cookie: Optional[str] = Cookie(default=None, alias=settings.AUTH_REFRESH_COOKIE_NAME),
    response: Response = None,  # type: ignore[assignment]
    svc: AuthService = Depends(get_auth_service),
):
    refresh_token = (payload.refresh_token if payload else None) or refresh_cookie
    if refresh_token:
        svc.log_out(LogoutIn(refresh_token=refresh_token))
    # Supprime le cookie côté client
    response.delete_cookie(key=settings.AUTH_REFRESH_COOKIE_NAME, path="/auth")
    return None

# -----------------------------
# Me (profil courant)
# -----------------------------
@router.get(
    "/me",
    summary="Récupérer l'utilisateur courant",
    response_model=UserOut,
    responses={
        200: {"description": "Utilisateur courant"},
        401: {"description": "Token invalide ou expiré"},
        404: {"description": "Utilisateur introuvable"},
    },
)
def me(
    access_token: str = Depends(get_access_token_from_bearer),
    svc: AuthService = Depends(get_auth_service),
):
    return svc.get_current_user(access_token=access_token)

# -----------------------------
# Changer le mot de passe
# -----------------------------
@router.post(
    "/change-password",
    summary="Changer le mot de passe",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Mot de passe changé"},
        401: {"description": "Ancien mot de passe invalide ou token invalide"},
        404: {"description": "Utilisateur introuvable"},
    },
)
def change_password(
    payload: ChangePasswordIn,
    access_token: str = Depends(get_access_token_from_bearer),
    svc: AuthService = Depends(get_auth_service),
):
    user = svc.get_current_user(access_token=access_token)
    svc.change_password(user_id=user.id, payload=payload)
    return None
