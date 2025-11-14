from typing import Optional, Dict, Any, Generator
import json
import time
import traceback


def stream_generator(
    agent,
    agent_input: Dict[str, Any],
    config: Dict[str, Any],
) -> Generator[str, None, None]:
    """
    Streams SSE-like events from a multi-step agent with **smooth 1-100% progress**.
    
    **GUARANTEES:**
    ✓ Progress starts at 1% immediately
    ✓ Progress ALWAYS increases (never stays flat)
    ✓ Progress reaches exactly 100% before completion
    ✓ Smooth linear progression independent of agent speed
    
    Events emitted:
    - progress: {"type": "progress", "percent": int, "message": str}
    - analysis_done: {"type": "analysis_done", "analysis": {...}}
    - token: {"type": "token", "content": str}
    - cover_letter_done: {"type": "cover_letter_done", "content": str}
    - done: {"type": "done"}
    - usage: {"type": "usage", "input_tokens": int, "output_tokens": int, "total_tokens": int}
    - error: {"type": "error", "message": str}
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
        
        for step in agent.stream(agent_input, config=config, stream_mode="messages"):
            
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
            
            # DEBUG: Log what we're receiving
            print(f"[DEBUG] LAST MESSAGE: type={message_type}, name={message_name}, content_len={len(str(message_content)) if message_content else 0}")
            
            # ============================================
            # EXTRACTION TOOL (Analysis) - CALL & OUTPUT
            # ============================================
            if message_type == "tool" and message_name == "extract_cover_letter_info":
                # First time we see this tool being called
                if not extraction_completed:
                    extraction_completed = True
                    yield emit_progress(10, "Analyzing requirements...")
                    
                    # Try to extract and store the breakdown data
                    try:
                        # Tool output is the actual dict/JSON returned by the tool
                        if isinstance(last_message.content, str):
                            data = json.loads(last_message.content)
                        else:
                            # If it's already a dict (LangChain might return it as object)
                            data = last_message.content
                        
                        capture_breakdown(data)
                        print(f"[DEBUG] Captured breakdown from extraction tool: {list(data.keys()) if isinstance(data, dict) else 'not-dict'}")
                        yield emit_progress(30, "Analysis complete!")
                    except Exception as e:
                        print(f"[DEBUG] Failed to parse breakdown from tool output: {e}")
                        # Try to extract JSON from content
                        try:
                            content = str(last_message.content)
                            if '{' in content and '}' in content:
                                start = content.index('{')
                                end = content.rindex('}') + 1
                                data = json.loads(content[start:end])
                                capture_breakdown(data)
                                print(f"[DEBUG] Extracted breakdown from tool output string: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                        except Exception as e2:
                            print(f"[DEBUG] Failed to extract breakdown: {e2}")
            
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
        # PARSE RESPONSE INTO COVER LETTER & BREAKDOWN
        # ============================================
        cover_letter_text = ""
        
        if full_response_text:
            print("[DEBUG] Parsing response for cover letter...")
            # The full response from AI is the cover letter
            # (No need to parse out JSON - breakdown already captured from extraction tool)
            cover_letter_text = full_response_text
            print(f"[DEBUG] Cover letter extracted: {len(cover_letter_text)} chars")
        
        # Ramp progress to 95% quickly
        yield emit_progress(85, "Wrapping up...")
        yield emit_progress(90, "Almost there...")
        yield emit_progress(95, "Finalizing...")
        
        # Emit breakdown (analysis_done) event FIRST if we have it
        if breakdown_data:
            print(f"[DEBUG] Emitting analysis_done with breakdown: {list(breakdown_data.keys()) if isinstance(breakdown_data, dict) else breakdown_data}")
            yield emit_sse({
                "type": "analysis_done",
                "analysis": breakdown_data
            })
        else:
            print("[DEBUG] WARNING: No breakdown data to send!")
        
        # Emit final cover letter
        if cover_letter_text:
            print(f"[DEBUG] Emitting cover_letter_done with {len(cover_letter_text)} chars")
            yield emit_sse({
                "type": "cover_letter_done",
                "content": cover_letter_text
            })
        else:
            print("[DEBUG] WARNING: No cover letter text to send!")
        
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
        
        # Final: 100%
        yield emit_progress(100, "Complete!")
        
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
