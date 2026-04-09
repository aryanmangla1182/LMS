# LMS Engine: Current State

## Purpose

This service is being built as a backend engine for an internal learning and role-readiness platform for Cultfit.

The product is not framed as a generic course platform. It is framed as a role-readiness system for operational teams such as:

- store staff
- store managers
- gym managers
- area managers

The core idea is:

- define what a role is responsible for
- define the competencies required for that role
- map learning content and assessments to those competencies
- collect evidence that a learner has demonstrated those competencies
- measure readiness for the current role and future roles
- react to weak business KPIs by recommending targeted remediation
- help the LMS manager continuously improve content based on repeated weak KPI patterns

## Product Model

The current system is built around 3 primary concepts:

- `Role`
- `Competency`
- `Evidence`

On top of that, a KPI feedback layer has been added:

- `KPI`
- `KPI Observation`
- `KPI Analysis`
- `Improvement Insight`

This gives the platform two connected loops.

### Loop 1: Learner Readiness

This is the standard LMS and readiness flow:

- role framework is defined
- competencies are attached to the role
- learning content and assessments are mapped to competencies
- employees complete learning and generate evidence
- readiness is computed from evidence against role requirements

### Loop 2: KPI-Driven Remediation and Platform Improvement

This is the newer performance loop:

- KPI observations are recorded for an employee
- weak KPI performance is detected
- the system links the weak KPI back to competencies
- the system recommends linked content and assessments for remediation
- repeated weak KPI patterns are aggregated for the LMS manager
- the LMS manager can see which KPI areas need better or new content

This second loop is what makes the platform continuously improving instead of only being a static course delivery system.

## What Has Been Built

### 1. Domain Model

The domain model currently includes:

- roles
- role competency requirements
- competencies
- learning assets
- assessments
- learning paths
- employees
- evidence records
- readiness reports
- KPIs
- KPI observations
- KPI recommendations
- weak KPI insight reports

These models are defined in [models.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/domain/models.py).

### 2. Backend Services

The service layer currently supports:

- creating competencies
- creating roles
- attaching competency requirements to roles
- creating learning assets
- creating assessments
- creating employees
- generating learning paths from role requirements
- recording evidence for employees
- evaluating readiness for a role
- creating KPIs
- recording KPI observations
- analyzing employee weak KPIs
- generating LMS manager weak-pattern reports

These services are implemented in [services.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/application/services.py).

### 3. Repository Layer

The current repository layer is in-memory only.

That means:

- data is stored in process memory
- restarting the service clears all created data
- there is no database yet
- there is no persistence, version history, or audit trail beyond runtime

This is implemented in [memory.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/repositories/memory.py).

### 4. HTTP API

The backend exposes a lightweight JSON API using the Python standard library HTTP server.

The current API supports:

- health check
- role management
- competency management
- learning asset creation
- assessment creation
- employee creation
- learning path generation and retrieval
- evidence capture
- readiness evaluation
- KPI creation
- KPI observation recording
- employee KPI analysis
- weak-KPI analytics for LMS managers
- dashboard summary
- demo data seeding

The HTTP layer is implemented in [http.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/api/http.py).

### 5. UI

A lightweight static UI has been added and is served directly by the backend.

The UI is not a production application. It is a first control-room style dashboard to make the current product model visible.

The UI currently shows:

- dashboard summary counts
- learner remediation view
- readiness summary for a selected employee
- LMS manager weak-KPI improvement view
- demo-data loading flow

UI files:

- [index.html](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/ui/index.html)
- [styles.css](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/ui/styles.css)
- [app.js](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/ui/app.js)

### 6. Entrypoint and Bootstrap

The application is wired through:

- [main.py](/Users/aryan.mangla/Desktop/LMS/main.py)
- [bootstrap.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/bootstrap.py)

`main.py` starts the local server and serves both API and UI.

## Current API Surface

The main endpoints currently available are:

