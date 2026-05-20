# ARCHITECTURE.md

## High Level System Overview

CodeGuard is a GitHub integrated AI agent built on the Claude Agent SDK. It operates as a fully automated code intelligence layer that activates in response to repository events and performs two distinct functions: reviewing pull requests for security vulnerabilities and code quality issues, and generating onboarding documentation for new repositories.

The system runs entirely within GitHub Actions. There is no persistent server or long running process. Each workflow run is a stateless execution triggered by a GitHub event, routed through a single entry point, dispatched to one of two pipelines, and terminated once all outputs have been committed or posted back to GitHub.

All AI reasoning is delegated to Claude sub-agents instantiated via the Claude Agent SDK. Each sub-agent receives a focused prompt and optional tool access, executes its task, and returns structured output to the calling module. The orchestration layer in Python coordinates these agents, assembles their outputs, and communicates results back to GitHub through the PyGithub library.

---

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline activates when a pull request is opened, synchronized, or reopened. Its purpose is to analyze the changes introduced by a pull request and post a structured review comment directly on the PR.

The pipeline begins by reading the PR number from the environment, then fetching the raw diff and the list of changed file paths from the GitHub API. These are assembled into a single context string. Three Claude sub-agents then run in sequence: one performs a security scan, one performs a code quality review, and one produces a plain English summary of what the PR does. Their outputs are composed into a single formatted markdown comment that is posted to the pull request.

### Onboarding Pipeline

The onboarding pipeline activates in two scenarios: a push to the main branch, or an issue comment containing the "/onboard" command. Its purpose is to generate a complete set of onboarding documentation for repositories that do not yet have one.

The pipeline begins by checking whether CONTRIBUTING.md already exists at the root of the target repository. If it does, the pipeline exits early with no action taken. If it does not, a Claude sub-agent with file system exploration tools analyzes the repository structure and produces a thorough codebase summary. Three additional Claude sub-agents then each take that summary and independently generate CONTRIBUTING.md, ARCHITECTURE.md, and SETUP.md. Each generated file is committed directly to the repository via the GitHub API.

---

## Module Breakdown

### src/main.py

The single entry point for the entire system. Reads the EVENT\_NAME environment variable and routes execution to either the PR review pipeline or the onboarding pipeline. Contains no business logic of its own; its sole responsibility is event type detection and pipeline dispatch.

### src/github\_client.py

A thin wrapper around the PyGithub library. Exposes five helper functions used by all other modules:

- get\_github\_client initializes and returns an authenticated Github instance using the GITHUB\_TOKEN environment variable.
- get\_repo returns a Repository object for the configured REPO\_NAME.
- get\_pr\_diff fetches and returns the raw unified diff for a given PR number.
- get\_changed\_files returns the list of file paths modified by a given PR.
- post\_pr\_comment posts a string as a comment on a given PR.
- commit\_file creates or updates a file at a given path in the repository with specified content.

### src/gather\_context.py

Orchestrates the initial data collection step of the PR review pipeline. Calls get\_pr\_diff and get\_changed\_files, then assembles their outputs into a single structured context string that is passed downstream to each of the three review agents.

### src/security\_scan.py

Instantiates a Claude sub-agent with a security focused prompt. The agent analyzes the PR context string and returns a structured findings list. Coverage includes hardcoded secrets, injection vulnerabilities, unsafe eval usage, missing input validation, and insecure dependencies.

### src/quality\_review.py

Instantiates a Claude sub-agent with a code quality focused prompt. The agent analyzes the PR context string and returns a structured notes list. Coverage includes cyclomatic complexity, naming conventions, error handling patterns, code duplication, test coverage, inline documentation, and hardcoded values.

### src/summarize\_pr.py

Instantiates a Claude sub-agent that produces a concise plain English summary of the pull request. The summary describes what the PR does, which parts of the codebase it affects, and any notable risks introduced by the changes.

### src/post\_results.py

Receives the outputs of the three review agents (security findings, quality notes, and summary) and composes them into a single formatted markdown string. Posts the composed comment to the pull request via the post\_pr\_comment helper.

### src/detect\_new\_repo.py

Guards the onboarding pipeline against redundant execution. Checks the repository root for the existence of CONTRIBUTING.md. Returns a boolean indicating whether the onboarding pipeline should proceed. If the file already exists, the pipeline is bypassed entirely.

### src/explore\_codebase.py

The first substantive step of the onboarding pipeline. Instantiates a Claude sub-agent equipped with Read, Glob, and Bash tools. The agent explores the repository structure autonomously and produces a thorough structured summary of the codebase, including directory layout, language and stack, entry points, key modules, dependencies, and configuration files. This summary is passed as input to each of the three documentation generators.

