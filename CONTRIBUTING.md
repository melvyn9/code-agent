# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent built on the Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories upon their first push to the default branch.

## Prerequisites

Before setting up the project locally, ensure you have the following installed:

- Python 3.11
- pip (included with Python 3.11)
- git

You will also need:

- An Anthropic API key with access to the claude-sonnet-4-6 model
- A GitHub personal access token with repository read and write permissions

## Cloning and Setting Up the Project

Clone the repository to your local machine:

```
git clone https://github.com/<owner>/codeguard.git
cd codeguard
```

Once inside the project directory, create a virtual environment:

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

You should see the virtual environment name appear in your shell prompt. All subsequent commands assume the virtual environment is active.

## Installing Dependencies

With the virtual environment active, install the required dependencies:

```
pip install -r requirements.txt
```

This installs the following packages:

- `claude-agent-sdk` — the Anthropic Claude Agent SDK used to run all AI-driven pipeline steps
- `pygithub` — a Python client for the GitHub REST API
- `python-dotenv` — loads environment variables from the `.env` file at startup

## Environment Variables

CodeGuard reads its configuration from environment variables. For local development, these are loaded from a `.env` file in the project root. Create this file by copying the structure below and filling in your own values:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here
REPO_NAME=owner/repository-name
EVENT_NAME=pull_request
```

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API credential. Required for all Claude agent calls across every pipeline step. |
| `GITHUB_TOKEN` | A GitHub personal access token. Used to authenticate API requests, fetch pull request diffs, post comments, and commit generated files. |
| `REPO_NAME` | The target repository in `owner/name` format. Tells the GitHub client which repository to operate on. |
| `EVENT_NAME` | Simulates the GitHub Actions event type locally. Set to `pull_request` to run the PR review pipeline, or `push` to run the onboarding documentation pipeline. |

The `.env` file is present in the repository for convenience but must never be committed with real credentials. Treat it as a secret and ensure it remains listed in `.gitignore`.

In the GitHub Actions environment, these variables are injected automatically from repository secrets and GitHub Actions context variables. You do not need to configure them manually for CI runs.

## Running the Project Locally

With the virtual environment active and the `.env` file populated, run the entry point directly:

```
python src/main.py
```

The application reads `EVENT_NAME` to decide which pipeline to execute. If `EVENT_NAME` is set to `pull_request`, it runs the PR review pipeline, which fetches the diff for the pull request identified by `PR_NUMBER`, runs the security scan, quality review, and summary agents, and posts a combined comment to the PR. If `EVENT_NAME` is set to `push`, it checks whether a `CONTRIBUTING.md` file already exists in the repository and, if not, explores the codebase and generates one.

To simulate a PR review locally, also set `PR_NUMBER` in your `.env` file to the number of an open pull request in the target repository.

## Branch Naming Conventions

Use descriptive, lowercase branch names with words separated by forward slashes or underscores to indicate the type and scope of the change:

- `feature/short-description` for new functionality
- `fix/short-description` for bug fixes
- `docs/short-description` for documentation changes
- `refactor/short-description` for internal code restructuring with no behavior change
- `chore/short-description` for maintenance tasks such as dependency updates or configuration changes

Keep branch names concise and specific enough that the purpose is clear from the name alone.

## Opening a Pull Request

Before opening a pull request:

1. Ensure all changes are committed to a branch that follows the naming conventions above.
2. Confirm the project runs without errors locally against a test repository.
3. Make sure no secrets or real credentials are included in any committed file.

To open a pull request, push your branch to the remote repository and open a PR against the `main` branch through the GitHub interface. Provide a clear title and a description that explains what the change does, which files are affected, and any relevant context for the reviewer.

Tag a maintainer for review once the PR is open and all automated checks have completed.

## What CodeGuard Checks on Every Pull Request

CodeGuard runs automatically on every pull request via the GitHub Actions workflow defined in `.github/workflows/codeguard.yml`. It triggers on `opened`, `synchronize`, and `reopened` events and posts a single consolidated review comment to the PR containing three sections.

**Security scan.** A dedicated Claude agent reviews the diff for hardcoded secrets, SQL injection risks, command injection risks, unsafe use of `eval` or `exec`, missing input validation, insecure dependencies, and sensitive data exposure. Each finding is reported with a severity level.

**Quality review.** A separate Claude agent reviews the same diff for code quality concerns including excessive function complexity, inconsistent naming conventions, missing error handling, duplicated logic, absent tests, and hardcoded values that should be constants or configuration.

**PR summary.** A third Claude agent writes a concise plain-English summary of what the pull request does, which parts of the codebase are affected, and any notable risks or trade-offs introduced by the change.

All three outputs are combined into a single formatted markdown comment and posted to the pull request automatically. No manual triggering is required.