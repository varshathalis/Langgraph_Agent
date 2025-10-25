# LangGraph Agent with MCP Server Integration

A production-ready agentic system that combines LangGraph for orchestration with Model Context Protocol (MCP) servers for tool execution. This system provides real-time SSE (Server-Sent Events) streaming of agent execution, allowing you to see the agent's thinking process and tool usage in real-time.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Setup & Installation](#setup--installation)
4. [Running the System](#running-the-system)
5. [API Flow](#api-flow)
6. [File Documentation](#file-documentation)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Components

The project consists of three main components that work together:

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Server (8001)                    │
│  Handles HTTP requests and SSE streaming to clients             │
└─────────────────────┬───────────────────────────────────────────┘
                      │ JSON Request
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  State Management (MessagesState)                        │  │
│  │  - Maintains conversation history                        │  │
│  │  - Tracks LLM calls                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Graph Nodes:                                                   │
│  ┌─────────────────┐        ┌──────────────────┐               │
│  │   llm_call      │───────▶│   tool_node      │               │
│  │  (Azure OpenAI) │        │  (Execute tools) │               │
│  └─────────────────┘        └──────────────────┘               │
│         ▲                            │                          │
│         └────────────────────────────┘                          │
│  Conditional routing based on tool calls                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Tool calls
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MCP Server (8080)                              │
│  Provides tool implementations:                                 │
│  - Math tools (add, subtract, multiply, divide)                │
│  - Generic tools (greeting handler)                            │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Client HTTP Request
    │
    ▼
POST /run_agent {"message": "calculate 2+2"}
    │
    ├─▶ SSE Event: thinking → Processing: calculate 2+2
    │
    ├─▶ Agent processes with LLM
    │   - Determines tools needed
    │   - Creates tool calls
    │
    ├─▶ SSE Event: agent_event → LLM response with tool_calls
    │
    ├─▶ Tool execution
    │   - Calls add(2, 2) → 4
    │
    ├─▶ SSE Event: agent_event → Tool result
    │
    ├─▶ LLM processes result
    │   - Generates final response
    │
    ├─▶ SSE Event: thinking → Agent processing complete
    │
    ├─▶ SSE Event: meta → stream_complete
    │
    ▼
Client receives full response stream
```

---

## Project Structure

```
Langgraph_Agent/
│
├── api.py                           # FastAPI SSE server (main entry point)
├── server.py                        # MCP server setup and registration
├── test_api.py                      # Testing script for agent functionality
│
├── agentic_components/              # Core agent components
│   ├── __init__.py
│   ├── agent.py                     # Main agent runner with streaming support
│   ├── graph.py                     # LangGraph workflow definition
│   ├── nodes.py                     # Graph nodes (llm_call, tool_node)
│   ├── state.py                     # State management (MessagesState)
│   ├── llm.py                       # LLM configuration (Azure OpenAI)
│   ├── mcp_tools.py                 # Tool definitions for agent
│   │
│   └── tools/                       # Tool implementations for MCP server
│       ├── __init__.py
│       ├── math_tools.py            # Math operations (add, subtract, etc.)
│       └── generic_tools.py         # Generic tools (greeting handler)
│
├── .env                             # Environment variables (not in repo)
└── README.md                        # This file
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Azure OpenAI API credentials
- Virtual environment (recommended)

### Installation Steps

1. **Clone and navigate to project:**
   ```bash
   cd Langgraph_Agent
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create `.env` file in project root:
   ```
   AZURE_OPENAI_API_KEY=your_api_key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_VERSION=2024-12-01-preview
   AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
   OPENAI_MODEL=gpt-4o-mini
   ```

---

## Running the System

### Quick Start (All-in-One)

```bash
# Terminal 1: Start MCP Server
python server.py

# Terminal 2: Start FastAPI Server
python api.py

# Terminal 3: Test the agent
python test_api.py
```

### Individual Server Startup

**MCP Server (Port 8080)**
```bash
python server.py
```
Output:
```
✅ Registered tools from agentic_components.tools.math_tools
✅ Registered tools from agentic_components.tools.generic_tools
🧩 All available tools registered successfully.
🌐 MCP server running at: http://localhost:8080/mcp
```

**FastAPI Server (Port 8001)**
```bash
python api.py
```
Output:
```
Starting LangGraph MCP Agent API on http://localhost:8001 ...
INFO:     Uvicorn running on http://127.0.0.1:8001
```

---

## API Flow

### Complete Request/Response Cycle

#### 1. **Client Request**
```bash
curl --location 'http://127.0.0.1:8001/run_agent' \
  --header 'Content-Type: application/json' \
  --data '{"message":"calculate 2+2"}'
```

#### 2. **API Processing**

```
api.py: run_agent_api()
  ├─ Receives JSON request with message
  ├─ Creates asyncio.Queue for event streaming
  ├─ Starts orchestrator_task() in background
  ├─ Returns StreamingResponse
  │
  └─ orchestrator_task() runs:
      ├─ Calls agent.run_agent(message, sse_send)
      └─ Emits events to queue
```

#### 3. **Event Generator**

```
event_generator(queue)
  ├─ Continuously polls queue
  ├─ Formats events as SSE
  ├─ Sends to client in real-time
  └─ Closes on "[DONE]" signal
```

#### 4. **Agent Processing**

```
agent.run_agent()
  ├─ Emit: thinking → "Processing: calculate 2+2"
  │
  ├─ Graph: llm_call node
  │  └─ Azure OpenAI decides to call 'add' tool
  │
  ├─ Emit: agent_event → {llm_call: {..., tool_calls: [{name: 'add', args: {a: 2, b: 2}}]}}
  │
  ├─ Graph: tool_node node
  │  └─ Execute: add(2, 2) → 4.0
  │
  ├─ Emit: agent_event → {tool_node: {..., result: 4.0}}
  │
  ├─ Graph: llm_call node (second iteration)
  │  └─ Process result, generate final response
  │
  ├─ Emit: agent_event → {llm_call: {..., content: "The result is 4"}}
  │
  └─ Emit: thinking → "Agent processing complete"
```

#### 5. **Stream Completion**

```
├─ Emit: meta → {usage: {}, info: "stream_complete"}
└─ Connection closes
```

---

## File Documentation

### Core Files

#### **api.py** (FastAPI SSE Server)

**Purpose:** HTTP endpoint for agent interaction with real-time streaming

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `format_sse(event, data)` | Formats event data as SSE message |
| `serialize_obj(obj)` | Converts complex objects to JSON-serializable format |
| `event_generator(queue)` | Async generator that yields formatted SSE events |
| `run_agent_api(req)` | Main endpoint - POST /run_agent |

**Request/Response:**

```python
# Request
POST /run_agent
Content-Type: application/json
{"message": "what is 5 times 3"}

# Response (SSE Stream)
event: thinking
data: {"content": "Processing: what is 5 times 3"}

event: agent_event
data: {"llm_call": {...}}

event: agent_event
data: {"tool_node": {...}}

event: meta
data: {"usage": {}, "info": "stream_complete"}
```

**Configuration:**
- Host: `127.0.0.1`
- Port: `8001`
- Media Type: `text/event-stream`
- Reload: `True` (development) / `False` (production)

---

#### **server.py** (MCP Server)

**Purpose:** Manages and serves tool implementations via MCP protocol

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `create_mcp_server()` | Initializes FastMCP instance and registers tools |
| Dynamic tool loading | Imports and registers tools from tool modules |

**Tool Registration Flow:**

```python
create_mcp_server()
  ├─ FastMCP("IntegratedTools")
  │
  ├─ For each tool module in ["math_tools", "generic_tools"]:
  │  ├─ Import module
  │  ├─ Call module.register_tools(mcp)
  │  └─ Register all tools
  │
  └─ Return configured mcp server
```

**Registered Tools:**
- **math_tools:** add, subtract, multiply, divide, calculate
- **generic_tools:** handle_greeting

**Configuration:**
- Host: `0.0.0.0`
- Port: `8080`
- Endpoint: `/mcp`

---

#### **agent.py** (Agent Runner)

**Purpose:** Executes the agent with optional SSE streaming

**Key Functions:**

| Function | Purpose |
| -------- | ------- |
| `run_agent(user_input, sse_send)` | Main async function that runs the graph with streaming |

**Signature:**
```python
async def run_agent(user_input: str, sse_send: Callable = None) -> str:
    """
    Args:
        user_input: The user's message/prompt
        sse_send: Async callback for streaming events
                 sse_send(event_name: str, payload: dict)

    Returns:
        Final response string from the agent
    """
```

**Execution Steps:**
1. Create initial HumanMessage from user input
2. Emit "thinking" event if sse_send provided
3. Execute agent.stream() with event callbacks
4. Extract final message from state
5. Emit completion event
6. Return final response

**Event Examples:**
```python
await sse_send("thinking", {"content": "Processing: calculate 2+2"})
await sse_send("agent_event", {"llm_call": {...}})
await sse_send("agent_event", {"tool_node": {...}})
await sse_send("thinking", {"content": "Agent processing complete"})
```

---

#### **graph.py** (LangGraph Workflow)

**Purpose:** Defines the agent's decision graph and node connections

**Graph Structure:**

```
START
  │
  ▼
llm_call
  │
  ├─ If tool_calls exist → tool_node → llm_call (loop)
  └─ If no tool_calls → END
```

**Node Connections:**

| From | To | Condition |
|------|----|---------|
| START | llm_call | Always |
| llm_call | tool_node | If message has tool_calls |
| llm_call | END | If no tool_calls |
| tool_node | llm_call | Always |

**Compilation:**
```python
agent = agent_builder.compile()
```

The compiled graph can be used with:
- `.invoke()` - Single execution
- `.stream()` - Event streaming (used for SSE)

---

#### **nodes.py** (Graph Nodes)

**Purpose:** Implements individual graph processing nodes

**Node Functions:**

##### `llm_call(state: dict) -> dict`
- **Input:** State with messages list
- **Process:**
  - Invokes Azure OpenAI with bound tools
  - Adds system message about arithmetic
  - Returns AIMessage with potential tool_calls
- **Output:** `{"messages": [AIMessage], "llm_calls": count}`

```python
# Node logic
response = model.invoke([SystemMessage(...)] + state["messages"])
return {"messages": [response], "llm_calls": count + 1}
```

##### `tool_node(state: dict) -> dict`
- **Input:** State with messages, last message has tool_calls
- **Process:**
  - Extracts tool_calls from last message
  - Looks up tool by name in tools_by_name dict
  - Executes tool with provided arguments
  - Creates ToolMessage with result
- **Output:** `{"messages": [ToolMessage, ...]}`

```python
# Node logic
for tool_call in last_message.tool_calls:
    tool = tools_by_name[tool_call["name"]]
    result = tool.invoke(tool_call["args"])
    messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
return {"messages": messages}
```

##### `should_continue(state: MessagesState) -> Literal["tool_node", END]`
- **Input:** Current state
- **Logic:**
  - Check if last message has tool_calls
  - Return "tool_node" to continue looping
  - Return END to finish
- **Output:** "tool_node" or END

```python
# Node logic
if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
    return "tool_node"
return END
```

---

#### **state.py** (State Management)

**Purpose:** Defines the agent's state schema

**MessagesState Class:**
```python
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
```

**Fields:**
- **messages:** List of conversation messages
  - Annotated with `operator.add` for automatic concatenation
  - Contains HumanMessage, AIMessage, ToolMessage types
  - Maintains full conversation history

- **llm_calls:** Counter for LLM invocations
  - Tracks number of times model was called
  - Helps monitor agent iterations

---

#### **llm.py** (LLM Configuration)

**Purpose:** Sets up Azure OpenAI model with tool binding

**Initialization:**

```python
# Load environment variables
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = "2024-12-01-preview"
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Create base model
_base_model = AzureChatOpenAI(
    openai_api_key=AZURE_API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    openai_api_version=AZURE_API_VERSION,
    model=AZURE_DEPLOYMENT_NAME,
    temperature=0.2  # Lower temperature for deterministic behavior
)

# Bind tools to model
_tools = get_builtin_tools()
model = _base_model.bind_tools(_tools)
```

**Available Tools:**
- add(a: float, b: float) → float
- subtract(a: float, b: float) → float
- multiply(a: float, b: float) → float
- divide(a: float, b: float) → float

---

#### **mcp_tools.py** (Tool Definitions)

**Purpose:** Defines tools for the agent using LangChain StructuredTool

**Tool Creation:**

```python
def get_builtin_tools() -> List[StructuredTool]:
    """Returns list of StructuredTool objects"""

    # Each tool is created using StructuredTool.from_function()
    add_tool = StructuredTool.from_function(
        func=add_func,
        name="add",
        description="Add two numbers together"
    )
    # ... similar for subtract, multiply, divide
```

**Tool Features:**
- Type hints for arguments (float, float)
- Clear descriptions for LLM
- Return types defined
- Error handling for edge cases (e.g., division by zero)

---

#### **test_api.py** (Testing Script)

**Purpose:** Direct testing of agent with async callbacks

**Usage:**
```bash
python test_api.py
```

**Test Flow:**
```python
async def test_run_agent():
    events = []

    async def sse_send(event, payload):
        events.append((event, payload))
        print(f"Event: {event}, Payload: {payload}")

    result = await run_agent("calculate 2+2", sse_send)
    print(f"Final result: {result}")
    print(f"Total events: {len(events)}")
```

**Output Examples:**
```
Event: thinking, Payload: {'content': 'Processing: calculate 2+2'}
Event: agent_event, Payload: {'llm_call': {...}}
Event: agent_event, Payload: {'tool_node': {...}}
Event: thinking, Payload: {'content': 'Agent processing complete'}

Final result: The result of 2 + 2 is 4.
Total events: 5
```

---

### Tool Files

#### **tools/math_tools.py**

**Purpose:** Math operation tools for MCP server

**Registered Functions:**
- `add(a: float, b: float)` → Returns sum
- `subtract(a: float, b: float)` → Returns difference
- `multiply(a: float, b: float)` → Returns product
- `divide(a: float, b: float)` → Returns quotient (raises on div by zero)
- `calculate(expression: str)` → Returns JSON string with result

**Registration:**
```python
def register_tools(mcp: FastMCP):
    @mcp.tool
    def add(a: float, b: float):
        """Add two numbers and return the sum."""
        return a + b
    # ... more tools
```

---

#### **tools/generic_tools.py**

**Purpose:** Conversational tools for MCP server

**Registered Functions:**
- `handle_greeting(text: str, openai_api_key: str, user_name: Optional[str])` → Returns greeting response

**Features:**
- Detects greeting keywords (hi, hello, hey, etc.)
- Uses Azure OpenAI to generate natural responses
- Supports optional user name
- Error handling for API failures

---

## Usage Examples

### Example 1: Simple Calculation

**Request:**
```bash
curl -X POST http://127.0.0.1:8001/run_agent \
  -H "Content-Type: application/json" \
  -d '{"message":"calculate 2+2"}'
```

**Response Stream:**
```
event: thinking
data: {"content": "Processing: calculate 2+2"}

event: agent_event
data: {"llm_call": {"messages": [{"tool_calls": [{"name": "add", "args": {"a": 2, "b": 2}}]}]}}

event: agent_event
data: {"tool_node": {"messages": [{"content": "4.0"}]}}

event: agent_event
data: {"llm_call": {"messages": [{"content": "The result of 2 + 2 is 4."}]}}

event: thinking
data: {"content": "Agent processing complete"}

event: meta
data: {"usage": {}, "info": "stream_complete"}
```

### Example 2: Complex Calculation

**Request:**
```bash
curl -X POST http://127.0.0.1:8001/run_agent \
  -H "Content-Type: application/json" \
  -d '{"message":"what is 10 multiplied by 5"}'
```

**Expected Flow:**
1. Agent recognizes multiplication is needed
2. Calls `multiply(10, 5)`
3. Gets result `50`
4. Formats response: "10 multiplied by 5 is 50"

### Example 3: Testing with Python

```python
import asyncio
from agentic_components.agent import run_agent

async def test():
    events = []

    async def capture_event(event_name, payload):
        events.append((event_name, payload))
        print(f"[{event_name}] {payload.get('content', 'Event emitted')}")

    result = await run_agent("divide 100 by 4", capture_event)
    print(f"\nFinal Answer: {result}")
    print(f"Total Events: {len(events)}")

asyncio.run(test())
```

---

## Troubleshooting

### Issue: Port Already in Use

**Problem:** "Port 8001 already in use"

**Solution:**
```bash
# Kill existing process
lsof -ti:8001 | xargs kill -9  # macOS/Linux
taskkill /PID <pid> /F  # Windows

# Or use different port
python -c "import uvicorn; uvicorn.run('api:app', host='127.0.0.1', port=8002)"
```

### Issue: Azure OpenAI Authentication Failed

**Problem:** "Invalid API key or endpoint"

**Solution:**
1. Verify `.env` file exists with correct values
2. Check credentials in Azure Portal
3. Test API key separately:
   ```python
   from langchain_openai import AzureChatOpenAI
   model = AzureChatOpenAI(
       openai_api_key="your_key",
       azure_endpoint="your_endpoint",
       openai_api_version="2024-12-01-preview",
       model="deployment_name"
   )
   print(model.invoke("test"))
   ```

### Issue: Agent Doesn't Call Tools

**Problem:** Agent generates response without calling tools

**Causes & Solutions:**
1. **Tools not bound:** Verify `model.bind_tools()` in `llm.py`
2. **Temperature too high:** Lower temperature (0.2 is default)
3. **Prompt unclear:** Make request more specific (e.g., "calculate 2+2" not "math")

### Issue: SSE Stream Ends Prematurely

**Problem:** Stream closes after first event

**Solution:**
1. Restart API server without reload:
   ```bash
   python -c "import uvicorn; uvicorn.run('api:app', host='127.0.0.1', port=8001, reload=False)"
   ```
2. Check for unhandled exceptions in agent
3. Increase timeout in `event_generator`:
   ```python
   msg = await asyncio.wait_for(queue.get(), timeout=5.0)
   ```

### Issue: Tools Not Found

**Problem:** "Tool 'add' not found"

**Solution:**
1. Verify `mcp_tools.py` defines the tool
2. Check tool is added to `_tools` list in `llm.py`
3. Rebuild tools mapping:
   ```python
   _tools_by_name = {tool.name: tool for tool in _tools}
   ```

### Debug Mode

Enable detailed logging:

```python
# In api.py
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add to event_generator
logger.debug(f"Queue size: {queue.qsize()}")
logger.debug(f"Yielding event: {event_name}")
```

---

## Performance Optimization

### Recommendations

1. **Caching:** Cache tool definitions
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1)
   def get_tools():
       return get_builtin_tools()
   ```

2. **Connection Pooling:** Use connection pools for Azure OpenAI
   ```python
   from httpx import AsyncClient
   client = AsyncClient(limits=Limits(max_connections=10))
   ```

3. **Batch Requests:** Group multiple requests
   ```python
   # Process multiple messages in batch
   await asyncio.gather(
       run_agent("calc 2+2"),
       run_agent("calc 3*4"),
       run_agent("calc 10/2")
   )
   ```

4. **Rate Limiting:** Implement request throttling
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   @app.post("/run_agent")
   @limiter.limit("10/minute")
   async def run_agent_api(req: Request):
   ```

---

## Contributing

### Adding New Tools

1. Create tool function with clear docstring:
   ```python
   def my_tool(arg1: str, arg2: int) -> str:
       """Tool description here."""
       return result
   ```

2. Register in `mcp_tools.py`:
   ```python
   my_tool = StructuredTool.from_function(
       func=my_tool,
       name="my_tool",
       description="What this tool does"
   )
   tools.append(my_tool)
   ```

3. Add to server tools:
   ```python
   # In tools/my_tools.py
   def register_tools(mcp: FastMCP):
       @mcp.tool
       def my_tool(arg1: str, arg2: int):
           """Tool description."""
           return result
   ```

### Extending Agent Logic

Modify `nodes.py` to add custom processing:

```python
def my_custom_node(state: dict):
    """Custom node logic"""
    # Access state
    messages = state["messages"]
    # Process
    result = custom_process(messages)
    # Return updated state
    return {"messages": [result]}

# Add to graph in graph.py
agent_builder.add_node("my_node", my_custom_node)
agent_builder.add_edge("llm_call", "my_node")
```

---

## Key Technologies

| Technology | Version | Purpose |
|-----------|---------|---------|
| LangGraph | Latest | Orchestration & agentic workflows |
| LangChain | Latest | LLM integrations & tools |
| FastAPI | 0.100+ | REST API & SSE streaming |
| Uvicorn | 0.20+ | ASGI server |
| FastMCP | Latest | Model Context Protocol server |
| Azure OpenAI | 2024-12-01 | LLM provider |
| Pydantic | 2.0+ | Data validation |
| Python | 3.10+ | Runtime |

---

## License

MIT License

---

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review test_api.py for usage patterns
3. Check Azure OpenAI documentation for API issues
4. Review LangGraph documentation for agent logic

---

## Next Steps

1. **Deployment:** Deploy to cloud (AWS Lambda, Azure Functions, etc.)
2. **Monitoring:** Add logging and metrics
3. **Scale:** Implement caching and rate limiting
4. **Extend:** Add more tools and capabilities
5. **Test:** Develop comprehensive test suite

