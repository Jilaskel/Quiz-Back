# Architecture du projet – Backend FastAPI

## Contexte technique
- **Framework :** Python + FastAPI
- **API :** REST (routes versionnées en `/api/v1`)
- **Stockage fichiers :** MinIO (S3-compatible)
- **Déploiement :** Docker (+ `docker-compose`)
- **Données :**
    - Modèles + accès DB centralisés dans `app/db/` (modèles + repositories + session)
    - Seed via `seed.py` + `seed_data.yaml

## Architecture : API versionnée + domaines métier (features) + couche DB
```
/ (racine)
├─ docker-compose.yaml         # Déploiement FastAPI + MinIO (et DB si présente)
├─ Dockerfile                  # Build image backend
├─ pyproject.toml              # Dépendances + tooling
├─ .env                        # Variables d’env (non commit si sensible)
├─ README.md
│
├─ scripts/
│  ├─ minio-init.sh            # Init buckets/policies MinIO (bootstrap)
│  └─ seed.py                  # Seed DB (souvent via seed_data.yaml)
│
└─ app/
   ├─ main.py                  # Création de l’app FastAPI + include_router
   │
   ├─ api/
   │  └─ v1/
   │     ├─ dependencies.py    # Dépendances FastAPI (auth, DB session, etc.)
   │     └─ routers/           # Couche HTTP (endpoints)
   │        ├─ authentication.py
   │        ├─ users.py
   │        ├─ themes.py
   │        └─ images.py
   │
   ├─ core/                    # Config globale & aspects transverses
   │  ├─ config.py             # Settings (env, secrets, URLs, etc.)
   │  └─ openapi.py            # Personnalisation OpenAPI (tags, docs, etc.)
   │
   ├─ db/                      # Couche persistance (DB)
   │  ├─ session.py            # Session/engine DB + gestion transactions
   │  ├─ seed.py               # Logique seed (si utilisée côté app)
   │  ├─ seed_data.yaml        # Données seed
   │  ├─ models/               # Modèles ORM (entités)
   │  │  ├─ base.py
   │  │  ├─ users.py
   │  │  ├─ themes.py
   │  │  ├─ images.py
   │  │  ├─ categories.py
   │  │  ├─ colors.py
   │  │  └─ refresh_tokens.py
   │  └─ repositories/         # Accès DB (CRUD/queries) par domaine
   │     ├─ base.py
   │     ├─ users.py
   │     ├─ themes.py
   │     ├─ images.py
   │     └─ refresh_tokens.py
   │
   ├─ features/                # Logique métier par domaine
   │  ├─ authentication/
   │  ├─ users/
   │  ├─ themes/
   │  │  ├─ schemas.py         # Contrats API (Pydantic) + validation
   │  │  └─ services.py        # Use-cases métier (orchestration repo + rules)
   │  └─ media/                # Domaine fichiers/médias (MinIO)
   │
   ├─ security/                # AuthN/AuthZ & crypto
   │  ├─ password.py           # Hash/verify mots de passe
   │  └─ tokens.py             # JWT / refresh tokens / scopes
   │
   └─ utils/                   # Utilitaires techniques transverses
      ├─ s3.py                 # Client MinIO/S3 (upload/download, presigned, etc.)
      └─ images.py             # Helpers image (naming, validation, conversions…)
