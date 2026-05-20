import asyncio
import os
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions
from github_client import get_changed_files, post_pr_comment

load_dotenv()

async def main():
    print("Running CodeGuard agent smoke test...")
    async for message in query(
        prompt="List the files in the current directory using the Bash tool.",
        options=ClaudeAgentOptions(
            allowed_tools=["Bash", "Glob"],
            model="claude-sonnet-4-6"
        )
    ):
        if hasattr(message, "result"):
            print("Agent output:", message.result)

asyncio.run(main())

pr_number = os.getenv("PR_NUMBER", "1")  # replace 1 with your actual test PR number

print("Changed files:", get_changed_files(pr_number))
post_pr_comment(pr_number, "CodeGuard is alive — Phase 1 complete!")