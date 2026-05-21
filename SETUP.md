# ARCHITECTURE.md

# CodeGuard Architecture

## High Level System Overview

CodeGuard is a GitHub integrated AI agent built on the Anthropic Claude Agent SDK. It operates as a fully automated code review and repository onboarding assistant that runs inside GitHub Actions. When a pull request is opened or updated, CodeGuard analyses the diff for security vulnerabilities and code quality issues, then posts a structured summary comment directly on the pull request. When a repository receives its first push to the main branch, CodeGuard explores the codebase and generates three onboarding documents: CONTRIBUTING.md, ARCHITECTURE.md, and SETUP.md.

The system has no persistent server, no database, and no web interface. Every execution is stateless and event driven. GitHub Actions provides the compute environment, secrets management, and event routing. The Claude Agent SDK provides the AI reasoning layer. PyGithub provides the GitHub API integration.

All application logic is written in Python 3.11 and lives under the `src/` directory. A single GitHub Actions workflow file orchestrates every trigger and execution path.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline activates on `pull_request` events. It is composed of four sequential stages.

**Stage 1: Context Assembly**
`src/gather_context.py` fetches the pull request number, repository name, list of changed files, and the raw unified diff from the GitHub API. It formats these into a single context string that all three review agents will share.

**Stage 2: Parallel Agent Execution**
Three independent Claude agents run concurrently using `asyncio.gather`:

- `src/security_scan.py` receives the context and searches for hardcoded secrets, injection vulnerabilities, unsafe uses of `eval`, missing input validation, and insecure dependency additions.
- `src/quality_review.py` receives the same context and evaluates cyclomatic complexity, naming conventions, error handling patterns, code duplication, test coverage gaps, inline documentation, and configuration hygiene.
- `src/summarize_pr.py` receives the same context and produces a plain English summary of what the pull request does, which parts of the codebase it affects, and any notable risks.

**Stage 3: Result Composition and Posting**
`src/post_results.py` takes the three agent outputs and assembles them into a single formatted markdown comment. It then calls `src/github_client.py` to post that comment to the pull request via the GitHub REST API.

**Stage 4: Completion**
The GitHub Actions job exits. No state is written to the repository. The comment is the only artifact.

---

### Onboarding Pipeline

The onboarding pipeline activates on two triggers: a `push` event to the main branch (when the repository is new), and an `issue_comment` event containing the `/onboard` command (manual re-trigger).

**Stage 1: Newness Check**
`src/detect_new_repo.py` calls the GitHub API to check whether CONTRIBUTING.md already exists in the repository root. If the file is present, the pipeline exits immediately without performing any further work. This prevents duplicate onboarding on every subsequent push.

**Stage 2: Codebase Exploration**
`src/explore_codebase.py` runs a Claude agent equipped with three tools: Glob, Read, and Bash. The agent uses these tools to traverse the repository, inspect files, and produce a structured architectural summary that describes the project's purpose, language, directory layout, key modules, and dependencies. This summary is a plain text document that the three documentation generators will each receive as input.

**Stage 3: Parallel Document Generation**
Three independent Claude agents run concurrently using `asyncio.gather`:

- `src/gen_contributing.py` generates a complete CONTRIBUTING.md covering prerequisites, local setup steps, environment variables, branch naming conventions, and the pull request workflow.
- `src/gen_architecture.py` generates a complete ARCHITECTURE.md covering the system overview, module breakdown, data flow, and external dependencies.
- `src/gen_setup_guide.py` generates a complete SETUP.md covering prerequisites, a numbered step by step setup sequence, an environment variable reference table, and common mistakes.

**Stage 4: Commit to Repository**
`src/github_client.py` commits each of the three generated files to the repository root using the GitHub REST API. If a file already exists (for example during a manual re-trigger), the commit updates the existing file rather than creating a duplicate.

---

## Module Breakdown

### src/main.py

