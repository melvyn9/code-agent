from claude_agent_sdk import query, ClaudeAgentOptions

async def run_summary(context):
    print("Running PR Summary...")

    prompt=f"""
You are a helpful code reviewer. Analyze the following pull request and write a concise plain-English summary of it.
Instructions
- DO NOT USE HYPHENS UNLESS ABSOLUTELY NECESSARY
- DO NOT USE EMOJIS UNLESS ABSOLUTELY NECESSARY
Your summary should cover:
- What this PR does (the intent, not just mechanics)
- Which parts of the codebase are affected
- Any notable risks or trade-offs introduced

Here is the pull request:
{context}

Respond in this exact format:
SUMMARY:
< 2-5 sentences here>
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

    print("Summary Complete.")
    return result