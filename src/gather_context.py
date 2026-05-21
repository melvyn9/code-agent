import os
from github_client import get_pr_diff, get_changed_files

def gather_pr_context(pr_number):
    print(f"Gathering context for PR #{pr_number}...")

    try:
        diff = get_pr_diff(pr_number)
    except Exception as e:
        print(f"Failed to fetch PR diff: {e}")
        diff = "Diff unavailable due to an error."

    try:
        changed_files = get_changed_files(pr_number)
    except Exception as e:
        print(f"Failed to fetch changed files: {e}")
        changed_files = []

    context = f"""
PR Number: {pr_number}
Repository: {os.getenv('REPO_NAME')}

Changed files:
{chr(10).join(f'-{f}' for f in changed_files)}

Diff:
{diff}
"""
    
    print(f"Context gathered. {len(changed_files)} file(s) changed.")
    return context