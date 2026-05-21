# ARCHITECTURE.md

## CodeGuard System Architecture

---

## High Level System Overview

CodeGuard is a GitHub integrated AI agent built on the Anthropic Claude Agent SDK. It operates as a stateless Python process invoked by GitHub Actions and performs two distinct automated tasks: reviewing pull requests for security vulnerabilities and code quality issues, and generating onboarding documentation for new repositories.

The system has no persistent server, no database, and no web interface. Every run is triggered by a GitHub event, executes to completion inside a GitHub Actions runner, and produces its outputs as pull request comments, committed markdown files, and an uploaded session artifact. All intelligence is delegated to Claude models via the Anthropic Claude Agent SDK.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline activates when a pull request is opened or updated, or when an issue comment contains the `/onboard` command directed at a pull request context.

The pipeline proceeds through the following stages in order:

1. `gather_context.py` assembles the pull request number, repository name, list of changed files, and the unified diff into a single context string.
2. `security_scan.py` sends that context to a Claude agent with a security focused prompt and returns a formatted FINDINGS block, filtered to the configured severity threshold.
3. `quality_review.py` sends the same context to a separate Claude agent with a code quality prompt and returns a formatted QUALITY NOTES block organised by issue type.
4. `summarize_pr.py` sends the context to a Claude Haiku model and returns a two to five sentence plain English summary of the pull request's intent and impact.
5. `post_results.py` assembles all three outputs into a single markdown comment body and publishes it to the pull request via `github_client.py`.

Each of the three AI calls is independent. The security scan, quality review, and summary each invoke their own Claude agent with their own prompt and return their own structured block. They are assembled only at the final posting step.

### Onboarding Pipeline

The onboarding pipeline activates on push events to the main branch when `detect_new_repo.py` determines that `CONTRIBUTING.md` does not yet exist in the repository.

The pipeline proceeds through the following stages in order:

1. `explore_codebase.py` runs a Claude agent equipped with the Read, Glob, and Bash tools to autonomously traverse the repository and produce a structured codebase summary string. Before running, it consults `cache.py` to check whether the repository structure has changed since the last run. If the cached hash matches the current file tree hash, the stored summary is returned directly and no AI exploration is performed.
2. `gen_contributing.py`, `gen_architecture.py`, and `gen_setup_guide.py` each receive the codebase summary string and independently prompt a Claude agent to produce the corresponding markdown document.
3. `github_client.py` creates or updates each of the three generated files in the repository using the GitHub API.

The three document generation calls are logically independent of one another. They share only the codebase summary string as input and each writes to a separate file path in the repository.

---

## Module Breakdown

### src/main.py

The sole entry point and central orchestrator. It loads configuration from `config.py`, reads environment variables to identify the triggering event type (pull request, push to main, or issue comment), and dispatches to either the PR review pipeline or the onboarding pipeline. After either pipeline completes, it calls `logger.py` to write the session record.

### src/config.py

Responsible for all configuration loading. It reads `.codeguard.yml` from the repository root using PyYAML, merges the parsed values with hardcoded defaults for any missing keys, and returns a unified dictionary. The dictionary is consumed by `main.py` to decide which pipeline features are enabled and what the active severity threshold is.

### src/github_client.py

A thin wrapper around the PyGitHub library. It exposes four functions used across the system: retrieving a pull request diff, listing the files changed in a pull request, posting a comment to a pull request, and creating or updating a file in the repository. All authentication is handled through the `GITHUB_TOKEN` environment variable. No other module interacts with the GitHub API directly.

### src/gather_context.py

Assembles the PR context string passed as input to the three AI review agents. It calls `github_client.py` to retrieve the pull request diff and list of changed files, then combines those with the pull request number and repository name into a single formatted string.

### src/security_scan.py

Sends the assembled PR context to a Claude agent with a structured security focused system prompt. Returns a formatted FINDINGS block. Results are filtered to include only findings at or above the severity threshold specified in the configuration.

