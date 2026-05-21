# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent built on the Anthropic Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for newly created repositories.

## Prerequisites

Before setting up the project, ensure you have the following installed:

- Python 3.11
- Git
- A GitHub account with access to the repository
- An Anthropic API key with access to Claude models
- A GitHub personal access token with repository read and write permissions

## Cloning and Setting Up the Project

Clone the repository to your local machine:

```
git clone https://github.com/<your-org>/codeguard.git
cd codeguard
```

Create a virtual environment in the project root:

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

You should see the `venv` prefix appear in your shell prompt, confirming the environment is active.

## Installing Dependencies

With the virtual environment active, install all runtime dependencies from the requirements file:

```
pip install -r requirements.txt
```

This installs `claude-agent-sdk`, `pygithub`, and `python-dotenv`.

## Environment Variables

CodeGuard reads configuration from environment variables at runtime. During local development these are loaded automatically from a `.env` file in the project root via `python-dotenv`. Create the file before running the project:

```
touch .env
```

Then populate it with the following variables:

**ANTHROPIC_API_KEY**
Your Anthropic API key. This is required by every agent module to send prompts to Claude and receive structured responses. Without it the process will exit immediately.

**GITHUB_TOKEN**
A GitHub personal access token. This is used by `github_client.py` to read pull request diffs, list changed files, post review comments, and commit generated documentation back to the repository. The token must have `repo` scope.

**REPO_NAME**
The full repository name in `owner/repository` format (for example `acme/codeguard`). This tells the GitHub client which repository to operate on.

**PR_NUMBER**
The number of the pull request to review. This is only required when simulating a pull request review pipeline locally. Leave it unset or empty when testing the onboarding pipeline.

**EVENT_NAME**
The GitHub event type that determines which pipeline `src/main.py` executes. Accepted values are `pull_request` (runs the PR review pipeline), `push` (runs the onboarding pipeline if `CONTRIBUTING.md` does not exist), and `issue_comment` (triggers manual onboarding re-run when a comment contains the `/onboard` command).

A complete `.env` file looks like this:

```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
REPO_NAME=acme/codeguard
PR_NUMBER=42
EVENT_NAME=pull_request
```

The `.env` file is listed in `.gitignore` and must never be committed to version control.

## Running the Project Locally

With the virtual environment active and `.env` populated, run the entry point directly:

```
python src/main.py
```

`src/main.py` reads `EVENT_NAME` and routes execution to the appropriate pipeline. To test the PR review pipeline, set `EVENT_NAME=pull_request` and provide a valid `PR_NUMBER`. To test the onboarding pipeline, set `EVENT_NAME=push` and ensure the target repository does not already contain a `CONTRIBUTING.md` at its root.

## Branch Naming Conventions

Use the following prefixes when naming branches:

- `feature/` for new functionality or capabilities (example: `feature/add-complexity-scoring`)
- `fix/` for bug fixes (example: `fix/post-comment-auth-error`)
- `docs/` for documentation changes only (example: `docs/update-setup-guide`)
- `refactor/` for internal restructuring that does not change external behavior (example: `refactor/consolidate-agent-options`)
- `chore/` for dependency updates, configuration changes, or tooling maintenance

Branch names should be lowercase and use forward slashes only as the prefix separator. Use descriptive names that communicate intent without requiring additional context.

## Opening a Pull Request

Before opening a pull request, verify that your branch is up to date with `main` and that `python src/main.py` runs without errors against a test repository.

When opening the pull request:

1. Target the `main` branch as the base.
2. Write a title that completes the sentence "This PR will..." in plain English.
3. Include a description that explains what changed, why it changed, and any risks or tradeoffs introduced.
4. Reference any related issues by number in the description.
5. Request at least one reviewer before marking the pull request as ready for review.

Keep pull requests focused on a single concern. Large or mixed-purpose pull requests are harder to review and harder to revert if a problem is found later.

## What CodeGuard Checks on Every Pull Request

When a pull request is opened, synchronized, or reopened against this repository, the `codeguard.yml` GitHub Actions workflow runs `python src/main.py` automatically with `EVENT_NAME=pull_request`. CodeGuard will post a single formatted markdown comment to the pull request containing the output of three independent review passes:

**Security scan** (`src/security_scan.py`) reports a structured `FINDINGS` list. It looks for hardcoded secrets and credentials, injection vulnerabilities, unsafe subprocess usage, and other patterns that introduce security risk.

**Quality review** (`src/quality_review.py`) reports a `QUALITY NOTES` list covering cyclomatic complexity, naming clarity, error handling gaps, code duplication, test coverage, and unsafe or missing configuration practices.

**PR summary** (`src/summarize_pr.py`) produces a short plain-English `SUMMARY` describing what the pull request does, which parts of the codebase it affects, and any notable risks a reviewer should pay attention to.

All three outputs are composed by `src/post_results.py` and posted as one comment. Address any security findings before requesting a final review. Quality notes are advisory and can be discussed in the pull request thread.