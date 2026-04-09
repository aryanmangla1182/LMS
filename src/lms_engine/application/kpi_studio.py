"""KPI video studio workflow services."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Sequence

from lms_engine.domain.models import (
    KPIQuiz,
    KPIStudioItem,
    KPIStudioStatus,
    QuizQuestion,
    VideoGenerationJob,
    VideoScenePlan,
    VideoVersion,
    VideoVersionStatus,
)
from lms_engine.integrations.video import VideoGenerationGateway


DEFAULT_KPI_LIBRARY: Sequence[Dict[str, str]] = (
    {
        "name": "UNIT PER TRANSACTION",
        "category": "commercial",
        "objective": "Coach the team to increase items per bill with confident recommendation habits.",
    },
    {
        "name": "AVERAGE TRANSACTION VALUE",
        "category": "commercial",
        "objective": "Help the team lift basket value through better discovery and stronger bundles.",
    },
    {
        "name": "AVERAGE SELLING PRICE",
        "category": "commercial",
        "objective": "Build confidence in premium recommendation without harming trust or service quality.",
    },
    {
        "name": "CONVERSION",
        "category": "commercial",
        "objective": "Show how the role turns walk-ins into buying customers through better service execution.",
    },
    {
        "name": "Adaptability & Problem Solving",
        "category": "behavioral",
        "objective": "Train the role to respond calmly when store conditions change during the shift.",
    },
    {
        "name": "Communication & Empathy",
        "category": "behavioral",
        "objective": "Model clear, human communication with customers and team members in live situations.",
    },
    {
        "name": "Customer Focus & Service Excellence",
        "category": "behavioral",
        "objective": "Reinforce service behaviors that improve trust, repeat visits, and stronger selling moments.",
    },
    {
        "name": "Initiative & Drive for Results",
        "category": "behavioral",
        "objective": "Show proactive ownership habits that improve execution before performance drops further.",
    },
    {
        "name": "Leadership & People Development",
        "category": "behavioral",
        "objective": "Demonstrate coaching rhythms that help team members improve and move to the next level.",
    },
    {
        "name": "Teamwork & Collaboration",
        "category": "behavioral",
        "objective": "Train the role to keep team communication tight during customer and operational pressure.",
    },
)


class KPIStudioService:
    """Generate, review, approve, and quiz KPI training videos."""

    def __init__(self, video_gateway: VideoGenerationGateway) -> None:
        self.video_gateway = video_gateway
        self._items: Dict[str, KPIStudioItem] = {}
        self.create_session({})

    def create_session(self, payload: Dict[str, Any]) -> List[KPIStudioItem]:
        role_name = str(payload.get("role_name") or payload.get("title") or "").strip()
        catalog = self._normalize_catalog(payload)
        items = [self._build_item(entry, role_name) for entry in catalog]
        self._items = {item.id: item for item in items}
        return self.list_items()

    def list_items(self) -> List[KPIStudioItem]:
        return [self._sync_item_state(item) for item in self._items.values()]

    def get_item(self, item_id: str) -> KPIStudioItem:
        item = self._items.get(item_id)
        if item is None:
            raise ValueError("KPI studio item not found: {0}".format(item_id))
        return self._sync_item_state(item)

    def generate_video_version(self, item_id: str, payload: Dict[str, Any]) -> VideoVersion:
        item = self.get_item(item_id)
        role_name = str(payload.get("role_name") or item.role_name).strip()
        revision_prompt = str(payload.get("revision_prompt", "")).strip()
        if not role_name:
            raise ValueError("role_name is required for first video generation")

        item.role_name = role_name
        if revision_prompt:
            item.revision_prompt_history.append(revision_prompt)

        prompt_used = self._build_generation_prompt(item, revision_prompt)
        item.script_draft = self._build_script(item, revision_prompt)
        item.storyboard_prompt_draft = prompt_used
        scene_plan = self._build_scene_plan(item, revision_prompt)
        source_type = "revision" if item.video_versions else "draft"

        try:
            generation = self.video_gateway.generate_scene_clips(scene_plan)
            status = VideoVersionStatus(generation.get("status", VideoVersionStatus.COMPLETED.value))
            video_url = self._video_url_for(generation.get("video_asset_id"), generation.get("video_url", ""))
            for scene in scene_plan:
                if scene.job_id:
                    scene.clip_url = self._asset_url(scene.job_id)
        except ValueError as exc:
            status = VideoVersionStatus.FAILED
            generation = {
                "status": status.value,
                "progress": 0,
                "job_ids": [],
                "video_url": "",
                "error": str(exc),
            }
            video_url = ""

        version = VideoVersion(
            version_number=len(item.video_versions) + 1,
            source_type=source_type,
            operator_notes=revision_prompt,
            scene_plan=scene_plan,
            prompt_used=prompt_used,
            status=status,
            video_url=video_url,
            generation_job=VideoGenerationJob(
                provider=self.video_gateway.provider_name,
                status=status,
                progress=int(generation.get("progress", 0)),
                job_ids=list(generation.get("job_ids", [])),
                error=str(generation.get("error", "")).strip(),
            ),
        )
        item.video_versions.append(version)
        item.video_versions = item.video_versions[-3:]
        item.studio_status = KPIStudioStatus.REVIEW
        if status == VideoVersionStatus.COMPLETED:
            item.final_version_id = version.id
            item.quiz = self._build_quiz(item, version)
        else:
            item.final_version_id = None
            item.quiz = None
        item.published = False
        return version

    def approve_version(self, item_id: str, version_id: str) -> KPIStudioItem:
        item = self.get_item(item_id)
        version = self._find_version(item, version_id)
        version.status = VideoVersionStatus.APPROVED
        item.final_version_id = version.id
        item.quiz = self._build_quiz(item, version)
        item.studio_status = KPIStudioStatus.APPROVED
        item.published = True
        return item

    def reopen_item(self, item_id: str) -> KPIStudioItem:
        item = self.get_item(item_id)
        item.final_version_id = None
        item.quiz = None
        item.published = False
        item.studio_status = KPIStudioStatus.REVIEW if item.video_versions else KPIStudioStatus.DRAFT
        for version in item.video_versions:
            if version.status == VideoVersionStatus.APPROVED:
                version.status = VideoVersionStatus.COMPLETED
        return item

    def _sync_item_state(self, item: KPIStudioItem) -> KPIStudioItem:
        latest_ready_version = next(
            (version for version in reversed(item.video_versions) if version.status in {VideoVersionStatus.COMPLETED, VideoVersionStatus.APPROVED}),
            None,
        )
        if latest_ready_version is None:
            item.final_version_id = None
            item.quiz = None
            item.studio_status = KPIStudioStatus.DRAFT if not item.video_versions else KPIStudioStatus.REVIEW
            item.published = False
            return item

        item.final_version_id = latest_ready_version.id
        if item.quiz is None or item.quiz.video_version_id != latest_ready_version.id:
            item.quiz = self._build_quiz(item, latest_ready_version)
        if latest_ready_version.status == VideoVersionStatus.APPROVED:
            item.studio_status = KPIStudioStatus.APPROVED
            item.published = True
        else:
            item.studio_status = KPIStudioStatus.REVIEW
            item.published = False
        return item

    def fetch_video_bytes(self, asset_id: str) -> tuple[str, bytes]:
        fetcher = getattr(self.video_gateway, "fetch_clip_bytes", None)
        if not callable(fetcher):
            raise ValueError("Video asset not available: {0}".format(asset_id))
        return fetcher(asset_id)

    def _normalize_catalog(self, payload: Dict[str, Any]) -> List[Dict[str, str]]:
        catalog: List[Dict[str, str]] = []
        seen = set()

        for item in payload.get("kpis", []) or []:
            if not isinstance(item, dict):
                continue
            primary = str(item.get("description") or item.get("name") or "").strip()
            fallback = str(item.get("name") or primary).strip()
            name = primary if " " in primary else fallback
            normalized_name = name.strip()
            if not normalized_name or normalized_name.lower() in seen:
                continue
            seen.add(normalized_name.lower())
            catalog.append(
                {
                    "name": normalized_name,
                    "category": "commercial",
                    "objective": "Train the role to improve {0} with better floor execution.".format(
                        normalized_name.lower()
                    ),
                }
            )

        for skill in payload.get("skills", []) or []:
            normalized = str(skill).strip()
            if not normalized or normalized.lower() in seen:
                continue
            seen.add(normalized.lower())
            catalog.append(
                {
                    "name": normalized,
                    "category": "behavioral",
                    "objective": "Coach stronger {0} habits in live store situations.".format(normalized.lower()),
                }
            )

        if catalog:
            return catalog
        return [dict(item) for item in DEFAULT_KPI_LIBRARY]

    def _build_item(self, entry: Dict[str, str], role_name: str) -> KPIStudioItem:
        return KPIStudioItem(
            id=self._stable_item_id(entry["name"], entry["category"]),
            kpi_name=entry["name"],
            category=entry["category"],
            role_name=role_name,
            training_objective=entry["objective"],
        )

    def _build_generation_prompt(self, item: KPIStudioItem, revision_prompt: str) -> str:
        prompt = (
            "Create a {0} second training video for {1} focused on {2}. Goal: {3}."
        ).format(item.target_duration_range, item.role_name, item.kpi_name, item.training_objective)
        if revision_prompt:
            prompt = "{0} Revision note: {1}.".format(prompt, revision_prompt)
        return prompt

    def _build_script(self, item: KPIStudioItem, revision_prompt: str) -> str:
        script = (
            "{0} should explain why {1} matters, what great execution looks like, "
            "how to coach the team, and how to hold the routine daily."
        ).format(item.role_name, item.kpi_name)
        if revision_prompt:
            script = "{0} Update requested: {1}.".format(script, revision_prompt)
        return script

    def _build_scene_plan(self, item: KPIStudioItem, revision_prompt: str) -> List[VideoScenePlan]:
        scenes = [
            (
                "Why the KPI matters",
                "Explain why this KPI matters on shift.",
                "Opening title card, score trend, and short floor context setup.",
            ),
            (
                "Spot the weak moment",
                "Show the behavior gap that weakens results.",
                "Manager coaching visual, customer moment, and red flag callouts.",
            ),
            (
                "Coach the fix",
                "Demonstrate one coaching move to use now.",
                "Simple playbook frame, team huddle, and action checklist overlay.",
            ),
            (
                "Lock the habit",
                "Close with the daily routine that sustains gains.",
                "Repeatable routine card, ownership cue, and positive closing frame.",
            ),
        ]
        return [
            VideoScenePlan(
                scene_number=index + 1,
                title=title,
                duration_seconds=18,
                narration=(
                    "{0} for {1}. Scene {2}: {3}"
                ).format(item.kpi_name, item.role_name, index + 1, body),
                visual_direction="{0}{1}".format(
                    visual,
                    " Revision note: {0}.".format(revision_prompt) if revision_prompt else "",
                ),
                sora_prompt=(
                    "Training video scene for {0} role about {1}. {2} Visual direction: {3}"
                ).format(item.role_name, item.kpi_name, body, visual),
            )
            for index, (title, body, visual) in enumerate(scenes)
        ]

    def _build_quiz(self, item: KPIStudioItem, version: VideoVersion) -> KPIQuiz:
        prompts = [
            "What is the primary goal of improving {kpi} in the {role} role?",
            "Which daily behavior from the video most directly supports {kpi}?",
            "A team member is skipping the key action from the video. What should {role} do first?",
            "Which coaching cue from the approved video helps protect {kpi} during rush hours?",
            "What is the strongest sign that the team is applying the {kpi} routine correctly?",
            "When reviewing shift performance, what should {role} check first for {kpi}?",
            "A customer interaction starts to stall. Which move from the video fits best?",
            "How should {role} reinforce the habit from the video after the shift?",
            "Why does the approved workflow connect service quality with {kpi} results?",
            "What is the clearest next step when {kpi} remains weak for two days?",
        ]
        questions: List[QuizQuestion] = []
        for index, template in enumerate(prompts):
            prompt = template.format(kpi=item.kpi_name, role=item.role_name)
            correct = "Apply the KPI coaching routine shown in the video."
            options = [
                correct,
                "Wait for weekly review before acting.",
                "Focus only on speed and skip coaching.",
                "Change the target without changing behavior.",
            ]
            questions.append(
                QuizQuestion(
                    prompt=prompt,
                    options=options,
                    correct_option_index=0,
                    explanation=(
                        "The approved video for {0} teaches {1} to improve {2} through repeated coaching and daily follow-through."
                    ).format(item.role_name, item.kpi_name, version.id),
                )
            )
        return KPIQuiz(
            role_name=item.role_name,
            kpi_name=item.kpi_name,
            video_version_id=version.id,
            questions=questions,
        )

    def _find_version(self, item: KPIStudioItem, version_id: str) -> VideoVersion:
        for version in item.video_versions:
            if version.id == version_id:
                return version
        raise ValueError("Video version not found: {0}".format(version_id))

    @staticmethod
    def _stable_item_id(name: str, category: str) -> str:
        digest = hashlib.sha1("{0}:{1}".format(category, name).encode("utf-8")).hexdigest()[:12]
        return "studio_{0}".format(digest)

    @staticmethod
    def _asset_url(asset_id: Optional[str]) -> Optional[str]:
        if not asset_id:
            return None
        return "/studio/videos/{0}".format(asset_id)

    def _video_url_for(self, asset_id: Optional[str], fallback_url: str) -> str:
        if asset_id:
            return self._asset_url(asset_id) or ""
        return str(fallback_url or "")
