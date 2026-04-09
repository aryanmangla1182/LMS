# LMS Engine Backend Architecture

## 1. Objective

This backend exists to power a role-readiness learning platform for Cultfit.

It is not designed as a generic content LMS where the primary output is course completion. It is designed as an engine that helps answer four backend questions for each employee:

- what role does this employee currently hold
- what competencies does that role require
- what evidence exists that those competencies are present
- what KPI weakness should trigger additional learning or content improvement

The backend therefore has two responsibilities:

1. run the standard learning and readiness loop
2. run the KPI-driven remediation and continuous-improvement loop

## 2. Product-to-Backend Translation

The product model has been translated into the backend around these first-class concepts:

- `Role`
- `Competency`
- `Evidence`

These are the core backbone entities.

On top of them, the backend adds a performance feedback layer:

- `KPI`
- `KPIObservation`
- `KPIAnalysis`
- `ImprovementInsightReport`

This means the backend is not only storing content and assessments. It is trying to model business capability.

## 3. Architecture Style

The current implementation is a modular monolith.

That choice is intentional for this stage because:

- the domain is still evolving
- workflows are tightly connected
- the current service benefits more from clear boundaries than from microservice separation
- consistency is more important than independent deployment right now

The code is divided into these layers:

- `domain`
- `repositories`
- `application`
- `api`
- `ui`

Even though the current persistence is in-memory, the code has already been separated so the database implementation can later replace the repository layer without rewriting the business logic.

## 4. Runtime Layout

The main runtime flow is:

1. `main.py` starts the process
2. `bootstrap.py` creates repositories and wires services
3. `http.py` exposes routes and dispatches requests
4. application services execute business rules
5. repositories read/write state
6. the response is serialized to JSON

Relevant files:

- [main.py](/Users/aryan.mangla/Desktop/LMS/main.py)
- [bootstrap.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/bootstrap.py)
- [http.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/api/http.py)
- [services.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/application/services.py)
- [models.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/domain/models.py)
- [memory.py](/Users/aryan.mangla/Desktop/LMS/src/lms_engine/repositories/memory.py)

## 5. Layer Breakdown

### 5.1 Domain Layer

The domain layer defines the business objects and enums used across the service.

It currently includes:

- content types
- assessment types
- evidence types
- KPI status values
- competency entities
- role entities and competency requirements
- learning assets
- assessments
- learning paths and learning path items
- employee profiles
- evidence records
- readiness reports and readiness gaps
- KPI definitions
- KPI observations
- KPI recommendations
- weak KPI insights

The domain layer contains no HTTP logic and no storage logic. It only models business concepts.

### 5.2 Repository Layer

The repository layer currently uses generic in-memory collections.

Current behavior:

- each repository stores records in a dictionary keyed by id
- data exists only while the process is running
- there are no transactions
- there is no durability

This is intentionally simple because the current goal is to validate the domain model before locking in database design.

### 5.3 Application Layer

The application layer contains business workflows and orchestration.

Current services:

- `RoleFrameworkService`
- `LearningCatalogService`
- `PeopleService`
- `LearningPathService`
- `EvidenceService`
- `KPIService`
- `ReadinessService`

This layer is the real backend core. It is where domain rules are applied.

### 5.4 API Layer

The API layer currently uses the Python standard library HTTP server.

Responsibilities:

- accept JSON requests
- route them to application services
- handle validation and not-found errors
- serialize dataclasses and enums to JSON
- serve the static UI files

This layer is intentionally thin. All decision-making happens in services, not in route handlers.

### 5.5 UI Layer

The UI is not the product target, but it is still part of the current backend package because:

- it demonstrates the engine behavior
- it helps inspect live data
- it proves the API is usable end-to-end

The UI is a static dashboard served directly by the backend.

## 6. Core Domain Model

### 6.1 Role

`Role` is the business anchor for learning.

Current fields include:

- name
- description
- responsibilities
- growth outcomes
- next role ids
- competency requirements
- framework version

