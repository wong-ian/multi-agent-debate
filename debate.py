from dotenv import load_dotenv
import os
import json
import re
from collections import Counter
from autogen.agentchat import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set in environment or .env file")

llm_config = {"config_list": [{"model": "gpt-4o-mini", "api_key": api_key}]}

debater_a = AssistantAgent(
    name="Debater_A",
    system_message=(
        "You are Debater_A. Your goal is to argue **FOR** the topic.\n"
        "**Style:** Be direct, confident, and conversational. Get straight to the point.\n"
        "**Rules:** Wait for the topic, then make your first argument. After that, you will refute your opponent and strengthen your case.\n"
        "Stay on topic. **Do not** talk about the debate's rules, your strategy, or the Judge."
    ),
    llm_config=llm_config,
)

debater_b = AssistantAgent(
    name="Debater_B",
    system_message=(
        "You are Debater_B. Your goal is to argue **AGAINST** the topic.\n"
        "**Style:** Be direct, confident, and conversational. Get straight to the point.\n"
        "**Rules:** Wait for your opponent's first argument, then begin your refutation.\n"
        "Stay on topic. **Do not** talk about the debate's rules, your strategy, or the Judge."
    ),
    llm_config=llm_config,
)

judge = AssistantAgent(
    name="Judge",
    system_message=(
        "You are a neutral debate judge.\n"
        "Your job is to provide a brief critique of the two arguments you just heard and declare a winner *for that round*.\n"
        "**Style:** Be direct, impartial, and concise. **Do not** use formal salutations.\n"
        "**Your response MUST end with one of these two exact phrases:**\n"
        "Round Winner: Debater_A\n"
        "Round Winner: Debater_B"
    ),
    llm_config=llm_config,
)

# Create a UserProxyAgent to initiate the conversation
user_proxy = UserProxyAgent(
    name="User_Proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

# Set up the group chat
group_chat = GroupChat(
    agents=[debater_a, debater_b, judge], 
    messages=[], 
    max_round=16, # 5 rounds * 3 speakers + 1 buffer
    speaker_selection_method="round_robin"
)

# The manager runs the chat and no longer needs termination logic
manager = GroupChatManager(
    groupchat=group_chat, 
    llm_config=llm_config
)

topic = "AI will benefit society more than it will harm it."

# Initiate the chat
user_proxy.initiate_chat(manager, message=topic)

# === PARSE AND SAVE THE DEBATE HISTORY AS JSON ===

messages = group_chat.messages
if not messages:
    raise RuntimeError("No messages found in group_chat.messages attribute")

# The first message is the topic from the User_Proxy
topic = messages[0].get("content", "Unknown Topic").strip()

# The actual debate messages start from the second message
debate_messages = messages[1:]

structured_messages = []
round_num = 1
round_winners = []

print("\n--- Parsing Debate History ---")

for msg in debate_messages:
    agent_name = msg.get("name", "unknown")
    content = msg.get("content", "").strip()
    
    if content:
        # Add message to the structured list
        structured_messages.append({
            "round": round_num,
            "agent": agent_name,
            "content": content
        })
        
        # If this is the Judge, find the round winner
        if agent_name == "Judge":
            print(f"Parsing Judge's critique for Round {round_num}...")
            # Use regex to find "Round Winner: Debater_A" or "Round Winner: Debater_B"
            match = re.search(r"Round Winner: (Debater_[AB])", content, re.IGNORECASE)
            
            if match:
                winner_name = match.group(1).replace("_a", "_A").replace("_b", "_B")
                round_winners.append(winner_name)
                print(f"Round {round_num} Winner: {winner_name}")
            else:
                print(f"Warning: Could not find a Round Winner for Round {round_num}.")
            
            # Increment round number
            round_num += 1

# Tally the winners
overall_winner = "Tie"
if round_winners:
    winner_counts = Counter(round_winners)
    # Check for a tie
    if len(winner_counts) > 1 and winner_counts.most_common(2)[0][1] == winner_counts.most_common(2)[1][1]:
        overall_winner = "Tie"
    else:
        overall_winner = winner_counts.most_common(1)[0][0]

print(f"\nOverall Winner: {overall_winner}")

# Create the final data object
output_data = {
    "topic": topic,
    "winner": overall_winner,
    "round_victories": dict(Counter(round_winners)), # Shows the score, e.g., {"Debater_A": 3, "Debater_B": 2}
    "message_count": len(structured_messages),
    "messages": structured_messages
}

# Write the data to a JSON file
print("\n--- SAVING DEBATE HISTORY (JSON) ---")
with open("debate_history.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

print("Debate saved to debate_history.json")