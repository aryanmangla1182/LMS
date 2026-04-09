"""Simple JSON-backed persistence for the LMS MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_STATE: Dict[str, Any] = {
    "roles": [],
    "users": [],
    "learners": [],
    "sessions": [],
    "enrollments": [],
    "assessment_attempts": [],
    "kpi_observations": [],
    "remediation_assignments": [],
    "activity_log": [],
}


class JsonStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(DEFAULT_STATE.copy())

    def load(self) -> Dict[str, Any]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        state = DEFAULT_STATE.copy()
        state.update(raw)
        return state

    def save(self, state: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")
