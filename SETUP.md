# CodeGuard Setup Guide

## Prerequisites

The following tools must be installed before proceeding. Exact versions are required to match the runtime environment used in GitHub Actions.

**Python 3.11**
CodeGuard uses 3.11 specific standard library features including `zoneinfo`. Do not use 3.10 or earlier. Verify your version with:

    python --version

**pip**
Comes bundled with Python 3.11. Verify with:

    pip --version

**Git**
Any recent version. Needed to clone the repository and to test against real pull requests.

**A GitHub account with repository access**
You will need a personal access token with `repo` scope to interact with the GitHub API locally.

**An Anthropic API key**
Obtain one from the Anthropic console at console.anthropic.com. The key must have access to claude-sonnet-4-6 and claude-haiku-4-5.

---

## Local Setup Instructions

### 1. Clone the Repository

    git clone https://github.com/YOUR_ORG/codeguard.git
    cd codeguard

### 2. Create a Virtual Environment

    python3.11 -m venv .venv

Activate it:

On macOS and Linux:

    source .venv/bin/activate

On Windows:

    .venv\Scripts\activate

Your terminal prompt should now show the `.venv` prefix. All subsequent commands assume the virtual environment is active.

### 3. Install Dependencies

    pip install -r requirements.txt

This installs the five direct runtime dependencies: the Claude Agent SDK, PyGitHub, python-dotenv, PyYAML, and tzdata.

### 4. Verify the Installation

    python -c "import anthropic; import github; import dotenv; import yaml; import tzdata; print('All dependencies loaded successfully')"

If any import fails, confirm you are inside the virtual environment and that `pip install` completed without errors.

---

## Creating and Populating the .env File

Create a file named `.env` at the root of the repository. This file is excluded from version control by `.gitignore` and must never be committed.

    touch .env

Open the file in your editor and populate it with the following variables:

    ANTHROPIC_API_KEY=your_anthropic_api_key_here

    GITHUB_TOKEN=your_github_personal_access_token_here

    GITHUB_REPOSITORY=owner/repository-name

    EVENT_NAME=pull_request

    PR_NUMBER=123

    GITHUB_SHA=the_full_commit_sha_you_want_to_test_against

**Variable reference:**

`ANTHROPIC_API_KEY`
Your secret key from the Anthropic console. Required for every agent call. Keep this value private.

`GITHUB_TOKEN`
A GitHub personal access token with `repo` scope. In GitHub Actions this is supplied automatically as `secrets.GITHUB_TOKEN`. Locally you must supply your own.

`GITHUB_REPOSITORY`
The full `owner/repo` identifier, for example `acme/backend-service`. Used by PyGitHub to resolve the repository object.

`EVENT_NAME`
Controls which pipeline runs. Set to `pull_request` for the PR review pipeline, `push` for the onboarding pipeline, or `issue_comment` for the manual `/onboard` command pipeline.

`PR_NUMBER`
The integer number of the pull request to review. Only required when `EVENT_NAME` is `pull_request` or `issue_comment`. Leave it out or set it to an empty string for push events.

`GITHUB_SHA`
The full SHA of the commit associated with the event. Required for the onboarding pipeline to correctly reference the tree being analyzed.

---

## Running the Project Locally

All execution goes through the single entry point `src/main.py`. The pipeline that runs is determined entirely by the `EVENT_NAME` variable in your `.env` file.

### Running the PR Review Pipeline

Set `EVENT_NAME=pull_request` and supply a valid `PR_NUMBER` in your `.env` file, then run:

    python src/main.py

This will:

1. Fetch the PR diff and changed file list from GitHub via `gather_context.py`
2. Run the security scan agent (claude-sonnet-4-6) via `security_scan.py`
3. Run the code quality review agent (claude-sonnet-4-6) via `quality_review.py`
4. Run the PR summary agent (claude-haiku-4-5) via `summarize_pr.py`
5. Assemble all three outputs and post a formatted markdown comment to the PR via `post_results.py`
6. Save session metadata to `codeguard_session.json`

### Running the Onboarding Pipeline

Set `EVENT_NAME=push` in your `.env` file. Remove or clear `PR_NUMBER`. Then run:

    python src/main.py

This will:

