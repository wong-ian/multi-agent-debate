import os
import uuid
import json
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from autogen.agentchat import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

LLM_CONFIG = {
    "config_list": [{"model": "gpt-4o-mini", "api_key": API_KEY}],
    "cache_seed": None
}

SESSIONS = {}

def parse_messages(messages: List[Dict], start_index: int = 0) -> List[Dict]:
    """
    Parses messages to assign correct round numbers.
    Crucially, it iterates through the FULL history to track round progression,
    then only returns the messages that are new (>= start_index).
    """
    structured_messages = []
    current_round = 1
    
    for i, msg in enumerate(messages):
        agent_name = msg.get("name", "unknown")
        content = msg.get("content", "").strip()
        
        # Skip system commands
        if "TERMINATE" in content or "Proceed to next round" in content:
            continue
            
        if content:
            # Only add to output if it's a new message
            if i >= start_index:
                structured_messages.append({
                    "round": current_round, 
                    "agent": agent_name,
                    "content": content
                })
            
            # Increment round AFTER processing the Judge's message
            # This ensures the Judge is included in the current round, 
            # and the NEXT message starts the new round.
            if agent_name == "Judge":
                current_round += 1

    return structured_messages

def create_debate_session(topic: str, agents_config: List[Dict]) -> Dict:
    session_id = str(uuid.uuid4())
    
    debaters = []
    judge = None
    
    for agent_conf in agents_config:
        if agent_conf['name'].startswith("Debater_"):
            debaters.append(AssistantAgent(
                name=agent_conf['name'],
                system_message=agent_conf['systemMessage'],
                llm_config=LLM_CONFIG,
            ))
        elif agent_conf['name'] == "Judge":
            judge = AssistantAgent(
                name=agent_conf['name'],
                system_message=agent_conf['systemMessage'],
                llm_config=LLM_CONFIG,
            )

    user_proxy = UserProxyAgent(
        name="Moderator",
        human_input_mode="NEVER",
        code_execution_config=False,
    )

    # Start with enough rounds for the intro + 3 turns
    group_chat = GroupChat(
        agents=[user_proxy, *debaters, judge],
        messages=[],
        max_round=4, 
        speaker_selection_method="round_robin"
    )

    manager = GroupChatManager(groupchat=group_chat, llm_config=LLM_CONFIG)

    # Run Round 1
    user_proxy.initiate_chat(manager, message=f"Debate Topic: {topic}")

    SESSIONS[session_id] = {
        "group_chat": group_chat,
        "manager": manager,
        "user_proxy": user_proxy,
        "sent_messages_count": len(group_chat.messages)
    }

    return {
        "session_id": session_id,
        "messages": parse_messages(group_chat.messages, start_index=1)
    }

def continue_debate_session(session_id: str) -> Dict:
    if session_id not in SESSIONS:
        return {"error": "Session not found"}

    session = SESSIONS[session_id]
    group_chat = session["group_chat"]
    manager = session["manager"]
    user_proxy = session["user_proxy"]
    last_count = session["sent_messages_count"]

    # Increase round limit for next 3 turns (A -> B -> Judge)
    # Adding 4 to safe-guard against system prompts consuming rounds
    group_chat.max_round += 4
    
    user_proxy.initiate_chat(
        manager, 
        message="Moderator: Proceed to the next round of arguments.", 
        clear_history=False
    )

    # Key Change: We pass the FULL message list to parse_messages, 
    # but tell it to only return items starting from `last_count`
    all_messages = group_chat.messages
    new_messages = parse_messages(all_messages, start_index=last_count)
    
    session["sent_messages_count"] = len(all_messages)

    return {
        "session_id": session_id,
        "messages": new_messages
    }
    
    
def save_debate_to_file(session_id: str, analysis_result: Dict) -> Dict:
    """
    Compiles the debate history and saves it to the /saved_debates folder.
    """
    import os, json, re # Ensure these are imported at the top
    from collections import Counter
    from autogen.agentchat import AssistantAgent

    if session_id not in SESSIONS:
        return {"error": "Session not found"}

    session = SESSIONS[session_id]
    messages = session["group_chat"].messages
    
    # 1. Parse Transcript & Scores (Uses the existing parse_messages logic)
    transcript = parse_messages(messages, start_index=0)
    
    # Calculate Scores/Winner based on transcript
    scores = Counter()
    for msg in transcript:
        if msg['agent'] == 'Judge':
            match = re.search(r"Round Winner: (Debater_[A-Z])", msg['content'], re.IGNORECASE)
            if match:
                scores[match.group(1)] += 1
    
    final_scores = dict(scores) # Ensures standard dict format
    winner = max(final_scores, key=final_scores.get) if final_scores else "Tie"
    
    # Check for ties
    if final_scores:
        top_score = final_scores[winner]
        if len([k for k, v in final_scores.items() if v == top_score]) > 1:
            winner = "Tie"

    # 2. Build Configuration List
    config = []
    for agent in session["group_chat"].agents:
        if isinstance(agent, AssistantAgent):
            config.append({
                "name": agent.name,
                "system_message": agent.system_message
            })

    # 3. Construct Final JSON
    data = {
        "metadata": {
            "topic": messages[0].get("content", "Unknown Topic").replace("Debate Topic: ", ""),
            "total_rounds": transcript[-1]['round'] if transcript else 0,
            "winner": winner,
            "final_scores": final_scores
        },
        "configuration": config,
        "transcript": transcript,
        "analysis": analysis_result
    }

    # 4. Save to Disk
    directory = "saved_debates"
    if not os.path.exists(directory):
        os.makedirs(directory)

    safe_topic = re.sub(r'[^a-zA-Z0-9]', '_', data['metadata']['topic'][:30])
    filename = f"{directory}/{safe_topic}.json"
    
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 5. Clean up the session state (CRUCIAL: Releases memory)
    del SESSIONS[session_id]

    return {"status": "saved", "filename": filename}