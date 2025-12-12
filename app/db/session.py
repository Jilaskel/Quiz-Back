"""
➡️ But : Configurer la base SQLite et gérer les sessions de base de données.

engine : connexion à la base SQLite (sqlite:///app.db).

init_db() : crée les tables à partir des modèles SQLModel.

get_session() : dépendance FastAPI qui ouvre une session, la fournit aux routes, puis la ferme proprement.

🔹 Avantages :

Un seul endroit pour gérer les connexions DB.

Réutilisable par injection (Depends(get_session)).
"""

from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

DATABASE_URL = f"sqlite:///{settings.SQLITE_PATH}"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
