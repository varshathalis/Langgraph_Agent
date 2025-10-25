"""
Simple test script for the API
"""
import asyncio
import sys

async def test_run_agent():
    """Test the run_agent function directly"""
    try:
        from agentic_components.agent import run_agent

        # Test with sse_send callback
        events = []

        async def sse_send(event, payload):
            events.append((event, payload))
            print(f"Event: {event}, Payload: {payload}")

        result = await run_agent("calculate 2+2", sse_send)
        print(f"\nFinal result: {result}")
        print(f"Total events: {len(events)}")

        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_run_agent())
    sys.exit(0 if success else 1)
