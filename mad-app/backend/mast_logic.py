import os
import json
import re
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 1. LOAD DEFINITIONS
try:
    with open("definitions.txt", "r", encoding="utf-8") as f:
        MAST_DEFINITIONS = f.read()
except FileNotFoundError:
    print("WARNING: definitions.txt not found.")
    MAST_DEFINITIONS = ""

# 2. LOAD EXAMPLES 
# (We try debate_examples.txt first, as that is your calibrated file. 
# If not found, we fall back to the generic examples.txt)
try:
    with open("debate_examples.txt", "r", encoding="utf-8") as f:
        MAST_EXAMPLES = f.read()
except FileNotFoundError:
    try:
        with open("examples.txt", "r", encoding="utf-8") as f:
            MAST_EXAMPLES = f.read()
    except FileNotFoundError:
        print("WARNING: No examples file found.")
        MAST_EXAMPLES = ""

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=60.0,
    max_retries=1
)

def analyze_round_taxonomy(messages: List[Dict]) -> Dict:
    # 1. Prepare the Trace
    trace = "\n".join([f"[{m.get('agent', 'System')}]: {m.get('content', '')}" for m in messages])

    # 2. THE EXACT PROMPT FROM THE PAPER
    # We construct it exactly as the 'openai_evaluator' function does.
    prompt = (
        "Below I will provide a multiagent system trace. provide me an analysis of the failure modes and inefficiencies as I will say below. \n"
        "In the traces, analyze the system behaviour."
        "There are several failure modes in multiagent systems I identified. I will provide them below. Tell me if you encounter any of them, as a binary yes or no. \n"
        "Also, give me a one sentence (be brief) summary of the problems with the inefficiencies or failure modes in the trace. Only mark a failure mode if you can provide an example of it in the trace, and specify that in your summary at the end"
        "Also tell me whether the task is successfully completed or not, as a binary yes or no."
        "At the very end, I provide you with the definitions of the failure modes and inefficiencies. After the definitions, I will provide you with examples of the failure modes and inefficiencies for you to understand them better."
        "Tell me if you encounter any of them between the @@ symbols as I will say below, as a binary yes or no."
        "Here are the things you should answer. Start after the @@ sign and end before the next @@ sign (do not include the @@ symbols in your answer):"
        "*** begin of things you should answer *** @@"
        "A. Freeform text summary of the problems with the inefficiencies or failure modes in the trace: <summary>"
        "B. Whether the task is successfully completed or not: <yes or no>"
        "C. Whether you encounter any of the failure modes or inefficiencies:"
        "1.1 Disobey Task Specification: <yes or no>"
        "1.2 Disobey Role Specification: <yes or no>"
        "1.3 Step Repetition: <yes or no>"
        "1.4 Loss of Conversation History: <yes or no>"
        "1.5 Unaware of Termination Conditions: <yes or no>"
        "2.1 Conversation Reset: <yes or no>"
        "2.2 Fail to Ask for Clarification: <yes or no>"
        "2.3 Task Derailment: <yes or no>"
        "2.4 Information Withholding: <yes or no>"
        "2.5 Ignored Other Agent's Input: <yes or no>"
        "2.6 Action-Reasoning Mismatch: <yes or no>"
        "3.1 Premature Termination: <yes or no>"
        "3.2 No or Incorrect Verification: <yes or no>"
        "3.3 Weak Verification: <yes or no>"
        "@@*** end of your answer ***"
        "An example answer is: \n"
        "A. The task is not completed due to disobeying role specification as agents went rogue and started to chat with each other instead of completing the task. Agents derailed and verifier is not strong enough to detect it.\n"
        "B. no \n"
        "C. \n"
        "1.1 no \n"
        "1.2 no \n"
        "1.3 no \n"
        "1.4 no \n"
        "1.5 no \n"
        "1.6 yes \n"
        "2.1 no \n"
        "2.2 no \n"
        "2.3 yes \n"
        "2.4 no \n"
        "2.5 no \n"
        "2.6 yes \n"
        "2.7 no \n"
        "3.1 no \n"
        "3.2 yes \n"
        "3.3 no \n"   
        "Here is the trace: \n"
        f"{trace}\n"
        "Also, here are the explanations (definitions) of the failure modes and inefficiencies: \n"
        f"{MAST_DEFINITIONS} \n"
        "Here are some examples of the failure modes and inefficiencies: \n"
        f"{MAST_EXAMPLES}"
    )

    try:
        # 3. Call OpenAI (TEXT MODE)
        # The paper uses temperature=1.0. We replicate that here.
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0 
        )
        
        raw_text = response.choices[0].message.content
        
        # 4. Parse the Text Response back into JSON for the Frontend
        return parse_mast_text_to_json(raw_text)

    except Exception as e:
        print(f"MAST ERROR: {str(e)}")
        return {"summary": f"System Error: {str(e)}", "failures": []}

