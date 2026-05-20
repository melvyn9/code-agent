# CodeGuard Architecture

## High-Level System Overview

CodeGuard is a GitHub integrated AI agent system built on the Anthropic Claude Agent SDK. It operates as a fully automated service that monitors repository events through GitHub Actions and responds by running one of two distinct pipelines: a pull request review pipeline that inspects incoming code changes for security vulnerabilities and quality issues, or an onboarding pipeline that generates foundational documentation for repositories that lack it.

The system has no persistent server or database. Every execution is stateless and ephemeral, triggered by a GitHub event, run inside a GitHub Actions runner, and concluded by writing output back to GitHub either as a pull request comment or as committed files. The sole entry point is `src/main.py`, which reads the triggering event type from the environment and delegates to the appropriate pipeline.

All AI capabilities are provided by Claude via the Claude Agent SDK. Each agent module is independently scoped with only the tools it needs to perform its task, a design that limits blast radius, enforces the principle of least privilege, and keeps agent prompts focused.

---

## Pipeline 1: Pull Request Review

The PR review pipeline activates when a pull request is opened, updated, or reopened against the repository.

**Trigger:** A `pull_request` event (opened, synchronize, or reopened) causes GitHub Actions to invoke `src/main.py` with `EVENT_NAME=pull_request` and a valid `PR_NUMBER`.

**Step 1 — Context Assembly:** `src/gather_context.py` calls `src/github_client.py` to fetch the PR number, repository name, list of changed files, and the raw unified diff. These are assembled into a single formatted string that will be injected into every downstream agent prompt.

**Step 2 — Parallel Agent Execution:** `src/main.py` invokes three agent modules concurrently using `asyncio.gather`:

* `src/security_scan.py` sends the context string to a Claude agent scoped to the Read tool. The agent inspects the diff for hardcoded secrets, injection vulnerabilities, unsafe subprocess usage, missing input validation, and insecure dependency additions. It returns structured FINDINGS output.
* `src/quality_review.py` sends the same context to a separate Claude agent. This agent evaluates code quality across dimensions including function complexity, naming consistency, error handling coverage, logic duplication, test coverage gaps, and hardcoded values. It returns structured QUALITY NOTES output.
* `src/summarize_pr.py` sends the context to a third Claude agent that produces a concise plain-English paragraph describing the intent of the pull request, which parts of the codebase are affected, and any notable risks.

**Step 3 — Result Composition and Posting:** `src/post_results.py` receives the three outputs and composes them into a single formatted markdown comment. It calls `src/github_client.py` to post the comment to the originating pull request.

---

## Pipeline 2: Onboarding

The onboarding pipeline activates when a push to the main branch is detected or when a maintainer manually triggers it via a slash command in an issue comment.

**Triggers:**

* A `push` event to the main branch causes GitHub Actions to invoke `src/main.py` with `EVENT_NAME=push`.
* An `issue_comment` event containing the `/onboard` command causes GitHub Actions to invoke `src/main.py` with `EVENT_NAME=issue_comment`.

**Step 1 — Onboarding Gate:** `src/detect_new_repo.py` calls `src/github_client.py` to check whether `CONTRIBUTING.md` already exists in the repository root. If it does, the pipeline exits immediately. If it does not, execution continues.

**Step 2 — Codebase Exploration:** `src/explore_codebase.py` runs a Claude agent with access to the Read, Glob, and Bash tools. This agent maps the repository structure, identifies programming languages and frameworks, locates entry points, and produces a structured codebase summary. This summary is used as the shared input for all three documentation generators.

**Step 3 — Parallel Documentation Generation:** `src/main.py` calls all three generators concurrently using `asyncio.gather`:

* `src/gen_contributing.py` runs a Claude agent that produces a complete `CONTRIBUTING.md` document covering setup instructions, environment variables, branching conventions, and CodeGuard integration notes.
* `src/gen_architecture.py` runs a Claude agent that produces an `ARCHITECTURE.md` document covering the system overview, both pipelines, module responsibilities, data flow, and external dependencies.
* `src/gen_setup_guide.py` runs a Claude agent that produces a `SETUP.md` document covering prerequisites, local setup steps, the environment variable reference, and instructions for running both pipelines manually.

