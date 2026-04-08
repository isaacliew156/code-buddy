import json
from openai import OpenAI
from config import OPENROUTER_API_KEY, BASE_URL, MODEL_NAME, MAX_TURNS
from tools import ALL_TOOLS
from emotion import EmotionState, parse_emotion_update, strip_emotion_block


def load_system_prompt() -> str:
    with open("prompts/system.md", "r") as f:
        return f.read()


def build_tool_schemas() -> list[dict]:
    return [tool.to_api_schema() for tool in ALL_TOOLS]


def find_tool(name: str):
    for tool in ALL_TOOLS:
        if tool.name == name:
            return tool
    return None


def build_system_message(base_prompt: str, emotion: EmotionState) -> str:
    """Combine base system prompt with current emotion state."""
    return base_prompt + "\n\n" + emotion.get_prompt_injection()


def process_emotion(text: str, emotion: EmotionState) -> str:
    """Parse emotion update from response, update state, return clean text."""
    if not text:
        return text
    parsed = parse_emotion_update(text)
    if parsed:
        print(
            f"[EMO_DEBUG] trigger: {parsed['trigger']} | "
            f"valence: {parsed['valence']} | "
            f"arousal: {parsed['arousal']} | "
            f"trust: {parsed['trust']}"
        )
        emotion.update(
            trigger=parsed["trigger"],
            valence_dir=parsed["valence"],
            arousal_dir=parsed["arousal"],
            trust_dir=parsed["trust"],
        )
    return strip_emotion_block(text)


def run():
    client = OpenAI(base_url=BASE_URL, api_key=OPENROUTER_API_KEY)
    base_prompt = load_system_prompt()
    tool_schemas = build_tool_schemas()
    emotion = EmotionState()
    messages = []

    print("Code Buddy (type 'exit' to quit)")
    print("-" * 40)

    while True:
        user_input = input("\nyou> ").strip()
        if not user_input or user_input.lower() in ("exit", "quit"):
            print("Bye!")
            break

        # Rebuild system message with current emotion state each turn
        system_msg = build_system_message(base_prompt, emotion)
        # Replace or insert system message at position 0
        if messages and messages[0].get("role") == "system":
            messages[0] = {"role": "system", "content": system_msg}
        else:
            messages.insert(0, {"role": "system", "content": system_msg})

        messages.append({"role": "user", "content": user_input})

        # Agentic loop: keep going until the model stops calling tools
        for turn in range(MAX_TURNS):
            response = client.chat.completions.create(
                model=MODEL_NAME,
                max_tokens=4096,
                tools=tool_schemas,
                messages=messages,
            )

            message = response.choices[0].message

            # Process emotion and get clean text
            clean_text = process_emotion(message.content, emotion)

            # Show clean text output
            if clean_text:
                print(f"\nassistant> {clean_text}")

            # Print emotion bar after text responses
            if message.content:
                print(emotion.format_bar())

            # Append the full assistant message (with emotion block intact for history)
            messages.append(message)

            # If no tool calls, this turn is done
            if not message.tool_calls:
                break

            # Execute each tool call and feed results back
            for tc in message.tool_calls:
                args = json.loads(tc.function.arguments)
                tool = find_tool(tc.function.name)
                if tool:
                    print(f"  [tool] {tc.function.name}({args})")
                    result = tool.call(**args)
                else:
                    result = f"[error] Unknown tool: {tc.function.name}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
        else:
            print(f"\n[max turns ({MAX_TURNS}) reached]")


if __name__ == "__main__":
    run()
