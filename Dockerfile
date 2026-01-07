# Używamy lekkiego Pythona
FROM python:3.11-slim

# Ustawienia
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Instalacja zależności
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn fastapi

# Kopiowanie kodu
COPY . .

# Uruchomienie serwera (port 8080 jest wymagany przez Cloud Run)
CMD ["uvicorn", "bq_analyst.main:app", "--host", "0.0.0.0", "--port", "8080"]