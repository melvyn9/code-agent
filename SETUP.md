# ARCHITECTURE.md

# CodeGuard Architecture

## High Level System Overview

CodeGuard is a GitHub integrated AI agent built on the Anthropic Claude Agent SDK. It monitors a repository for two categories of events and responds automatically: it reviews every pull request for security vulnerabilities and code quality issues, and it generates onboarding documentation whenever a new repository is detected to be missing it.

The system has no persistent server or database. Each run is a stateless, ephemeral Python process launched by a GitHub Actions workflow. All state lives either in the GitHub repository itself (comments, committed files) or in environment variables injected at runtime by the workflow runner.

There are two distinct pipelines:

1. The **PR Review Pipeline** analyzes an open pull request and posts a structured markdown comment.
2. The **Onboarding Pipeline** explores the codebase and commits three documentation files directly to the repository.

Both pipelines share a common GitHub client abstraction and are invoked from a single entry point that routes between them based on the incoming GitHub event type.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline is triggered when a pull request is opened, synchronized, or reopened. The entry point reads the `PR_NUMBER` environment variable, fetches the diff and changed file list from GitHub, and assembles a context string. That context is passed concurrently to three independent Claude agents:

- A security scan agent that identifies vulnerabilities such as hardcoded secrets, injection risks, and unsafe subprocess usage.
- A quality review agent that evaluates complexity, naming, error handling, duplication, test coverage, and configuration issues.
- A summarization agent that produces a plain English description of what the pull request does and what risks it introduces.

Once all three agents have returned their outputs, a composition step merges them into a single formatted markdown comment and posts it to the pull request via the GitHub API.

### Onboarding Pipeline

The onboarding pipeline is triggered in two ways: automatically on any push to the main branch when `CONTRIBUTING.md` does not yet exist in the repository root, or manually when a maintainer posts a comment containing the `/onboard` command on any issue.

When triggered, an exploration agent with filesystem tool access maps the repository structure and produces a structured codebase summary. That summary is passed to three independent Claude agents that each generate one documentation file:

- `CONTRIBUTING.md` covering contribution guidelines and workflow.
- `ARCHITECTURE.md` covering system design and module responsibilities.
- `SETUP.md` covering local development environment setup.

Each generated file is committed directly to the repository root via the GitHub API.

---

## Module Breakdown

### `src/main.py`

The single entry point for every pipeline execution. It reads the `EVENT_NAME` environment variable and branches accordingly: `pull_request` events invoke the PR review pipeline, `push` events invoke the onboarding pipeline if `CONTRIBUTING.md` is absent, and `issue_comment` events invoke the onboarding pipeline if the comment body contains `/onboard`. This module contains no business logic of its own; it delegates immediately to the appropriate pipeline modules.

### `src/github_client.py`

A thin wrapper around the PyGithub library. It exposes four reusable helpers used throughout both pipelines:

- `get_pr_diff` fetches the raw unified diff for a given pull request number.
- `get_changed_files` returns the list of filenames modified by a pull request.
- `post_pr_comment` posts a markdown formatted string as a comment on a pull request.
- `commit_file` creates or updates a file at a specified path in the repository with a provided commit message and content string.

All four helpers authenticate using the `GITHUB_TOKEN` environment variable and operate against the repository identified by `REPO_NAME`.

### `src/gather_context.py`

Assembles the PR context string that is passed as input to the three review agents. It calls `get_pr_diff` and `get_changed_files` from `github_client.py` and formats the results together with the PR number and repository name into a single structured string. Centralizing this assembly means each review agent receives identical, consistently formatted input.

### `src/security_scan.py`

An async Claude agent that receives the PR context string and returns a structured `FINDINGS` list. Each finding identifies a specific security concern: hardcoded credentials, injection vulnerabilities, unsafe use of `subprocess`, insecure deserialization, and similar issues. The agent uses the `query` function from the Claude Agent SDK with a prompt that instructs it to reason specifically about security impact and line references.

### `src/quality_review.py`

An async Claude agent that receives the PR context string and returns a `QUALITY NOTES` list. It evaluates the changed code across six dimensions: cyclomatic complexity, identifier naming, error and exception handling, code duplication, test coverage gaps, and hardcoded configuration values. Each note includes a brief rationale.

### `src/summarize_pr.py`

An async Claude agent that receives the PR context string and produces a short `SUMMARY` section in plain English. The summary describes what the pull request does, which parts of the codebase it touches, and any notable risks introduced. This section anchors the final comment and gives reviewers a quick orientation before reading the detailed findings.

### `src/post_results.py`

Receives the string outputs from `security_scan.py`, `quality_review.py`, and `summarize_pr.py` and composes them into a single markdown document. It applies a consistent heading structure and then calls `post_pr_comment` from `github_client.py` to publish the result. This module is the only place where the three agent outputs are combined.

### `src/detect_new_repo.py`

Checks whether `CONTRIBUTING.md` already exists at the root of the repository by attempting to retrieve the file via the GitHub API. Returns a boolean. Called by `main.py` during `push` events to decide whether to trigger the onboarding pipeline. This check prevents the onboarding pipeline from overwriting documentation that already exists.

### `src/explore_codebase.py`