- `GET /`
- `GET /health`
- `GET /roles`
- `POST /roles`
- `GET /competencies`
- `POST /competencies`
- `POST /roles/{role_id}/requirements`
- `GET /roles/{role_id}/learning-path`
- `POST /roles/{role_id}/learning-path/generate`
- `GET /assets`
- `POST /assets`
- `GET /assessments`
- `POST /assessments`
- `GET /employees`
- `POST /employees`
- `POST /employees/{employee_id}/evidence`
- `GET /employees/{employee_id}/readiness`
- `GET /kpis`
- `POST /kpis`
- `POST /employees/{employee_id}/kpi-observations`
- `GET /employees/{employee_id}/kpi-analysis`
- `GET /analytics/weak-kpis`
- `GET /dashboard/summary`
- `POST /demo/seed`

## Current Readiness Logic

The readiness model currently works like this:

- a role defines required competencies and required proficiency levels
- evidence is collected for each competency
- evidence is converted into an estimated achieved level
- coverage is measured against role requirements
- compliance score, competency coverage, and readiness score are returned

The readiness score is currently explainable but simple. It is enough for the first engine version, but it is not yet a production-grade talent evaluation model.

## Current KPI Logic

The KPI layer currently works like this:

- a KPI is linked to one or more competencies
- a KPI observation is recorded with `value` and `target_value`
- if the ratio falls below the KPI weak threshold, the KPI is marked weak
- weak KPIs generate learner remediation recommendations
- the system collects all weak observations and aggregates them into manager improvement insights

This supports both:

- targeted remediation for a learner
- content-improvement visibility for the LMS team

## What The UI Demonstrates

The UI currently demonstrates three important ideas:

### A. Role-Based Learning Is Not Enough

The system is not only showing assigned courses. It is showing how a role maps to competencies and how readiness is measured.

### B. KPI-Based Remediation Exists

When an employee has weak KPI performance, the system recommends the linked remediation path.

### C. The Platform Can Improve Itself

The LMS manager dashboard highlights KPI areas that remain weak across employees so learning content and assessments can be revised.

## Demo Data

A demo seed endpoint exists:

- `POST /demo/seed`

It creates:

- sample competencies
- a sample `Store Manager` role
- sample learning assets
- sample assessments
- sample KPIs
- sample employees
- sample evidence
- sample KPI observations

This makes it easy to inspect the UI without manually creating data first.

## What Is Not Built Yet

The following are not implemented yet:

- database persistence
- authentication and authorization
- employee/org sync from external systems
- real course enrollment records
- remediation assignment records
- content versioning
- role framework versioning
- practical evaluation workflow with real evaluator forms
- promotion workflow
- notifications and reminders
- audit logs
- reporting exports
- search and filtering
- production-grade frontend
- AI-assisted draft generation

## Known Limitations

The current implementation is intentionally early-stage.

Important limitations:

- all data is in memory only
- there is no user auth or role-based access control
- the UI is a static dashboard, not a complete application
- the readiness model is simplified
- KPI observations are manually recorded
- learning recommendations are linked by competency, not by advanced recommendation logic
- no relational database or migrations exist yet
- no deployment setup exists yet

## Recommended Next Steps

The most useful next build steps are:

### 1. Persistence

Add a real database and move repositories off in-memory storage.

This should include:

- employees
- roles
- competencies
- learning assets
- assessments
- evidence
- KPI observations
- readiness snapshots

### 2. Assignment and Remediation Workflow

The KPI analysis currently recommends content, but it does not yet create formal remediation assignments.

This should be upgraded so that:

- weak KPI analysis creates remediation assignments
- assignment completion is tracked
- reassessment is required after remediation

### 3. Auth and Access Control

Add user roles such as:

- learner
- manager
- evaluator
- LMS admin
- super admin

### 4. External Integrations

Integrate employee hierarchy and org structure from the source system instead of manually creating employees.

### 5. Better Readiness and Analytics

Improve:

- readiness scoring
- KPI trend tracking
- historical snapshots
- manager dashboards
- org and role filters

### 6. AI Layer

Later, AI can be added for:

- competency draft generation
- learning path draft generation
- quiz generation
- remediation recommendations
- weak-KPI insight summarization

## Current Summary

At this point, the project includes:

- a backend engine for role-readiness learning
- a working domain model around role, competency, and evidence
- a KPI-driven remediation layer
- an LMS-manager improvement analytics layer
- a basic but functional dashboard UI
- local tests validating the main readiness and KPI loops

This is a solid foundation for the next phase, but it is still an MVP scaffold and not yet a production service.
