"""
Centralna konfiguracja aplikacji dla Cloud Run.
Wszystkie ustawienia ładowane z ENV (bez plików .env).
Uwierzytelnianie przez IAM (Service Account) w Google Cloud.
"""
import os


class Settings:
    """Ustawienia aplikacji ładowane z zmiennych środowiskowych Cloud Run."""
    
    # === Google Cloud (z ENV Cloud Run) ===
    PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "epir-adk-agent-v2-48a86e6f")
    LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    
    # === Model Configuration ===
    MODEL_NAME: str = os.getenv("MODEL_NAME", "publishers/google/models/gemini-3-flash-preview")
    
    # === MCP (opcjonalne) ===
    MCP_SERVER_NAME: str = os.getenv(
        "MCP_SERVER_NAME",
        "projects/epir-adk-agent-v2-48a86e6f/locations/global/mcpServers/google-bigquery.googleapis.com-mcp"
    )
    
    # === Agent Configuration ===
    RECURSION_LIMIT: int = int(os.getenv("AGENT_RECURSION_LIMIT", "15"))
    TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.0"))
    
    # === Application ===
    PORT: int = int(os.getenv("PORT", "8080"))
    ENV: str = os.getenv("ENV", "production")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# Singleton ustawień
settings = Settings()