```

## Rôles et responsabilités par couche

`app/api/v1/routers/` (Couche HTTP)
- Déclare les endpoints FastAPI (routes, query/path params, status codes)
- Convertit HTTP → appels métier (services)
- Gère uniquement :
    - validation d’entrée via Pydantic (souvent `features/*/schemas.py`)
    - dépendances FastAPI (auth, DB session, current user)
    - mapping erreurs métier → HTTP (ex: 404, 409, 401)
- ❌ Pas de logique métier complexe ici
- ❌ Pas d’accès DB direct ici (pas de requêtes ORM directes)

`app/features/<feature>/` (Cœur métier)
- Contient la logique fonctionnelle par domaine (users, themes, authentication, media…)
- `schemas.py`
    - modèles Pydantic d’entrée/sortie
    - contraintes de validation (types, regex, min/max, etc.)
- `services.py`
    - cas d’usage (ex: créer un thème, uploader une image, rafraîchir un token)
    - orchestration : repositories + utils + security + règles métier
    - point central pour tests unitaires métier

`app/db/models/` (Modèles de données)
- Décrit les entités persistées (ORM)
- Doit rester “donnée-centric” (relations, colonnes, contraintes)
- ❌ Pas de règles métier applicatives

`app/db/repositories/` (Accès DB)
- Encapsule les opérations DB (CRUD, queries, filtres, pagination)
- Retourne des entités / DTO internes
- Ne connaît pas HTTP
- ❌ Pas de dépendance vers `routers/`

`app/db/session.py`
- Gestion du cycle de vie de la session DB (connexion, commit/rollback)
- Utilisé via dépendances FastAPI (`dependencies.py`)

`app/security/`
- Tout ce qui touche à l’authentification/autorisation :
    - hashing de mots de passe
    - JWT / refresh tokens / vérification / expiration
- Doit être agnostique du métier (réutilisable)

`app/utils/`
- Helpers techniques transverses
- `s3.py` centralise l’intégration MinIO (S3-compatible)
- `images.py` centralise les helpers liés aux fichiers image
- ❌ Pas de règles métier “users/themes” ici

`scripts/` + Docker
- `docker-compose.yaml` orchestre FastAPI + MinIO (et autres services)
- `scripts/minio-init.sh` bootstrap MinIO (buckets, policies, etc.)
- `seed.py` + `seed_data.yaml` pour initialiser la DB avec des données de dev

## Règles simples : où modifier / où ajouter

### Ajouter un nouvel endpoint (nouvelle route API)

1. Créer/modifier un fichier dans : `app/api/v1/routers/<domaine>.py`
2. Appeler un service dans : `app/features/<domaine>/services.py`
3. Définir les schémas Pydantic dans : `app/features/<domaine>/schemas.py`

✅ Le router orchestre HTTP, le service orchestre le métier.

### Ajouter une nouvelle feature métier (nouveau domaine)

Créer un dossier :
```
app/features/<nouvelle_feature>/
├─ schemas.py
└─ services.py
```
Puis :
- Ajouter un router : `app/api/v1/routers/<nouvelle_feature>.py`
- Ajouter (si nécessaire) :
    - modèle DB dans `app/db/models/`
    - repository dans `app/db/repositories/`

### Ajouter / modifier une opération DB
- Modèle : `app/db/models/<domaine>.py`
- Accès DB : `app/db/repositories/<domaine>.py`
- Usage métier : `app/features/<domaine>/services.py`

❌ Un router ne doit pas importer directement un modèle ORM pour requêter.

### Gérer le stockage de fichiers (MinIO)
- Toute interaction MinIO (upload/download/presigned URLs) doit passer par :
    - `app/utils/s3.py`
- La logique métier “quoi stocker, quand, avec quelles permissions, lien avec DB” vit dans :
    - `app/features/media/` (ou la feature concernée, ex: `themes/services.py` si c’est lié aux thèmes par exemple)

## Configuration & variables d’environnement
- Déclarer/centraliser dans : `app/core/config.py`
- Utiliser .env en local (ne pas committer si sensible)
- Les valeurs MinIO (endpoint, keys, bucket…) doivent être des settings, pas hardcodées

## Flux logique recommandé (pour guider contributeurs et LLM)
```
HTTP Request
  → Router (app/api/v1/routers/*)
     → Service métier (app/features/<feature>/services.py)
        → Repositories (app/db/repositories/*)
           → Models + Session (app/db/models/*, app/db/session.py)

+ Pour les fichiers :
Service métier → utils/s3.py (MinIO)
```

## Convention d’import (conseillée)
- Les routers importent uniquement :
    - `features/<feature>/schemas.py`
    - `features/<feature>/services.py`
    - `api/v1/dependencies.py`
- Les services importent :
    - repositories + utils + security + config
- Les repositories importent :
- `db/session.py` + `db/models/*`

## Version courte pour prompt LLM
```
Tu interviens sur un backend Python FastAPI.

STACK TECHNIQUE
- FastAPI
- API versionnée en /api/v1
- Stockage fichiers : MinIO (S3)
- Déploiement : Docker + docker-compose

ARCHITECTURE À RESPECTER (OBLIGATOIRE)
- Les routes HTTP vivent dans app/api/v1/routers
- La logique métier vit dans app/features/<feature>/services.py
- Les schémas Pydantic vivent dans app/features/<feature>/schemas.py
- L’accès DB est encapsulé dans app/db/repositories
- Les entités DB vivent dans app/db/models
- Les intégrations techniques (MinIO/S3) vivent dans app/utils (ex: utils/s3.py)
- ❌ Pas de logique métier dans les routers
- ❌ Pas d’accès DB direct dans les routers
- ✅ Toute opération métier passe par un service
- ✅ Toute opération fichier passe par utils/s3.py, orchestrée par un service

OBJECTIF
[Décris ici précisément la fonctionnalité à ajouter ou la modification à effectuer]

SORTIE ATTENDUE
- Liste des fichiers à créer ou modifier
- Contenu complet des nouveaux fichiers
- Modifications ciblées et cohérentes avec l’architecture
```