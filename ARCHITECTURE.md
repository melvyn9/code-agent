# ARCHITECTURE.md

# CodeGuard Architecture

## High Level System Overview

CodeGuard is a GitHub integrated AI agent built on the Anthropic Claude Agent SDK. Its purpose is to automatically review pull requests for security vulnerabilities and code quality issues, and to generate onboarding documentation for repositories that do not yet have it.

The system runs entirely inside GitHub Actions. When a GitHub event fires, the workflow injects environment variables into the runtime, and `src/main.py` reads the event type to decide which of the two pipelines to execute. All AI reasoning is delegated to Claude agents via the SDK. All GitHub interaction is handled through PyGithub. The system produces two categories of output: structured markdown comments posted to pull requests, and documentation files committed directly to the repository.

There are no servers, databases, or persistent processes. Each GitHub Actions run is stateless. State is stored in the repository itself (existing files signal whether onboarding has already run) and in GitHub pull request comments.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline is triggered by `pull_request` events (opened, synchronize, reopened). Its goal is to produce a structured code review comment on the pull request covering security, quality, and a plain English summary.

The pipeline runs in four stages:

1. **Context gathering** — `gather_context.py` fetches the PR diff and the list of changed files from the GitHub API and packages them into a single context string.
2. **Parallel agent analysis** — `security_scan.py`, `quality_review.py`, and `summarize_pr.py` each run an independent Claude agent against the same context string. Security scan looks for hardcoded secrets, injection vulnerabilities, unsafe `eval` or `exec` usage, and insecure dependencies. Quality review looks for complexity, naming inconsistencies, missing error handling, duplicated logic, and absent tests. The summarizer produces a 2 to 5 sentence plain English description of what the PR does, which parts of the codebase it touches, and any notable risks.
3. **Result combination** — `post_results.py` merges the three agent outputs into a single structured markdown comment.
4. **Comment posting** — `post_results.py` calls the GitHub API to post the combined comment to the pull request.

### Onboarding Pipeline

The onboarding pipeline is triggered by `push` events to the main branch. Its goal is to generate `CONTRIBUTING.md` and `ARCHITECTURE.md` for repositories that do not yet have them.

The pipeline runs in three stages:

1. **Detection** — `detect_new_repo.py` checks whether `CONTRIBUTING.md` already exists at the repository root. If it does, the pipeline exits early. If it does not, the pipeline continues.
2. **Codebase exploration** — `explore_codebase.py` runs a Claude agent equipped with Glob, Read, and Bash tools. The agent maps the repository structure, identifies the language and framework, locates entry points, and summarizes key modules and dependencies. The output is a codebase summary string.
3. **Document generation** — `gen_contributing.py` and `gen_architecture.py` each take the codebase summary and run a Claude agent to generate the respective documentation file. Both files are committed to the repository root via the GitHub API.

---

## Module Breakdown

### `src/main.py`

The sole entry point for the entire system. Reads the `EVENT_NAME` environment variable and routes execution to either the PR review pipeline or the onboarding pipeline. Contains no business logic of its own beyond the routing decision.

### `src/github_client.py`

Provides all GitHub API helper functions used across both pipelines. Key functions include:

- `get_pr_diff` — fetches the raw unified diff for a pull request
- `get_changed_files` — returns the list of files modified by a pull request
- `post_pr_comment` — posts a markdown string as a comment on a pull request
- `commit_file` — creates or updates a file at a given path in the repository with a specified commit message

All functions in this module accept a PyGithub client instance and the repository name as parameters. This module is the only place in the codebase that directly calls the GitHub API.

### `src/gather_context.py`

Calls `get_pr_diff` and `get_changed_files` from `github_client.py` and assembles the results into a single context string. This string is passed unchanged to `security_scan.py`, `quality_review.py`, and `summarize_pr.py`, ensuring all three review agents operate on the same input.

### `src/security_scan.py`

Runs a Claude agent instructed to analyze the PR diff for hardcoded secrets, injection vulnerabilities, unsafe `eval` or `exec` usage, and insecure dependencies. Returns a markdown formatted string of findings.

### `src/quality_review.py`

Runs a Claude agent instructed to analyze the PR diff for code complexity, naming inconsistencies, missing error handling, duplicated logic, and absent tests. Returns a markdown formatted string of findings.

### `src/summarize_pr.py`

Runs a Claude agent instructed to produce a 2 to 5 sentence plain English summary of the pull request: what it does, which parts of the codebase it affects, and any notable risks. Returns a markdown formatted string.

### `src/post_results.py`

Accepts the outputs of `security_scan.py`, `quality_review.py`, and `summarize_pr.py` and combines them into a single structured markdown comment with labeled sections. Calls `post_pr_comment` from `github_client.py` to post the comment to the pull request.

### `src/detect_new_repo.py`

Checks whether `CONTRIBUTING.md` exists at the root of the target repository using the GitHub API. Returns a boolean signal that `main.py` uses to decide whether to proceed with the onboarding pipeline or exit early.

### `src/explore_codebase.py`

Runs a Claude agent with access to Glob, Read, and Bash tools. The agent explores the repository to map its directory structure, identify the primary language and framework, locate entry points, and summarize key modules and their dependencies. Returns a codebase summary string that is passed to `gen_contributing.py` and `gen_architecture.py`.

