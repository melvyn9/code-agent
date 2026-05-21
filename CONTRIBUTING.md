# Contributing to CodeGuard

CodeGuard is a GitHub integrated AI agent built on the Anthropic Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories upon first push.

## Prerequisites

Before setting up CodeGuard locally, ensure you have the following installed:

- Python 3.11
- Git
- pip (bundled with Python 3.11)
- A GitHub account with access to the repository
- An Anthropic API key with access to the Claude claude-sonnet-4-6 model

## Cloning and Setting Up the Project

Clone the repository to your local machine:

```
git clone https://github.com/your-org/codeguard.git
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

Your terminal prompt will change to indicate the virtual environment is active. All subsequent commands assume the virtual environment is activated.

## Installing Dependencies

With the virtual environment active, install all required dependencies:

```
pip install -r requirements.txt
```

This installs the three direct dependencies: `claude-agent-sdk`, `pygithub`, and `python-dotenv`.

## Environment Variables

CodeGuard reads its configuration entirely from environment variables. For local development, create a `.env` file in the repository root. This file is excluded from version control via `.gitignore` and must never be committed.

Create the file with the following contents, substituting real values:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here
REPO_NAME=owner/repository-name
PR_NUMBER=123
EVENT_NAME=pull_request
```

Variable reference:

**ANTHROPIC_API_KEY** authenticates requests to the Anthropic API. All Claude agent calls in `src/security_scan.py`, `src/quality_review.py`, `src/summarize_pr.py`, `src/explore_codebase.py`, `src/gen_contributing.py`, `src/gen_architecture.py`, and `src/gen_setup_guide.py` require this key.

**GITHUB_TOKEN** authenticates requests to the GitHub REST API via PyGithub. It is used to fetch PR diffs, list changed files, post review comments, and commit generated documentation files to the repository.

**REPO_NAME** identifies the target repository in `owner/repository` format. This tells the GitHub client which repository to operate on.

**PR_NUMBER** specifies which pull request to review. This is only required when running the PR review pipeline locally.

**EVENT_NAME** controls which pipeline `src/main.py` executes. Set it to `pull_request` to run the PR review pipeline, `push` to run the onboarding documentation pipeline, or `issue_comment` to trigger a manual onboarding run.

## Running the Project Locally

With the virtual environment active and the `.env` file in place, run the entry point directly:

```
python src/main.py
```

The application reads `EVENT_NAME` and dispatches to the appropriate pipeline. For a PR review, ensure `PR_NUMBER` and `REPO_NAME` are set correctly. For an onboarding run, set `EVENT_NAME=push` and `REPO_NAME` to a repository that does not yet have a `CONTRIBUTING.md` in its root.

## Branch Naming Conventions

Branch names should follow this pattern:

```
type/short-description
```

Accepted types are `feat` for new features, `fix` for bug fixes, `docs` for documentation changes, `refactor` for code restructuring without behavior changes, and `chore` for maintenance tasks such as dependency updates or CI configuration changes.

Examples:

```
feat/parallel-doc-generation
fix/post-results-encoding
docs/update-architecture-overview
refactor/github-client-error-handling
```

Branch names should be lowercase, use only hyphens as word separators, and be concise enough to understand at a glance. Never commit directly to `main`.

## Opening a Pull Request

Before opening a pull request, ensure your branch is up to date with `main`:

```
git fetch origin
git rebase origin/main
```

Push your branch to the remote:

```
git push origin your-branch-name
```

Open a pull request against `main` through the GitHub web interface. The pull request title should use the same type prefix as the branch name, written in sentence case. For example: `Feat: add parallel doc generation using asyncio.gather`.

In the pull request description, include a summary of what the change does, which modules it touches, and any notable risks or tradeoffs. If the change affects agent behavior, note the model and prompt modifications made. Link any related issues using the `Closes #issue-number` syntax so they are automatically closed on merge.

Request at least one review from a project maintainer before merging.

## What CodeGuard Checks on Every Pull Request

When a pull request is opened or updated, the GitHub Actions workflow defined in `.github/workflows/codeguard.yml` triggers CodeGuard automatically. The following checks run on every pull request:

**PR Summary** collects the diff and changed file list, then produces a plain English 2 to 5 sentence description of what the pull request does, which parts of the codebase it affects, and any notable risks. This is posted as the opening section of the automated review comment.

**Security Scan** analyzes the diff for hardcoded secrets, injection vulnerabilities, unsafe use of `eval`, missing input validation, and insecure dependency additions. Findings are categorized by severity and included in the review comment.

**Quality Review** evaluates the changed code for excessive complexity, poor naming, insufficient error handling, duplicated logic, missing test coverage, undocumented public interfaces, and misconfiguration risks. Notes are included in the review comment alongside the security findings.

All three outputs are composed into a single formatted markdown comment posted directly to the pull request by `src/post_results.py`. No external services beyond the Anthropic API and GitHub API are involved.