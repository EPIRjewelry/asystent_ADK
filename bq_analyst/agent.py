import os

from google import genai
from google.genai import types
from google.adk.tools.api_registry import ApiRegistry

# --- KONFIGURACJA INFRASTRUKTURY ---
# W Cloud Run nie potrzebujemy pliku klucza - używamy tożsamości wbudowanej
CORRECT_PROJECT_ID = "epir-adk-agent-v2-48a86e6f"
# Vertex AI (GenAI) – możliwość sterowania przez zmienne środowiskowe;
# domyślnie zostawiamy pierwotny projekt i ustawiamy lokalizację na "global",
# bo model Gemini 3 Flash bywa dostępny globalnie, a nie w każdym regionie.
VERTEXAI_PROJECT_ID = os.getenv("VERTEXAI_PROJECT", CORRECT_PROJECT_ID)
VERTEXAI_LOCATION = os.getenv("VERTEXAI_LOCATION", "global")
VERTEXAI_MODEL = os.getenv("VERTEXAI_MODEL", "publishers/google/models/gemini-3-flash-preview")


# MCP BigQuery
MCP_SERVER_NAME = "projects/epir-adk-agent-v2-48a86e6f/locations/global/mcpServers/google-bigquery.googleapis.com-mcp"
api_registry = ApiRegistry(CORRECT_PROJECT_ID)
registry_tools = api_registry.get_toolset(mcp_server_name=MCP_SERVER_NAME)

# Inicjalizacja klienta Google GenAI dla Vertex AI
try:
    genai_client = genai.Client(
        vertexai=True,
        project=VERTEXAI_PROJECT_ID,
        location=VERTEXAI_LOCATION,
    )
    print(f"🔌 [SYSTEM] Połączono z Vertex AI GenAI (project={VERTEXAI_PROJECT_ID}, location={VERTEXAI_LOCATION})")
except Exception as e:
    genai_client = None
    print(f"⚠️ [SYSTEM] Błąd inicjalizacji GenAI: {e}")

# --- NARZĘDZIA (TOOLS) ---



# --- LOGIKA AGENTA ---

SYSTEM_PROMPT = """
Jesteś Starszym Analitykiem Danych w EPIR Art Jewellery. 
Twoim celem jest wyciąganie wniosków biznesowych z danych BigQuery.

**Zasady:**
1. Analizuj intencje użytkownika.
2. Używaj get_table_schema w razie wątpliwości co do struktury tabeli.
3. Pisz poprawny SQL (Standard SQL).
4. Odpowiadaj zwięźle i konkretnie.
5. Zawsze podawaj źródło danych (dataset.table).
"""

def run_agent(prompt: str) -> tuple[str, object | None]:
    """
    Uruchamia agenta analitycznego z danym zapytaniem.
    
    Args:
        prompt: Zapytanie użytkownika
    
    Returns:
        Tuple zawierający tekst odpowiedzi oraz obiekt odpowiedzi (do śledzenia procesu myślowego)
    """
    if not genai_client:
        return "Błąd: Klient GenAI nie został zainicjalizowany.", None
    
    try:
        response = genai_client.models.generate_content(
            model=VERTEXAI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=registry_tools.tools,
                temperature=0.7,
            )
        )
        
        text = response.text if response.text else str(response)
        return text, response
    
    except Exception as e:
        return f"Błąd podczas pracy agenta: {str(e)}", None
