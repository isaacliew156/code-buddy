import json
import os
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


LESSONS_PATH = "data/wiki/lessons.md"


def load_lessons() -> str:
    """Read past lessons if the file exists."""
    if os.path.isfile(LESSONS_PATH):
        with open(LESSONS_PATH, "r") as f:
            return f.read().strip()
    return ""


def build_system_message(base_prompt: str, emotion: EmotionState) -> str:
    """Combine base system prompt with lessons and current emotion state."""
    parts = [base_prompt]
    lessons = load_lessons()
    if lessons:
        parts.append(
            f"--- CRITICAL: PAST MISTAKES (DO NOT REPEAT) ---\n"
            f"You MUST review these lessons BEFORE taking any action. "
            f"These are mistakes you made before. Do NOT repeat them.\n\n"
            f"{lessons}"
        )
    parts.append(emotion.get_prompt_injection())
    return "\n\n".join(parts)


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


LESSON_PROMPT = (
    "You seem frustrated by repeated failures. Take a moment to reflect. "
    "Use file_write to append a lesson to data/wiki/lessons.md with this format:\n\n"
    "## Lesson [today's date]\n"
    "**Trigger:** what went wrong\n"
    "**Learning:** what to do differently next time\n"
    "**Context:** relevant details\n\n"
    "Append to the file, do not overwrite existing content."
)


def check_frustration(emotion: EmotionState, messages: list) -> bool:
    """Inject a lesson-writing prompt if the agent is frustrated."""
    emotion.check_frustration_reset()
    if emotion.is_frustrated() and not emotion.frustration_triggered:
        emotion.frustration_triggered = True
        messages.append({"role": "user", "content": LESSON_PROMPT})
        print("[LESSON] Frustration detected — asking agent to write a lesson.")
        return True
    return False


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

        # Inject a fake assistant self-reminder about past lessons
        lessons = load_lessons()
        if lessons:
            messages.append({
                "role": "assistant",
                "content": (
                    "Before I proceed, let me check my past lessons... "
                    f"I previously learned:\n{lessons}\n"
                    "I will apply these lessons to this task."
                ),
            })

        messages.append({"role": "user", "content": user_input})

        print("[DEBUG PROMPT]", messages[0]["content"][-500:])

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

            # Append the full assistant message (with emotion block intact for history)
            messages.append(message)

            # Check for frustration and inject lesson prompt if needed
            if not message.tool_calls:
                # Only show emotion bar on final response (no tool calls)
                if message.content:
                    print(emotion.format_bar())
                if check_frustration(emotion, messages):
                    # Continue the loop so the agent processes the lesson prompt
                    continue
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
