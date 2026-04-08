import os
from tools.base import Tool


class FileReadTool(Tool):
    name = "file_read"
    description = "Read the contents of a file."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file to read.",
            }
        },
        "required": ["path"],
    }

    def call(self, **kwargs) -> str:
        path = kwargs["path"]
        if not os.path.isfile(path):
            return f"[error] File not found: {path}"
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            return f"[error] {e}"
