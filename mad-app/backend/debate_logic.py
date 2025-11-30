import os
import uuid
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