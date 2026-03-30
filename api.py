from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Question(BaseModel):
    question: str

@app.get("/")
def home():
    return {"message": "API dziala"}

@app.post("/ask")
def ask_ai(q: Question):
    return {"answer": f"Test dziala: {q.question}"}