from langchain_core.messages import HumanMessage
from agentic_components.graph import agent


async def run_agent(user_input, sse_send=None):
    """
    Run the agent with optional SSE streaming callback.

    Args:
        user_input: The user's message/prompt
        sse_send: Async callback function(event: str, payload: dict) for streaming events

    Returns:
        The final AI message response
    """
    messages = [HumanMessage(content=user_input)]

    # Stream events from the agent if callback provided
    if sse_send:
        await sse_send("thinking", {"content": f"Processing: {user_input}"})

    # Invoke agent with streaming if available
    if sse_send and hasattr(agent, 'stream'):
        # Use streaming if available
        final_state = None
        for event in agent.stream({"messages": messages}):
            if sse_send:
                await sse_send("agent_event", event)
            final_state = event

        # Extract the final response - event structure is {key: {messages: [...]}}
        if final_state:
            # Get the last dict in the stream events
            for key, state in final_state.items():
                if isinstance(state, dict) and 'messages' in state:
                    response = state
                    break
            else:
                response = final_state
        else:
            response = {}
    else:
        # Fallback to regular invoke
        response = agent.invoke({"messages": messages})

    if sse_send:
        await sse_send("thinking", {"content": "Agent processing complete"})

    # Extract final message content
    if isinstance(response, dict) and 'messages' in response and response['messages']:
        ai_message = response['messages'][-1].content
    else:
        ai_message = "No response from agent"

    return ai_message
