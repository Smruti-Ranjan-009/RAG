"""Versioned prompts, loaded from `prompts.yaml` (shipped next to this module).

Per RAG.md's Phase-2 requirement: a prompt change is now a diffable, reviewed
edit to a config file, not buried in application code. Switching the active
version — e.g. rolling back after Phase-3 eval shows a regression — is a
one-line change to `prompts.yaml`, not a code deploy.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

PROMPTS_FILE = Path(__file__).parent / "prompts.yaml"


@lru_cache(maxsize=1)
def _load_prompts() -> dict:
    with open(PROMPTS_FILE) as f:
        return yaml.safe_load(f)


def get_prompt_template(version: str | None = None) -> str:
    """Returns the template string for `version`, or the configured
    `active_version` if none is given."""
    config = _load_prompts()
    version = version or config["active_version"]
    try:
        return config["versions"][version]["template"]
    except KeyError:
        available = list(config["versions"].keys())
        raise ValueError(f"Unknown prompt version {version!r}. Available: {available}")
