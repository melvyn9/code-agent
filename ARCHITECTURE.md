# ARCHITECTURE.md

# CodeGuard Architecture

## High-Level System Overview

CodeGuard is a GitHub-integrated AI agent that operates in two distinct modes depending on the event that triggers it. When a pull request is opened or updated, CodeGuard runs a three-stage review pipeline that produces a security scan, a code quality assessment, and a plain-English summary, all posted as a single comment on the pull request. When a push lands on the main branch of a repository that has no existing CONTRIBUTING.md file, CodeGuard runs an onboarding pipeline that explores the codebase and generates three documentation files committed directly to the repository.

All intelligence is provided by Claude models accessed through the Anthropic Claude Agent SDK. All GitHub interactions are mediated through PyGithub. The system has no database, no server, and no persistent state beyond the files it commits. It runs entirely inside a GitHub Actions runner and exits after each invocation.

## The Two Pipelines

### PR Review Pipeline

The PR review pipeline is activated when EVENT_NAME is set to a pull request event. The orchestrator in src/main.py collects the pull request diff and file list, then fans out to three independent Claude agent calls running in sequence. The security agent inspects the diff for vulnerabilities. The quality agent inspects it for maintainability issues. The summary agent produces a human-readable description of the change. The three outputs are assembled into a single markdown comment and posted to the pull request.

The pipeline is purely read-only with respect to the repository. It does not commit any files. Its only write operation is posting the comment via the GitHub REST API.

### Onboarding Pipeline

The onboarding pipeline is activated when EVENT_NAME corresponds to a push to the main branch. The orchestrator first checks whether CONTRIBUTING.md already exists in the repository root. If it does, the pipeline exits immediately. If it does not, the orchestrator runs a codebase exploration agent that maps the directory structure and identifies languages, frameworks, and entry points. The resulting summary is passed to three documentation generator agents, each of which produces one markdown file. The orchestrator then commits all three files to the repository via the GitHub Contents API.

The onboarding pipeline is write-heavy. Its entire purpose is to produce and persist documentation artifacts. It does not post any pull request comments.

## Module Breakdown

### src/main.py

The single entry point and top-level orchestrator. Reads the EVENT_NAME environment variable and branches into either the PR review pipeline or the onboarding pipeline. In the PR review path it calls gather_context, then security_scan, quality_review, and summarize_pr in sequence, then passes all three results to post_results. In the onboarding path it calls detect_new_repo and, if onboarding is warranted, calls explore_codebase and then the three documentation generators before committing the generated files via github_client.commit_file.

### src/github_client.py

The GitHub API layer. Wraps PyGithub and exposes four functions to the rest of the system. get_pr_diff fetches the raw patch text for each changed file in a pull request. get_changed_files returns the list of modified file paths. post_pr_comment creates a markdown comment on a specified pull request. commit_file creates or updates a file in the repository using the GitHub Contents API. All four functions accept GITHUB_TOKEN and REPO_NAME from the environment rather than from a passed configuration object.

### src/gather_context.py

Assembles the context string that is shared across all three review agents. Calls get_pr_diff and get_changed_files from github_client and packages the PR number, repository name, file list, and full diff into a single formatted string. This string is the sole input to the security, quality, and summary agents.

### src/security_scan.py

Runs the security analysis agent. Sends the PR context string to a Claude agent configured with the Read tool and a prompt directing it to identify hardcoded secrets, injection vulnerabilities, unsafe subprocess usage, missing input validation, and insecure dependency additions. Returns a structured FINDINGS block as a string.

### src/quality_review.py

Runs the code quality agent. Sends the same PR context string to a Claude agent with a prompt focused on function complexity, naming consistency, error handling, code duplication, test coverage gaps, and hardcoded configuration values. Returns a structured QUALITY NOTES block as a string.

### src/summarize_pr.py

Runs the summary agent. Prompts a Claude agent to write a two to five sentence plain-English description of what the PR does, which parts of the codebase are affected, and any notable risks. Returns a SUMMARY block as a string.

### src/post_results.py

Composes and posts the final GitHub comment. Accepts the three agent output strings, strips their individual section headers, and assembles them under a single CodeGuard Review heading in markdown. Calls post_pr_comment from github_client to deliver the assembled comment.

### src/detect_new_repo.py

Implements the onboarding gate. Uses the GitHub Contents API to check whether CONTRIBUTING.md exists in the repository root. Returns a boolean that the orchestrator uses to decide whether to proceed with documentation generation. This check prevents the onboarding pipeline from overwriting documentation that already exists.

### src/explore_codebase.py

Runs the codebase exploration agent. Gives a Claude agent access to the Read, Glob, and Bash tools and prompts it to map the directory structure, identify languages and frameworks, locate entry points, and note configuration files. Returns a structured JSON-style summary string that is passed unchanged to all three documentation generator modules.

### src/gen_contributing.py

