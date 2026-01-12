"""
EPIR BigQuery Analyst - FastAPI Server
Vertex AI Agent Engine compatible endpoint
Wersja: 2.0.0
"""
from contextlib import asynccontextmanager
from typing import Optional
import logging
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from bq_analyst.agent import BigQueryAnalyst
from bq_analyst.config import settings

# === Logging ===
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === Agent Singleton ===
agent: Optional[BigQueryAnalyst] = None


# === Lifespan (zamiast deprecated on_event) ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager dla FastAPI."""
    global agent
    logger.info("🚀 Starting EPIR BigQuery Analyst Agent...")
    
    agent = BigQueryAnalyst()
    agent.set_up()
    
    logger.info("✅ Agent ready and listening")
    yield
    
    logger.info("🛑 Shutting down agent...")
    agent = None


# === FastAPI App ===
app = FastAPI(
    title="EPIR BigQuery Analyst Agent",
    description="Vertex AI Agent Engine compatible REST API for BigQuery analytics",
    version="2.0.0",
    lifespan=lifespan,
)

# === CORS Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W produkcji ogranicz do konkretnych domen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===
class QueryRequest(BaseModel):
    """Żądanie zapytania do agenta."""
    text: str = Field(..., min_length=1, max_length=10000, alias="text", description="Treść zapytania")
    query: Optional[str] = Field(None, description="Alias dla text (kompatybilność)")
    thread_id: Optional[str] = Field(None, description="ID sesji (opcjonalne)")
    
    def get_query_text(self) -> str:
        """Pobiera tekst zapytania z dowolnego pola."""
        return self.query or self.text


class QueryResponse(BaseModel):
    """Odpowiedź agenta."""
    response: str
    thread_id: str
    metadata: dict


class HealthResponse(BaseModel):
    """Status zdrowia serwisu."""
    status: str
    service: str
    version: str
    environment: str


class HistoryResponse(BaseModel):
    """Historia konwersacji."""
    thread_id: str
    messages: list


# === Endpoints ===

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check dla Cloud Run."""
    return HealthResponse(
        status="ok",
        service="bq-analyst-agent",
        version="2.0.0",
        environment=settings.ENV,
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Alias dla health check."""
    return await health_check()


@app.post("/agent/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Główny endpoint do zapytań analitycznych.
    Obsługuje sesje wieloturowe (przekaż thread_id do kontynuacji).
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Generuj thread_id jeśli nie podano
    thread_id = request.thread_id or str(uuid.uuid4())
    query_text = request.get_query_text()
    
    logger.info(f"POST /agent/query | thread={thread_id} | query={query_text[:50]}...")
    
    try:
        result = agent.query(query_text, thread_id=thread_id)
        
        return QueryResponse(
            response=result["response"],
            thread_id=result["thread_id"],
            metadata={
                "steps": result["steps"],
                "tool_calls": result["tool_calls"],
                "tool_results": result.get("tool_results", 0),
            }
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agent/history/{thread_id}", response_model=HistoryResponse)
async def get_history(thread_id: str):
    """Pobiera historię konwersacji dla danej sesji."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    history = agent.get_history(thread_id)
    
    return HistoryResponse(
        thread_id=thread_id,
        messages=history,
    )


@app.post("/chat")
async def chat_legacy(request: QueryRequest):
    """
    Legacy endpoint dla kompatybilności wstecznej.
    Przekierowuje do /agent/query.
    """
    result = await query_agent(request)
    return {"response": result.response}


# === Main ===
if __name__ == "__main__":
    uvicorn.run(
        "bq_analyst.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=(settings.ENV == "dev"),
        log_level=settings.LOG_LEVEL.lower(),
    )