**Step 4 — File Commit:** Each generator passes its output to `src/github_client.py`, which commits or updates the corresponding file directly to the repository root.

---

## Module Breakdown

### src/main.py

The sole entry point and top-level orchestrator. Reads `EVENT_NAME` from the environment and branches execution into the PR review pipeline or the onboarding pipeline. Uses `asyncio.gather` to run concurrent agent calls within each pipeline. Contains no business logic; its only responsibility is routing and coordination.

### src/github_client.py

The GitHub API abstraction layer. Wraps PyGithub to expose a clean internal interface for all GitHub operations. Functions include fetching PR diffs, listing changed files, posting PR comments, and committing or updating repository files. All PyGithub usage is contained here, keeping the rest of the codebase decoupled from the GitHub API client.

### src/gather_context.py

Assembles the formatted context string used by the three PR review agents. Accepts the PR number, repository name, file list, and raw diff and returns a single string suitable for injection into agent prompts. Contains no AI calls.

### src/security_scan.py

Runs a narrowly scoped Claude agent over the assembled PR context. The agent is constrained to the Read tool and is prompted to identify hardcoded secrets, injection vulnerabilities, unsafe subprocess usage, missing input validation, and insecure dependency additions. Returns structured FINDINGS output.

### src/quality_review.py

Runs a Claude agent focused on code quality over the same PR context. The agent checks for overly complex functions, naming inconsistencies, missing error handling, duplicated logic, missing tests, and hardcoded values. Returns structured QUALITY NOTES output.

### src/summarize_pr.py

Runs a Claude agent that reads the PR context and produces a concise paragraph summarizing the intent of the change, the affected areas of the codebase, and any notable risks. Its output anchors the human-readable section of the final PR comment.

### src/post_results.py

Receives the outputs from the three review agents, composes them into a single markdown-formatted comment, and delegates posting to `src/github_client.py`. Contains the comment template and formatting logic.

### src/detect_new_repo.py

Acts as the onboarding gate. Queries the repository for the presence of `CONTRIBUTING.md` via `src/github_client.py`. Returns a boolean that controls whether the onboarding pipeline proceeds.

### src/explore_codebase.py

Runs a Claude agent equipped with the Read, Glob, and Bash tools to perform active codebase exploration. The agent traverses the directory structure, identifies languages, frameworks, and entry points, and produces a structured summary. This summary is passed to all three documentation generators.

### src/gen_contributing.py

Runs a Claude agent that takes the codebase summary and produces a complete `CONTRIBUTING.md` file. Coverage includes setup instructions, environment variables, branching conventions, and notes on CodeGuard behavior within the repository.

### src/gen_architecture.py

Runs a Claude agent that takes the codebase summary and produces a complete `ARCHITECTURE.md` file. Coverage includes the system overview, both pipelines, module responsibilities, data flow, and external dependencies.

### src/gen_setup_guide.py

Runs a Claude agent that takes the codebase summary and produces a complete `SETUP.md` file. Coverage includes prerequisites, local setup steps, an environment variable reference, and instructions for manually triggering both pipelines.

---

## Data Flow

The following describes the end-to-end data movement for each pipeline.

### PR Review Data Flow

```
GitHub pull_request event
        │
        ▼
GitHub Actions runner
  sets ENV: EVENT_NAME, PR_NUMBER, REPO_NAME,
            GITHUB_TOKEN, ANTHROPIC_API_KEY
        │
        ▼
src/main.py  ──►  src/gather_context.py
                        │
                        ▼
                  src/github_client.py  ──►  GitHub API
                        │
                        ▼
                  context string (PR number + files + diff)
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
src/security_scan  src/quality_review  src/summarize_pr
   (Claude agent)    (Claude agent)     (Claude agent)
        │               │               │
        ▼               ▼               ▼
    FINDINGS      QUALITY NOTES      SUMMARY
        │               │               │
        └───────────────┴───────────────┘
                        │
                        ▼
                src/post_results.py
                        │
                        ▼
              formatted markdown comment
                        │
                        ▼
               src/github_client.py  ──►  GitHub PR comment
```

