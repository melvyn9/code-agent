import json
import os
import hashlib
from github_client import get_repo

CACHE_FILE = ".codeguard_cache.json"

# Recursively lists all files in the repo, sorts them, and returns an MD5 hash of the path list.
def get_repo_structure_hash():
    repo = get_repo()
    contents = repo.get_contents("")
    files = []

    while contents:
        item = contents.pop(0)
        if item.type == "dir":
            contents.extend(repo.get_contents(item.path))
        else:
            files.append(item.path)

    files.sort()
    structure_string = "\n".join(files)
    return hashlib.md5(structure_string.encode()).hexdigest()

# Reads the cache JSON file from disk; returns an empty dict if the file doesn't exist yet.
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)

# Writes the given data dict to the cache file as formatted JSON.
def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Returns the cached codebase summary string, or None if not yet stored.
def get_cached_summary():
    cache = load_cache()
    return cache.get("codebase_summary")

# Persists the codebase summary string into the cache file for reuse on the next run.
def save_summary_to_cache(summary):
    cache = load_cache()
    cache["codebase_summary"] = summary
    save_cache(cache)

# Compares the current repo file structure hash to the cached one; updates the cache and returns True if it changed.
def has_structure_changed():
    print("Checking repo structure cache...")
    current_hash = get_repo_structure_hash()
    cache = load_cache()
    cached_hash = cache.get("structure_hash")

    if cached_hash == current_hash:
        print("Repo structure unchanged. Skipping exploration.")
        return False
    
    print("Repo structure changed or no cache found. Running exploration.")
    cache["structure_hash"] = current_hash
    save_cache(cache)
    return True