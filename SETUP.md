# ARCHITECTURE.md

# CodeGuard Architecture

## High Level System Overview

CodeGuard is a GitHub integrated AI agent built on the Anthropic Claude Agent SDK. It operates as a GitHub Actions job rather than a long running server, meaning it is instantiated on demand in response to repository events, executes a single pipeline run, and then exits. There is no persistent process, no web server, and no inbound HTTP surface.

The system implements two distinct automated pipelines. The first analyzes incoming pull requests for security vulnerabilities and code quality issues, then posts a structured review comment back to the pull request thread. The second detects repositories that lack onboarding documentation and generates a full suite of documents (CONTRIBUTING.md, ARCHITECTURE.md, and SETUP.md) by exploring the codebase with AI agents.

All AI reasoning is delegated to Anthropic models via the Claude Agent SDK. Heavier analysis tasks use claude-sonnet-4-6 while lighter summarization tasks use claude-haiku-4-5. The orchestration layer in Python coordinates context assembly, agent dispatch, result composition, and GitHub API interactions.

---

## The Two Pipelines

### PR Review Pipeline

The PR Review pipeline is triggered when a pull request is opened or synchronized against the repository. The orchestrator reads the PR number from the environment, fetches the diff and file list from GitHub, and assembles a plain text context block. That context is fed sequentially to three independent agents: a security scanner, a code quality reviewer, and a PR summarizer. The three structured outputs are composed into a single markdown comment body and posted back to the pull request via the GitHub REST API.

Each of the three agent invocations is independently gated by a feature flag in `.codeguard.yml`, so operators can disable any combination of security scanning, quality review, or summarization without modifying source code.

### Onboarding Pipeline

The Onboarding pipeline activates under two conditions: a push event to a repository that does not yet contain a CONTRIBUTING.md file at its root, or a manual trigger issued by posting a comment containing the string `/onboard` on any issue in the repository.

When onboarding is needed, the system first checks a local JSON cache to determine whether the repository structure has changed since the last exploration. If the cached MD5 hash of the file tree matches the current tree, the stored codebase summary is reused, avoiding redundant AI calls. Otherwise, an exploration agent equipped with Glob, Read, and Bash tools traverses the repository and produces a comprehensive summary, which is then written back to the cache.

The codebase summary is passed independently to three document generation agents, each producing one of the three onboarding documents. The resulting files are committed directly to the repository via the GitHub API, creating or updating them as needed.

---

## Module Breakdown

### src/main.py

The sole entry point and top level orchestrator. On startup it loads environment variables, reads the configuration file, determines the event type by inspecting the `EVENT_NAME` variable, and routes execution to either the PR Review pipeline or the Onboarding pipeline. It also initializes the SessionLogger and writes the session log to `codeguard_session.json` on exit. It is invoked by the GitHub Actions runner via `python src/main.py`.

### src/github_client.py

A thin wrapper around PyGithub that exposes four utility functions used by the rest of the system. `fetch_pr_diff` retrieves the raw unified diff for a given pull request. `list_changed_files` returns the list of filenames touched by the pull request. `post_pr_comment` posts a markdown string to the pull request thread and includes retry logic with exponential backoff to handle transient GitHub API rate limits. `create_or_update_file` commits a file at a specified repository path, either creating it if it does not exist or replacing its contents if it does.

### src/gather_context.py

Assembles the plain text context block that is passed as input to the three PR Review agents. The block includes the PR number, repository name, the list of changed files, and the full raw diff. Centralizing context assembly here ensures that all three agents operate from an identical, consistently formatted input.

### src/security_scan.py

Invokes the Claude Agent SDK with claude-sonnet-4-6 and a security focused system prompt scoped to the Read tool. The prompt instructs the model to identify vulnerabilities, injection risks, secrets exposure, and insecure patterns. The agent returns a structured FINDINGS block. Before returning results to the caller, this module filters the findings against the severity threshold configured in `.codeguard.yml`, suppressing lower severity findings when the operator has configured a stricter threshold.

### src/quality_review.py

