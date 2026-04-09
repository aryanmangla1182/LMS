"""KPI video studio workflow services."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
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


TRAINING_GUIDE_PATH = Path(__file__).resolve().parent.parent / "data" / "kpi_training_guide.json"


def _load_training_guide() -> Dict[str, Any]:
    if not TRAINING_GUIDE_PATH.exists():
        return {"modules": [], "bonus_quiz_prompts": [], "master_video_script": ""}
    return json.loads(TRAINING_GUIDE_PATH.read_text(encoding="utf-8"))


def _lookup_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _compact_text(value: str, max_words: int) -> str:
    words = value.strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return "{0}...".format(" ".join(words[:max_words]))


def _meaning_distractors(category: str) -> List[str]:
    if category == "commercial":
        return [
            "How quickly billing is completed during the shift.",
            "How many discounts are given in a day.",
            "How many people enter the store without buying.",
        ]
    return [
        "Working alone without asking questions.",
        "Following instructions without understanding the customer.",
        "Finishing tasks quickly even if the customer feels ignored.",
    ]


TRAINING_GUIDE = _load_training_guide()
TRAINING_GUIDE_MODULES: Sequence[Dict[str, Any]] = tuple(TRAINING_GUIDE.get("modules", []))
TRAINING_GUIDE_INDEX = {
    _lookup_key(alias): module
    for module in TRAINING_GUIDE_MODULES
    for alias in [module["name"], *module.get("aliases", [])]
}
DEFAULT_KPI_LIBRARY: Sequence[Dict[str, str]] = tuple(
    {
        "name": module["name"],
        "category": str(module["category"]),
        "objective": str(module["training_objective"]),
    }
    for module in TRAINING_GUIDE_MODULES
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
            guide_entry = self._guide_entry_for(normalized_name)
            canonical_name = str(guide_entry["name"]) if guide_entry else normalized_name
            seen_key = canonical_name.lower()
            if not canonical_name or seen_key in seen:
                continue
            seen.add(seen_key)
            if guide_entry:
                catalog.append(self._catalog_entry_from_guide(guide_entry))
            else:
                catalog.append(
                    {
                        "name": canonical_name,
                        "category": "commercial",
                        "objective": "Train the role to improve {0} with better floor execution.".format(
                            canonical_name.lower()
                        ),
                    }
                )

        for skill in payload.get("skills", []) or []:
            normalized = str(skill).strip()
            guide_entry = self._guide_entry_for(normalized)
            canonical_name = str(guide_entry["name"]) if guide_entry else normalized
            seen_key = canonical_name.lower()
            if not canonical_name or seen_key in seen:
                continue
            seen.add(seen_key)
            if guide_entry:
                catalog.append(self._catalog_entry_from_guide(guide_entry))
            else:
                catalog.append(
                    {
                        "name": canonical_name,
                        "category": "behavioral",
                        "objective": "Coach stronger {0} habits in live store situations.".format(canonical_name.lower()),
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
        guide_entry = self._guide_entry_for(item.kpi_name)
        prompt = (
            "Create a {0} second training video for {1} focused on {2}. Goal: {3}."
        ).format(item.target_duration_range, item.role_name, item.kpi_name, item.training_objective)
        if guide_entry:
            prompt = "{0} Meaning: {1} Scenario: {2} Good behavior: {3}".format(
                prompt,
                guide_entry["simple_meaning"],
                guide_entry["scenario_setup"],
                guide_entry["good_behavior"],
            )
        if revision_prompt:
            prompt = "{0} Revision note: {1}.".format(prompt, revision_prompt)
        return prompt

    def _build_script(self, item: KPIStudioItem, revision_prompt: str) -> str:
        guide_entry = self._guide_entry_for(item.kpi_name)
        if guide_entry:
            parts = [
                str(guide_entry["simple_meaning"]),
                "Scenario: {0} Bad approach: {1} Better approach: {2}".format(
                    guide_entry["scenario_setup"],
                    guide_entry["scenario_bad"],
                    guide_entry["scenario_good"],
                ),
                "Good versus bad: bad means {0} Good means {1}".format(
                    guide_entry["bad_behavior"],
                    guide_entry["good_behavior"],
                ),
                "Improve by {0}".format(" ".join(str(action) for action in guide_entry["improvement_actions"])),
                str(guide_entry["video_script"]),
            ]
            script = " ".join(parts)
        else:
            script = (
                "{0} should explain why {1} matters, what great execution looks like, "
                "how to coach the team, and how to hold the routine daily."
            ).format(item.role_name, item.kpi_name)
        if revision_prompt:
            script = "{0} Update requested: {1}.".format(script, revision_prompt)
        return script

    def _build_scene_plan(self, item: KPIStudioItem, revision_prompt: str) -> List[VideoScenePlan]:
        guide_entry = self._guide_entry_for(item.kpi_name)
        if guide_entry:
            actions = list(guide_entry["improvement_actions"])
            bad_short = _compact_text(str(guide_entry["scenario_bad"]), 4)
            good_short = _compact_text(str(guide_entry["scenario_good"]), 8)
            good_behavior_short = _compact_text(str(guide_entry["good_behavior"]), 8)
            simple_short = _compact_text(str(guide_entry["simple_meaning"]), 16)
            actions_short = _compact_text(" ".join(actions), 12)
            scene_specs = [
                (
                    "What this means",
                    simple_short,
                    "Meaning card, key term highlight, and calm presenter framing.",
                ),
                (
                    "Store floor scenario",
                    "Avoid {0}. Use {1}.".format(bad_short, good_short),
                    "Show the customer moment, then contrast bad and good responses clearly.",
                ),
                (
                    "Good versus bad",
                    "Good looks like {0}. Offer a solution.".format(good_behavior_short),
                    "Split-screen comparison with bad behavior on one side and good behavior on the other.",
                ),
                (
                    "How to improve",
                    "Improve this every shift: {0}".format(actions_short),
                    "Checklist overlay, team huddle close, and clear manager coaching cue.",
                ),
            ]
            if revision_prompt:
                scene_specs[-1] = (
                    scene_specs[-1][0],
                    "{0} Revision note: {1}".format(scene_specs[-1][1], revision_prompt),
                    "{0} Revision note: {1}".format(scene_specs[-1][2], revision_prompt),
                )
            return [
                VideoScenePlan(
                    scene_number=index + 1,
                    title=title,
                    duration_seconds=18,
                    narration="{0} for {1}. Scene {2}: {3}".format(item.kpi_name, item.role_name, index + 1, body),
                    visual_direction=visual,
                    sora_prompt="Training video scene for {0} role about {1}. {2} Visual direction: {3}".format(
                        item.role_name,
                        item.kpi_name,
                        body,
                        visual,
                    ),
                )
                for index, (title, body, visual) in enumerate(scene_specs)
            ]
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
        guide_entry = self._guide_entry_for(item.kpi_name)
        if guide_entry:
            quiz_label = str(guide_entry.get("quiz_label") or item.kpi_name)
            actions = list(guide_entry["improvement_actions"])
            action_one = actions[0]
            action_two = actions[1] if len(actions) > 1 else actions[0]
            action_three = actions[2] if len(actions) > 2 else actions[-1]
            scenario_good = str(guide_entry["scenario_good"])
            scenario_bad = str(guide_entry["scenario_bad"])
            good_behavior = str(guide_entry["good_behavior"])
            bad_behavior = str(guide_entry["bad_behavior"])
            training_objective = str(guide_entry["training_objective"])
            video_script = str(guide_entry["video_script"])
            simple_meaning = str(guide_entry["simple_meaning"])
            common_wrong_moves = [
                "Move straight to billing without asking one more question.",
                "Wait for the customer to ask for help before acting.",
                "Push a random product that does not match the need.",
                "Use a defensive tone to end the conversation faster.",
                "Delay action until the next review.",
            ]
            questions = [
                QuizQuestion(
                    prompt="What does {0} mean in this role?".format(quiz_label),
                    options=[
                        simple_meaning,
                        *_meaning_distractors(str(guide_entry["category"])),
                    ],
                    correct_option_index=0,
                    explanation=video_script,
                ),
                QuizQuestion(
                    prompt="In the training scenario for {0}, what is the best next move?".format(quiz_label),
                    options=[
                        scenario_good,
                        scenario_bad,
                        common_wrong_moves[0],
                        common_wrong_moves[1],
                    ],
                    correct_option_index=0,
                    explanation="The strong example in the video shows {0}".format(good_behavior),
                ),
                QuizQuestion(
                    prompt="Which response from the video weakens {0}?".format(quiz_label),
                    options=[
                        scenario_bad,
                        scenario_good,
                        action_one,
                        action_two,
                    ],
                    correct_option_index=0,
                    explanation="The weak example in the video shows {0}".format(bad_behavior),
                ),
                QuizQuestion(
                    prompt="Which action would most directly strengthen {0} on the floor?".format(quiz_label),
                    options=[
                        action_one,
                        common_wrong_moves[0],
                        common_wrong_moves[2],
                        common_wrong_moves[4],
                    ],
                    correct_option_index=0,
                    explanation="The guide says to improve by {0}".format(action_one.lower()),
                ),
                QuizQuestion(
                    prompt="Which coaching habit from the guide supports {0} consistently?".format(quiz_label),
                    options=[
                        action_two,
                        "Stop helping once the first option fails.",
                        "Use the same line for every customer without listening.",
                        "Let the opportunity pass if the store is busy.",
                    ],
                    correct_option_index=0,
                    explanation="This action supports the skill or KPI in daily execution.",
                ),
                QuizQuestion(
                    prompt="What is the strongest coaching message for {0}?".format(quiz_label),
                    options=[
                        action_three,
                        "Stay passive and wait for instructions.",
                        "Protect the old habit even when it is not working.",
                        "Focus only on speed and ignore quality.",
                    ],
                    correct_option_index=0,
                    explanation="The video closes by reinforcing this repeatable routine.",
                ),
                QuizQuestion(
                    prompt="Why does this training matter for {0}?".format(quiz_label),
                    options=[
                        training_objective,
                        "It removes the need to engage customers.",
                        "It only matters during end-of-month reporting.",
                        "It replaces teamwork on the floor.",
                    ],
                    correct_option_index=0,
                    explanation="The objective anchors why this behavior or KPI matters in the role.",
                ),
                QuizQuestion(
                    prompt="Which statement best describes the strong example from the video for {0}?".format(quiz_label),
                    options=[
                        good_behavior,
                        bad_behavior,
                        "Do less and wait for direction.",
                        "End the sale conversation quickly.",
                    ],
                    correct_option_index=0,
                    explanation="The good example is the standard learners should copy.",
                ),
                QuizQuestion(
                    prompt="What should the learner avoid when working on {0}?".format(quiz_label),
                    options=[
                        bad_behavior,
                        good_behavior,
                        action_one,
                        action_three,
                    ],
                    correct_option_index=0,
                    explanation="The bad pattern is what weakens results and customer experience.",
                ),
                QuizQuestion(
                    prompt="What outcome should strong execution create for {0}?".format(quiz_label),
                    options=[
                        video_script,
                        "Less effort and less follow-through on the floor.",
                        "More missed selling or service moments.",
                        "A weaker customer experience.",
                    ],
                    correct_option_index=0,
                    explanation="For {0}, strong execution comes from applying the coached behavior in real customer moments.".format(
                        quiz_label
                    ),
                ),
            ]
            return KPIQuiz(
                role_name=item.role_name,
                kpi_name=item.kpi_name,
                video_version_id=version.id,
                questions=questions,
            )
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

    def _guide_entry_for(self, name: str) -> Optional[Dict[str, Any]]:
        return TRAINING_GUIDE_INDEX.get(_lookup_key(name))

    def _catalog_entry_from_guide(self, guide_entry: Dict[str, Any]) -> Dict[str, str]:
        return {
            "name": str(guide_entry["name"]),
            "category": str(guide_entry["category"]),
            "objective": str(guide_entry["training_objective"]),
        }

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
