from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict

# Import the new session functions
from debate_logic import (
    create_debate_session,
    continue_debate_session,
    create_streaming_debate_session,
    stream_debate_round,
    # initialize_streaming_debate,
)
from nlp_logic import perform_analysis

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentConfig(BaseModel):
    name: str
    systemMessage: str


class DebateRequest(BaseModel):
    moderator_message: str
    agents_config: List[AgentConfig]


class ContinueRequest(BaseModel):
    session_id: str


class AnalysisRequest(BaseModel):
    messages: List[Dict]


@app.post("/api/start-debate")
async def api_start_debate(request: DebateRequest):
    """Starts a new live session"""
    try:
        agents_dict = [agent.dict() for agent in request.agents_config]
        return create_debate_session(request.topic, agents_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/continue-debate")
async def api_continue_debate(request: ContinueRequest):
    """Steps the live session forward one round"""
    try:
        return continue_debate_session(request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze-debate")
async def api_analyze_debate(request: AnalysisRequest):
    return perform_analysis(request.messages)


@app.post("/api/create-streaming-debate-session")
async def api_create_streaming_debate_session(request: DebateRequest):
    """Start a streaming debate session"""
    try:
        agents_dict = [agent.dict() for agent in request.agents_config]
        return create_streaming_debate_session(request.moderator_message, agents_dict)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


# @app.post("/api/initialize-streaming-debate/{session_id}")
# async def api_initialize_streaming_debate(session_id: str, request: dict):
#     """Initialize the streaming debate with a topic"""
#     try:
#         moderator_message = request.get("moderator_message", "")
#         return initialize_streaming_debate(session_id, moderator_message)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream-debate/{session_id}")
async def api_stream_debate(session_id: str):
    """Stream debate messages in real-time using Server-Sent Events"""
    try:

        async def generate():
            async for message_data in stream_debate_round(session_id):
                yield message_data

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
