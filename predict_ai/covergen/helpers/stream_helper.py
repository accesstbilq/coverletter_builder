import json
import time
import traceback
from typing import Dict, Any, Generator

# --- JSON extractor helper ---
class JSONExtractionError(Exception):
    pass


def extract_json_and_span(text: str):
    """
    Find first top-level JSON object in `text`.
    Returns tuple: (parsed_json: dict, start_index: int, end_index_inclusive: int)
    Raises JSONExtractionError on failure.
    """
    if not text or "{" not in text:
        raise JSONExtractionError("No JSON object start found in text.")

    start = text.find("{")
    stack = []
    idx = start
    in_string = False
    escape = False

    while idx < len(text):
        ch = text[idx]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                stack.append("{")
            elif ch == "}":
                if not stack:
                    raise JSONExtractionError("Unbalanced braces while parsing JSON.")
                stack.pop()
                if not stack:
                    end = idx + 1  # end is exclusive here
                    candidate = text[start:end]
                    try:
                        parsed = json.loads(candidate)
                        return parsed, start, end
                    except json.JSONDecodeError as e:
                        # helpful debug info
                        raise JSONExtractionError(f"JSON decode failed: {e.msg}. Candidate prefix: {candidate[:400]}...") from e
        idx += 1

    raise JSONExtractionError("Reached end of text without closing JSON object.")


