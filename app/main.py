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

def needs_extraction(message: str, response: str) -> bool:
    command_keywords = ["delete", "remove", "forget", "add", "update"]
    if any(kw in message.lower() for kw in command_keywords):
        print("DEBUG: needs_extraction: command detected, skipping classification")
        return True
    
    check = ollama_service.chat([
            {"role": "system", "content": "Reply only with 'yes' or 'no'. Does this conversation mention at least 2 distinct named entities (people, places, or projects)?"},
            {"role": "user", "content": f"User: {message}\nResponse: {response}"}
    ])
    result = "yes" in check['content'].lower()
    print(f"DEBUG: needs_extraction classification: {result} ({check['content']})")
    return result

async def maybe_update_graph(message: str, response: str):
    if needs_extraction(message, response):
        await update_graph_task(message)

#routes
@app.post("/chat")
async def chatEndpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    save_message("user", request.message)

    graph_service = Neo4jService()
    try:
        context = graph_service.getContext(request.message)
        print(f"DEBUG: injected context:\n{context}")
        
        base_prompt = """
        You're locus, a personal knowledge assistant. Talk like a good friend, not a bot.
        Avoid "assistant" speak (don't say "how can i help" or "here is the info").
        Keep responses short — 1 to 3 sentences unless the user asks for detail.
        Never say "here's what I know" or "based on the facts." Just answer.
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
            - just state the facts naturally.
            - DO NOT use external knowledge about people, companies, or projects.
            - If facts for 'rishi' and 'rishi thakkar' are present, treat them as the same person.

            EXAMPLES:
            Context: rishi STUDENT_AT cal_poly, rishi LIVES_IN slo
            User: who is rishi?
            Response: Rishi's a CS student at Cal Poly. Lives in SLO too.

            Context: vectr BUILT_BY rishi and scott, vectr HAS_FEATURE rag
            User: tell me about vectr
            Response: Vectr's an intelligence-native workspace — Rishi and Scott built it. Has RAG baked in.

            CURRENT CONTEXT FACTS:
            {context}
            """

        else:
            system_prompt = f"""{base_prompt}
            COLD START MODE: Your graph is currently empty for this topic.
            - DO NOT invent details about the user or their life.
            - Respond informally, like you're talking to a friend.
            - If the user is providing information, acknowledge the information with natural reactions (e.g., "sweet. got it." or "sounds good!").
            - If the user asks a question, explain that u haven't built a knowledge base for that yet and ask them to tell you more.

            EXAMPLES:
            user: 'who is rishi?'
            you: 'I don't have any information about rishi yet. Could you tell me more?'

            user: 'I'm working on a new project called vectr'
            you: 'Got it. I'll remember that for you. What does vectr do?'
            """
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ]
        response = ollama_service.chat(messages, options={"temperature": 0.8})
        content = response['content']
        
        save_message("assistant", content)
        background_tasks.add_task(maybe_update_graph, request.message, content)
        
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