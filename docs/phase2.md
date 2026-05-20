# Title: Phase 2 — PR Review Agent

## Goal
Build the core review pipeline: three focused agents that analyze a PR for security vulnerabilities, code quality issues, and generate a plain-English summary, then post all findings as a structured comment to the PR on GitHub.

---

## Work Done

### Project structure
```
src/
├── main.py              # updated — orchestrates the full pipeline
├── github_client.py     # unchanged
├── gather_context.py    # new — fetches PR diff and changed files
├── security_scan.py     # new — security analysis agent
├── quality_review.py    # new — code quality review agent
├── summarize_pr.py      # new — plain-English summary agent
└── post_results.py      # new — builds and posts the GitHub comment
```

### Key files

**`src/gather_context.py`** — fetches PR diff and changed files, packages into a single context string passed to all three agents
```python
import os
from github_client import get_pr_diff, get_changed_files

def gather_pr_context(pr_number):
    print(f"Gathering context for PR #{pr_number}...")
    diff = get_pr_diff(pr_number)
    changed_files = get_changed_files(pr_number)
    context = f"""
PR Number: {pr_number}
Repository: {os.getenv('REPO_NAME')}

Changed files:
{chr(10).join(f'- {f}' for f in changed_files)}

Diff:
{diff}
"""
    print(f"Context gathered. {len(changed_files)} file(s) changed.")
    return context
```

**`src/security_scan.py`** — agent scans for secrets, injections, OWASP issues
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_security_scan(context):
    print("Running security scan...")
    prompt = f"""
You are a security-focused code reviewer. Analyze the following pull request and identify security vulnerabilities.

Look specifically for:
- Hardcoded secrets, API keys, tokens, or passwords
- SQL injection vulnerabilities
- Command injection vulnerabilities
- Unsafe use of eval(), exec(), or subprocess with user input
- Missing input validation on user-facing functions
- Insecure dependencies added in requirements.txt or package.json
- Sensitive data being logged or exposed

Here is the pull request:

{context}

Respond in this exact format:
FINDINGS:
- [SEVERITY: HIGH/MEDIUM/LOW] filename:line_number - description of issue

If no issues are found, respond with:
FINDINGS:
- No security issues found
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
    print("Security scan complete.")
    return result
```

**`src/quality_review.py`** — agent reviews complexity, naming, error handling, test coverage
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_quality_review(context):
    print("Running quality review...")
    prompt = f"""
You are an experienced software engineer doing a code review. Analyze the following pull request and identify code quality issues.

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
```

**`src/summarize_pr.py`** — agent writes a plain-English summary of the PR
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_summary(context):
    print("Running PR summary...")
    prompt = f"""
You are a helpful code reviewer. Analyze the following pull request and write a concise plain-English summary of it.

Your summary should cover:
- What this PR does (the intent, not just the mechanics)
- Which parts of the codebase are affected
- Any notable risks or trade-offs introduced

Here is the pull request:

{context}

Respond in this exact format:
SUMMARY:
<2-4 sentences here>
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
    print("Summary complete.")
    return result
```

**`src/post_results.py`** — combines all three outputs into a structured markdown comment and posts it to GitHub
```python
from github_client import post_pr_comment

def build_comment(summary, security, quality):
    return f"""## CodeGuard Review 🛡️

### Summary
{summary.replace("SUMMARY:", "").strip()}

### Security Findings
{security.replace("FINDINGS:", "").strip()}

### Quality Notes
{quality.replace("QUALITY NOTES:", "").strip()}

---
*Reviewed by CodeGuard using Claude Agent SDK · Model: claude-sonnet-4-6*"""

def post_review(pr_number, summary, security, quality):
    print("Posting review to GitHub...")
    comment = build_comment(summary, security, quality)
    post_pr_comment(pr_number, comment)
    print("Review posted successfully.")
```

**`src/main.py`** — orchestrates the full pipeline
```python
import asyncio
import os
from dotenv import load_dotenv
from gather_context import gather_pr_context
from security_scan import run_security_scan
from quality_review import run_quality_review
from summarize_pr import run_summary
from post_results import post_review

load_dotenv()

async def main():
    pr_number = os.getenv("PR_NUMBER", "1")
    context = gather_pr_context(pr_number)
    security_results = await run_security_scan(context)
    quality_results = await run_quality_review(context)
    summary_results = await run_summary(context)
    post_review(pr_number, summary_results, security_results, quality_results)

asyncio.run(main())
```

### Summary
Built the full PR review pipeline across five new modules. `gather_context.py` fetches the PR diff and changed files from GitHub and packages them into a single context string. That context is passed to three separate agents — `security_scan.py`, `quality_review.py`, and `summarize_pr.py` — each with a focused prompt and role. `post_results.py` combines all three outputs into a structured markdown comment and posts it to the PR via the GitHub API. Confirmed the full pipeline working end-to-end both locally and via GitHub Actions, with CodeGuard successfully reviewing its own Phase 2 PR.

---

## Blockers

- **`PermissionError` string accidentally embedded in `quality_review.py` prompt** — corrupted every prompt sent to the quality agent
  - Fix: removed the stray string from the prompt
- **Typo `"PR Numer"` in `gather_context.py`** — injected into every agent prompt
  - Fix: corrected to `"PR Number"`
- **Print statements in `main.py` printing headers but not results** — made local debugging impossible
  - Fix: removed stale print statements since results are now posted to GitHub

---

## To Do Next

- Phase 3.1: Add new repo detection logic in `detect_new_repo.py`
- Phase 3.2: Write `explore_codebase.py` — agent maps structure, stack, and entry points
- Phase 3.3: Write `gen_contributing.py` — generates CONTRIBUTING.md
- Phase 3.4: Write `gen_architecture.py` — generates ARCHITECTURE.md
- Phase 3.5: Write `gen_setup_guide.py` — generates SETUP.md
- Phase 3.6: Add `/onboard` manual re-trigger via issue comment
 