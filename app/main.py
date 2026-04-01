from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.services.ollama import OllamaService
from app.services.extractor import ExtractorService
from app.services.neo4j_service import Neo4jService
from app.db.sqlite import save_message
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
ollama_service = OllamaService()

class ChatRequest(BaseModel):
    message:str

@app.post("/chat")
async def chatEndpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    #save user message to db
    save_message("user", request.message)

    #get response from chat model
    try:
        messages = [{"role": "user", "content": request.message}]
        response = ollama_service.chat(messages)
        content = response['content']
        save_message("assistant", content)
        background_tasks.add_task(update_graph_task, request.message)
        return {"response":content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def update_graph_task(text: str):
    extractor = ExtractorService()
    graph_service = Neo4jService()
    try:
        entities = extractor.extract(text)
        graph_service.upsertGraph(entities)
        print("graph background update complete")
    except Exception as e:
        print(f"graph update failed: {e}")
    finally:
        graph_service.close()