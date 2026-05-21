# ARCHITECTURE.md

# CodeGuard Architecture

## High-Level System Overview

CodeGuard is a GitHub-integrated AI agent built on the Anthropic Claude Agent SDK. It runs entirely inside GitHub Actions and provides two automated pipelines: a pull request review pipeline that scans incoming code changes for security vulnerabilities and code quality issues, and an onboarding pipeline that generates structured documentation for new repositories.

All agent reasoning is delegated to Claude models through the SDK. CodeGuard itself acts as a thin orchestration layer that routes events, assembles context, invokes agents, and delivers results back to GitHub. There is no persistent server, no database, and no long-running process. Each GitHub Actions job starts fresh, completes its work, and exits.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline activates when a pull request is opened, synchronized, or reopened. It executes the following stages in sequence:

1. **Context assembly** — the diff and changed file list for the PR are fetched from the GitHub API and formatted into a single context string.
2. **Security scan** — a Claude agent reads the context and identifies security vulnerabilities, returning a structured FINDINGS block.
3. **Quality review** — a second Claude agent reads the context and identifies code quality issues, returning a structured QUALITY NOTES block.
4. **Summary** — a third Claude agent reads the context and produces a plain-English explanation of what the PR does, which parts of the codebase it affects, and any notable risks.
5. **Post results** — the three output blocks are assembled into a single markdown comment and posted directly onto the PR.

### Onboarding Pipeline

The onboarding pipeline activates on two triggers: a push to the main branch (when no CONTRIBUTING.md is detected in the repository), and a manual `/onboard` command posted as an issue comment.

It executes the following stages in sequence:

1. **New repo detection** — the system checks whether CONTRIBUTING.md already exists. If it does, the pipeline exits early.
2. **Codebase exploration** — a Claude agent with Read, Glob, and Bash tools maps the repository structure and produces a structured codebase summary.
3. **Documentation generation** — three Claude agents run in sequence, each consuming the codebase summary and writing one documentation file: CONTRIBUTING.md, ARCHITECTURE.md, and SETUP.md.
4. **Commit files** — each generated file is committed to the repository root via the GitHub Contents API.

---

## Module Breakdown

### src/main.py

The sole entry point and routing layer. It reads the `EVENT_NAME` environment variable and dispatches execution to the appropriate pipeline. For `pull_request` events it runs the five-stage review pipeline. For `push` events it checks for new repo conditions and runs the onboarding pipeline if needed. For `issue_comment` events it checks whether the comment body contains `/onboard` and triggers the onboarding pipeline manually. No business logic lives here; all work is delegated to the modules below.

### src/github_client.py

The GitHub API utility layer. It wraps PyGithub and exposes four functions used throughout the system:

- `get_pr_diff()` fetches the raw unified diff for a pull request.
- `get_changed_files()` returns a list of file paths modified by the PR.
- `post_pr_comment()` writes a markdown string as a comment on a PR.
- `commit_file()` creates or updates a file in the repository using the GitHub Contents API.

All functions read `GITHUB_TOKEN` and `REPO_NAME` from the environment.

### src/gather_context.py

Assembles the context string that is passed as input to all three PR review agents. It calls `get_pr_diff()` and `get_changed_files()` and formats them alongside the repository name and PR number into a single prompt-ready string.

### src/security_scan.py

Runs a Claude agent with the Read tool and a security-focused system prompt. The agent looks for hardcoded secrets, injection vulnerabilities, unsafe use of `eval` or `exec`, missing input validation, insecure dependencies, and sensitive data exposure. It returns a structured FINDINGS block as a string.

### src/quality_review.py

Runs a Claude agent with the Read tool and a code quality system prompt. The agent checks for overly complex functions, naming inconsistencies, weak error handling, duplicated logic, missing tests, and hardcoded values. It returns a structured QUALITY NOTES block as a string.

### src/summarize_pr.py

Runs a Claude agent with the Read tool to produce a concise plain-English summary of the PR. The summary describes what the PR does, which parts of the codebase it touches, and any notable risks or trade-offs. It returns a structured SUMMARY block as a string.

### src/post_results.py

Assembles the outputs from the three review agents into a single branded markdown comment and posts it to the PR via `post_pr_comment()`. The comment is structured with labeled sections for summary, security findings, and quality notes.

### src/detect_new_repo.py

Determines whether onboarding should run. It attempts to fetch CONTRIBUTING.md from the repository root via the GitHub API. If the file is absent it returns `True`. If the file already exists it returns `False`, preventing duplicate onboarding runs.

### src/explore_codebase.py

Runs a Claude agent equipped with Read, Glob, and Bash tools to map the repository structure. The agent explores directories, reads source files, and produces a structured codebase summary. This summary is the shared input passed to all three documentation generator modules.

### src/gen_contributing.py

Runs a Claude agent that writes a complete CONTRIBUTING.md file from the codebase summary. The output covers project overview, prerequisites, local setup, environment variables, branching conventions, and PR submission instructions.

### src/gen_architecture.py

Runs a Claude agent that writes a complete ARCHITECTURE.md file from the codebase summary. The output covers system overview, pipeline descriptions, module breakdown, data flow, and external dependencies.