The single application entry point and async orchestrator. Reads the `EVENT_NAME` environment variable set by GitHub Actions and dispatches to the appropriate pipeline. Handles three cases: `pull_request` events route to the PR review pipeline, `push` events route to the onboarding pipeline (after the newness check), and `issue_comment` events containing the `/onboard` command bypass the newness check and force onboarding to run. All async coordination, including `asyncio.gather` calls for parallel agent execution, is managed here.

### src/github_client.py

The GitHub API abstraction layer. Wraps PyGithub to provide four functions used by the rest of the system:

- `get_pr_diff` fetches the raw unified diff for a pull request.
- `get_changed_files` returns the list of file paths modified by a pull request.
- `post_pr_comment` posts a string as an issue comment on a pull request.
- `commit_file` creates or updates a file at a given repository path with provided string content.

All four functions authenticate using the `GITHUB_TOKEN` environment variable.

### src/gather_context.py

Assembles the PR review context. Calls `get_pr_diff` and `get_changed_files` from `github_client`, then formats the pull request number, repository name, file list, and diff into a single multi-section string. This string is the sole input to all three review agents.

### src/security_scan.py

Runs a Claude agent with a security focused system prompt. The agent receives the PR context string and returns a structured list of findings covering hardcoded secrets, injection vulnerabilities, unsafe `eval` usage, missing input validation, and insecure dependency additions. Returns a plain text or markdown findings block.

### src/quality_review.py

Runs a Claude agent with a code quality focused system prompt. The agent receives the same PR context string and evaluates complexity, naming, error handling, duplication, test coverage, documentation, and configuration issues. Returns a structured markdown findings block.

### src/summarize_pr.py

Runs a Claude agent with a summarisation prompt. The agent produces a two to five sentence plain English description of what the pull request does, which parts of the codebase it touches, and any notable risks. Returns a short prose block.

### src/post_results.py

Composes the outputs from `summarize_pr`, `security_scan`, and `quality_review` into a single formatted markdown comment with clear section headings. Calls `post_pr_comment` from `github_client` to publish the comment to the pull request.

### src/detect_new_repo.py

Checks whether CONTRIBUTING.md exists in the repository root by querying the GitHub API via `github_client`. Returns a boolean. Used by `main.py` to gate the onboarding pipeline on `push` events.

### src/explore_codebase.py

Runs a Claude agent equipped with Glob, Read, and Bash tools. The agent autonomously traverses the repository structure, reads key files, and produces a structured architectural summary as a plain text document. This summary is the shared input to all three documentation generators. No external input beyond repository access credentials is required.

### src/gen_contributing.py

Accepts the codebase summary string from `explore_codebase` and runs a Claude agent with a prompt instructing it to produce a complete CONTRIBUTING.md. The output covers prerequisites, local setup, environment variable configuration, branch naming conventions, and the pull request workflow. Returns the file content as a string.

### src/gen_architecture.py

Accepts the codebase summary string and runs a Claude agent to produce a complete ARCHITECTURE.md covering system overview, module breakdown, data flow, and external dependencies. Returns the file content as a string.

### src/gen_setup_guide.py

Accepts the codebase summary string and runs a Claude agent to produce a complete SETUP.md covering prerequisites, a numbered setup sequence, an environment variable reference, and common mistakes. Returns the file content as a string.

---

## Data Flow

### PR Review Data Flow

    GitHub pull_request event
        |
        v
    GitHub Actions workflow (codeguard.yml)
        sets ENV: EVENT_NAME, PR_NUMBER, REPO_NAME, GITHUB_TOKEN, ANTHROPIC_API_KEY
        |
        v
    src/main.py
        detects EVENT_NAME == "pull_request"
        |
        v
    src/gather_context.py
        calls github_client.get_pr_diff and get_changed_files
        returns: formatted context string
        |
        v
    asyncio.gather (concurrent)
        |           |           |
        v           v           v
    security_   quality_    summarize_
    scan.py     review.py   pr.py
        |           |           |
        v           v           v
    findings    findings    summary
    string      string      string
        |           |           |
        +-----+-----+
               |
               v
    src/post_results.py
        composes markdown comment
        calls github_client.post_pr_comment
        |
        v
    Pull request comment posted on GitHub

