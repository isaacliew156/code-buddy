import json
import os
import random
import sys
import threading
import time
from openai import OpenAI
from config import OPENROUTER_API_KEY, BASE_URL, MODEL_NAME, MAX_TURNS
from tools import ALL_TOOLS
from emotion import EmotionState, parse_emotion_update, strip_emotion_block


# --- ANSI color helpers ---
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"

SEPARATOR = f"{DIM}{'─' * 48}{RESET}"

TOOL_ICONS = {
    "bash": "\u26a1",
    "file_read": "\U0001f4c4",
    "file_write": "\u270f\ufe0f",
}

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

THINKING_MESSAGES = [
    "Thinking...",
    "Brewing coffee...",
    "Consulting the matrix...",
    "Reading the docs...",
    "Asking my brain cells...",
    "Compiling thoughts...",
    "Crunching numbers...",
    "Warming up neurons...",
    "Downloading intelligence...",
    "Channeling inner Karpathy...",
    "Summoning the LLM gods...",
    "Petting virtual cats...",
    "Calculating vibes...",
    "Loading personality.dll...",
    "Reticulating splines...",
    "Defragmenting brain...",
    "sudo think harder...",
    "git pull wisdom...",
    "pip install brainpower...",
    "Consulting Stack Overflow...",
    "Rolling a d20 for intelligence...",
    "Asking ChatGPT... jk...",
    "Converting caffeine to code...",
    "Searching for meaning...",
    "Tuning hyperparameters...",
    "Running gradient descent on your question...",
    "Allocating brain memory...",
    "Spinning up attention heads...",
    "Tokenizing your soul...",
    "Backpropagating thoughts...",
]


