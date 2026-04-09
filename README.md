# LMS Engine

This service is the backend engine for a role-readiness LMS. It is centered on:

- roles
- competencies
- evidence
- KPI-driven remediation
- LMS-manager improvement insights

The engine exposes a small JSON API using the Python standard library so it can
run in a clean environment without framework dependencies.

## Core Concepts

- `Role`: business responsibility and growth context.
- `Competency`: capability required to perform a role well.
- `Evidence`: proof that a learner has demonstrated a competency.
- `KPI`: business metric linked back to competencies so weak performance can
  trigger remediation.

Courses, content, assessments, and readiness reports exist to support these
core entities. The platform now supports two connected loops:

- learner remediation when KPI performance drops
- content improvement when the LMS manager sees repeated weak KPI patterns

## Modules

- `domain`: entity definitions and enums
- `repositories`: in-memory repositories for the first engine iteration
- `application`: business services for framework management, learning paths,
  evidence capture, readiness scoring, KPI analysis, and improvement insights
- `api`: lightweight HTTP interface
- `ui`: static dashboard for the learner-remediation and manager-improvement
  loops

## Run

```bash
python3 main.py
```

The server starts on `http://127.0.0.1:8000`.

The UI is served from `/`.

## Key Endpoints

- `GET /health`
- `GET /roles`
- `POST /roles`
- `POST /roles/{role_id}/requirements`
- `GET /competencies`
- `POST /competencies`
- `GET /assets`
- `POST /assets`
- `GET /assessments`
- `POST /assessments`
- `GET /employees`
- `POST /employees`
- `GET /kpis`
- `POST /kpis`
- `POST /roles/{role_id}/learning-path/generate`
- `GET /roles/{role_id}/learning-path`
- `POST /employees/{employee_id}/evidence`
- `POST /employees/{employee_id}/kpi-observations`
- `GET /employees/{employee_id}/kpi-analysis`
- `GET /employees/{employee_id}/readiness`
- `GET /analytics/weak-kpis`
- `GET /dashboard/summary`
- `POST /demo/seed`

## Test

```bash
python3 -m unittest discover -s tests
```
