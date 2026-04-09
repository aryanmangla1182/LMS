# LMS Engine MVP

This is a working LMS MVP for role-based learning, assessments, KPI remediation, and trainer metrics.

## What It Does

- generate a role blueprint from role inputs
- review and publish a role learning path
- create AI-generated or fallback-generated course content
- enroll learners into the published role course
- let learners complete lessons and submit assessments
- analyze weak skills and likely KPI risk areas from assessment results
- record KPI observations and assign KPI-specific remediation
- show trainer metrics for role performance, weak skills, weak KPIs, and recent activity

## AI Support

If `OPENAI_API_KEY` is set, the role blueprint and course draft use the OpenAI Responses API.

If `OPENAI_API_KEY` is not set, the app still works using a deterministic fallback generator.

Optional environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` default: `gpt-4.1-mini`
- `HOST` default: `127.0.0.1`
- `PORT` default: `8000`

## Run

```bash
python3 main.py
```

If port `8000` is busy:

```bash
PORT=8010 python3 main.py
```

The UI is served from `/`.

## Main Flows

### Admin Studio

- create or generate a role blueprint
- review the AI draft
- publish the role
- create learner enrollments

### Learner Experience

- open assigned course
- mark lessons complete
- take the assessment
- inspect weak-skill analysis
- record KPI observations
- receive remediation when KPIs are weak

### Trainer Metrics

- learner counts
- completion percentage
- assessment averages
- weak skill hotspots
- weak KPI hotspots
- event log

## Persistence

App state is stored in:

- `src/lms_engine/data/state.json`

This is file-backed persistence for MVP use, not a production database.

## Test

```bash
python3 -m unittest discover -s tests
```