Invokes the Claude Agent SDK with claude-sonnet-4-6 and a code quality focused system prompt also scoped to the Read tool. The prompt directs the model to assess readability, maintainability, test coverage signals, error handling, and adherence to language idioms. The agent returns a structured QUALITY NOTES block.

### src/summarize_pr.py

Invokes the Claude Agent SDK with claude-haiku-4-5, the lighter model, to generate a concise plain English SUMMARY of the pull request. The summary covers the inferred intent of the change, the areas of the codebase affected, and any notable trade-offs. Using the smaller model here reflects that summarization requires less analytical depth than security or quality analysis.

### src/post_results.py

Composes the outputs of the three review agents into a single cohesive markdown comment body, then delegates posting to `github_client.post_pr_comment`. This module owns the visual structure of the review comment: section headers, separators, and the ordering of security findings, quality notes, and the summary.

### src/detect_new_repo.py

Determines whether the Onboarding pipeline needs to run by checking whether CONTRIBUTING.md exists at the root of the target repository. Its absence is treated as the signal that the repository has not yet been onboarded. This module is intentionally narrow in scope so the detection logic can be updated or replaced without touching the broader orchestrator.

### src/explore_codebase.py

Runs the Claude Agent SDK exploration agent, equipping it with Glob, Read, and Bash tools so it can traverse the repository file tree, read source files, and execute safe introspection commands. The agent produces a comprehensive plain text codebase summary. Before invoking the agent, this module reads the cache via `src/cache.py`; after a successful exploration it writes the new summary and hash back to the cache.

### src/gen_contributing.py

Accepts the codebase summary as input and invokes the Claude Agent SDK with a prompt that instructs the model to produce a contributor guide covering development setup, branching conventions, commit message style, pull request expectations, and code review norms.

### src/gen_architecture.py

Accepts the codebase summary as input and invokes the Claude Agent SDK with a prompt that instructs the model to produce an architecture document covering system design, module responsibilities, data flow, and dependency rationale.

### src/gen_setup_guide.py

Accepts the codebase summary as input and invokes the Claude Agent SDK with a prompt that instructs the model to produce a setup guide covering prerequisites, installation steps, environment variable configuration, and instructions for running the project locally.

### src/cache.py

Manages the `.codeguard_cache.json` file, a JSON store with two fields: an MD5 hash of the repository file tree snapshot and the most recently produced codebase summary string. It exposes read and write functions used by `src/explore_codebase.py` to avoid redundant AI exploration calls when the repository has not changed between runs.

### src/config.py

Reads `.codeguard.yml` using PyYAML and merges its contents with hardcoded defaults. The resulting configuration object controls four feature flags (security scanning, quality review, summarization, and onboarding document generation) and the security severity threshold. Modules that need configuration receive this object from the orchestrator rather than reading the file themselves.

### src/logger.py

Defines `SessionLogger`, a lightweight structured logger that records each agent invocation as a JSON object containing the agent name, prompt character length, result character length, a 300-character preview of the result text, and an ISO 8601 timestamp localized to America/Los_Angeles. At the end of each run the accumulated log is serialized and written to `codeguard_session.json`. The session log is intended for operator inspection and debugging rather than any automated downstream consumption.

---

## Data Flow

### PR Review Pipeline Data Flow

1. The GitHub Actions runner sets `EVENT_NAME=pull_request` and `PR_NUMBER=<n>` in the job environment.
2. `src/main.py` reads those values and loads the configuration from `.codeguard.yml`.
3. `src/github_client.py` calls the GitHub REST API to fetch the diff and the list of changed files for the specified PR.
4. `src/gather_context.py` formats the PR metadata and diff into a single plain text context block.
5. The context block is passed to `src/security_scan.py`, `src/quality_review.py`, and `src/summarize_pr.py` in sequence.
6. Each module dispatches an async agent call via the Claude Agent SDK and receives a structured text block in return.
7. `src/post_results.py` merges the three text blocks into a markdown comment and calls `src/github_client.py` to post it to the pull request.
8. `src/logger.py` records each agent invocation and `src/main.py` writes `codeguard_session.json` before exiting.

