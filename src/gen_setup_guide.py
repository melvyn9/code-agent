from claude_agent_sdk import query, ClaudeAgentOptions

# Runs a Claude agent to generate a complete SETUP.md with step-by-step local setup instructions.
async def gen_setup_guide(codebase_summary):
    print("Generating SETUP.md")
    prompt = f"""
You are a senior software engineer writing a setup guide for a new developer joining the project.
Using the codebase summary below, write a complete SETUP.md file.
Instructions:
- Do not use hyphens unless necessary

Cover the following:
- Prerequisites (exact versions of tools needed)
- Step-by-step local setup instructions
- How to create and populate the .env file with all required variables
- How to run the project locally for both pipelines (PR review and onboarding)
- How to run against a real PR for testing
- Common setup mistakes and how to fix them

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
            model="claude-sonnet-4-6",
            allowed_tools=["Read"]
        ),
    ):
        if hasattr(message, "result"):
            result = message.result

    print("SETUP.md generated.")
    return result