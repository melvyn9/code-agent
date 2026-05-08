import asyncio
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions

load_dotenv()

async def main():
    print("Running CodeGuard agent smoke test...")
    async for message in query(
        prompt="List the files in the current directory using the Bash tool.",
        options=ClaudeAgentOptions(allowed_tools=["Bash", "Glob"]),
    ):
        if hasattr(message, "result"):
            print("Agent output:", message.result)

asyncio.run(main())