An async Claude agent that is granted access to the `Glob`, `Read`, and `Bash` tools from the Claude Agent SDK. It uses those tools to traverse the repository directory tree, read representative files, and produce a structured prose summary of the codebase: languages used, directory layout, key modules, entry points, and configuration files. The output of this agent is the shared input for all three documentation generator agents.

### `src/gen_contributing.py`

An async Claude agent that receives the codebase summary from `explore_codebase.py` and generates a complete `CONTRIBUTING.md` file. The prompt instructs the agent to cover branching conventions, pull request guidelines, code style expectations, and the process for reporting issues.

### `src/gen_architecture.py`

An async Claude agent that receives the codebase summary and generates a complete `ARCHITECTURE.md` file. The prompt instructs the agent to describe the high level design, module responsibilities, data flow, and external dependencies.

### `src/gen_setup_guide.py`

An async Claude agent that receives the codebase summary and generates a complete `SETUP.md` file. The prompt instructs the agent to cover prerequisites, dependency installation, environment variable configuration, and steps to run the project locally.

---

## Data Flow

### PR Review Data Flow

1. A pull request event fires the GitHub Actions workflow.
2. The workflow runner injects `EVENT_NAME=pull_request`, `PR_NUMBER`, `REPO_NAME`, `GITHUB_TOKEN`, and `ANTHROPIC_API_KEY` as environment variables, then executes `python src/main.py`.
3. `main.py` reads `EVENT_NAME` and calls the PR review pipeline.
4. `gather_context.py` calls `github_client.py` to fetch the diff and file list, then returns a formatted context string.
5. `main.py` calls `security_scan.py`, `quality_review.py`, and `summarize_pr.py` concurrently, passing the context string to each.
6. Each agent sends a prompt to the Claude API and streams back a structured text response.
7. All three responses are passed to `post_results.py`, which formats and posts the combined comment via `github_client.py`.

### Onboarding Data Flow

1. A push to main (or an `/onboard` comment) fires the GitHub Actions workflow.
2. The workflow runner injects `EVENT_NAME`, `REPO_NAME`, `GITHUB_TOKEN`, and `ANTHROPIC_API_KEY`, then executes `python src/main.py`.
3. `main.py` reads `EVENT_NAME`. For `push` events it calls `detect_new_repo.py` first; if `CONTRIBUTING.md` is absent it proceeds.
4. `explore_codebase.py` uses `Glob`, `Read`, and `Bash` tools to inspect the repository and returns a codebase summary string.
5. `main.py` calls `gen_contributing.py`, `gen_architecture.py`, and `gen_setup_guide.py` concurrently, passing the codebase summary to each.
6. Each agent sends a prompt to the Claude API and streams back the full file content.
7. For each generated file, `main.py` calls `commit_file` in `github_client.py` to write the content to the repository root.

---

## External Dependencies

### claude agent sdk

Provides the `query` function and `ClaudeAgentOptions` class used by every agent module. The SDK handles prompt construction, streaming response consumption, tool call execution (for `explore_codebase.py`), and communication with the Anthropic API endpoint. It is the core orchestration layer for all AI driven steps. The model targeted across all agents is `claude-sonnet-4-6`.

### pygithub

Wraps the GitHub REST API and is used exclusively in `github_client.py`. It handles authentication via a personal access token, fetches pull request metadata and diffs, posts issue comments, and creates or updates repository files. Using PyGithub instead of raw HTTP calls eliminates boilerplate around authentication headers, pagination, and response parsing.

### python-dotenv

Loads key value pairs from a `.env` file into the process environment at startup during local development. This allows developers to set `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `REPO_NAME`, `PR_NUMBER`, and `EVENT_NAME` locally without modifying shell profiles or hardcoding values. In the GitHub Actions environment the `.env` file is not present and the variables are provided directly by the workflow runner, so `python-dotenv` becomes a no op in production.

---

## GitHub Actions Integration

The workflow is defined in `.github/workflows/codeguard.yml` and is the sole mechanism by which CodeGuard is executed. It is never invoked manually in production.

### Triggers

The workflow listens for three event types:

- `pull_request` with activity types `opened`, `synchronize`, and `reopened`. This covers new PRs and every subsequent push to an open PR branch.
- `push` filtered to the `main` branch. This covers merges and direct commits that could signal a newly initialized repository.
- `issue_comment` with activity type `created`. This enables the `/onboard` manual trigger for maintainers.

### Steps

Each workflow run performs the following steps in order:

1. Check out the repository using `actions/checkout` so that `explore_codebase.py` can read the local filesystem.
2. Set up Python 3.11 using `actions/setup-python`.
3. Install dependencies by running `pip install -r requirements.txt`.
4. Execute `python src/main.py`.

### Environment Variables

The workflow injects the following variables into the process environment for each run:

- `ANTHROPIC_API_KEY` from a GitHub Actions secret, used by the Claude Agent SDK for API authentication.
- `GITHUB_TOKEN` from `secrets.GITHUB_TOKEN`, the automatically provisioned token used by PyGithub.
- `REPO_NAME` from `github.repository`, the full `owner/repo` identifier.
- `PR_NUMBER` from `github.event.pull_request.number`, available on `pull_request` events.
- `EVENT_NAME` from `github.event_name`, the string that `main.py` reads to route between pipelines.