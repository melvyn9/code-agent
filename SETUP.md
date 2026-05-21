# CodeGuard Architecture

## High-Level System Overview

CodeGuard is a GitHub-integrated AI agent built on the Claude Agent SDK. It operates as a stateless GitHub Actions job rather than a long-running server, meaning it is invoked on demand by GitHub event webhooks, completes its work, writes its outputs, and exits. There is no persistent process, no web framework, and no database beyond a lightweight JSON cache file.

The system serves two distinct purposes. First, it automatically reviews pull requests for security vulnerabilities and code quality issues, then posts a structured markdown comment directly to the pull request on GitHub. Second, when a repository receives its first push and lacks onboarding documentation, it explores the codebase and generates three documentation files: CONTRIBUTING.md, ARCHITECTURE.md, and SETUP.md. Both purposes are served by the same entry point and share the same configuration, logging, and GitHub client infrastructure.

All AI reasoning is delegated to Anthropic models via the Claude Agent SDK. The heavier analysis tasks use claude-sonnet-4-6 for its deeper reasoning capability. The pull request summarization task uses claude-haiku-4-5 because it requires only lightweight text transformation and benefits from faster, lower-cost inference.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline is triggered when GitHub emits a `pull_request` event. The orchestrator in `src/main.py` reads the `EVENT_NAME` environment variable, identifies the event as a pull request, and begins the review sequence.

The pipeline proceeds through five stages:

**Stage 1 — Context Assembly.** The system fetches the pull request diff and the list of changed files from GitHub using PyGithub. These raw materials are assembled by `src/gather_context.py` into a single plain-text context block that includes the PR number, repository name, changed file paths, and the full unified diff. This block becomes the shared input passed to all three review agents.

**Stage 2 — Security Scan.** `src/security_scan.py` dispatches an agent call to claude-sonnet-4-6 with a security-focused prompt and the context block as input. The agent is scoped to the Read tool only. It returns a structured FINDINGS block listing any discovered vulnerabilities. Results are filtered against the configured severity threshold (low, medium, or high) defined in `.codeguard.yml` before being passed downstream.

**Stage 3 — Quality Review.** `src/quality_review.py` dispatches a second agent call to claude-sonnet-4-6 with a code quality prompt. It also receives the same context block and returns a structured QUALITY NOTES block describing issues such as maintainability concerns, test coverage gaps, or antipatterns.

**Stage 4 — PR Summary.** `src/summarize_pr.py` dispatches a third agent call, this time to claude-haiku-4-5. It receives the context block and produces a concise plain-English SUMMARY covering the intent of the pull request, the affected areas of the codebase, and any notable trade-offs observed in the diff.

**Stage 5 — Comment Posting.** `src/post_results.py` receives the three outputs (findings, quality notes, and summary) and composes them into a single formatted markdown comment body. It then calls `src/github_client.py` to post the comment to the pull request. The posting function includes retry logic to handle transient GitHub API failures.

### Onboarding Pipeline

The onboarding pipeline runs under two conditions: a `push` event to the repository, or an `issue_comment` event where the comment body contains the string `/onboard`. In both cases `src/main.py` routes execution to the onboarding sequence.

The pipeline proceeds through six stages:

**Stage 1 — New Repository Detection.** `src/detect_new_repo.py` checks whether CONTRIBUTING.md already exists at the repository root via the GitHub API. If it is present, the pipeline exits immediately with no further action, preventing redundant documentation regeneration on established repositories.

**Stage 2 — Cache Check.** `src/cache.py` reads `.codeguard_cache.json` and computes an MD5 hash of the current repository file tree. If the hash matches the stored hash and a cached codebase summary already exists, the pipeline skips the exploration stage and uses the cached summary directly. This prevents unnecessary AI agent calls on repeated triggers against an unchanged codebase.

**Stage 3 — Codebase Exploration.** If no valid cache entry exists, `src/explore_codebase.py` dispatches an agent call to claude-sonnet-4-6 with access to three tools: Glob (for listing files by pattern), Read (for reading file contents), and Bash (for running lightweight inspection commands). The agent explores the repository structure autonomously and returns a comprehensive plain-text codebase summary. This summary is then written back to the cache alongside the current file tree hash.

**Stage 4 — Document Generation.** Three agents run in sequence, each receiving the codebase summary as input:

- `src/gen_contributing.py` produces a raw CONTRIBUTING.md document.
- `src/gen_architecture.py` produces a raw ARCHITECTURE.md document.
- `src/gen_setup_guide.py` produces a raw SETUP.md document.

**Stage 5 — File Commit.** Each generated document is committed to the repository root by calling `src/github_client.py`'s create-or-update-file function. If a file already exists (for example on a re-onboard triggered by `/onboard`), the function updates it in place using the existing file's SHA.

**Stage 6 — Session Logging.** At the close of both pipelines, `src/logger.py` writes `codeguard_session.json` to disk, recording the full invocation log for the run.

---

