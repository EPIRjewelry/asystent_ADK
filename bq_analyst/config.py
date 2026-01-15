"""
Centralna konfiguracja aplikacji dla Cloud Run.
Wszystkie ustawienia ładowane z ENV (bez plików .env).
Uwierzytelnianie przez IAM (Service Account) w Google Cloud.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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

    # === Checkpointer (pamięć sesji) ===
    CHECKPOINTER_BACKEND: str = os.getenv("CHECKPOINTER_BACKEND", "memory").lower()
    FIRESTORE_PROJECT: Optional[str] = os.getenv("FIRESTORE_PROJECT")
    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")
    FIRESTORE_CHECKPOINTS_COLLECTION: str = os.getenv(
        "FIRESTORE_CHECKPOINTS_COLLECTION",
        "langgraph_checkpoints",
    )
    FIRESTORE_BLOBS_COLLECTION: str = os.getenv(
        "FIRESTORE_BLOBS_COLLECTION",
        "langgraph_blobs",
    )
    FIRESTORE_WRITES_COLLECTION: str = os.getenv(
        "FIRESTORE_WRITES_COLLECTION",
        "langgraph_writes",
    )
    
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

    def validate(self) -> bool:
        """Waliduj krytyczne ustawienia przy starcie."""
        issues = []

        if self.ENABLE_TRACING:
            if not self.LANGCHAIN_API_KEY or self.LANGCHAIN_API_KEY.strip() == "":
                issues.append(
                    "❌ LANGCHAIN_TRACING_V2=true ale LANGCHAIN_API_KEY jest pusty/brak. "
                    "Tracing LangSmith NIE będzie dostępny."
                )
            else:
                logger.info(
                    "✅ LangSmith tracing ENABLED. Project: %s",
                    self.LANGCHAIN_PROJECT,
                )
        else:
            logger.info("⊘ LangSmith tracing DISABLED (LANGCHAIN_TRACING_V2=false)")

        if not self.PROJECT_ID:
            issues.append("❌ GOOGLE_CLOUD_PROJECT nie ustawiony!")

        if not self.MODEL_NAME:
            issues.append("❌ MODEL_NAME nie ustawiony!")

        if self.CHECKPOINTER_BACKEND == "firestore":
            logger.info(
                "🧠 Checkpointer: Firestore (project=%s, db=%s)",
                self.FIRESTORE_PROJECT or self.PROJECT_ID,
                self.FIRESTORE_DATABASE,
            )
        else:
            logger.info("🧠 Checkpointer: InMemory (MemorySaver)")

        for issue in issues:
            logger.warning(issue)

        logger.info(
            "⚙️  Konfiguracja: PROJECT=%s, MODEL=%s, ENV=%s",
            self.PROJECT_ID,
            self.MODEL_NAME,
            self.ENV,
        )

        return len(issues) == 0


# Singleton ustawień
settings = Settings()
settings.validate()
