Here is the complete `CONTRIBUTING.md` content:

---

```markdown
# Contributing to CodeGuard

CodeGuard is a GitHub integrated AI agent built on the Claude Agent SDK that automatically reviews pull requests for security vulnerabilities and code quality issues, and generates onboarding documentation for newly initialized repositories.

---

## Prerequisites

Before setting up the project, ensure you have the following installed on your machine:

- Python 3.11
- Git
- A GitHub account with access to the repository
- An Anthropic API key with access to the claude-sonnet-4-6 model

---

## Cloning and Setting Up the Project Locally

Clone the repository to your local machine:

```
git clone https://github.com/<your-org>/codeguard.git
cd codeguard
```

Create a Python virtual environment in the project root:

```
python3.11 -m venv venv
```

---

## Activating the Virtual Environment

On macOS and Linux:

```
source venv/bin/activate
```

On Windows:

```
venv\Scripts\activate
```

You should see the environment name appear in your shell prompt. Run `deactivate` at any time to exit the virtual environment.

---

## Installing Dependencies

With the virtual environment active, install all runtime dependencies from `requirements.txt`:

```
pip install -r requirements.txt
```

This installs `claude-agent-sdk`, `pygithub`, and `python-dotenv`.

---

## Environment Variables

CodeGuard reads configuration exclusively from environment variables. Locally, these are loaded from a `.env` file in the project root using `python-dotenv`. This file is excluded from version control via `.gitignore` and must be created manually.

Create a `.env` file in the project root with the following contents:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here
REPO_NAME=owner/repository-name
PR_NUMBER=123
EVENT_NAME=pull_request
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Authenticates requests to the Anthropic API. All Claude agent calls across every module depend on this key. |
| `GITHUB_TOKEN` | Yes | A GitHub personal access token used by PyGithub to read pull request data, post review comments, and commit generated files back to the repository. |
| `REPO_NAME` | Yes | The full repository identifier in `owner/repository` format. Used to target the correct GitHub repository when fetching diffs and posting comments. |
| `PR_NUMBER` | Conditionally required | The pull request number to review. Required when `EVENT_NAME` is set to `pull_request`. Can be omitted when testing the onboarding pipeline locally. |
| `EVENT_NAME` | Yes | Controls which pipeline runs. Set to `pull_request` to trigger the PR review pipeline, or `push` to trigger the repository onboarding pipeline. |

Never commit your `.env` file or any of its values to version control.

---

## Running the Project Locally

With the virtual environment active and your `.env` file in place, run the entry point directly:

```
python src/main.py
```

The orchestrator reads `EVENT_NAME` and routes execution accordingly:

- If `EVENT_NAME` is `pull_request`, CodeGuard fetches the PR diff, runs the security scan, quality review, and PR summary agents in sequence, then posts a consolidated markdown comment to the pull request.
- If `EVENT_NAME` is `push`, CodeGuard checks whether `CONTRIBUTING.md` already exists in the repository root. If it does not, it explores the codebase, generates a `CONTRIBUTING.md` file using a Claude agent, and commits it directly to the repository.

---

## Branch Naming Conventions

Use the following prefixes to keep branch names consistent and scannable:

| Prefix | Use for |
|---|---|
| `feat/` | New features or capabilities |
| `fix/` | Bug fixes |
| `docs/` | Documentation changes only |
| `refactor/` | Code restructuring without behavior changes |
| `chore/` | Dependency updates, config changes, or tooling |

Branch names should be lowercase and use hyphens to separate words. Examples:

```
feat/add-dependency-audit-agent
fix/post-results-encoding-error
docs/update-environment-variable-table
```

---

## Opening a Pull Request

1. Create a branch from `main` following the naming conventions above.
2. Make your changes and commit them with clear, descriptive commit messages written in the imperative mood (for example, "Add input validation to gather_context").
3. Push your branch to the remote repository.
4. Open a pull request against `main` on GitHub.
5. Fill in the pull request description with a summary of what changed and why.
6. Wait for CodeGuard and any human reviewers to complete their reviews before merging.

Keep pull requests focused on a single concern. Large or unrelated changes are harder to review and more likely to introduce regressions.

---

## What CodeGuard Checks on Every Pull Request

CodeGuard runs automatically on every pull request via GitHub Actions. It executes three independent Claude agent passes against the PR diff and posts a single consolidated comment with the combined findings.

**Security scan**

Looks for hardcoded secrets or credentials, injection vulnerabilities, unsafe use of `eval` or `exec`, missing input validation, and insecure dependency additions.

**Quality review**

Assesses function complexity, naming consistency, error handling completeness, duplicated logic, missing tests, and hardcoded values that should be configurable.

**PR summary**

Produces a 2 to 5 sentence plain English summary of the pull request covering its intent, the areas of the codebase it affects, and any notable risks introduced.

All three outputs are combined into a single formatted markdown comment posted directly to the pull request. No action is required to trigger this review; it runs on every `opened`, `synchronize`, and `reopened` pull request event automatically.
```

---

The document follows your formatting constraints (no unnecessary hyphens, no emojis) and covers all nine required topics. A few decisions worth noting:

- `PR_NUMBER` is marked "Conditionally required" rather than simply "Yes" or "No" because it is genuinely only needed when running the PR review pipeline, and flagging that distinction saves contributors from a confusing runtime error.
- The branch naming table uses hyphens because those are the conventional separator in branch names themselves, which counts as "necessary" per your instruction.
- The CodeGuard checks section is written entirely in prose and bold headings rather than nested bullets, keeping it readable without over-structuring what is essentially a narrative description of automated behavior.