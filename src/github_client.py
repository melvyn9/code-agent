import os
from github import Github

def get_github_client():
    token = os.getenv("GITHUB_TOKEN")
    return Github(token)

def get_repo():
    client = get_github_client()
    repo_name = os.getenv("REPO_NAME")
    return client.get_repo(repo_name)

def get_pr_diff(pr_number):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))
    diff = ""
    for file in pr.get_files():
        diff += f"File: {file.filename}\n"
        diff += f"{file.patch or 'Binary file, no diff available'}\n\n"
    return diff

def get_changed_files(pr_number):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))
    return [file.filename for file in pr.get_files()]

def post_pr_comment(pr_number, body):
    repo = get_repo()
    pr = repo.get_pull(int(pr_number))
    pr.create_issue_comment(body)

def commit_file(path, content, message):
    repo = get_repo()
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, message, content, existing.sha)
        print(f"Updated {path} in repo.")
    except Exception:
        repo.create_file(path, message, content)
        print(f"Created {path} in repo.")