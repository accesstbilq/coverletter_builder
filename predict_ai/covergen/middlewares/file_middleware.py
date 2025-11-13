from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def inject_file_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Inject context about files user has uploaded this session."""
    # Read from State: get uploaded files metadata
    uploaded_files = request.state.get("uploaded_files", [])  

    if uploaded_files:
        # Build context about available files
        file_descriptions = []
        for file in uploaded_files:
            file_descriptions.append(
                f"- {file['name']} ({file['type']}): {file['summary']}"
            )

        file_context = f"""Files you have access to in this conversation:
        {chr(10).join(file_descriptions)}

        Reference these files when answering questions."""
        
        print("file_context ################", file_context)

        # Inject file context before recent messages
        messages = [  
            *request.messages,
            {"role": "user", "content": file_context},
        ]
        request = request.override(messages=messages)  

    return handler(request)