### src/quality_review.py

Sends the assembled PR context to a Claude agent with a code quality system prompt. Returns a formatted QUALITY NOTES block with issues organised by category. Operates entirely independently of `security_scan.py`.

### src/summarize_pr.py

Sends the assembled PR context to the Claude Haiku model and returns a concise plain English summary of the pull request's purpose and likely impact. Haiku is used here rather than a larger model because summarisation requires less reasoning depth and benefits from lower latency.

### src/post_results.py

Accepts the summary string, the FINDINGS block, and the QUALITY NOTES block, and assembles them into a single markdown comment. Calls `github_client.post_pr_comment` to publish the comment on the pull request. This module contains no AI calls; it is purely compositional.

### src/explore_codebase.py

Runs a Claude agent with access to the Read, Glob, and Bash tools. The agent autonomously explores the repository structure and produces a structured codebase summary string. Before invoking the agent, it calls `cache.py` to check whether the repository file tree has changed. If the hash is unchanged, the cached summary is returned immediately and the agent is not invoked.

### src/gen_contributing.py

Accepts the codebase summary string and prompts a Claude agent to produce a `CONTRIBUTING.md` document. Returns the raw markdown content.

### src/gen_architecture.py

Accepts the codebase summary string and prompts a Claude agent to produce an `ARCHITECTURE.md` document. Returns the raw markdown content.

### src/gen_setup_guide.py

Accepts the codebase summary string and prompts a Claude agent to produce a `SETUP.md` document. Returns the raw markdown content.

### src/detect_new_repo.py

Checks whether `CONTRIBUTING.md` already exists in the repository by querying the GitHub API via `github_client.py`. If the file is absent, the function returns true and `main.py` proceeds with the onboarding pipeline. This module has no AI calls.

### src/cache.py

Computes an MD5 hash of the full repository file tree by listing all files via the GitHub API. Compares the computed hash against a stored hash in `.codeguard_cache.json`. If the hashes differ or no cache exists, returns a miss and the caller proceeds to run `explore_codebase.py`. After a successful exploration, persists both the new hash and the generated codebase summary string to `.codeguard_cache.json`.

### src/logger.py

Implements the `SessionLogger` class. Every agent module registers its invocation metadata and a truncated output preview with the logger during a run. At the end of the run, `main.py` calls the logger to serialise the complete record as `codeguard_session.json`. Timestamps are recorded in the America/Los_Angeles timezone using the `tzdata` package.

---

## Data Flow

### PR Review Data Flow

```
GitHub Event (pull_request / issue_comment)
        |
        v
main.py reads EVENT_NAME, PR_NUMBER from environment
        |
        v
config.py loads .codeguard.yml and returns feature flags + severity threshold
        |
        v
gather_context.py calls github_client.py to fetch diff and changed files
        |
        v
    [assembled PR context string]
        |
        +----> security_scan.py ----> Claude agent (security prompt) ----> FINDINGS block
        |
        +----> quality_review.py ---> Claude agent (quality prompt)  ----> QUALITY NOTES block
        |
        +----> summarize_pr.py -----> Claude Haiku model             ----> summary string
        |
        v
post_results.py assembles all three outputs into a markdown comment
        |
        v
github_client.post_pr_comment publishes comment on the pull request
        |
        v
logger.py writes codeguard_session.json
        |
        v
GitHub Actions uploads codeguard_session.json as an artifact
```

### Onboarding Data Flow

