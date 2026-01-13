# === Frontend Build Stage ===
FROM node:20-slim as frontend-builder

WORKDIR /app-frontend
# Kopiujemy pliki zależności
COPY frontend/package*.json ./
RUN npm ci

# Kopiujemy kod źródłowy frontendu
COPY frontend/ ./
# Budujemy produkcyjną wersję
RUN npm run build


# === Python Build Stage ===
FROM python:3.11-slim as python-builder

WORKDIR /app-python
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# === Runtime Stage ===
FROM python:3.11-slim

# Zmienne środowiskowe
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ENV=production

WORKDIR /app

# Kopiowanie wheels z buildera i instalacja
COPY --from=python-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Kopiowanie kodu aplikacji backendowej
COPY bq_analyst/ ./bq_analyst/

# Kopiowanie zbudowanego frontendu do folderu widocznego dla FastAPI
COPY --from=frontend-builder /app-frontend/dist ./frontend/dist

# Bezpieczeństwo: non-root user
RUN adduser --disabled-password --gecos "" --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Przycisk startowy
EXPOSE 8080

# Health check dla Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Uruchomienie FastAPI przez uvicorn
CMD ["uvicorn", "bq_analyst.main:app", "--host", "0.0.0.0", "--port", "8080"]
