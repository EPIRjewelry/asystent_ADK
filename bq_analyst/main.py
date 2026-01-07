from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .agent import root_agent

app = FastAPI()

# Dodanie middleware CORS, aby przeglądarka mogła wysyłać żądania
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dozwól wszystkim serwerom (w produkcji ogranicz do swoich domen)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    text: str


@app.get("/")
def health_check():
    return {"status": "Agent działa na Cloud Run! Wersja v2."}


@app.post("/chat")
def chat(request: QueryRequest):
    try:
        result = root_agent.run(request.text)
        # ADK AgentResult zazwyczaj ma atrybuty output / response; jeśli brak, bierzemy str()
        answer = getattr(result, "output", None) or getattr(result, "response", None) or getattr(result, "text", None)
        if answer is None:
            answer = str(result)
        return {"response": answer}
    except Exception as e:
        return {"error": str(e)}
