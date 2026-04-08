from abc import ABC, abstractmethod


class Tool(ABC):
    """Base class for all tools."""

    name: str
    description: str
    input_schema: dict

    def to_api_schema(self) -> dict:
        """Convert to the OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    @abstractmethod
    def call(self, **kwargs) -> str:
        """Execute the tool and return a string result."""
        ...
