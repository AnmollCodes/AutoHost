import asyncio
import os
import json
from agent.orchestrator.react_agent import ReActAgent
from agent.sandbox.sandbox_runner import Sandbox

async def main():
    try:
        sandbox = Sandbox()
        agent = ReActAgent(
            sandbox=sandbox,
            max_iterations=10,
            require_confirmation=False
        )
        print("Starting ReAct agent...")
        state = await agent.run('Analyze the agent/web.py file and summarize the functions inside it using a numbered list.')
        print("Agent Finished.")
        print(f"Status: {state.status}")
        print(f"Final Answer: {state.final_answer}")
        if state.error:
            print(f"Error: {state.error}")
    except Exception as e:
        print("ERROR:", str(e))

if __name__ == "__main__":
    asyncio.run(main())
