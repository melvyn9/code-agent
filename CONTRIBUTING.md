# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent that automatically reviews pull requests for security vulnerabilities and code quality issues. It also generates onboarding documentation for new repositories and posts all findings as structured comments directly on pull requests.

## Prerequisites

You will need the following before setting up the project locally.

**Python 3.11**
CodeGuard is written entirely in Python 3.11. Earlier versions are not supported. Verify your version with:

    python --version

**Git**
Standard Git installation is required to clone the repository and manage branches.

**A GitHub personal access token**
The token must have `repo` scope so the application can read pull request diffs and post comments.

**An Anthropic API key**
CodeGuard uses the Claude Agent SDK to run all AI review and documentation tasks. You can obtain an API key from the Anthropic console.

## Cloning and Setting Up the Project Locally

Clone the repository and move into the project directory:

    git clone https://github.com/your-org/codeguard.git
    cd codeguard

Create a virtual environment inside the project directory:

    python -m venv venv

## Activating the Virtual Environment

On macOS and Linux:

    source venv/bin/activate

On Windows:

    venv\Scripts\activate

Your shell prompt will update to show `(venv)` when the environment is active. All subsequent commands assume the virtual environment is active.

## Installing Dependencies

With the virtual environment active, install the three required packages:

    pip install -r requirements.txt

This installs `claude-agent-sdk` (the Anthropic Claude Agent SDK), `pygithub` (the GitHub REST API wrapper), and `python-dotenv` (local environment variable loading).

## Required Environment Variables

CodeGuard reads all configuration from environment variables. In GitHub Actions these are injected automatically from repository secrets. For local development, create a `.env` file in the project root with the following variables.

**ANTHROPIC_API_KEY**
Your Anthropic API key. This authenticates all calls to the Claude Agent SDK that power the security scan, quality review, summarization, codebase exploration, and documentation generation agents.

**GITHUB_TOKEN**
A GitHub personal access token with `repo` scope. This authenticates all GitHub API calls made through PyGithub, including reading pull request diffs, listing changed files, posting review comments, and committing generated documentation files.

**REPO_NAME**
The full repository name in `owner/repository` format, for example `your-org/codeguard`. This tells the GitHub client which repository to operate against.

**PR_NUMBER**
The pull request number to review, for example `42`. This is used by the PR review pipeline to fetch the correct diff and post the comment on the correct pull request. Leave this unset or empty when testing the onboarding pipeline on a push event.

**EVENT_NAME**
Controls which pipeline `src/main.py` executes. Set this to `pull_request` to run the full PR review pipeline (security scan, quality review, summary, and comment). Set it to `push` to run the onboarding pipeline (codebase exploration and documentation generation). Set it to `issue_comment` to simulate the manual `/onboard` comment trigger.

A minimal `.env` file for local PR review testing looks like this:

    ANTHROPIC_API_KEY=sk-ant-...
    GITHUB_TOKEN=ghp_...
    REPO_NAME=your-org/codeguard
    PR_NUMBER=5
    EVENT_NAME=pull_request

## Running the Project Locally

With the virtual environment active and the `.env` file populated, run the entry point:

    python src/main.py

The application reads `EVENT_NAME` and dispatches to the appropriate pipeline. For `pull_request`, it fetches the diff, runs three AI review agents in sequence, and posts a structured comment on the specified pull request. For `push`, it checks whether `CONTRIBUTING.md` already exists in the repository and, if not, explores the codebase and commits `CONTRIBUTING.md`, `ARCHITECTURE.md`, and `SETUP.md` to the repository root.

## Branch Naming Conventions

Use the following prefixes to keep branch history readable.

`feature/short-description` for new capabilities, for example `feature/add-license-scan`.

`fix/short-description` for bug fixes, for example `fix/post-comment-encoding`.

`docs/short-description` for documentation changes only, for example `docs/update-setup-guide`.

`chore/short-description` for maintenance tasks that do not affect application behavior, for example `chore/update-dependencies`.

Branch names should be lowercase with words separated by hyphens. Do not push directly to `main`.

## Opening a Pull Request

1. Create a branch following the naming conventions above.
2. Make your changes and commit them with a clear, imperative commit message.
3. Push the branch to the remote repository.
4. Open a pull request against `main` through the GitHub web interface or the GitHub CLI.
5. Write a description that explains what the change does and why it is needed.
6. CodeGuard will automatically run on the pull request once it is opened or updated. Wait for the CodeGuard review comment to appear before requesting a human reviewer.

Pull requests that introduce new agent modules should include the corresponding entry in `src/main.py` so the routing layer can reach them. Pull requests that change environment variable requirements should update the `.env` documentation in this file.

## What CodeGuard Checks on Every Pull Request

When a pull request is opened, synchronized, or reopened, the GitHub Actions workflow triggers `src/main.py` with `EVENT_NAME` set to `pull_request`. CodeGuard performs three automated checks and posts the results as a single structured comment on the pull request.

**Security scan**
The security agent reviews the pull request diff for hardcoded secrets and credentials, injection vulnerabilities, unsafe use of `eval` or `exec`, missing input validation, insecure or unpinned dependencies, and unintended exposure of sensitive data. Results appear under the FINDINGS section of the review comment.

**Quality review**
The quality agent reviews the diff for overly complex or deeply nested functions, inconsistent naming conventions, weak or missing error handling, duplicated logic, absent test coverage, and hardcoded values that should be configuration. Results appear under the QUALITY NOTES section of the review comment.

**Plain-English summary**
The summarization agent produces a concise description of what the pull request does, which parts of the codebase it affects, and any notable risks or trade-offs introduced by the change. This appears at the top of the review comment under the SUMMARY section.

All three outputs are assembled by `src/post_results.py` and posted as a single comment attributed to CodeGuard. The comment is updated on each new push to the branch.