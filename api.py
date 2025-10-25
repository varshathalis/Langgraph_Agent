"""
FastAPI SSE Server for LangGraph MCP Agent
------------------------------------------
Run with:
    python api.py
"""

import asyncio
import json
import os
from pprint import pprint

import uvicorn
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse
from typing import List, Optional

from agentic_components.agent import run_agent

app = FastAPI(title="LangGraph MCP Agent (SSE API)")

# ======================================================
# 🔸 Helper: SSE Event Formatter
# ======================================================
def serialize_obj(obj):
    """Serialize complex objects to JSON-friendly format"""
    if hasattr(obj, '__dict__'):
        return {k: serialize_obj(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_obj(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_obj(v) for k, v in obj.items()}
    elif hasattr(obj, '__str__'):
        try:
            return str(obj)
        except:
            return repr(obj)
    return obj

def format_sse(event: str, data: dict | str) -> str:
    """Format an event + data as a proper SSE message."""
    if not isinstance(data, str):
        try:
            # Try to serialize complex objects
            data_clean = serialize_obj(data)
            data = json.dumps(data_clean, ensure_ascii=False, default=str)
        except Exception as e:
            data = json.dumps({"error": f"Serialization error: {str(e)}"}, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


# ======================================================
# 🔸 Event Generator for StreamingResponse
# ======================================================
async def event_generator(queue: asyncio.Queue):
    """Continuously stream messages from the async queue."""
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # Send a keep-alive comment if queue is empty
                yield ": keep-alive\n\n"
                continue

            if msg == "[DONE]":
                # Final completion event
                yield format_sse("meta", {"usage": {}, "info": "stream_complete"})
                break

            if isinstance(msg, tuple) and len(msg) == 2:
                event_name, payload = msg
                yield format_sse(event_name, payload)
            else:
                # Fallback if something unstructured appears
                yield format_sse("thinking", {"content": str(msg)})
    finally:
        pass


# ======================================================
# 🔸 Main Endpoint
# ======================================================
@app.post("/run_agent")
async def run_agent_api(req: Request):

    data = await req.json()
    queue = asyncio.Queue()

    async def sse_send(event: str, payload: dict):
        """Push an SSE event to the async queue."""
        await queue.put((event, payload))

    async def orchestrator_task():
        try:
            # Run the LangGraph agent (it will emit thinking/tool/token/etc.)
            await run_agent(data['message'], sse_send)
        except Exception as e:
            await sse_send("meta", {"error": str(e)})
        finally:
            await queue.put("[DONE]")

    asyncio.create_task(orchestrator_task())
    return StreamingResponse(event_generator(queue), media_type="text/event-stream")

# ======================================================
# 🔸 Entry Point
# ======================================================
if __name__ == "__main__":
    print("Starting LangGraph MCP Agent API on http://localhost:8001 ...")
    uvicorn.run("api:app", host="127.0.0.1", port=8001, reload=True)
