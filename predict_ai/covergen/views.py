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
from .tools.retrieval_tool import find_relevant_past_projects # <-- IMPORT NEW TOOL
from dotenv import load_dotenv
from langchain.agents import create_agent
import json

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
    file_base64 = payload.get("file_base64")
    file_name = payload.get("file_name")
    generation_mode = payload.get("generation_mode", "Creative") 
    categories = payload.get("categories")


    config = {"configurable": {"thread_id": session_id}}

    # ---- System prompt (New single-prompt logic) ----
    from .helpers.system_prompts import AGENT_SYSTEM_PROMPT
    
    agent_prompt = build_system_prompt(
        base_prompt=AGENT_SYSTEM_PROMPT,
        file_name=file_name,
        file_base64=file_base64 or "",
        generation_mode=generation_mode,
    )

    state = {"data": ''}

    # ---- Build single agent input ----
    agent_input = build_agent_prompt(
        agent_prompt, 
        client_text, 
        state, 
        file_base64, 
        file_name, 
        context_snippets,
        categories
    )
    
    # ---- Create model with BOTH tools ----
    model = ChatOpenAI(model="gpt-5.1", temperature=0.1)
    
    # The agent now has access to both tools
    tools = [extract_cover_letter_info, find_relevant_past_projects]
    
    agent = create_agent(model=model, tools=tools, checkpointer=checkpointer)

    # ---- Streaming response with dual output ----
    response = StreamingHttpResponse(
        stream_generator(
            agent=agent,
            agent_input=agent_input, # Pass the single input
            config=config
            # No longer need extraction_input
        ),
        content_type="text/event-stream",
        charset="utf-8",
    )
    return response