from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.services.ollama import OllamaService
from app.services.extractor import ExtractorService
from app.services.neo4jService import Neo4jService
from app.db.sqlite import save_message
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # can be secured later, for future dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ollama_service = OllamaService()

class ChatRequest(BaseModel):
    message:str

#routes
@app.post("/chat")
async def chatEndpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    save_message("user", request.message)

    graph_service = Neo4jService()
    try:
        context = graph_service.getContext(request.message)
        
        system_prompt = "ur locus, a personal knowledge assistant. be concise and helpful."
        if context:
            system_prompt += f"\n\nhere are some facts from the user's graph that might be relevant:\n{context}"
            print(f"DEBUG: injected context:\n{context}")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ]
        response = ollama_service.chat(messages)
        content = response['content']
        
        save_message("assistant", content)
        background_tasks.add_task(update_graph_task, request.message)
        
        return {"response": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        graph_service.close()


    # #save user message to db
    # save_message("user", request.message)

    # #get response from chat model
    # try:
    #     messages = [{"role": "user", "content": request.message}]
    #     response = ollama_service.chat(messages)
    #     content = response['content']
    #     save_message("assistant", content)
    #     background_tasks.add_task(update_graph_task, request.message)
    #     return {"response":content}
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph")
async def getGraphEndpoint():
    graphService=Neo4jService()
    try:
        return graphService.getGraph()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        graphService.close()

#final graph updating background task
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