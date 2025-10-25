"""
Unified MCP Server
------------------
This server automatically loads and registers tools from:
    - tools/github_tools.py
    - tools/jira_tools.py
    - tools/notion_tools.py

Run with:
    python server.py
"""

# Fix OpenMP runtime conflict and Windows asyncio issues
import os
import sys
import asyncio

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import importlib
import uvicorn
from fastmcp import FastMCP


def create_mcp_server() -> FastMCP:
    """Create a single MCP server and load all tool modules."""
    mcp = FastMCP("IntegratedTools")

    tool_modules = ["math_tools", "generic_tools"]

    for module_name in tool_modules:
        module_path = f"agentic_components.tools.{module_name}"
        try:
            module = importlib.import_module(module_path)

            if hasattr(module, "register_tools"):
                module.register_tools(mcp)
                print(f"✅ Registered tools from {module_path}")
            else:
                print(f"⚠️ No register_tools() found in {module_path}")

        except ModuleNotFoundError as e:
            print(f"⚠️ Skipping missing tool module: {module_path} ({e})")

    print("🧩 All available tools registered successfully.")
    return mcp


if __name__ == "__main__":
    port = 8080
    path = "/mcp"

    mcp = create_mcp_server()
    app = mcp.http_app(path=path)

    print(f"🌐 MCP server running at: http://localhost:{port}{path}")
    uvicorn.run(app, host="0.0.0.0", port=port)