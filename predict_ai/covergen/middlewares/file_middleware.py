from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from ..helpers.system_prompts import UpworkResponse
import mimetypes

@wrap_model_call
def inject_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """
    Inject context about files, categories, and snippets user has provided this session.
    Handles payload keys: 'files', 'context_snippets', 'categories'.
    """
    print("[TEST Inject Context]")
    # 1. Read from State using the specific keys from your payload
    # We look for 'files', defaulting to empty list if not found.
    raw_files = request.state.get("uploaded_files", [])
    base64_string = request.state.get("base64_string", "")
    file_name = request.state.get("file_name", None)
    context_snippets = request.state.get("context_snippets", [])
    categories = request.state.get("categories", [])

    context_parts = []

    # 2. Process Categories
    if categories:
        # Handle if categories is a list ["A", "B"] or a string "A, B"
        cat_str = ", ".join(categories) if isinstance(categories, list) else str(categories)
        context_parts.append(f"Active Categories/Tags: {cat_str}")

    # 3. Process Files
    # safeguard: ensure raw_files is a list (metadata) and not raw binary bytes
    if raw_files and isinstance(raw_files, list):
        file_descriptions = []
        for file in raw_files:
            # Only process if it looks like a dictionary (metadata)
            if isinstance(file, dict):
                name = file.get('name', 'Unknown File')
                f_type = file.get('type', 'N/A')
                summary = file.get('summary', 'No summary available.')
                file_descriptions.append(f"- {name} ({f_type}): {summary}")
            elif hasattr(file, 'filename'): 
                # Handle objects like UploadFile that have attributes but aren't dicts
                file_descriptions.append(f"- {file.filename}")
        
        if file_descriptions:
            files_str = "Files uploaded:\n" + "\n".join(file_descriptions)
            context_parts.append(files_str)
    
    # Note: If 'files' was raw binary data (bytes), we intentionally skipped it above 
    # to prevent injecting illegible binary characters into the LLM prompt.

    # 4. Process Context Snippets (URLs, Filenames, or Text)
    if context_snippets:
        snippet_descriptions = []
        for i, snip in enumerate(context_snippets, 1):
            # Handle if snippet is a string (URL/filename) or a dictionary object
            content = snip if isinstance(snip, str) else snip.get('content', str(snip))
            snippet_descriptions.append(f"{i}. {content}")
            
        snippets_str = "Relevant Sources/Context:\n" + "\n".join(snippet_descriptions)
        context_parts.append(snippets_str)


    if base64_string:
        # Auto-detect MIME type
        detected_mime = None
        if file_name:
            detected_mime, _ = mimetypes.guess_type(file_name)
        if not detected_mime:
            detected_mime = "application/octet-stream"

        snippets_str = "Files uploaded:\n" + "\n".join(base64_string) + "mime_type: " + detected_mime + "\n"
        context_parts.append(snippets_str)
    print("CONETXT PART *******", context_parts, base64_string)
    # 5. Inject into Messages
    if context_parts:
        # Join all parts with double newlines for distinct separation
        full_context_block = "\n\n".join(context_parts)
        
        final_system_instruction = (
            f"CONTEXT INFORMATION:\n"
            f"====================\n"
            f"{full_context_block}\n"
            f"====================\n"
            f"Please use the context above to answer the user's request."
        )

        print("### Injected Context ###\n", final_system_instruction)

        # Inject as a system message
        messages = [
            *request.messages,
            {"role": "system", "content": final_system_instruction}, 
        ]

        print("message in middlware£££££££££££3333333", messages)
        request = request.override(messages=messages)

    return handler(request)


@wrap_model_call
def state_based_output(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Select output format based on State."""
    # request.messages is a shortcut for request.state["messages"]

    request = request.override(response_format=UpworkResponse) 

    return handler(request)
