# FlashDash Backend Service

Python FastAPI service for orchestrating GrapheneOS flashing operations.

## Setup

1. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your paths
```

4. Run the service:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 17890
```

## Environment Variables

See `.env.example` for all required configuration.

## API Documentation

Once running, visit:
- Swagger UI: http://127.0.0.1:17890/docs
- ReDoc: http://127.0.0.1:17890/redoc

