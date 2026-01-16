import os
from typing import List, Dict
from openai import OpenAI

# Load the official taxonomy definitions [cite: 3362]
with open("definitions.txt", "r") as f:
    MAST_DEFINITIONS = f.read()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_round_taxonomy(messages: List[Dict]) -> Dict:
    # Format round messages for the judge
    transcript = "\n".join([f"{m['agent']}: {m['content']}" for m in messages])
    
    # Prompt structure inspired by llm_judge_pipeline.ipynb
    prompt = f"""
    You are an expert Multi-Agent System (MAS) diagnostic judge. 
    Analyze the following round of an AI debate using the MAST Taxonomy.
    
    TAXONOMY DEFINITIONS:
    {MAST_DEFINITIONS}
    
    ROUND TRANSCRIPT:
    {transcript}
    
    Analyze the behavior. Return a JSON object: 
    {{
        "summary": "Brief freeform text summary of failures/inefficiencies",
        "task_progress": "yes/no",
        "failures": [
            {{ "id": "1.3", "name": "Step Repetition", "detected": true }},
            ... (include all 14 modes as binary values)
        ]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o", # Or o1 as used in the paper for high agreement [cite: 2039]
        messages=[{"role": "system", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    import json
    return json.loads(response.choices[0].message.content)