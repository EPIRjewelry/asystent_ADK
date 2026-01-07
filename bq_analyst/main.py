from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class QueryRequest(BaseModel):
    text: str


@app.get("/")
def health_check():
    return {"status": "Agent działa na Cloud Run! Wersja v2."}


@app.post("/chat")
def chat(request: QueryRequest):
    return {"response": f"Odebrałem: {request.text}. (Tu agent ADK odpowie)"}
