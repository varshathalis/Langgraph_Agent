from langchain_core.messages import HumanMessage
from agentic_components.graph import agent


def run(user_input):
    messages = [HumanMessage(content=user_input)]
    response = agent.invoke({"messages": messages})
    ai_message = response['messages'][1].content
    return ai_message