1. Check whether `CONTRIBUTING.md` already exists in the repository via `detect_new_repo.py`. If it does, the pipeline exits early.
2. Explore the codebase structure using a claude-sonnet-4-6 agent with file system tools via `explore_codebase.py`. Results are cached in `.codeguard_cache.json`.
3. Generate `CONTRIBUTING.md`, `ARCHITECTURE.md`, and `SETUP.md` in parallel using three focused claude-sonnet-4-6 agents.
4. Commit all three files to the repository via the GitHub API.
5. Save session metadata to `codeguard_session.json`.

---

## Running Against a Real Pull Request for Testing

To test the full review pipeline against an actual open pull request:

### Step 1: Identify a Target PR

Find an open pull request in a repository your `GITHUB_TOKEN` has access to. Note the repository full name and the PR number.

### Step 2: Update Your .env File

    GITHUB_REPOSITORY=owner/repo-name
    EVENT_NAME=pull_request
    PR_NUMBER=42

Set `PR_NUMBER` to the number of the pull request you want to review.

### Step 3: Run the Entry Point

    python src/main.py

The agent will post a real comment to that pull request. Use a test or sandbox repository to avoid posting unwanted comments to a production PR.

### Step 4: Inspect the Session Log

After the run completes, open `codeguard_session.json` in the project root. This file records every agent invocation with its name, prompt length, result length, a 300-character preview, and a Pacific time timestamp. This is the primary debugging artifact for understanding what each agent received and produced.

### Step 5: Verify the Comment on GitHub

Navigate to the pull request on GitHub. The CodeGuard comment should appear with three sections: a security scan report, a quality review, and a plain-English PR summary.

---

## Common Setup Mistakes and How to Fix Them

**Wrong Python version**

Symptom: `ModuleNotFoundError: No module named 'zoneinfo'` or similar errors involving the standard library.

Fix: Confirm that `python --version` reports `3.11.x`. If your system default is an older version, specify the interpreter explicitly when creating the virtual environment:

    python3.11 -m venv .venv

**Virtual environment not activated**

Symptom: `ModuleNotFoundError: No module named 'anthropic'` even after running `pip install`.

Fix: The packages were installed into a virtual environment that is not currently active. Run `source .venv/bin/activate` (macOS and Linux) or `.venv\Scripts\activate` (Windows) and try again.

**Incorrect GITHUB_TOKEN scope**

Symptom: PyGitHub raises a `401 Unauthorized` or `403 Forbidden` error when the script attempts to fetch PR data or post a comment.

Fix: Regenerate your personal access token in GitHub Settings under Developer settings and ensure the `repo` scope is checked. Tokens scoped only to `public_repo` will fail on private repositories.

**EVENT_NAME not set or misspelled**

Symptom: The script exits immediately without running any agents, or runs the wrong pipeline.

Fix: Open `.env` and confirm `EVENT_NAME` is set to exactly `pull_request`, `push`, or `issue_comment` with no extra whitespace or quotes.

**PR_NUMBER missing for a PR review run**

Symptom: A `KeyError` or `TypeError` in `main.py` when it attempts to read the PR number from the environment.

Fix: Set `PR_NUMBER` to the integer number of an open pull request in the repository specified by `GITHUB_REPOSITORY`.

**CONTRIBUTING.md already exists so onboarding exits early**

Symptom: Running with `EVENT_NAME=push` produces no output and no files are committed.

Fix: This is expected behavior. The onboarding pipeline is designed to run only once, on a fresh repository. To force a re-run during development, temporarily delete or rename `CONTRIBUTING.md` in the target repository, then run the pipeline again.

**Stale cache causing outdated codebase summaries**

Symptom: The onboarding documents reflect an older state of the repository that does not match the current code.

Fix: Delete `.codeguard_cache.json` from the project root. On the next run, `cache.py` will recompute the file tree hash and `explore_codebase.py` will regenerate the codebase summary from scratch.

**Missing tzdata on Linux causing timezone errors**

Symptom: `ZoneInfoNotFoundError: 'America/Los_Angeles'` on Linux systems where the operating system does not ship IANA timezone data.

Fix: Confirm that `tzdata` was installed by checking `pip show tzdata`. If it is missing, run `pip install tzdata` inside the virtual environment.