### src/gen\_contributing.py

Receives the codebase summary and instantiates a Claude sub-agent to generate a complete CONTRIBUTING.md file. Commits the result to the repository root via commit\_file.

### src/gen\_architecture.py

Receives the codebase summary and instantiates a Claude sub-agent to generate a complete ARCHITECTURE.md file. Commits the result to the repository root via commit\_file.

### src/gen\_setup\_guide.py

Receives the codebase summary and instantiates a Claude sub-agent to generate a complete SETUP.md file. Commits the result to the repository root via commit\_file.

---

## Data Flow

### PR Review Data Flow

1. GitHub Actions detects a pull\_request event and sets EVENT\_NAME, PR\_NUMBER, REPO\_NAME, GITHUB\_TOKEN, and ANTHROPIC\_API\_KEY in the workflow environment.
2. src/main.py reads EVENT\_NAME and dispatches to the PR review pipeline.
3. src/gather\_context.py calls src/github\_client.py to fetch the PR diff and changed file list, then assembles them into a context string.
4. The context string is passed to src/security\_scan.py, src/quality\_review.py, and src/summarize\_pr.py, each of which passes it to a Claude sub-agent and returns structured output.
5. src/post\_results.py receives all three outputs, composes a formatted markdown comment, and calls post\_pr\_comment to write it to the PR on GitHub.

### Onboarding Data Flow

1. GitHub Actions detects a push to main or an issue\_comment event containing "/onboard" and sets the required environment variables.
2. src/main.py reads EVENT\_NAME and, for issue\_comment events, checks COMMENT\_BODY for the "/onboard" trigger before dispatching to the onboarding pipeline.
3. src/detect\_new\_repo.py calls the GitHub API to check whether CONTRIBUTING.md exists. If it does, execution stops.
4. src/explore\_codebase.py instantiates a Claude sub-agent with file exploration tools. The agent reads the repository and returns a structured codebase summary string.
5. The codebase summary is passed independently to src/gen\_contributing.py, src/gen\_architecture.py, and src/gen\_setup\_guide.py.
6. Each generator passes the summary to a Claude sub-agent, receives generated markdown content, and calls commit\_file to write the result to the repository.

---

## External Dependencies

### claude-agent-sdk

The Anthropic Claude Agent SDK is the core AI framework. It is used in every agent module to instantiate sub-agents via the query() async generator interface, with ClaudeAgentOptions controlling model selection and tool scoping. Each sub-agent is isolated to a specific task and given only the tools and prompt context it needs, which keeps reasoning focused and outputs predictable.

### pygithub (PyGithub)

PyGithub is the GitHub REST API client library. It is used exclusively within src/github\_client.py to authenticate with GitHub, fetch PR diffs and changed file lists, post PR comments, and commit generated files back to the repository. Centralizing all GitHub interactions in a single wrapper module keeps the rest of the codebase decoupled from the API client.

### python-dotenv

python-dotenv is used to load environment variables from a local .env file during development. In production the same variables are injected by GitHub Actions from repository secrets, so python-dotenv has no effect at runtime. It exists solely to make local testing convenient without requiring manual export of sensitive values in the shell.

---

## GitHub Actions Integration

The workflow is defined in .github/workflows/codeguard.yml and is the sole mechanism by which CodeGuard is triggered in production.

### Triggers

The workflow responds to three event types:

- pull\_request with activity types opened, synchronize, and reopened routes to the PR review pipeline.
- push targeting the main branch routes to the onboarding pipeline.
- issue\_comment with activity type created routes to the onboarding pipeline when COMMENT\_BODY contains the "/onboard" command. The COMMENT\_BODY variable is injected into the environment so src/main.py can inspect it.

### Execution Steps

1. The workflow checks out the repository at the triggering commit.
2. Python 3.11 is configured using the actions/setup-python action.
3. Dependencies are installed from requirements.txt via pip.
4. src/main.py is executed directly with the command "python src/main.py".

### Environment Variable Injection

All secrets and context variables are injected from GitHub repository secrets into the workflow environment. These include ANTHROPIC\_API\_KEY for Claude SDK authentication, GITHUB\_TOKEN for PyGithub authentication, REPO\_NAME identifying the target repository, EVENT\_NAME carrying the GitHub event type, PR\_NUMBER carrying the pull request number for PR review runs, and COMMENT\_BODY carrying the issue comment text for comment triggered onboarding runs.

Because all configuration flows through environment variables, the same Python source code runs identically in both local development (sourced from .env via python-dotenv) and in the GitHub Actions runner (injected from secrets), with no environment specific branching required in application code.