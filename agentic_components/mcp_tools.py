"""
MCP Tools Integration
---------------------
Loads tools from the MCP server and converts them to LangChain tools.
"""

import json
import httpx
import asyncio
from typing import Any, Dict, List
from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel, Field, create_model

# MCP Server endpoint
MCP_SERVER_URL = "http://127.0.0.1:8080/mcp"

async def fetch_mcp_tools() -> List[Dict[str, Any]]:
    """Fetch available tools from the MCP server"""
    try:
        async with httpx.AsyncClient() as client:
            # Attempt to fetch tools from the MCP server
            response = await client.post(
                f"{MCP_SERVER_URL}/tools/list",
                json={},
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("tools", [])
    except Exception as e:
        print(f"Warning: Could not fetch tools from MCP: {e}")

    return []

async def call_mcp_tool(tool_name: str, **kwargs) -> str:
    """Call a tool via the MCP server"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/tools/call",
                json={
                    "name": tool_name,
                    "arguments": kwargs
                },
                timeout=10.0
            )
            if response.status_code == 200:
                result = response.json()
                return json.dumps(result)
            else:
                return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error calling tool: {str(e)}"

async def create_langchain_tools() -> List[Tool]:
    """Create LangChain tools from MCP server"""
    tools = []

    try:
        mcp_tools = await fetch_mcp_tools()

        for tool_def in mcp_tools:
            tool_name = tool_def.get("name", "")
            tool_desc = tool_def.get("description", "")
            tool_params = tool_def.get("inputSchema", {}).get("properties", {})

            # Create a function for this tool
            async def tool_func(tool_n=tool_name, **kwargs) -> str:
                return await call_mcp_tool(tool_n, **kwargs)

            # Create LangChain Tool
            def make_tool_func(tn):
                def tool_func(**kw):
                    return asyncio.run(call_mcp_tool(tn, **kw))
                return tool_func

            tool = Tool(
                name=tool_name,
                description=tool_desc,
                func=make_tool_func(tool_name)
            )
            tools.append(tool)

    except Exception as e:
        print(f"Error creating LangChain tools: {e}")

    return tools

# Default built-in tools (math operations)
def get_builtin_tools() -> List[StructuredTool]:
    """Get built-in tools that don't require MCP server"""

    def add_func(a: float, b: float) -> float:
        """Add two numbers together"""
        return a + b

    def subtract_func(a: float, b: float) -> float:
        """Subtract b from a"""
        return a - b

    def multiply_func(a: float, b: float) -> float:
        """Multiply two numbers together"""
        return a * b

    def divide_func(a: float, b: float) -> float:
        """Divide a by b"""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    # Create tools with proper schema
    add_tool = StructuredTool.from_function(
        func=add_func,
        name="add",
        description="Add two numbers together"
    )

    subtract_tool = StructuredTool.from_function(
        func=subtract_func,
        name="subtract",
        description="Subtract b from a"
    )

    multiply_tool = StructuredTool.from_function(
        func=multiply_func,
        name="multiply",
        description="Multiply two numbers together"
    )

    divide_tool = StructuredTool.from_function(
        func=divide_func,
        name="divide",
        description="Divide a by b"
    )

    tools = [add_tool, subtract_tool, multiply_tool, divide_tool]

    return tools
