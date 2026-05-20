# Title: Phase 3 — Onboarding Agent

## Goal
Build an onboarding agent that detects when a repository is new and automatically generates three documentation files — CONTRIBUTING.md, ARCHITECTURE.md, and SETUP.md — by exploring the codebase and committing them directly to the repo. Also support a `/onboard` manual re-trigger via PR comment.

---

## Work Done

### Project structure
```
src/
├── main.py                  # updated — extracts run_onboarding(), adds issue_comment routing
├── github_client.py         # updated — adds commit_file() helper
├── gather_context.py        # unchanged
├── security_scan.py         # unchanged
├── quality_review.py        # unchanged
├── summarize_pr.py          # unchanged
├── post_results.py          # unchanged
├── detect_new_repo.py       # new — checks if CONTRIBUTING.md exists
├── explore_codebase.py      # new — maps repo structure, stack, entry points
├── gen_contributing.py      # new — generates CONTRIBUTING.md
├── gen_architecture.py      # new — generates ARCHITECTURE.md
└── gen_setup_guide.py       # new — generates SETUP.md
```

### Key files

**`src/detect_new_repo.py`** — checks if CONTRIBUTING.md exists, gates the onboarding pipeline
```python
import os
from github_client import get_repo

def is_new_repo():
    print("Checking if repo needs onboarding...")
    repo = get_repo()
    try:
        repo.get_contents("CONTRIBUTING.md")
        print("CONTRIBUTING.md already exists. Skipping onboarding.")
        return False
    except Exception:
        print("CONTRIBUTING.md not found. Onboarding needed.")
        return True
```

**`src/explore_codebase.py`** — agent maps the full repo using Read, Glob, and Bash tools
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def explore_codebase():
    print("Exploring codebase...")
    prompt = """
You are a software architect analyzing a codebase for the first time.
Explore the repository structure and produce a thorough summary.

Cover the following:
- Overall purpose of the project
- Directory structure and what each folder contains
- Programming language(s) and frameworks used
- Main entry point(s)
- Key modules and their responsibilities
- Configuration files present
- External dependencies and what they are used for

Use the Glob tool to map the directory structure and the Read tool to inspect
key files like requirements.txt, package.json, main entry points, and any
existing documentation.

Respond in this exact format:

PROJECT OVERVIEW:
LANGUAGE AND STACK:
ENTRY POINTS:
DIRECTORY STRUCTURE:
KEY MODULES:
DEPENDENCIES:
CONFIG FILES:
"""
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
    print("Codebase exploration complete.")
    return result
```

**`src/gen_contributing.py`** — generates CONTRIBUTING.md from codebase summary
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def gen_contributing(codebase_summary):
    print("Generating CONTRIBUTING.md...")
    prompt = f"""
You are a senior software engineer writing onboarding documentation for a new contributor.
Using the codebase summary below, write a complete CONTRIBUTING.md file.

Cover the following:
- Project overview (1-2 sentences)
- Prerequisites (language version, tools needed)
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
            model="claude-sonnet-4-6"
        ),
    ):
        if hasattr(message, "result"):
            result = message.result
    print("CONTRIBUTING.md generated.")
    return result
```

**`src/gen_architecture.py`** — generates ARCHITECTURE.md from codebase summary
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def gen_architecture(codebase_summary):
    print("Generating ARCHITECTURE.md...")
    prompt = f"""
You are a software architect writing technical documentation for a project.
Using the codebase summary below, write a complete ARCHITECTURE.md file.

Cover the following:
- High-level system overview
- How the two pipelines work (PR review and onboarding)
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
```

**`src/gen_setup_guide.py`** — generates SETUP.md from codebase summary
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def gen_setup_guide(codebase_summary):
    print("Generating SETUP.md...")
    prompt = f"""
You are a senior software engineer writing a setup guide for a new developer joining the project.
Using the codebase summary below, write a complete SETUP.md file.

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
            allowed_tools=["Read"],
            model="claude-sonnet-4-6"
        ),
    ):
        if hasattr(message, "result"):
            result = message.result
    print("SETUP.md generated.")
    return result
```

**`github_client.py` — new `commit_file()` helper**
```python
def commit_file(path, content, message):
    repo = get_repo()
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, message, content, existing.sha)
        print(f"Updated {path} in repo.")
    except Exception:
        repo.create_file(path, message, content)
        print(f"Created {path} in repo.")