Generates CONTRIBUTING.md. Sends the codebase summary to a Claude agent with a prompt requesting a contributor guide covering local setup, environment variables, branch conventions, and the pull request process. Returns raw markdown as a string.

### src/gen_architecture.py

Generates ARCHITECTURE.md. Sends the codebase summary to a Claude agent with a prompt requesting a high-level architecture document covering module responsibilities, data flows, and external dependencies. Returns raw markdown as a string.

### src/gen_setup_guide.py

Generates SETUP.md. Sends the codebase summary to a Claude agent with a prompt requesting a step-by-step setup guide covering prerequisites, environment configuration, and instructions for running both pipelines. Returns raw markdown as a string.

## Data Flow

### PR Review Data Flow

GitHub emits a pull_request event. The Actions runner sets EVENT_NAME, REPO_NAME, PR_NUMBER, GITHUB_TOKEN, and ANTHROPIC_API_KEY as environment variables and executes python src/main.py. main.py identifies the event as a pull request and calls gather_context.py. gather_context.py calls github_client.get_pr_diff and github_client.get_changed_files, which make authenticated REST calls to the GitHub API and return the diff and file list. gather_context.py formats these into a single context string and returns it to main.py.

main.py passes the context string to security_scan.py, quality_review.py, and summarize_pr.py in sequence. Each module sends the context to the Anthropic API via the Claude Agent SDK and receives a structured text block in return. The three blocks are returned to main.py and forwarded to post_results.py. post_results.py assembles them into a single markdown string and calls github_client.post_pr_comment, which posts the comment to the pull request via the GitHub REST API. Execution ends.

### Onboarding Data Flow

GitHub emits a push event targeting the main branch. The Actions runner sets the environment variables and executes python src/main.py. main.py identifies the event as a push and calls detect_new_repo.py. detect_new_repo.py calls the GitHub Contents API to check for CONTRIBUTING.md. If the file exists, execution ends. If it does not, main.py calls explore_codebase.py.

explore_codebase.py instantiates a Claude agent with Read, Glob, and Bash tools and prompts it to survey the repository. The agent uses the tools to read files and list directories in the runner's working copy of the repository. It returns a codebase summary string to main.py.

main.py passes the summary to gen_contributing.py, gen_architecture.py, and gen_setup_guide.py in sequence. Each module sends the summary to the Anthropic API and receives a raw markdown string. main.py calls github_client.commit_file three times, once per document, each of which makes a PUT request to the GitHub Contents API to create the file in the repository. Execution ends.

## External Dependencies

### claude-agent-sdk (Anthropic)

The core AI framework. Provides the query function and ClaudeAgentOptions class used in every agent module. The SDK handles streaming responses from Claude models, tool call dispatch during agentic turns, and retry logic. It is the reason the system can instruct a model to read files, run glob patterns, and execute shell commands during the exploration phase, and why each review and generation task can be expressed as a natural-language prompt rather than a programmatic pipeline.

### PyGithub

Wraps the GitHub REST API. Used exclusively in github_client.py. PyGithub is chosen because it provides typed Python objects for repositories, pull requests, files, and comments, reducing the amount of raw HTTP handling the project needs to maintain. All four functions in github_client.py delegate to PyGithub for authentication, request construction, and response parsing.

### python-dotenv

Loads environment variables from a local .env file at process startup. It is present solely to support local development and testing. In production the GitHub Actions runner injects all required variables directly into the process environment, so python-dotenv has no effect. Locally it allows a developer to place ANTHROPIC_API_KEY, GITHUB_TOKEN, REPO_NAME, and PR_NUMBER in a .env file without exporting them to the shell session.

## GitHub Actions Integration

The workflow is defined in .github/workflows/codeguard.yml. It declares two triggers. The pull_request trigger fires on the opened, synchronize, and reopened activity types, covering initial PR creation and subsequent commits. The push trigger fires on pushes to the main branch, covering direct commits and merged pull requests.

Both triggers run the same single job on an ubuntu-latest runner. The job checks out the repository, sets up Python 3.11, and installs the three direct dependencies from requirements.txt using pip. It then runs python src/main.py.

Five environment variables are injected into the step. ANTHROPIC_API_KEY and GITHUB_TOKEN are read from GitHub Secrets. REPO_NAME is populated from the github.repository context variable, which the Actions runtime provides automatically. PR_NUMBER is populated from github.event.pull_request.number, which is present on pull request events and empty on push events. EVENT_NAME is populated from github.event_name, which is the string "pull_request" or "push" and is what main.py uses to route execution.

GITHUB_TOKEN is the built-in token that Actions mints for each workflow run. It is granted write permissions to the repository contents so that the onboarding pipeline can commit generated files, and write permissions to pull request discussions so that the review pipeline can post comments. No external token rotation or secrets management is required beyond the ANTHROPIC_API_KEY.