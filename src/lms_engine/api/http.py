"""HTTP interface for the LMS MVP."""

from __future__ import annotations

import json
import mimetypes
from datetime import datetime
from dataclasses import asdict, is_dataclass
from enum import Enum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

from lms_engine.application.mvp import AppError, AuthorizationError, NotFoundError, ValidationError
from lms_engine.bootstrap import AppContainer


UI_DIR = Path(__file__).resolve().parent.parent / "ui"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


class RouteNotFoundError(NotFoundError):
    pass


def serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return serialize(asdict(value))
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


def create_handler(container: AppContainer) -> Callable[..., BaseHTTPRequestHandler]:
    class LMSRequestHandler(BaseHTTPRequestHandler):
        server_version = "LMSEngineMVP/0.2"

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            try:
                if method == "GET" and path in STATIC_FILES:
                    self._send_static(path)
                    return
                if method == "GET" and path.startswith("/media/"):
                    self._send_media(path)
                    return
                if method == "GET" and path.startswith("/studio/videos/"):
                    self._send_studio_video(path)
                    return
                payload = self._read_json_body() if method == "POST" else None
                token = self._extract_token()
                response = route_request(container, method, path, payload, token)
                self._send_json(HTTPStatus.OK, response)
            except RouteNotFoundError as exc:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except AuthorizationError as exc:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except NotFoundError as exc:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except ValidationError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except AppError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except KeyError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing field: {0}".format(exc.args[0])})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def _read_json_body(self) -> Dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length == 0:
                return {}
            raw_body = self.rfile.read(content_length)
            return json.loads(raw_body.decode("utf-8"))

        def _send_json(self, status_code: HTTPStatus, payload: Dict[str, Any]) -> None:
            response_bytes = json.dumps(serialize(payload)).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)

        def _send_static(self, path: str) -> None:
            filename, content_type = STATIC_FILES[path]
            file_path = UI_DIR / filename
            if not file_path.exists():
                raise RouteNotFoundError("Static file not found: {0}".format(path))
            response_bytes = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)

        def _send_media(self, path: str) -> None:
            relative_path = path[len("/media/") :]
            file_path = container.engine.asset_store.resolve(relative_path)
            if not file_path.exists():
                raise RouteNotFoundError("Media file not found: {0}".format(path))
            response_bytes = file_path.read_bytes()
            content_type, _ = mimetypes.guess_type(str(file_path))
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)

        def _send_studio_video(self, path: str) -> None:
            asset_id = path[len("/studio/videos/") :]
            mime_type, response_bytes = container.kpi_studio.fetch_video_bytes(asset_id)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)

        def _extract_token(self) -> str:
            header = self.headers.get("Authorization", "")
            if header.startswith("Bearer "):
                return header[len("Bearer ") :].strip()
            return ""

    return LMSRequestHandler


