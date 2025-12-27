import os
import uuid
import asyncio
import json
import threading
import time
from typing import List, Dict
from dotenv import load_dotenv

# AutoGen v0.4 imports
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")


# v0.4 model client configuration
def create_model_client():
    return OpenAIChatCompletionClient(
        model="gpt-4o-mini", api_key=API_KEY, temperature=0, seed=42
    )


SESSIONS = {}


class StreamingGroupChatManager:
    def __init__(self, group_chat):
        self.group_chat = group_chat
        self._cancellation_token = None

    async def stream_debate_round(self, moderator_message: str):
        """Stream messages as they're generated using v0.4 run_stream"""
        try:
            # Create cancellation token for this round
            self._cancellation_token = CancellationToken()

            # Use the new v0.4 run_stream method
            stream = self.group_chat.run_stream(
                task=moderator_message, cancellation_token=self._cancellation_token
            )

            async for message in stream:
                # Format message for SSE
                formatted_msg = self._format_message_for_stream(message)
                if formatted_msg:
                    yield formatted_msg

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    def _format_message_for_stream(self, message) -> str:
        """Format message for SSE"""
        # Handle different message types from v0.4
        if hasattr(message, "source") and hasattr(message, "content"):
            # Skip system messages and termination messages
            content = str(message.content).strip()
            if (
                content
                and "TERMINATE" not in content
                and "Proceed to next round" not in content
            ):
                formatted_msg = {
                    "agent": message.source,
                    "content": content,
                    "timestamp": int(time.time() * 1000),  # milliseconds
                }
                return f"data: {json.dumps(formatted_msg)}\n\n"
        return ""

    def stop_streaming(self):
        """Stop the streaming process"""
        if self._cancellation_token:
            self._cancellation_token.cancel()


def parse_messages(messages: List[Dict], start_index: int = 0) -> List[Dict]:
    """
    Parses messages to assign correct round numbers.
    Crucially, it iterates through the FULL history to track round progression,
    then only returns the messages that are new (>= start_index).
    """
    structured_messages = []
    current_round = 1
    last_round = -1
    round_inner_index = 0

    for i, msg in enumerate(messages):
        agent_name = msg.get("name", "unknown")
        content = msg.get("content", "").strip()

        if last_round != current_round:
            round_inner_index = 0
            last_round = current_round
        else:
            round_inner_index += 1
        # Skip system commands
        if "TERMINATE" in content or "Proceed to next round" in content:
            continue

        if content:
            # Only add to output if it's a new message
            if i >= start_index:
                structured_messages.append(
                    {
                        "round": current_round,
                        "agent": agent_name,
                        "content": content,
                        "round_inner_index": round_inner_index,
                    }
                )

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
    model_client = create_model_client()

    for agent_conf in agents_config:
        if agent_conf["name"].startswith("Debater_"):
            debaters.append(
                AssistantAgent(
                    name=agent_conf["name"],
                    system_message=agent_conf["systemMessage"],
                    model_client=model_client,
                )
            )
        elif agent_conf["name"] == "Judge":
            judge = AssistantAgent(
                name=agent_conf["name"],
                system_message=agent_conf["systemMessage"],
                model_client=model_client,
            )

    user_proxy = UserProxyAgent(name="Moderator")

    # Create RoundRobinGroupChat with termination condition
    termination_condition = MaxMessageTermination(max_messages=4)
    group_chat = RoundRobinGroupChat(
        participants=[user_proxy, *debaters, judge],
        termination_condition=termination_condition,
    )

    # Note: In v0.4, we don't use initiate_chat. Instead, we'll run the chat when needed.
    SESSIONS[session_id] = {
        "group_chat": group_chat,
        "user_proxy": user_proxy,
        "sent_messages_count": 0,
        "model_client": model_client,
    }

    # Run the initial round synchronously for compatibility
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the first round
    task_result = loop.run_until_complete(group_chat.run(task=f"Debate Topic: {topic}"))

    # Convert v0.4 messages to v0.2 format for compatibility
    converted_messages = []
    for i, msg in enumerate(task_result.messages):
        if hasattr(msg, "source") and hasattr(msg, "content"):
            content = str(msg.content).strip()
            if content and not content.startswith("Debate Topic:"):
                converted_messages.append({"name": msg.source, "content": content})

    SESSIONS[session_id]["sent_messages_count"] = len(task_result.messages)

    return {
        "session_id": session_id,
        "messages": parse_messages(converted_messages, start_index=0),
    }


