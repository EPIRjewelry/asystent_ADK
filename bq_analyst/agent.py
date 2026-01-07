from google.cloud import bigquery
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner 
from google.genai import types 

# --- KONFIGURACJA INFRASTRUKTURY ---
# W Cloud Run nie potrzebujemy pliku klucza - używamy tożsamości wbudowanej
CORRECT_PROJECT_ID = "epir-adk-agent-v2-48a86e6f"

try:
    # Wymuszamy projekt i region
    bq_client = bigquery.Client(project=CORRECT_PROJECT_ID, location="us-central1")
    print(f"🔌 [SYSTEM] Połączono z BigQuery. Projekt: {bq_client.project}")
except Exception as e:
    bq_client = None
    print(f"⚠️ [SYSTEM] Błąd inicjalizacji: {e}")

# --- NARZĘDZIA (TOOLS) ---

def run_sql_query(query: str) -> dict:
    if not bq_client:
        return {"error": "BigQuery client not connected."}

    # Bezpiecznik Rzemieślnika
    forbidden = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "MERGE", "GRANT"]
    if any(cmd in query.upper() for cmd in forbidden):
        return {"error": "SAFETY VIOLATION: Modification commands are strictly forbidden."}
    
    try:
        query_job = bq_client.query(query)
        results = [dict(row) for row in query_job]
        
        return {
            "status": "success", 
            "rows_count": len(results), 
            "data": results[:50], 
            "note": "Output limited to 50 rows for context safety."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_table_schema(dataset_id: str, table_id: str) -> dict:
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

# --- LOGIKA AGENTA ---

SYSTEM_PROMPT = """
Jesteś Starszym Analitykiem Danych w EPIR Art Jewellery. 
Twoim celem jest wyciąganie wniosków biznesowych z danych BigQuery.
1. Analizuj intencje.
2. Używaj get_table_schema w razie wątpliwości.
3. Pisz poprawny SQL (Standard SQL).
4. Odpowiadaj zwięźle.
"""

thinking_planner = BuiltInPlanner(
    thinking_config=types.ThinkingConfig(
        include_thoughts=True
    )
)

root_agent = Agent(
    model='gemini-3-flash-preview', 
    name='bq_analyst',
    description="Agent analityczny SQL",
    instruction=SYSTEM_PROMPT,
    tools=[run_sql_query, get_table_schema],
    planner=thinking_planner
)
