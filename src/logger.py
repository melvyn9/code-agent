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