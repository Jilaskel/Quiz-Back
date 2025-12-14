# Quiz Backend

A simple FastAPI backend for a quiz application.

## Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

3. Install dependencies:
   ```
   pip install -e .
   ```

## Running the Server

```
uvicorn app.main:app --reload
```

The server will start on `http://127.0.0.1:8000` or `http://localhost:8000`

## Populate Database

```
python .\scripts\seed.py
```

## Access Documentation

- Swagger UI : http://127.0.0.1:8000/docs
- ReDoc : http://127.0.0.1:8000/redoc
- OpenAPI JSON : http://127.0.0.1:8000/openapi.json

## Docker Launch (API server + File management MinIO for images and audio)

Download and install : Dockerhttps://www.docker.com/products/docker-desktop/

Open Docker Desktop

Run docker build (no python venv needed)
```
docker compose up --build
```

### Comandes Docker

Run docker build (no python venv needed)
```
docker compose up --build
```

Télécharger (ou mettre à jour) les images nécessaires à ton projet.
```
docker compose pull
```

Reset complet de l’environnement et des données persistantes.
```
docker compose down -v
```

### Access UI by Docker

- Swagger UI : http://127.0.0.1:8000/docs
- MinIO UI : http://localhost:9001/login (id en local minioadmin:minioadmin)