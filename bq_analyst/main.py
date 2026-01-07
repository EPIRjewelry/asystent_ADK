from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    return {"response": f"Odebrałem: {request.text}. (Tu agent ADK odpowie)"}
