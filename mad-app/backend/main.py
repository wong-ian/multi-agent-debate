from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

# Import the new session functions
from debate_logic import create_debate_session, continue_debate_session
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
    topic: str
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