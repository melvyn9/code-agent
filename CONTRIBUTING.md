# Contributing to CodeGuard

CodeGuard is a GitHub integrated AI agent that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories upon their first push.

## Prerequisites

Before setting up the project locally, ensure you have the following installed:

- Python 3.11
- Git
- A text editor or IDE of your choice
- A GitHub account with access to the repository
- An Anthropic API key with access to Claude models

## Cloning and Setting Up the Project

Clone the repository to your local machine:

```
git clone https://github.com/<your-org>/codeguard.git
cd codeguard
```

Once inside the project directory, create a virtual environment using the Python 3.11 interpreter:

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

Your terminal prompt should now reflect the active environment. All subsequent commands assume the virtual environment is active.

## Installing Dependencies

With the virtual environment active, install all required dependencies from the requirements file:

```
pip install -r requirements.txt
```

This installs the following direct dependencies:

- `claude-agent-sdk` for AI agent orchestration and async streaming calls to Anthropic models
- `pygithub` for interacting with the GitHub REST API
- `python-dotenv` for loading environment variables from a `.env` file
- `pyyaml` for parsing the `.codeguard.yml` configuration file
- `tzdata` for IANA timezone support on Windows

## Environment Variables

Create a `.env` file in the repository root. This file is excluded from version control and must never be committed. Populate it with the following variables:

```
ANTHROPIC_API_KEY=
GITHUB_TOKEN=
REPO_NAME=
EVENT_NAME=
PR_NUMBER=
COMMENT_BODY=
```

**ANTHROPIC_API_KEY** is your Anthropic API key. It authenticates all calls to Claude models, including `claude-sonnet-4-6` for deep analysis and `claude-haiku-4-5` for summarization.

**GITHUB_TOKEN** is a GitHub personal access token or Actions token. It authorizes CodeGuard to read pull request diffs, list changed files, post review comments, and commit generated documentation files to the target repository.

**REPO_NAME** is the full name of the target GitHub repository in `owner/repo` format. CodeGuard uses this to locate the correct repository when making GitHub API calls.

**EVENT_NAME** controls which pipeline CodeGuard executes on startup. Set it to `pull_request` to trigger the PR review pipeline, `push` to trigger the onboarding pipeline, or leave it as the raw value passed by the GitHub Actions runner.

**PR_NUMBER** is the number of the pull request to review. This is only required when `EVENT_NAME` is `pull_request`.

**COMMENT_BODY** is the body text of an issue comment. This is only required when CodeGuard is triggered by a comment containing `/onboard`, which initiates a manual onboarding run.

## Running the Project Locally

With the virtual environment active and the `.env` file populated, start CodeGuard by running the entry point directly:

```
python src/main.py
```

CodeGuard will read `EVENT_NAME` from the environment, load configuration from `.codeguard.yml` if it exists in the working directory, and execute the appropriate pipeline. Runtime artifacts written during the session include `codeguard_session.json` (a timestamped log of all agent invocations) and `.codeguard_cache.json` (a cache of the repository structure hash and codebase summary). Both files are excluded from version control.

To customize which features run, edit `.codeguard.yml` in the repository root. The file controls whether the security scan, quality review, PR summary, and onboarding documentation features are enabled, and sets the minimum severity threshold for security findings:

```
security:
  enabled: true
  severity_threshold: medium
quality:
  enabled: true
summary:
  enabled: true
onboarding:
  enabled: true
```

## Branch Naming Conventions

Use the following prefixes when naming branches:

- `feature/` for new functionality (example: `feature/add-severity-filter`)
- `fix/` for bug fixes (example: `fix/retry-logic-on-comment-post`)
- `docs/` for documentation changes (example: `docs/update-contributing`)
- `refactor/` for internal changes that do not affect behavior
- `chore/` for maintenance tasks such as dependency updates or CI changes

Branch names should be lowercase and use hyphens to separate words. Keep names concise and descriptive of the change being made.

## Opening a Pull Request

Before opening a pull request, ensure your branch is up to date with `main` and that your changes do not break the existing entry point behavior. Then push your branch and open a pull request against `main` on GitHub.

Your pull request description should include the following:

- A plain English summary of what changed and why
- Any environment variable additions or changes required
- Notes on manual testing steps performed

Assign at least one reviewer before marking the pull request ready for review. Draft pull requests are acceptable for early feedback but should be converted to ready before final review.

## What CodeGuard Checks on Every Pull Request

When a pull request is opened or updated against a CodeGuard enabled repository, the agent automatically performs the following checks and posts a single structured comment to the pull request:

**Security scan** analyzes the diff for vulnerabilities such as hardcoded secrets, unsafe deserialization, injection risks, and insecure dependencies. Findings are filtered by the configured severity threshold and reported in a structured FINDINGS block.

**Quality review** evaluates the changed code for issues including excessive complexity, missing error handling, unclear naming, and violations of established patterns in the codebase. Results are reported in a structured QUALITY NOTES block.

**Pull request summary** produces a concise plain English description of the intent of the changes, the files and areas affected, and any notable trade-offs observed in the diff.

All three outputs are composed into a single comment posted to the pull request by CodeGuard. No separate status checks or annotations are created. The full session log for each run is written to `codeguard_session.json` in the repository root of the runner environment.