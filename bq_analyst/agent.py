"""
BigQuery Analyst Agent - Vertex AI Agent Engine + LangGraph
Wersja: 2.0.0
"""
from typing import List, Dict, Any, TypedDict, Annotated
import operator
import logging

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import (
    BaseMessage, 
    HumanMessage, 
    AIMessage, 
    SystemMessage,
    ToolMessage
)
from langchain_core.tools import tool, ToolException
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from google.cloud import bigquery

from bq_analyst.config import settings

# === Logging ===
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


# === Definicja Stanu Grafu ===
class AgentState(TypedDict):
    """Stan agenta przechowywany w LangGraph."""
    messages: Annotated[List[BaseMessage], operator.add]


# === Narzędzia (Tools) ===

def _get_bq_client() -> bigquery.Client:
    """Lazy initialization BigQuery client."""
    return bigquery.Client(project=settings.PROJECT_ID)


@tool
def list_datasets() -> str:
    """Listuje dostępne datasety w BigQuery. Użyj tego jako pierwszy krok, by poznać strukturę danych."""
    logger.info("Tool called: list_datasets")
    try:
        client = _get_bq_client()
        datasets = list(client.list_datasets())
        if not datasets:
            return "Brak dostępnych datasetów w projekcie."
        result = [d.dataset_id for d in datasets]
        logger.info(f"Found {len(result)} datasets")
        return str(result)
    except Exception as e:
        logger.error(f"list_datasets error: {e}")
        raise ToolException(f"Błąd listowania datasetów: {str(e)}")


@tool
def list_tables(dataset_id: str) -> str:
    """Listuje tabele w podanym datasecie BigQuery."""
    logger.info(f"Tool called: list_tables(dataset_id={dataset_id})")
    try:
        client = _get_bq_client()
        tables = list(client.list_tables(dataset_id))
        if not tables:
            return f"Brak tabel w datasecie {dataset_id}."
        result = [t.table_id for t in tables]
        logger.info(f"Found {len(result)} tables in {dataset_id}")
        return str(result)
    except Exception as e:
        logger.error(f"list_tables error: {e}")
        raise ToolException(f"Błąd listowania tabel: {str(e)}")


@tool
def get_table_schema(dataset_id: str, table_id: str) -> str:
    """Pobiera schemat tabeli BigQuery. Zawsze użyj tego przed pisaniem SQL, by poznać nazwy i typy kolumn."""
    logger.info(f"Tool called: get_table_schema(dataset={dataset_id}, table={table_id})")
    try:
        client = _get_bq_client()
        table_ref = f"{settings.PROJECT_ID}.{dataset_id}.{table_id}"
        table = client.get_table(table_ref)
        schema_info = [
            f"{field.name}: {field.field_type} {'(NULLABLE)' if field.mode == 'NULLABLE' else '(REQUIRED)' if field.mode == 'REQUIRED' else '(REPEATED)'}"
            for field in table.schema
        ]
        result = f"Schemat tabeli {table_ref}:\n" + "\n".join(schema_info)
        logger.info(f"Schema retrieved for {table_ref}")
        return result
    except Exception as e:
        logger.error(f"get_table_schema error: {e}")
        raise ToolException(f"Błąd pobierania schematu: {str(e)}")


@tool
def execute_sql(query: str) -> str:
    """
    Wykonuje zapytanie SQL w BigQuery (tylko READ-ONLY).
    WAŻNE: Przed użyciem sprawdź schemat tabeli za pomocą get_table_schema.
    """
    logger.info(f"Tool called: execute_sql")
    logger.debug(f"SQL Query: {query}")
    
    # === Zabezpieczenie: blokada modyfikujących operacji ===
    FORBIDDEN_KEYWORDS = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE", "MERGE"]
    query_upper = query.upper()
    
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in query_upper:
            error_msg = f"BŁĄD BEZPIECZEŃSTWA: Operacja '{keyword}' jest zabroniona. Dozwolone są tylko zapytania SELECT."
            logger.warning(f"Blocked forbidden SQL operation: {keyword}")
            raise ToolException(error_msg)
    
    try:
        client = _get_bq_client()
        query_job = client.query(query)
        results = query_job.result()
        
        rows = [dict(row) for row in results]
        row_count = len(rows)
        
        # Limitowanie wyników dla czytelności
        MAX_ROWS = 50
        if row_count > MAX_ROWS:
            rows = rows[:MAX_ROWS]
            result = f"Wyniki (pierwsze {MAX_ROWS} z {row_count} wierszy):\n{str(rows)}"
        else:
            result = f"Wyniki ({row_count} wierszy):\n{str(rows)}"
        
        logger.info(f"SQL executed successfully, returned {row_count} rows")
        return result
        
    except Exception as e:
        error_msg = f"Błąd wykonania SQL: {str(e)}"
        logger.error(f"execute_sql error: {e}")
        # Zwracamy błąd jako ToolException, by agent mógł spróbować naprawić zapytanie
        raise ToolException(error_msg)


