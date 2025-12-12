"""
➡️ But : Centraliser les dépendances réutilisables des routes.

Exemples :

get_todo_service() : crée un TodoService à partir d’une session DB.

pagination() : paramètres communs page et size.

🔹 Avantages :

Routes plus propres (pas de code dupliqué).

Facile à injecter dans plusieurs endpoints (Depends()).
"""

from fastapi import Depends, Query
from sqlmodel import Session
from app.db.session import get_session
from app.domain.repositories import TodoRepository
from app.domain.services import TodoService

def get_todo_service(session: Session = Depends(get_session)):
    return TodoService(TodoRepository(session))

def pagination(
    page: int = Query(1, ge=1, description="Numéro de page", examples=[1]),
    size: int = Query(20, ge=1, le=100, description="Taille de page", examples=[20]),
):
    offset = (page - 1) * size
    return {"offset": offset, "limit": size}
