# Contributing to CodeGuard

CodeGuard is a GitHub-integrated AI agent built on the Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for new repositories when they receive their first push.

## Prerequisites

Before setting up the project, ensure you have the following installed on your machine.

**Python 3.11**
CodeGuard requires Python 3.11 specifically. You can check your version by running:

    python3 --version

If you need to install or switch to Python 3.11, use your system package manager or a version manager such as pyenv.

**Git**
Git must be installed to clone the repository and manage branches.

**A GitHub account**
You will need a GitHub account with access to the repository you intend to work on.

**API credentials**
You will need an Anthropic API key and a GitHub personal access token before you can run the project locally. See the Environment Variables section below for details.

## Cloning and Setting Up the Project Locally

Clone the repository to your local machine:

    git clone https://github.com/your-org/codeguard.git
    cd codeguard

Once inside the project directory, create a Python virtual environment:

    python3.11 -m venv venv

## Activating the Virtual Environment

On macOS and Linux:

    source venv/bin/activate

On Windows:

    venv\Scripts\activate

Your terminal prompt should change to indicate the virtual environment is active. You must activate the virtual environment before installing dependencies or running the project.

## Installing Dependencies

With the virtual environment active, install all required dependencies from the requirements file:

    pip install -r requirements.txt

This installs the following three packages:

- **claude-agent-sdk** — the Anthropic Claude Agent SDK used to run all AI agent pipelines throughout the project
- **pygithub** — a Python wrapper around the GitHub REST API used to fetch PR diffs, list changed files, post comments, and commit files
- **python-dotenv** — loads environment variables from a local .env file so the project can run outside of GitHub Actions

## Environment Variables

CodeGuard relies on environment variables for secrets and runtime configuration. When running locally, these are loaded from a .env file in the project root. This file is gitignored and must never be committed.

Create a .env file in the project root with the following contents:

    ANTHROPIC_API_KEY=your_anthropic_api_key_here
    GITHUB_TOKEN=your_github_personal_access_token_here
    REPO_NAME=owner/repository-name
    PR_NUMBER=123
    EVENT_NAME=pull_request

**ANTHROPIC_API_KEY**
Your Anthropic API key. This authenticates all requests made to Claude via the Claude Agent SDK. Obtain one from the Anthropic console at console.anthropic.com.

**GITHUB_TOKEN**
A GitHub personal access token with repo scope. This allows CodeGuard to read PR diffs, list changed files, post comments, and commit generated documentation files to repositories.

**REPO_NAME**
The full repository name in owner/repo format (for example, acme-corp/codeguard). This tells the GitHub client which repository to operate on.

**PR_NUMBER**
The pull request number to review. This is only required when running the PR review pipeline. Set it to any open PR number in the target repository.

**EVENT_NAME**
Controls which pipeline runs. Set this to pull_request to trigger the PR review pipeline, or push to trigger the onboarding documentation pipeline.

In GitHub Actions, all of these variables are injected automatically from repository secrets and the workflow context. You do not need to configure them manually for CI runs.

## Running the Project Locally

With the virtual environment active and your .env file configured, run the project with:

    python src/main.py

The orchestrator reads EVENT_NAME and routes to the appropriate pipeline. If EVENT_NAME is pull_request, it will gather context from the specified PR, run the security scan, quality review, and summary agents, and post a structured comment to the PR. If EVENT_NAME is push, it will check whether onboarding documentation already exists in the target repository and generate CONTRIBUTING.md and ARCHITECTURE.md if it does not.

## Branch Naming Conventions

All work should be done on a dedicated branch. Use the following naming patterns:

    feature/short-description
    fix/short-description
    docs/short-description
    refactor/short-description

Branch names should be lowercase and use forward slashes to separate the type prefix from the description. Use short and descriptive names that communicate what the branch does. For example:

    feature/add-complexity-threshold
    fix/pr-comment-formatting
    docs/update-architecture

Do not commit directly to the main branch.

## Opening a Pull Request

Before opening a pull request, ensure the following:

1. Your branch is up to date with main.
2. Your code runs locally without errors.
3. You have not committed the .env file or any secrets.
4. Your changes are scoped to a single concern.

To open a pull request, push your branch to the remote repository and open a PR against the main branch through the GitHub UI or CLI. Write a clear title and description explaining what the PR does and why. Reference any related issues in the description.

## What CodeGuard Checks on Every Pull Request

When you open a pull request against this repository, CodeGuard will automatically run three review agents on your diff and post a single structured comment with their combined findings.

**Security scan**
The security agent analyzes your changes for hardcoded secrets, injection vulnerabilities, unsafe use of eval or exec, and insecure dependencies.

**Code quality review**
The quality agent analyzes your changes for excessive complexity, naming inconsistencies, missing error handling, duplicated logic, and absent tests.

**PR summary**
The summary agent produces a plain-English summary of two to five sentences describing what the PR does, which parts of the codebase it affects, and any notable risks.

These checks run automatically on every pull request event including when a PR is opened, updated with new commits, or reopened. They are informational and do not block merging, but reviewers will consider their findings during code review.