### Onboarding Pipeline Data Flow

1. The GitHub Actions runner sets `EVENT_NAME=push` (or the comment body triggers the manual path via `EVENT_NAME=issue_comment`).
2. `src/main.py` calls `src/detect_new_repo.py`, which queries the GitHub API for the presence of CONTRIBUTING.md.
3. If onboarding is needed, `src/explore_codebase.py` checks `src/cache.py` for a valid cached summary. On a cache miss it invokes the exploration agent, receives the codebase summary, and writes it back to the cache.
4. The codebase summary string is passed to `src/gen_contributing.py`, `src/gen_architecture.py`, and `src/gen_setup_guide.py`.
5. Each module dispatches an agent call and receives the raw document text.
6. `src/main.py` calls `src/github_client.py` three times to commit each document to the repository, creating or updating the files as appropriate.
7. The session logger records all agent invocations and the session JSON is written on exit.

---

## External Dependencies

### claude-agent-sdk

The Anthropic Claude Agent SDK is the core AI orchestration layer. It provides the async `query` interface, the `ClaudeAgentOptions` class for scoping tool permissions per invocation, and the streaming result handling used by all agent modules. The SDK abstracts model selection, tool execution, and result aggregation, allowing each module to declare only what tools it needs (for example, security scan uses only Read while codebase exploration uses Glob, Read, and Bash).

### pygithub

PyGithub is the Python wrapper around the GitHub REST API v3. It is used to fetch pull request diffs and changed file lists, post comments to pull request threads, and create or update files committed directly to a repository branch. It handles authentication via a personal access token supplied through the `GITHUB_TOKEN` environment variable.

### python-dotenv

python-dotenv reads the `.env` file at process startup and populates the process environment. This allows secrets and runtime parameters such as `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `REPO_NAME`, `EVENT_NAME`, `PR_NUMBER`, and `COMMENT_BODY` to be stored outside source control while remaining accessible to the application through `os.environ`.

### pyyaml

PyYAML parses `.codeguard.yml` into a Python dictionary. YAML was chosen for the configuration format because it is human readable and does not require quoting string values, making it accessible to non-developer repository maintainers who need to adjust feature flags or severity thresholds.

### tzdata

The tzdata package ships the IANA timezone database as a Python package. It is required on Windows where the operating system does not bundle timezone data, ensuring that the standard library `zoneinfo` module can resolve the America/Los_Angeles timezone used by `SessionLogger` for timestamping agent invocations.

---

## GitHub Actions Integration

The GitHub Actions workflow file defines the conditions under which CodeGuard is invoked and supplies the environment variables the system depends on.

The workflow is triggered on three event types: `pull_request` (with the `opened` and `synchronize` activity types), `push` (to the default branch), and `issue_comment` (with the `created` activity type, filtered to comments that contain `/onboard`).

The job checks out the repository, sets up Python 3.11, installs dependencies from `requirements.txt` into the virtual environment, and then runs `python src/main.py`. The following environment variables are injected into the job step:

`ANTHROPIC_API_KEY` is read from a repository secret and authorizes calls to the Anthropic API.
`GITHUB_TOKEN` is provided automatically by the Actions runtime and authorizes PyGithub to read PR data and commit files.
`REPO_NAME` is set to the `github.repository` context value (owner/repo format).
`EVENT_NAME` is set to the `github.event_name` context value and drives pipeline branching inside `src/main.py`.
`PR_NUMBER` is set to the pull request number when the trigger is a pull request event.
`COMMENT_BODY` is set to the issue comment body when the trigger is an issue comment event, allowing `src/main.py` to detect the `/onboard` command.

Because the project has no server process to keep running between events, the GitHub Actions model is the natural deployment target: each event spawns a fresh ephemeral job, the pipeline runs to completion, and the runner is released. The only state that persists between runs is what is committed to the repository itself (the generated documentation files) and the `.codeguard_cache.json` file if the workflow is configured to cache it between jobs using the Actions cache action.