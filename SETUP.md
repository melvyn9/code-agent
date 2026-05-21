# ARCHITECTURE.md

# CodeGuard Architecture

## High-Level System Overview

CodeGuard is a GitHub-integrated AI agent that performs two distinct automated tasks on repositories: pull request review and onboarding documentation generation. It operates entirely within GitHub Actions, is written in Python 3.11, and relies on the Claude Agent SDK to power every AI-driven step.

When a pull request is opened or updated, CodeGuard runs three parallel AI agents that scan the diff for security vulnerabilities, assess code quality, and summarize the change in plain English. The combined findings are posted back to the pull request as a formatted Markdown comment.

When a push event lands on a repository that has no CONTRIBUTING.md file, CodeGuard treats the repository as new and triggers a separate onboarding pipeline that explores the codebase and generates three documentation files: CONTRIBUTING.md, ARCHITECTURE.md, and SETUP.md. These files are committed directly to the repository.

All execution happens inside a single GitHub Actions workflow. There is no server, no database, and no persistent state outside of what GitHub itself stores.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline is triggered when the EVENT_NAME environment variable is set to `pull_request` or when a qualifying `issue_comment` event includes a recognized command in COMMENT_BODY.

Execution proceeds as follows:

1. `main.py` reads EVENT_NAME and routes to the PR review branch.
2. `gather_context.py` fetches the PR number, repository name, list of changed files, and raw diff from GitHub, then assembles them into a single context string.
3. Three agent modules run against that context string in sequence: `security_scan.py`, `quality_review.py`, and `summarize_pr.py`. Each runs an independent Claude Agent SDK query with a different focused prompt.
4. `post_results.py` combines the three outputs into a single formatted Markdown comment and posts it to the pull request via `github_client.post_pr_comment`.

### Onboarding Pipeline

The onboarding pipeline is triggered when the EVENT_NAME environment variable is set to `push`.

Execution proceeds as follows:

1. `main.py` reads EVENT_NAME and routes to the onboarding branch.
2. `detect_new_repo.py` checks whether CONTRIBUTING.md exists in the repository root. If the file already exists, the pipeline exits immediately and no further work is done.
3. `explore_codebase.py` runs a Claude Agent SDK query with Read, Glob, and Bash tools enabled. The agent maps the directory structure, identifies languages and frameworks, locates entry points, and returns a structured codebase summary string.
4. Three generator modules run in sequence using that summary: `gen_contributing.py`, `gen_architecture.py`, and `gen_setup_guide.py`. Each runs a Claude Agent SDK query and returns the full text of one documentation file.
5. Each generated file is committed to the repository root via `github_client.commit_file`.

---

## Module Breakdown

### src/main.py

The single entry point for the entire application. GitHub Actions invokes this file directly with `python src/main.py`. On startup it reads the EVENT_NAME and COMMENT_BODY environment variables, decides which pipeline applies, and calls the appropriate orchestration logic. It contains no AI logic itself and no GitHub API calls; it is purely a router.

### src/github_client.py

The sole layer that communicates with the GitHub REST API. It wraps PyGithub and exposes six helper functions:

| Function | Responsibility |
|---|---|
| `get_github_client` | Authenticates using GITHUB_TOKEN and returns a PyGithub client instance |
| `get_repo` | Returns a PyGithub repository object for a given repo name |
| `get_pr_diff` | Fetches the raw unified diff for a pull request |
| `get_changed_files` | Returns the list of files modified by a pull request |
| `post_pr_comment` | Posts a Markdown string as a comment on a pull request |
| `commit_file` | Creates or updates a file in the repository with a given path and content |

All other modules that need GitHub access import from this file. No other module interacts with PyGithub directly.

### src/gather_context.py

Assembles the context string that is passed into every PR review agent. It calls `github_client.get_pr_diff` and `github_client.get_changed_files`, then formats the PR number, repository name, file list, and diff into a single structured string.

### src/security_scan.py

Runs a Claude Agent SDK query focused on security. The prompt instructs the agent to look for hardcoded secrets, injection vulnerabilities, unsafe `eval` or `exec` usage, missing input validation, insecure dependencies, and sensitive data in logs. Returns the agent's findings as a string.

### src/quality_review.py

Runs a Claude Agent SDK query focused on code quality. The prompt instructs the agent to look for overly complex functions, naming inconsistencies, weak error handling, duplicated logic, missing tests, and hardcoded values. Returns the agent's findings as a string.

### src/summarize_pr.py

Runs a Claude Agent SDK query that produces a plain-English summary of the pull request. The output is 2 to 5 sentences covering the intent of the change, which areas of the codebase it affects, and any notable risks. Returns the summary as a string.

### src/post_results.py

Takes the three strings returned by `security_scan.py`, `quality_review.py`, and `summarize_pr.py`, formats them into a single structured Markdown comment, and calls `github_client.post_pr_comment` to post it on the pull request.

### src/detect_new_repo.py

Checks whether CONTRIBUTING.md exists in the repository root by calling the GitHub API. Returns a boolean. If the file is present the onboarding pipeline exits immediately without generating or committing any files.

### src/explore_codebase.py

Runs a Claude Agent SDK query with the Read, Glob, and Bash tools enabled. The agent is instructed to walk the directory tree, identify programming languages and frameworks in use, find entry points, and document the overall structure. Returns a codebase summary string that is passed unchanged to all three document generator modules.

### src/gen_contributing.py

Takes the codebase summary and runs a Claude Agent SDK query to produce a complete CONTRIBUTING.md file. The output covers prerequisites, local setup steps, environment variable configuration, pull request conventions, and a description of what CodeGuard checks automatically on each PR.

