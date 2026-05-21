# Contributing to CodeGuard

CodeGuard is an AI powered GitHub automation agent that runs entirely inside GitHub Actions to automatically review pull requests for security vulnerabilities and code quality issues and to generate onboarding documentation for new repositories upon first push. It is built on the Claude Agent SDK by Anthropic and uses PyGitHub to interact with the GitHub REST API.

## Prerequisites

Before setting up the project locally, ensure you have the following installed:

- Python 3.11 (exact version required; the GitHub Actions workflow installs 3.11 explicitly)
- pip (included with Python 3.11)
- git
- A GitHub personal access token with repository read and write permissions
- An Anthropic API key with access to claude-sonnet-4-6 and claude-haiku-4-5

## Cloning and Setting Up the Project

Clone the repository to your local machine:

    git clone https://github.com/your-org/codeguard.git
    cd codeguard

Create a virtual environment in the repository root:

    python3.11 -m venv venv

## Activating the Virtual Environment

On macOS and Linux:

    source venv/bin/activate

On Windows:

    venv\Scripts\activate

You should see the virtual environment name in your shell prompt once it is active. All subsequent commands assume the virtual environment is active.

## Installing Dependencies

With the virtual environment active, install all runtime dependencies from the requirements file:

    pip install -r requirements.txt

This installs the five direct dependencies: the Claude Agent SDK, PyGitHub, python-dotenv, PyYAML, and tzdata.

## Environment Variables

CodeGuard reads its configuration from environment variables at runtime. During local development, create a file named `.env` in the repository root. The python-dotenv library loads this file automatically when `src/main.py` starts. The `.env` file is excluded from version control via `.gitignore` and must never be committed.

The required variables are:

**ANTHROPIC_API_KEY**
Your Anthropic API key. All agent modules use this key to authenticate calls to Claude models. Without it, every agent invocation will fail.

**GITHUB_TOKEN**
A GitHub personal access token. PyGitHub uses this token to fetch PR diffs and file lists, post review comments, commit generated documentation, and traverse the repository file tree for cache hashing. The token needs read and write access to the target repository.

**GITHUB_REPOSITORY**
The full repository name in `owner/repo` format (for example, `acme/codeguard`). The orchestrator uses this to instantiate the PyGitHub client and locate the correct repository.

**EVENT_NAME**
Controls which pipeline `src/main.py` executes. Set this to `pull_request` to run the PR review pipeline (security scan, quality review, and summary), `push` to run the onboarding documentation pipeline, or `issue_comment` to run the manual `/onboard` command pipeline triggered by a PR comment.

**PR_NUMBER**
The pull request number to review. Required when `EVENT_NAME` is `pull_request` or `issue_comment`. Not used by the push pipeline.

**SECURITY_THRESHOLD** (optional)
Sets the minimum severity level that the security agent will report. Accepted values are `low`, `medium`, and `high`. If omitted, the value falls back to whatever is set in `.codeguard.yml`, or to the hardcoded default if that file is absent.

## Running the Project Locally

With the virtual environment active and the `.env` file populated, run the entry point directly:

    python src/main.py

The orchestrator reads `EVENT_NAME`, routes execution to the appropriate pipeline, and writes a session log to `codeguard_session.json` on completion. Review that file to see metadata about each agent invocation including prompt length, result length, a preview of the output, and a Pacific time timestamp.

To test the PR review pipeline locally, set `EVENT_NAME=pull_request` and `PR_NUMBER` to any open pull request number in the target repository before running.

## Branch Naming Conventions

All branches must be created from `main`. Use the following prefixes to indicate the purpose of a branch:

- `feature/` for new capabilities or agent additions (example: `feature/add-license-scan`)
- `fix/` for bug corrections (example: `fix/cache-hash-collision`)
- `docs/` for documentation only changes (example: `docs/update-setup-guide`)
- `chore/` for dependency updates, CI changes, or housekeeping (example: `chore/pin-pygithub-version`)

Branch names should be lowercase and use hyphens to separate words within the descriptor segment. Keep branch names concise and descriptive.

## Opening a Pull Request

Before opening a pull request, ensure the following:

1. Your branch is up to date with `main`.
2. All new or changed modules have corresponding docstrings.
3. The `EVENT_NAME`, `GITHUB_TOKEN`, and `ANTHROPIC_API_KEY` variables are documented in this file if you introduced them.
4. Any new direct dependency is added to `requirements.txt`.

Open a pull request against `main` with a title that summarizes the change in plain English. The body should describe what problem the change solves, what approach was taken, and any decisions a reviewer should know about. Tag at least one maintainer as a reviewer before marking the PR ready for review.

## What CodeGuard Checks on Every Pull Request

When a pull request is opened or updated, the GitHub Actions workflow triggers CodeGuard to run three automated checks and post a single consolidated comment to the PR.

**Security scan**
A claude-sonnet-4-6 agent reviews the PR diff for hardcoded secrets, injection vulnerabilities, unsafe subprocess usage, and similar issues. Findings are filtered to the configured severity threshold before being included in the comment.

**Quality review**
A second claude-sonnet-4-6 agent reviews the same diff for code quality issues including excessive complexity, poor naming, missing error handling, code duplication, and absent tests.

**PR summary**
A claude-haiku-4-5 agent writes a concise plain English summary of what the PR does and what risks it introduces. This summary appears at the top of the consolidated comment to give reviewers immediate context.

All three outputs are assembled by `src/post_results.py` into a single formatted markdown comment and posted to the PR via the GitHub API. A session log is uploaded as a GitHub Actions artifact after every run and is retained for later inspection.