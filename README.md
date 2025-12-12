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

## Access Documentation

- Swagger UI : http://127.0.0.1:8000/docs
- ReDoc : http://127.0.0.1:8000/redoc
- OpenAPI JSON : http://127.0.0.1:8000/openapi.json