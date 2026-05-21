# ARCHITECTURE.md

# CodeGuard Architecture

## High Level System Overview

CodeGuard is an AI powered GitHub automation agent that operates entirely within GitHub Actions. It has two primary responsibilities: reviewing pull requests for security vulnerabilities and code quality issues, and generating onboarding documentation for repositories that do not yet have any.

The system is driven by a single Python entry point that reads GitHub event context at runtime and routes execution to the appropriate pipeline. All AI reasoning is delegated to Claude models via the Anthropic Claude Agent SDK. Every interaction with GitHub — reading diffs, posting comments, committing files — goes through the PyGitHub library. Execution is asynchronous, with multiple agent coroutines capable of running in parallel via Python's asyncio runtime.

There are no servers, no databases, and no persistent infrastructure. The entire system lives in source control and executes ephemerally inside GitHub Actions runners.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline is triggered when a pull request is opened or updated. Its goal is to produce a single formatted comment on the PR that contains a security analysis, a code quality analysis, and a plain English summary.

Execution proceeds as follows:

1. `src/main.py` detects a `pull_request` event and calls `src/gather_context.py`.
2. `gather_context.py` fetches the PR diff and the list of changed files from GitHub, then packages them into a single context string.
3. `src/main.py` dispatches three agent calls, potentially in parallel via asyncio: `src/security_scan.py`, `src/quality_review.py`, and `src/summarize_pr.py`.
4. Each agent module sends its prompt plus the context string to a Claude model and returns a result string.
5. `src/post_results.py` receives the three result strings, assembles them into a single markdown comment body, and posts it to the PR via the GitHub API.

The security scan and quality review each use `claude-sonnet-4-6`. The summary uses the lighter `claude-haiku-4-5` model because it requires less analytical depth. Each of the four feature areas (security, quality, summary, onboarding) can be disabled independently via `.codeguard.yml`.

### Onboarding Pipeline

The onboarding pipeline is triggered on a push to the main branch. Its goal is to generate three documentation files — `CONTRIBUTING.md`, `ARCHITECTURE.md`, and `SETUP.md` — and commit them directly to the repository.

Execution proceeds as follows:

1. `src/main.py` detects a `push` event and calls `src/detect_new_repo.py`.
2. `detect_new_repo.py` checks whether `CONTRIBUTING.md` already exists. If it does, the pipeline exits immediately. If it does not, onboarding proceeds.
3. `src/explore_codebase.py` is called. It first consults `src/cache.py` to see whether a valid cached summary exists. If the repository file tree hash matches the stored hash, the cached summary is returned immediately. Otherwise, a `claude-sonnet-4-6` agent equipped with `Read`, `Glob`, and `Bash` tools explores the repository and produces a structured textual summary. The result is written back to the cache.
4. `src/main.py` dispatches three documentation generator agents in parallel: `src/gen_contributing.py`, `src/gen_architecture.py`, and `src/gen_setup_guide.py`. Each receives the codebase summary and returns a markdown document string.
5. Each generated file is committed to the repository via the GitHub API.

A third trigger also exists for the onboarding pipeline: a manual `/onboard` command posted as a PR comment. In that case, `src/main.py` detects an `issue_comment` event, verifies the comment body, and runs the same onboarding steps described above.

---

## Module Breakdown

### src/main.py

The orchestrator and sole entry point for every execution. Reads the `EVENT_NAME` environment variable to determine which pipeline to run. Coordinates calls to all other modules, manages asyncio task dispatch for parallel agent execution, and writes `codeguard_session.json` to disk on completion for upload as a GitHub Actions artifact.

### src/gather_context.py

Fetches the diff and the list of changed files for a given PR using PyGitHub. Combines them into a single formatted context string that is passed to all three review agents.

### src/security_scan.py

Runs a `claude-sonnet-4-6` agent with a prompt focused on identifying hardcoded secrets, injection vulnerabilities, unsafe subprocess usage, insecure deserialization, and related issues. The severity threshold (low, medium, or high) is read from configuration and controls how aggressively the agent flags findings.

### src/quality_review.py

Runs a `claude-sonnet-4-6` agent with a prompt focused on code quality: excessive complexity, poor naming, missing error handling, code duplication, and absent or inadequate tests.

### src/summarize_pr.py

Runs a `claude-haiku-4-5` agent to produce a concise plain English summary of what the PR does and what risks it may introduce. Uses the lighter Haiku model because the task requires comprehension and synthesis rather than deep analytical reasoning.

### src/post_results.py

Assembles the outputs of the three review agents into a single structured markdown comment and posts it to the PR using PyGitHub.

### src/detect_new_repo.py

Checks whether `CONTRIBUTING.md` exists in the repository root via the GitHub API. Returns a boolean. If `CONTRIBUTING.md` is present, the onboarding pipeline is skipped entirely.

### src/explore_codebase.py

Runs a `claude-sonnet-4-6` agent equipped with `Read`, `Glob`, and `Bash` tools. The agent autonomously explores the repository structure and produces a structured textual summary suitable for use as input to the documentation generators. Consults the cache before running and persists results after running.

### src/gen_contributing.py

Runs a `claude-sonnet-4-6` agent that takes the codebase summary and generates a `CONTRIBUTING.md` file.

### src/gen_architecture.py

Runs a `claude-sonnet-4-6` agent that takes the codebase summary and generates an `ARCHITECTURE.md` file.

### src/gen_setup_guide.py

Runs a `claude-sonnet-4-6` agent that takes the codebase summary and generates a `SETUP.md` file.

### src/cache.py