class Spinner:
    """Animated spinner for waiting on API calls."""

    def __init__(self, message="Thinking..."):
        self.message = message
        self._stop = threading.Event()
        self._thread = None

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
            sys.stdout.write(f"\r{DIM}{frame} {self.message}{RESET}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.08)
        # Clear the spinner line
        sys.stdout.write("\r" + " " * (len(self.message) + 4) + "\r")
        sys.stdout.flush()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()


def fmt_tool_call(name: str, args: dict) -> str:
    """Format a tool call for compact display."""
    icon = TOOL_ICONS.get(name, "\U0001f527")
    if name == "bash":
        detail = args.get("command", "")
    elif name == "file_read":
        detail = args.get("path", "")
    elif name == "file_write":
        detail = args.get("path", "")
    else:
        detail = str(args)
    return f"  {YELLOW}[tool]{RESET} {icon} {name} \u2192 {detail}"


def fmt_tool_result(name: str, result: str) -> str:
    """Format a tool result with truncation rules."""
    if name == "file_read":
        lines = result.splitlines()
        if len(lines) > 3:
            preview = "\n".join(lines[:3])
            return f"  {DIM}[result] {preview}\n  ... ({len(lines) - 3} more lines){RESET}"
        return f"  {DIM}[result] {result}{RESET}"
    else:
        display = result if len(result) <= 1500 else result[:1500] + "... (truncated)"
        return f"  {DIM}[result] {display}{RESET}"


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


SCRIPTS_DIR = "scripts"


def load_scripts() -> str:
    """List all files in the scripts/ directory."""
    if not os.path.isdir(SCRIPTS_DIR):
        return ""
    files = sorted(os.listdir(SCRIPTS_DIR))
    if not files:
        return ""
    return "\n".join(f"- scripts/{f}" for f in files)


def build_system_message(base_prompt: str, emotion: EmotionState) -> str:
    """Combine base system prompt with lessons, scripts, and current emotion state."""
    parts = [base_prompt]
    lessons = load_lessons()
    if lessons:
        parts.append(
            f"--- CRITICAL: PAST MISTAKES (DO NOT REPEAT) ---\n"
            f"You MUST review these lessons BEFORE taking any action. "
            f"These are mistakes you made before. Do NOT repeat them.\n\n"
            f"{lessons}"
        )
    scripts = load_scripts()
    if scripts:
        parts.append(
            f"--- AVAILABLE SCRIPTS ---\n"
            f"These utility scripts exist and can be reused:\n{scripts}"
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
        print(f"{BOLD}{RED}[LESSON]{RESET} Frustration detected — asking agent to write a lesson.")
        return True
    return False


EMOTION_BLOCK_START = "[EMOTION_UPDATE]"
EMOTION_BLOCK_END = "[/EMOTION_UPDATE]"


def stream_response(client, model, messages, tool_schemas, spinner):
    """Stream a chat completion, returning (full_text, tool_calls_list).

    Shows spinner until first token arrives, then streams text char by char.
    Suppresses [EMOTION_UPDATE]...[/EMOTION_UPDATE] blocks from terminal output.
    Accumulates tool calls from deltas.
    """
    stream = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        tools=tool_schemas,
        messages=messages,
        stream=True,
    )

    full_text = ""
    tool_calls_acc = {}  # index -> {id, name, arguments}
    started_text = False
    in_emotion_block = False
    # Buffer for detecting the start of [EMOTION_UPDATE]
    # We buffer chars that could be the beginning of the tag
    pending = ""

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if not delta:
            continue

        # Stream text content
        if delta.content:
            full_text += delta.content

            if not started_text:
                spinner.stop()
                sys.stdout.write(f"\n{CYAN}assistant>{RESET} ")
                started_text = True

            # Process each character for emotion block detection
            for ch in delta.content:
                if in_emotion_block:
                    # Silently consume until we see the end tag
                    pending += ch
                    if pending.endswith(EMOTION_BLOCK_END):
                        in_emotion_block = False
                        pending = ""
                else:
                    pending += ch
                    # Check if pending could be the start of the tag
                    if EMOTION_BLOCK_START.startswith(pending):
                        # Still a potential match, keep buffering
                        continue
                    elif EMOTION_BLOCK_START in pending:
                        # Tag found — print everything before it, enter block mode
                        before = pending[:pending.index(EMOTION_BLOCK_START)]
                        if before:
                            sys.stdout.write(before)
                            sys.stdout.flush()
                        in_emotion_block = True
                        # Keep the rest after the start tag in pending
                        pending = pending[pending.index(EMOTION_BLOCK_START) + len(EMOTION_BLOCK_START):]
                    else:
                        # No match possible — flush pending to terminal
                        sys.stdout.write(pending)
                        sys.stdout.flush()
                        pending = ""

        # Accumulate tool calls across chunks
        if delta.tool_calls:
            if not started_text:
                spinner.stop()
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {
                        "id": tc_delta.id or "",
                        "name": "",
                        "arguments": "",
                    }
                if tc_delta.id:
                    tool_calls_acc[idx]["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tool_calls_acc[idx]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments

    # Stop spinner in case stream ended without text or tool calls
    spinner.stop()

    # Flush any remaining pending text (not part of emotion block)
    if pending and not in_emotion_block:
        sys.stdout.write(pending)
        sys.stdout.flush()

    if started_text:
        sys.stdout.write("\n")
        sys.stdout.flush()

    # Convert accumulated tool calls to a structured list
    tool_calls = []
    for idx in sorted(tool_calls_acc.keys()):
        tool_calls.append(tool_calls_acc[idx])

    return full_text, tool_calls


LOGO = r"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣀⣀⠀⠀⣀⡠⠴⠒⠚⠉⠉⠓⠒⠦⣄⣶⠒⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡷⢬⣉⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠠⡌⠻⣧⢻⣧⣤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣖⠗⡋⢹⠀⠀⢰⡄⠀⠀⢸⣷⡀⠀⣠⠽⣆⢼⣇⢻⣸⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡜⣡⣶⢋⡏⠙⢢⣏⣇⠀⠀⠈⣇⡵⡏⠀⠀⢹⡏⢾⣿⠃⢿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⢿⢻⣏⣿⡇⡄⣾⠀⠹⡄⠄⠀⡇⠀⠹⣤⠈⠹⣿⣾⢸⠀⢘⣷⣄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣴⣯⣿⣽⣿⣷⢸⡗⠦⣄⡹⣼⣄⣿⣴⠛⠹⡄⡇⣿⣿⠾⠚⢹⢿⢽⣽⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⣞⣾⣿⢿⣯⢻⢻⡴⠞⠁⠈⠻⣿⣌⡉⠓⣿⣰⡿⠀⠀⠀⠸⡜⡾⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⣡⠊⢸⣹⠁⠈⠙⣾⡄⠁⠀⢰⠛⠉⠉⠉⢳⣀⣿⣿⠃⠀⠀⣀⣀⣧⣿⡞⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠋⡴⠁⠀⠸⢿⣤⣤⣤⣹⣿⣷⣶⣾⣷⣶⣶⣺⣋⣽⣿⣷⠶⠟⠛⠋⢧⠀⠀⠸⡜⣷⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡜⠁⡰⠁⠀⠀⢠⡿⠀⠀⠀⠉⠉⠉⠙⢻⡟⣹⣿⠃⣿⠋⠁⠀⠀⠀⠀⠀⠸⡄⠀⠀⢣⠹⣧⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠏⡀⢠⠇⠀⠀⢠⡿⠁⠀⠀⠀⠀⣤⣶⡴⠚⢻⠡⣸⠀⢹⣆⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠸⡄⢻⣇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡏⣼⠁⢸⠀⠀⠀⣾⠃⠀⠀⠀⠀⠀⢻⣿⣧⣀⣬⠋⠁⠀⣠⣿⣶⣆⠀⠀⠀⠀⠀⡇⠀⠀⠀⡇⠈⣿⡀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣸⣿⠀⡇⠀⢰⣸⡟⠀⠀⠀⣀⣠⠴⠚⣟⣻⣧⣯⣗⣤⣾⣿⣿⡿⠋⠀⠀⠀⠀⣸⣤⠀⠀⠀⡇⡆⢻⠃⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡿⢸⡀⣇⠀⣸⣿⡁⠀⣾⣻⡁⣀⣤⣶⠟⠋⠉⠛⢿⣋⣻⡏⠉⠀⠀⠀⠀⠀⢰⣿⡇⠀⠀⠀⣷⡇⣸⡄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠿⠇⠀⢧⢸⠀⣿⡿⠇⠀⠈⠛⠛⠋⠉⠀⠀⠀⠀⠀⡟⠀⣿⠇⠀⠀⠀⠀⠀⢠⣿⣿⡇⠀⠀⣰⡿⣧⣿⠃⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣄⣹⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⡇⠀⣿⠀⠀⠀⠀⠀⠀⣸⡿⢸⠁⢠⣾⠋⢰⣿⡏⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠛⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣶⣶⡿⠀⠀⠀⠀⠀⠀⠉⠁⢸⣶⡟⠁⠀⠾⠟⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""


def run():
    client = OpenAI(base_url=BASE_URL, api_key=OPENROUTER_API_KEY)
    base_prompt = load_system_prompt()
    tool_schemas = build_tool_schemas()
    emotion = EmotionState()
    messages = []

    print(LOGO)
    print("         \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
    print("         \u2551           \U0001f916 Code Buddy              \u2551")
    print("         \u2551     ~ Your Coding Friend \u55b5 Miao     \u2551")
    print("         \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d")
    print()
    print("Code Buddy (type 'exit' to quit)")
    print(SEPARATOR)

    while True:
        user_input = input(f"\n{GREEN}you>{RESET} ").strip()
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

        # Agentic loop: keep going until the model stops calling tools
        for turn in range(MAX_TURNS):
            spinner = Spinner(random.choice(THINKING_MESSAGES))
            spinner.start()

            full_text, tool_calls = stream_response(
                client, MODEL_NAME, messages, tool_schemas, spinner
            )

            # Process emotion from the full text
            clean_text = process_emotion(full_text, emotion)

            # Build assistant message for history
            assistant_msg = {"role": "assistant", "content": full_text or ""}
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls
                ]
            messages.append(assistant_msg)

            # If no tool calls, this turn is done
            if not tool_calls:
                if full_text:
                    print(emotion.format_bar())
                if check_frustration(emotion, messages):
                    continue
                break

            # Execute each tool call and feed results back
            for tc in tool_calls:
                args = json.loads(tc["arguments"])
                tool = find_tool(tc["name"])
                if tool:
                    print(fmt_tool_call(tc["name"], args))
                    result = tool.call(**args)
                else:
                    result = f"[error] Unknown tool: {tc['name']}"
                print(fmt_tool_result(tc["name"], result))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )
        else:
            print(f"\n[max turns ({MAX_TURNS}) reached]")

        print(SEPARATOR)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nBye!")
