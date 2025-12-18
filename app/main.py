"""
➡️ But : assembler toutes les pièces du puzzle.

Crée l’instance FastAPI (app).

Configure :

CORS (autorisations de qui peut appeler ces API)

titre, version, tags

schéma OpenAPI personnalisé

Inclut les routers (ex : /api/v1/todos).

Initialise la base SQLite au démarrage (@app.on_event("startup")).

🔹 Avantages :

Centralise la configuration du serveur HTTP.

Point unique d’exécution : uvicorn app.main:app --reload.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.openapi import custom_openapi
from app.db.session import init_db

from app.api.v1.routers import users, authentication, images, themes, audios, videos

import uvicorn

app = FastAPI(
    title=settings.APP_NAME,
    version="0.0.1",
    # contact={"name": "API team", "email": "api@example.com"},
    # license_info={"name": "MIT"},
    openapi_tags=[
        # {"name": "users", "description": "Gestion de Utilisateurs"},
        {"name": "auth", "description": "Opérations liées à l'authentification"},
        {"name": "images", "description": "Opérations liées au stockage des images"},
        {"name": "audios", "description": "Opérations liées au stockage des audios"},
        {"name": "videos", "description": "Opérations liées au stockage des videos"},
        {"name": "themes", "description": "Opérations liées aux thèmes"},
    ],
)

# CORS (ajustez selon vos besoins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Routers
# app.include_router(users.router, prefix="/api/v1")
app.include_router(authentication.router, prefix="/api/v1")
app.include_router(images.router, prefix="/api/v1")
app.include_router(themes.router, prefix="/api/v1")
app.include_router(audios.router, prefix="/api/v1")
app.include_router(videos.router, prefix="/api/v1")

# Génération du schéma OpenAPI custom (facultatif, mais propre)
app.openapi = lambda: custom_openapi(app)

# Démarrage
@app.on_event("startup")
def on_startup():
    init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080, reload=(settings.ENV == "dev")) # http://localhost:8080