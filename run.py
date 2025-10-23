from langchain_core.messages import HumanMessage
from graph import agent

if __name__ == "__main__":
    print("🤖 MCP Agent is ready. Type your message below (or 'exit' to quit):\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("👋 Exiting the chat. Goodbye!")
            break

        # Wrap user input into LangChain's message format
        messages = [HumanMessage(content=user_input)]

        # Invoke your LangGraph agent
        response = agent.invoke({"messages": messages})

        # Print all returned messages (including model responses)
        print("\n--- Response ---")
        for m in response["messages"]:
            m.pretty_print()
        print("----------------\n")
