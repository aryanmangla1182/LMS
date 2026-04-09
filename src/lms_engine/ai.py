"""AI generation support for the LMS MVP."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from urllib import error, request


class AIContentGenerator:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_role_package(self, payload: Dict[str, Any], review_note: str = "") -> Dict[str, Any]:
        if not self.enabled:
            return self._fallback_package(payload, review_note)

        try:
            return self._openai_package(payload, review_note)
        except Exception:
            return self._fallback_package(payload, review_note)

    def analyze_sales_pitch(
        self,
        transcript: str,
        role_title: str,
        role_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not transcript.strip():
            return {
                "overall_score": 0,
                "summary": "No pitch transcript was available for analysis.",
                "strengths": [],
                "improvements": ["Record a clear pitch and retry the analyzer."],
                "rubric": [],
                "recommended_next_step": "Retry with a clearer opening, customer discovery, and close.",
            }
        if not self.enabled:
            return self._fallback_pitch_analysis(transcript, role_title, role_context or {})
        try:
            return self._openai_pitch_analysis(transcript, role_title, role_context or {})
        except Exception:
            return self._fallback_pitch_analysis(transcript, role_title, role_context or {})

    def _openai_package(self, payload: Dict[str, Any], review_note: str) -> Dict[str, Any]:
        responsibilities = payload.get("responsibilities", [])
        input_skills = [item.strip() for item in payload.get("skills", []) if str(item).strip()]
        input_kpis = payload.get("kpis", [])
        prompt = {
            "segment": payload.get("segment", ""),
            "role_title": payload.get("title", ""),
            "role_level": payload.get("level", ""),
            "legacy_mappings": payload.get("legacy_mappings", []),
            "work_summary": payload.get("work_summary", ""),
            "responsibilities": responsibilities,
            "must_use_skills": input_skills,
            "must_use_kpis": input_kpis,
            "review_note": review_note,
        }

        system_prompt = (
            "You generate workforce learning blueprints for an internal LMS. "
            "Return only valid JSON. Build a role package with realistic skills, KPIs, "
            "learning-path sections, course sections, quiz questions, and KPI remediation paths. "
            "Each course must include compliance content, current-level growth content, and next-level growth content. "
            "If must_use_skills or must_use_kpis are provided, preserve them exactly and build around them."
        )
        user_prompt = (
            "Generate JSON for this role package. "
            "Use concise but useful content. Ensure remediation paths connect weak KPIs to specific lessons. "
            "JSON schema keys required: summary, legacy_mapping_notes, skills, kpis, learning_path_sections, "
            "course_sections, assessment, remediation_paths. "
            "JSON input: {0}".format(json.dumps(prompt))
        )
        body = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            "text": {"format": {"type": "json_object"}},
        }
        req = request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Bearer {0}".format(self.api_key),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise RuntimeError(exc.read().decode("utf-8")) from exc

        text = self._extract_output_text(data)
        return json.loads(text)

    def _extract_output_text(self, data: Dict[str, Any]) -> str:
        if data.get("output_text"):
            return data["output_text"]
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return text
        raise RuntimeError("No text output found in AI response")

    def _openai_pitch_analysis(
        self,
        transcript: str,
        role_title: str,
        role_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        system_prompt = (
            "You evaluate frontline retail and service sales pitches for an internal LMS. "
            "Return only valid JSON and score the pitch on a practical coaching rubric."
        )
        user_prompt = {
            "role_title": role_title,
            "role_context": role_context,
            "transcript": transcript,
            "required_schema": {
                "overall_score": "0-100 number",
                "summary": "short coaching summary",
                "strengths": ["list of strengths"],
                "improvements": ["list of improvements"],
                "rubric": [
                    {
                        "category": "Opening Clarity | Need Discovery | Product Explanation | Objection Handling | Confidence And Close",
                        "score": "0-100 number",
                        "reason": "short reason",
                    }
                ],
                "recommended_next_step": "one clear next coaching step",
            },
        }
        body = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": json.dumps(user_prompt)}],
                },
            ],
            "text": {"format": {"type": "json_object"}},
        }
        req = request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Bearer {0}".format(self.api_key),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise RuntimeError(exc.read().decode("utf-8")) from exc
        return json.loads(self._extract_output_text(data))

    def _fallback_pitch_analysis(
        self,
        transcript: str,
        role_title: str,
        role_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = transcript.lower()
        word_count = len([word for word in transcript.split() if word.strip()])

        categories = [
            (
                "Opening Clarity",
                ["hello", "hi", "good", "welcome", "today", role_title.lower()],
                "Start with a sharper opening that names the customer context and reason for the conversation.",
            ),
            (
                "Need Discovery",
                ["need", "goal", "looking", "use", "routine", "problem", "help"],
                "Ask more discovery questions before moving into the recommendation.",
            ),
            (
                "Product Explanation",
                ["feature", "benefit", "plan", "membership", "product", "service", "because"],
                "Explain the recommendation more clearly using benefits tied to customer needs.",
            ),
            (
                "Objection Handling",
                ["cost", "price", "budget", "concern", "issue", "worry", "understand"],
                "Address objections more directly with empathy and one concrete response.",
            ),
            (
                "Confidence And Close",
                ["recommend", "next step", "today", "start", "signup", "book", "join", "close"],
                "End with a clearer recommendation and call to action.",
            ),
        ]

        rubric = []
        improvements: List[str] = []
        strengths: List[str] = []

        for category, keywords, improvement in categories:
            hits = sum(1 for keyword in keywords if keyword in normalized)
            base_score = 45 + min(hits, 4) * 12
            if word_count > 120:
                base_score += 6
            elif word_count < 45:
                base_score -= 8
            score = max(20, min(95, base_score))
            if score >= 75:
                strengths.append("{0} looked solid in this pitch.".format(category))
                reason = "The transcript shows enough evidence of {0}.".format(category.lower())
            else:
                improvements.append(improvement)
                reason = "The transcript does not show enough evidence of {0}.".format(category.lower())
            rubric.append(
                {
                    "category": category,
                    "score": score,
                    "reason": reason,
                }
            )

        if not strengths:
            strengths.append("The learner attempted a full pitch and created enough material for coaching.")

        overall_score = round(sum(item["score"] for item in rubric) / float(len(rubric)), 2)
        lowest = min(rubric, key=lambda item: item["score"])

        summary = (
            "This pitch for the {0} role is at {1}/100. "
            "The clearest coaching opportunity is {2}."
        ).format(role_title, overall_score, lowest["category"].lower())

        if role_context.get("kpis"):
            improvements.append(
                "Tie the pitch more clearly to business outcomes such as {0}.".format(
                    ", ".join(role_context["kpis"][:2])
                )
            )

        return {
            "overall_score": overall_score,
            "summary": summary,
            "strengths": strengths[:3],
            "improvements": improvements[:4],
            "rubric": rubric,
            "recommended_next_step": "Retry the pitch with extra focus on {0}.".format(lowest["category"].lower()),
        }

    def _fallback_package(self, payload: Dict[str, Any], review_note: str) -> Dict[str, Any]:
        title = payload.get("title", "Role").strip() or "Role"
        level = payload.get("level", "L1").strip() or "L1"
        segment = payload.get("segment", "Operations").strip() or "Operations"
        responsibilities = [item.strip() for item in payload.get("responsibilities", []) if item.strip()]
        input_skills = [item.strip() for item in payload.get("skills", []) if str(item).strip()]
        input_kpis = payload.get("kpis", [])
        if not responsibilities:
            responsibilities = [
                "Deliver reliable day-to-day execution",
                "Coach the team on expected standards",
                "Maintain process and KPI discipline",
            ]

        review_suffix = " Updated after review: {0}.".format(review_note.strip()) if review_note.strip() else ""

        if input_skills:
            skill_names = [(name, "custom") for name in input_skills]
        else:
            skill_names = self._default_skill_names(title, responsibilities)
        skills = [
            {
                "name": name,
                "description": "{0} for the {1} role in {2}.{3}".format(name, title, segment, review_suffix),
                "category": category,
            }
            for name, category in skill_names
        ]
        if input_kpis:
            kpis = []
            for index, item in enumerate(input_kpis):
                linked = [skills[index % len(skills)]["name"]] if skills else []
                if len(skills) > 1:
                    linked.append(skills[(index + 1) % len(skills)]["name"])
                kpis.append(
                    {
                        "name": item.get("name", "KPI").strip(),
                        "description": item.get("description", "Measures role performance.").strip(),
                        "target_value": item.get("target_value", 100),
                        "unit": item.get("unit", "%"),
                        "weak_threshold": float(item.get("weak_threshold", 0.85)),
                        "linked_skill_names": linked,
                    }
                )
        else:
            kpis = [
                {
                    "name": "Execution Score",
                    "description": "Measures consistency of operational execution.",
                    "target_value": 90,
                    "unit": "%",
                    "weak_threshold": 0.88,
                    "linked_skill_names": [skills[0]["name"], skills[1]["name"]],
                },
                {
                    "name": "Customer Experience",
                    "description": "Measures service quality and issue handling.",
                    "target_value": 4.6,
                    "unit": "/5",
                    "weak_threshold": 0.9,
                    "linked_skill_names": [skills[1]["name"], skills[2]["name"]],
                },
                {
                    "name": "Growth Readiness",
                    "description": "Measures progression against the next-level behaviors.",
                    "target_value": 85,
                    "unit": "%",
                    "weak_threshold": 0.85,
                    "linked_skill_names": [skills[2]["name"], skills[3]["name"]],
                },
            ]
        learning_path_sections = [
            {
                "key": "compliance",
                "title": "Compliance and Operating Standards",
                "goal": "Make sure the learner is compliant and reliable in the current role.",
                "items": [
                    {
                        "title": "{0} SOP Foundations".format(title),
                        "description": "Video lesson on non-negotiable operating standards, handoff process, and policy essentials.",
                        "skill_names": [skills[0]["name"]],
                        "kpi_names": [kpis[0]["name"]],
                        "resource_type": "video",
                        "duration_minutes": 1,
                    },
                    {
                        "title": "{0} Risk and Escalation Drill".format(title),
                        "description": "Scenario-based video on handling exceptions, escalations, and recovery without breaking process.",
                        "skill_names": [skills[0]["name"], skills[1]["name"]],
                        "kpi_names": [kpis[0]["name"]],
                        "resource_type": "video",
                        "duration_minutes": 1,
                    },
                    {
                        "title": "Policy and Safety Checklist",
                        "description": "Mandatory on-floor checklist covering policy, safety, and reporting controls.",
                        "skill_names": [skills[1]["name"]],
                        "kpi_names": [kpis[0]["name"]],
                        "resource_type": "assignment",
                        "duration_minutes": 12,
                    },
                ],
            },
            {
                "key": "current_growth",
                "title": "Grow Stronger in the Current Level",
                "goal": "Improve performance in the current role through role-critical skills.",
                "items": [
                    {
                        "title": "{0} Performance Coaching".format(title),
                        "description": "Manager-style video on sharpening team rhythm, service quality, and daily execution habits.",
                        "skill_names": [skills[1]["name"], skills[2]["name"]],
                        "kpi_names": [kpis[min(1, len(kpis) - 1)]["name"], kpis[0]["name"]],
                        "resource_type": "video",
                        "duration_minutes": 1,
                    },
                    {
                        "title": "{0} KPI Recovery Moves".format(title),
                        "description": "Video lesson on diagnosing weak KPIs and selecting the right daily recovery actions.",
                        "skill_names": [skills[0]["name"], skills[2]["name"], skills[3]["name"]],
                        "kpi_names": [kpis[0]["name"]],
                        "resource_type": "video",
                        "duration_minutes": 1,
                    },
                    {
                        "title": "Decision-Making in Live Operations",
                        "description": "Decision brief for handling day-to-day tradeoffs with speed and consistency.",
                        "skill_names": [skills[0]["name"], skills[2]["name"]],
                        "kpi_names": [kpis[0]["name"], kpis[min(1, len(kpis) - 1)]["name"]],
                        "resource_type": "document",
                        "duration_minutes": 15,
                    },
                ],
            },
            {
                "key": "next_growth",
                "title": "Prepare for the Next Level",
                "goal": "Build the behaviors and judgement needed for the next role.",
                "items": [
                    {
                        "title": "Leading Beyond the Current Role",
                        "description": "Leadership video focused on ownership, influence, and next-level communication.",
                        "skill_names": [skills[3]["name"], skills[4]["name"]],
                        "kpi_names": [kpis[min(2, len(kpis) - 1)]["name"]],
                        "resource_type": "video",
                        "duration_minutes": 1,
                    },
                    {
                        "title": "{0} Team Development Lab".format(title),
                        "description": "Video lesson on coaching successors, delegating effectively, and building bench strength.",
                        "skill_names": [skills[3]["name"], skills[4]["name"]],
                        "kpi_names": [kpis[min(2, len(kpis) - 1)]["name"]],
                        "resource_type": "video",
                        "duration_minutes": 1,
                    },
                    {
                        "title": "Next-Level Business Review Assignment",
                        "description": "Apply role thinking to a broader operating problem.",
                        "skill_names": [skills[4]["name"]],
                        "kpi_names": [kpis[min(2, len(kpis) - 1)]["name"]],
                        "resource_type": "assignment",
                        "duration_minutes": 25,
                    },
                ],
            },
        ]

        course_sections = []
        for section in learning_path_sections:
            lessons = []
            for item in section["items"]:
                lessons.append(
                    {
                        "title": item["title"],
                        "resource_type": item["resource_type"],
                        "summary": item["description"],
                        "content": self._lesson_content(
                            title,
                            level,
                            segment,
                            item["title"],
                            item["resource_type"],
                            item["skill_names"],
                            item["kpi_names"],
                            responsibilities,
                            review_note,
                        ),
                        "skill_names": item["skill_names"],
                        "kpi_names": item["kpi_names"],
                        "duration_minutes": item["duration_minutes"],
                    }
                )
            course_sections.append(
                {
                    "key": section["key"],
                    "title": section["title"],
                    "description": section["goal"],
                    "lessons": lessons,
                }
            )

        assessment = {
            "title": "{0} Mastery Check".format(title),
            "passing_score": 75,
            "questions": self._default_questions(title, skills, kpis, responsibilities),
        }
        remediation_paths = []
        for kpi in kpis:
            remediation_paths.append(
                {
                    "kpi_name": kpi["name"],
                    "title": "{0} Recovery Sprint".format(kpi["name"]),
                    "summary": "Targeted lessons and retest for weak {0}.".format(kpi["name"]),
                    "lesson_titles": [course_sections[1]["lessons"][0]["title"], course_sections[0]["lessons"][0]["title"]],
                }
            )

        return {
            "summary": "{0} blueprint for the {1} segment at level {2}.{3}".format(title, segment, level, review_suffix),
            "legacy_mapping_notes": "Legacy role mapping: {0}".format(", ".join(payload.get("legacy_mappings", [])) or "No mapping provided"),
            "skills": skills,
            "kpis": kpis,
            "learning_path_sections": learning_path_sections,
            "course_sections": course_sections,
            "assessment": assessment,
            "remediation_paths": remediation_paths,
        }

    def _default_skill_names(self, title: str, responsibilities: List[str]) -> List[tuple[str, str]]:
        base = [
            ("Operational Discipline", "operations"),
            ("People Coaching", "people"),
            ("Customer and Service Recovery", "service"),
            ("Growth Leadership", "leadership"),
            ("Business Review and Planning", "commercial"),
        ]
        if "manager" not in title.lower():
            base[-1] = ("Personal Ownership and Escalation", "execution")
        return base

    def _lesson_content(
        self,
        title: str,
        level: str,
        segment: str,
        lesson_title: str,
        resource_type: str,
        skill_names: List[str],
        kpi_names: List[str],
        responsibilities: List[str],
        review_note: str,
    ) -> str:
        lines = [
            "Format: {0}".format(resource_type.title()),
            "Role: {0} | Segment: {1} | Level: {2}".format(title, segment, level),
            "Lesson: {0}".format(lesson_title),
            "",
            "What this module covers:",
        ]
        lines.extend("- {0}".format(item) for item in responsibilities[:3])
        if skill_names:
            lines.append("")
            lines.append("Primary skills:")
            lines.extend("- {0}".format(item) for item in skill_names[:3])
        if kpi_names:
            lines.append("")
            lines.append("KPIs supported:")
            lines.extend("- {0}".format(item) for item in kpi_names[:3])
        lines.extend(
            [
                "",
                "Scenario:",
                "You are running a live shift and one of the role-critical KPIs starts slipping while service quality is under pressure.",
                "",
                "What good looks like:",
                "- Spot the issue early",
                "- Coach the team with one clear action",
                "- Protect compliance before chasing output",
                "- Recheck the KPI after the intervention",
                "",
                "On-floor drill:",
                "Apply one improvement move from this module in the next operating cycle and note the result.",
            ]
        )
        if review_note.strip():
            lines.append("")
            lines.append("Reviewer request addressed: {0}".format(review_note.strip()))
        return "\n".join(lines)

    def _default_questions(
        self,
        title: str,
        skills: List[Dict[str, Any]],
        kpis: List[Dict[str, Any]],
        responsibilities: List[str],
    ) -> List[Dict[str, Any]]:
        first_kpi = kpis[0]["name"]
        second_kpi = kpis[min(1, len(kpis) - 1)]["name"]
        third_kpi = kpis[min(2, len(kpis) - 1)]["name"]
        return [
            {
                "prompt": "Which action best protects compliance in the {0} role?".format(title),
                "options": [
                    "Skip SOP checks when the floor is busy",
                    "Follow the checklist even under pressure",
                    "Wait for a manager before acting",
                    "Focus only on revenue outcomes",
                ],
                "correct_option_index": 1,
                "explanation": "Reliable execution starts with standard work even during high pressure periods.",
                "skill_names": [skills[0]["name"]],
                "kpi_names": [first_kpi],
            },
            {
                "prompt": "What is the best first response when a KPI drops below target?",
                "options": [
                    "Ignore it for one month",
                    "Blame the team",
                    "Review the linked skill gap and respond with targeted coaching",
                    "Assign every course again",
                ],
                "correct_option_index": 2,
                "explanation": "The right response is targeted remediation tied to the actual skill and KPI weakness.",
                "skill_names": [skills[1]["name"], skills[2]["name"]],
                "kpi_names": [first_kpi, second_kpi],
            },
            {
                "prompt": "Which behavior best prepares someone for the next role?",
                "options": [
                    "Only complete mandatory tasks",
                    "Think beyond own shift and review broader outcomes",
                    "Avoid difficult conversations",
                    "Rely on manager escalation for every decision",
                ],
                "correct_option_index": 1,
                "explanation": "Next-level readiness requires broader ownership and decision quality.",
                "skill_names": [skills[3]["name"], skills[4]["name"]],
                "kpi_names": [third_kpi],
            },
            {
                "prompt": "A repeated customer issue appears in the same week. What should happen next?",
                "options": [
                    "Treat each issue as unrelated",
                    "Escalate only if the customer asks",
                    "Capture the pattern, coach the team, and adjust execution",
                    "Pause all KPI reviews",
                ],
                "correct_option_index": 2,
                "explanation": "Pattern recognition and corrective coaching improve service and execution KPIs.",
                "skill_names": [skills[1]["name"], skills[2]["name"]],
                "kpi_names": [second_kpi],
            },
            {
                "prompt": "A team member keeps missing the daily standard that protects {0}. What is the best manager move?".format(first_kpi),
                "options": [
                    "Wait until the monthly review",
                    "Coach on the missed standard immediately and observe the next cycle",
                    "Escalate without any local intervention",
                    "Replace the KPI target with a lower one",
                ],
                "correct_option_index": 1,
                "explanation": "Immediate coaching tied to the missed standard is the fastest way to recover a weak KPI.",
                "skill_names": [skills[1]["name"], skills[3]["name"]],
                "kpi_names": [first_kpi],
            },
            {
                "prompt": "Which action is most likely to improve {0} without hurting service quality?".format(second_kpi),
                "options": [
                    "Push random upsells without understanding the need",
                    "Use product recommendations linked to the customer need and current basket",
                    "Skip service steps to save time",
                    "Reduce coaching to focus only on billing speed",
                ],
                "correct_option_index": 1,
                "explanation": "Better commercial outcomes come from relevant recommendations and consistent service behavior.",
                "skill_names": [skills[2]["name"], skills[3]["name"]],
                "kpi_names": [second_kpi],
            },
            {
                "prompt": "You are reviewing end-of-day performance and {0} is weak for the third time this week. What should happen?".format(third_kpi),
                "options": [
                    "Treat it as random variation",
                    "Capture the pattern, review root cause, and assign targeted learning",
                    "Stop reporting it for a week",
                    "Change the KPI definition",
                ],
                "correct_option_index": 1,
                "explanation": "Repeated KPI weakness needs pattern review and targeted intervention, not guesswork.",
                "skill_names": [skills[0]["name"], skills[4]["name"]],
                "kpi_names": [third_kpi],
            },
            {
                "prompt": "Which response shows the strongest next-level judgement for the {0} role?".format(title),
                "options": [
                    "Optimise only your own shift outcomes",
                    "Build a repeatable fix the team can use after you leave the floor",
                    "Wait for your manager to decide",
                    "Focus only on the easiest KPI to move",
                ],
                "correct_option_index": 1,
                "explanation": "Next-level behaviour creates repeatable team capability, not one-off heroics.",
                "skill_names": [skills[3]["name"], skills[4]["name"]],
                "kpi_names": [first_kpi, third_kpi],
            },
            {
                "prompt": "What is the best evidence that a weak topic from training has actually improved on the job?",
                "options": [
                    "The learner says they understood the video",
                    "The linked KPI improves and the operating behavior is observed consistently",
                    "The learner watched the lesson twice",
                    "A manager assumes it is fixed",
                ],
                "correct_option_index": 1,
                "explanation": "The platform should connect learning completion to KPI recovery and observed execution quality.",
                "skill_names": [skills[0]["name"], skills[2]["name"]],
                "kpi_names": [first_kpi, second_kpi],
            },
        ]
