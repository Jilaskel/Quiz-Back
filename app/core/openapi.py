"""
➡️ But : Personnaliser la documentation Swagger/OpenAPI.

custom_openapi(app) modifie le schéma généré par FastAPI pour :

ajouter un titre, une description détaillée,

inclure un contact, une licence,

centraliser la personnalisation du Swagger.

🔹 Avantages :

La doc est toujours complète et cohérente.

Tu peux y ajouter des conventions d’API (pagination, formats, etc.).
"""

from fastapi.openapi.utils import get_openapi

def custom_openapi(app):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=(
            "API de démonstration FastAPI + SQLite.\n\n"
            "### Conventions\n"
            "- Toutes les heures sont en UTC.\n"
            "- Pagination: query params `page` & `size`.\n"
        ),
        routes=app.routes,
    )
    # openapi_schema["info"]["contact"] = {"name": "API team", "email": "api@example.com"}
    # openapi_schema["info"]["license"] = {"name": "MIT"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema
