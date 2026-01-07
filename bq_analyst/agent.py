import os



from google.cloud import bigquery
from google.adk.agents import Agent
# Nowe, architektoniczne importy - oddzielamy "mózg" (Planner) od "ciała" (Agent)
from google.adk.planners import BuiltInPlanner 
from google.genai import types 

# --- KONFIGURACJA INFRASTRUKTURY ---

# --- KONFIGURACJA INFRASTRUKTURY ---
# UWAGA: Poprawiony identyfikator projektu zgodnie z Twoją weryfikacją
CORRECT_PROJECT_ID = "epir-adk-agent-v2-48a86e6f"

try:
    # Wymuszamy projekt i region zgodnie z konfiguracją (us-central1)
    bq_client = bigquery.Client(project=CORRECT_PROJECT_ID, location="us-central1")
    print(f"🔌 [SYSTEM] Połączono z BigQuery. Projekt: {bq_client.project}")
except Exception as e:
    bq_client = None
    print(f"⚠️ [SYSTEM] Błąd inicjalizacji: {e}")

# --- NARZĘDZIA (TOOLS) ---

def run_sql_query(query: str) -> dict:
    """
    Executes a Standard SQL query in BigQuery and returns the results.
    WARNING: Only READ operations (SELECT) are allowed.
    """
    if not bq_client:
        return {"error": "BigQuery client not connected. Check local auth."}

    # Bezpiecznik Rzemieślnika: Blokada destrukcji
    forbidden = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "MERGE", "GRANT"]
    if any(cmd in query.upper() for cmd in forbidden):
        return {"error": "SAFETY VIOLATION: Modification commands are strictly forbidden."}
    
    try:
        # Opcjonalnie: JobConfig z dry_run=True można dodać do walidacji przed wykonaniem
        query_job = bq_client.query(query)
        # Pobieramy wyniki i konwertujemy na listę słowników
        results = [dict(row) for row in query_job]
        
        # Limit bezpieczeństwa dla kontekstu modelu (żeby nie zapchać tokenów)
        return {
            "status": "success", 
            "rows_count": len(results), 
            "data": results[:50], 
            "note": "Output limited to 50 rows for context safety."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_table_schema(dataset_id: str, table_id: str) -> dict:
    """Retrieves schema for a specific table to understand column names and types."""
    if not bq_client:
        return {"error": "BigQuery client not connected."}
        
    try:
        table_ref = bq_client.dataset(dataset_id).table(table_id)
        table = bq_client.get_table(table_ref)
        schema = [
            {"name": field.name, "type": field.field_type, "description": field.description} 
            for field in table.schema
        ]
        return {"status": "success", "schema": schema}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- LOGIKA AGENTA (ADK ROOT) ---

SYSTEM_PROMPT = """
Jesteś Starszym Analitykiem Danych w EPIR Art Jewellery. 
Twoim celem jest wyciąganie wniosków biznesowych z danych BigQuery.

PROTOKÓŁ DZIAŁANIA (Thinking Mode):
1. **Analiza Intencji**: Zrozum, o co pyta użytkownik.
2. **Weryfikacja Struktury**: Jeśli nie masz pewności co do nazw kolumn, UŻYJ `get_table_schema`.
3. **Konstrukcja SQL**: Przygotuj zapytanie w bloku myślowym. Upewnij się, że używasz poprawnej składni BigQuery.
4. **Egzekucja**: Użyj `run_sql_query`.
5. **Synteza**: Odpowiedz użytkownikowi zwięźle.
"""

# Definicja Plannera - tu konfigurujemy "Thinking Mode" zgodnie ze sztuką
thinking_planner = BuiltInPlanner(
    thinking_config=types.ThinkingConfig(
        include_thoughts=True,
        thinking_level=types.ThinkingLevel.HIGH  # Gemini 3 wymaga tego parametru
    )
)

root_agent = Agent(
    model='gemini-3-flash-preview', 
    name='bq_analyst',
    description="Agent analityczny SQL dla EPIR Art Jewellery",
    instruction=SYSTEM_PROMPT,
    tools=[run_sql_query, get_table_schema],
    planner=thinking_planner  # Wstrzykujemy mózg do agenta
)