## Module Breakdown

### src/main.py

The sole entry point and top-level orchestrator. On startup it loads environment variables, reads the configuration file, instantiates the session logger, and branches on `EVENT_NAME` to dispatch to the PR review pipeline, the push-triggered onboarding pipeline, or the manually triggered onboarding pipeline. It is invoked directly by the GitHub Actions runner via `python src/main.py`.

### src/github_client.py

Wraps PyGithub to provide four utility functions used across both pipelines:

- Fetch the raw unified diff for a given pull request number.
- List the paths of all files changed in a pull request.
- Post a markdown comment to a pull request, with exponential backoff retry logic.
- Create or update a file at a given path in the repository, accepting the file content as a string and committing it with a provided message.

### src/gather_context.py

Assembles the shared plain-text context block that feeds all three PR review agents. It accepts the PR number, repository name, file list, and diff string and formats them into a single structured block. Having one context assembly function ensures all agents reason over identical input.

### src/security_scan.py

Invokes claude-sonnet-4-6 via the Claude Agent SDK with a security analysis system prompt and the assembled context block. The agent is granted only the Read tool, preventing it from taking any side effects. The returned FINDINGS block is filtered by the severity threshold defined in configuration before being returned to the caller.

### src/quality_review.py

Invokes claude-sonnet-4-6 with a code quality system prompt. Like the security agent, it is scoped to the Read tool. It returns a structured QUALITY NOTES block summarizing maintainability issues, design concerns, and antipatterns observed in the diff.

### src/summarize_pr.py

Invokes claude-haiku-4-5 with a summarization prompt. It receives the same context block as the other review agents but uses the lighter model because summarization requires no deep reasoning. It returns a plain-English SUMMARY block describing the intent, scope, and trade-offs of the pull request.

### src/post_results.py

Receives the three review outputs from the security, quality, and summary agents. It composes them into a single markdown comment body with section headers and consistent formatting. It delegates the actual API call to `src/github_client.py`.

### src/detect_new_repo.py

Uses the GitHub API to check whether CONTRIBUTING.md exists at the repository root. Returns a boolean that the orchestrator uses to decide whether to proceed with or skip the onboarding pipeline.

### src/explore_codebase.py

Dispatches a long-running agent call to claude-sonnet-4-6 with Glob, Read, and Bash tools enabled. The agent autonomously explores the repository structure and returns a comprehensive plain-text summary of the codebase. Before dispatching it reads the current cache entry; after dispatching it writes the new summary and file tree hash back to the cache.

### src/gen_contributing.py

Feeds the codebase summary into a prompt that instructs claude-sonnet-4-6 to produce a complete CONTRIBUTING.md document covering contribution workflow, coding standards, and review expectations appropriate for the detected stack.

### src/gen_architecture.py

Feeds the codebase summary into a prompt that instructs claude-sonnet-4-6 to produce a complete ARCHITECTURE.md document describing the system design, module responsibilities, and data flow for the repository being onboarded.

### src/gen_setup_guide.py

Feeds the codebase summary into a prompt that instructs claude-sonnet-4-6 to produce a complete SETUP.md document covering prerequisites, installation steps, environment configuration, and how to run the project locally.

### src/cache.py

Manages `.codeguard_cache.json`. Exposes functions to read the cache, write to the cache, and compute an MD5 hash of the repository file tree. The hash comparison prevents redundant exploration agent calls when the codebase has not changed between triggering events.

### src/config.py

Reads `.codeguard.yml` using PyYAML and merges its values with hardcoded defaults. Exposes a configuration object consumed by `src/main.py` and the individual pipeline modules to determine which features are enabled and what the active severity threshold is.

### src/logger.py

Defines `SessionLogger`, a class that accumulates structured log entries during a run. Each entry records the agent name, the input prompt length, the output result length, a 300-character preview of the result, and a UTC-offset timestamp in the America/Los_Angeles timezone. At the end of a run the orchestrator calls the logger to write the full log to `codeguard_session.json`.

---

## Data Flow

### PR Review Data Flow

1. GitHub emits a `pull_request` event and triggers the GitHub Actions workflow.
2. The workflow runner sets `EVENT_NAME=pull_request`, `REPO_NAME`, and `PR_NUMBER` as environment variables and executes `python src/main.py`.
3. `src/config.py` loads `.codeguard.yml` and merges it with defaults.
4. `src/github_client.py` fetches the PR diff and changed file list from the GitHub REST API using the `GITHUB_TOKEN`.
5. `src/gather_context.py` formats the PR number, repository name, file list, and diff into a plain-text context block.
6. `src/security_scan.py` sends the context block to claude-sonnet-4-6 and receives a FINDINGS block.
7. `src/quality_review.py` sends the same context block to claude-sonnet-4-6 and receives a QUALITY NOTES block.
8. `src/summarize_pr.py` sends the context block to claude-haiku-4-5 and receives a SUMMARY block.
9. `src/post_results.py` composes the three blocks into a single markdown comment and calls `src/github_client.py` to post it to the PR.
10. `src/logger.py` writes `codeguard_session.json` with the full invocation record.

