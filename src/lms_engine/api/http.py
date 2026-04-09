"""HTTP interface for the LMS engine."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

from lms_engine.application.services import LMSValidationError, NotFoundError, serialize
from lms_engine.bootstrap import AppContainer


UI_DIR = Path(__file__).resolve().parent.parent / "ui"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


class RouteNotFoundError(NotFoundError):
    """Raised when no handler matches an HTTP route."""


def create_handler(container: AppContainer) -> Callable[..., BaseHTTPRequestHandler]:
    class LMSRequestHandler(BaseHTTPRequestHandler):
        server_version = "LMSEngine/0.1"

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = {key: values[0] for key, values in parse_qs(parsed.query).items()}

            try:
                if method == "GET" and path in STATIC_FILES:
                    self._send_static(path)
                    return
                payload = self._read_json_body() if method == "POST" else None
                response = route_request(container, method, path, query, payload)
                self._send_json(HTTPStatus.OK, response)
            except RouteNotFoundError as exc:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except NotFoundError as exc:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except LMSValidationError as exc:
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
            try:
                return json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise LMSValidationError("Invalid JSON payload") from exc

        def _send_json(self, status_code: HTTPStatus, payload: Dict[str, Any]) -> None:
            response_bytes = json.dumps(payload).encode("utf-8")
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

    return LMSRequestHandler


def route_request(
    container: AppContainer,
    method: str,
    path: str,
    query: Dict[str, str],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if method == "GET" and path == "/health":
        return {"status": "ok"}

    if method == "GET" and path == "/roles":
        return {"items": serialize(container.role_framework.list_roles())}

    if method == "POST" and path == "/roles":
        return {"item": serialize(container.role_framework.create_role(payload or {}))}

    if path.startswith("/roles/"):
        role_suffix = path[len("/roles/") :]
        if "/" not in role_suffix and method == "GET":
            return {"item": serialize(container.role_framework.get_role(role_suffix))}

        if role_suffix.endswith("/requirements") and method == "POST":
            role_id = role_suffix[: -len("/requirements")].rstrip("/")
            return {"item": serialize(container.role_framework.add_requirement(role_id, payload or {}))}

        if role_suffix.endswith("/learning-path/generate") and method == "POST":
            role_id = role_suffix[: -len("/learning-path/generate")].rstrip("/")
            return {"item": serialize(container.learning_paths.generate_for_role(role_id))}

        if role_suffix.endswith("/learning-path") and method == "GET":
            role_id = role_suffix[: -len("/learning-path")].rstrip("/")
            return {"item": serialize(container.learning_paths.get_for_role(role_id))}

    if method == "GET" and path == "/competencies":
        return {"items": serialize(container.role_framework.list_competencies())}

    if method == "POST" and path == "/competencies":
        return {"item": serialize(container.role_framework.create_competency(payload or {}))}

    if method == "GET" and path == "/assets":
        return {"items": serialize(container.learning_catalog.list_assets())}

    if method == "POST" and path == "/assets":
        return {"item": serialize(container.learning_catalog.create_asset(payload or {}))}

    if method == "GET" and path == "/assessments":
        return {"items": serialize(container.learning_catalog.list_assessments())}

    if method == "POST" and path == "/assessments":
        return {"item": serialize(container.learning_catalog.create_assessment(payload or {}))}

    if method == "GET" and path == "/employees":
        return {"items": serialize(container.people.list_employees())}

    if method == "POST" and path == "/employees":
        return {"item": serialize(container.people.create_employee(payload or {}))}

    if method == "GET" and path == "/kpis":
        return {"items": serialize(container.kpis.list_kpis())}

    if method == "POST" and path == "/kpis":
        return {"item": serialize(container.kpis.create_kpi(payload or {}))}

    if method == "GET" and path == "/analytics/weak-kpis":
        return {"item": serialize(container.kpis.manager_improvement_report())}

    if method == "GET" and path == "/dashboard/summary":
        return {
            "item": {
                "roles": len(container.role_framework.list_roles()),
                "competencies": len(container.role_framework.list_competencies()),
                "assets": len(container.learning_catalog.list_assets()),
                "assessments": len(container.learning_catalog.list_assessments()),
                "employees": len(container.people.list_employees()),
                "kpis": len(container.kpis.list_kpis()),
                "weak_kpi_patterns": len(container.kpis.manager_improvement_report().weak_kpis),
            }
        }

    if method == "POST" and path == "/demo/seed":
        return {"item": serialize(seed_demo_data(container))}

    if path.startswith("/employees/"):
        employee_suffix = path[len("/employees/") :]

        if employee_suffix.endswith("/evidence") and method == "POST":
            employee_id = employee_suffix[: -len("/evidence")].rstrip("/")
            return {"item": serialize(container.evidence.record_evidence(employee_id, payload or {}))}

        if employee_suffix.endswith("/kpi-observations") and method == "POST":
            employee_id = employee_suffix[: -len("/kpi-observations")].rstrip("/")
            return {"item": serialize(container.kpis.record_observation(employee_id, payload or {}))}

        if employee_suffix.endswith("/kpi-analysis") and method == "GET":
            employee_id = employee_suffix[: -len("/kpi-analysis")].rstrip("/")
            return {"item": serialize(container.kpis.analyze_employee(employee_id))}

        if employee_suffix.endswith("/readiness") and method == "GET":
            employee_id = employee_suffix[: -len("/readiness")].rstrip("/")
            target_role_id = query.get("target_role_id")
            return {"item": serialize(container.readiness.evaluate(employee_id, target_role_id=target_role_id))}

    raise RouteNotFoundError("Route not found: {0} {1}".format(method, path))


def create_server(container: AppContainer, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    handler = create_handler(container)
    return ThreadingHTTPServer((host, port), handler)


def seed_demo_data(container: AppContainer) -> Dict[str, Any]:
    if container.people.list_employees():
        return {"seeded": False, "reason": "Demo data already exists."}

    coaching = container.role_framework.create_competency(
        {
            "name": "Team Coaching",
            "description": "Coach frontline staff on sales and service execution.",
            "category": "people",
        }
    )
    operations = container.role_framework.create_competency(
        {
            "name": "Store Operations",
            "description": "Run opening, closing, and floor standards consistently.",
            "category": "operations",
        }
    )
    conversion = container.role_framework.create_competency(
        {
            "name": "Sales Conversion",
            "description": "Convert walk-ins and membership interest into revenue.",
            "category": "commercial",
        }
    )

    store_manager = container.role_framework.create_role(
        {
            "name": "Store Manager",
            "description": "Own store execution, staff performance, and daily commercial outcomes.",
            "responsibilities": [
                "Run daily store operations",
                "Coach staff on conversion and service",
                "Maintain floor compliance",
            ],
            "growth_outcomes": ["Become ready for Area Manager"],
        }
    )
    for competency_id, level, weight in (
        (coaching.id, 4, 1.0),
        (operations.id, 5, 1.2),
        (conversion.id, 4, 1.1),
    ):
        container.role_framework.add_requirement(
            store_manager.id,
            {
                "competency_id": competency_id,
                "required_level": level,
                "mandatory": True,
                "weight": weight,
            },
        )

    container.learning_catalog.create_asset(
        {
            "title": "Floor Coaching Playbook",
            "summary": "Observed coaching framework for retail teams.",
            "content_type": "video",
            "competency_ids": [coaching.id],
            "estimated_minutes": 18,
        }
    )
    container.learning_catalog.create_asset(
        {
            "title": "Store Opening and Audit Standards",
            "summary": "SOPs for operational consistency and audit readiness.",
            "content_type": "sop",
            "competency_ids": [operations.id],
            "estimated_minutes": 12,
        }
    )
    container.learning_catalog.create_asset(
        {
            "title": "Conversion Recovery Clinic",
            "summary": "How to improve weak conversion through scripting and follow-through.",
            "content_type": "microlearning",
            "competency_ids": [conversion.id],
            "estimated_minutes": 10,
        }
    )
    container.learning_catalog.create_assessment(
        {
            "title": "Operations Walkthrough Check",
            "assessment_type": "practical",
            "competency_ids": [operations.id],
            "passing_score": 80,
            "max_score": 100,
        }
    )
    container.learning_catalog.create_assessment(
        {
            "title": "Conversion Scenario Test",
            "assessment_type": "scenario",
            "competency_ids": [conversion.id],
            "passing_score": 75,
            "max_score": 100,
        }
    )
    container.learning_paths.generate_for_role(store_manager.id)

    conversion_kpi = container.kpis.create_kpi(
        {
            "name": "Conversion Rate",
            "description": "How effectively the store converts inbound demand.",
            "competency_ids": [conversion.id, coaching.id],
            "weak_threshold": 0.85,
        }
    )
    audit_kpi = container.kpis.create_kpi(
        {
            "name": "Audit Score",
            "description": "Operational and SOP compliance score.",
            "competency_ids": [operations.id],
            "weak_threshold": 0.9,
        }
    )

    asha = container.people.create_employee(
        {
            "name": "Asha Menon",
            "email": "asha@cult.fit",
            "current_role_id": store_manager.id,
            "org_unit": "Retail South",
        }
    )
    dev = container.people.create_employee(
        {
            "name": "Dev Shah",
            "email": "dev@cult.fit",
            "current_role_id": store_manager.id,
            "org_unit": "Retail West",
        }
    )

    container.evidence.record_evidence(
        asha.id,
        {
            "competency_id": coaching.id,
            "evidence_type": "manager_signoff",
            "status": "verified",
            "notes": "Strong observed coaching cadence.",
        },
    )
    container.evidence.record_evidence(
        asha.id,
        {
            "competency_id": operations.id,
            "evidence_type": "practical_evaluation",
            "status": "passed",
            "score": 88,
            "max_score": 100,
        },
    )
    container.evidence.record_evidence(
        dev.id,
        {
            "competency_id": operations.id,
            "evidence_type": "practical_evaluation",
            "status": "passed",
            "score": 72,
            "max_score": 100,
        },
    )

    container.kpis.record_observation(
        asha.id,
        {
            "kpi_id": conversion_kpi.id,
            "value": 18,
            "target_value": 25,
            "period_label": "March 2026",
            "notes": "Walk-in conversion below target.",
        },
    )
    container.kpis.record_observation(
        asha.id,
        {
            "kpi_id": audit_kpi.id,
            "value": 92,
            "target_value": 95,
            "period_label": "March 2026",
            "notes": "Mostly healthy audit performance.",
        },
    )
    container.kpis.record_observation(
        dev.id,
        {
            "kpi_id": audit_kpi.id,
            "value": 78,
            "target_value": 95,
            "period_label": "March 2026",
            "notes": "Repeated SOP misses.",
        },
    )

    return {
        "seeded": True,
        "role_id": store_manager.id,
        "employee_ids": [asha.id, dev.id],
        "kpi_ids": [conversion_kpi.id, audit_kpi.id],
    }