```
GitHub Event (push to main)
        |
        v
main.py reads EVENT_NAME from environment
        |
        v
detect_new_repo.py queries GitHub API for CONTRIBUTING.md existence
        |
        [if absent]
        v
cache.py computes MD5 hash of repository file tree
        |
        +-- [hash matches cached hash] --> return cached codebase summary
        |
        +-- [hash differs or no cache] --> explore_codebase.py runs Claude agent
                                           with Read, Glob, Bash tools
                                           --> structured codebase summary string
                                           --> cache.py persists new hash + summary
        |
        v
    [codebase summary string]
        |
        +----> gen_contributing.py --> Claude agent --> CONTRIBUTING.md content
        |
        +----> gen_architecture.py --> Claude agent --> ARCHITECTURE.md content
        |
        +----> gen_setup_guide.py  --> Claude agent --> SETUP.md content
        |
        v
github_client.create_or_update_file commits each document to the repository
        |
        v
logger.py writes codeguard_session.json
        |
        v
GitHub Actions uploads codeguard_session.json as an artifact
```

---

## External Dependencies

### Anthropic Claude Agent SDK (`claude-agent-sdk`)

The core AI execution framework. Every module that performs an AI task imports the `query` function and the `ClaudeAgentOptions` class from this SDK. The SDK manages the conversation loop, tool execution, and model invocation. CodeGuard delegates all intelligence to Claude through this interface and has no custom model logic of its own.

### PyGitHub (`pygithub`)

The Python client for the GitHub REST API. Used exclusively within `github_client.py` to abstract all repository interactions. Chosen because it provides a Pythonic, object oriented interface over the raw GitHub API and handles authentication, pagination, and request construction automatically.

### python-dotenv

Loads `.env` files into environment variables at process start. Used only during local development runs to replicate the environment variable context that GitHub Actions provides automatically in CI. Has no effect in production.

### PyYAML (`pyyaml`)

Parses the `.codeguard.yml` configuration file into a Python dictionary. Used exclusively within `config.py`. Chosen because YAML is the standard format for GitHub Actions and repository configuration files, and PyYAML is the canonical Python parser for it.

### tzdata

Provides timezone data required by `logger.py` to record session timestamps in the America/Los_Angeles timezone. Included as an explicit dependency because some minimal runtime environments do not ship system timezone data by default.

---

## GitHub Actions Integration

The workflow is defined in `.github/workflows/codeguard.yml` and is the only mechanism by which the system is invoked in production.

### Trigger Conditions

The workflow fires on three event types:

- `pull_request` events with actions `opened`, `synchronize`, and `reopened`, which trigger the PR review pipeline.
- `push` events targeting the main branch, which trigger the onboarding pipeline check.
- `issue_comment` events with action `created`, which trigger the PR review pipeline when the comment body contains the `/onboard` command.

### Environment Variable Injection

The workflow sets all environment variables that `main.py` and other modules read at runtime. This includes:

- `ANTHROPIC_API_KEY` sourced from a GitHub Actions secret, used by the Claude Agent SDK for model authentication.
- `GITHUB_TOKEN` sourced from the built-in `secrets.GITHUB_TOKEN`, used by `github_client.py` for all GitHub API calls.
- `REPO_NAME` set from `github.repository`, identifying the target repository.
- `EVENT_NAME` set from `github.event_name`, used by `main.py` to select the correct pipeline.
- `PR_NUMBER` set from `github.event.pull_request.number` or the issue comment context, used by `gather_context.py`.
- `COMMENT_BODY` set from `github.event.comment.body` when the trigger is an issue comment, used by `main.py` to detect the `/onboard` command.

### Execution Steps

The workflow checks out the repository, sets up Python 3.11, installs dependencies from `requirements.txt` into the virtual environment, and then executes `python src/main.py`. After the process exits, the workflow runs an artifact upload step that attaches `codeguard_session.json` to the workflow run, making the full session log available for inspection in the GitHub Actions UI.

### Secrets and Permissions

The workflow requires two secrets: `ANTHROPIC_API_KEY` must be added manually to the repository's Actions secrets. `GITHUB_TOKEN` is provided automatically by GitHub Actions. The workflow also requires that the Actions runner has write permission to repository contents so that `github_client.py` can commit the generated onboarding documents.