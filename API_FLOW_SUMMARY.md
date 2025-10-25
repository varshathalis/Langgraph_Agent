# API Flow Summary - Visual Guide

## System Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENT                                  │
│                   (Browser, cURL, Python)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP POST
                             │ /run_agent
                             │ {"message": "calculate 2+2"}
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Server (8001)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ run_agent_api()                                          │  │
│  │ 1. Parse JSON request                                   │  │
│  │ 2. Create asyncio.Queue()                              │  │
│  │ 3. Start orchestrator_task() in background             │  │
│  │ 4. Return StreamingResponse(event_generator)           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Parallel Process: orchestrator_task()                          │
│  ├─ Call: run_agent(message, sse_send)                         │
│  └─ Put events into queue                                       │
│                                                                  │
│  Event Generator: event_generator(queue)                       │
│  ├─ Poll queue continuously                                    │
│  ├─ Format as SSE                                              │
│  └─ Yield to client in real-time                              │
└────────────────────────────┬─────────────────────────────────────┘
                             │ SSE Stream
                             │ event: thinking
                             │ data: {...}
                             │
                             │ event: agent_event
                             │ data: {...}
                             │
                             │ event: meta
                             │ data: {...}
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ run_agent(user_input, sse_send)                         │  │
│  │                                                           │  │
│  │ 1. Create HumanMessage from input                       │  │
│  │ 2. Emit thinking event                                  │  │
│  │ 3. Stream from agent.stream()                           │  │
│  │    ├─ Run llm_call node                                │  │
│  │    ├─ Run tool_node node                               │  │
│  │    ├─ Continue or END based on should_continue()       │  │
│  │    └─ Emit agent_event for each step                   │  │
│  │ 4. Extract final response                              │  │
│  │ 5. Emit completion event                               │  │
│  │ 6. Return final message                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Graph Workflow:                                                │
│  START                                                          │
│    │                                                            │
│    ▼                                                            │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  llm_call (Node)                                      │    │
│  │  • Takes: State with messages                         │    │
│  │  • Action: Invoke model with bound tools              │    │
│  │  • Returns: AIMessage with tool_calls or final text   │    │
│  └────────────────────┬──────────────────────────────────┘    │
│                       │                                         │
│            ┌──────────┴──────────┐                             │
│            │                     │                             │
│         YES │ tool_calls?        │ NO                          │
│            ▼                     ▼                             │
│  ┌──────────────────┐          END ─────────────▶ Return     │
│  │  tool_node       │                                          │
│  │  • Find tool     │                                          │
│  │  • Execute       │                                          │
│  │  • Return result │                                          │
│  └────────┬─────────┘                                          │
│           │                                                    │
│           └───────────────────────┐                           │
│                                   ▼                           │
│                        Back to llm_call                       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Detailed Flow Example: "calculate 2+2"

### Step 1: Client Sends Request
```bash
curl -X POST http://127.0.0.1:8001/run_agent \
  -H "Content-Type: application/json" \
  -d '{"message":"calculate 2+2"}'
```

### Step 2: API Receives and Processes
```
api.py: run_agent_api(req)
  1. data = await req.json()
     → {"message": "calculate 2+2"}

  2. queue = asyncio.Queue()
     → Create event queue

  3. async def sse_send(event, payload):
       → Callback to put events in queue

  4. asyncio.create_task(orchestrator_task())
     → Start background task

  5. return StreamingResponse(event_generator(queue))
     → Return stream handler
```

### Step 3: Agent Initialization
```
agent.run_agent("calculate 2+2", sse_send)

  1. Create messages = [HumanMessage(content="calculate 2+2")]

  2. Emit event:
     await sse_send("thinking",
       {"content": "Processing: calculate 2+2"})

     Queue → "thinking" event sent to client
```

**Client receives:**
```
event: thinking
data: {"content": "Processing: calculate 2+2"}

```

