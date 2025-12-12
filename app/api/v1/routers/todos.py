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
from app.api.v1.dependencies import get_todo_service, pagination
from app.domain.schemas import TodoCreate, TodoUpdate, TodoOut
from app.domain.services import TodoService

router = APIRouter(
    prefix="/todos",
    tags=["todos"],
    responses={404: {"description": "Not Found"}},
)

@router.get(
    "",
    summary="Lister les todos",
    description="Retourne une liste paginée de tâches.",
    response_model=dict,  # {"items": list[TodoOut], "total": int}
    responses={
        200: {
            "description": "Liste paginée",
            "content": {
                "application/json": {
                    "example": {"items": [{"id": 1, "title": "Acheter du lait", "done": False,
                                           "created_at": "2025-01-01T10:00:00Z", "updated_at": None}],
                                "total": 1}
                }
            },
        }
    },
)
def list_todos(p=Depends(pagination), svc: TodoService = Depends(get_todo_service)):
    data = svc.list(**p)
    # Contrôle fin du schéma : on convertit les items -> TodoOut
    data["items"] = [TodoOut.model_validate(i) for i in data["items"]]
    return data

@router.post(
    "",
    summary="Créer un todo",
    status_code=status.HTTP_201_CREATED,
    response_model=TodoOut,
)
def create_todo(payload: TodoCreate, svc: TodoService = Depends(get_todo_service)):
    return svc.create(title=payload.title)

@router.get(
    "/{todo_id}",
    summary="Récupérer un todo",
    response_model=TodoOut,
)
def get_todo(todo_id: int, svc: TodoService = Depends(get_todo_service)):
    return svc.get(todo_id)

@router.patch(
    "/{todo_id}",
    summary="Mettre à jour un todo",
    response_model=TodoOut,
)
def update_todo(todo_id: int, payload: TodoUpdate, svc: TodoService = Depends(get_todo_service)):
    return svc.update(todo_id, title=payload.title, done=payload.done)

@router.delete(
    "/{todo_id}",
    summary="Supprimer un todo",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_todo(todo_id: int, svc: TodoService = Depends(get_todo_service)):
    svc.delete(todo_id)
    return None
