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
def format_sse(event: str, data: dict | str) -> str:
    """Format an event + data as a proper SSE message."""
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


# ======================================================
# 🔸 Event Generator for StreamingResponse
# ======================================================
async def event_generator(queue: asyncio.Queue):
    """Continuously stream messages from the async queue."""
    while True:
        msg = await queue.get()

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

    # Heartbeat
    yield ":\nok\nretry: 2000\n\n"


# ======================================================
# 🔸 Main Endpoint
# ======================================================
@app.post("/run_agent")
async def run_agent_api(req: Request):

    data = await req.json()
    pprint(data)
    queue = asyncio.Queue()

    async def sse_send(event: str, payload: dict):
        """Push an SSE event to the async queue."""
        await queue.put((event, payload))

    async def orchestrator_task():
        try:
            # Run the LangGraph agent (it will emit thinking/tool/token/etc.)
            await run_agent(data, sse_send)
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
    print("🚀 Starting LangGraph MCP Agent API on http://localhost:8000 ...")
    uvicorn.run("api:app", host="127.0.0.1", port=8001, reload=True)
