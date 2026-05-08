# Title: Phase 1 — Foundation

## Goal
Get the bare scaffolding working end-to-end: project structure, Claude Agent SDK running locally, GitHub Actions workflow triggering on PRs, and GitHub API helpers confirmed working.

---

## Work Done

### Project structure
```
codeguard/
├── .github/
│   └── workflows/
│       └── codeguard.yml
├── docs/
│   └── phase-1.md
├── src/
│   ├── main.py
│   └── github_client.py
├── venv/
├── .env
├── .gitignore
└── requirements.txt
```

### Key files

**`requirements.txt`**
```
claude-agent-sdk
pygithub
python-dotenv
```

**`src/main.py`** — SDK smoke test, verifies the agent can run and use tools
```python
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
        ),
    ):
        if hasattr(message, "result"):
            print("Agent output:", message.result)

asyncio.run(main())

pr_number = os.getenv("PR_NUMBER", "1")

print("Changed files:", get_changed_files(pr_number))
post_pr_comment(pr_number, "CodeGuard is alive — Phase 1 complete!")
```

**`src/github_client.py`** — GitHub API helpers using PyGithub
```python
import os
from github import Github

def get_github_client():
    token = os.getenv("GITHUB_TOKEN")
    return Github(token)

def get_repo():
    client = get_github_client()
    repo_name = os.getenv("REPO_NAME")
    return client.get_repo(repo_name)

def get_pr_diff(pr_number):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))
    diff = ""
    for file in pr.get_files():
        diff += f"File: {file.filename}\n"
        diff += f"{file.patch or 'Binary file, no diff available'}\n\n"
    return diff

def get_changed_files(pr_number):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))
    return [file.filename for file in pr.get_files()]

def post_pr_comment(pr_number, body):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))
    pr.create_issue_comment(body)
```

**`.github/workflows/codeguard.yml`** — triggers on every PR, runs the agent in CI
```yaml
name: CodeGuard

on:
  pull_request:
    types: [opened, synchronize, reopened]

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
        run: python src/main.py
```

### Summary
Set up the full project scaffold on Windows. Installed the Claude Agent SDK, PyGithub, and python-dotenv inside a virtual environment. Verified the agent runs locally and can use Bash and Glob tools. Created the GitHub Actions workflow that triggers on pull request events. Confirmed the workflow fires and passes on a real test PR. Built and tested all three GitHub API helpers — `get_pr_diff()`, `get_changed_files()`, and `post_pr_comment()` — with a live comment successfully posted to a real PR. Selected `claude-sonnet-4-6` as the model for all CodeGuard agents.

---

## Blockers

- **venv activation failing on Windows PowerShell** — PowerShell blocked script execution by default
  - Fix: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`, then use `.\venv\Scripts\Activate.ps1`
- **ModuleNotFoundError for dotenv** — pip was installing into system Python instead of the venv
  - Fix: Always activate venv first, then run pip install
- **AssertionError: None on REPO_NAME** — `REPO_NAME` was missing from `.env`
  - Fix: Add `REPO_NAME=username/repo-name` to `.env`

---

## To Do Next

- Phase 2.1: Write `gather_context.py` — fetch PR diff and pass it to the agent as context
- Phase 2.2: Write `security_scan.py` — agent scans for secrets, injections, OWASP issues
- Phase 2.3: Write `quality_review.py` — agent reviews complexity, style, test coverage
- Phase 2.4: Write `summarize_pr.py` — agent writes plain-English PR summary
- Phase 2.5: Write `post_results.py` — combine all outputs into a structured GitHub comment