Why this matters:

- learning is role-specific, not generic
- readiness is evaluated against role requirements
- future progression can later be built from role ladders

### 6.2 Competency

`Competency` describes what the employee must be able to do.

Current fields include:

- name
- description
- category
- proficiency scale max

Competencies are the bridge between:

- roles
- learning assets
- assessments
- evidence
- KPIs

This is why they are central to the backend.

### 6.3 RoleRequirement

`RoleRequirement` links a role to a competency.

Current fields:

- `competency_id`
- `required_level`
- `mandatory`
- `weight`

This lets the backend express:

- which skills are mandatory
- how strong those skills must be
- how much each requirement should influence readiness

### 6.4 LearningAsset

`LearningAsset` models role-supporting content.

Examples:

- video
- document
- SOP
- microlearning

Key point:

learning assets are not primary business objects by themselves. They exist to support one or more competencies.

### 6.5 Assessment

`Assessment` models a validation mechanism for competencies.

Examples:

- quiz
- scenario test
- practical assessment
- certification

An assessment creates measurable evidence. It is therefore more important than content alone in this system.

### 6.6 LearningPath

`LearningPath` is currently a generated role-level structure.

Each item in the path includes:

- the competency being targeted
- the required level
- whether it is mandatory
- linked learning assets
- linked assessments

This lets the backend produce a role-focused path even though the current system does not yet persist formal enrollments.

### 6.7 EmployeeProfile

`EmployeeProfile` stores learner identity in the LMS context.

Current fields:

- name
- email
- current role id
- org unit
- manager id

This is minimal and intentionally not yet an HR master model.

### 6.8 EvidenceRecord

`EvidenceRecord` is the proof layer.

Evidence types currently include:

- quiz attempt
- practical evaluation
- manager signoff
- course completion
- manual

This is one of the most important backend objects because readiness is calculated from evidence, not from content assignment alone.

### 6.9 KPI and KPIObservation

`KPI` links business performance back to competencies.

Current KPI fields:

- name
- description
- linked competency ids
- weak threshold

`KPIObservation` captures:

- employee
- KPI
- current value
- target value
- period label
- weak or healthy status

This is what enables the backend to say:

- the employee completed the course
- but business performance is still weak
- so assign more targeted learning or revise the content system

### 6.10 KPIAnalysis and ImprovementInsightReport

`KPIAnalysis` is employee-specific.

It answers:

- which KPIs are weak
- which competencies are implicated
- which assets and assessments should be used as remediation

`ImprovementInsightReport` is LMS-manager-specific.

It answers:

- which KPI areas stay weak across the org
- how many employees are affected
- whether the content and assessment coverage around those KPIs is thin

## 7. Service Responsibilities

### 7.1 RoleFrameworkService

Responsibilities:

- create competencies
- list competencies
- create roles
- list roles
- fetch a role
- add or update competency requirements on a role

This service owns the role framework.

### 7.2 LearningCatalogService

Responsibilities:

- create assets
- create assessments
- list assets
- list assessments
- list assets for a competency
- list assessments for a competency

This service owns the learning catalog and competency linkage.

### 7.3 PeopleService

Responsibilities:

- create employees
- fetch one employee
- list employees

This is intentionally narrow right now.

### 7.4 LearningPathService

Responsibilities:

- generate a role learning path from competency requirements
- fetch the learning path for a role

Generation logic currently works by:

- reading all competency requirements on the role
- resolving linked assets and linked assessments for each competency
- building path items around that relationship

### 7.5 EvidenceService

Responsibilities:

- record evidence for an employee against a competency
- list evidence for an employee

This service does not yet validate against assignment or assessment attempt history. That is a later-phase capability.

### 7.6 ReadinessService

Responsibilities:

- evaluate readiness for the current role or a target role

The service currently:

- loads the employee
- loads the target role
- groups successful evidence by competency
- estimates achieved level from the best available evidence
- compares achieved level with required level
- computes compliance score
- computes competency coverage
- computes a weighted readiness score
- returns gap objects for unmet competencies

