import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def gen_contributing(codebase_summary):
    print("Generating CONTRIBUTING.md")

    prompt = f"""
You are a senior software engineer writing onboarding documentation for a new contributor.PermissionError
Using the codebase summary below, write a complete CONTRIBUTING.md file

INSTRUCTIONS:
- No hyphens unless necessary
- No emojis

Cover the following:
- Project overview (1-2 sentences)
- Prerequisities (language version, tools needed)
- How to clone and set up the project locally
- How to activate the virtual environment
- How to install dependencies
- Required environment variables and what they do
- How to run the project locally
- Branch naming conventions
- How to open a pull request
- What CodeGuard will automatically check on every PR

Codebase summary:
{codebase_summary}

Output rules:
- Output raw markdown only — no code fences, no backticks wrapping the document
- Do not include any explanation, preamble, or notes before or after the document
- Do not add any commentary about decisions you made
- The first line of your response must be the first line of the markdown document itself
"""
    result = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read"],
            model="claude-sonnet-4-6",
        ),
    ):
        if hasattr(message, "result"):
            result = message.result
    
    print("CONTRIBUTING.md generated.")
    return result