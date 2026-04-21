from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

# Import the correct function name from your logic file
from debate_logic import create_debate_session, continue_debate_session, regenerate_round
from nlp_logic import perform_analysis
from mast_logic import analyze_round_taxonomy  # Make sure this matches your mast_logic.py

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

class SaveRequest(BaseModel):
    session_id: str
    analysis_result: Dict

class RegenerateRequest(BaseModel):
    session_id: str
    round_number: int
    mast_failures: List[str]
    human_input: str

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

@app.post("/api/analyze-taxonomy")
async def api_analyze_taxonomy(request: AnalysisRequest):
    try:
        return analyze_round_taxonomy(request.messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/regenerate-round")
async def api_regenerate_round(request: RegenerateRequest):
    """Rewinds to the previous-round checkpoint and reruns the round with human moderator context."""
    try:
        result = regenerate_round(
            request.session_id,
            request.round_number,
            request.mast_failures,
            request.human_input,
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-debate")
async def api_save_debate(request: SaveRequest):
    """
    Saves the finished debate to a JSON file.
    """
    from debate_logic import save_debate_to_file, SESSIONS 
    try:
        if request.session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Session not found in memory.")
            
        # --- FIX APPLIED HERE ---
        # Pass the analysis_result directly as it is already a standard dictionary
        save_result = save_debate_to_file(request.session_id, request.analysis_result) 
        
        return save_result
    except HTTPException:
        raise
    except Exception as e:
        # LOGGING REMAINS TO CATCH OTHER ISSUES
        print(f"\n--- FATAL SAVE ERROR ---")
        import traceback
        traceback.print_exc()
        print(f"------------------------\n")
        raise HTTPException(status_code=500, detail=f"Failed to save debate due to: {e}")
