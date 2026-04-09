"""Core domain models for the LMS engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_id(prefix: str) -> str:
    return "{0}_{1}".format(prefix, uuid4().hex[:12])


class ContentType(str, Enum):
    VIDEO = "video"
    DOCUMENT = "document"
    SOP = "sop"
    MICROLEARNING = "microlearning"


class AssessmentType(str, Enum):
    QUIZ = "quiz"
    SCENARIO = "scenario"
    PRACTICAL = "practical"
    CERTIFICATION = "certification"


class EvidenceType(str, Enum):
    QUIZ_ATTEMPT = "quiz_attempt"
    PRACTICAL_EVALUATION = "practical_evaluation"
    MANAGER_SIGNOFF = "manager_signoff"
    COURSE_COMPLETION = "course_completion"
    MANUAL = "manual"


class KPIStatus(str, Enum):
    HEALTHY = "healthy"
    WEAK = "weak"


class KPIStudioStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"


class VideoVersionStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVED = "approved"


@dataclass
class Competency:
    name: str
    description: str
    category: str
    proficiency_scale_max: int = 5
    id: str = field(default_factory=lambda: generate_id("cmp"))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class RoleRequirement:
    competency_id: str
    required_level: int
    mandatory: bool = True
    weight: float = 1.0


@dataclass
class Role:
    name: str
    description: str
    responsibilities: List[str]
    growth_outcomes: List[str]
    next_role_ids: List[str] = field(default_factory=list)
    competency_requirements: List[RoleRequirement] = field(default_factory=list)
    framework_version: int = 1
    id: str = field(default_factory=lambda: generate_id("role"))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class LearningAsset:
    title: str
    summary: str
    content_type: ContentType
    competency_ids: List[str]
    estimated_minutes: int
    url: Optional[str] = None
    id: str = field(default_factory=lambda: generate_id("asset"))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class Assessment:
    title: str
    assessment_type: AssessmentType
    competency_ids: List[str]
    passing_score: float
    max_score: float
    instructions: str = ""
    id: str = field(default_factory=lambda: generate_id("asm"))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class LearningPathItem:
    competency_id: str
    required_level: int
    mandatory: bool
    asset_ids: List[str]
    assessment_ids: List[str]
    notes: str = ""


@dataclass
class LearningPath:
    role_id: str
    version: int
    items: List[LearningPathItem]
    id: str = field(default_factory=lambda: generate_id("path"))
    generated_at: datetime = field(default_factory=utc_now)


@dataclass
class EmployeeProfile:
    name: str
    email: str
    current_role_id: str
    org_unit: str
    manager_id: Optional[str] = None
    id: str = field(default_factory=lambda: generate_id("emp"))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class EvidenceRecord:
    employee_id: str
    competency_id: str
    evidence_type: EvidenceType
    status: str
    score: float = 0.0
    max_score: float = 0.0
    source_id: Optional[str] = None
    notes: str = ""
    reviewer_id: Optional[str] = None
    id: str = field(default_factory=lambda: generate_id("evd"))
    recorded_at: datetime = field(default_factory=utc_now)


@dataclass
class KPI:
    name: str
    description: str
    competency_ids: List[str]
    weak_threshold: float
    id: str = field(default_factory=lambda: generate_id("kpi"))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class KPIObservation:
    employee_id: str
    kpi_id: str
    value: float
    target_value: float
    period_label: str
    status: KPIStatus
    notes: str = ""
    id: str = field(default_factory=lambda: generate_id("obs"))
    observed_at: datetime = field(default_factory=utc_now)


@dataclass
class KPIRecommendation:
    kpi_id: str
    kpi_name: str
    gap_to_target: float
    competency_ids: List[str]
    asset_ids: List[str]
    assessment_ids: List[str]
    action_summary: str


@dataclass
class KPIAnalysis:
    employee_id: str
    weak_kpis: List[KPIRecommendation]
    analyzed_at: datetime = field(default_factory=utc_now)


@dataclass
class WeakKPIInsight:
    kpi_id: str
    kpi_name: str
    weak_observation_count: int
    affected_employee_count: int
    linked_competency_ids: List[str]
    linked_asset_count: int
    linked_assessment_count: int
    action_summary: str


@dataclass
class ImprovementInsightReport:
    weak_kpis: List[WeakKPIInsight]
    generated_at: datetime = field(default_factory=utc_now)


@dataclass
class ReadinessGap:
    competency_id: str
    competency_name: str
    required_level: int
    achieved_level: float
    evidence_count: int
    mandatory: bool


@dataclass
class ReadinessReport:
    employee_id: str
    current_role_id: str
    target_role_id: str
    compliance_score: float
    competency_coverage: float
    readiness_score: float
    ready: bool
    gaps: List[ReadinessGap]
    generated_at: datetime = field(default_factory=utc_now)


@dataclass
class VideoScenePlan:
    scene_number: int
    title: str
    duration_seconds: int
    narration: str
    visual_direction: str
    sora_prompt: str
    clip_url: Optional[str] = None
    job_id: Optional[str] = None
    status: VideoVersionStatus = VideoVersionStatus.QUEUED
    error_message: str = ""


@dataclass
class VideoGenerationJob:
    provider: str
    status: VideoVersionStatus
    progress: int
    job_ids: List[str]
    error: str = ""


@dataclass
class QuizQuestion:
    prompt: str
    options: List[str]
    correct_option_index: int
    explanation: str
    id: str = field(default_factory=lambda: generate_id("qq"))


@dataclass
class KPIQuiz:
    role_name: str
    kpi_name: str
    video_version_id: str
    questions: List[QuizQuestion]
    id: str = field(default_factory=lambda: generate_id("quiz"))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class VideoVersion:
    version_number: int
    source_type: str
    operator_notes: str
    scene_plan: List[VideoScenePlan]
    prompt_used: str
    status: VideoVersionStatus
    generation_job: VideoGenerationJob
    video_url: str = ""
    id: str = field(default_factory=lambda: generate_id("vid"))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class KPIStudioItem:
    kpi_name: str
    category: str
    training_objective: str
    role_name: str = ""
    target_duration_range: str = "60-90 seconds"
    script_draft: str = ""
    storyboard_prompt_draft: str = ""
    revision_prompt_history: List[str] = field(default_factory=list)
    video_versions: List[VideoVersion] = field(default_factory=list)
    final_version_id: Optional[str] = None
    quiz: Optional[KPIQuiz] = None
    studio_status: KPIStudioStatus = KPIStudioStatus.DRAFT
    published: bool = False
    id: str = field(default_factory=lambda: generate_id("studio"))
    created_at: datetime = field(default_factory=utc_now)
