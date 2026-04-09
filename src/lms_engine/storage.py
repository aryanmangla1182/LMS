"""Simple JSON-backed persistence for the LMS MVP."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any, Dict


DEFAULT_STATE: Dict[str, Any] = {
    "roles": [],
    "users": [],
    "learners": [],
    "sessions": [],
    "enrollments": [],
    "assessment_attempts": [],
    "assignment_submissions": [],
    "kpi_observations": [],
    "remediation_assignments": [],
    "activity_log": [],
    "media_assets": [],
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


class AssetStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_text(self, filename: str, content: str) -> Dict[str, str]:
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return self._present(path)

    def save_json(self, filename: str, payload: Dict[str, Any]) -> Dict[str, str]:
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self._present(path)

    def save_binary(self, filename: str, payload: bytes) -> Dict[str, str]:
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return self._present(path)

    def resolve(self, relative_path: str) -> Path:
        return (self.root / relative_path).resolve()

    def content_type(self, relative_path: str) -> str:
        content_type, _ = mimetypes.guess_type(relative_path)
        return content_type or "application/octet-stream"

    def _present(self, path: Path) -> Dict[str, str]:
        relative = path.relative_to(self.root).as_posix()
        return {
            "relative_path": relative,
            "url": "/media/{0}".format(relative),
        }
