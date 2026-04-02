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
        print(f"DEBUG: injected context:\n{context}")
        
        base_prompt = """
        You're locus, a personal knowledge assistant. Respond informally, like you're talking to a friend.

        EXAMPLE:
        user: 'who is rishi?'
        you: 'hey there! here's what I know about rishi: {context here}'
        """
        # If facts for 'rishi' and 'rishi thakkar' are both present, treat them as the same person.

        # EXAMPLES:
        # Context: rishi STUDENT_AT cal_poly, rishi LIVES_IN slo
        # User: who is rishi?
        # Response: rishi is a student at cal poly and lives in slo.

        # Context: vectr BUILT_BY rishi and scott, vectr HAS_FEATURE rag
        # User: tell me about vectr
        # Response: vectr is an intelligence-native workspace built by rishi and scott that features rag.
        
        if context:
            system_prompt = f"""{base_prompt}
            GROUNDED MODE: You're provided with verified facts from the user's personal graph.
            - ONLY use the provided facts to answer.
            - Respond informally, like you're talking to a friend.
            - DO NOT use external knowledge about people, companies, or projects.
            - If facts for 'rishi' and 'rishi thakkar' are present, treat them as the same person.

            EXAMPLES:
            Context: rishi STUDENT_AT cal_poly, rishi LIVES_IN slo
            User: who is rishi?
            Response: Here's what I know about rishi: rishi is a student at cal poly and lives in slo.

            Context: vectr BUILT_BY rishi and scott, vectr HAS_FEATURE rag
            User: tell me about vectr
            Response: Here are some facts about vectr: vectr is an intelligence-native workspace built by rishi and scott that features rag.

            CURRENT CONTEXT FACTS:
            {context}
            """

            print(f"DEBUG: injected context:\n{context}")

        else:
            system_prompt = f"""{base_prompt}
            COLD START MODE: Your graph is currently empty for this topic.
            - DO NOT invent details about the user or their life.
            - Respond informally, like you're talking to a friend.
            - If the user is providing information, acknowledge it neutrally (e.g., "noted" or "got it").
            - If the user asks a question, explain that u haven't built a knowledge base for that yet and ask them to tell you more.

            EXAMPLES:
            user: 'who is rishi?'
            you: 'Hey there! I don't have any information about rishi yet. Could you tell me more?'

            user: 'I'm working on a new project called vectr'
            you: 'Got it. I'll remember that for you. What does vectr do?'
            """
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ]
        response = ollama_service.chat(messages)
        content = response['content']
        
        save_message("assistant", content)
        background_tasks.add_task(update_graph_task, f"User: {request.message} | Locus: {content}")
        
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