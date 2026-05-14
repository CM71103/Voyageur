import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from voyageur import (
    extract_brief,
    generate_itinerary,
    refine_or_answer,
    build_memory_context,
    save_session_preferences,
    debug_memories,
)
from schemas import Itinerary
from memory import get_all_memories

app = FastAPI(title="Voyageur")

USER_ID = "priya"


class StartRequest(BaseModel):
    description: str


class ChatRequest(BaseModel):
    message: str
    current_itinerary: dict | None = None


class MemoriesRequest(BaseModel):
    history: list = []


@app.post("/api/start")
def start_trip(req: StartRequest):
    try:
        brief = extract_brief(req.description)
        itinerary = generate_itinerary(brief)
        memory_context = build_memory_context(USER_ID)
        return {
            "brief": brief.model_dump(),
            "itinerary": itinerary.model_dump(),
            "memory_context": memory_context,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        if req.current_itinerary:
            itinerary = Itinerary(**req.current_itinerary)
            result_type, result = refine_or_answer(itinerary, req.message)
            if result_type == "json" and result is not None:
                return {"type": "itinerary", "itinerary": result.model_dump(), "content": None}
            else:
                return {"type": "text", "itinerary": None, "content": str(result)}
        else:
            return {"type": "text", "itinerary": None, "content": "Start a trip first by describing your plans."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memories")
def get_memories():
    return {"memories": get_all_memories(USER_ID)}


@app.post("/api/save-memories")
def save_memories(req: MemoriesRequest):
    save_session_preferences(USER_ID, req.history)
    return {"status": "ok"}


# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# STATIC_DIR = os.path.join(BASE_DIR, "static")
# os.makedirs(STATIC_DIR, exist_ok=True)
# app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
