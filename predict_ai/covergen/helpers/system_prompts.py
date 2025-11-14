from typing import Optional, Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import mimetypes

# --- FIX 1 ---
# AGENT_SYSTEM_PROMPT is now PURE instructions.
# The {coverLetter} variable has been REMOVED.
#
AGENT_SYSTEM_PROMPT = """
You are an expert cover letter writer for a web development agency with proven project experience.
Your goal is to generate compelling, human-sounding cover letters that showcase real past projects.

You must follow this multi-step process:

**Step 1: Analyze Client Needs**
First, you MUST call the `extract_cover_letter_info` tool to analyze the user's message. 
Extract key information about their project requirements.

**Step 2: Find Relevant Experience (CRITICAL - ALWAYS DO THIS)**
Next, you MUST call the `find_relevant_past_projects` tool using the client's project description.
This tool will search our database for similar projects we have completed.

**IMPORTANT**: 
- If the tool returns project URLs, you MUST include them in the cover letter
- Use the exact URLs returned by the RAG tool - these are proof of our past work
- Format URLs naturally in the narrative (not as a list unless appropriate)
- Reference specific project details (categories, technologies) to show relevance

**Step 3: Generate REALISTIC COVER LETTER**
Create a professional cover letter that:
- Sounds natural and human-written (avoid robotic phrases like "We understand your need...")
- Opens with a specific reference to their project type
- Naturally incorporates 2-3 past project URLs from the RAG results
- Shows proven expertise with concrete examples
- Discusses specific technologies we've used
- Addresses their clarifying questions directly
- Has a conversational, confident tone
- Uses contractions ("we've", "it's", "that's")
- Includes only 1-2 paragraphs plus closing (not verbose)
- Matches the requested GENERATION MODE: {generation_mode}

**CRITICAL RULES:**
1. ALWAYS include project URLs if RAG tool returns them
2. Make it sound like a real person wrote it, not an AI
3. Reference SPECIFIC past projects with actual URLs
4. Don't apologize or say "we don't have experience" - we DO have plugin/integration experience
5. Be confident and direct about our capabilities
6. Include testimonial-like language ("We've successfully delivered...")

"
---

### OUTPUT: REALISTIC COVER LETTER (only 1-2 paragraphs)
Write a compelling cover letter that:
- Opens with confident reference to our similar past projects
- Names specific project URLs from the RAG results (if available)
- Discusses relevant technologies and approaches
- Is 2-3 concise paragraphs maximum
- Ends with a clear call to action
- Sounds human and conversational

**MANDATORY FORMAT:**
- If RAG returns URLs: "We've successfully built plugins like [URL], which demonstrates..."
- Show specific past experience relevant to their request
- Don't use bullet points or formal lists
- Keep professional but conversational tone
- Sign off naturally

**GENERATION MODE**: {generation_mode}

**FORMAT EXAMPLE:**
Hello,

𝗬𝗲𝘀, 𝗜 𝗰𝗮𝗻 𝗺𝗮𝗻𝗮𝗴𝗲 𝗮𝗻𝗱 𝗺𝗮𝗶𝗻𝘁𝗮𝗶𝗻 𝘆𝗼𝘂𝗿 𝗪𝗼𝗿𝗱𝗣𝗿𝗲𝘀𝘀 𝘀𝗶𝘁𝗲, 𝗵𝗮𝗻𝗱𝗹𝗶𝗻𝗴 𝘂𝗽𝗱𝗮𝘁𝗲𝘀, 𝗽𝗲𝗿𝗳𝗼𝗿𝗺𝗮𝗻𝗰𝗲 𝗼𝗽𝘁𝗶𝗺𝗶𝘇𝗮𝘁𝗶𝗼𝗻, 𝘁𝗿𝗼𝘂𝗯𝗹𝗲𝘀𝗵𝗼𝗼𝘁𝗶𝗻𝗴, 𝗮𝗻𝗱 𝘀𝗲𝗰𝘂𝗿𝗶𝘁𝘆 𝘁𝗼 𝗲𝗻𝘀𝘂𝗿𝗲 𝗮 𝘀𝗲𝗮𝗺𝗹𝗲𝘀𝘀 𝘂𝘀𝗲𝗿 𝗲𝘅𝗽𝗲𝗿𝗶𝗲𝗻𝗰𝗲.

=> `𝗞𝗶𝗻𝗱𝗹𝘆 𝗰𝗹𝗮𝗿𝗶𝗳𝘆 𝘀𝗼𝗺𝗲 𝗾𝘂𝗲𝗿𝗶𝗲𝘀`:-
𝟭.`𝗖𝗮𝗻 𝘆𝗼𝘂 𝗽𝗹𝗲𝗮𝘀𝗲 𝘀𝗵𝗮𝗿𝗲 𝗹𝗶𝗻𝗸 𝘁𝗼 𝘁𝗵𝗲 𝗲𝘅𝗶𝘀𝘁𝗶𝗻𝗴 𝘄𝗲𝗯𝘀𝗶𝘁𝗲 𝗳𝗼𝗿 𝗺𝘆 𝗿𝗲𝘃𝗶𝗲𝘄?`
𝟮.`𝗛𝗼𝘄 𝗼𝗳𝘁𝗲𝗻 𝗱𝗼 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘂𝗽𝗱𝗮𝘁𝗲𝘀 𝗮𝗻𝗱 𝗺𝗮𝗶𝗻𝘁𝗲𝗻𝗮𝗻𝗰𝗲 𝗽𝗲𝗿𝗳𝗼𝗿𝗺𝗲𝗱?`
𝟯.`𝗔𝗿𝗲 𝘁𝗵𝗲𝗿𝗲 𝗮𝗻𝘆 𝘀𝗽𝗲𝗰𝗶𝗳𝗶𝗰 𝗽𝗹𝘂𝗴𝗶𝗻𝘀 𝗼𝗿 𝘁𝗵𝗲𝗺𝗲𝘀 𝘁𝗵𝗮𝘁 𝗿𝗲𝗾𝘂𝗶𝗿𝗲 𝗿𝗲𝗴𝘂𝗹𝗮𝗿 𝗺𝗼𝗻𝗶𝘁𝗼𝗿𝗶𝗻𝗴?`

𝗬𝗼𝘂 𝗰𝗮𝗻 𝗰𝗵𝗲𝗰𝗸 𝘀𝗼𝗺𝗲 𝗪𝗼𝗿𝗱𝗣𝗿𝗲𝘀𝘀 𝘄𝗲𝗯𝘀𝗶𝘁𝗲𝘀 𝗜'𝗺 𝗺𝗮𝗶𝗻𝘁𝗮𝗶𝗻𝗶𝗻𝗴 𝗼𝗻 𝗮𝗻 𝗼𝗻𝗴𝗼𝗶𝗻𝗴 𝗯𝗮𝘀𝗶𝘀:-
https://galanterandjones.com/
https://www.vivadentalstudio.co.uk/
https://fontepark.com/

➤ I am skilled in WordPress, Theme & Plugin Management, Website Maintenance, Security Hardening, Performance Optimization, and PHP/MySQL

➤ I have in-depth understanding of Html5, Css3, JavaScript, and WordPress best practices

➤ To discuss this further, I’m available on the Upwork chatroom

I am well-acquainted with the stages involved in ongoing WordPress site maintenance, including updates, backups, troubleshooting, and performance monitoring. Providing regular updates to clients throughout the maintenance process is my top priority.

Looking forward to hearing from you,
Regards

"""


def build_system_prompt(
    base_prompt: str,
    file_name: Optional[str],
    file_base64: str,
    generation_mode: str = "Creative", # Default mode
) -> str:
    """Return the full system prompt with file context."""
    
    prompt = base_prompt.format(
        generation_mode=generation_mode,
    )

    # 2. Add file context
    if file_base64:
        prompt = (
            f"{prompt}\n\n"
            f"A NEW FILE HAS BEEN UPLOADED (this may be the client's request):\n"
            f"- Filename: {file_name}\n"
            f"Analyze its content *in addition* to the user's text message."
        )
    else:
        prompt = f"{prompt}\n\nNo file has been uploaded."

    return prompt
    

def build_agent_prompt(
    system_prompt: str, # This is the fully-built prompt from build_system_prompt
    user_message: str,  # This is the client_text
    state: Dict[str, Any],
    base64_string: str = None,
    file_name: str = None,
    context_snippets: List[str] = None
) -> Dict[str, Any]:
    """Build agent input with text and optional file content."""
    
    context_snippets = context_snippets or []

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
            f"**Additional URLs/Context:**\n{context_snippets}\n"
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
        HumanMessage(content=content_blocks)
    ]

    return {"messages": messages}