### src/gen_setup_guide.py

Runs a Claude agent that writes a complete SETUP.md file from the codebase summary. The output covers prerequisites, step-by-step local setup, `.env` population, instructions for running both pipelines, and common setup mistakes.

---

## Data Flow

### PR Review Data Flow

```
GitHub webhook (pull_request event)
        │
        ▼
GitHub Actions triggers codeguard.yml
        │
        ▼
src/main.py reads EVENT_NAME → dispatches to PR review pipeline
        │
        ▼
src/gather_context.py
  → github_client.get_pr_diff()       ← GitHub API
  → github_client.get_changed_files() ← GitHub API
  → returns context string
        │
        ├──────────────────────────────────────────────────┐
        │                                                  │
        ▼                                                  ▼
src/security_scan.py              src/quality_review.py
  → Claude agent (Read tool)        → Claude agent (Read tool)
  → returns FINDINGS block          → returns QUALITY NOTES block
        │                                                  │
        └──────────────────┬───────────────────────────────┘
                           │
                           ▼
                  src/summarize_pr.py
                    → Claude agent (Read tool)
                    → returns SUMMARY block
                           │
                           ▼
                  src/post_results.py
                    → assembles markdown comment
                    → github_client.post_pr_comment() ← GitHub API
                           │
                           ▼
                  Comment posted on PR
```

### Onboarding Data Flow

```
GitHub webhook (push to main or issue_comment /onboard)
        │
        ▼
GitHub Actions triggers codeguard.yml
        │
        ▼
src/main.py reads EVENT_NAME → dispatches to onboarding pipeline
        │
        ▼
src/detect_new_repo.py
  → github_client fetches CONTRIBUTING.md ← GitHub API
  → returns True (absent) or False (exists)
        │
        ▼ (only if True)
src/explore_codebase.py
  → Claude agent (Read + Glob + Bash tools)
  → returns codebase summary string
        │
        ├─────────────────────────────────────────────────┐
        │                         │                       │
        ▼                         ▼                       ▼
src/gen_contributing.py  src/gen_architecture.py  src/gen_setup_guide.py
  → Claude agent           → Claude agent           → Claude agent
  → CONTRIBUTING.md        → ARCHITECTURE.md        → SETUP.md
        │                         │                       │
        └─────────────────────────┴───────────────────────┘
                                  │
                                  ▼
                        github_client.commit_file() × 3 ← GitHub API
                                  │
                                  ▼
                        Files committed to repository root
```

---

## External Dependencies

### claude-agent-sdk

The Anthropic Claude Agent SDK for Python. It provides the `query()` coroutine and `ClaudeAgentOptions` class used to run every AI agent in the system. Each agent call specifies a model, a set of permitted tools (Read, Glob, Bash), and a prompt. The SDK handles all communication with the Anthropic API, manages tool execution loops, and returns the final text response. This is the core intelligence layer of CodeGuard; without it the system has no ability to reason about code.

### pygithub

A Python wrapper around the GitHub REST API. It is used for every GitHub interaction in the system: fetching PR diffs, listing changed files, posting PR comments, and creating or updating files in the repository. PyGithub abstracts away raw HTTP and pagination concerns, providing a clean object model for repositories, pull requests, and file contents.

### python-dotenv

A utility for loading environment variables from a `.env` file into the process environment. It is used only during local development to populate `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `REPO_NAME`, and `PR_NUMBER` without manually exporting variables. In production (GitHub Actions) these variables are injected directly by the workflow and python-dotenv has no effect.

---

## GitHub Actions Integration

The file `.github/workflows/codeguard.yml` is the single workflow definition for the project. It contains all trigger definitions and job steps.

### Triggers

The workflow listens for three event types:

- `pull_request` with activity types `opened`, `synchronize`, and `reopened` — activates the PR review pipeline.
- `push` to the `main` branch — activates the onboarding pipeline when CONTRIBUTING.md is absent.
- `issue_comment` with activity type `created` — activates the onboarding pipeline when the comment body contains `/onboard`.

### Job Steps

Each triggered job runs on an Ubuntu runner and executes the following steps in order:

1. Check out the repository using `actions/checkout`.
2. Set up Python 3.11 using `actions/setup-python`.
3. Install dependencies via `pip install -r requirements.txt`.
4. Run `python src/main.py`.

### Environment Variables

The workflow injects the following variables into the job environment from GitHub secrets and context expressions:

| Variable | Source | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | GitHub secret | Authenticates Claude API calls |
| `GITHUB_TOKEN` | GitHub secret | Authenticates GitHub API calls |
| `REPO_NAME` | GitHub context (`github.repository`) | Identifies the target repository |
| `PR_NUMBER` | GitHub context (`github.event.pull_request.number`) | Identifies the target PR |
| `EVENT_NAME` | GitHub context (`github.event_name`) | Controls pipeline routing in main.py |

The `EVENT_NAME` variable is the primary dispatch signal. `src/main.py` reads it first and uses it to decide which pipeline to execute, making the workflow stateless and self-contained across all three trigger types.