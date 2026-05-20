# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for newly created repositories. It is triggered by GitHub Actions and posts its findings directly as GitHub comments.

## Prerequisites

Before setting up the project, ensure you have the following installed:

- Python 3.11
- Git
- A GitHub account with access to the repository
- An Anthropic API key with access to Claude models

## Cloning and Setting Up the Project Locally

Clone the repository to your local machine:

```
git clone https://github.com/<your-org>/codeguard.git
cd codeguard
```

Create a virtual environment inside the project directory:

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

You should see `(venv)` appear in your terminal prompt when the environment is active. Always activate the virtual environment before running any project commands or installing dependencies.

## Installing Dependencies

With the virtual environment active, install all required dependencies from the lockfile:

```
pip install -r requirements.txt
```

This installs the three direct dependencies: `claude-agent-sdk`, `pygithub`, and `python-dotenv`.

## Environment Variables

The project uses `python-dotenv` to load environment variables from a `.env` file at the project root. This file is excluded from version control. Create it manually before running the project locally:

```
touch .env
```

Add the following variables to the file:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key. Used by all Claude agent modules to authenticate requests to the Anthropic API. |
| `GITHUB_TOKEN` | A GitHub personal access token with `repo` scope. Used by `github_client.py` to read pull request diffs, post comments, and commit generated files via the GitHub REST API. |
| `REPO_NAME` | The full repository name in `owner/repo` format. Identifies which repository the agent should operate on during a local run. |
| `PR_NUMBER` | The number of the pull request to review. Required when simulating the PR review pipeline locally. Set to any open PR number in the target repository. |
| `EVENT_NAME` | Controls which pipeline runs. Set to `pull_request` to trigger the PR review pipeline, or `push` to trigger the onboarding documentation pipeline. |

In the GitHub Actions environment these variables are injected automatically from repository secrets and workflow context. You do not need to configure them in GitHub manually beyond setting `ANTHROPIC_API_KEY` as a repository secret.

## Running the Project Locally

With the virtual environment active and the `.env` file populated, run the entry point directly:

```
python src/main.py
```

The orchestrator in `src/main.py` reads the `EVENT_NAME` variable and routes execution accordingly. Setting `EVENT_NAME=pull_request` runs the full PR review pipeline: it gathers the diff, runs the security scan, quality review, and summary agents, then posts a combined comment to the pull request. Setting `EVENT_NAME=push` runs the onboarding pipeline: it checks whether `CONTRIBUTING.md` already exists in the repository and, if not, explores the codebase and generates and commits `CONTRIBUTING.md`, `ARCHITECTURE.md`, and `SETUP.md`.

## Branch Naming Conventions

Use the following prefixes when naming branches:

- `feature/short-description` for new functionality
- `fix/short-description` for bug fixes
- `docs/short-description` for documentation changes
- `refactor/short-description` for internal changes that do not affect external behavior
- `chore/short-description` for maintenance tasks such as dependency updates or CI changes

Use lowercase letters and separate words with hyphens within the description segment. Keep branch names concise and descriptive of the change being made.

## Opening a Pull Request

Before opening a pull request, ensure your branch is up to date with `main` and that the project runs without errors locally.

When opening a pull request:

1. Target the `main` branch as the base.
2. Write a clear title summarizing what the change does.
3. In the description, explain what problem the change addresses, what approach was taken, and any decisions that reviewers should be aware of.
4. Link any relevant issues using GitHub's closing keywords if applicable.
5. Request a review from at least one team member before merging.

Do not merge your own pull request without a review unless explicitly agreed upon for trivial fixes.

## What CodeGuard Checks on Every Pull Request

CodeGuard runs automatically on every pull request via GitHub Actions. It performs three independent analyses and posts the results as a single comment on the pull request.

**Security scan** checks for hardcoded secrets or credentials, injection vulnerabilities, unsafe use of `subprocess`, missing input validation, and insecure dependency additions.

**Code quality review** checks for overly complex functions, inconsistent naming, insufficient error handling, code duplication, lack of test coverage, and hardcoded configuration values that should be environment variables.

**PR summary** produces a plain-English description of what the pull request does, which parts of the codebase are affected, and any notable risks introduced.

All findings are posted as a single formatted comment under a CodeGuard Review heading. Address any flagged issues before requesting a human review.