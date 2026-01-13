"""
EPIR BigQuery Analyst - FastAPI Server
Vertex AI Agent Engine compatible endpoint
Wersja: 2.0.0
"""
from dotenv import load_dotenv
load_dotenv()  # Ładuj zmienne z .env dla lokalnego developmentu

from contextlib import asynccontextmanager
from typing import Optional
import logging
import uuid
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8080,https://adk-agent-580145215562.us-central1.run.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# === Static Files (Frontend) ===
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")
    logger.info(f"✅ Frontend mounted from {frontend_path}")
else:
    logger.warning(f"⚠️  Frontend not found at {frontend_path} - API only mode")


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

@app.get("/")
async def root():
    """Serwuje stronę główną React."""
    frontend_index = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    # Fallback do health check jeśli frontend nie istnieje
    return HealthResponse(
        status="ok",
        service="bq-analyst-agent",
        version="2.0.0",
        environment=settings.ENV,
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint dla Cloud Run."""
    return HealthResponse(
        status="healthy",
        service="EPIR BigQuery Analyst Agent",
        version="2.0.0",
        environment=settings.ENV,
    )


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


# === Statyczne pliki frontendu (Vite assets) ===
frontend_root = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_root.exists():
    app.mount("/assets", StaticFiles(directory=frontend_root / "assets"), name="assets")


# === SPA Fallback (musi być ostatni endpoint) ===
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """
    Catch-all endpoint dla React SPA routing.
    Zwraca index.html dla wszystkich nieznanych ścieżek.
    """
    frontend_index = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    raise HTTPException(status_code=404, detail="Frontend not found")


# === Main ===
if __name__ == "__main__":
    uvicorn.run(
        "bq_analyst.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=(settings.ENV == "dev"),
        log_level=settings.LOG_LEVEL.lower(),
    )
