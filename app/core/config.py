"""
➡️ But : Centraliser tous les paramètres configurables (nom d’app, chemin DB, secrets, etc.)

Utilise pydantic-settings pour charger automatiquement les variables d’environnement (.env, variables système…).

Fournit un objet settings unique, que tu importes ailleurs :

from app.core.config import settings
print(settings.APP_NAME)


🔹 Avantages :

Plus propre que des constantes éparpillées dans le code.

Facilite le passage entre environnements (dev / prod / test).
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Todo API"
    ENV: str = "dev"
    SQLITE_PATH: str = "app.db"  # fichier SQLite

    model_config = {"env_file": ".env"}

settings = Settings()
