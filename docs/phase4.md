# Title: Phase 4 — Polish

## Goal
Turn the working prototype into a portfolio-ready project by adding configuration support, error handling, session logging, performance optimizations, cost reductions, and a polished README with a live demo asset.

---

## Work Done

### Project structure
```
src/
├── main.py              # updated — config, logger, parallel onboarding, routing hardening
├── github_client.py     # updated — retry logic on post_pr_comment
├── gather_context.py    # updated — error handling on GitHub API calls
├── security_scan.py     # updated — error handling, severity threshold support
├── quality_review.py    # updated — error handling
├── summarize_pr.py      # updated — error handling, switched to claude-haiku-4-5
├── post_results.py      # unchanged
├── detect_new_repo.py   # unchanged
├── explore_codebase.py  # updated — cache integration, error handling
├── gen_contributing.py  # unchanged
├── gen_architecture.py  # unchanged
├── gen_setup_guide.py   # unchanged
├── config.py            # new — loads and parses .codeguard.yml
├── logger.py            # new — session logging with Pacific time
└── cache.py             # new — file structure hashing and codebase summary caching
.codeguard.yml           # new — user-facing config file
README.md                # updated — full portfolio README with demo screenshot
```

### Key files

**`src/config.py`** — loads .codeguard.yml and merges with defaults
```python
import os
import yaml

DEFAULT_CONFIG = {
    "security": {"enabled": True, "severity_threshold": "low"},
    "quality": {"enabled": True},
    "summary": {"enabled": True},
    "onboarding": {"enabled": True},
}

def load_config():
    config_path = ".codeguard.yml"
    if not os.path.exists(config_path):
        print("No .codeguard.yml found. Using defaults.")
        return DEFAULT_CONFIG
    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f)
    config = DEFAULT_CONFIG.copy()
    for key in DEFAULT_CONFIG:
        if key in user_config:
            config[key] = {**DEFAULT_CONFIG[key], **user_config[key]}
    print(f"Config loaded from {config_path}")
    return config
```

**`src/logger.py`** — session logger with Pacific time using zoneinfo
```python
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

class SessionLogger:
    def __init__(self):
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
        self.session = {
            "timestamp": now.isoformat(),
            "repo": os.getenv("REPO_NAME"),
            "pr_number": os.getenv("PR_NUMBER"),
            "event": os.getenv("EVENT_NAME"),
            "runs": []
        }

    def log(self, agent_name, prompt, result, status="success"):
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
        self.session["runs"].append({
            "agent": agent_name,
            "status": status,
            "prompt_length": len(prompt),
            "result_length": len(result),
            "result_preview": result[:300],
            "timestamp": now.isoformat()
        })

    def save(self, path="codeguard_session.json"):
        with open(path, "w") as f:
            json.dump(self.session, f, indent=2)
        print(f"Session log saved to {path}")
```

**`src/cache.py`** — hashes repo file structure and caches codebase summary to disk
```python
import json
import os
import hashlib
from github_client import get_repo

CACHE_FILE = ".codeguard_cache.json"

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

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_cached_summary():
    cache = load_cache()
    return cache.get("codebase_summary")

def save_summary_to_cache(summary):
    cache = load_cache()
    cache["codebase_summary"] = summary
    save_cache(cache)

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
```

**`.codeguard.yml`** — user-facing config file
```yaml
security:
  enabled: true
  severity_threshold: low  # low | medium | high

quality:
  enabled: true

summary:
  enabled: true

onboarding:
  enabled: true
```

**`requirements.txt`** — updated dependencies
```
claude-agent-sdk
pygithub
python-dotenv
pyyaml
tzdata
```

### Summary
Added config file support via `.codeguard.yml` and `src/config.py` — users can now enable/disable each agent and set a severity threshold without touching code. Wrapped all agent calls in try/except for graceful degradation — failures post a fallback comment instead of crashing. Added retry logic with 3 second delay to `post_pr_comment()`. Built `src/logger.py` to record every agent run to `codeguard_session.json` with Pacific time timestamps, uploaded as a GitHub Actions artifact for 7 days. Switched `summarize_pr.py` from `claude-sonnet-4-6` to `claude-haiku-4-5` — 3x cheaper with equal output quality confirmed on a real PR. Replaced sequential doc generation with `asyncio.gather()` for parallel execution — roughly 3x faster onboarding pipeline. Built `src/cache.py` to hash the repo file structure using MD5 and persist the codebase summary to disk — subsequent `/onboard` triggers skip the expensive exploration step if the structure has not changed. Confirmed cache working on the `/onboard` re-trigger path. Opened a PR with intentional security vulnerabilities to generate the demo screenshot — CodeGuard caught every planted bug including hardcoded secrets, SQL injection, command injection, hardcoded credentials, missing error handling, magic numbers, and no tests. Wrote the full portfolio README with architecture overview, install instructions, cost table, and key engineering decisions.

---

## Blockers

- **`zoneinfo` requires `tzdata` on Windows** — Python's built-in zoneinfo module does not ship timezone data on Windows unlike macOS and Linux. Fix: `pip install tzdata` and add to `requirements.txt`
- **`get_changed_files()` and `post_pr_comment()` accidentally merged** — retry logic was pasted into the wrong function during error handling implementation. Fix: separated them back into their correct implementations
- **`.codeguard_cache.json` accidentally committed to version control** — the cache file was tracked before being added to `.gitignore`. Fix: `git rm --cached .codeguard_cache.json`
- **Cache not triggering** — `explore_codebase.py` was running without the cache check because the updated version was never saved. Fix: replaced the entire file with the correct version including cache imports
- **Working on wrong branch** — Phase 4 work was done on `phase-2/pr-review-agent` instead of a dedicated phase-4 branch. Managed via `git stash` and careful branch switching
- **`zoneinfo` initially replaced with `pytz`** — `pytz` is considered legacy since Python 3.9. Reverted to `zoneinfo` with `tzdata` for the correct modern approach

---

## To Do Next

- Merge `phase-2/pr-review-agent` into main
- Close the `feat/intentional-bugs-demo` PR
- Project complete — ready for portfolio