### Step 4: First LLM Call
```
Graph: llm_call node executes

llm_call(state)
  1. Get messages from state
  2. Invoke model:
     model.invoke([
       SystemMessage("You are helpful..."),
       HumanMessage("calculate 2+2")
     ])

  3. Azure OpenAI analyzes request:
     - Recognizes arithmetic task
     - Looks at bound tools
     - Decides to call "add" tool
     - Creates tool_call: add(a=2, b=2)

  4. Returns AIMessage with tool_calls:
     {
       "content": "",
       "tool_calls": [
         {
           "name": "add",
           "args": {"a": 2, "b": 2},
           "id": "call_abc123"
         }
       ]
     }

  5. Update state:
     state["messages"].append(AIMessage(...))
     state["llm_calls"] = 1
```

**Agent emits event:**
```
await sse_send("agent_event", {
  "llm_call": {
    "messages": [...],
    "llm_calls": 1
  }
})
```

**Client receives:**
```
event: agent_event
data: {"llm_call": {"messages": [...], "llm_calls": 1}}

```

### Step 5: Decision Point
```
Graph: should_continue(state)

Check last message for tool_calls:
  if last_message.tool_calls:
    → Return "tool_node"   (Continue loop)
  else:
    → Return END           (Finish)

Decision: "tool_node" (tool_calls exist)
```

### Step 6: Tool Execution
```
Graph: tool_node node executes

tool_node(state)
  1. Get last message from state
     → Has tool_calls: [{"name": "add", "args": {"a": 2, "b": 2}}]

  2. For each tool_call:
     tool_name = "add"
     tool_args = {"a": 2, "b": 2}

     tool = tools_by_name["add"]
     → Find add tool in tools dictionary

     result = tool.invoke({"a": 2, "b": 2})
     → mcp_tools.add_func(2, 2)
     → Returns: 4.0

  3. Create ToolMessage:
     ToolMessage(
       content="4.0",
       tool_call_id="call_abc123"
     )

  4. Return result:
     {"messages": [ToolMessage(content="4.0", ...)]}
```

**Agent emits event:**
```
await sse_send("agent_event", {
  "tool_node": {
    "messages": [...]
  }
})
```

**Client receives:**
```
event: agent_event
data: {"tool_node": {"messages": [{"content": "4.0"}]}}

```

### Step 7: Second LLM Call (Process Result)
```
Graph: Back to llm_call node

llm_call(state)  [Second iteration]
  1. Get messages:
     [
       HumanMessage("calculate 2+2"),
       AIMessage(tool_calls=...),
       ToolMessage("4.0")
     ]

  2. Invoke model with all messages:
     model.invoke([
       SystemMessage(...),
       HumanMessage("calculate 2+2"),
       AIMessage(tool_calls=...),
       ToolMessage("4.0")
     ])

  3. Azure OpenAI:
     - Sees tool result: 4.0
     - No more tools needed
     - Generates final response:
       "The result of 2 + 2 is 4."

  4. Returns AIMessage:
     {
       "content": "The result of 2 + 2 is 4.",
       "tool_calls": []  (or None)
     }

  5. Update state:
     state["llm_calls"] = 2
```

**Agent emits event:**
```
await sse_send("agent_event", {
  "llm_call": {
    "messages": [...],
    "llm_calls": 2
  }
})
```

**Client receives:**
```
event: agent_event
data: {"llm_call": {"messages": [...], "llm_calls": 2}}

```

### Step 8: Second Decision Point
```
Graph: should_continue(state)

Check last message for tool_calls:
  Last message: AIMessage with content="The result of 2 + 2 is 4."
  No tool_calls present

Decision: END (No more tools needed)
```

### Step 9: Stream Completion
```
agent.run_agent() completion:
  1. Emit completion event:
     await sse_send("thinking",
       {"content": "Agent processing complete"})

  2. Extract final message:
     ai_message = "The result of 2 + 2 is 4."

  3. In orchestrator_task():
     Put "[DONE]" in queue to signal completion

Event Generator:
  1. Receives "[DONE]"
  2. Emit final event:
     yield format_sse("meta",
       {"usage": {}, "info": "stream_complete"})
  3. Break from loop
  4. Connection closes
```