Computes an MD5 hash of the repository file tree by enumerating all files via the GitHub API. Compares the computed hash against a hash stored in `.codeguard_cache.json`. Provides read and write accessors for both the hash and the cached codebase summary string. This avoids re-running the expensive `explore_codebase` agent when the repository has not changed since the last run.

### src/config.py

Loads `.codeguard.yml` using PyYAML. Deep merges each configuration section with hardcoded defaults so that any omitted key falls back gracefully. If the file is absent entirely, all defaults are used.

### src/logger.py

Implements `SessionLogger`, a class that records a structured log entry for each agent invocation. Each entry captures the agent name, prompt length, result length, a 300 character preview of the result, and a timestamp in Pacific time. At the end of a run, the entire session is serialized to `codeguard_session.json`.

---

## Data Flow

### PR Review Data Flow

```
GitHub pull_request event
        │
        ▼
src/main.py reads EVENT_NAME, PR number, repo name
        │
        ▼
src/gather_context.py ──► GitHub API (diff + file list)
        │
        ▼
     context string
     ┌──┴──────────────┬─────────────────┐
     ▼                 ▼                 ▼
security_scan.py   quality_review.py  summarize_pr.py
(claude-sonnet)    (claude-sonnet)    (claude-haiku)
     │                 │                 │
     └──────────┬──────┘                 │
                ▼                        │
         security result          summary result
                │                        │
                └──────────┬─────────────┘
                           ▼
                  src/post_results.py
                           │
                           ▼
                  GitHub API (PR comment)
```

### Onboarding Data Flow

```
GitHub push event (or /onboard comment)
        │
        ▼
src/main.py reads EVENT_NAME, repo name
        │
        ▼
src/detect_new_repo.py ──► GitHub API (check CONTRIBUTING.md)
        │
   (absent only)
        ▼
src/cache.py ──► GitHub API (file tree MD5 hash)
        │
   (cache miss)
        ▼
src/explore_codebase.py (claude-sonnet + Read/Glob/Bash tools)
        │
        ▼
     codebase summary string ──► cache write
     ┌──────────┬──────────┐
     ▼          ▼          ▼
gen_contributing  gen_architecture  gen_setup_guide
(claude-sonnet)  (claude-sonnet)   (claude-sonnet)
     │                │                  │
     ▼                ▼                  ▼
CONTRIBUTING.md  ARCHITECTURE.md      SETUP.md
     └────────────────┴──────────────────┘
                       │
                       ▼
             GitHub API (commit files)
```

Throughout both pipelines, `src/logger.py` records an entry for each agent call. On completion, `src/main.py` writes `codeguard_session.json` to disk.

---

## External Dependencies

### claude-agent-sdk (Anthropic Claude Agent SDK)

Provides the `query` coroutine and `ClaudeAgentOptions` class used by every agent module. All AI reasoning in the system — security analysis, quality review, PR summarization, codebase exploration, and documentation generation — is expressed as a prompt sent through this SDK. The SDK handles streaming, retries, and tool execution loops for agents that use tools such as `Read`, `Glob`, and `Bash`.

### pygithub

Abstracts the GitHub REST API into a Python object model. Used in `gather_context.py` to fetch PR diffs and file lists, in `post_results.py` to post PR comments, in `detect_new_repo.py` to check for existing files, in `explore_codebase.py` and `cache.py` to traverse the repository file tree, and in the documentation generators to commit the generated markdown files.

### python-dotenv

Loads key-value pairs from a `.env` file into environment variables at process startup. This allows the project to run locally with secrets stored in a `.env` file rather than requiring manual shell exports. In production (GitHub Actions), environment variables are injected by the workflow and this library has no effect.

### pyyaml

Parses `.codeguard.yml`, the user-facing project configuration file. Used exclusively in `src/config.py`.

### tzdata

Supplies IANA timezone data on Linux environments where the operating system does not include it natively. Required so that the `zoneinfo` standard library module can resolve `America/Los_Angeles` for the Pacific time timestamps written by `src/logger.py`. GitHub Actions runners are Linux-based and do not include system timezone data by default.

---

## GitHub Actions Integration

The entire system is defined in `.github/workflows/codeguard.yml`. This single workflow file ties together all triggers, permissions, environment setup, and artifact retention.

### Triggers

The workflow responds to three event types:

- `pull_request` — fires when a PR is opened, synchronized, or reopened. Routes to the PR review pipeline.
- `push` to the main branch — fires when a commit lands on main. Routes to the onboarding pipeline.
- `issue_comment` — fires when a comment is posted on any issue or PR. `src/main.py` inspects the comment body and only proceeds if it contains the `/onboard` command.

### Permissions

The workflow grants two explicit permissions to the `GITHUB_TOKEN`:

- `pull-requests: write` — required to post the review comment on the PR.
- `contents: write` — required to commit the generated documentation files to the repository.

### Runtime Steps

1. Check out the repository at the relevant ref.
2. Set up Python 3.11.
3. Install dependencies from `requirements.txt` via pip.
4. Run `python src/main.py` with the following environment variables injected:
   - `ANTHROPIC_API_KEY` — authenticates calls to the Claude API.
   - `GITHUB_TOKEN` — authenticates PyGitHub calls.
   - `EVENT_NAME` — the GitHub event name, used by `src/main.py` to select the pipeline.
   - `PR_NUMBER` — the pull request number, present for PR and comment events.
   - `REPO_NAME` — the full repository name in `owner/repo` format.
   - `COMMENT_BODY` — the comment text, present for comment events.
5. Upload `codeguard_session.json` as a named artifact retained for 30 days, regardless of whether the run succeeded or failed. This artifact provides an audit trail of every agent invocation, its inputs, its outputs, and the time it occurred.