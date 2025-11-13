# tools/file_tools.py
import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

# --------------------------------------------------------------------------- #
# 1. Where the files are saved (same as in process_uploaded_file)
# --------------------------------------------------------------------------- #
UPLOAD_ROOT = Path("media") / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# 2. Helper – get the saved file path for a session
# --------------------------------------------------------------------------- #
def _get_file_path_from_checkpoint(config: RunnableConfig) -> Path | None:
    """
    Extract the saved file path from the LangChain checkpoint.
    The checkpointer is stored in config['configurable']['checkpointer']
    """
    try:
        # 1. Get checkpointer from config
        checkpointer = config["configurable"]["checkpointer"]

        # 2. Get current thread_id
        thread_id = config["configurable"]["thread_id"]

        # 3. Load the latest checkpoint for this thread
        checkpoint_tuple = checkpointer.get_tuple({"configurable": {"thread_id": thread_id}})
        if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
            return None

        # 4. Extract saved file path
        state = checkpoint_tuple.checkpoint.get("state", {})
        file_path_str = state.get("uploaded_file_path")
        if not file_path_str:
            return None

        file_path = Path(file_path_str)
        return file_path if file_path.is_file() else None

    except Exception as e:
        print(f"[Tool] Error reading checkpoint: {e}")
        return None


# --------------------------------------------------------------------------- #
# 3. Tool – search inside the uploaded file
# --------------------------------------------------------------------------- #
@tool
def search_uploaded_file(query: str, config: RunnableConfig) -> str:
    """Search inside the uploaded file."""
    file_path = _get_file_path_from_checkpoint(config)
    if not file_path:
        return "No file uploaded in this session."

    text = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    relevant = []

    for i, line in enumerate(lines):
        if query.lower() in line.lower():
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            relevant.extend(lines[start:end])

    if relevant:
        return "Found:\n\n" + "\n".join(relevant[:50])
    else:
        return f"No matches. Preview:\n\n{text[:1500]}"

@tool
def read_entire_file(config: RunnableConfig) -> str:
    """Return full file content."""
    file_path = _get_file_path_from_checkpoint(config)
    if not file_path:
        return "No file uploaded."

    text = file_path.read_text(encoding="utf-8", errors="ignore")
    return f"File: {file_path.name}\n\n{text}"

@tool
def get_file_info(config: RunnableConfig) -> str:
    """File metadata."""
    file_path = _get_file_path_from_checkpoint(config)
    if not file_path:
        return "No file uploaded."

    text = file_path.read_text(encoding="utf-8", errors="ignore")
    return f"""File Info:
- Name: {file_path.name}
- Size: {len(text)} chars
- Lines: {len(text.splitlines())}
- Words: {len(text.split())}
"""