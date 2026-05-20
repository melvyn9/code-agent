import os
from github_client import get_repo

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