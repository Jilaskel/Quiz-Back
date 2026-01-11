# Architecture — Quiz-Back

Résumé concis destiné à servir de contexte pour toutes modifications futures.

## Vue d'ensemble
- Application Python (FastAPI probable) organisée en couche API / features / DB / utils.
- Contenu principal : [app/](app/)
- Déploiement : `Dockerfile` + `docker-compose.yaml`.

## Composants principaux
- API & routeurs : [app/main.py](app/main.py), [app/api/v1/routers/games.py](app/api/v1/routers/games.py), [app/api/v1/routers/users.py](app/api/v1/routers/users.py)
- Noyau & config : [app/core/config.py](app/core/config.py), [app/core/openapi.py](app/core/openapi.py)
- Couche métier (features) : [app/features/](app/features/) — modules `authentication`, `games`, `media`, `questions`, `themes`, `users` (chaque module expose `schemas.py` et `services.py`).
- Modèles & accès DB : [app/db/models/](app/db/models/), [app/db/repositories/](app/db/repositories/), session : [app/db/session.py](app/db/session.py)
- Sécurité : [app/security/tokens.py](app/security/tokens.py), [app/security/password.py](app/security/password.py)
- Stockage média : MinIO (dossier `minio-data/`, script `scripts/minio-init.sh`)

## Flux de données (simplifié)
- Client → API routers (`app/api/v1/routers/*`) → services (`app/features/*/services.py`) → repositories (`app/db/repositories/*`) → modèles (`app/db/models/*`) → stockage (MinIO / DB)

## Déploiement & exécution locale
- Docker compose orchestré par `docker-compose.yaml`.
- Fichiers pertinents : `Dockerfile`, `docker-compose.yaml`, `.env`.

## Diagramme (Mermaid)
```mermaid
flowchart LR
  Client -->|HTTP| API[API Routers]
  API --> Services[Features Services]
  Services --> Repos[DB Repositories]
  Repos --> Models[DB Models]
  Services -->|upload/download| MinIO[MinIO (media)]
  subgraph Deployment
    Docker[Docker Compose]
  end
  Docker --> API
  Docker --> MinIO
```

## Où chercher pour une modification donnée
- Endpoints : [app/api/v1/routers](app/api/v1/routers)
- Logique métier : [app/features/](app/features/)
- Modèles / migrations : [app/db/models/](app/db/models/)
- Repositories (accès DB) : [app/db/repositories/](app/db/repositories/)

## Contexte à fournir pour futures demandes
Pour toute demande, inclure au minimum :
- Description courte du changement attendu (ex : nouvelle route, modifier modèle, corriger logique)
- Fichiers ciblés ou endpoints concernés (ex : `app/api/v1/routers/games.py`)
- Comportement attendu (request/response exemples) et priorité (breaking/non-breaking)
- Si pertinent : données de test ou fixtures, tokens d'auth fictifs, et exemples d'images/audios si changement média

---
Fichier créé automatiquement par l'assistant pour servir de contexte. Dis-moi si tu veux que j'ajoute un diagramme plus détaillé (séquence, composants) ou une version en `docs/`.
