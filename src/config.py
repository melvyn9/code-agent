import os
import yaml

DEFAULT_CONFIG = {
    "security": {"enabled": True, "severity_threshold": "low"},
    "quality": {"enabled": True},
    "summary": {"enabled": True},
    "onboarding": {"enabled": True},
}

# Loads .codeguard.yml and deep-merges each section with DEFAULT_CONFIG; falls back to defaults if the file is missing.
def load_config():
    config_path = ".codeguard.yml"
    if not os.path.exists(config_path):
        print("No .codeguard.yml found. Using defaults.")
        return DEFAULT_CONFIG

    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f)

    # Merge user config with defaults
    config = DEFAULT_CONFIG.copy()
    for key in DEFAULT_CONFIG:
        if key in user_config:
            config[key] = {**DEFAULT_CONFIG[key], **user_config[key]}

    print(f"Config loaded from {config_path}")
    return config