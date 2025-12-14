# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Déps système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copie du projet (pyproject.toml inclus)
COPY . /app

# Installe ton package via PEP 517 (pyproject)
# Si tu n'as pas de build-backend, pip install -e . fonctionne aussi.
RUN pip install --no-cache-dir .

EXPOSE 8080

# Lance uvicorn (adapter module si besoin)
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8080"]