def parse_mast_text_to_json(text: str) -> Dict:
    """
    Parses the 'A... B... C...' text format from the paper into the JSON 
    structure expected by the Svelte frontend.
    Logic adapted from the notebook's 'parse_responses' function.
    """
    # Default State
    result = {
        "summary": "Analysis failed to parse.",
        "task_progress": "yes",
        "failures": []
    }

    try:
        # Clean up markers
        cleaned_response = text.strip()
        if cleaned_response.startswith('@@'):
            cleaned_response = cleaned_response[2:]
        if cleaned_response.endswith('@@'):
            cleaned_response = cleaned_response[:-2]

        # 1. Extract Summary (Section A)
        # Regex: Look for A. <content> B.
        summary_match = re.search(r"A\.(.*?)B\.", cleaned_response, re.DOTALL | re.IGNORECASE)
        if summary_match:
            result["summary"] = summary_match.group(1).strip()
        else:
            # Fallback for looser formats
            summary_match = re.search(r"A\.(.*?)(\n|$)", cleaned_response, re.DOTALL)
            if summary_match:
                result["summary"] = summary_match.group(1).strip()

        # 2. Extract Task Progress (Section B)
        # Regex: Look for B. <content> C.
        progress_match = re.search(r"B\.(.*?)C\.", cleaned_response, re.DOTALL | re.IGNORECASE)
        if progress_match:
            progress_text = progress_match.group(1).lower()
            if "no" in progress_text:
                result["task_progress"] = "no"
            else:
                result["task_progress"] = "yes"

        # 3. Extract Failures (Section C)
        # We need to map the paper's list to your frontend's requirements.
        failure_map = {
            "1.1": "Disobey Task Specification",
            "1.2": "Disobey Role Specification",
            "1.3": "Step Repetition",
            "1.4": "Loss of Conversation History",
            "1.5": "Unaware of Termination Conditions",
            "2.1": "Conversation Reset",
            "2.2": "Fail to Ask for Clarification",
            "2.3": "Task Derailment",
            "2.4": "Information Withholding",
            "2.5": "Ignored Other Agent's Input",
            "2.6": "Action-Reasoning Mismatch",
            "3.1": "Premature Termination",
            "3.2": "No or Incorrect Verification",
            "3.3": "Weak Verification"
        }

        failures_list = []
        
        # We look for the "C." section explicitly to narrow search range
        c_section_match = re.search(r"C\.(.*)", cleaned_response, re.DOTALL | re.IGNORECASE)
        c_text = c_section_match.group(1) if c_section_match else cleaned_response

        for fid, fname in failure_map.items():
            is_detected = False
            
            # Robust Regex from the notebook's logic:
            # Look for the ID (e.g., "1.1") followed eventually by "yes" or "no"
            pattern = rf"{re.escape(fid)}.*?(yes|no)"
            match = re.search(pattern, c_text, re.IGNORECASE)
            
            if match:
                answer = match.group(1).lower()
                if "yes" in answer:
                    is_detected = True
            
            failures_list.append({
                "id": fid,
                "name": fname,
                "detected": is_detected
            })

        result["failures"] = failures_list

    except Exception as e:
        print(f"PARSING ERROR: {e}")
        # Return the raw text as summary so you can debug visually in the UI
        result["summary"] = f"Parse Error. Raw Output: {text[:150]}..."
    
    return result