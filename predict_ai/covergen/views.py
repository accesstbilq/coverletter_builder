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
from .tools.extraction_tool import get_extraction_tool
from dotenv import load_dotenv
from langchain_core.tools import tool
from typing import Dict, List, Literal
from pydantic import BaseModel, Field
from langchain.agents import create_agent

import json


def chatbot_view(request: HttpRequest):
    """Render chatbot page"""
    return render(request, "coverletter.html")


# LOAD ENV VARIABLE
load_dotenv()

# Initialize langchain short memory
checkpointer = InMemorySaver()


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
    
    config = {"configurable": {"thread_id": session_id}}

    # ---- System prompts for both phases ----
    from .helpers.system_prompts import EXTRACTION_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT
    
    extraction_prompt = build_system_prompt(
        base_prompt=EXTRACTION_SYSTEM_PROMPT,
        file_name=file_name,
        file_base64=file_base64 or ""
    )
    
    response_prompt = build_system_prompt(
        base_prompt=RESPONSE_SYSTEM_PROMPT,
        file_name=file_name,
        file_base64=file_base64 or ""
    )

    state = {"data": ''}

    # ---- Build inputs ----
    extraction_input = build_agent_prompt(
        extraction_prompt, 
        client_text, 
        state, 
        file_base64, 
        file_name, 
        context_snippets
    )
    
    response_input = build_agent_prompt(
        response_prompt, 
        client_text, 
        state, 
        file_base64, 
        file_name, 
        context_snippets
    )

        # ---- Create model with structured output tool ----
    model = ChatOpenAI(model="gpt-4o", max_tokens=1024, temperature=0.1)
    agent = create_agent(model=model, tools=[get_extraction_tool], checkpointer=checkpointer)

    # ---- Streaming response with dual output ----
    response = StreamingHttpResponse(
        stream_generator(
            agent=agent,
            agent_input=response_input,
            config=config,
            extraction_input=extraction_input,
        ),
        content_type="text/event-stream",
        charset="utf-8",
    )
    return response