### `src/gen_contributing.py`

Takes the codebase summary string from `explore_codebase.py` and runs a Claude agent instructed to generate a complete `CONTRIBUTING.md` file. Calls `commit_file` from `github_client.py` to commit the generated file to the repository root.

### `src/gen_architecture.py`

Takes the same codebase summary string and runs a Claude agent instructed to generate a complete `ARCHITECTURE.md` file. Calls `commit_file` from `github_client.py` to commit the generated file to the repository root.

---

## Data Flow

### PR Review Data Flow

```
GitHub pull_request event
        |
        v
GitHub Actions injects ENV vars (EVENT_NAME, PR_NUMBER, REPO_NAME, tokens)
        |
        v
src/main.py reads EVENT_NAME → routes to PR review pipeline
        |
        v
src/gather_context.py
  → calls github_client.get_pr_diff()
  → calls github_client.get_changed_files()
  → returns combined context string
        |
        v
 ┌──────┴───────────────────────┐
 │                              │
 v                              v                              v
src/security_scan.py   src/quality_review.py   src/summarize_pr.py
 (Claude agent)          (Claude agent)           (Claude agent)
 → markdown findings    → markdown findings      → markdown summary
 └──────────────────────────────┘
        |
        v
src/post_results.py
  → merges three outputs into structured markdown
  → calls github_client.post_pr_comment()
        |
        v
Structured review comment posted to pull request
```

### Onboarding Data Flow

```
GitHub push event (main branch)
        |
        v
GitHub Actions injects ENV vars (EVENT_NAME, REPO_NAME, tokens)
        |
        v
src/main.py reads EVENT_NAME → routes to onboarding pipeline
        |
        v
src/detect_new_repo.py
  → checks if CONTRIBUTING.md exists via GitHub API
  → if exists: exit early
  → if not: continue
        |
        v
src/explore_codebase.py
  → Claude agent with Glob, Read, Bash tools
  → maps structure, identifies language and entry points
  → returns codebase summary string
        |
        v
 ┌──────┴──────────────────┐
 │                         │
 v                         v
src/gen_contributing.py   src/gen_architecture.py
 (Claude agent)            (Claude agent)
 → generates CONTRIBUTING.md  → generates ARCHITECTURE.md
 → calls github_client.commit_file()  → calls github_client.commit_file()
        |                         |
        v                         v
CONTRIBUTING.md committed    ARCHITECTURE.md committed
to repository root           to repository root
```

---

## External Dependencies

### claude-agent-sdk

The Anthropic Claude Agent SDK is the core AI runtime for the project. It provides the `query` function and `ClaudeAgentOptions` used in every agent module. The SDK is used because it abstracts the complexity of running multi-turn AI agents, managing tool calls, and handling model responses. All agents in the system use the `claude-sonnet-4-6` model. The `explore_codebase.py` module takes advantage of the SDK's tool scoping feature to give the agent access to Glob, Read, and Bash tools for repository exploration.

### pygithub

PyGithub is a Python wrapper around the GitHub REST API. It is the only library in the codebase that communicates with GitHub. It is used in `github_client.py` to fetch PR diffs, list changed files, post comments, and commit files. PyGithub was chosen because it provides a clean Python interface to the GitHub API without requiring manual HTTP request construction or response parsing.

### python-dotenv

python-dotenv is used exclusively in local development. It loads environment variables from a `.env` file so that `main.py` and the agent modules can read `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `REPO_NAME`, and `PR_NUMBER` without requiring those variables to be manually exported in the shell. In GitHub Actions, these variables are injected directly by the workflow, so python-dotenv has no effect in CI.

---

## GitHub Actions Integration

The workflow is defined in `.github/workflows/codeguard.yml`. It is the trigger layer that connects GitHub repository events to the Python application.

### Triggers

The workflow fires on two event types:

- `pull_request` with activity types `opened`, `synchronize`, and `reopened`
- `push` to the `main` branch

### Runtime Setup

Each workflow run performs the following steps in order:

1. Checks out the repository using the standard `actions/checkout` action
2. Sets up Python 3.11 using `actions/setup-python`
3. Installs dependencies from `requirements.txt` via pip
4. Runs `src/main.py`

### Environment Variable Injection

The workflow injects the following environment variables into the `src/main.py` process:

| Variable | Source | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | GitHub secret | Authenticates requests to the Claude API |
| `GITHUB_TOKEN` | GitHub secret | Authenticates PyGithub calls to the GitHub API |
| `REPO_NAME` | GitHub Actions context (`github.repository`) | Identifies the repository to operate on |
| `PR_NUMBER` | GitHub Actions context (`github.event.pull_request.number`) | Identifies the pull request for the review pipeline |
| `EVENT_NAME` | GitHub Actions context (`github.event_name`) | Tells `main.py` which pipeline to run |

### Routing

`EVENT_NAME` is the single value that controls which pipeline runs. When `EVENT_NAME` is `pull_request`, the PR review pipeline executes. When `EVENT_NAME` is `push`, the onboarding pipeline executes. This means a single workflow file and a single entry point handle both features without duplication.

### Secrets Management

`ANTHROPIC_API_KEY` and `GITHUB_TOKEN` are stored as GitHub Actions secrets and are never written to the repository. The `.env` file used for local development is excluded by `.gitignore` and is never committed.