# --- Updated stream_generator (drop-in replacement) ---
def stream_generator(
    agent,
    agent_input: Dict[str, Any],
    config: Dict[str, Any],
    state: Dict[str, Any]
) -> Generator[str, None, None]:
    """
    Streams SSE-like events from a multi-step agent with **smooth 1-100% progress**.

    Emits an additional structured_data event when JSON is found inside the AI response:
    - structured_data: {"type": "structured_data", "data": {...}}
    - structured_data_failed: {"type": "structured_data_failed", "error": "...", "candidate": "..."}
    (candidate is truncated for safety)
    """
    # ============================================
    # TIMING & PROGRESS STATE
    # ============================================
    start_time = time.time()
    last_progress = 0
    last_emit_time = time.time()
    generation_start_time = None

    # Phase tracking
    extraction_completed = False
    projects_completed = False
    generation_completed = False

    # Content buffering
    full_response_text = ""
    last_content = ""

    # Breakdown data (from extraction tool)
    breakdown_data = None

    # Token usage
    prompt_tokens = 0
    completion_tokens = 0

    def emit_sse(obj: dict) -> str:
        """Format SSE data line"""
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    def emit_progress(percent: int, message: str) -> str:
        """Emit monotonically increasing progress (1-100)"""
        nonlocal last_progress, last_emit_time

        percent = max(1, min(100, percent))

        # Only emit if progress increased
        if percent > last_progress:
            last_progress = percent
            last_emit_time = time.time()
            return emit_sse({
                "type": "progress",
                "percent": percent,
                "message": message
            })
        return ""

    def update_response_text(new_text: str) -> None:
        """Update full response text with new content"""
        print(f"[DEBUG] Updating response text with {len(new_text)} chars")
        nonlocal full_response_text
        full_response_text += new_text

    def capture_breakdown(data: dict) -> None:
        """Capture breakdown data from extraction tool"""
        nonlocal breakdown_data
        breakdown_data = data

    def get_smooth_progress(elapsed_time: float, phase_name: str) -> int:
        """
        Get smooth progress based on elapsed time.
        Allocates progress ranges to different phases:
        - 1-15%: Initialization & Analysis
        - 15-50%: Processing & Projects
        - 50-95%: Generation
        - 95-100%: Finalization
        """
        if elapsed_time < 1:
            # First second: init to 15%
            return max(1, 1 + int(14 * (elapsed_time / 1)))
        elif elapsed_time < 5:
            # Seconds 1-5: 15% to 50%
            progress = 15 + int(35 * ((elapsed_time - 1) / 4))
            return min(progress, 50)
        elif elapsed_time < 15:
            # Seconds 5-15: 50% to 95%
            progress = 50 + int(45 * ((elapsed_time - 5) / 10))
            return min(progress, 95)
        else:
            # Beyond 15 seconds: 95% to 99%
            return min(99, 95 + int(4 * ((elapsed_time - 15) / 10)))

    try:
        # ============================================
        # START: Initialize at 1%
        # ============================================
        yield emit_progress(1, "Initializing...")

        extraction_completed = False
        projects_completed = False
        generation_completed = False
        generation_start_time = None

        # ============================================
        # STREAM AGENT EXECUTION
        # ============================================
        all_messages = []  # Collect all messages to find final AI response

        for step in agent.stream(agent_input, config=config, stream_mode="messages",state=state):
            last_message1 =step
            # yield last_message1
            # yield emit_sse({
            #     "type": "streaming",
            #     "messages": last_message1
            # }) 

            # Emit smooth progress every 100ms
            elapsed = time.time() - start_time
            now = time.time()
            if now - last_emit_time >= 0.1 and not generation_completed:
                smooth_pct = get_smooth_progress(elapsed, "processing")
                message_templates = [
                    "Analyzing...",
                    "Processing...",
                    "Thinking...",
                    "Generating...",
                    "Almost done..."
                ]
                msg_idx = min(len(message_templates) - 1, int(smooth_pct / 20))
                yield emit_progress(smooth_pct, message_templates[msg_idx])

            # Validate step structure
            if not isinstance(step, list) or not step:
                continue

            # Store all messages
            all_messages.extend(step)

            for idx, msg in enumerate(step):
                message_type = getattr(msg, 'type', None)
                message_name = getattr(msg, 'name', None)
                message_content = getattr(msg, 'content', None)

                # DEBUG: Log every message
                print(f"[DEBUG] Step {idx}: type={message_type}, name={message_name}, content_len={len(str(message_content)) if message_content else 0}")

            last_message = step[-1]
            message_type = getattr(last_message, 'type', None)
            message_name = getattr(last_message, 'name', None)
            message_content = getattr(last_message, 'content', None)
            print(f"[DEBUG] Last message: type={message_type}")
           # ============================================
            # PROJECTS TOOL
            # ============================================
            if message_type == "tool" and message_name == "find_relevant_past_projects":
                if not projects_completed:
                    projects_completed = True
                    yield emit_progress(45, "Finding relevant projects...")
                    yield emit_progress(55, "Projects matched!")

            # ============================================
            # AI RESPONSE (Generation)
            # ============================================
            elif message_type == "ai":

                # Mark generation start
                if generation_start_time is None:
                    generation_start_time = time.time()
                    yield emit_progress(60, "Generating response...")

                # Stream tokens
                current_content = last_message.content


                if isinstance(current_content, str) and current_content != last_content:
                    if current_content.startswith(last_content):
                        # Incremental update
                        new_part = current_content[len(last_content):]
                        if new_part:
                            update_response_text(new_part)
                            yield emit_sse({
                                "type": "token",
                                "content": new_part
                            })
                    else:
                        # Full replacement (first time or reset)
                        update_response_text(current_content)
                        yield emit_sse({
                            "type": "token",
                            "content": current_content
                        })

                    last_content = current_content

            # ============================================
            # TOKEN USAGE (Extract from any message)
            # ============================================
            if hasattr(last_message, "usage_metadata") and last_message.usage_metadata:
                usage = last_message.usage_metadata
                in_tokens = usage.get("input_tokens")
                out_tokens = usage.get("output_tokens")

                if in_tokens is not None:
                    prompt_tokens = in_tokens
                if out_tokens is not None:
                    completion_tokens = out_tokens

                print(f"[DEBUG] Token usage found: input={in_tokens}, output={out_tokens}")

        # ============================================
        # EXTRACT FINAL RESPONSE FROM COLLECTED MESSAGES
        # ============================================
        print(f"[DEBUG] Total messages collected: {len(all_messages)}")
        print(f"[DEBUG] Current token counts: prompt={prompt_tokens}, completion={completion_tokens}")

        # Extract token usage from all collected messages
        for msg in all_messages:
            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                usage = msg.usage_metadata
                in_tokens = usage.get("input_tokens")
                out_tokens = usage.get("output_tokens")

                if in_tokens is not None and in_tokens > 0:
                    prompt_tokens = in_tokens
                if out_tokens is not None and out_tokens > 0:
                    completion_tokens = out_tokens

                print(f"[DEBUG] Token usage from message: input={in_tokens}, output={out_tokens}")

        # If no response was captured, search backwards through all messages for AI response
        if not full_response_text:
            print("[DEBUG] No response captured from stream, searching all messages...")
            for msg in reversed(all_messages):
                msg_type = getattr(msg, 'type', None)
                msg_content = getattr(msg, 'content', None)

                print(f"[DEBUG] Checking message type: {msg_type}, has_content: {bool(msg_content)}")

                if msg_type == "ai" and isinstance(msg_content, str) and msg_content:
                    full_response_text = msg_content
                    print(f"[DEBUG] Found AI response in collected messages: {len(full_response_text)} chars")
                    break

        # ============================================
        # COMPLETION SEQUENCE
        # ============================================
        generation_completed = True

        # If still no response, try to get it from agent state
        if not full_response_text:
            print("[DEBUG] No response in messages, checking agent state...")
            try:
                final_state = agent.get_state(config)
                print(f"[DEBUG] Final state type: {type(final_state)}")

                if hasattr(final_state, 'values') and isinstance(final_state.values, dict):
                    if 'messages' in final_state.values:
                        messages = final_state.values['messages']
                        for msg in reversed(messages):
                            # Extract token usage from final state messages
                            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                                usage = msg.usage_metadata
                                in_tokens = usage.get("input_tokens")
                                out_tokens = usage.get("output_tokens")

                                if in_tokens is not None and in_tokens > 0:
                                    prompt_tokens = in_tokens
                                if out_tokens is not None and out_tokens > 0:
                                    completion_tokens = out_tokens

                                print(f"[DEBUG] Token usage from state: input={in_tokens}, output={out_tokens}")

                            # Extract response
                            if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content'):
                                full_response_text = msg.content
                                print(f"[DEBUG] Found AI response in state: {len(full_response_text)} chars")
                                break
            except Exception as e:
                print(f"[DEBUG] Error extracting from state: {e}")

        # ============================================
        # PARSE RESPONSE INTO COVER LETTER & STRUCTURED DATA
        # ============================================
        cover_letter_only = ""
        if full_response_text:
            # 1) First try: treat the entire response as JSON (structured output case)
            parsed_top = None
            try:
                parsed_top = json.loads(full_response_text)
            except Exception:
                parsed_top = None

            if isinstance(parsed_top, dict) and (
                "human_proposal_text" in parsed_top or "structured_data" in parsed_top
            ):
                # This is the UpworkResponse-style JSON:
                # {
                #   "human_proposal_text": "...",
                #   "structured_data": { ... }
                # }

                cover_letter_only = parsed_top.get("human_proposal_text", "") or ""
                structured = parsed_top.get("structured_data", {}) or {}

                # Emit structured JSON as its own event
                print("[DEBUG] Emitting structured_data event from top-level JSON")
                yield emit_sse({
                    "type": "structured_data",
                    "data": structured
                })

                # Fallback if somehow proposal is empty
                if not cover_letter_only.strip():
                    print("[DEBUG] Empty human_proposal_text, falling back to full_response_text")
                    cover_letter_only = full_response_text

            else:
                # 2) Fallback: old behavior — cover letter + JSON embedded in text
                try:
                    parsed_json, json_start, json_end = extract_json_and_span(full_response_text)

                    # Emit structured JSON as its own event
                    print("[DEBUG] Emitting structured_data event with parsed JSON from embedded block")
                    yield emit_sse({
                        "type": "structured_data",
                        "data": parsed_json
                    })

                    # Remove JSON block from the end of the response to get clean cover letter
                    cover_letter_only = full_response_text[:json_start]

                    # Heuristics to clean trailing separators / headers
                    import re
                    cover_letter_only = re.sub(r"(?s)\n\s*={3,}\s*$", "\n", cover_letter_only)  # trailing =====
                    cover_letter_only = re.sub(r"(?i)\n\s*###?\s*\**OUTPUT\s*2.*$", "\n", cover_letter_only)
                    cover_letter_only = re.sub(r"(?i)\n\s*###?\s*\**OUTPUT\s*1.*$", "\n", cover_letter_only)
                    cover_letter_only = re.sub(r"(?s)\n\s*[\-*_]{3,}\s*$", "\n", cover_letter_only)
                    cover_letter_only = cover_letter_only.rstrip()

                    if not cover_letter_only.strip():
                        print("[DEBUG] cover_letter_only empty after trimming; falling back to full_response_text")
                        cover_letter_only = full_response_text

                except JSONExtractionError as jde:
                    # Parsing failed: emit a structured_data_failed event and send full response as cover letter
                    print(f"[DEBUG] structured JSON extraction failed: {jde}")
                    candidate = ""
                    try:
                        first_brace = full_response_text.find("{")
                        if first_brace != -1:
                            candidate = full_response_text[first_brace:first_brace + 4000]
                    except Exception:
                        candidate = ""

                    yield emit_sse({
                        "type": "structured_data_failed",
                        "error": str(jde),
                        "candidate": candidate[:2000]
                    })

                    cover_letter_only = full_response_text

                except Exception as e:
                    # Unexpected error during extraction
                    print(f"[DEBUG] Unexpected error extracting structured JSON: {e}")
                    yield emit_sse({
                        "type": "structured_data_failed",
                        "error": "unexpected error: " + str(e),
                        "candidate": ""
                    })
                    cover_letter_only = full_response_text
        else:
            print("[DEBUG] No full_response_text to parse for structured JSON")
            cover_letter_only = full_response_text


        # Emit final cover letter using cover_letter_only (this will not include the JSON block)
        if cover_letter_only:
            print(f"[DEBUG] Emitting cover_letter_done (cleaned) with {len(cover_letter_only)} chars")
            yield emit_sse({
                "type": "cover_letter_done",
                "content": cover_letter_only
            })
        else:
            print("[DEBUG] WARNING: No cover letter text to send!")

        # Emit breakdown (analysis_done) event FIRST if we have it
        if breakdown_data:
            print(f"[DEBUG] Emitting analysis_done with breakdown: {list(breakdown_data.keys()) if isinstance(breakdown_data, dict) else breakdown_data}")
            yield emit_sse({
                "type": "analysis_done",
                "analysis": breakdown_data
            })
        else:
            print("[DEBUG] WARNING: No breakdown data to send!")


        # Emit done event
        yield emit_sse({"type": "done"})

        # Emit token usage
        total_tokens = prompt_tokens + completion_tokens
        print(f"[DEBUG] Final token counts - input: {prompt_tokens}, output: {completion_tokens}, total: {total_tokens}")

        yield emit_sse({
            "type": "usage",
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens
        })
        
    except Exception as e:
        # ============================================
        # ERROR HANDLING
        # ============================================
        error_detail = traceback.format_exc()
        print(f"Stream error: {error_detail}")

        yield emit_sse({
            "type": "error",
            "message": str(e),
            "detail": error_detail if config.get("debug") else None
        })

        # Still try to reach 100%
        try:
            yield emit_progress(last_progress + 5, f"Error: {str(e)}")
        except:
            pass
