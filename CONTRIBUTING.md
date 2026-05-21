# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent built on the Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories upon their first push.

## Prerequisites

Before setting up the project, ensure you have the following installed:

- Python 3.11
- Git
- A terminal with access to `python3` and `pip`
- A GitHub account with access to the target repository
- An Anthropic API key with access to Claude models

## Cloning and Setting Up the Project

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

You should see `(venv)` appear at the beginning of your shell prompt, confirming the environment is active.

## Installing Dependencies

With the virtual environment active, install all required packages:

```
pip install -r requirements.txt
```

This installs the five direct dependencies: `claude-agent-sdk`, `pygithub`, `python-dotenv`, `pyyaml`, and `tzdata`.

## Environment Variables

Create a `.env` file in the repository root. This file is excluded from version control and must never be committed. The following variables are required:

**ANTHROPIC_API_KEY**
Your Anthropic API key. CodeGuard uses this to authenticate all calls to Anthropic models, including `claude-sonnet-4-6` for deep analysis and `claude-haiku-4-5` for summarization.

**GITHUB_TOKEN**
A GitHub personal access token or Actions token with permissions to read pull request diffs, post comments, and commit files to the target repository.

**REPO_NAME**
The full name of the target repository in the format `owner/repository`. CodeGuard uses this to identify which repository to read from and write to via the GitHub API.

**EVENT_NAME**
The GitHub Actions event that triggered the run. Accepted values are `pull_request`, `push`, and `issue_comment`. CodeGuard uses this variable to determine which pipeline to execute at startup.

**PR_NUMBER**
The pull request number to review. This is required when `EVENT_NAME` is `pull_request`.

**COMMENT_BODY**
The full text of the issue comment that triggered the run. This is required when `EVENT_NAME` is `issue_comment` and CodeGuard needs to detect the `/onboard` command.

A minimal `.env` file for local pull request review testing looks like this:

```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
REPO_NAME=your-org/your-repo
EVENT_NAME=pull_request
PR_NUMBER=42
```

## Configuration

CodeGuard reads an optional `.codeguard.yml` file from the repository root to control which feature modules are enabled and what security severity threshold to apply. If this file is absent, all modules default to enabled and the severity threshold defaults to `low`. The available keys are:

```yaml
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

Valid values for `severity_threshold` are `low`, `medium`, and `high`.

## Running the Project Locally

With the virtual environment active and the `.env` file populated, run the entry point directly:

```
python src/main.py
```

CodeGuard reads `EVENT_NAME` from the environment on startup and routes execution to the appropriate pipeline. For a pull request review, it will fetch the diff for `PR_NUMBER` in `REPO_NAME`, invoke the security, quality, and summary agents, compose the results into a structured comment, and post it to the pull request. For a push event with no existing `CONTRIBUTING.md`, it will explore the codebase and generate onboarding documentation.

Generated runtime files (`codeguard_session.json` and `.codeguard_cache.json`) are written to the repository root after each run. Both files are excluded from version control.

## Branch Naming Conventions

All work should happen on a dedicated branch. Use the following naming patterns:

- `feature/<short-description>` for new functionality
- `fix/<short-description>` for bug fixes
- `docs/<short-description>` for documentation changes
- `refactor/<short-description>` for internal restructuring that does not change behavior
- `chore/<short-description>` for dependency updates, configuration changes, and other maintenance tasks

Branch names should use lowercase letters and hyphens only. Keep them concise and descriptive, for example `feature/cache-invalidation` or `fix/retry-on-rate-limit`.

## Opening a Pull Request

Before opening a pull request:

1. Confirm all changed modules are covered by a manual test or a documented rationale if automated testing is not yet in scope for that module.
2. Ensure your `.env` file is not staged or committed.
3. Run the project locally against a test repository to verify the pipeline completes without errors.
4. Write a clear pull request description that explains what changed, why it changed, and any trade-offs or risks you are aware of.

Open the pull request against the `main` branch. Mark it as a draft if it is not yet ready for review. Assign at least one reviewer before marking it ready.

## What CodeGuard Checks on Every Pull Request

When a pull request is opened or updated in any repository where CodeGuard is installed, the following checks run automatically:

**Security scan**
CodeGuard invokes a Claude agent with a focused security analysis prompt to identify vulnerabilities in the changed code. Findings are filtered by the configured severity threshold and reported as a structured FINDINGS block in the review comment.

**Code quality review**
A separate Claude agent reviews the diff for code quality issues including clarity, maintainability, error handling, and adherence to idiomatic patterns. Results are reported as a QUALITY NOTES block.

**Pull request summary**
A lighter Claude model produces a concise plain-English summary of the pull request's intent, affected areas, and any notable trade-offs. This appears at the top of the review comment to give reviewers immediate context.

All three outputs are composed into a single structured markdown comment posted directly to the pull request by the `post_results` module. The full agent session log, including prompt lengths, result lengths, and timestamps, is saved to `codeguard_session.json` for debugging and auditing purposes.