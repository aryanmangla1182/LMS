"""Application services for the LMS engine."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from lms_engine.domain.models import (
    Assessment,
    AssessmentType,
    Competency,
    ContentType,
    EmployeeProfile,
    EvidenceRecord,
    EvidenceType,
    ImprovementInsightReport,
    KPI,
    KPIAnalysis,
    KPIObservation,
    KPIRecommendation,
    KPIStatus,
    LearningAsset,
    LearningPath,
    LearningPathItem,
    ReadinessGap,
    ReadinessReport,
    Role,
    RoleRequirement,
    WeakKPIInsight,
)
from lms_engine.repositories.memory import InMemoryRepository, LearningPathRepository


SUCCESS_STATUSES = {"completed", "passed", "verified"}


class LMSValidationError(ValueError):
    """Raised when incoming data is invalid for the domain."""


class NotFoundError(LookupError):
    """Raised when a required record is missing."""


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


class RoleFrameworkService:
    def __init__(
        self,
        role_repo: InMemoryRepository[Role],
        competency_repo: InMemoryRepository[Competency],
    ) -> None:
        self.role_repo = role_repo
        self.competency_repo = competency_repo

    def create_competency(self, payload: Dict[str, Any]) -> Competency:
        competency = Competency(
            name=payload["name"].strip(),
            description=payload["description"].strip(),
            category=payload.get("category", "general").strip(),
            proficiency_scale_max=int(payload.get("proficiency_scale_max", 5)),
        )
        return self.competency_repo.add(competency)

    def list_competencies(self) -> List[Competency]:
        return self.competency_repo.list()

    def create_role(self, payload: Dict[str, Any]) -> Role:
        role = Role(
            name=payload["name"].strip(),
            description=payload["description"].strip(),
            responsibilities=[item.strip() for item in payload.get("responsibilities", [])],
            growth_outcomes=[item.strip() for item in payload.get("growth_outcomes", [])],
            next_role_ids=payload.get("next_role_ids", []),
        )
        return self.role_repo.add(role)

    def list_roles(self) -> List[Role]:
        return self.role_repo.list()

    def get_role(self, role_id: str) -> Role:
        role = self.role_repo.get(role_id)
        if role is None:
            raise NotFoundError("Role not found: {0}".format(role_id))
        return role

    def add_requirement(self, role_id: str, payload: Dict[str, Any]) -> Role:
        role = self.get_role(role_id)
        competency_id = payload["competency_id"]
        competency = self.competency_repo.get(competency_id)
        if competency is None:
            raise NotFoundError("Competency not found: {0}".format(competency_id))

        required_level = int(payload["required_level"])
        if required_level < 1 or required_level > competency.proficiency_scale_max:
            raise LMSValidationError(
                "required_level must be between 1 and {0}".format(competency.proficiency_scale_max)
            )

        existing = [item for item in role.competency_requirements if item.competency_id == competency_id]
        if existing:
            existing[0].required_level = required_level
            existing[0].mandatory = bool(payload.get("mandatory", True))
            existing[0].weight = float(payload.get("weight", 1.0))
        else:
            role.competency_requirements.append(
                RoleRequirement(
                    competency_id=competency_id,
                    required_level=required_level,
                    mandatory=bool(payload.get("mandatory", True)),
                    weight=float(payload.get("weight", 1.0)),
                )
            )
        return role


class LearningCatalogService:
    def __init__(
        self,
        competency_repo: InMemoryRepository[Competency],
        asset_repo: InMemoryRepository[LearningAsset],
        assessment_repo: InMemoryRepository[Assessment],
    ) -> None:
        self.competency_repo = competency_repo
        self.asset_repo = asset_repo
        self.assessment_repo = assessment_repo

    def create_asset(self, payload: Dict[str, Any]) -> LearningAsset:
        competency_ids = payload.get("competency_ids", [])
        self._ensure_competencies_exist(competency_ids)

        asset = LearningAsset(
            title=payload["title"].strip(),
            summary=payload["summary"].strip(),
            content_type=ContentType(payload["content_type"]),
            competency_ids=competency_ids,
            estimated_minutes=int(payload.get("estimated_minutes", 0)),
            url=payload.get("url"),
        )
        return self.asset_repo.add(asset)

    def create_assessment(self, payload: Dict[str, Any]) -> Assessment:
        competency_ids = payload.get("competency_ids", [])
        self._ensure_competencies_exist(competency_ids)

        max_score = float(payload.get("max_score", 100))
        passing_score = float(payload.get("passing_score", max_score))
        if passing_score > max_score:
            raise LMSValidationError("passing_score cannot be greater than max_score")

        assessment = Assessment(
            title=payload["title"].strip(),
            assessment_type=AssessmentType(payload["assessment_type"]),
            competency_ids=competency_ids,
            passing_score=passing_score,
            max_score=max_score,
            instructions=payload.get("instructions", "").strip(),
        )
        return self.assessment_repo.add(assessment)

    def list_assets(self) -> List[LearningAsset]:
        return self.asset_repo.list()

    def list_assessments(self) -> List[Assessment]:
        return self.assessment_repo.list()

    def list_assets_for_competency(self, competency_id: str) -> List[LearningAsset]:
        return [asset for asset in self.asset_repo.all() if competency_id in asset.competency_ids]

    def list_assessments_for_competency(self, competency_id: str) -> List[Assessment]:
        return [assessment for assessment in self.assessment_repo.all() if competency_id in assessment.competency_ids]

    def _ensure_competencies_exist(self, competency_ids: List[str]) -> None:
        for competency_id in competency_ids:
            if self.competency_repo.get(competency_id) is None:
                raise NotFoundError("Competency not found: {0}".format(competency_id))


class PeopleService:
    def __init__(
        self,
        employee_repo: InMemoryRepository[EmployeeProfile],
        role_repo: InMemoryRepository[Role],
    ) -> None:
        self.employee_repo = employee_repo
        self.role_repo = role_repo

    def create_employee(self, payload: Dict[str, Any]) -> EmployeeProfile:
        role_id = payload["current_role_id"]
        if self.role_repo.get(role_id) is None:
            raise NotFoundError("Role not found: {0}".format(role_id))

        employee = EmployeeProfile(
            name=payload["name"].strip(),
            email=payload["email"].strip(),
            current_role_id=role_id,
            org_unit=payload.get("org_unit", "unassigned").strip(),
            manager_id=payload.get("manager_id"),
        )
        return self.employee_repo.add(employee)

    def get_employee(self, employee_id: str) -> EmployeeProfile:
        employee = self.employee_repo.get(employee_id)
        if employee is None:
            raise NotFoundError("Employee not found: {0}".format(employee_id))
        return employee

    def list_employees(self) -> List[EmployeeProfile]:
        return self.employee_repo.list()


class LearningPathService:
    def __init__(
        self,
        role_service: RoleFrameworkService,
        competency_repo: InMemoryRepository[Competency],
        catalog_service: LearningCatalogService,
        learning_path_repo: LearningPathRepository[LearningPath],
    ) -> None:
        self.role_service = role_service
        self.competency_repo = competency_repo
        self.catalog_service = catalog_service
        self.learning_path_repo = learning_path_repo

    def generate_for_role(self, role_id: str) -> LearningPath:
        role = self.role_service.get_role(role_id)
        items: List[LearningPathItem] = []

        for requirement in role.competency_requirements:
            competency = self.competency_repo.get(requirement.competency_id)
            if competency is None:
                raise NotFoundError("Competency not found: {0}".format(requirement.competency_id))

            assets = self.catalog_service.list_assets_for_competency(competency.id)
            assessments = self.catalog_service.list_assessments_for_competency(competency.id)
            notes = ""
            if not assets:
                notes = "No learning asset linked to this competency yet."
            if not assessments:
                notes = "{0} No assessment linked yet.".format(notes).strip()

            items.append(
                LearningPathItem(
                    competency_id=competency.id,
                    required_level=requirement.required_level,
                    mandatory=requirement.mandatory,
                    asset_ids=[asset.id for asset in assets],
                    assessment_ids=[assessment.id for assessment in assessments],
                    notes=notes,
                )
            )

        learning_path = LearningPath(
            role_id=role.id,
            version=role.framework_version,
            items=items,
        )
        self.learning_path_repo.add(learning_path)
        return learning_path

    def get_for_role(self, role_id: str) -> LearningPath:
        learning_path = self.learning_path_repo.get_by_role(role_id)
        if learning_path is None:
            raise NotFoundError("Learning path not found for role: {0}".format(role_id))
        return learning_path


class EvidenceService:
    def __init__(
        self,
        employee_repo: InMemoryRepository[EmployeeProfile],
        competency_repo: InMemoryRepository[Competency],
        evidence_repo: InMemoryRepository[EvidenceRecord],
    ) -> None:
        self.employee_repo = employee_repo
        self.competency_repo = competency_repo
        self.evidence_repo = evidence_repo

    def record_evidence(self, employee_id: str, payload: Dict[str, Any]) -> EvidenceRecord:
        if self.employee_repo.get(employee_id) is None:
            raise NotFoundError("Employee not found: {0}".format(employee_id))

        competency_id = payload["competency_id"]
        if self.competency_repo.get(competency_id) is None:
            raise NotFoundError("Competency not found: {0}".format(competency_id))

        evidence = EvidenceRecord(
            employee_id=employee_id,
            competency_id=competency_id,
            evidence_type=EvidenceType(payload["evidence_type"]),
            status=payload.get("status", "completed"),
            score=float(payload.get("score", 0.0)),
            max_score=float(payload.get("max_score", 0.0)),
            source_id=payload.get("source_id"),
            notes=payload.get("notes", "").strip(),
            reviewer_id=payload.get("reviewer_id"),
        )
        return self.evidence_repo.add(evidence)

    def list_employee_evidence(self, employee_id: str) -> List[EvidenceRecord]:
        return [item for item in self.evidence_repo.all() if item.employee_id == employee_id]


class KPIService:
    def __init__(
        self,
        employee_repo: InMemoryRepository[EmployeeProfile],
        competency_repo: InMemoryRepository[Competency],
        kpi_repo: InMemoryRepository[KPI],
        observation_repo: InMemoryRepository[KPIObservation],
        catalog_service: LearningCatalogService,
    ) -> None:
        self.employee_repo = employee_repo
        self.competency_repo = competency_repo
        self.kpi_repo = kpi_repo
        self.observation_repo = observation_repo
        self.catalog_service = catalog_service

    def create_kpi(self, payload: Dict[str, Any]) -> KPI:
        competency_ids = payload.get("competency_ids", [])
        for competency_id in competency_ids:
            if self.competency_repo.get(competency_id) is None:
                raise NotFoundError("Competency not found: {0}".format(competency_id))

        weak_threshold = float(payload.get("weak_threshold", 0.8))
        if weak_threshold <= 0:
            raise LMSValidationError("weak_threshold must be greater than 0")

        kpi = KPI(
            name=payload["name"].strip(),
            description=payload["description"].strip(),
            competency_ids=competency_ids,
            weak_threshold=weak_threshold,
        )
        return self.kpi_repo.add(kpi)

    def list_kpis(self) -> List[KPI]:
        return self.kpi_repo.list()

    def record_observation(self, employee_id: str, payload: Dict[str, Any]) -> KPIObservation:
        if self.employee_repo.get(employee_id) is None:
            raise NotFoundError("Employee not found: {0}".format(employee_id))

        kpi_id = payload["kpi_id"]
        kpi = self.kpi_repo.get(kpi_id)
        if kpi is None:
            raise NotFoundError("KPI not found: {0}".format(kpi_id))

        value = float(payload["value"])
        target_value = float(payload["target_value"])
        if target_value <= 0:
            raise LMSValidationError("target_value must be greater than 0")

        status = KPIStatus.WEAK if (value / target_value) < kpi.weak_threshold else KPIStatus.HEALTHY
        observation = KPIObservation(
            employee_id=employee_id,
            kpi_id=kpi.id,
            value=value,
            target_value=target_value,
            period_label=payload.get("period_label", "current").strip(),
            status=status,
            notes=payload.get("notes", "").strip(),
        )
        return self.observation_repo.add(observation)

    def list_employee_observations(self, employee_id: str) -> List[KPIObservation]:
        return [item for item in self.observation_repo.all() if item.employee_id == employee_id]

    def analyze_employee(self, employee_id: str) -> KPIAnalysis:
        if self.employee_repo.get(employee_id) is None:
            raise NotFoundError("Employee not found: {0}".format(employee_id))

        latest_by_kpi: Dict[str, KPIObservation] = {}
        for observation in self.list_employee_observations(employee_id):
            previous = latest_by_kpi.get(observation.kpi_id)
            if previous is None or observation.observed_at > previous.observed_at:
                latest_by_kpi[observation.kpi_id] = observation

        recommendations: List[KPIRecommendation] = []
        for observation in latest_by_kpi.values():
            if observation.status != KPIStatus.WEAK:
                continue

            kpi = self.kpi_repo.get(observation.kpi_id)
            if kpi is None:
                continue

            asset_ids: List[str] = []
            assessment_ids: List[str] = []
            for competency_id in kpi.competency_ids:
                asset_ids.extend(asset.id for asset in self.catalog_service.list_assets_for_competency(competency_id))
                assessment_ids.extend(
                    assessment.id
                    for assessment in self.catalog_service.list_assessments_for_competency(competency_id)
                )

            recommendations.append(
                KPIRecommendation(
                    kpi_id=kpi.id,
                    kpi_name=kpi.name,
                    gap_to_target=round(observation.target_value - observation.value, 2),
                    competency_ids=kpi.competency_ids,
                    asset_ids=sorted(set(asset_ids)),
                    assessment_ids=sorted(set(assessment_ids)),
                    action_summary=self._build_action_summary(kpi.name, asset_ids, assessment_ids),
                )
            )

        recommendations.sort(key=lambda item: item.gap_to_target, reverse=True)
        return KPIAnalysis(employee_id=employee_id, weak_kpis=recommendations)

    def manager_improvement_report(self) -> ImprovementInsightReport:
        observation_groups: Dict[str, List[KPIObservation]] = {}
        for observation in self.observation_repo.all():
            if observation.status != KPIStatus.WEAK:
                continue
            observation_groups.setdefault(observation.kpi_id, []).append(observation)

        insights: List[WeakKPIInsight] = []
        for kpi_id, observations in observation_groups.items():
            kpi = self.kpi_repo.get(kpi_id)
            if kpi is None:
                continue

            asset_ids: List[str] = []
            assessment_ids: List[str] = []
            for competency_id in kpi.competency_ids:
                asset_ids.extend(asset.id for asset in self.catalog_service.list_assets_for_competency(competency_id))
                assessment_ids.extend(
                    assessment.id
                    for assessment in self.catalog_service.list_assessments_for_competency(competency_id)
                )

            linked_asset_count = len(set(asset_ids))
            linked_assessment_count = len(set(assessment_ids))
            if linked_asset_count == 0 and linked_assessment_count == 0:
                action_summary = "Build new remediation content and assessment for this KPI."
            elif linked_asset_count == 0:
                action_summary = "Add targeted learning content. Assessment exists but remediation is thin."
            elif linked_assessment_count == 0:
                action_summary = "Add validation for this KPI. Content exists but proof is weak."
            else:
                action_summary = "Review linked content quality and iterate where outcomes stay weak."

            insights.append(
                WeakKPIInsight(
                    kpi_id=kpi.id,
                    kpi_name=kpi.name,
                    weak_observation_count=len(observations),
                    affected_employee_count=len({item.employee_id for item in observations}),
                    linked_competency_ids=kpi.competency_ids,
                    linked_asset_count=linked_asset_count,
                    linked_assessment_count=linked_assessment_count,
                    action_summary=action_summary,
                )
            )

        insights.sort(
            key=lambda item: (item.weak_observation_count, item.affected_employee_count),
            reverse=True,
        )
        return ImprovementInsightReport(weak_kpis=insights)

    @staticmethod
    def _build_action_summary(kpi_name: str, asset_ids: List[str], assessment_ids: List[str]) -> str:
        if asset_ids and assessment_ids:
            return "KPI '{0}' is weak. Assign remediation content and retest.".format(kpi_name)
        if asset_ids:
            return "KPI '{0}' is weak. Assign linked content and add an assessment.".format(kpi_name)
        if assessment_ids:
            return "KPI '{0}' is weak. Retest now and create supporting content.".format(kpi_name)
        return "KPI '{0}' is weak. No remediation path exists yet.".format(kpi_name)


class ReadinessService:
    def __init__(
        self,
        people_service: PeopleService,
        role_service: RoleFrameworkService,
        competency_repo: InMemoryRepository[Competency],
        evidence_service: EvidenceService,
    ) -> None:
        self.people_service = people_service
        self.role_service = role_service
        self.competency_repo = competency_repo
        self.evidence_service = evidence_service

    def evaluate(self, employee_id: str, target_role_id: Optional[str] = None) -> ReadinessReport:
        employee = self.people_service.get_employee(employee_id)
        role = self.role_service.get_role(target_role_id or employee.current_role_id)
        evidence = self.evidence_service.list_employee_evidence(employee_id)
        gaps: List[ReadinessGap] = []

        if not role.competency_requirements:
            return ReadinessReport(
                employee_id=employee.id,
                current_role_id=employee.current_role_id,
                target_role_id=role.id,
                compliance_score=0.0,
                competency_coverage=0.0,
                readiness_score=0.0,
                ready=False,
                gaps=[],
            )

        mandatory_requirements = [item for item in role.competency_requirements if item.mandatory]
        covered_requirements = 0
        mandatory_covered = 0
        weighted_total = 0.0
        weighted_score = 0.0

        for requirement in role.competency_requirements:
            competency = self.competency_repo.get(requirement.competency_id)
            competency_name = competency.name if competency else requirement.competency_id
            related_evidence = [
                item
                for item in evidence
                if item.competency_id == requirement.competency_id and item.status in SUCCESS_STATUSES
            ]

            achieved_level = self._estimate_level(related_evidence)
            if achieved_level >= requirement.required_level:
                covered_requirements += 1
                if requirement.mandatory:
                    mandatory_covered += 1
            else:
                gaps.append(
                    ReadinessGap(
                        competency_id=requirement.competency_id,
                        competency_name=competency_name,
                        required_level=requirement.required_level,
                        achieved_level=achieved_level,
                        evidence_count=len(related_evidence),
                        mandatory=requirement.mandatory,
                    )
                )

            weighted_total += requirement.weight
            weighted_score += min(achieved_level / float(requirement.required_level), 1.0) * requirement.weight

        compliance_score = (
            round((mandatory_covered / float(len(mandatory_requirements))) * 100, 2) if mandatory_requirements else 100.0
        )
        competency_coverage = round((covered_requirements / float(len(role.competency_requirements))) * 100, 2)
        readiness_score = round((weighted_score / weighted_total) * 100, 2) if weighted_total else 0.0
        ready = compliance_score == 100.0 and readiness_score >= 80.0

        return ReadinessReport(
            employee_id=employee.id,
            current_role_id=employee.current_role_id,
            target_role_id=role.id,
            compliance_score=compliance_score,
            competency_coverage=competency_coverage,
            readiness_score=readiness_score,
            ready=ready,
            gaps=gaps,
        )

    @staticmethod
    def _estimate_level(evidence: List[EvidenceRecord]) -> float:
        if not evidence:
            return 0.0

        best_level = 0.0
        for item in evidence:
            if item.max_score > 0:
                level = min((item.score / item.max_score) * 5.0, 5.0)
            elif item.status in SUCCESS_STATUSES:
                level = 5.0
            else:
                level = 0.0
            if level > best_level:
                best_level = level
        return round(best_level, 2)
