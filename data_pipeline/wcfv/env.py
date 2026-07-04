"""
Tiny .env loader (no external dependency).

Reads KEY=VALUE lines from data_pipeline/.env into os.environ so secrets like the
Odds API key never have to be hard-coded or committed. Lines starting with '#' and
blank lines are ignored; existing environment variables are not overwritten.
"""

from __future__ import annotations

import os

from wcfv.paths import PROJECT_ROOT

ENV_FILE = PROJECT_ROOT / ".env"


def load_env(path=ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
