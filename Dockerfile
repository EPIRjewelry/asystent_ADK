# === Build Stage ===
FROM python:3.11-slim as builder

WORKDIR /build

# Instalacja zależności kompilacji + Node.js dla frontendu
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalacja Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Build Python wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Build Frontend
COPY frontend/package*.json /build/frontend/
WORKDIR /build/frontend
RUN npm ci

COPY frontend/ /build/frontend/
RUN (chmod +x node_modules/.bin/vite || true) \
    && (npm run build || node node_modules/vite/bin/vite.js build)


# === Runtime Stage ===
FROM python:3.11-slim

# Zmienne środowiskowe
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ENV=production

WORKDIR /app

# Kopiowanie wheels z buildera
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Kopiowanie kodu aplikacji
COPY bq_analyst/ ./bq_analyst/

# Kopiowanie zbudowanego frontendu
COPY --from=builder /build/frontend/dist ./frontend/dist

# Bezpieczeństwo: non-root user
RUN adduser --disabled-password --gecos "" --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Port
EXPOSE 8080

# Health check dla Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Uruchomienie FastAPI przez uvicorn
CMD ["uvicorn", "bq_analyst.main:app", "--host", "0.0.0.0", "--port", "8080"]
