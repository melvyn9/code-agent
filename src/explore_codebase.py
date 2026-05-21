import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from cache import has_structure_changed, get_cached_summary, save_summary_to_cache

# Runs a Claude agent to map the repo structure and produce a structured summary; returns a cached result if the file structure hasn't changed.
async def explore_codebase():
    if not has_structure_changed():
        cached = get_cached_summary()
        if cached:
            print("Using cached codebase summary.")
            return cached
    
    print("Exploring codebase...")

    prompt = """
You are a senior software architect analyzing a codebase for the first time.
Explore the repository structure and produce a thorough summary.
INSTRUCTIONS:
- Do not use hyphens
- Do not use emojis

Cover the following:
- Overall purpose of the project
- Directory structure and what each folder contains
- Programming language(s) and frameworks used
- Main entry point(s)
- Key modules and their responsibilities
- Configuration files present (.env.example, Makefile, docker-compose.yml, etc.)
- External dependencies and what they are used for

Use the Glob tool to map the directory structure and Read tool to inspect key files like requirements.txt, package.json, main entry points, and any existing documentation.

Respond in this exact format:

PROJECT OVERVIEW:
<1-2 sentence description of what the project does>

LANGUAGE AND STACK:
<languages, frameworks, key libraries>

ENTRY POINTS:
<main files that run the project>

DIRECTORY STRUCTURE:
<key folders and what they contain>

KEY MODULES:
<each important file and its responsibility>

DEPENDENCIES:
<external libraries and what they are used for>

CONFIG FILES:
<any configuration files found>
"""
    try:
        result = ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                allowed_tools=["Read", "Glob", "Bash"],
                model="claude-sonnet-4-6"
            ),
        ):
            if hasattr(message, "result"):
                result = message.result
            elif hasattr(message, "output"):
                result = message.output
        
        save_summary_to_cache(result)
        print("Codebase exploration completed.")
        return result
    
    except Exception as e:
        print(f"Codebase exploration failed: {e}")
        return f"Exploration failed: {str(e)}"