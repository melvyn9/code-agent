# Contributing to CodeGuard

CodeGuard is a GitHub integrated AI agent built on the Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories.

## Prerequisites

Before setting up the project, ensure you have the following installed and available:

- Python 3.11
- Git
- A GitHub account with access to the repository
- An Anthropic API key with access to claude-sonnet-4-6
- A GitHub personal access token with read and write permissions for repository contents and pull requests

## Cloning and Setting Up Locally

Clone the repository to your local machine:

```
git clone https://github.com/<your-org>/codeguard.git
cd codeguard
```

Create a virtual environment in the repository root:

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

With the virtual environment active, install all required dependencies from the requirements file:

```
pip install -r requirements.txt
```

This installs three direct dependencies: claude-agent-sdk (the Anthropic Claude Agent SDK providing the agent runtime), pygithub (the GitHub REST API wrapper), and python-dotenv (environment variable loading for local development).

## Environment Variables

CodeGuard requires the following environment variables at runtime. For local development, create a file named `.env` in the repository root. This file is excluded from version control via `.gitignore` and will be loaded automatically by python-dotenv when the application starts.

**ANTHROPIC_API_KEY**
Your Anthropic API key. This is passed to the Claude Agent SDK to authenticate all agent calls made by the security scan, quality review, summary, and documentation generation modules.

**GITHUB_TOKEN**
A GitHub personal access token. This is used by github_client.py to authenticate requests to the GitHub REST API, including fetching pull request diffs, posting review comments, and committing generated documentation files to the repository.

**REPO_NAME**
The full repository name in `owner/repository` format (for example, `myorg/myrepo`). This tells the GitHub client which repository to operate against.

**PR_NUMBER**
The pull request number to review. This is required when running the PR review pipeline. In GitHub Actions this is injected automatically by the workflow. For local testing, set it to the number of an open pull request in the target repository.

**EVENT_NAME**
Controls which execution path `src/main.py` takes. Accepted values are `pull_request` (runs the PR review pipeline), `push` (runs the onboarding pipeline when a new repository is detected), and `issue_comment` (retriggers onboarding when the `/onboard` command is posted in an issue).

A minimal `.env` file for local development looks like this:

```
ANTHROPIC_API_KEY=your_anthropic_api_key
GITHUB_TOKEN=your_github_token
REPO_NAME=your-org/your-repo
PR_NUMBER=42
EVENT_NAME=pull_request
```

## Running the Project Locally

With the virtual environment active and the `.env` file in place, invoke the entry point directly:

```
python src/main.py
```

The application reads `EVENT_NAME` and routes to the appropriate pipeline. To test the PR review pipeline, set `EVENT_NAME=pull_request` and provide a valid `PR_NUMBER`. To test the onboarding pipeline, set `EVENT_NAME=push` and ensure the target repository does not already contain a `CONTRIBUTING.md` in its root.

## Branch Naming Conventions

All work should be done on a dedicated branch rather than directly on `main`. Use the following naming patterns:

- `feature/short-description` for new functionality
- `fix/short-description` for bug fixes
- `docs/short-description` for documentation changes
- `refactor/short-description` for code restructuring without behavior changes

Branch names should be lowercase and use forward slashes to separate the type prefix from the description. Keep descriptions concise and descriptive enough to communicate intent without reading the full commit history.

## Opening a Pull Request

Before opening a pull request, ensure your branch is up to date with `main` and that the application runs without errors against a test repository.

When you open a pull request against `main`, the CodeGuard GitHub Actions workflow (`.github/workflows/codeguard.yml`) triggers automatically. The workflow provisions Python 3.11, installs dependencies, and runs `src/main.py` with all required environment variables injected from repository secrets.

In the pull request description, include a summary of what changed, why it was changed, and any modules or agent prompts that were modified. If you changed an agent prompt in any of the `src/` modules, note which agent was affected and describe how the output behavior may differ.

Pull requests require at least one approving review before merging. Squash merging is preferred to keep the `main` branch history linear.

## What CodeGuard Checks on Every Pull Request

When a pull request is opened, synchronized, or reopened, CodeGuard automatically performs the following checks and posts a single consolidated comment to the pull request:

**Security scan**
The security agent inspects the pull request diff for hardcoded secrets, injection vulnerabilities, unsafe subprocess usage, missing input validation, and insecure dependency additions. Findings are reported with file locations and descriptions.

**Code quality review**
The quality agent checks for overly complex functions, naming inconsistencies, missing error handling, duplicated logic, missing tests, and hardcoded values that should be configurable.

**Pull request summary**
The summary agent produces a plain-English paragraph describing the intent of the pull request, the parts of the codebase affected, and any notable risks introduced by the changes.

All three agents run in parallel via `asyncio.gather` and their outputs are composed into a single formatted markdown comment posted to the pull request by `src/post_results.py`. No human intervention is required to trigger these checks.