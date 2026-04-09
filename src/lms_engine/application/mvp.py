"""Persisted MVP service for the LMS engine."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import random
from typing import Any, Dict, List, Optional
from uuid import uuid4

from lms_engine.ai import AIContentGenerator
from lms_engine.storage import AssetStore, JsonStore


class AppError(Exception):
    pass


class NotFoundError(AppError):
    pass


class ValidationError(AppError):
    pass


class AuthorizationError(AppError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    return "{0}_{1}".format(prefix, uuid4().hex[:10])


@dataclass
class AppConfig:
    ai_enabled: bool
    openai_model: str
    trainer_phone: str


class LMSEngineService:
    def __init__(self, store: JsonStore, asset_store: AssetStore, generator: AIContentGenerator) -> None:
        self.store = store
        self.asset_store = asset_store
        self.generator = generator
        self.default_trainer_phone = os.getenv("LMS_TRAINER_PHONE", os.getenv("LMS_OWNER_PHONE", "9999999999"))
        self.default_trainer_name = os.getenv("LMS_TRAINER_NAME", os.getenv("LMS_OWNER_NAME", "Cultfit LMS Trainer"))
        self.default_trainer_code = os.getenv("LMS_TRAINER_CODE", os.getenv("LMS_OWNER_CODE", "111111"))
        self._ensure_trainer_account()

    def get_config(self) -> AppConfig:
        return AppConfig(
            ai_enabled=self.generator.enabled,
            openai_model=self.generator.model,
            trainer_phone=self.default_trainer_phone,
        )

    def reset_and_seed_demo(self) -> Dict[str, Any]:
        self.store.save(
            {
                "roles": [],
                "users": [],
                "learners": [],
                "sessions": [],
                "enrollments": [],
                "assessment_attempts": [],
                "assignment_submissions": [],
                "kpi_observations": [],
                "remediation_assignments": [],
                "activity_log": [],
                "media_assets": [],
            }
        )
        self._ensure_trainer_account()
        role = self.generate_role_blueprint(
            {
                "segment": "Retail",
                "title": "Store Manager",
                "level": "L3",
                "legacy_mappings": ["Retail Store Lead", "Store Staff Level 2"],
                "work_summary": "Leads store execution, team performance, customer experience, and local commercial outcomes.",
                "responsibilities": [
                    "Open and close the store without compliance gaps",
                    "Coach staff on service and conversion",
                    "Track daily business performance and resolve weak areas",
                    "Prepare strong team members for the next level",
                ],
            }
        )
        role = self.apply_role_review(
            role["id"],
            {
                "review_note": "Make compliance more explicit and strengthen next-level leadership content.",
            },
        )
        role = self.publish_role(role["id"])
        learner = self.create_learner(
            {
                "name": "Asha Menon",
                "phone_number": "9000000001",
                "email": "asha@cult.fit",
                "role_id": role["id"],
                "org_unit": "Retail South",
            }
        )
        second = self.create_learner(
            {
                "name": "Dev Shah",
                "phone_number": "9000000002",
                "email": "dev@cult.fit",
                "role_id": role["id"],
                "org_unit": "Retail West",
            }
        )
        first_enrollment = self._get_learner_enrollment(self._state(), learner["id"])
        for lesson in first_enrollment["course"]["sections"][0]["lessons"][:1]:
            self.complete_lesson(first_enrollment["id"], lesson["id"])
        answers = []
        for question in first_enrollment["course"]["assessment"]["questions"]:
            selected = question["correct_option_index"]
            if len(answers) == 1:
                selected = 0
            answers.append({"question_id": question["id"], "selected_option_index": selected})
        self.submit_assessment(first_enrollment["id"], {"answers": answers})
        self.record_kpi_observation(
            learner["id"],
            {
                "kpi_id": role["kpis"][0]["id"],
                "value": 76,
                "target_value": role["kpis"][0]["target_value"],
                "period_label": "April 2026",
                "notes": "Execution dipped during a staffing gap.",
            },
        )
        self.record_kpi_observation(
            second["id"],
            {
                "kpi_id": role["kpis"][1]["id"],
                "value": 3.7,
                "target_value": role["kpis"][1]["target_value"],
                "period_label": "April 2026",
                "notes": "Service escalations increased this month.",
            },
        )
        return {
            "role_id": role["id"],
            "learner_ids": [learner["id"], second["id"]],
            "message": "Demo workspace ready.",
        }

    def request_login_code(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        phone = self._normalize_phone(payload.get("phone_number", ""))
        state = self._state()
        user = self._find_user_by_phone(state, phone)
        code = self.default_trainer_code if self._normalized_user_type(user) == "trainer" else "{0:06d}".format(random.randint(0, 999999))
        user["login_code"] = code
        user["login_code_issued_at"] = now_iso()
        self._log_event(state, "login_code_requested", {"user_id": user["id"], "user_type": user["user_type"]})
        self._save(state)
        return {
            "message": "Login code generated.",
            "code": code,
            "user_type": user["user_type"],
        }

    def verify_login_code(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        phone = self._normalize_phone(payload.get("phone_number", ""))
        code = str(payload.get("code", "")).strip()
        state = self._state()
        user = self._find_user_by_phone(state, phone)
        if user.get("login_code") != code:
            raise AuthorizationError("Invalid code")

        token = make_id("sess")
        session = {
            "id": token,
            "token": token,
            "user_id": user["id"],
            "created_at": now_iso(),
        }
        state["sessions"].append(session)
        user["last_login_at"] = now_iso()
        user["login_code"] = None
        self._log_event(state, "login_verified", {"user_id": user["id"], "user_type": user["user_type"]})
        self._save(state)
        return {
            "token": token,
            "user": self._present_user(user),
        }

    def get_current_user(self, token: str) -> Dict[str, Any]:
        return self._present_user(self._require_user_by_token(token))

    def list_users(self) -> List[Dict[str, Any]]:
        return [self._present_user(user) for user in self._state()["users"]]

    def list_roles(self) -> List[Dict[str, Any]]:
        return self._state()["roles"]

    def get_role(self, role_id: str) -> Dict[str, Any]:
        state = self._state()
        role = self._find_by_id(state["roles"], role_id, "Role")
        return role

    def generate_role_blueprint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        title = payload.get("title", "").strip()
        segment = payload.get("segment", "").strip()
        if not title or not segment:
            raise ValidationError("segment and title are required")

        responsibilities = self._normalize_lines(payload.get("responsibilities", []))
        if not responsibilities:
            raise ValidationError("At least one responsibility is required")

        package = self.generator.generate_role_package(payload)
        role = self._build_role_record(payload, package, review_note="")
        state = self._state()
        state["roles"].append(role)
        self._log_event(state, "role_generated", {"role_id": role["id"], "title": title})
        self._save(state)
        return role

    def apply_role_review(self, role_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        review_note = payload.get("review_note", "").strip()
        if not review_note:
            raise ValidationError("review_note is required")

        state = self._state()
        role = self._find_by_id(state["roles"], role_id, "Role")
        source_payload = {
            "segment": role["segment"],
            "title": role["title"],
            "level": role["level"],
            "legacy_mappings": role["legacy_mappings"],
            "work_summary": role["work_summary"],
            "responsibilities": role["responsibilities"],
            "skills": [item["name"] for item in role["skills"]],
            "kpis": [
                {
                    "name": item["name"],
                    "description": item["description"],
                    "target_value": item["target_value"],
                    "unit": item["unit"],
                    "weak_threshold": item["weak_threshold"],
                }
                for item in role["kpis"]
            ],
        }
        package = self.generator.generate_role_package(source_payload, review_note=review_note)
        updated = self._build_role_record(source_payload, package, review_note=review_note, existing=role)
        index = state["roles"].index(role)
        state["roles"][index] = updated
        self._log_event(state, "role_review_applied", {"role_id": role_id, "review_note": review_note})
        self._save(state)
        return updated

    def publish_role(self, role_id: str) -> Dict[str, Any]:
        state = self._state()
        role = self._find_by_id(state["roles"], role_id, "Role")
        role["status"] = "published"
        role["published_at"] = now_iso()
        role["learning_path"]["status"] = "published"
        self._log_event(state, "role_published", {"role_id": role_id})
        for learner in state["learners"]:
            if learner["role_id"] == role_id and not self._get_enrollment(state, learner["id"], role_id):
                state["enrollments"].append(self._build_enrollment(learner, role))
        self._save(state)
        return role

    def list_learners(self) -> List[Dict[str, Any]]:
        return self._state()["learners"]

    def create_user(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        role_id = payload.get("role_id", "").strip()
        if not role_id:
            raise ValidationError("role_id is required")

        state = self._state()
        role = self._find_by_id(state["roles"], role_id, "Role")
        if role["status"] != "published":
            raise ValidationError("Role must be published before assigning learners")

        phone_number = self._normalize_phone(payload.get("phone_number", ""))
        if any(user["phone_number"] == phone_number for user in state["users"]):
            raise ValidationError("phone_number already exists")

        learner = {
            "id": make_id("lrn"),
            "name": payload.get("name", "").strip(),
            "phone_number": phone_number,
            "role_id": role_id,
            "org_unit": payload.get("org_unit", "").strip() or "Unassigned",
            "created_at": now_iso(),
        }
        if not learner["name"] or not learner["phone_number"]:
            raise ValidationError("name and phone_number are required")

        user = {
            "id": make_id("usr"),
            "name": learner["name"],
            "phone_number": learner["phone_number"],
            "user_type": "learner",
            "learner_id": learner["id"],
            "role_id": role_id,
            "created_at": now_iso(),
            "login_code": None,
            "login_code_issued_at": None,
            "last_login_at": None,
        }
        state["learners"].append(learner)
        state["users"].append(user)
        state["enrollments"].append(self._build_enrollment(learner, role))
        self._log_event(state, "learner_created", {"learner_id": learner["id"], "role_id": role_id, "user_id": user["id"]})
        self._save(state)
        return {
            "user": self._present_user(user),
            "learner": learner,
        }

    def create_learner(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        phone_number = payload.get("phone_number") or payload.get("email") or ""
        result = self.create_user(
            {
                "name": payload.get("name", ""),
                "phone_number": phone_number,
                "role_id": payload.get("role_id", ""),
                "org_unit": payload.get("org_unit", ""),
            }
        )
        learner = result["learner"]
        learner["email"] = payload.get("email", "").strip()
        state = self._state()
        stored = self._find_by_id(state["learners"], learner["id"], "Learner")
        stored["email"] = learner["email"]
        self._save(state)
        return stored

    def get_learner_dashboard(self, learner_id: str) -> Dict[str, Any]:
        state = self._state()
        learner = self._find_by_id(state["learners"], learner_id, "Learner")
        role = self._find_by_id(state["roles"], learner["role_id"], "Role")
        enrollment = self._get_learner_enrollment(state, learner_id)
        attempts = [item for item in state["assessment_attempts"] if item["enrollment_id"] == enrollment["id"]]
        assignment_submissions = [item for item in state["assignment_submissions"] if item["enrollment_id"] == enrollment["id"]]
        kpi_obs = [item for item in state["kpi_observations"] if item["learner_id"] == learner_id]
        remediation = [item for item in state["remediation_assignments"] if item["learner_id"] == learner_id]
        latest_attempt = attempts[-1] if attempts else None
        latest_kpi_status = self._latest_kpi_observations(kpi_obs)

        completed_ids = set(enrollment["completed_lesson_ids"])
        total_lessons = sum(len(section["lessons"]) for section in enrollment["course"]["sections"])
        completion_pct = round((len(completed_ids) / float(total_lessons)) * 100, 2) if total_lessons else 0.0

        healthy_kpis = sum(1 for item in latest_kpi_status.values() if item["status"] == "healthy")
        weak_kpis = [item for item in latest_kpi_status.values() if item["status"] == "weak"]

        return {
            "learner": learner,
            "role": role,
            "enrollment": enrollment,
            "metrics": {
                "completion_percentage": completion_pct,
                "lessons_completed": len(completed_ids),
                "total_lessons": total_lessons,
                "latest_assessment_score": latest_attempt["score_percentage"] if latest_attempt else None,
                "weak_skill_count": len(latest_attempt["weak_skills"]) if latest_attempt else 0,
                "healthy_kpis": healthy_kpis,
                "weak_kpis": len(weak_kpis),
            },
            "latest_assessment": latest_attempt,
            "assignment_submissions": assignment_submissions,
            "kpi_observations": kpi_obs,
            "remediation_assignments": remediation,
        }

    def complete_lesson(self, enrollment_id: str, lesson_id: str) -> Dict[str, Any]:
        state = self._state()
        enrollment = self._find_by_id(state["enrollments"], enrollment_id, "Enrollment")
        lesson = self._find_lesson(enrollment["course"], lesson_id)
        if lesson_id not in enrollment["completed_lesson_ids"]:
            enrollment["completed_lesson_ids"].append(lesson_id)
        self._log_event(state, "lesson_completed", {"enrollment_id": enrollment_id, "lesson_id": lesson_id})
        self._save(state)
        return {"lesson": lesson, "completed_lesson_ids": enrollment["completed_lesson_ids"]}

    def submit_assessment(self, enrollment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._state()
        enrollment = self._find_by_id(state["enrollments"], enrollment_id, "Enrollment")
        answers = payload.get("answers", [])
        assessment = enrollment["course"]["assessment"]
        question_index = {item["id"]: item for item in assessment["questions"]}
        question_results = []
        skill_counter = defaultdict(lambda: {"name": "", "correct": 0, "total": 0})
        kpi_counter = defaultdict(lambda: {"name": "", "correct": 0, "total": 0})
        correct = 0

        for answer in answers:
            question = question_index.get(answer.get("question_id"))
            if question is None:
                continue
            selected = int(answer.get("selected_option_index", -1))
            is_correct = selected == question["correct_option_index"]
            if is_correct:
                correct += 1
            question_results.append(
                {
                    "question_id": question["id"],
                    "prompt": question["prompt"],
                    "selected_option_index": selected,
                    "correct_option_index": question["correct_option_index"],
                    "is_correct": is_correct,
                    "explanation": question["explanation"],
                    "skill_ids": question["skill_ids"],
                    "kpi_ids": question["kpi_ids"],
                }
            )
            for skill_id in question["skill_ids"]:
                skill = self._find_skill(enrollment["role_snapshot"], skill_id)
                skill_counter[skill_id]["name"] = skill["name"]
                skill_counter[skill_id]["total"] += 1
                if is_correct:
                    skill_counter[skill_id]["correct"] += 1
            for kpi_id in question["kpi_ids"]:
                kpi = self._find_kpi(enrollment["role_snapshot"], kpi_id)
                kpi_counter[kpi_id]["name"] = kpi["name"]
                kpi_counter[kpi_id]["total"] += 1
                if is_correct:
                    kpi_counter[kpi_id]["correct"] += 1

        total = len(question_results) or len(assessment["questions"])
        score_pct = round((correct / float(total)) * 100, 2) if total else 0.0
        weak_skills = [
            {
                "skill_id": skill_id,
                "skill_name": data["name"],
                "accuracy": round((data["correct"] / float(data["total"])) * 100, 2) if data["total"] else 0.0,
            }
            for skill_id, data in skill_counter.items()
            if data["total"] and (data["correct"] / float(data["total"])) < 0.7
        ]
        weak_kpis = [
            {
                "kpi_id": kpi_id,
                "kpi_name": data["name"],
                "accuracy": round((data["correct"] / float(data["total"])) * 100, 2) if data["total"] else 0.0,
            }
            for kpi_id, data in kpi_counter.items()
            if data["total"] and (data["correct"] / float(data["total"])) < 0.7
        ]

        attempt = {
            "id": make_id("att"),
            "enrollment_id": enrollment_id,
            "learner_id": enrollment["learner_id"],
            "role_id": enrollment["role_id"],
            "assessment_id": assessment["id"],
            "score_percentage": score_pct,
            "passed": score_pct >= assessment["passing_score"],
            "submitted_at": now_iso(),
            "question_results": question_results,
            "weak_skills": weak_skills,
            "weak_kpis": weak_kpis,
            "analysis_summary": self._build_attempt_summary(score_pct, weak_skills, weak_kpis),
        }
        state["assessment_attempts"].append(attempt)
        enrollment["last_assessment_attempt_id"] = attempt["id"]
        self._log_event(state, "assessment_submitted", {"enrollment_id": enrollment_id, "attempt_id": attempt["id"]})
        self._save(state)
        return attempt

    def submit_assignment(self, enrollment_id: str, lesson_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._state()
        enrollment = self._find_by_id(state["enrollments"], enrollment_id, "Enrollment")
        lesson = self._find_lesson(enrollment["course"], lesson_id)
        if lesson["resource_type"] != "assignment":
            raise ValidationError("Assignment submission is only supported for assignment lessons")

        responses = payload.get("responses", [])
        prompts = lesson.get("assignment_prompts", [])
        if prompts and len(responses) < len(prompts):
            raise ValidationError("Please answer all assignment prompts")

        existing = None
        for item in state["assignment_submissions"]:
            if item["enrollment_id"] == enrollment_id and item["lesson_id"] == lesson_id:
                existing = item
                break

        submission = existing or {
            "id": make_id("asub"),
            "enrollment_id": enrollment_id,
            "learner_id": enrollment["learner_id"],
            "role_id": enrollment["role_id"],
            "lesson_id": lesson_id,
            "created_at": now_iso(),
        }
        submission["responses"] = responses
        submission["submitted_at"] = now_iso()

        if existing is None:
            state["assignment_submissions"].append(submission)
        if lesson_id not in enrollment["completed_lesson_ids"]:
            enrollment["completed_lesson_ids"].append(lesson_id)
        self._log_event(state, "assignment_submitted", {"enrollment_id": enrollment_id, "lesson_id": lesson_id, "submission_id": submission["id"]})
        self._save(state)
        return submission

    def record_kpi_observation(self, learner_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._state()
        learner = self._find_by_id(state["learners"], learner_id, "Learner")
        role = self._find_by_id(state["roles"], learner["role_id"], "Role")
        kpi = self._find_kpi(role, payload.get("kpi_id", ""))
        value = float(payload.get("value", 0))
        target_value = float(payload.get("target_value", kpi["target_value"]))
        if target_value <= 0:
            raise ValidationError("target_value must be greater than 0")

        status = "weak" if (value / target_value) < kpi["weak_threshold"] else "healthy"
        observation = {
            "id": make_id("kpiobs"),
            "learner_id": learner_id,
            "role_id": role["id"],
            "kpi_id": kpi["id"],
            "kpi_name": kpi["name"],
            "value": value,
            "target_value": target_value,
            "period_label": payload.get("period_label", "Current Period"),
            "status": status,
            "notes": payload.get("notes", "").strip(),
            "created_at": now_iso(),
        }
        state["kpi_observations"].append(observation)

        assignments = []
        if status == "weak":
            for remediation in role["remediation_catalog"]:
                if remediation["kpi_id"] != kpi["id"]:
                    continue
                assignment = {
                    "id": make_id("rem"),
                    "learner_id": learner_id,
                    "role_id": role["id"],
                    "kpi_id": kpi["id"],
                    "title": remediation["title"],
                    "summary": remediation["summary"],
                    "lesson_ids": remediation["lesson_ids"],
                    "status": "assigned",
                    "created_at": now_iso(),
                }
                state["remediation_assignments"].append(assignment)
                assignments.append(assignment)
        else:
            for assignment in state["remediation_assignments"]:
                if (
                    assignment["learner_id"] == learner_id
                    and assignment["role_id"] == role["id"]
                    and assignment["kpi_id"] == kpi["id"]
                    and assignment["status"] == "assigned"
                ):
                    assignment["status"] = "resolved"
                    assignment["resolved_at"] = now_iso()

        self._log_event(
            state,
            "kpi_observed",
            {"learner_id": learner_id, "kpi_id": kpi["id"], "status": status, "assignment_count": len(assignments)},
        )
        self._save(state)
        return {"observation": observation, "assignments": assignments}

    def get_trainer_dashboard(self) -> Dict[str, Any]:
        state = self._state()
        roles = state["roles"]
        learners = state["learners"]
        enrollments = state["enrollments"]
        attempts = state["assessment_attempts"]
        observations = state["kpi_observations"]
        remediation = state["remediation_assignments"]

        published_roles = [role for role in roles if role["status"] == "published"]
        total_lessons = 0
        total_completed = 0
        for enrollment in enrollments:
            total_completed += len(enrollment["completed_lesson_ids"])
            total_lessons += sum(len(section["lessons"]) for section in enrollment["course"]["sections"])

        latest_attempts = self._latest_attempts_by_enrollment(attempts)
        assessment_avg = round(
            sum(item["score_percentage"] for item in latest_attempts.values()) / float(len(latest_attempts)),
            2,
        ) if latest_attempts else None

        weak_skill_counter = Counter()
        for attempt in attempts:
            for weak in attempt["weak_skills"]:
                weak_skill_counter[weak["skill_name"]] += 1

        weak_kpi_counter = Counter(item["kpi_name"] for item in observations if item["status"] == "weak")
        role_metrics = []
        for role in published_roles:
            role_learners = [item for item in learners if item["role_id"] == role["id"]]
            role_enrollments = [item for item in enrollments if item["role_id"] == role["id"]]
            role_attempts = [item for item in latest_attempts.values() if item["role_id"] == role["id"]] if latest_attempts else []
            completion_pct = 0.0
            completed = sum(len(item["completed_lesson_ids"]) for item in role_enrollments)
            possible = sum(sum(len(section["lessons"]) for section in item["course"]["sections"]) for item in role_enrollments)
            if possible:
                completion_pct = round((completed / float(possible)) * 100, 2)
            role_metrics.append(
                {
                    "role_id": role["id"],
                    "role_title": role["title"],
                    "segment": role["segment"],
                    "learner_count": len(role_learners),
                    "completion_percentage": completion_pct,
                    "latest_attempt_average": round(
                        sum(item["score_percentage"] for item in role_attempts) / float(len(role_attempts)),
                        2,
                    ) if role_attempts else None,
                }
            )

        return {
            "summary": {
                "roles_published": len(published_roles),
                "learners": len(learners),
                "course_completion_percentage": round((total_completed / float(total_lessons)) * 100, 2) if total_lessons else 0.0,
                "assessment_average": assessment_avg,
                "weak_kpi_observations": sum(
                    1 for item in self._latest_kpi_observations(observations).values() if item["status"] == "weak"
                ),
                "open_remediation_assignments": sum(1 for item in remediation if item["status"] == "assigned"),
                "ai_enabled": self.generator.enabled,
            },
            "role_metrics": role_metrics,
            "weak_skills": [{"label": label, "count": count} for label, count in weak_skill_counter.most_common(6)],
            "weak_kpis": [{"label": label, "count": count} for label, count in weak_kpi_counter.most_common(6)],
            "activity_log": state["activity_log"][-12:][::-1],
        }

    def require_trainer(self, token: str) -> Dict[str, Any]:
        user = self._require_user_by_token(token)
        if self._normalized_user_type(user) != "trainer":
            raise AuthorizationError("Trainer access required")
        return user

    def get_owner_dashboard(self) -> Dict[str, Any]:
        return self.get_trainer_dashboard()

    def require_owner(self, token: str) -> Dict[str, Any]:
        return self.require_trainer(token)

    def require_learner(self, token: str) -> Dict[str, Any]:
        user = self._require_user_by_token(token)
        if user["user_type"] != "learner":
            raise AuthorizationError("Learner access required")
        return user

    def get_my_dashboard(self, token: str) -> Dict[str, Any]:
        user = self.require_learner(token)
        return self.get_learner_dashboard(user["learner_id"])

    def complete_my_lesson(self, token: str, lesson_id: str) -> Dict[str, Any]:
        user = self.require_learner(token)
        state = self._state()
        enrollment = self._get_learner_enrollment(state, user["learner_id"])
        return self.complete_lesson(enrollment["id"], lesson_id)

    def submit_my_assessment(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = self.require_learner(token)
        state = self._state()
        enrollment = self._get_learner_enrollment(state, user["learner_id"])
        return self.submit_assessment(enrollment["id"], payload)

    def record_my_kpi(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = self.require_learner(token)
        return self.record_kpi_observation(user["learner_id"], payload)

    def submit_my_assignment(self, token: str, lesson_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = self.require_learner(token)
        state = self._state()
        enrollment = self._get_learner_enrollment(state, user["learner_id"])
        return self.submit_assignment(enrollment["id"], lesson_id, payload)

    def upload_lesson_media(self, token: str, lesson_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = self._require_user_by_token(token)
        if self._normalized_user_type(user) not in {"trainer", "learner"}:
            raise AuthorizationError("Valid session required")

        encoded = str(payload.get("base64_data", "")).strip()
        extension = str(payload.get("extension", "webm")).strip().lower() or "webm"
        mime_type = str(payload.get("mime_type", "video/webm")).strip() or "video/webm"
        if not encoded:
            raise ValidationError("base64_data is required")

        import base64

        binary = base64.b64decode(encoded)
        asset = self.asset_store.save_binary("video/{0}.{1}".format(lesson_id, extension), binary)

        state = self._state()
        updated = None
        for role in state["roles"]:
            for section in role["course_template"]["sections"]:
                for lesson in section["lessons"]:
                    if lesson["id"] == lesson_id:
                        lesson["media_asset"] = {
                            "kind": "video",
                            "mime_type": mime_type,
                            "relative_path": asset["relative_path"],
                            "url": asset["url"],
                            "stored_at": now_iso(),
                        }
                        updated = lesson["media_asset"]
            for enrollment in state["enrollments"]:
                if enrollment["role_id"] != role["id"]:
                    continue
                for section in enrollment["course"]["sections"]:
                    for lesson in section["lessons"]:
                        if lesson["id"] == lesson_id:
                            lesson["media_asset"] = deepcopy(updated) if updated else lesson.get("media_asset")

        if updated is None:
            raise NotFoundError("Lesson not found: {0}".format(lesson_id))

        state["media_assets"].append(
            {
                "id": make_id("asset"),
                "lesson_id": lesson_id,
                "kind": "video",
                "mime_type": mime_type,
                "relative_path": asset["relative_path"],
                "url": asset["url"],
                "created_at": now_iso(),
            }
        )
        self._save(state)
        return updated

    def _build_role_record(
        self,
        payload: Dict[str, Any],
        package: Dict[str, Any],
        review_note: str,
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        role_id = existing["id"] if existing else make_id("role")
        created_at = existing["created_at"] if existing else now_iso()
        review_notes = deepcopy(existing["review_notes"]) if existing else []
        if review_note:
            review_notes.append({"id": make_id("review"), "text": review_note, "created_at": now_iso()})

        skill_lookup = {}
        skills = []
        for item in package.get("skills", []):
            skill_id = item.get("id") or (existing and self._match_existing_skill(existing, item.get("name", ""))) or make_id("skl")
            skills.append(
                {
                    "id": skill_id,
                    "name": item.get("name", "").strip(),
                    "description": item.get("description", "").strip(),
                    "category": item.get("category", "general").strip(),
                }
            )
            skill_lookup[item.get("name", "").strip().lower()] = skill_id

        kpi_lookup = {}
        kpis = []
        for item in package.get("kpis", []):
            kpi_id = item.get("id") or (existing and self._match_existing_kpi(existing, item.get("name", ""))) or make_id("kpi")
            linked_skill_ids = [skill_lookup[name.lower()] for name in item.get("linked_skill_names", []) if name.lower() in skill_lookup]
            kpis.append(
                {
                    "id": kpi_id,
                    "name": item.get("name", "").strip(),
                    "description": item.get("description", "").strip(),
                    "target_value": item.get("target_value", 100),
                    "unit": item.get("unit", "%"),
                    "weak_threshold": float(item.get("weak_threshold", 0.85)),
                    "linked_skill_ids": linked_skill_ids,
                }
            )
            kpi_lookup[item.get("name", "").strip().lower()] = kpi_id

        learning_path = {
            "status": "in_review",
            "sections": [],
        }
        for section in package.get("learning_path_sections", []):
            learning_path["sections"].append(
                {
                    "id": make_id("pathsec"),
                    "key": section.get("key", "section"),
                    "title": section.get("title", "").strip(),
                    "goal": section.get("goal", "").strip(),
                    "items": [
                        {
                            "id": make_id("pathitem"),
                            "title": item.get("title", "").strip(),
                            "description": item.get("description", "").strip(),
                            "resource_type": item.get("resource_type", "document"),
                            "duration_minutes": int(item.get("duration_minutes", 10)),
                            "skill_ids": [skill_lookup[name.lower()] for name in item.get("skill_names", []) if name.lower() in skill_lookup],
                            "kpi_ids": [kpi_lookup[name.lower()] for name in item.get("kpi_names", []) if name.lower() in kpi_lookup],
                        }
                        for item in section.get("items", [])
                    ],
                }
            )

        course_sections = []
        lesson_map = {}
        for section in package.get("course_sections", []):
            lessons = []
            for lesson in section.get("lessons", []):
                lesson_id = make_id("lesson")
                content_asset = self.asset_store.save_text(
                    "lesson/{0}.md".format(lesson_id),
                    lesson.get("content", "").strip(),
                )
                lesson_record = {
                    "id": lesson_id,
                    "title": lesson.get("title", "").strip(),
                    "resource_type": lesson.get("resource_type", "document"),
                    "summary": lesson.get("summary", "").strip(),
                    "content": lesson.get("content", "").strip(),
                    "duration_minutes": int(lesson.get("duration_minutes", 10)),
                    "skill_ids": [skill_lookup[name.lower()] for name in lesson.get("skill_names", []) if name.lower() in skill_lookup],
                    "kpi_ids": [kpi_lookup[name.lower()] for name in lesson.get("kpi_names", []) if name.lower() in kpi_lookup],
                    "content_asset": {
                        "kind": "lesson_content",
                        "relative_path": content_asset["relative_path"],
                        "url": content_asset["url"],
                    },
                }
                if lesson_record["resource_type"] == "video":
                    storyboard_asset = self.asset_store.save_json(
                        "storyboard/{0}.json".format(lesson_id),
                        {
                            "title": lesson_record["title"],
                            "summary": lesson_record["summary"],
                            "content": lesson_record["content"],
                            "duration_minutes": lesson_record["duration_minutes"],
                        },
                    )
                    lesson_record["media_asset"] = {
                        "kind": "video_storyboard",
                        "relative_path": storyboard_asset["relative_path"],
                        "url": storyboard_asset["url"],
                        "status": "pending_video_upload",
                    }
                if lesson_record["resource_type"] == "assignment":
                    lesson_record["assignment_prompts"] = self._build_assignment_prompts(
                        lesson_record["title"],
                        lesson_record["summary"],
                        lesson_record["content"],
                    )
                lessons.append(lesson_record)
                lesson_map[lesson_record["title"].lower()] = lesson_id
            course_sections.append(
                {
                    "id": make_id("coursesection"),
                    "key": section.get("key", "section"),
                    "title": section.get("title", "").strip(),
                    "description": section.get("description", "").strip(),
                    "lessons": lessons,
                }
            )

        questions = []
        for question in package.get("assessment", {}).get("questions", []):
            questions.append(
                {
                    "id": make_id("q"),
                    "prompt": question.get("prompt", "").strip(),
                    "options": [option.strip() for option in question.get("options", [])],
                    "correct_option_index": int(question.get("correct_option_index", 0)),
                    "explanation": question.get("explanation", "").strip(),
                    "skill_ids": [skill_lookup[name.lower()] for name in question.get("skill_names", []) if name.lower() in skill_lookup],
                    "kpi_ids": [kpi_lookup[name.lower()] for name in question.get("kpi_names", []) if name.lower() in kpi_lookup],
                }
            )
        assessment_asset = self.asset_store.save_json(
            "assessment/{0}.json".format(role_id),
            {
                "title": package.get("assessment", {}).get("title", "Role Mastery Check"),
                "questions": questions,
            },
        )

        remediation_catalog = []
        for item in package.get("remediation_paths", []):
            kpi_name = item.get("kpi_name", "").strip().lower()
            if kpi_name not in kpi_lookup:
                continue
            lesson_ids = [
                lesson_map[lesson_title.lower()]
                for lesson_title in item.get("lesson_titles", [])
                if lesson_title.lower() in lesson_map
            ]
            remediation_catalog.append(
                {
                    "id": make_id("remcat"),
                    "kpi_id": kpi_lookup[kpi_name],
                    "title": item.get("title", "").strip(),
                    "summary": item.get("summary", "").strip(),
                    "lesson_ids": lesson_ids,
                }
            )

        return {
            "id": role_id,
            "segment": payload.get("segment", "").strip(),
            "title": payload.get("title", "").strip(),
            "level": payload.get("level", "").strip(),
            "legacy_mappings": self._normalize_lines(payload.get("legacy_mappings", [])),
            "work_summary": payload.get("work_summary", "").strip(),
            "responsibilities": self._normalize_lines(payload.get("responsibilities", [])),
            "summary": package.get("summary", "").strip(),
            "legacy_mapping_notes": package.get("legacy_mapping_notes", "").strip(),
            "skills": skills,
            "kpis": kpis,
            "learning_path": learning_path,
            "review_notes": review_notes,
            "course_template": {
                "id": make_id("course"),
                "title": "{0} Role Academy".format(payload.get("title", "").strip()),
                "description": "AI-generated role course for {0}.".format(payload.get("title", "").strip()),
                "sections": course_sections,
                "assessment": {
                    "id": make_id("assessment"),
                    "title": package.get("assessment", {}).get("title", "Role Mastery Check"),
                    "passing_score": int(package.get("assessment", {}).get("passing_score", 70)),
                    "questions": questions,
                    "content_asset": {
                        "kind": "assessment_bank",
                        "relative_path": assessment_asset["relative_path"],
                        "url": assessment_asset["url"],
                    },
                },
            },
            "remediation_catalog": remediation_catalog,
            "status": existing["status"] if existing else "draft",
            "created_at": created_at,
            "updated_at": now_iso(),
            "published_at": existing.get("published_at") if existing else None,
        }

    def _build_enrollment(self, learner: Dict[str, Any], role: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": make_id("enr"),
            "learner_id": learner["id"],
            "role_id": role["id"],
            "course": deepcopy(role["course_template"]),
            "role_snapshot": {"skills": deepcopy(role["skills"]), "kpis": deepcopy(role["kpis"])},
            "completed_lesson_ids": [],
            "last_assessment_attempt_id": None,
            "created_at": now_iso(),
        }

    def _build_attempt_summary(
        self,
        score_pct: float,
        weak_skills: List[Dict[str, Any]],
        weak_kpis: List[Dict[str, Any]],
    ) -> str:
        if not weak_skills and not weak_kpis:
            return "Strong attempt. Keep applying the course in live operations."
        parts = ["Assessment score: {0}%.".format(score_pct)]
        if weak_skills:
            parts.append("Weak skills: {0}.".format(", ".join(item["skill_name"] for item in weak_skills)))
        if weak_kpis:
            parts.append("Likely KPI risk areas: {0}.".format(", ".join(item["kpi_name"] for item in weak_kpis)))
        parts.append("Revisit linked lessons before the next attempt.")
        return " ".join(parts)

    def _find_by_id(self, items: List[Dict[str, Any]], item_id: str, label: str) -> Dict[str, Any]:
        for item in items:
            if item["id"] == item_id:
                return item
        raise NotFoundError("{0} not found: {1}".format(label, item_id))

    def _find_user_by_phone(self, state: Dict[str, Any], phone_number: str) -> Dict[str, Any]:
        for user in state["users"]:
            if user["phone_number"] == phone_number:
                return user
        raise NotFoundError("User not found for phone_number: {0}".format(phone_number))

    def _find_lesson(self, course: Dict[str, Any], lesson_id: str) -> Dict[str, Any]:
        for section in course["sections"]:
            for lesson in section["lessons"]:
                if lesson["id"] == lesson_id:
                    return lesson
        raise NotFoundError("Lesson not found: {0}".format(lesson_id))

    def _build_assignment_prompts(self, title: str, summary: str, content: str) -> List[Dict[str, str]]:
        prompts = []
        lines = [line.strip("- ").strip() for line in str(content).splitlines() if line.strip()]
        focus_lines = [line for line in lines if len(line) > 12][:3]
        for index, line in enumerate(focus_lines[:2], start=1):
            prompts.append(
                {
                    "id": make_id("aprompt"),
                    "prompt": "Prompt {0}: {1}".format(index, line),
                    "expected_response": "Describe the concrete action you will take for this point.",
                }
            )
        prompts.append(
            {
                "id": make_id("aprompt"),
                "prompt": "What action will you apply from {0} in the next operating cycle?".format(title),
                "expected_response": summary or "Explain the action, owner, and timing.",
            }
        )
        prompts.append(
            {
                "id": make_id("aprompt"),
                "prompt": "How will you know this assignment worked on the floor?",
                "expected_response": "Mention the KPI, behaviour change, or observation you will track.",
            }
        )
        return prompts[:3]

    def _find_skill(self, role_snapshot: Dict[str, Any], skill_id: str) -> Dict[str, Any]:
        for skill in role_snapshot["skills"]:
            if skill["id"] == skill_id:
                return skill
        raise NotFoundError("Skill not found: {0}".format(skill_id))

    def _find_kpi(self, role: Dict[str, Any], kpi_id: str) -> Dict[str, Any]:
        for kpi in role["kpis"]:
            if kpi["id"] == kpi_id:
                return kpi
        raise NotFoundError("KPI not found: {0}".format(kpi_id))

    def _match_existing_skill(self, role: Dict[str, Any], name: str) -> Optional[str]:
        for skill in role.get("skills", []):
            if skill["name"].lower() == name.lower():
                return skill["id"]
        return None

    def _match_existing_kpi(self, role: Dict[str, Any], name: str) -> Optional[str]:
        for kpi in role.get("kpis", []):
            if kpi["name"].lower() == name.lower():
                return kpi["id"]
        return None

    def _state(self) -> Dict[str, Any]:
        self._ensure_trainer_account()
        return self.store.load()

    def _save(self, state: Dict[str, Any]) -> None:
        self.store.save(state)

    def _log_event(self, state: Dict[str, Any], event_type: str, payload: Dict[str, Any]) -> None:
        state["activity_log"].append(
            {
                "id": make_id("evt"),
                "type": event_type,
                "payload": payload,
                "created_at": now_iso(),
            }
        )

    def _get_learner_enrollment(self, state: Dict[str, Any], learner_id: str) -> Dict[str, Any]:
        for enrollment in state["enrollments"]:
            if enrollment["learner_id"] == learner_id:
                return enrollment
        raise NotFoundError("Enrollment not found for learner: {0}".format(learner_id))

    def _get_enrollment(self, state: Dict[str, Any], learner_id: str, role_id: str) -> Optional[Dict[str, Any]]:
        for enrollment in state["enrollments"]:
            if enrollment["learner_id"] == learner_id and enrollment["role_id"] == role_id:
                return enrollment
        return None

    def _require_user_by_token(self, token: str) -> Dict[str, Any]:
        if not token:
            raise AuthorizationError("Authentication required")
        state = self._state()
        session = None
        for item in state["sessions"]:
            if item["token"] == token:
                session = item
                break
        if session is None:
            raise AuthorizationError("Invalid session")
        return self._find_by_id(state["users"], session["user_id"], "User")

    def _present_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user["id"],
            "name": user["name"],
            "phone_number": user["phone_number"],
            "user_type": self._normalized_user_type(user),
            "learner_id": user.get("learner_id"),
            "role_id": user.get("role_id"),
            "last_login_at": user.get("last_login_at"),
        }

    def _normalize_phone(self, value: str) -> str:
        phone = "".join(char for char in str(value) if char.isdigit())
        if len(phone) < 10:
            raise ValidationError("phone_number must have at least 10 digits")
        return phone

    def _ensure_trainer_account(self) -> None:
        state = self.store.load()
        for user in state.get("users", []):
            if user.get("user_type") == "trainer":
                return
            if user.get("user_type") == "owner":
                user["user_type"] = "trainer"
                if not user.get("name"):
                    user["name"] = self.default_trainer_name
                state["activity_log"].append(
                    {
                        "id": make_id("evt"),
                        "type": "trainer_migrated",
                        "payload": {"user_id": user["id"], "phone_number": user["phone_number"]},
                        "created_at": now_iso(),
                    }
                )
                self.store.save(state)
                return
        trainer = {
            "id": make_id("usr"),
            "name": self.default_trainer_name,
            "phone_number": self._normalize_phone(self.default_trainer_phone),
            "user_type": "trainer",
            "learner_id": None,
            "role_id": None,
            "created_at": now_iso(),
            "login_code": self.default_trainer_code,
            "login_code_issued_at": now_iso(),
            "last_login_at": None,
        }
        state["users"].append(trainer)
        state["activity_log"].append(
            {
                "id": make_id("evt"),
                "type": "trainer_seeded",
                "payload": {"user_id": trainer["id"], "phone_number": trainer["phone_number"]},
                "created_at": now_iso(),
            }
        )
        self.store.save(state)

    def _normalized_user_type(self, user: Dict[str, Any]) -> str:
        if user.get("user_type") == "owner":
            return "trainer"
        return user.get("user_type", "")

    def _latest_attempts_by_enrollment(self, attempts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        latest = {}
        for attempt in attempts:
            current = latest.get(attempt["enrollment_id"])
            if current is None or attempt["submitted_at"] > current["submitted_at"]:
                latest[attempt["enrollment_id"]] = attempt
        return latest

    def _latest_kpi_observations(self, observations: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        latest = {}
        for observation in observations:
            key = "{0}:{1}".format(observation["learner_id"], observation["kpi_id"])
            current = latest.get(key)
            if current is None or observation["created_at"] > current["created_at"]:
                latest[key] = observation
        return latest

    def _normalize_lines(self, value: Any) -> List[str]:
        if isinstance(value, str):
            parts = value.splitlines()
        else:
            parts = list(value)
        return [item.strip() for item in parts if str(item).strip()]
