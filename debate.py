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
        "You are a neutral judge. You will be called after Debater_A and Debater_B have each spoken. "
        "You will speak 5 times in total.\n"
        "**ROUNDS 1-4:** Provide a brief critique of their arguments for that round. DO NOT declare a winner.\n"
        "**ROUND 5 (FINAL):** This is your final message. You MUST declare a winner. "
        "Your message must ONLY contain the winner declaration, starting *exactly* with 'Winner:' (e.g., 'Winner: Debater_A'). "
        "Do not add any other summary or text to your final message."
    ),
    llm_config=llm_config,
)

# Create a UserProxyAgent to initiate the conversation
user_proxy = UserProxyAgent(
    name="User_Proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

# Add the user_proxy to the group chat
group_chat = GroupChat(
    agents=[debater_a, debater_b, judge], 
    messages=[], 
    max_round=15, 
    speaker_selection_method="round_robin"
)


manager = GroupChatManager(
    groupchat=group_chat, 
    llm_config=llm_config,
    is_termination_msg=lambda x: "winner:" in x.get("content", "").lower()
)

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
            print(f"{name}: {content}\n")
            f.write(f"{name}: {content}\n\n")

print("Debate saved to debate_history.txt")