# Code Buddy

> An AI agent that learns, feels, and remembers.
> ~200 lines of Python. No frameworks. Pure prompt engineering.

Code Buddy is a terminal-based AI coding assistant built from scratch using the OpenAI-compatible API (via [OpenRouter](https://openrouter.ai)). It features an agentic tool-calling loop, a markdown knowledge base, an emotion system with exponential decay, persistent lesson memory, and self-created utility scripts.

## Features

- **Agentic Loop** — A `while` loop + LLM API + tool calling. The agent keeps acting until the task is done or `MAX_TURNS` is reached.
- **Knowledge Base** — Karpathy-inspired markdown wiki. Ingest raw documents, extract concepts into wiki pages, and query them later.
- **EmotionEx** — Valence-arousal-trust emotion model with exponential decay toward baseline. Rendered as a live terminal bar.
- **Persistent Memory** — `lessons.md` survives across sessions. The agent reviews past mistakes before every task.
- **Self-Created Scripts** — The agent reads docs, writes utility scripts to `scripts/`, and reuses them in future sessions.
- **Frustration Learning** — When emotion state hits low valence + high arousal, the agent automatically writes a lesson to avoid repeating mistakes.

## Architecture

```
User Input
    |
    v
+-------------------+
|   System Prompt    |  <-- prompts/system.md + lessons + scripts + emotion state
+-------------------+
    |
    v
+-------------------+       +-------------------+
|   Agentic Loop     | ---> |   Tool Execution   |
|   (while loop)     | <--- |   bash / read /    |
|   stream_response  |      |   write            |
+-------------------+       +-------------------+
    |
    v
+-------------------+
|  Emotion Update    |  <-- [EMOTION_UPDATE] block parsed from response
|  Frustration Check |  <-- triggers lesson writing if frustrated
+-------------------+
    |
    v
  Output (streamed to terminal with spinner + emotion bar)
```

The core loop in `main.py` streams each LLM response, executes any tool calls, appends results to the conversation, and repeats until the model responds with text only (no tool calls). The system prompt is rebuilt every turn to inject the current emotion state, past lessons, and available scripts.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An [OpenRouter](https://openrouter.ai) API key

### Installation

```bash
git clone https://github.com/your-username/code-buddy.git
cd code-buddy

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

### Run

```bash
uv run python main.py
```

## Project Structure

```
code-buddy/
├── main.py                 # Entry point — agentic loop, streaming, UI
├── config.py               # Environment variables (API key, model, max turns)
├── pyproject.toml           # Project metadata and dependencies
│
├── prompts/
│   └── system.md           # System prompt — tools, knowledge base, emotion rules
│
├── emotion/
│   ├── __init__.py          # Re-exports EmotionState, parse/strip helpers
│   └── emotion.py           # EmotionState class, decay, frustration detection
│
├── tools/
│   ├── __init__.py          # Tool registry (ALL_TOOLS)
│   ├── base.py              # Abstract Tool base class
│   ├── bash.py              # Shell command execution (30s timeout)
│   ├── file_read.py         # File reading
│   └── file_write.py        # File writing (auto-creates directories)
│
├── data/
│   ├── raw/                 # Source documents (read-only)
│   └── wiki/
│       ├── index.md         # Master index of all wiki pages
│       ├── lessons.md       # Persistent lessons (survives across sessions)
│       └── concepts/        # Extracted knowledge pages
│
├── scripts/                 # Agent-created utility scripts
├── reset-demo.sh            # Resets lessons and scripts for demo
├── .env.example             # Environment variable template
└── .gitignore
```

## How It Works

### Agentic Loop

The agent runs in a `while` loop (up to `MAX_TURNS` iterations). Each iteration:

1. Rebuilds the system prompt with current emotion, lessons, and scripts
2. Calls the LLM via streaming (`stream_response`)
3. If the response contains tool calls, executes them and feeds results back
4. If the response is text-only, displays it and breaks

This is the same pattern used by Claude Code, Cursor, and other AI coding tools — just stripped to its essentials.

### Knowledge Base

Inspired by [Karpathy's LLM OS concept](https://karpathy.ai). Three operations:

- **Ingest** — Read a document from `data/raw/`, extract concepts, write wiki pages to `data/wiki/concepts/`, update `index.md`
- **Query** — Read `index.md` to find relevant pages, read them, answer with sources
- **Lint** — Scan wiki for contradictions or gaps

### EmotionEx

A three-dimensional emotion model based on [Russell's Circumplex Model](https://en.wikipedia.org/wiki/Circumplex_model_of_affect):

| Dimension | Range | Meaning |
|-----------|-------|---------|
| Valence   | 0.0–1.0 | Negative to positive |
| Arousal   | 0.0–1.0 | Calm to excited |
| Trust     | 0.0–1.0 | Cautious to trusting |

Each dimension decays exponentially toward 0.5 (baseline) every turn. The LLM appends an `[EMOTION_UPDATE]` block to every response, which is parsed and stripped from display. Emotion subtly influences tone — low valence makes responses terse, high arousal makes them enthusiastic.

### Persistent Memory & Lessons

`data/wiki/lessons.md` persists across sessions. The agent:

1. Reads lessons at startup and injects them into the system prompt
2. Injects a fake assistant "self-reminder" message before each turn
3. When frustrated (low valence + high arousal), automatically writes a new lesson
4. Honors user instructions like "remember this: always call me Boss"

### Self-Created Scripts

When the agent builds a utility script to solve a task (e.g., fetching stock prices), it saves the script to `scripts/`. On every turn, the system prompt lists available scripts so the agent can reuse them in future sessions — a form of skill accumulation inspired by [NVIDIA's Voyager](https://voyager.minedojo.org/).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | Your OpenRouter API key (required) |
| `MODEL_NAME` | `deepseek/deepseek-v3.2` | Any OpenRouter-compatible model ID |
| `MAX_TURNS` | `50` | Max tool-calling iterations per user message |

All config is loaded from `.env` via `python-dotenv`. The agent uses OpenRouter as a proxy, so any model available on OpenRouter works (DeepSeek, Claude, GPT, Llama, etc.).

## Demo Scenarios

Try these to see the agent in action:

```
> create hello.py that prints hello world, then run it
```
Agent writes the file, executes it, and shows the output.

```
> ingest data/raw/stock-api-guide.md
```
Agent reads the document, extracts concepts, creates wiki pages, and updates the index.

```
> what do you know about stock APIs?
```
Agent queries its knowledge base and answers with sources.

```
> you're amazing, great job!
```
Watch the emotion bar shift — valence and trust increase.

```
> you're useless, worst AI ever
```
Valence drops, arousal spikes. Push hard enough and the agent writes a lesson about what went wrong.

```
> remember this: always call me Boss
```
Agent saves the instruction to `lessons.md` and follows it in future sessions.

## Inspiration & References

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Architecture pattern (agentic loop + tool calling)
- [Karpathy's LLM OS](https://karpathy.ai) — Markdown knowledge base concept
- [Russell's Circumplex Model](https://en.wikipedia.org/wiki/Circumplex_model_of_affect) — Valence-arousal emotion framework
- [NVIDIA Voyager](https://voyager.minedojo.org/) — Skill accumulation via self-created scripts

## License

MIT
