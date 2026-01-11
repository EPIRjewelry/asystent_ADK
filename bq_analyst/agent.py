from google.cloud import bigquery
from google import genai
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
    print(f"⚠️ [SYSTEM] Błąd inicjalizacji BigQuery: {e}")

# Inicjalizacja klienta Google GenAI dla Vertex AI
try:
    genai_client = genai.Client(
        vertexai=True,
        project=CORRECT_PROJECT_ID,
        location="us-central1"
    )
    print(f"🔌 [SYSTEM] Połączono z Vertex AI GenAI")
except Exception as e:
    genai_client = None
    print(f"⚠️ [SYSTEM] Błąd inicjalizacji GenAI: {e}")

# --- NARZĘDZIA (TOOLS) ---

def run_sql_query(query: str) -> dict:
    """
    Wykonuje zapytanie SQL do BigQuery i zwraca wyniki.
    
    Args:
        query: Zapytanie SQL (Standard SQL)
    
    Returns:
        Dict zawierający wyniki lub błąd
    """
    if not bq_client:
        return {"error": "BigQuery client not connected."}
    
    forbidden = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "MERGE", "GRANT"]
    if any(cmd in query.upper() for cmd in forbidden):
        return {"error": "SAFETY VIOLATION: Modification commands are strictly forbidden."}
    
    try:
        query_job = bq_client.query(query)
        results = [dict(row) for row in query_job]
        
        return {
            "status": "success",
            "rows": results[:50],
            "row_count": len(results),
            "note": "Output limited to 50 rows for context safety."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_table_schema(dataset_id: str, table_id: str) -> dict:
    """
    Pobiera schemat tabeli z BigQuery.
    
    Args:
        dataset_id: ID datasetu
        table_id: ID tabeli
    
    Returns:
        Dict zawierający schemat tabeli
    """
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

**Zasady:**
1. Analizuj intencje użytkownika.
2. Używaj get_table_schema w razie wątpliwości co do struktury tabeli.
3. Pisz poprawny SQL (Standard SQL).
4. Odpowiadaj zwięźle i konkretnie.
5. Zawsze podawaj źródło danych (dataset.table).
"""

def run_agent(prompt: str) -> str:
    """
    Uruchamia agenta analitycznego z danym zapytaniem.
    
    Args:
        prompt: Zapytanie użytkownika
    
    Returns:
        Odpowiedź agenta jako string
    """
    if not genai_client:
        return "Błąd: Klient GenAI nie został zainicjalizowany."
    
    try:
        response = genai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[run_sql_query, get_table_schema],
                temperature=0.7,
            )
        )
        
        return response.text if response.text else str(response)
    
    except Exception as e:
        return f"Błąd podczas pracy agenta: {str(e)}"
