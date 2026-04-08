import re

BASELINE = 0.5
DECAY_RATE = 0.05

INTENSITY_MAP = {
    "+strong": 0.20,
    "+moderate": 0.10,
    "+slight": 0.05,
    "neutral": 0.0,
    "-slight": -0.05,
    "-moderate": -0.10,
    "-strong": -0.20,
}

EMOTION_FACES = {
    (True, True): "\U0001f604",    # high valence, high arousal -> excited
    (True, False): "\U0001f60a",   # high valence, low arousal -> calm happy
    (False, True): "\U0001f623",   # low valence, high arousal -> frustrated
    (False, False): "\U0001f614",  # low valence, low arousal -> sad
}


def clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


class EmotionState:
    def __init__(self, valence: float = 0.5, arousal: float = 0.5, trust: float = 0.5):
        self.valence = clamp(valence)
        self.arousal = clamp(arousal)
        self.trust = clamp(trust)
        self.emotion_log: list[dict] = []
        self.frustration_triggered = False

    def decay(self):
        """Exponential decay toward baseline each turn."""
        self.valence += (BASELINE - self.valence) * DECAY_RATE
        self.arousal += (BASELINE - self.arousal) * DECAY_RATE
        self.trust += (BASELINE - self.trust) * DECAY_RATE

    def update(self, trigger: str, valence_dir: str, arousal_dir: str, trust_dir: str):
        """Apply an emotion update from parsed directions."""
        self.decay()
        self.valence = clamp(self.valence + INTENSITY_MAP.get(valence_dir, 0))
        self.arousal = clamp(self.arousal + INTENSITY_MAP.get(arousal_dir, 0))
        self.trust = clamp(self.trust + INTENSITY_MAP.get(trust_dir, 0))
        self.emotion_log.append({
            "trigger": trigger,
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "trust": round(self.trust, 3),
        })

    def is_frustrated(self) -> bool:
        """Frustration = low valence + high arousal."""
        # TODO: raise threshold back after testing
        return self.valence < 0.45 and self.arousal > 0.4

    def check_frustration_reset(self):
        """Reset frustration flag when valence recovers above 0.4."""
        if self.frustration_triggered and self.valence > 0.4:
            self.frustration_triggered = False

    def get_face(self) -> str:
        return EMOTION_FACES[(self.valence >= 0.5, self.arousal >= 0.5)]

    def describe_state(self) -> str:
        """Human-readable description of current emotional state."""
        parts = []

        if self.valence > 0.7:
            parts.append("feeling positive")
        elif self.valence < 0.3:
            parts.append("feeling negative")
        else:
            parts.append("emotionally neutral")

        if self.arousal > 0.7:
            parts.append("highly engaged")
        elif self.arousal < 0.3:
            parts.append("calm and relaxed")

        if self.trust > 0.7:
            parts.append("high trust in user")
        elif self.trust < 0.3:
            parts.append("cautious toward user")

        return "; ".join(parts) if parts else "baseline state"

    def get_prompt_injection(self) -> str:
        """Generate emotion context block for system prompt injection."""
        lines = [
            "[CURRENT_EMOTION_STATE]",
            f"valence: {self.valence:.2f} | arousal: {self.arousal:.2f} | trust: {self.trust:.2f}",
            f"description: {self.describe_state()}",
        ]
        recent = self.emotion_log[-3:]
        if recent:
            lines.append("recent triggers:")
            for entry in recent:
                lines.append(
                    f"  - \"{entry['trigger']}\" -> "
                    f"v={entry['valence']} a={entry['arousal']} t={entry['trust']}"
                )
        lines.append("[/CURRENT_EMOTION_STATE]")
        return "\n".join(lines)

    def format_bar(self) -> str:
        """Render the terminal emotion bar."""
        face = self.get_face()

        def bar(val: float) -> str:
            filled = round(val * 7)
            return "\u2588" * filled + "\u2591" * (7 - filled)

        return (
            f"[EMO] {face} "
            f"valence: {bar(self.valence)} {self.valence:.2f} | "
            f"arousal: {bar(self.arousal)} {self.arousal:.2f} | "
            f"trust: {bar(self.trust)} {self.trust:.2f}"
        )


def parse_emotion_update(text: str) -> dict | None:
    """Extract [EMOTION_UPDATE] block from LLM response text.

    Expected format:
    [EMOTION_UPDATE]
    trigger: <description>
    valence: <direction>
    arousal: <direction>
    trust: <direction>
    [/EMOTION_UPDATE]
    """
    match = re.search(
        r"\[EMOTION_UPDATE\]\s*\n(.*?)\[/EMOTION_UPDATE\]",
        text,
        re.DOTALL,
    )
    if not match:
        return None

    block = match.group(1)
    result = {}
    for line in block.strip().splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip().lower()] = val.strip()

    required = {"trigger", "valence", "arousal", "trust"}
    if not required.issubset(result.keys()):
        return None

    return result


def strip_emotion_block(text: str) -> str:
    """Remove the [EMOTION_UPDATE] block from display text."""
    return re.sub(
        r"\[EMOTION_UPDATE\].*?\[/EMOTION_UPDATE\]\s*",
        "",
        text,
        flags=re.DOTALL,
    ).strip()
