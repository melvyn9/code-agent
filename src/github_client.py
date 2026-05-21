import os
from github import Github
import time

# Returns an authenticated GitHub client using the GITHUB_TOKEN env var.
def get_github_client():
    token = os.getenv("GITHUB_TOKEN")
    return Github(token)

# Returns the PyGithub Repo object for the repo specified by REPO_NAME.
def get_repo():
    client = get_github_client()
    repo_name = os.getenv("REPO_NAME")
    return client.get_repo(repo_name)

# Fetches every file's diff for a PR and concatenates them into one string.
def get_pr_diff(pr_number):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))
    diff = ""
    for file in pr.get_files():
        diff += f"File: {file.filename}\n"
        diff += f"{file.patch or 'Binary file, no diff available'}\n\n"
    return diff

# Returns a list of filenames changed in the given PR.
def get_changed_files(pr_number):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))
    return [file.filename for file in pr.get_files()]

# Posts a comment on a PR, retrying up to `retries` times on failure with a 3-second delay.
def post_pr_comment(pr_number, body, retries=2):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))

    for attempt in range(retries + 1):
        try:
            pr.create_issue_comment(body)
            print("Comment posted successfully.")
            return
        except Exception as e:
            if attempt < retries:
                print(f"Failed to post comment (attempt {attempt + 1}). Retrying in 3 seconds...")
                time.sleep(3)
            else:
                print(f"Failed to post comment after {retries + 1} attempts: {e}")
                raise

# Creates a new file or updates an existing one in the repo, determined by whether the path already exists.
def commit_file(path, content, message):
    repo = get_repo()
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, message, content, existing.sha)
        print(f"Updated {path} in repo.")
    except Exception:
        repo.create_file(path, message, content)
        print(f"Created {path} in repo.")