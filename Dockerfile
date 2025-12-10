# Build and run from repo root. Context: .
FROM python:3.11-slim

WORKDIR /app

# Backend code and deps
COPY backend /app/backend
COPY models /app/models
COPY monitor_recommendations.py /app/backend/
# CPU-only PyTorch to keep image under Fly's 8GB limit
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /app/backend/requirements-docker.txt

# Checkpoints and data: model_service uses BASE_DIR=/app (parent of backend), so put Checkpoints and data under /app
COPY Checkpoints /app/Checkpoints
COPY data /app/data

WORKDIR /app/backend
ENV PORT=8080
EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port 8080
