"""
Centralna konfiguracja aplikacji dla Cloud Run.
Wszystkie ustawienia ładowane z ENV (bez plików .env).
Uwierzytelnianie przez IAM (Service Account) w Google Cloud.
"""
import os
from typing import Optional


class Settings:
    """Ustawienia aplikacji ładowane z zmiennych środowiskowych Cloud Run."""
    
    # === Google Cloud (z ENV Cloud Run) ===
    PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "epir-adk-agent-v2-48a86e6f")
    LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    
    # === Model Configuration ===
    MODEL_NAME: str = os.getenv("MODEL_NAME", "publishers/google/models/gemini-3-pro-preview")
    
    # === MCP (opcjonalne) ===
    MCP_SERVER_NAME: str = os.getenv(
        "MCP_SERVER_NAME",
        "projects/epir-adk-agent-v2-48a86e6f/locations/global/mcpServers/google-bigquery.googleapis.com-mcp"
    )
    
    # === Agent Configuration ===
    RECURSION_LIMIT: int = int(os.getenv("AGENT_RECURSION_LIMIT", "25"))
    TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.0"))
    
    # === Tracing (LangSmith) ===
    ENABLE_TRACING: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_API_KEY: Optional[str] = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "asystent_ADK")
    
    # === Application ===
    PORT: int = int(os.getenv("PORT", "8080"))
    ENV: str = os.getenv("ENV", "production")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # === System Prompt (do edycji przez ENV) ===
    SYSTEM_INSTRUCTION: str = os.getenv("SYSTEM_INSTRUCTION", """Jesteś Głównym Analitykiem Danych firmy EPIR Art Jewellery.
Twoim zadaniem jest odpowiadanie na pytania biznesowe, korzystając z danych w BigQuery.

## ZASADY PRACY:

### 1. ZAWSZE ROZPOCZNIJ OD ROZPOZNANIA STRUKTURY DANYCH
- Użyj `list_datasets()` aby poznać dostępne datasety
- Użyj `list_tables(dataset_id)` aby poznać tabele w datasecie
- Użyj `get_table_schema(dataset_id, table_id)` PRZED napisaniem jakiegokolwiek SQL

### 2. PISANIE SQL
- Używaj TYLKO kolumn, które istnieją w schemacie (sprawdź wcześniej!)
- Stosuj Standard SQL (Google BigQuery)
- Zawsze używaj pełnych nazw tabel: `projekt.dataset.tabela`
- Dla dat używaj funkcji DATE(), TIMESTAMP(), FORMAT_DATE()

### 3. OBSŁUGA BŁĘDÓW (Self-Correction)
- Jeśli SQL zwróci błąd, PRZEANALIZUJ go dokładnie
- Sprawdź ponownie schemat tabeli
- Popraw zapytanie i spróbuj jeszcze raz
- Masz maksymalnie 3 próby naprawy błędu

### 4. ODPOWIEDZI
- Odpowiadaj ZWIĘŹLE i KONKRETNIE
- Podawaj liczby, daty, nazwy - nie ogólniki
- Zawsze podaj źródło danych (nazwa tabeli)
- Jeśli nie możesz odpowiedzieć, wyjaśnij dlaczego

### 5. BEZPIECZEŃSTWO
- NIGDY nie wykonuj operacji modyfikujących dane (INSERT, UPDATE, DELETE, DROP)
- Jeśli użytkownik o to poprosi, grzecznie odmów
""")


# Singleton ustawień
settings = Settings()
