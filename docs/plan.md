# CodeGuard — Full Project Plan

A GitHub-integrated AI agent built on the Claude Agent SDK that automatically reviews PRs for security vulnerabilities and code quality, and generates onboarding documentation for new repositories.

---

## Project overview

**What it does:**
- Runs on every PR/push to scan for security issues, review code quality, and summarize changes
- Runs once on new repositories to generate architecture docs, a CONTRIBUTING.md, and a setup guide

**Tech stack:**
- Claude Agent SDK (Python)
- GitHub Actions (trigger + runner)
- GitHub REST API (posting comments, committing docs)
- PyGithub (GitHub API wrapper)

---

## Phase 1 — Foundation (Week 1)

Goal: Get the bare scaffolding working end-to-end before adding any AI logic.

### 1.1 Set up the project repo

- Create a new GitHub repository called `codeguard`
- Initialize a Python project with a `src/` folder and `requirements.txt`
- Add a `.gitignore` for Python, virtual envs, and secrets
- Write a basic `README.md` placeholder

### 1.2 Install and verify the Claude Agent SDK

- Install dependencies:
  ```
  pip install claude-agent-sdk pygithub
  ```
- Write a `hello_agent.py` script that runs a minimal query:
  ```python
  import asyncio
  from claude_agent_sdk import query, ClaudeAgentOptions

  async def main():
      async for message in query(
          prompt="List the files in the current directory.",
          options=ClaudeAgentOptions(allowed_tools=["Bash", "Glob"]),
      ):
          if hasattr(message, "result"):
              print(message.result)

  asyncio.run(main())
  ```
- Confirm the agent runs locally and can use Bash and file tools

### 1.3 Set up GitHub Actions

- Create `.github/workflows/codeguard.yml`
- Trigger on `pull_request` events (opened, synchronize, reopened)
- Pass `GITHUB_TOKEN` and `ANTHROPIC_API_KEY` as secrets
- Have the workflow run `python src/main.py` as a smoke test
- Confirm the workflow fires on a test PR

### 1.4 GitHub API plumbing

- Write a `github_client.py` module using PyGithub
- Implement helper functions:
  - `get_pr_diff(pr_number)` — fetch the raw diff
  - `get_changed_files(pr_number)` — list of changed file paths
  - `post_pr_comment(pr_number, body)` — post a markdown comment
- Test each function manually with a real PR

---

## Phase 2 — PR Review Agent (Weeks 2–3)

Goal: Build the three-part review loop and post structured results as a GitHub comment.

### 2.1 Data gathering step

- Write `gather_context.py`
- Fetch PR title, description, base branch, diff, and changed file paths
- Pass this context as the initial prompt to the agent
- Verify the agent can read the relevant files using its `Read` tool

### 2.2 Security scan

- Write `security_scan.py`
- Prompt the agent to look for:
  - Hardcoded secrets, API keys, or credentials
  - SQL injection and command injection patterns
  - Unsafe use of `eval`, `exec`, or `subprocess`
  - Missing input validation on user-facing functions
  - Insecure dependency additions in `requirements.txt` / `package.json`
- Output: a structured list of findings with file name, line reference, severity, and description

### 2.3 Code quality review

- Write `quality_review.py`
- Prompt the agent to assess:
  - Functions that are too long or too complex
  - Inconsistent naming conventions vs. the existing codebase
  - Missing or weak test coverage for changed code
  - Duplicated logic that could be extracted
  - Whether the change follows existing architectural patterns
- Output: a list of suggestions with file references and a brief rationale

### 2.4 PR summary generation

- Write `summarize_pr.py`
- Prompt the agent to write a plain-English summary covering:
  - What the PR does (intent, not just mechanics)
  - Which parts of the codebase are affected
  - Any notable risks or trade-offs introduced
- Output: 2–4 sentence paragraph, readable by a non-author reviewer

### 2.5 Compose and post the GitHub comment

- Write `post_results.py`
- Combine outputs from steps 2.2–2.4 into a single markdown comment:
  ```markdown
  ## CodeGuard review

  ### Summary
  <agent summary here>

  ### Security findings
  <findings list or "No issues found">

  ### Code quality notes
  <suggestions list or "No issues found">

  ---
  *Reviewed by CodeGuard using Claude Agent SDK*
  ```
- Post via `post_pr_comment()` from Phase 1
- Test end-to-end on a real PR with intentional issues planted

---

## Phase 3 — Onboarding Agent (Week 4)

Goal: Detect new repositories and auto-generate documentation on first push.

### 3.1 New repo detection

- Add a second workflow trigger in `codeguard.yml` for `push` to the default branch
- Write detection logic in `detect_new_repo.py`:
  - Check if `CONTRIBUTING.md` already exists in the repo root
  - If it does not exist, trigger the onboarding agent
  - If it does exist, skip onboarding silently

### 3.2 Codebase exploration

- Write `explore_codebase.py`
- Give the agent access to `Glob`, `Read`, and `Bash` tools
- Prompt the agent to:
  - Map the top-level directory structure
  - Identify the language(s) and framework(s) in use
  - Find the main entry point(s)
  - Identify key modules and their responsibilities
  - Note any existing configuration files (`.env.example`, `Makefile`, `docker-compose.yml`, etc.)
- Output: a structured summary to be passed to the next steps

### 3.3 Generate CONTRIBUTING.md

- Write `gen_contributing.py`
- Prompt the agent using the exploration output to write a `CONTRIBUTING.md` covering:
  - How to clone and set up the project locally
  - How to run tests
  - Branch naming and PR conventions
  - Code style notes (inferred from existing code)
- Commit the file to the repo root via the GitHub API

### 3.4 Generate ARCHITECTURE.md