### src/gen_architecture.py

Takes the codebase summary and runs a Claude Agent SDK query to produce a complete ARCHITECTURE.md file. The output covers the system overview, both pipelines, module responsibilities, data flow, and GitHub Actions integration.

### src/gen_setup_guide.py

Takes the codebase summary and runs a Claude Agent SDK query to produce a complete SETUP.md file. The output covers prerequisites, step-by-step installation, how to populate the `.env` file, and how to test both pipelines locally.

---

## Data Flow

### PR Review Data Flow

```
GitHub Event (pull_request / issue_comment)
        │
        ▼
GitHub Actions sets EVENT_NAME, PR_NUMBER, REPO_NAME
        │
        ▼
src/main.py reads EVENT_NAME → routes to PR review branch
        │
        ▼
src/gather_context.py
  ├── github_client.get_changed_files(PR_NUMBER) → file list
  └── github_client.get_pr_diff(PR_NUMBER)       → raw diff
        │
        ▼
  context_string = PR_NUMBER + REPO_NAME + file list + diff
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼                             ▼
src/security_scan.py            src/quality_review.py          src/summarize_pr.py
  Claude SDK query                Claude SDK query               Claude SDK query
  → security_findings             → quality_findings             → pr_summary
        │                                      │                             │
        └──────────────────────────────────────┘─────────────────────────────┘
        │
        ▼
src/post_results.py
  formats Markdown comment
        │
        ▼
github_client.post_pr_comment(PR_NUMBER, comment)
        │
        ▼
Comment appears on GitHub pull request
```

### Onboarding Data Flow

```
GitHub Event (push)
        │
        ▼
GitHub Actions sets EVENT_NAME, REPO_NAME
        │
        ▼
src/main.py reads EVENT_NAME → routes to onboarding branch
        │
        ▼
src/detect_new_repo.py
  github_client checks for CONTRIBUTING.md
  └── exists? → exit immediately
  └── missing? → continue
        │
        ▼
src/explore_codebase.py
  Claude SDK query (Read + Glob + Bash tools enabled)
  agent walks repo, maps structure, identifies frameworks
  → codebase_summary string
        │
        ├───────────────────────────────────┐─────────────────────────────────┐
        ▼                                   ▼                                 ▼
src/gen_contributing.py       src/gen_architecture.py         src/gen_setup_guide.py
  Claude SDK query               Claude SDK query               Claude SDK query
  → contributing_md              → architecture_md              → setup_md
        │                                   │                                 │
        └───────────────────────────────────┘─────────────────────────────────┘
        │
        ▼
github_client.commit_file × 3
  CONTRIBUTING.md, ARCHITECTURE.md, SETUP.md committed to repo root
        │
        ▼
Files appear in repository on GitHub
```

---

## External Dependencies

### claude-agent-sdk (Anthropic Claude Agent SDK)

This is the core AI framework used by every agent module in the application. It provides the `query` function and the `ClaudeAgentOptions` class. The SDK wraps calls to Claude models and supports optional tool access controls, which is how `explore_codebase.py` enables file reading and shell tools for the codebase exploration step while keeping those tools disabled for the review and generation agents. Every AI-driven step in both pipelines runs through this SDK.

### pygithub (PyGithub)

PyGithub is the GitHub REST API client. It is used exclusively inside `github_client.py` to authenticate with a personal access token, fetch pull request diffs and file lists, post PR comments, and commit or update files in the repository. Centralizing all PyGithub usage in a single module keeps the rest of the codebase free of API details and makes the GitHub integration straightforward to test or swap out.

### python-dotenv

python-dotenv is used to load environment variables from the `.env` file during local development. In production the GitHub Actions runner injects all required secrets and variables directly through the workflow definition, so python-dotenv has no effect at runtime. Its sole purpose is to allow developers to run and test both pipelines locally without manually exporting variables in every shell session.

---

## GitHub Actions Integration

The entire application is driven by the workflow definition at `.github/workflows/codeguard.yml`.

### Triggers

The workflow responds to three GitHub event types:

| Event | Condition | Purpose |
|---|---|---|
| `pull_request` | types: opened, synchronize, reopened | Triggers the PR review pipeline |
| `push` | all branches | Triggers the onboarding pipeline if CONTRIBUTING.md is absent |
| `issue_comment` | types: created | Allows on-demand review via a comment command |

### Runtime Environment

The workflow runner installs Python 3.11, installs all dependencies from `requirements.txt`, and then executes `python src/main.py`. Before execution it injects two secrets from the repository's GitHub Secrets store:

- `ANTHROPIC_API_KEY` is required by the Claude Agent SDK to authenticate with the Anthropic API.
- `GITHUB_TOKEN` is required by PyGithub to read diffs and post comments or commits. GitHub Actions generates this token automatically for each workflow run.

The workflow also sets contextual environment variables such as EVENT_NAME, PR_NUMBER, REPO_NAME, and COMMENT_BODY from GitHub Actions expression syntax so that `main.py` can route execution correctly without parsing the raw event payload.

### Routing Logic

The variable EVENT_NAME is the primary routing signal read by `main.py`. A value of `pull_request` or a `issue_comment` value combined with a recognized command string in COMMENT_BODY sends execution to the PR review pipeline. A value of `push` sends execution to the onboarding pipeline, which then self-gates via the CONTRIBUTING.md presence check before doing any AI work.

### No Persistent Infrastructure

CodeGuard requires no servers, databases, or external storage. The GitHub Actions runner is ephemeral and is discarded after each workflow run. All state persists in GitHub itself: PR comments, committed documentation files, and the repository contents that determine whether onboarding should run.