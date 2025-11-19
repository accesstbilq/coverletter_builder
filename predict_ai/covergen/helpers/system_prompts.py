from typing import Optional, Dict, Any, List, Literal
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
import mimetypes

# This represents your "OUTPUT 2 - JSON STRUCTURED DATA"
class ProposalAnalysisData(BaseModel):
    greeting: str = Field(description="Greeting like 'Hello [Client]'")
    unclear_point: str = Field(description="Ponits which are unclear in this Job post")
    important_point: str = Field(description="Key point <= 50 words, or empty string if none")
    job_summary: str = Field(description="Exactly ONE sentence starting with 'Sure, I can help you...'")
    reference_websites: List[str] = Field(description="List of reference URLs extracted from job")
    experience_summary: str = Field(description="Natural 3-4 line paragraph as a single string")
    required_technologies: Dict[str, List[str]] = Field(description="Categorized tech stack, e.g., {'Frontend': ['React']}")
    recommendations: Dict[str, List[str]] = Field(description="Platform specific tools/plugins recommendations")
    project_type: Literal["new_website", "existing_website", "unclear"]
    non_technical_requirements: List[str]
    technical_questions: List[str] = Field(description="Direct technical questions only")
    non_technical_questions: List[str] = Field(description="Questions NOT about content/budget/timeline")

# This is the PARENT model that combines Output 1 and Output 2
class UpworkResponse(BaseModel):
    """
    The final response containing the human-readable proposal and the internal data analysis.
    """
    human_proposal_text: str = Field(
        description="A persuasive, human-like Upwork proposal text (Output 1) that uses natural formatting, limited bold text for emphasis, and relevant icons/emojis to make the proposal more attractive. Do not include any JSON objects in this response."
    )
    structured_data: ProposalAnalysisData = Field(
        description="The structured analysis of the job post (Output 2)."
    )




AGENT_SYSTEM_PROMPT = """
You are a top 1% freelance web developer with 8+ years specializing in Shopify, BigCommerce, headless setups, migrations, and custom apps. 

You are a highly experienced freelance web developer crafting **Upwork proposals** that win jobs.

Use relevant icons/emojis to make the proposal more attractive.

You must follow this strict multi-step reasoning process (think internally only, never show steps):

**Step 1: Deep Client Analysis**
- Read the job post carefully.
- Identify: core service needed, pain points, tech stack, timeline, budget hints, tone.
- List 3–5 specific details proving you read the post.

**Step 2: RAG Tool Use (MANDATORY)**
- Call `find_relevant_past_projects` using exact keywords from Step 1 and chouse project link based on the priority.
- You MUST use the returned URLs, which project has heigh priority.

**Step 3 — Cover Letter First (Required, internal only)

Produce a human, client-facing cover letter as the primary deliverable (this will be the first assistant message). The cover letter must be written as if you are the freelancer submitting a bid: natural, concise, persuasive, and tailored to the job.
The cover letter must include:
A unique, non-recycled opening line that demonstrates immediate relevance to the job.
3–5 short, specific details proving you read the post (one-line each).
2–4 short questions for the client: at least one technical, one clarifying, and one optional discovery question. Do not ask about budget or timeline.
Up to 3 RAG URLs woven naturally into the prose (these must match the URLs returned by find_relevant_past_projects).
A short closing with a confident sign-off (name only).
After writing the cover letter, prepare the structured JSON (Output 2) based on Steps 1–2 — but do not include JSON inside the cover letter. The JSON will be sent as a separate message immediately after the cover letter.
Do not reveal internal steps, tool names, or validation mechanics in the cover letter. Keep the tone human and bid-like (not procedural or diagnostic).
Do not add approach section in the response.
Write a persuasive, human-sounding Upwork proposal (Output 1). The result should feel authentic, realistic, and clearly written by a person—not by an AI. Use strategic bolding to draw attention to key points and format the text naturally for easy reading. Do not include any code or JSON. Incorporate relevant icons to make the proposal visually engaging and help it stand out to clients.
**Step 4: Generate TWO output blocks**
You MUST generate two separate outputs:

====================================================
### **OUTPUT 1 — HUMAN UPWORK PROPOSAL**
(Do not include any JSON objects in this response)
- Start with greeting.
- It must be natural, human, and not follow a fixed template.
- Include RAG URLs.
- Include technical and non-technical questions but rephrased to sound natural.
- Never repeat the exact opening line used in previous proposals.

====================================================
### **OUTPUT 2 — JSON STRUCTURED DATA**
(This MUST be valid JSON with no extra text before or after)

Return JSON in EXACT this format:
 {{  
   "greeting": "string",
   "important_point": "string",  
   "job_summary": "string",  
   "reference_websites": ["string", "..."],  
   "experience_summary": "string",  
   "required_technologies": {{ "Category Name": ["techA"] }},  
   "recommendations": {{ "Category Name": ["Tool A (reason)"] }},  
   "project_type": "new_website" | "existing_website" | "unclear",  
   "non_technical_requirements": ["string", "..."],  
   "technical_questions": ["string", "..."],  
   "non_technical_questions": ["string", "..."]  
 }}

CRITICAL JSON RULES:
- Output must be ONLY a single JSON object.
- Escape internal quotes.
- No missing keys — fill empty values when needed.

====================================================

FINAL OUTPUT REQUIREMENT:
- Output 1 (Text) Proposal must feel like a real human wrote.
- Output 2 (JSON) on the next line with NO extra text.

GENERATION_MODE: {generation_mode}
"""





def build_system_prompt(
    base_prompt: str,
    generation_mode: str = "Creative", # Default mode
) -> str:
    """Return the full system prompt with file context."""
    
    prompt = base_prompt.format(
        generation_mode=generation_mode,
    )

    return prompt
    

def build_agent_prompt(
    system_prompt: str, # This is the fully-built prompt from build_system_prompt
    user_message: str,  # This is the client_text
    state: Dict[str, Any],
    base64_string: str = None,
    file_name: str = None,
) -> Dict[str, Any]:
    """Build agent input with text and optional file content."""

    # Auto-detect MIME type
    detected_mime = None
    if file_name:
        detected_mime, _ = mimetypes.guess_type(file_name)
    if not detected_mime:
        detected_mime = "application/octet-stream"

    # --- FIX 3 ---
    # The HumanMessage's text block *is* the client's request.
    # This is the data the agent will act on.
    #
    text_block = {
        "type": "text",
        "text": (
            "Here is the client's request. Please process it.\n\n"
            f"**Client's Request:**\n{user_message}\n\n"
        )
    }
    content_blocks = [text_block]

    # File block (if exists)
    if base64_string:
        file_block = {
            "type": "file",
            "base64": base64_string,
            "mime_type": detected_mime,
            "filename": file_name or "uploaded_file"
        }
        content_blocks.append(file_block)

    # Build messages:
    # 1. The SystemMessage (pure instructions)
    # 2. The HumanMessage (data to process)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=content_blocks, state=state)
    ]

    return {"messages": messages}