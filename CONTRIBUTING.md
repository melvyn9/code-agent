# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent built on the Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories by analyzing their codebase structure.

## Prerequisites

Before setting up the project, ensure you have the following installed:

- Python 3.11
- Git
- A GitHub account with access to the repository
- An Anthropic API key with access to the Claude API

## Cloning and Setting Up the Project

Clone the repository to your local machine:

```
git clone https://github.com/YOUR_ORG/codeguard.git
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

With the virtual environment active, install the project dependencies from `requirements.txt`:

```
pip install -r requirements.txt
```

This installs the three direct dependencies: `claude-agent-sdk`, `pygithub`, and `python-dotenv`.

## Environment Variables

Create a `.env` file in the project root. This file is excluded from version control and is used only for local development. Do not commit it.

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here
REPO_NAME=owner/repository-name
EVENT_NAME=pull_request
PR_NUMBER=123
COMMENT_BODY=/onboard
```

| Variable | Description |
| --- | --- |
| `ANTHROPIC_API_KEY` | Your Anthropic API key. Used by the Claude Agent SDK to authenticate all sub-agent calls. |
| `GITHUB_TOKEN` | A GitHub personal access token with `repo` scope. Used by PyGithub to fetch PR diffs, post comments, and commit generated files. |
| `REPO_NAME` | The full repository identifier in `owner/repo` format. Tells the GitHub client which repository to operate on. |
| `EVENT_NAME` | The GitHub event type that triggered execution. Accepted values are `pull_request`, `push`, and `issue_comment`. Controls which pipeline `src/main.py` routes to. |
| `PR_NUMBER` | The pull request number to review. Required when `EVENT_NAME` is `pull_request`. |
| `COMMENT_BODY` | The body of an issue comment. Required when `EVENT_NAME` is `issue_comment`. Set to `/onboard` to trigger the onboarding documentation pipeline locally. |

## Running the Project Locally

With the virtual environment active and your `.env` file populated, run the entry point directly:

```
python src/main.py
```

`src/main.py` reads the `EVENT_NAME` variable and routes execution to one of two pipelines:

- If `EVENT_NAME` is `pull_request`, it runs the PR review pipeline, which gathers diff context, runs security and quality sub-agents, and posts a combined markdown comment to the pull request.
- If `EVENT_NAME` is `push` or `issue_comment` (with `COMMENT_BODY` set to `/onboard`), it runs the onboarding pipeline, which explores the repository structure and commits generated documentation files.

## Branch Naming Conventions

Use the following prefixes when naming branches:

| Prefix | Use case |
| --- | --- |
| `feat/` | New features or capabilities |
| `fix/` | Bug fixes |
| `docs/` | Documentation changes only |
| `refactor/` | Code restructuring with no behavior change |
| `chore/` | Dependency updates, tooling, and maintenance |

Branch names should be lowercase and use forward slashes as the only separator. Use short descriptive names after the prefix, for example `feat/add-quality-scoring` or `fix/pr-comment-formatting`.

## Opening a Pull Request

1. Create a branch from `main` following the naming conventions above.
2. Make your changes, commit them with clear and descriptive commit messages written in the imperative mood.
3. Push your branch and open a pull request against `main`.
4. Fill out the pull request description explaining what the change does, why it is needed, and how it was tested.
5. Request a review from at least one maintainer before merging.

Keep pull requests focused on a single concern. If you are making unrelated changes, open separate pull requests.

## What CodeGuard Checks on Every Pull Request

CodeGuard runs automatically on every pull request via the GitHub Actions workflow defined in `.github/workflows/codeguard.yml`. It posts a single formatted markdown comment to the PR with the output of three sub-agent checks:

**Security scan** reviews the diff for hardcoded secrets, injection vulnerabilities, unsafe use of `eval`, missing input validation, and insecure dependencies.

**Code quality review** reviews the diff for excessive complexity, naming convention violations, insufficient error handling, code duplication, inadequate test coverage, missing or misleading comments, and hardcoded values that should be configurable.

**PR summary** produces a concise plain-English description of what the pull request does, which parts of the codebase it affects, and any notable risks introduced by the change.

No action is required to trigger these checks. They run automatically when a pull request is opened, updated, or reopened.