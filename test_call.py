import asyncio
from agent.llm.client import call_llm_json_async

async def main():
    try:
        raw = await call_llm_json_async('Analyze the agent/web.py file and summarize the functions inside it using a numbered list.')
        print("RAW RESPONSE START")
        print(raw)
        print("RAW RESPONSE END")
    except Exception as e:
        print("ERROR:", str(e))

if __name__ == "__main__":
    asyncio.run(main())
