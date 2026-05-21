# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent built on the Anthropic Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories.

## Prerequisites

Before setting up CodeGuard locally, ensure you have the following installed:

- Python 3.11
- Git
- A GitHub account with access to the repository
- An Anthropic API key with access to Claude models

## Cloning and Setting Up the Project

Clone the repository to your local machine:

```
git clone https://github.com/<your-org>/codeguard.git
cd codeguard
```

Create a Python virtual environment in the project root:

```
python3.11 -m venv venv
```

## Activating the Virtual Environment

On macOS and Linux:

```
source venv/bin/activate
```

On Windows:

```
venv\Scripts\activate
```

You should see `(venv)` prepended to your shell prompt once the environment is active. All subsequent commands assume the virtual environment is active.

## Installing Dependencies

With the virtual environment active, install all required packages:

```
pip install -r requirements.txt
```

The project depends on the following packages:

- `claude-agent-sdk` — the Anthropic Claude Agent SDK, which provides the `query` function and `ClaudeAgentOptions` class used by every agent module
- `pygithub` — the Python GitHub API client used to interact with repositories, pull requests, and file contents
- `python-dotenv` — loads `.env` files into environment variables for local development
- `pyyaml` — parses the `.codeguard.yml` configuration file into a Python dictionary
- `tzdata` — provides timezone data used by the session logger to record timestamps in America/Los Angeles time

## Required Environment Variables

Create a `.env` file in the project root by copying the example below. This file is used only for local development and must never be committed to the repository.

```
ANTHROPIC_API_KEY=
GITHUB_TOKEN=
REPO_NAME=
EVENT_NAME=
PR_NUMBER=
COMMENT_BODY=
```

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key. Required by every agent module to invoke Claude models. |
| `GITHUB_TOKEN` | A GitHub personal access token with `repo` scope. Used by `github_client.py` to read pull request data, post comments, and create or update files in the repository. |
| `REPO_NAME` | The full repository name in `owner/repo` format, for example `myorg/codeguard`. Tells the agent which repository to operate on. |
| `EVENT_NAME` | The GitHub Actions event that triggered the run. Accepted values are `pull_request`, `push`, and `issue_comment`. The orchestrator uses this to route to the correct pipeline. |
| `PR_NUMBER` | The pull request number to review. Required when `EVENT_NAME` is `pull_request`. |
| `COMMENT_BODY` | The body of the issue comment that triggered the run. Required when `EVENT_NAME` is `issue_comment` so the orchestrator can detect the `/onboard` command. |

In the GitHub Actions environment, all of these variables are injected automatically from GitHub secrets and workflow context. You do not need to set them manually for CI runs.

## Running the Project Locally

With the virtual environment active and your `.env` file populated, run the agent from the project root:

```
python src/main.py
```

The orchestrator reads `EVENT_NAME` and routes execution accordingly:

- If `EVENT_NAME` is `pull_request`, it runs the PR review pipeline: it gathers the diff, invokes the security and quality agents, assembles the results, and posts a comment to the pull request.
- If `EVENT_NAME` is `push`, it checks whether `CONTRIBUTING.md` exists in the repository and, if not, triggers the onboarding documentation pipeline.
- If `EVENT_NAME` is `issue_comment` and `COMMENT_BODY` contains `/onboard`, it triggers the onboarding documentation pipeline directly.

At the end of every run, a session log is written to `codeguard_session.json` in the project root. This file records metadata and a truncated result preview for each agent invocation and is useful for local debugging.

## Branch Naming Conventions

Use the following prefixes when naming branches:

- `feature/` for new features or capabilities, for example `feature/add-severity-filter`
- `fix/` for bug fixes, for example `fix/cache-hash-collision`
- `docs/` for documentation changes only, for example `docs/update-setup-guide`
- `chore/` for dependency updates, configuration changes, or other maintenance work

Branch names should be lowercase and use hyphens to separate words. Do not include ticket numbers or personal identifiers in branch names.

## Opening a Pull Request

1. Create a branch from `main` using the naming convention above.
2. Make your changes and commit them with clear, imperative commit messages that describe what the change does, for example `Add severity threshold validation to config loader`.
3. Push your branch and open a pull request against `main`.
4. In the pull request description, summarise what you changed and why. If the change affects the `.codeguard.yml` configuration schema, document the new or modified fields.
5. Ensure all required environment variables referenced in your changes are documented in this file and in `.env.example` if one exists.
6. Wait for the CodeGuard automated review to complete before requesting a human review.

## What CodeGuard Checks on Every Pull Request

When a pull request is opened or updated, the GitHub Actions workflow triggers CodeGuard automatically. It performs the following checks and posts its findings as a single comment on the pull request:

**PR Summary.** The `summarize_pr` module uses Claude Haiku to produce a two to five sentence plain-English description of the pull request's intent and impact. This summary appears at the top of the comment to give reviewers immediate context.

**Security Scan.** The `security_scan` module sends the full PR diff to a Claude agent with a security-focused prompt. It returns a FINDINGS block listing any detected vulnerabilities. Results are filtered by the severity threshold set in `.codeguard.yml`. Only findings at or above the configured threshold are included in the comment.

**Code Quality Review.** The `quality_review` module sends the PR diff to a Claude agent with a code quality prompt. It returns a QUALITY NOTES block categorised by issue type, covering concerns such as error handling, code clarity, test coverage, and maintainability.

All three sections are assembled by `post_results.py` into a single markdown comment and posted to the pull request via the GitHub API. The full session log, including each agent invocation's inputs and outputs, is uploaded as a GitHub Actions artifact named `codeguard_session` for observability and debugging purposes.