def continue_debate_session(session_id: str) -> Dict:
    if session_id not in SESSIONS:
        return {"error": "Session not found"}

    session = SESSIONS[session_id]
    group_chat = session["group_chat"]
    last_count = session["sent_messages_count"]

    # Run next round
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Continue the chat with new round
    task_result = loop.run_until_complete(
        group_chat.run(task="Proceed to the next round of arguments.")
    )

    # Convert v0.4 messages to v0.2 format for compatibility
    all_messages = []
    for msg in task_result.messages:
        if hasattr(msg, "source") and hasattr(msg, "content"):
            content = str(msg.content).strip()
            if content:
                all_messages.append({"name": msg.source, "content": content})

    # Parse new messages starting from last count
    new_messages = parse_messages(all_messages, start_index=last_count)
    session["sent_messages_count"] = len(all_messages)

    return {"session_id": session_id, "messages": new_messages}


def create_streaming_debate_session(
    moderator_message: str, agents_config: List[Dict]
) -> Dict:
    """Create a new streaming debate session"""
    session_id = str(uuid.uuid4())

    debaters = []
    judge = None
    model_client = create_model_client()

    for agent_conf in agents_config:
        if agent_conf["name"].startswith("Debater_"):
            debaters.append(
                AssistantAgent(
                    name=agent_conf["name"],
                    system_message=agent_conf["systemMessage"],
                    model_client=model_client,
                )
            )
        elif agent_conf["name"] == "Judge":
            judge = AssistantAgent(
                name=agent_conf["name"],
                system_message=agent_conf["systemMessage"],
                model_client=model_client,
            )

    # user_proxy = UserProxyAgent(
    #     name="Moderator",
    #     code_execution_config=False,
    # )

    # Create RoundRobinGroupChat with termination condition
    termination_condition = MaxMessageTermination(max_messages=4)
    group_chat = RoundRobinGroupChat(
        participants=[*debaters, judge],
        termination_condition=termination_condition,
    )

    # Create streaming manager
    streaming_manager = StreamingGroupChatManager(group_chat)

    SESSIONS[session_id] = {
        "streaming_manager": streaming_manager,
        "moderator_message": moderator_message,
        "group_chat": group_chat,
        # "user_proxy": user_proxy,
        "sent_messages_count": 0,
        "round": 1,
        "model_client": model_client,
    }

    return {"session_id": session_id}


async def stream_debate_round(session_id: str, prompt: str = None):
    """Stream a debate round for the given session"""
    if session_id not in SESSIONS:
        yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
        return

    session = SESSIONS[session_id]
    streaming_manager = session["streaming_manager"]
    moderator_message = session["moderator_message"]

    print(
        f"Starting streaming for session {session_id}, round {session['round']}, moderator_message: {moderator_message}"
    )

    # Yield start indicator
    yield f"data: {json.dumps({'status': 'started', 'round': session['round']})}\n\n"

    try:
        # Stream the messages from this round
        async for message_data in streaming_manager.stream_debate_round(
            moderator_message
        ):
            yield message_data

        # Update round counter
        session["round"] += 1

        # Yield completion indicator
        yield f"data: {json.dumps({'status': 'completed', 'round': session['round'] - 1})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


# def initialize_streaming_debate(session_id: str, topic: str):
#     """Initialize the debate with the given topic"""
#     if session_id not in SESSIONS:
#         return {"error": "Session not found"}

#     session = SESSIONS[session_id]

#     # Store the topic for reference
#     session["topic"] = topic

#     # Return session info without initial messages for pure streaming
#     return {
#         "session_id": session_id,
#         "messages": [],  # No initial messages - will be streamed
#         "topic": topic
#     }
