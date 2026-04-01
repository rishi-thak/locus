from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.services.ollama import OllamaService
from app.db.sqlite import save_message
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
ollama_service = OllamaService()

class ChatRequest(BaseModel):
    message:str

@app.post("/chat")
async def chatEndpoint(request: ChatRequest):
    #save user message to db
    save_message("user", request.message)

    #get response from chat model
    try:
        messages = [{"role": "user", "content": request.message}]
        response = ollama_service.chat(messages)
        content = response['content']
        save_message("assistant", content)
        return {"response":content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    