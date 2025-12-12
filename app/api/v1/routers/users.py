"""
➡️ But : Définir les endpoints de l’API.

C’est la couche la plus proche du web :

Réceptionne les requêtes HTTP (GET, POST, PATCH, DELETE…)

Appelle le service correspondant

Retourne les schémas de sortie (response_model)

Chaque fonction représente une route.

🔹 Avantages :

Automatiquement documentée dans Swagger :

summary, description, response_model, examples

Isolation totale du reste du code : les routes ne contiennent ni SQL ni logique métier.
"""

from fastapi import APIRouter, Depends, status
from app.api.v1.dependencies import get_user_service, pagination
from app.features.users.schemas import UserCreate, UserOut, UserUpdate
from app.features.users.services import UserService

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not Found"}},
)

@router.get(
    "",
    summary="Lister les utilisateurs",
    description="Retourne une liste paginée de tâches.",
    response_model=dict,  # {"items": list[UserOut], "total": int}
    responses={
        200: {
            "description": "Liste paginée",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1, 
                                "username": "Tholas", 
                                "created_at": "2025-01-01T10:00:00Z", 
                                "updated_at": "2025-01-01T10:00:00Z"
                            },
                            {
                                "id": 2, 
                                "username": "Martin", 
                                "created_at": "2025-02-01T10:00:00Z", 
                                "updated_at": "2025-02-01T10:00:00Z"
                            },
                        ],
                        "total": 2
                    }
                }
            },
        }
    },
)
def list_todos(p=Depends(pagination), svc: UserService = Depends(get_user_service)):
    data = svc.list(**p)
    # Contrôle fin du schéma : on convertit les items -> UserOut
    data["items"] = [UserOut.model_validate(i) for i in data["items"]]
    return data

@router.post(
    "",
    summary="Créer un utilisateur",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
)
def create_user(payload: UserCreate, svc: UserService = Depends(get_user_service)):
    return svc.create(username=payload.username, password=payload.password)

@router.get(
    "/{user_id}",
    summary="Récupérer un utilisateur",
    response_model=UserOut,
)
def get_user(user_id: int, svc: UserService = Depends(get_user_service)):
    return svc.get(user_id)

@router.patch(
    "/{user_id}",
    summary="Mettre à jour un utilisateur",
    response_model=UserOut,
)
def update_user(user_id: int, payload: UserUpdate, svc: UserService = Depends(get_user_service)):
    return svc.update(user_id, username=payload.username, password=payload.password)

@router.delete(
    "/{user_id}",
    summary="Supprimer un utilisateur",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(user_id: int, svc: UserService = Depends(get_user_service)):
    svc.delete(user_id)
    return None