- Write `gen_architecture.py`
- Prompt the agent to write an `ARCHITECTURE.md` covering:
  - High-level system overview
  - Module breakdown and responsibilities
  - Key data flows
  - External dependencies and why they were chosen (where inferable)
- Commit the file to the repo root via the GitHub API

### 3.5 Generate setup guide

- Write `gen_setup_guide.py`
- Prompt the agent to write a `SETUP.md` covering:
  - Prerequisites (language version, tools needed)
  - Step-by-step local setup instructions
  - Environment variable reference
  - How to run the project and its tests
- Commit the file to the repo root via the GitHub API

### 3.6 Manual re-trigger

- Add support for a `/onboard` comment on any PR to re-run the onboarding agent
- Implement via a `issue_comment` workflow trigger that checks the comment body

---

## Phase 4 — Polish (Week 5)

Goal: Turn a working prototype into a portfolio-ready project.

### 4.1 Config file support

- Add support for a `.codeguard.yml` file in the target repo:
  ```yaml
  security:
    enabled: true
    severity_threshold: medium  # low | medium | high

  quality:
    enabled: true
    max_function_lines: 50

  onboarding:
    enabled: true
    docs_branch: main
  ```
- Parse this config at the start of each run and pass relevant options to the agent

### 4.2 Error handling and graceful degradation

- Wrap all agent calls in try/except
- If the agent fails or times out, post a minimal comment explaining what happened rather than silently failing
- Add retry logic (max 2 retries) for transient GitHub API errors

### 4.3 Session logging

- Save each agent run's full message transcript to a JSON log file
- Store logs as GitHub Actions artifacts (available for 7 days)
- This lets you inspect exactly what the agent did on any given run

### 4.4 Apply CodeGuard to itself

- Add the CodeGuard workflow to the CodeGuard repo itself
- Open a PR with an intentional bug and a missing test
- Screenshot the resulting comment — this is your primary demo asset

### 4.5 Write the README

The README is a core part of the portfolio piece. Include:
- What CodeGuard does and why you built it
- A screenshot of a real PR comment it generated
- Architecture diagram (link to this plan or embed the diagram)
- How to install it in any repo (step-by-step)
- What you learned — specifically the agent engineering decisions you made (tool scoping, prompt structure, handling failures)

### 4.6 Parallel doc generation with asyncio.gather()

- Replace the sequential doc generator calls in `run_onboarding()` with parallel execution:
  ```python
  contributing, architecture, setup = await asyncio.gather(
      gen_contributing(codebase_summary),
      gen_architecture(codebase_summary),
      gen_setup_guide(codebase_summary)
  )
  ```
- All three doc generators take the same input and don't depend on each other, so they can run simultaneously
- Expected result: roughly 3x faster onboarding pipeline

### 4.7 Model pinning by task

- Use cheaper, faster models for simpler tasks and reserve Sonnet for complex analysis:
  ```python
  # Haiku for summary — simple plain-English writing task
  ClaudeAgentOptions(model="claude-haiku-4-5", ...)

  # Sonnet for security and quality — requires deep reasoning
  ClaudeAgentOptions(model="claude-sonnet-4-6", ...)
  ```
- Expected result: lower cost per PR review with no meaningful quality drop on the summary

### 4.8 Codebase exploration caching

- Store a hash of the repo's file structure after each successful onboarding run
- On subsequent push events, compare the current structure hash to the stored one
- Only re-run `explore_codebase.py` if the structure has changed significantly
- Expected result: avoid paying for a full exploration on every push to main

---

## File structure (target end state)

```
codeguard/
├── .github/
│   └── workflows/
│       └── codeguard.yml
├── src/
│   ├── main.py               # Entry point, reads event type and routes
│   ├── github_client.py      # GitHub API helpers
│   ├── gather_context.py     # Fetch PR diff and file contents
│   ├── security_scan.py      # Security analysis agent
│   ├── quality_review.py     # Code quality agent
│   ├── summarize_pr.py       # PR summary agent
│   ├── post_results.py       # Compose and post GitHub comment
│   ├── detect_new_repo.py    # New repo detection logic
│   ├── explore_codebase.py   # Codebase mapping agent
│   ├── gen_contributing.py   # CONTRIBUTING.md generator
│   ├── gen_architecture.py   # ARCHITECTURE.md generator
│   └── gen_setup_guide.py    # SETUP.md generator
├── .codeguard.yml            # Default config (used by CodeGuard on itself)
├── requirements.txt
└── README.md
```

---

## Key agent engineering decisions to document

These are the things interviewers will ask about — have answers ready.

- **Why separate agents per task?** Each concern (security, quality, summary) has a different prompt, different tools, and different output format. Separating them keeps prompts focused and makes failures easier to debug.
- **Tool scoping** — the PR review agents only need `Read` and `Bash` (read-only). The onboarding agent needs those plus write access to commit files. Restricting tools to the minimum needed is a real safety practice.
- **Why not one giant prompt?** A single prompt doing security + quality + summary produces unfocused output. Three focused agents each do one job well.
- **How you handle failures** — if the agent errors, you post a comment saying so rather than silently failing. Visible failures are better than invisible ones in CI systems.
- **Session logging** — being able to inspect what the agent actually did is critical for debugging and for demonstrating the system to others.
- **Parallel execution** — doc generators run concurrently with asyncio.gather() since they share the same input and have no dependencies on each other.
- **Model selection by task** — using Haiku for simple writing tasks and Sonnet for deep code analysis balances cost and quality.
- **Caching exploration results** — avoiding redundant API calls by hashing the repo structure and only re-exploring when something meaningful changes.

---

*Built with Claude Agent SDK · Python · GitHub Actions*