```

**`src/main.py`** — updated with onboarding extraction and issue_comment routing
```python
import asyncio
import os
from dotenv import load_dotenv
from gather_context import gather_pr_context
from security_scan import run_security_scan
from quality_review import run_quality_review
from summarize_pr import run_summary
from post_results import post_review
from detect_new_repo import is_new_repo
from explore_codebase import explore_codebase
from gen_contributing import gen_contributing
from gen_architecture import gen_architecture
from gen_setup_guide import gen_setup_guide
from github_client import commit_file, post_pr_comment

load_dotenv()

async def run_onboarding():
    print("Starting onboarding pipeline...")
    codebase_summary = await explore_codebase()
    contributing = await gen_contributing(codebase_summary)
    commit_file("CONTRIBUTING.md", contributing, "docs: add CONTRIBUTING.md via CodeGuard onboarding")
    architecture = await gen_architecture(codebase_summary)
    commit_file("ARCHITECTURE.md", architecture, "docs: add ARCHITECTURE.md via CodeGuard onboarding")
    setup = await gen_setup_guide(codebase_summary)
    commit_file("SETUP.md", setup, "docs: add SETUP.md via CodeGuard onboarding")
    print("Onboarding pipeline complete.")

async def main():
    event_name = os.getenv("EVENT_NAME", "pull_request")
    comment_body = os.getenv("COMMENT_BODY", "").strip()

    if event_name == "issue_comment":
        if comment_body == "/onboard":
            print("/onboard command detected. Running onboarding pipeline...")
            await run_onboarding()
        else:
            print("Comment is not an onboard command. Skipping.")

    elif event_name == "push":
        if is_new_repo():
            await run_onboarding()
        else:
            print("Repo already onboarded. Nothing to do.")

    else:
        pr_number = os.getenv("PR_NUMBER", "1")
        context = gather_pr_context(pr_number)
        security_results = await run_security_scan(context)
        quality_results = await run_quality_review(context)
        summary_results = await run_summary(context)
        post_review(pr_number, summary_results, security_results, quality_results)

asyncio.run(main())
```

**`.github/workflows/codeguard.yml`** — updated with issue_comment trigger and COMMENT_BODY
```yaml
name: CodeGuard

on:
  pull_request:
    types: [opened, synchronize, reopened]
  push:
    branches:
      - main
  issue_comment:
    types: [created]

permissions:
  pull-requests: write
  contents: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run CodeGuard
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          REPO_NAME: ${{ github.repository }}
          EVENT_NAME: ${{ github.event_name }}
          COMMENT_BODY: ${{ github.event.comment.body }}
        run: python src/main.py
```

### Summary
Built the full onboarding pipeline across six new or updated files. `detect_new_repo.py` gates the pipeline by checking for `CONTRIBUTING.md`. `explore_codebase.py` uses Read, Glob, and Bash tools to map the full repo and produce a structured codebase summary. That summary is passed to three doc generators — `gen_contributing.py`, `gen_architecture.py`, and `gen_setup_guide.py` — each producing clean raw markdown committed directly to the repo via a new `commit_file()` helper in `github_client.py`. Added `/onboard` manual re-trigger support via `issue_comment` workflow trigger. Extracted `run_onboarding()` into a shared function used by both the push trigger and the comment trigger. Confirmed all three docs generated cleanly with no code fences or fluff.

---

## Blockers

- **Agent wrapping output in code fences and adding explanation text** — the prompt was not explicit enough about output format
  - Fix: added Output rules section to all three doc generator prompts explicitly forbidding code fences, preamble, and commentary
- **Generated docs slow to produce** — agents run sequentially, each waiting for the previous to finish
  - Note: will fix in Phase 4 using asyncio.gather() to run all three in parallel

---

## To Do Next

- Phase 4.1: Add `.codeguard.yml` config file support
- Phase 4.2: Add error handling and graceful degradation
- Phase 4.3: Add session logging — save agent transcripts as GitHub Actions artifacts
- Phase 4.4: Run CodeGuard on itself — open a PR with an intentional bug
- Phase 4.5: Write the README with architecture diagram and demo screenshot
- Optimization: Use asyncio.gather() to run doc generators in parallel