### Onboarding Data Flow

```
GitHub push or issue_comment event
        │
        ▼
GitHub Actions runner
  sets ENV: EVENT_NAME, REPO_NAME,
            GITHUB_TOKEN, ANTHROPIC_API_KEY
        │
        ▼
src/main.py  ──►  src/detect_new_repo.py
                        │
                        ▼
              CONTRIBUTING.md present?
              YES → exit   NO → continue
                                │
                                ▼
                      src/explore_codebase.py
                        (Claude agent with
                         Read + Glob + Bash)
                                │
                                ▼
                         codebase summary
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
src/gen_contributing    src/gen_architecture    src/gen_setup_guide
   (Claude agent)          (Claude agent)         (Claude agent)
        │                       │                       │
        ▼                       ▼                       ▼
  CONTRIBUTING.md         ARCHITECTURE.md           SETUP.md
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                                │
                                ▼
                      src/github_client.py
                                │
                                ▼
                    Committed files in repo root
```

---

## External Dependencies

### claude-agent-sdk

The Anthropic Claude Agent SDK is the AI runtime for every agent in the system. It provides the `query` function and `ClaudeAgentOptions` class. The SDK is used in `src/security_scan.py`, `src/quality_review.py`, `src/summarize_pr.py`, `src/explore_codebase.py`, `src/gen_contributing.py`, `src/gen_architecture.py`, and `src/gen_setup_guide.py`. Tool access is scoped per agent at instantiation time: review agents receive only the Read tool to prevent side effects during analysis, while the codebase explorer receives Read, Glob, and Bash to enable active filesystem traversal. The active model across all agents is `claude-sonnet-4-6`.

### pygithub

PyGithub is the Python wrapper for the GitHub REST API. It is used exclusively within `src/github_client.py`. It enables authenticated access to pull request metadata, file diffs, repository contents, comment posting, and file commits without requiring manual HTTP request construction. Centralizing PyGithub usage in a single module ensures that the rest of the codebase remains decoupled from API implementation details.

### python-dotenv

python-dotenv is used for local development ergonomics. It loads variables from a `.env` file into the process environment, supplying `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, and `REPO_NAME` without requiring manual shell exports. In production, these variables are injected directly by GitHub Actions and python-dotenv has no effect.

---

## GitHub Actions Integration

The workflow is defined in `.github/workflows/codeguard.yml` and is the sole mechanism by which CodeGuard is triggered in production.

### Trigger Events

The workflow listens for three event types:

* `pull_request` with activity types `opened`, `synchronize`, and `reopened` to activate the PR review pipeline.
* `push` to the `main` branch to activate the onboarding pipeline on first push.
* `issue_comment` with activity type `created` to allow manual onboarding retrigger via the `/onboard` command.

### Permissions

The workflow grants `pull-requests: write` to allow posting review comments, and `contents: write` to allow committing generated documentation files directly to the repository.

### Runtime Setup

The workflow provisions Python 3.11, installs dependencies from `requirements.txt` via pip, and executes `python src/main.py`.

### Environment Variable Injection

The following variables are injected into the runner environment at job execution time:

* `ANTHROPIC_API_KEY` — sourced from a repository secret; required by the Claude Agent SDK for all agent calls.
* `GITHUB_TOKEN` — sourced from the built-in Actions token; used by PyGithub to authenticate against the GitHub API.
* `PR_NUMBER` — sourced from the GitHub Actions event context; present only during `pull_request` events.
* `REPO_NAME` — sourced from the `github.repository` context variable; present for all events.
* `EVENT_NAME` — sourced from `github.event_name`; read by `src/main.py` to determine which pipeline to execute.

### Execution Model

Each GitHub Actions job run is fully stateless. No data persists between runs. All inputs arrive via environment variables, all outputs are written back to GitHub via API calls, and the runner is discarded at job completion.