from claude_agent_sdk import query, ClaudeAgentOptions

# Runs a Claude agent to generate a complete ARCHITECTURE.md covering pipelines, modules, and data flow.
async def gen_architecture(codebase_summary):
    print("Generating ARCHITECTURE.md")

    prompt = f"""
You are a software architect writing technical documentation for a project.
Using the codebase summary below, write a complete ARCHITECTURE.md file.
Instructions:
- Do not use hyphens unless necessary

Cover the following:
- High-level system over
- How the two pipelines work (PR Review and onboarding)
- Module breakdown — each file and its responsibility
- Data flow — how data moves through the system from trigger to output
- External dependencies and why they are used
- GitHub Actions integration — how the workflow ties everything together

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
            model="claude-sonnet-4-6"
        ),
    ):
        if hasattr(message, "result"):
            result = message.result
    print("ARCHITECTURE.md generated.")
    return result