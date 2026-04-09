"""Application bootstrap for wiring repositories and services."""

from __future__ import annotations

from dataclasses import dataclass

from lms_engine.application.services import (
    EvidenceService,
    KPIService,
    LearningCatalogService,
    LearningPathService,
    PeopleService,
    ReadinessService,
    RoleFrameworkService,
)
from lms_engine.domain.models import (
    Assessment,
    Competency,
    EmployeeProfile,
    EvidenceRecord,
    KPI,
    KPIObservation,
    LearningAsset,
    LearningPath,
    Role,
)
from lms_engine.repositories.memory import InMemoryRepository, LearningPathRepository


@dataclass
class AppContainer:
    role_framework: RoleFrameworkService
    learning_catalog: LearningCatalogService
    people: PeopleService
    learning_paths: LearningPathService
    evidence: EvidenceService
    kpis: KPIService
    readiness: ReadinessService


def build_container() -> AppContainer:
    role_repo: InMemoryRepository[Role] = InMemoryRepository()
    competency_repo: InMemoryRepository[Competency] = InMemoryRepository()
    asset_repo: InMemoryRepository[LearningAsset] = InMemoryRepository()
    assessment_repo: InMemoryRepository[Assessment] = InMemoryRepository()
    employee_repo: InMemoryRepository[EmployeeProfile] = InMemoryRepository()
    evidence_repo: InMemoryRepository[EvidenceRecord] = InMemoryRepository()
    kpi_repo: InMemoryRepository[KPI] = InMemoryRepository()
    observation_repo: InMemoryRepository[KPIObservation] = InMemoryRepository()
    learning_path_repo: LearningPathRepository[LearningPath] = LearningPathRepository()

    role_framework = RoleFrameworkService(role_repo=role_repo, competency_repo=competency_repo)
    learning_catalog = LearningCatalogService(
        competency_repo=competency_repo,
        asset_repo=asset_repo,
        assessment_repo=assessment_repo,
    )
    people = PeopleService(employee_repo=employee_repo, role_repo=role_repo)
    evidence = EvidenceService(
        employee_repo=employee_repo,
        competency_repo=competency_repo,
        evidence_repo=evidence_repo,
    )
    kpis = KPIService(
        employee_repo=employee_repo,
        competency_repo=competency_repo,
        kpi_repo=kpi_repo,
        observation_repo=observation_repo,
        catalog_service=learning_catalog,
    )
    learning_paths = LearningPathService(
        role_service=role_framework,
        competency_repo=competency_repo,
        catalog_service=learning_catalog,
        learning_path_repo=learning_path_repo,
    )
    readiness = ReadinessService(
        people_service=people,
        role_service=role_framework,
        competency_repo=competency_repo,
        evidence_service=evidence,
    )

    return AppContainer(
        role_framework=role_framework,
        learning_catalog=learning_catalog,
        people=people,
        learning_paths=learning_paths,
        evidence=evidence,
        kpis=kpis,
        readiness=readiness,
    )
