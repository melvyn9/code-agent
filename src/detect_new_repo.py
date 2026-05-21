import os
from github_client import get_repo

# Returns True if CONTRIBUTING.md is missing from the repo, signalling that onboarding should run.
def is_new_repo():
    print("Checking if repo needs onboarding...")
    repo = get_repo()

    try:
        repo.get_contents("CONTRIBUTING.md")
        print("CONTRIBUTING.md already exists. Skipping onboarding.")
        return False
    except Exception:
        print("CONTRIBUTING.md not found. Onboarding needed.")
        return True