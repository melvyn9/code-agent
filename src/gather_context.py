import os
from github_client import get_pr_diff, get_changed_files

def gather_pr_context(pr_number):
    print(f"Gathering context for PR #{pr_number}...")
    diff = get_pr_diff(pr_number)
    changed_files = get_changed_files(pr_number)
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