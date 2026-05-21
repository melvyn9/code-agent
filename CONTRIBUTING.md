# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories. It is triggered by GitHub Actions and posts its results directly back to GitHub as pull request comments or committed files.

## Prerequisites

Before setting up the project locally, ensure you have the following installed:

- Python 3.11
- Git
- A terminal with access to `python3` and `pip`
- A GitHub account with a personal access token that has repository read and write permissions
- An Anthropic API key with access to the Claude models

## Cloning and Setting Up the Project

Clone the repository to your local machine:

```
git clone https://github.com/your-org/codeguard.git
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

You should see `(venv)` appear at the start of your terminal prompt confirming the environment is active.

## Installing Dependencies

With the virtual environment active, install all required packages:

```
pip install -r requirements.txt
```

This installs the three direct dependencies: `claude-agent-sdk`, `pygithub`, and `python-dotenv`.

## Environment Variables

Create a file named `.env` in the root of the project. This file is used during local development and testing to provide secrets and runtime configuration without hardcoding them. The `.env` file is not committed to version control.

Populate it with the following variables:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here
REPO_NAME=owner/repository-name
EVENT_NAME=pull_request
PR_NUMBER=1
COMMENT_BODY=
```

Variable descriptions:

**ANTHROPIC_API_KEY** authenticates all Claude Agent SDK queries made by the review and documentation generation agents. This key is required for every pipeline run.

**GITHUB_TOKEN** authenticates all GitHub REST API calls made through PyGithub, including reading pull request diffs, posting comments, and committing generated files to a repository.

**REPO_NAME** specifies the target GitHub repository in `owner/repo` format. This tells the agent which repository to read from and write results to.

**EVENT_NAME** controls which pipeline the entry point routes to. Set it to `pull_request` to trigger the PR review pipeline or `push` to trigger the onboarding documentation pipeline.

**PR_NUMBER** identifies which pull request to review. This is only required when `EVENT_NAME` is set to `pull_request`.

**COMMENT_BODY** carries the text of an issue comment when simulating a comment-triggered run. Leave it empty unless you are testing comment-based command routing.

## Running the Project Locally

With the virtual environment active and the `.env` file populated, run the entry point directly:

```
python src/main.py
```

The entry point reads `EVENT_NAME` and routes execution to either the PR review pipeline or the onboarding documentation pipeline. Results are posted back to the GitHub repository specified in `REPO_NAME`.

To test the PR review pipeline, set `EVENT_NAME=pull_request` and provide a valid `PR_NUMBER`. To test the onboarding pipeline, set `EVENT_NAME=push` and point `REPO_NAME` at a repository that does not yet contain a `CONTRIBUTING.md` file in its root.

## Branch Naming Conventions

Use the following prefixes when naming branches:

- `feature/short-description` for new features or capabilities
- `fix/short-description` for bug fixes
- `docs/short-description` for documentation changes
- `refactor/short-description` for code restructuring that does not change behavior
- `test/short-description` for adding or updating tests

Keep branch names lowercase and use hyphens to separate words within the description segment. Branch names should be concise and descriptive enough that the purpose is clear without reading the commit history.

## Opening a Pull Request

Before opening a pull request, ensure your branch is up to date with `main` and that the application runs without errors locally.

Push your branch to the remote repository and open a pull request against `main` through the GitHub web interface or the GitHub CLI. In the pull request description, include a summary of what changed and why, any environment variable additions or changes, and the steps you used to test your changes locally.

Pull requests require at least one approval before merging. Keep pull requests focused on a single concern. If your change touches multiple unrelated areas, split it into separate pull requests.

## What CodeGuard Checks on Every Pull Request

When you open or update a pull request, the CodeGuard GitHub Actions workflow runs automatically and posts a structured comment with the following three sections.

**Security scan** checks for hardcoded secrets and credentials, injection vulnerabilities, unsafe use of `eval` or `exec`, missing input validation, insecure dependency usage, and logging of sensitive data.

**Code quality review** checks for overly complex functions, naming inconsistencies, weak or missing error handling, duplicated logic, missing test coverage, and hardcoded values that should be configurable.

**Pull request summary** produces a plain-English summary of two to five sentences covering the intent of the changes, the areas of the codebase affected, and any notable risks introduced.

These checks are informational. They are posted as a comment by the CodeGuard bot and do not block merging, but reviewers are expected to address any flagged issues before approval.