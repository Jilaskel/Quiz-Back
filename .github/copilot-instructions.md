# Copilot Instructions for Quiz-Back

## Project Overview

**Quiz-Back** is a FastAPI backend for a quiz application with multi-player game support. It uses SQLModel (SQLAlchemy 2.x + Pydantic v2) for data access, MinIO for media storage (images, audios, videos), and JWT-based authentication.

**Key Tech Stack:**
- FastAPI (≥0.124.2), Uvicorn, SQLModel
- SQLite (dev) / Postgres-compatible
- MinIO for S3-compatible media storage
- JWT authentication with refresh tokens (cookies)
- Docker Compose orchestration

## Layered Architecture

All code flows through this vertical stack:

```
Client → API Routers → Services → Repositories → Models → Database/MinIO
```

### 1. **API Layer** (`app/api/v1/routers/`)
- HTTP endpoints grouped by domain: `games.py`, `users.py`, `authentication.py`, `images.py`, `audios.py`, `videos.py`, `themes.py`
- Use `APIRouter` with prefix (e.g., `prefix="/games"`)
- Dependency injection via `app/api/v1/dependencies.py` for services, auth, and session
- Return Pydantic schemas (from `app/features/*/schemas.py`)
- Validate auth with `get_access_token_from_bearer()` dependency

**Example pattern:**
```python
@router.get("/games/{game_id}", response_model=GameStateOut)
def get_game(game_id: int, service: GameService = Depends(get_game_service)):
    return service.get_by_id(game_id)
```

### 2. **Feature Services** (`app/features/{domain}/services.py`)
- Business logic layer: orchestrates repositories, applies rules, raises `HTTPException` for errors
- One service per feature (UserService, GameService, GameService, etc.)
- Never write SQL directly; delegate to repositories
- Raise custom errors: `HTTPException`, `PermissionError`, `ConflictError`

**Example:**
```python
class GameService:
    def __init__(self, repo: GameRepository):
        self.repo = repo
    def create(self, data: GameCreateIn) -> Game:
        # validate, then call repo
        if self.repo.get(id): raise HTTPException(409, "Already exists")
        return self.repo.create(...)
```

### 3. **Data Models** (`app/db/models/`)
- SQLModel classes inheriting from `BaseModelDB` (in `app/db/models/base.py`)
- Each model = one table; include `table=True` parameter
- Use `Field()` for column options (index, unique, foreign_key, etc.)
- Use `Relationship()` for ORM relations (e.g., User → Images)

**Key models:** User, Game, Player, Round, Grid, Theme, Question, Joker, Bonus, Image, Audio, Video

### 4. **Repositories** (`app/db/repositories/`)
- Data access layer: `list()`, `get()`, `create()`, `update()`, `delete()` operations
- Inherit from generic `BaseRepository` for common patterns
- All database queries here; services call repos
- Return model instances or lists

## Critical Developer Workflows

### Local Development
```bash
# Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -e .

# Run server (auto-reload)
uvicorn app.main:app --reload
# → http://localhost:8000/docs (Swagger UI)
```

### Database Initialization
```bash
# Populate default data (themes, jokers, bonuses, etc.)
python scripts/seed.py

# In Docker:
docker compose exec api python scripts/seed.py
```

### Docker Development
```bash
# Build & start all services (API + MinIO)
docker compose up --build

# Access:
# - API Swagger: http://localhost:8080/docs
# - MinIO Console: http://localhost:9001 (minioadmin:minioadmin)

# Full reset (purge all data)
docker compose down -v
```

### Configuration
- All settings in `app/core/config.py` via Pydantic BaseSettings
- Environment variables from `.env` override defaults
- Critical vars: `JWT_SECRET_KEY`, `S3_*` (MinIO), `DATABASE_URL`
- In dev: defaults work (JWT secret insecure, MinIO local, SQLite)

## Code Patterns & Conventions