### Onboarding Data Flow

1. GitHub emits a `push` or qualifying `issue_comment` event and triggers the GitHub Actions workflow.
2. The workflow runner sets `EVENT_NAME` appropriately and executes `python src/main.py`.
3. `src/config.py` loads configuration and checks that the onboarding feature is enabled.
4. `src/detect_new_repo.py` queries the GitHub API for the presence of CONTRIBUTING.md. If found, the pipeline exits.
5. `src/cache.py` reads `.codeguard_cache.json` and computes the current file tree hash.
6. If the hash is stale or absent, `src/explore_codebase.py` dispatches an agent with Glob, Read, and Bash tools to explore the repository and produce a codebase summary. The summary and new hash are written back to the cache.
7. If the hash is current, the cached summary is used directly, skipping the exploration agent call.
8. `src/gen_contributing.py`, `src/gen_architecture.py`, and `src/gen_setup_guide.py` each receive the codebase summary and return a complete document as a string.
9. `src/github_client.py` commits each of the three documents to the repository root.
10. `src/logger.py` writes `codeguard_session.json`.

---

## External Dependencies

### claude-agent-sdk

Provides the async agent dispatch interface and `ClaudeAgentOptions` class used by every module that calls an Anthropic model. It abstracts the streaming API, tool permission scoping, and model selection. Without it each module would need to implement its own streaming HTTP client, tool execution loop, and retry handling against the Anthropic API directly. All five agent-dispatching modules (`src/security_scan.py`, `src/quality_review.py`, `src/summarize_pr.py`, `src/explore_codebase.py`, and the three document generators) depend on it.

### pygithub

Wraps the GitHub REST API in a typed Python interface. It is used exclusively in `src/github_client.py` and `src/detect_new_repo.py`. It handles authentication via the `GITHUB_TOKEN`, pagination for file listing, and the ETag-based conditional update required when committing files that may already exist. Replacing it with raw HTTP calls would require reimplementing authentication, pagination, and error parsing.

### python-dotenv

Loads the `.env` file at process startup, populating the environment variables that the rest of the system reads via `os.environ`. It allows secrets such as `ANTHROPIC_API_KEY` and `GITHUB_TOKEN` to be stored outside the codebase during local development while remaining compatible with the environment variable injection that GitHub Actions provides in production.

### pyyaml

Parses `.codeguard.yml` into a Python dictionary in `src/config.py`. YAML was chosen as the configuration format because it is human-readable and widely understood by developers who interact with GitHub Actions workflows, which also use YAML.

### tzdata

Supplies the IANA timezone database on operating systems (notably Windows) where it is not bundled with the OS. It is required by the standard library `zoneinfo` module used in `src/logger.py` to record timestamps in the America/Los_Angeles timezone. On Linux-based GitHub Actions runners the system timezone database is already present, but the dependency is declared in `requirements.txt` to ensure portability across development environments.

---

## GitHub Actions Integration

CodeGuard is designed to run exclusively as a GitHub Actions job. There is no alternative deployment target such as a container service or a webhook server. The workflow file (stored in `.github/workflows/`) defines the events that trigger execution and the environment in which `src/main.py` runs.

**Trigger events.** The workflow listens for three event types:

- `pull_request` with action types `opened`, `synchronize`, and `reopened` to trigger the PR review pipeline.
- `push` to the default branch to trigger the onboarding pipeline.
- `issue_comment` with action type `created` to trigger the manual onboarding pipeline when the comment body contains `/onboard`.

**Environment variable injection.** GitHub Actions passes context to the job via environment variables. The workflow maps GitHub Actions expression values to the variables that `python-dotenv` and `os.environ` expect:

- `EVENT_NAME` is set from `github.event_name`.
- `REPO_NAME` is set from `github.repository`.
- `PR_NUMBER` is set from `github.event.pull_request.number` (available on pull request events).
- `COMMENT_BODY` is set from `github.event.comment.body` (available on issue comment events).
- `GITHUB_TOKEN` is provided by the Actions runner automatically and mapped into the environment.
- `ANTHROPIC_API_KEY` is stored as a GitHub Actions secret and mapped into the environment.

**Permissions.** The workflow grants the job `pull-requests: write` permission to allow posting review comments and `contents: write` permission to allow committing generated documentation files. No other permissions are requested.

**Steps.** The workflow job defines four steps: checking out the repository, setting up Python 3.11, installing dependencies from `requirements.txt` via pip, and executing `python src/main.py`. The checkout step includes the full repository history so that `src/explore_codebase.py` can access all files when the onboarding pipeline runs.

**Conditional execution.** Because `src/main.py` branches entirely on the `EVENT_NAME` environment variable, a single workflow job definition handles all three trigger paths. The workflow itself does not need conditional step logic; the Python orchestrator handles routing internally.