This is a transparent scoring model, which is useful at the current stage because it is easy to explain and debug.

### 7.7 KPIService

Responsibilities:

- create KPI definitions
- list KPIs
- record KPI observations
- analyze a specific employee’s weak KPIs
- generate weak KPI improvement reports for LMS managers

This service is the key differentiator relative to a simple LMS backend.

## 8. Data Flow by Use Case

### 8.1 Role Setup Flow

1. admin creates a competency
2. admin creates a role
3. admin attaches competency requirements to the role
4. admin creates assets and assessments linked to competencies
5. learning path is generated for the role

Output:

- a role framework with attached learning support

### 8.2 Learner Readiness Flow

1. employee is created with a current role
2. evidence is recorded against competencies
3. readiness is evaluated
4. the backend returns:
   - compliance score
   - competency coverage
   - readiness score
   - gaps

Output:

- an explainable readiness report

### 8.3 KPI Remediation Flow

1. KPI is defined and linked to competencies
2. KPI observation is recorded for an employee
3. if observation ratio is below threshold, the observation is weak
4. employee analysis fetches all latest weak KPI observations
5. service resolves the linked competencies
6. service resolves the linked assets and assessments
7. backend returns remediation recommendations

Output:

- personalized learning suggestions driven by business weakness

### 8.4 LMS Manager Improvement Flow

1. system scans all weak KPI observations
2. observations are grouped by KPI
3. affected employee counts are calculated
4. linked assets and assessment coverage are calculated
5. action summary is generated

Output:

- a ranked report of weak business areas and likely content gaps

## 9. Readiness Logic

The current readiness model is intentionally simple and explainable.

For each role requirement:

- find all successful evidence linked to the competency
- estimate the achieved proficiency level
- compare achieved level to required level
- count coverage
- contribute weighted score

Current achieved-level logic:

- if scored evidence exists, convert score ratio to a level on a 5-point scale
- if non-scored successful evidence exists, treat it as full level
- use the best evidence observed for that competency

Current outputs:

- `compliance_score`
- `competency_coverage`
- `readiness_score`
- `ready`
- `gaps`

Important caveat:

this is not yet a production-grade readiness model because it does not yet handle:

- evidence recency decay
- repeated failures
- assessor reliability
- manager overrides
- minimum evidence count rules
- target-role promotion workflow

## 10. KPI Logic

The KPI engine currently uses a threshold model.

For each KPI observation:

- compute `value / target_value`
- compare against the KPI weak threshold
- mark the observation `weak` or `healthy`

When a KPI is weak:

- employee analysis uses linked competencies to find related learning assets and assessments
- manager analysis uses aggregated weak counts to identify weak content domains

Current strengths:

- simple to reason about
- easy to demo
- aligned with operational business metrics

Current limitations:

- no trend analysis yet
- no time-series persistence
- no multi-period scoring model
- no role-specific KPI thresholds
- no automated remediation assignment

## 11. Current API Design

The API is route-oriented and intentionally small.

### 11.1 Framework Endpoints

- `GET /roles`
- `POST /roles`
- `GET /competencies`
- `POST /competencies`
- `POST /roles/{role_id}/requirements`

### 11.2 Catalog Endpoints

- `GET /assets`
- `POST /assets`
- `GET /assessments`
- `POST /assessments`

### 11.3 Learning Path Endpoints

- `GET /roles/{role_id}/learning-path`
- `POST /roles/{role_id}/learning-path/generate`

### 11.4 People and Evidence Endpoints

- `GET /employees`
- `POST /employees`
- `POST /employees/{employee_id}/evidence`
- `GET /employees/{employee_id}/readiness`

### 11.5 KPI Endpoints

- `GET /kpis`
- `POST /kpis`
- `POST /employees/{employee_id}/kpi-observations`
- `GET /employees/{employee_id}/kpi-analysis`
- `GET /analytics/weak-kpis`

### 11.6 Utility Endpoints