def route_request(
    container: AppContainer,
    method: str,
    path: str,
    payload_or_context: Optional[Dict[str, Any]],
    payload_or_token: Any,
) -> Dict[str, Any]:
    engine = container.engine
    payload: Optional[Dict[str, Any]]
    token = ""

    if isinstance(payload_or_token, str):
        payload = payload_or_context
        token = payload_or_token
    else:
        payload = payload_or_token if isinstance(payload_or_token, dict) else payload_or_context

    if method == "GET" and path == "/api/health":
        return {"status": "ok"}

    if method == "GET" and path == "/api/config":
        return {"item": engine.get_config()}

    if method == "POST" and path == "/api/demo/seed":
        engine.require_trainer(token)
        return {"item": engine.reset_and_seed_demo()}

    if method == "POST" and path == "/api/auth/request-code":
        return {"item": engine.request_login_code(payload or {})}

    if method == "POST" and path == "/api/auth/verify-code":
        return {"item": engine.verify_login_code(payload or {})}

    if method == "GET" and path == "/api/auth/me":
        return {"item": engine.get_current_user(token)}

    if method == "GET" and path == "/api/roles":
        engine.require_trainer(token)
        return {"items": engine.list_roles()}

    if method == "POST" and path == "/api/roles/generate":
        engine.require_trainer(token)
        return {"item": engine.generate_role_blueprint(payload or {})}

    if path.startswith("/api/roles/"):
        suffix = path[len("/api/roles/") :]
        if "/" not in suffix and method == "GET":
            engine.require_trainer(token)
            return {"item": engine.get_role(suffix)}
        if suffix.endswith("/review") and method == "POST":
            engine.require_trainer(token)
            role_id = suffix[: -len("/review")].rstrip("/")
            return {"item": engine.apply_role_review(role_id, payload or {})}
        if suffix.endswith("/publish") and method == "POST":
            engine.require_trainer(token)
            role_id = suffix[: -len("/publish")].rstrip("/")
            return {"item": engine.publish_role(role_id)}

    if method == "GET" and path == "/api/learners":
        engine.require_trainer(token)
        return {"items": engine.list_learners()}

    if method == "GET" and path == "/api/users":
        engine.require_trainer(token)
        return {"items": engine.list_users()}

    if method == "POST" and path == "/api/users":
        engine.require_trainer(token)
        return {"item": engine.create_user(payload or {})}

    if method == "GET" and path in {"/api/dashboard/trainer", "/api/dashboard/owner"}:
        engine.require_trainer(token)
        return {"item": engine.get_trainer_dashboard()}

    if method == "GET" and path == "/api/my/dashboard":
        return {"item": engine.get_my_dashboard(token)}

    if method == "GET" and path == "/api/my/pitches":
        return {"items": engine.list_my_pitch_sessions(token)}

    if method == "POST" and path == "/api/my/pitches/analyze":
        return {"item": engine.analyze_my_pitch(token, payload or {})}

    if path.startswith("/api/my/lessons/") and path.endswith("/complete") and method == "POST":
        lesson_id = path[len("/api/my/lessons/") : -len("/complete")].rstrip("/")
        return {"item": engine.complete_my_lesson(token, lesson_id)}

    if path.startswith("/api/my/assignments/") and path.endswith("/submit") and method == "POST":
        lesson_id = path[len("/api/my/assignments/") : -len("/submit")].rstrip("/")
        return {"item": engine.submit_my_assignment(token, lesson_id, payload or {})}

    if method == "POST" and path == "/api/my/assessment/submit":
        return {"item": engine.submit_my_assessment(token, payload or {})}

    if method == "POST" and path == "/api/my/kpis":
        return {"item": engine.record_my_kpi(token, payload or {})}

    if path.startswith("/api/my/lessons/") and path.endswith("/media") and method == "POST":
        lesson_id = path[len("/api/my/lessons/") : -len("/media")].rstrip("/")
        return {"item": engine.upload_lesson_media(token, lesson_id, payload or {})}

    if method == "POST" and path == "/studio/session":
        return {"items": serialize(container.kpi_studio.create_session(payload or {}))}

    if method == "GET" and path == "/studio/kpis":
        return {"items": serialize(container.kpi_studio.list_items())}

    if path.startswith("/studio/kpis/"):
        suffix = path[len("/studio/kpis/") :]
        if "/" not in suffix and method == "GET":
            return {"item": serialize(container.kpi_studio.get_item(suffix))}
        if suffix.endswith("/reopen") and method == "POST":
            item_id = suffix[: -len("/reopen")].rstrip("/")
            return {"item": serialize(container.kpi_studio.reopen_item(item_id))}
        if suffix.endswith("/versions") and method == "POST":
            item_id = suffix[: -len("/versions")].rstrip("/")
            version = container.kpi_studio.generate_video_version(item_id, payload or {})
            return {"item": serialize(version)}
        if "/versions/" in suffix and suffix.endswith("/approve") and method == "POST":
            item_id, version_suffix = suffix.split("/versions/", 1)
            version_id = version_suffix[: -len("/approve")].rstrip("/")
            return {"item": serialize(container.kpi_studio.approve_version(item_id.rstrip("/"), version_id))}

    raise RouteNotFoundError("Route not found: {0} {1}".format(method, path))


def create_server(container: AppContainer, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    handler = create_handler(container)
    return ThreadingHTTPServer((host, port), handler)
