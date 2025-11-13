from typing import Optional, Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import mimetypes

# Prompt for structured extraction (used with tool calling)
EXTRACTION_SYSTEM_PROMPT = """
You are a professional cover letter analyzer for a web development agency. 

Your task is to extract structured information from the client's cover letter using the extract_cover_letter_info tool.

**EXTRACTION GUIDELINES**:

1. **greeting** and **client_name**: Extract from salutations or signatures
2. **main_objective**: Primary goal in one concise sentence (max 50 words)
3. **project_scope**: 2-3 sentences describing the project, key features, target users
4. **reference_sites**: Any URLs or website names mentioned
5. **technologies_needed**: ALL required technologies grouped by category (Frontend, Backend, Platform, Design, etc.)
   - INCLUDE: Languages, frameworks, platforms, design tools, APIs
   - INFER from project description
   - EXCLUDE: Abstract goals or feature names
6. **tool_recommendations**: Specific plugins/apps/services with reasoning
7. **project_category**: new_website | existing_website | website_update | unclear
8. **non_tech_requirements**: Timeline, budget, deliverables, communication preferences
9. **clarifying_questions**: 3-5 direct questions (NO introductory phrases like "Regarding...")
10. **suggested_response**: Professional 2-3 paragraph response (200-300 words)

Always use the extract_cover_letter_info tool to return your analysis.

Cover Letter to Analyze:
---
{coverLetter}
"""

# Prompt for formatted response generation
RESPONSE_SYSTEM_PROMPT = """
You are a professional web development consultant responding to a client's cover letter.

Your task is to write a compelling, personalized cover letter response that:
- Shows you understand their specific needs
- Demonstrates relevant expertise with concrete examples
- Mentions specific technologies/platforms they need
- Explains HOW your skills solve their problems
- Maintains a confident, professional, warm tone
- Includes clear next steps

Structure (2-3 paragraphs, 200-300 words):
1. Greeting + acknowledgment of their needs
2. Your relevant experience tailored to their project
3. Next steps/enthusiasm to collaborate

Write naturally as if you're a senior developer genuinely interested in their project.

Client's Cover Letter:
---
{coverLetter}
"""

# Legacy combined prompt (keep for reference)
SYSTEM_PROMPT = EXTRACTION_SYSTEM_PROMPT


def build_system_prompt(
    base_prompt: str,
    file_name: Optional[str],
    file_base64: str,
) -> str:
    """Return the full system prompt with file context."""
    if file_base64:
        return (
            f"{base_prompt}\n\n"
            f"A NEW FILE HAS BEEN UPLOADED:\n"
            f"- Filename: {file_name}\n"
            f"- Size: {len(file_base64)} characters\n\n"
            f"The user's message may be about this newly uploaded file."
        )
    else:
        return f"{base_prompt}\nNo file has been uploaded in this session yet."
    

def build_agent_prompt(
    system_prompt: str,
    user_message: str,
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

    # Text block
    text_block = {
        "type": "text",
        "text": (
            "Process the following user inputs.\n\n"
            f"User Message:\n{user_message}\n\n"
            f"State:\n{state}\n\n"
            f"Context Snippets:\n{context_snippets}\n\n"
            "If a file is attached, read and analyze its content."
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

    # Build messages
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=content_blocks)
    ]

    return {"messages": messages}