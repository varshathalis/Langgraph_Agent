# server.py
import os
from fastmcp import FastMCP

from agentic_components.tools.math_tools import register_math_tools

if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", 8000))

    mcp = FastMCP("Math MCP Server")
    register_math_tools(mcp)

    print("\n" + "=" * 60)
    print("Math MCP Server")
    print("=" * 60)
    print(f"Endpoint: http://127.0.0.1:{port}/mcp")
    print("Tools: add, subtract, multiply, divide, calculate")
    print("=" * 60 + "\n")

    mcp.run(transport="http", host="127.0.0.1", port=port)
