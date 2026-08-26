"""Same sibling-repo credential fallback pattern used across this portfolio."""

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

HERE = Path(__file__).parent
JIRA_FALLBACK_ENV = HERE.parent / "pm-automation-system" / ".env"


def _fill_from(cfg, keys, fallback_path):
    missing = [k for k in keys if not cfg.get(k)]
    if missing and fallback_path.exists():
        fallback = dotenv_values(fallback_path)
        for k in missing:
            if fallback.get(k):
                cfg[k] = fallback[k]


def load_config() -> dict:
    load_dotenv(HERE / ".env")
    cfg = {
        "JIRA_URL": os.environ.get("JIRA_URL", ""),
        "JIRA_EMAIL": os.environ.get("JIRA_EMAIL", ""),
        "JIRA_API_TOKEN": os.environ.get("JIRA_API_TOKEN", ""),
        "JIRA_PROJECT_KEY": os.environ.get("JIRA_PROJECT_KEY", "PGMAUTO"),
    }
    _fill_from(cfg, ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"], JIRA_FALLBACK_ENV)
    return cfg
