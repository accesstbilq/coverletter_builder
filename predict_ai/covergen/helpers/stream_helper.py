from typing import Optional, Dict, Any, Generator
import json
import time
import traceback
import math


def stream_generator(
    agent,
    agent_input: Dict[str, Any],
    config: Dict[str, Any],
    extraction_input: Optional[Dict[str, Any]] = None,
) -> Generator[str, None, None]:
    """
    Streams SSE-like events with fine-grained progress (1..100).

    Exposed SSE messages (JSON inside `data: ...`):
      - token:    {'type':'token', 'content': '<new_text>'}
      - progress: {'type':'progress', 'percent': <int>, 'message': '<text>'}
      - done:     {'type':'done'}
      - usage:    {'type':'usage', ...}
      - error:    {'type':'error', 'message': ...}

    Heuristic for percent:
      - estimate expected output length (characters) from inputs
      - percent = min(99, int(chars_received / expected_chars * 99))
      - ensure monotonic increase and emit only on increase
      - final percent 100 emitted before completion
    """
    last_content = ""
    prompt_tokens = completion_tokens = 0

    # ---- derive a rough expected output size (chars) from agent_input ----
    # Try to extract client_text from agent_input messages; fallback to averages.
    expected_chars = 1000  # default fallback
    try:
        # agent_input may be {"messages": [SystemMessage(...), HumanMessage(...)]}
        msgs = agent_input.get("messages") if isinstance(agent_input, dict) else None
        if msgs:
            total_len = 0
            for m in msgs:
                # m might be a langchain Message object or a dict/str
                try:
                    # for LangChain Message objects: .content property (string or list)
                    cont = getattr(m, "content", None)
                except Exception:
                    cont = None

                if cont is None:
                    # maybe it's already a dict or str
                    cont = m

                if isinstance(cont, list):
                    # multimodal content blocks -> measure textual block lengths
                    for block in cont:
                        if isinstance(block, dict):
                            # text blocks: block.get("text")
                            t = block.get("text") or block.get("filename") or ""
                            total_len += len(str(t))
                        else:
                            total_len += len(str(block))
                else:
                    total_len += len(str(cont))
            # base expected on inputs (scale factor to allow longer outputs)
            expected_chars = max(800, int(total_len * 1.5))

    except Exception:
        expected_chars = 1000

    # clamp expected_chars to a sensible range to avoid extreme percents
    expected_chars = int(max(400, min(expected_chars, 20000)))

    chars_received = 0
    last_progress = 0
    last_emit_time = 0.0
    progress_emit_interval = 0.08  # seconds, allow more frequent updates if percent changes

    def emit_sse(obj: dict):
        """Helper to format SSE data lines"""
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    def maybe_emit_progress(message_hint: str = "Processing..."):
        nonlocal last_progress, last_emit_time
        # compute percent mapped to 1..99
        pct = int(min(99, math.floor((chars_received / expected_chars) * 99)))
        pct = max(1, pct)  # ensure at least 1 while streaming
        now = time.time()
        # emit only if percent increased or more than interval passed (to avoid stall)
        if pct > last_progress or (now - last_emit_time) > 1.5:
            last_progress = pct
            last_emit_time = now
            return emit_sse({"type": "progress", "percent": pct, "message": message_hint})
        return None

    try:

        # 2) Stream from the agent
        # We expect agent.stream(...) to yield (token_message, metadata) tuples
        for token_message, metadata in agent.stream(agent_input, config=config, stream_mode="messages"):
            if not token_message:
                continue

            last_message = token_message

            # If message has textual content, compute delta relative to last_content
            if hasattr(last_message, "content") and last_message.content:
                current = last_message.content
                if isinstance(current, str):
                    # new text relative to last_content
                    if current != last_content:
                        if current.startswith(last_content):
                            new_part = current[len(last_content):]
                            if new_part:
                                # update counters
                                chars_received += len(new_part)
                                # emit token event (original behavior)
                                yield emit_sse({"type": "token", "content": new_part})

                                # emit progress event if percent increases
                                p = maybe_emit_progress("Processing...")
                                if p:
                                    yield p
                        else:
                            # content replaced/not contiguous — emit the whole current
                            yield emit_sse({"type": "token", "content": current})
                            chars_received += len(current)
                            p = maybe_emit_progress("Processing...")
                            if p:
                                yield p
                        last_content = current

                else:
                    # non-string content (rare) — serialize and stream
                    s = str(current)
                    yield emit_sse({"type": "token", "content": s})
                    chars_received += len(s)
                    p = maybe_emit_progress("Processing...")
                    if p:
                        yield p
                    last_content = str(current)

            # update usage metadata if present
            if hasattr(last_message, "usage_metadata") and last_message.usage_metadata:
                usage = last_message.usage_metadata
                prompt_tokens = usage.get("input_tokens", prompt_tokens)
                completion_tokens = usage.get("output_tokens", completion_tokens)

            # also check metadata for hints that generation phase started — increase expected_chars adaptively
            # (if metadata provides estimated remaining length, we could use it; otherwise adapt)
            if metadata and isinstance(metadata, dict):
                # optional: if agent provides estimated_total_output_chars, use it
                est_total = metadata.get("estimated_total_chars") or metadata.get("estimated_output_size")
                if isinstance(est_total, (int, float)) and est_total > expected_chars:
                    expected_chars = int(min(20000, max(expected_chars, int(est_total))))

        # 3) Finalization: ensure progress reaches 99..100 and emit final events
        # emit an intermediate high-percent if missing
        if last_progress < 98:
            yield emit_sse({"type": "progress", "percent": max(last_progress, 98), "message": "Finalizing result..."})

        # final done + usage
        yield emit_sse({"type": "done"})
        total = prompt_tokens + completion_tokens
        yield emit_sse({"type": "usage", "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total})

        # final 100% progress
        yield emit_sse({"type": "progress", "percent": 100, "message": "Completed"})
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Stream error: {error_detail}")
        yield emit_sse({"type": "error", "message": str(e)})
