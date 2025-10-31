from dotenv import load_dotenv
import os
from autogen.agentchat import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set in environment or .env file")

llm_config = {"config_list": [{"model": "gpt-4o-mini", "api_key": api_key}]}

debater_a = AssistantAgent(
    name="Debater_A",
    system_message="You are arguing for the proposition. Be concise and logical.",
    llm_config=llm_config,
)

debater_b = AssistantAgent(
    name="Debater_B",
    system_message="You are arguing against the proposition. Be concise and logical.",
    llm_config=llm_config,
)

judge = AssistantAgent(
    name="Judge",
    system_message=(
        "You are a neutral judge. After each pair of responses, comment briefly. After 5 pairs, declare the winner."
    ),
    llm_config=llm_config,
)

# Create a UserProxyAgent to initiate the conversation
user_proxy = UserProxyAgent(
    name="User_Proxy",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: x.get("content", "").find("winner") >= 0,
    code_execution_config=False,
)

# Add the user_proxy to the group chat
group_chat = GroupChat(agents=[user_proxy, debater_a, debater_b, judge], messages=[], max_round=10)
manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

topic = "AI will benefit society more than it will harm it."


user_proxy.initiate_chat(manager, message=topic)

# Access conversation messages directly from the group_chat object
messages = group_chat.messages
if not messages:
    raise RuntimeError("No messages found in group_chat.messages attribute")

with open("debate_history.txt", "w", encoding="utf-8") as f:
    for msg in messages:
        name = msg.get("name", "unknown")
        content = msg.get("content", "")
        if content:
            print(f"{name}: {content}")
            f.write(f"{name}: {content}\n")

print("Debate saved to debate_history.txt")
