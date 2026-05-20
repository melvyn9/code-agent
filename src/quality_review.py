import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_quality_review(context):
    print("Running quality review...")

    prompt = f"""
You are an experienced software engineer doing a code review. Analyze the following pull request and identify code quality issues.PermissionError
Instructions
- DO NOT USE HYPHENS UNLESS ABSOLUTELY NECESSARY
- DO NOT USE EMOJIS UNLESS ABSOLUTELY NECESSARY
Look specifically for:
- Functions that are too long or too complex
- Inconsistent naming conventions
- Missing or weak error handling
- Duplicated logic that could be extracted
- Missing tests for new code
- Poor or missing comments on complex logic
- Hardcoded values that should be constants or config

Here is the pull request:
{context}

Respond in this exact format:
QUALITY NOTES:
- [TYPE: COMPLEXITY/NAMING/ERROR_HANDLING/DUPLICATION/TESTING/COMMENTS/CONFIG] filename:line_number - description of issue

If no issues are found, respond with:
QUALITY NOTES:
- No quality issues found
"""
    
    result = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read"],
            model="claude-sonnet-4-6"
        ),
    ):
        if hasattr(message, "result"):
            result = message.result
    print("Quality review complete.")
    return result