**Client receives:**
```
event: thinking
data: {"content": "Agent processing complete"}

event: meta
data: {"usage": {}, "info": "stream_complete"}

[Connection closed]
```

---

## Complete Event Stream Example

```
event: thinking
data: {"content": "Processing: calculate 2+2"}

event: agent_event
data: {"llm_call": {
  "messages": [
    {
      "type": "ai",
      "content": "",
      "tool_calls": [
        {
          "name": "add",
          "args": {"a": 2, "b": 2},
          "id": "call_abc123"
        }
      ]
    }
  ],
  "llm_calls": 1
}}

event: agent_event
data: {"tool_node": {
  "messages": [
    {
      "type": "tool",
      "content": "4.0",
      "tool_call_id": "call_abc123"
    }
  ]
}}

event: agent_event
data: {"llm_call": {
  "messages": [
    {
      "type": "ai",
      "content": "The result of 2 + 2 is 4.",
      "tool_calls": []
    }
  ],
  "llm_calls": 2
}}

event: thinking
data: {"content": "Agent processing complete"}

event: meta
data: {"usage": {}, "info": "stream_complete"}
```

---

## Key Components Reference

### 1. Queue-Based Event Streaming
- **Purpose:** Decouple agent processing from HTTP response
- **Mechanism:** asyncio.Queue acts as buffer
- **Benefit:** Real-time events, no buffering delays

### 2. State Management
- **Messages:** Full conversation history
- **LLM Calls:** Counter for monitoring loops
- **Operator.add:** Automatic message concatenation

### 3. Tool Integration
- **Binding:** Tools attached to model at initialization
- **Discovery:** Model knows tool signatures
- **Execution:** tools_by_name dictionary for lookup
- **Results:** Returned as ToolMessage objects

### 4. Graph Routing
- **Conditional Edges:** Based on tool_calls presence
- **Looping:** tool_node → llm_call → decision
- **Termination:** END when no more tool calls

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Time to First Event | 50-500ms | Depends on network |
| LLM Call Duration | 1-5s | Depends on input |
| Tool Execution | <100ms | Local operations |
| Event Throughput | 10-100 events/sec | Queue processing |
| Memory per Request | 1-10MB | Depends on history |

---

## Error Handling Flow

```
try:
  await run_agent(data['message'], sse_send)
except Exception as e:
  await sse_send("meta", {"error": str(e)})
finally:
  await queue.put("[DONE]")
```

If an error occurs:
1. Exception is caught
2. Error event sent to client
3. "[DONE]" signal sent
4. Stream closes gracefully

---

## Extended Example: Complex Query

**Input:** "What is 10 times 3 minus 5"

**Expected Flow:**

1. LLM determines: needs multiply(10, 3) = 30
2. Tool execution: Returns 30
3. LLM determines: needs subtract(30, 5) = 25
4. Tool execution: Returns 25
5. LLM generates: "10 times 3 minus 5 is 25"
6. No more tools needed
7. Stream completes

**Events Generated:** 7+ events showing each step

---

## Integration Points

### Client Integration
```javascript
const eventSource = new EventSource('/run_agent');
eventSource.addEventListener('thinking', (event) => {
  console.log('Thinking:', JSON.parse(event.data));
});
eventSource.addEventListener('agent_event', (event) => {
  console.log('Agent Step:', JSON.parse(event.data));
});
eventSource.addEventListener('meta', (event) => {
  console.log('Complete:', JSON.parse(event.data));
});
```

### Python Integration
```python
import asyncio
from agentic_components.agent import run_agent

async def main():
    events = []

    async def capture(event_name, payload):
        events.append((event_name, payload))
        print(f"[{event_name}] {payload}")

    result = await run_agent("calculate 5+5", capture)
    print(f"\nFinal: {result}")
    print(f"Total events: {len(events)}")

asyncio.run(main())
```

---

## Next Steps

1. **Monitor:** Add logging to track event flow
2. **Scale:** Implement batching for multiple requests
3. **Extend:** Add new tools and nodes
4. **Optimize:** Cache tool definitions
5. **Deploy:** Move to production server

