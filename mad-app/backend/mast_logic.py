import os
from typing import List, Dict
from openai import OpenAI

# Berkeley MAST Failure Taxonomy Definitions
MAST_TAXONOMY = """
FC1: System Design Issues
- FM-1.1: Disobey task specification (Violates constraints/requirements)
- FM-1.2: Disobey role specification (Agent acts outside its assigned persona)
- FM-1.3: Step repetition (Unnecessary reiteration of completed steps)
- FM-1.4: Loss of conversation history (Forgets context/previous turns)
- FM-1.5: Unaware of termination conditions (Doesn't know when to stop)

FC2: Inter-Agent Misalignment
- FM-2.1: Conversation reset (Unexpectedly restarts dialogue)
- FM-2.2: Fail to ask for clarification (Proceeds with wrong assumptions)
- FM-2.3: Task derailment (Deviates from the intended objective)
- FM-2.4: Information withholding (Possesses data but doesn't share it)
- FM-2.5: Ignored other agent's input (Disregards teammate's logic)
- FM-2.6: Reasoning-action mismatch (Logic says one thing, action does another)

FC3: Task Verification
- FM-3.1: Premature termination (Ends task before completion)
- FM-3.2: No or incomplete verification (Omission of proper checking)
- FM-3.3: Incorrect verification (Validates wrong/false information)
"""

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_round_mast(messages: List[Dict]) -> Dict:
    transcript = "\n".join([f"{m['agent']}: {m['content']}" for m in messages])
    
    prompt = f"""
    You are an expert Multi-Agent System (MAS) diagnostic judge. 
    Analyze the following round of an AI debate using the MAST Taxonomy.
    
    TAXONOMY DEFINITIONS:
    {MAST_TAXONOMY}
    
    ROUND TRANSCRIPT:
    {transcript}
    
    Identify if ANY failure modes occurred. 
    Return a JSON object: 
    {{
        "failures": [{{ "mode_id": "FM-X.X", "mode_name": "...", "reasoning": "..." }}],
        "health_score": 0-100,
        "summary": "Short 1-sentence diagnostic"
    }}
    If no failures, return an empty failures list and health_score 100.
    """
    
    # Using a high-reasoning model for diagnostic accuracy (similar to o1 in paper)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    import json
    return json.loads(response.choices[0].message.content)