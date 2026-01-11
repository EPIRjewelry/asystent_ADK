# Używamy lekkiego Pythona
FROM python:3.11-slim

# Ustawienia
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Instalacja zależności
COPY requirements-streamlit.txt .
RUN pip install --no-cache-dir -r requirements-streamlit.txt

# Kopiowanie kodu
COPY . .

# Expose port 8080 (wymagany przez Cloud Run)
EXPOSE 8080

# Uruchomienie Streamlit na porcie 8080
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