- `GET /health`
- `GET /dashboard/summary`
- `POST /demo/seed`
- `GET /`

The current API style is sufficient for local development and product validation. It should later be migrated to a framework with stronger validation, middleware, and auth support.

## 12. Bootstrapping and Dependency Wiring

`bootstrap.py` is responsible for constructing the backend container.

It currently:

- creates repositories
- creates services
- injects repositories into services
- injects cross-service dependencies where needed
- returns a single `AppContainer`

This is a good current pattern because:

- service wiring is explicit
- dependencies are visible
- there is a single place to replace repository implementations later

## 13. UI-to-Backend Contract

The current UI consumes the backend like a thin API client.

It calls:

- `/dashboard/summary`
- `/employees`
- `/analytics/weak-kpis`
- `/employees/{employee_id}/kpi-analysis`
- `/employees/{employee_id}/readiness`
- `/demo/seed`

This is useful because it proves:

- the backend contract is usable by a frontend
- the current service boundaries are already visible in product terms

## 14. Testing Strategy

There are currently unit-style integration tests in:

- [test_engine.py](/Users/aryan.mangla/Desktop/LMS/tests/test_engine.py)

The tests currently cover:

- role framework setup
- learning path generation
- readiness scoring
- KPI-driven remediation
- manager weak-pattern analytics

This is enough for the current scaffold, but not enough for a production backend.

Missing test coverage includes:

- route-level HTTP tests
- invalid payload and validation cases
- missing entity paths
- seed behavior
- UI contract tests
- persistence tests

## 15. Known Gaps in the Current Backend

The backend is functional but still early-stage.

Major gaps:

- no persistent database
- no migrations
- no auth
- no RBAC
- no organization hierarchy sync
- no assignment model
- no remediation assignment workflow
- no notifications
- no audit logging
- no content versioning
- no framework version history beyond a simple field
- no asynchronous jobs
- no scheduler
- no analytics warehouse
- no file storage integration

These are normal gaps for the current stage, but they matter if this moves toward production.

## 16. Recommended Next Backend Milestones

### 16.1 Persistence Layer

Replace in-memory repositories with database-backed repositories.

Suggested first persisted tables:

- roles
- competencies
- role_requirements
- learning_assets
- assessments
- employees
- evidence_records
- kpis
- kpi_observations
- learning_paths

### 16.2 Assignment Model

Introduce:

- course assignments
- remediation assignments
- due dates
- assignment status
- reassessment status

Right now the backend can recommend remediation, but it cannot yet formally assign or track it.

### 16.3 Auth and Access Control

Add clear backend roles:

- learner
- manager
- evaluator
- LMS admin
- super admin

Then secure the route layer accordingly.

### 16.4 Org and Hierarchy Model

Integrate employee and reporting hierarchy from source systems.

Future entities likely needed:

- org unit
- location
- city
- cluster
- reporting manager chain

### 16.5 Readiness V2

Upgrade the readiness model to include:

- stronger evidence rules
- recency handling
- target-role comparisons
- promotion readiness evidence
- manager validation workflow

### 16.6 KPI and Analytics V2

Upgrade the KPI engine to include:

- trend history
- period comparisons
- threshold configuration per role or org unit
- cohort analysis
- recurring remediation effectiveness

### 16.7 AI Layer

Later, AI can be added as a draft-generation and insight layer for:

- role-to-competency drafting
- learning path generation
- assessment drafting
- recommendation summarization
- weak-KPI insight summarization

AI should remain assistive, not authoritative, in this backend.

## 17. Summary

The backend that exists today is a clean first engine for:

- role-based learning
- competency-linked content and assessments
- evidence-driven readiness
- KPI-driven remediation
- LMS-manager continuous improvement insight

The current architecture is appropriate for the stage:

- simple enough to move fast
- structured enough to grow
- separated enough to evolve into a more serious service

The next important step is not adding more surface area. It is making the current model durable through persistence, assignments, auth, and stronger readiness/KPI logic.
