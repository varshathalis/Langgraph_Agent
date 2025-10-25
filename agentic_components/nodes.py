from langchain.messages import SystemMessage
from langchain.messages import ToolMessage
from agentic_components.state import MessagesState
from agentic_components.llm import model, _tools
from typing import Literal
from langgraph.graph import END
import json

# Create a mapping of tool names to tool objects
_tools_by_name = {tool.name: tool for tool in _tools}

def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""
    try:
        # model is already bound with tools
        response = model.invoke(
            [
                SystemMessage(
                    content="You are a helpful assistant tasked with performing arithmetic on a set of inputs. Use available tools when needed."
                )
            ]
            + state["messages"]
        )

        return {
            "messages": [response],
            "llm_calls": state.get('llm_calls', 0) + 1
        }
    except Exception as e:
        print(f"Error in llm_call: {e}")
        raise


def tool_node(state: dict):
    """Performs the tool call"""
    result = []

    try:
        last_message = state["messages"][-1]
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {"messages": result}

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            try:
                # Get tool from our mapping
                tool = _tools_by_name.get(tool_name)

                if tool:
                    # Execute the tool
                    observation = tool.invoke(tool_args)
                else:
                    observation = f"Tool '{tool_name}' not found. Available tools: {list(_tools_by_name.keys())}"

                result.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
            except Exception as e:
                result.append(ToolMessage(content=f"Error executing tool: {str(e)}", tool_call_id=tool_call["id"]))

        return {"messages": result}
    except Exception as e:
        print(f"Error in tool_node: {e}")
        return {"messages": result}


def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END