# === System Prompt ===
SYSTEM_INSTRUCTION = """Jesteś Głównym Analitykiem Danych firmy EPIR Art Jewellery.
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
"""


# === Klasa Agenta ===
class BigQueryAnalyst:
    """
    Agent Analityczny zgodny z interfejsem Vertex AI Reasoning Engine.
    Wykorzystuje LangGraph do orkiestracji z pętlą narzędziową.
    """
    
    def __init__(self):
        self.project_id = settings.PROJECT_ID
        self.location = settings.LOCATION
        self.model_name = settings.MODEL_NAME
        self.app = None
        self.memory = MemorySaver()  # Pamięć sesji
        logger.info(f"BigQueryAnalyst initialized (project={self.project_id}, model={self.model_name})")
    
    def set_up(self):
        """Inicjalizacja grafu LangGraph (Lazy Loading)."""
        logger.info("Setting up LangGraph workflow...")
        
        # 1. Model LLM
        llm = ChatVertexAI(
            model_name=self.model_name,
            project=self.project_id,
            location=self.location,
            temperature=settings.TEMPERATURE,
            max_output_tokens=4096,
        )
        
        # 2. Narzędzia
        tools = [list_datasets, list_tables, get_table_schema, execute_sql]
        llm_with_tools = llm.bind_tools(tools)
        
        # 3. Węzeł: Wywołanie modelu
        def call_model(state: AgentState) -> Dict[str, List[BaseMessage]]:
            messages = state["messages"]
            
            # Dodaj System Prompt jeśli brak
            if not any(isinstance(m, SystemMessage) for m in messages):
                messages = [SystemMessage(content=SYSTEM_INSTRUCTION)] + messages
            
            logger.debug(f"Calling model with {len(messages)} messages")
            response = llm_with_tools.invoke(messages)
            logger.debug(f"Model response: tool_calls={bool(response.tool_calls)}")
            
            return {"messages": [response]}
        
        # 4. Węzeł: Obsługa narzędzi
        tool_node = ToolNode(tools, handle_tool_errors=True)
        
        # 5. Budowa grafu
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        
        workflow.set_entry_point("agent")
        
        # 6. Logika warunkowa: kontynuować czy zakończyć?
        def should_continue(state: AgentState) -> str:
            last_message = state["messages"][-1]
            
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                logger.debug("Routing to tools")
                return "tools"
            
            logger.debug("Routing to END")
            return END
        
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", END: END}
        )
        workflow.add_edge("tools", "agent")  # Pętla: Tools → Agent
        
        # 7. Kompilacja z pamięcią
        self.app = workflow.compile(checkpointer=self.memory)
        logger.info("LangGraph workflow compiled successfully")
    
    def query(
        self, 
        input_text: str, 
        thread_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Główna metoda zapytania do agenta.
        
        Args:
            input_text: Zapytanie użytkownika
            thread_id: ID sesji (dla pamięci kontekstu)
        
        Returns:
            Dict z odpowiedzią i metadanymi
        """
        if not self.app:
            self.set_up()
        
        logger.info(f"Processing query (thread={thread_id}): {input_text[:100]}...")
        
        inputs = {"messages": [HumanMessage(content=input_text)]}
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": settings.RECURSION_LIMIT,
        }
        
        try:
            final_state = self.app.invoke(inputs, config=config)
            
            # Zbierz metryki
            messages = final_state["messages"]
            tool_calls_count = sum(
                1 for m in messages 
                if isinstance(m, AIMessage) and m.tool_calls
            )
            tool_results_count = sum(
                1 for m in messages 
                if isinstance(m, ToolMessage)
            )
            
            # Ostatnia odpowiedź
            last_message = messages[-1]
            response_text = last_message.content if hasattr(last_message, "content") else str(last_message)
            
            logger.info(f"Query completed: {len(messages)} messages, {tool_calls_count} tool calls")
            
            return {
                "response": response_text,
                "thread_id": thread_id,
                "steps": len(messages),
                "tool_calls": tool_calls_count,
                "tool_results": tool_results_count,
            }
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                "response": f"Przepraszam, wystąpił błąd podczas przetwarzania zapytania: {str(e)}",
                "thread_id": thread_id,
                "steps": 0,
                "tool_calls": 0,
                "tool_results": 0,
                "error": str(e),
            }
    
    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Pobiera historię konwersacji dla danej sesji."""
        if not self.app:
            return []
        
        try:
            state = self.app.get_state({"configurable": {"thread_id": thread_id}})
            if state and state.values:
                return [
                    {"role": type(m).__name__, "content": m.content}
                    for m in state.values.get("messages", [])
                ]
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
        
        return []



