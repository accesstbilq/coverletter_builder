from django.shortcuts import render
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import StreamingHttpResponse
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from .helpers.system_prompts import build_system_prompt, build_agent_prompt
from .helpers.stream_helper import stream_generator
from .tools.extraction_tool import extract_cover_letter_info
from .tools.retrieval_tool import find_relevant_past_projects
from .middlewares.file_middleware import inject_context, state_based_output
from dotenv import load_dotenv
from langchain.agents import create_agent
import json
from django.conf import settings



CSV_FILE_PATH = settings.BASE_DIR / "active_projects_2025-11-12_15-24-13.csv"
# LOAD ENV VARIABLE
load_dotenv()

# Initialize langchain short memory
checkpointer = InMemorySaver()

def chatbot_view(request: HttpRequest):
    """Render chatbot page"""
    return render(request, "coverletter.html")


@csrf_exempt
@require_POST
def generate_cover_letter(request: HttpRequest):
    """Handle chat with dual output: JSON structure + formatted response."""
    
    # ---- Parse request ----
    payload = json.loads(request.body)
    session_id = payload.get("session_id")
    client_text = payload.get("client_text")
    context_snippets = payload.get("context_snippets")
    files = payload.get("files")
    generation_mode = payload.get("generation_mode", "Creative") 
    categories = payload.get("selected_categories")


    config = {"configurable": {"thread_id": session_id}}

    # ---- System prompt (New single-prompt logic) ----
    from .helpers.system_prompts import AGENT_SYSTEM_PROMPT
    
    agent_prompt = build_system_prompt(
        base_prompt=AGENT_SYSTEM_PROMPT,
        generation_mode=generation_mode,
    )

    state = {"categories": categories, "context_snippets": context_snippets, "uploaded_files": files}

    # ---- Build single agent input ----
    agent_input = build_agent_prompt(
        agent_prompt, 
        client_text, 
        state,
    )
    
    # ---- Create model with BOTH tools ----
    model = ChatOpenAI(model="gpt-5.1", temperature=0.1)
    
    # The agent now has access to both tools
    tools = [extract_cover_letter_info, find_relevant_past_projects]
    
    agent = create_agent(model=model, tools=tools, middleware=[inject_context, state_based_output], checkpointer=checkpointer)

    # ---- Streaming response with dual output ----
    response = StreamingHttpResponse(
        stream_generator(
            agent=agent,
            agent_input=agent_input,
            config=config
        ),
        content_type="text/event-stream",
        charset="utf-8",
    )
    return response