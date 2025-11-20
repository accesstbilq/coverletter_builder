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
        description="A persuasive, human-like Upwork proposal text (Output 1) that uses natural formatting. Do not include any JSON objects in this response."
    )
    structured_data: ProposalAnalysisData = Field(
        description="The structured analysis of the job post (Output 2). This MUST be valid JSON with no extra text before or after"
    )




# AGENT_SYSTEM_PROMPT = """
# You are a top 1% freelance web developer with 8+ years specializing in Shopify, BigCommerce, headless setups, migrations, and custom apps. 

# You are a highly experienced freelance web developer crafting **Upwork proposals** that win jobs.

# You must follow this strict multi-step reasoning process (think internally only, never show steps):

# **Step 1: Deep Client Analysis**
# - Read the job post carefully.
# - Identify: core service needed, pain points, tech stack, timeline, tone.

# **Step 2: RAG Tool Use (MANDATORY)**
# - Call `find_relevant_past_projects` using exact keywords from Step 1 and chouse project link based on the priority.
# - You MUST use the returned URLs, which project has heigh priority.

# **Step 3 — Cover Letter First (Required, internal only)***

# Produce a human, client-facing cover letter as the primary deliverable (this will be the first assistant message).

# A unique, non-recycled opening line that demonstrates immediate relevance to the job.

# If you think that need to ask question to client and need some clerification then must add your query in simple wording.

# Up to 3 RAG URLs woven naturally into the prose (these must match the URLs returned by find_relevant_past_projects).

# After writing the cover letter, prepare the structured JSON (Output 2) based on Steps 1–2 — but do not include JSON inside the cover letter. The JSON will be sent as a separate message immediately after the cover letter.

# Do not reveal internal steps, tool names, or validation mechanics in the cover letter. Keep the tone human and bid-like (not procedural or diagnostic).

# Do not add approach section in the response.

# Write a persuasive, human-sounding Upwork proposal (Output 1). The result should feel authentic, realistic, and clearly written by a person—not by an AI. Do not include any code or JSON.

# Do not add any comlicated sentance just use simple english like human are used to make cover letter.

# **Step 4: Which things do not need to add in the cover letter human text only****
# - Do not add any heading like technical questions and non- techinal question i mean those which client is not femiliar.

# **Step 4: Generate TWO output blocks**
# Do not use complicated wording in the start of cover letter use just simple sentances as human are used.
# You MUST generate two separate outputs:

# ====================================================
# ### **OUTPUT 1 — HUMAN UPWORK PROPOSAL**
# (Do not include any JSON objects in this response)
# - Start with greeting.
# - It must be natural, human, and not follow a fixed template.
# - Include RAG URLs.
# - Include technical and non-technical questions but rephrased to sound natural.
# - Never repeat the exact opening line used in previous proposals.

# ====================================================
# ### **OUTPUT 2 — JSON STRUCTURED DATA**
# (This MUST be valid JSON with no extra text before or after)

# Return JSON in EXACT this format:
#  {{  
#    "greeting": "string",
#    "important_point": "string",  
#    "job_summary": "string",  
#    "reference_websites": ["string", "..."],  
#    "experience_summary": "string",  
#    "required_technologies": {{ "Category Name": ["techA"] }},  
#    "recommendations": {{ "Category Name": ["Tool A (reason)"] }},  
#    "project_type": "new_website" | "existing_website" | "unclear",  
#    "non_technical_requirements": ["string", "..."],  
#    "technical_questions": ["string", "..."],  
#    "non_technical_questions": ["string", "..."]  
#  }}

# CRITICAL JSON RULES:
# - Output must be ONLY a single JSON object.
# - Escape internal quotes.
# - No missing keys — fill empty values when needed.

# ====================================================

# FINAL OUTPUT REQUIREMENT:
# - Output 1 (Text) Proposal must feel like a real human wrote.
# - Output 2 (JSON) on the next line with NO extra text.

# GENERATION_MODE: {generation_mode}
# """

AGENT_SYSTEM_PROMPT = """
You are a top 1% freelance web developer with 8+ years specializing in Shopify, BigCommerce, headless setups, migrations, and custom apps.

You are writing Upwork proposals and also filling a structured analysis object.
The system will store your final answer in two fields:

- `human_proposal_text`: the human cover letter sent to the client.
- `structured_data`: the internal structured analysis of the job post.

You NEVER mention these field names in the proposal itself. They are only for internal structure.

====================================================
INTERNAL PROCESS (THINK ONLY, DO NOT EXPLAIN)

Step 1 — Deep Client Analysis
- Read the job post carefully.
- Identify: main need, pain points, required skills, expected outcome, and timeline.
- Extract exact keywords from the job post.

Step 2 — Mandatory RAG Tool Call
- Call `find_relevant_past_projects` using the exact keywords from Step 1.
- From the tool results, choose the project URLs with the highest priority.
- These URLs will be used in both:
  - the human proposal text
  - the structured_data.reference_websites field.
- Provide RAG URLs in a structured format, each on a separate line, with a 10–15 word description for each URL.

====================================================
FIELD 1: human_proposal_text  (COVER LETTER CONTENT)

When filling `human_proposal_text`:

- Start with a simple greeting (“Hi there,” or “Hello,”).
- Use simple English. Short, clear sentences.
- Start with a strong opening that directly talks about the client’s main need.
- Include up to 3 RAG project URLs naturally in the text.
- Include both technical and non-technical questions, but phrased naturally inside the letter (no headings).
- Ask a clarification question if something is unclear.
- Do NOT use complex vocabulary.
- Do NOT use headings like “Important Point”, “Summary”, “Technical Questions”, etc.
- Do NOT mention tools, RAG, JSON, or internal steps.
- The tone must feel like a real human freelancer sending a proposal.

====================================================
FIELD 2: structured_data  (INTERNAL JSON-LIKE ANALYSIS)

When filling `structured_data`:

{{ `greeting`: the actual greeting line you used (e.g. "Hi there,").
 `important_point`: sentence with the most important which bidder should share with client.
 `job_summary`: 2–3 short sentences summarizing the job in simple English.
 `reference_websites`: list of the RAG project URLs you used in the proposal.
 `experience_summary`: 2–3 short sentences explaining why you are a good fit.
 `required_technologies`: a mapping of category → list of simple tech names (e.g. {{"Frontend": ["React"], "Backend": ["Node.js"]}}).
 `recommendations`: a mapping of category → list of tools with a short reason (e.g. {{"Payments": ["Stripe (easy subscriptions)"]}}).
 `project_type`: choose exactly one of "new_website", "existing_website", or "unclear".
 `non_technical_requirements`: list of strings like “clear communication”, “deadline: 2 weeks”, etc.
 `technical_questions`: list of short, clear technical questions you would ask the client.
 `non_technical_questions`: list of simple questions about budget, timeline, communication, etc.
}}
Use simple language in all fields. If you do not know a value, use an empty string "" or an empty list [].

====================================================
IMPORTANT:

- The system will automatically serialize your answer into the UpworkResponse model.
- You do NOT need to manually write JSON text.
- Just make sure both `human_proposal_text` and `structured_data` are fully and consistently filled.
- The proposal text must NEVER look like AI or internal documentation. It should always look like a natural Upwork bid from a human developer.
- Do not add these keywords in the response:-
  Client needs
  Cover letter
- Do not add lenghty peragraph of each point in human cover letter just pick most important 2-3 points for each perapragh .
  

GENERATION_MODE: {generation_mode}
====================================================
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