### Schema Pattern (Request/Response)
- Input schemas: `*In` suffix (e.g., `GameCreateIn`) — Pydantic models
- Output schemas: `*Out` suffix (e.g., `GameStateOut`) — include only needed fields
- Join schemas for relations: `GameWithPlayersOut` includes nested Player objects
- Separate public views (`*PublicOut`) to exclude sensitive data

### Error Handling
- Use `HTTPException(status_code=..., detail="...")` from FastAPI
- Custom errors raised by services: `PermissionError`, `ConflictError`
- Routers must catch and convert to HTTP responses

### Media Uploads/Downloads (MinIO)
- Images, audios, videos stored in S3-compatible MinIO
- Models have image_id/audio_id foreign keys to Image/Audio models
- Service layer calls `app/utils/s3.py` for upload/download and pre-signed URLs
- Max file size: `MAX_UPLOAD_MB` (default 10)

### Authentication
- JWT tokens generated in `app/security/tokens.py`
- Access token in Authorization header (Bearer)
- Refresh token in HTTP-only cookie (refresh_token)
- Dependency `get_access_token_from_bearer()` extracts & validates in routes
- Password hashed with argon2 (`app/security/password.py`)

### Game Mechanics (Domain-Specific)
- Games contain Players (tracks score, multiplier)
- Rounds track questions answered in a grid
- Grids are 2D arrays of Question IDs (allowed sizes: 4×5 to 10×10)
- Jokers/Bonuses are one-time power-ups used per game
- Questions marked by Category and Theme
- Hard-coded general knowledge themes: IDs 9–12 (configurable in `GENERAL_THEME_IDS`)

## Cross-Component Communication Patterns

### Dependency Injection (FastAPI `Depends`)
- Session injection: `session: Session = Depends(get_session)`
- Service injection: `service: GameService = Depends(get_game_service)`
- All defined in `app/api/v1/dependencies.py`
- Services instantiated per-request with fresh session

### Repository Access
- Always pass session to repo constructor: `repo = GameRepository(session)`
- Never use global session or engine; rely on DI

### Error Flow
```
Router endpoint → calls Service → Service validates & calls Repo
                                    ↓ (on error)
                            raises HTTPException
                                    ↓
                        Router catches & returns 400/404/409
```

## File Organization Quick Reference

| Purpose | Path |
|---------|------|
| Main app & CORS | [app/main.py](app/main.py) |
| Environment config | [app/core/config.py](app/core/config.py) |
| JWT/password utilities | [app/security/tokens.py](app/security/tokens.py), [app/security/password.py](app/security/password.py) |
| API endpoints | [app/api/v1/routers/](app/api/v1/routers/) |
| Service logic | [app/features/{domain}/services.py](app/features/) |
| Request/response schemas | [app/features/{domain}/schemas.py](app/features/) |
| ORM models | [app/db/models/](app/db/models/) |
| Data access | [app/db/repositories/](app/db/repositories/) |
| Database session | [app/db/session.py](app/db/session.py) |
| MinIO/S3 utilities | [app/utils/s3.py](app/utils/s3.py) |
| Seed data (YAML) | [app/db/seed_data.yaml](app/db/seed_data.yaml) |
| Seed script | [scripts/seed.py](scripts/seed.py) |

## When Adding Features

1. **New Entity?** Create model in `app/db/models/{domain}.py`, add to session init
2. **New Endpoint?** Add router in `app/api/v1/routers/{domain}.py`, add schemas to `app/features/{domain}/schemas.py`
3. **New Business Logic?** Implement in `app/features/{domain}/services.py`
4. **Data Access?** Implement repo in `app/db/repositories/{domain}.py`
5. **Media Upload?** Use `app/utils/s3.py` utilities; add Image/Audio/Video models
6. **Auth Required?** Inject `token` via `get_access_token_from_bearer()` dependency, extract user from token service

---

*Last updated: 2026-01-23*