### Onboarding Data Flow

    GitHub push event (to main) or issue_comment containing "/onboard"
        |
        v
    GitHub Actions workflow (codeguard.yml)
        sets ENV: EVENT_NAME, REPO_NAME, GITHUB_TOKEN, ANTHROPIC_API_KEY
        |
        v
    src/main.py
        detects EVENT_NAME == "push" or "/onboard" comment
        |
        v
    src/detect_new_repo.py
        checks whether CONTRIBUTING.md exists
        if exists and not forced: exit
        |
        v
    src/explore_codebase.py
        Claude agent with Glob, Read, Bash tools
        returns: codebase summary string
        |
        v
    asyncio.gather (concurrent)
        |                   |                   |
        v                   v                   v
    gen_contributing.py  gen_architecture.py  gen_setup_guide.py
        |                   |                   |
        v                   v                   v
    CONTRIBUTING.md      ARCHITECTURE.md      SETUP.md
    content string       content string       content string
        |                   |                   |
        +--------+----------+
                 |
                 v
    src/github_client.py
        commit_file called three times (or concurrently)
        |
        v
    Three files committed to repository root on GitHub

---

## External Dependencies

### claude-agent-sdk

The Anthropic Claude Agent SDK is the AI reasoning layer for every agent in the system. It provides an async streaming interface to Claude models and supports configurable tool access (Read, Glob, Bash) scoped per agent invocation. The SDK is used rather than raw API calls because it handles streaming responses, tool call execution loops, and model selection in a single abstraction. The `claude-sonnet-4-6` model is selected for all tasks as it provides the right balance of instruction following and reasoning depth for code analysis and document generation.

### pygithub

PyGithub provides a typed Python wrapper around the GitHub REST API. It is used to fetch pull request diffs and changed file lists, post issue comments, and commit or update files in a repository. The REST API is used instead of the GraphQL API because PyGithub covers all required operations with a simpler interface and no schema management overhead.

### python-dotenv

python-dotenv loads key value pairs from a `.env` file into `os.environ` at process startup. It is used exclusively during local development to supply `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `REPO_NAME`, `PR_NUMBER`, and `EVENT_NAME` without hardcoding credentials. In the GitHub Actions environment these same variables are injected as environment variables by the workflow, so python-dotenv has no effect in production but causes no harm.

---

## GitHub Actions Integration

The file `.github/workflows/codeguard.yml` is the single workflow definition that drives all CodeGuard execution. It defines three triggers:

- `pull_request` events on any branch activate the PR review pipeline.
- `push` events targeting the main branch activate the onboarding pipeline.
- `issue_comment` events activate the onboarding pipeline when the comment body contains the `/onboard` command.

The workflow defines a single job that runs on `ubuntu-latest`. The job steps are:

1. Check out the repository using `actions/checkout`.
2. Set up Python 3.11 using `actions/setup-python`.
3. Install dependencies from `requirements.txt` using pip.
4. Run `python src/main.py`.

Secrets are passed to the process as environment variables. `ANTHROPIC_API_KEY` is drawn from the repository secrets store and made available as `ANTHROPIC_API_KEY`. `GITHUB_TOKEN` is the automatically provisioned Actions token available as `secrets.GITHUB_TOKEN`, granting the workflow read access to pull request data and write access to post comments and commit files. Runtime context variables (`PR_NUMBER`, `REPO_NAME`, `EVENT_NAME`) are populated from GitHub Actions expression contexts (`github.event.number`, `github.repository`, `github.event_name`) and passed as environment variables so that `src/main.py` can read them with `os.environ`.

Because the workflow uses the built-in `GITHUB_TOKEN`, no additional GitHub App registration or personal access token configuration is required for standard repository usage. The token's write permissions cover issue comment creation and repository content commits, which are the only write operations CodeGuard performs.