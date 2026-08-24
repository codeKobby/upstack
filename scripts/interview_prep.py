#!/usr/bin/env python3
"""Plan evidence-backed, progressive software-engineering interview preparation.

This helper is deliberately deterministic. It does not browse, claim access to
leaked questions, assess a learner's answer, call an external MCP, or write
files unless --write is supplied. The host agent supplies the job description,
search results, candidate reports, and (when requested) an attempt; the agent
then explains and evaluates the returned contract in the learner's chosen
output mode.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
EVIDENCE_CLASSES = (
    "verified_requirement",
    "official_company_signal",
    "high_confidence_public_pattern",
    "plausible_requirement_derived",
    "practice_only",
)

COMPETENCY_RULES: dict[str, tuple[str, ...]] = {
    "frontend": ("react", "frontend", "front-end", "javascript", "typescript", "browser", "accessibility", "web performance", "css"),
    "backend": ("backend", "back-end", "api", "service", "microservice", "distributed", "database", "sql", "python", "java", "go"),
    "data": ("data", "analytics", "pipeline", "warehouse", "etl", "spark", "sql", "machine learning", "ml"),
    "systems": ("systems", "infra", "infrastructure", "kubernetes", "docker", "network", "concurrency", "operating system", "runtime"),
    "security": ("security", "privacy", "iam", "authentication", "authorization", "threat", "vulnerability", "compliance"),
    "ai": ("artificial intelligence", "machine learning", "llm", "generative ai", "model", "prompt", "embedding", "evaluation"),
    "testing": ("test", "quality", "ci/cd", "continuous integration", "reliability", "observability", "debugging"),
    "leadership": ("mentor", "leadership", "cross-functional", "stakeholder", "ownership", "technical lead", "influence"),
}

QUESTION_PATTERNS: dict[str, list[dict[str, Any]]] = {
    "frontend": [
        {"category": "practical", "prompt": "Improve or extend an existing UI feature while preserving behavior, accessibility, and test coverage.", "probes": ["requirements clarification", "component boundaries", "state management", "accessibility", "verification"]},
        {"category": "debugging", "prompt": "Diagnose a user-visible browser or frontend bug from a small existing codebase and explain the root cause.", "probes": ["code reading", "hypothesis testing", "browser behavior", "regression prevention"]},
    ],
    "backend": [
        {"category": "practical", "prompt": "Design or extend an API endpoint with validation, error handling, tests, and operational considerations.", "probes": ["API design", "data validation", "failure handling", "testing", "security"]},
        {"category": "system_design", "prompt": "Design a service for a stated workload, clarify requirements, and defend storage, consistency, scaling, and failure choices.", "probes": ["requirements clarification", "architecture", "trade-offs", "reliability", "capacity"]},
    ],
    "data": [
        {"category": "practical", "prompt": "Design or debug a data pipeline and explain correctness, idempotency, freshness, and failure recovery.", "probes": ["data modeling", "pipeline semantics", "backfills", "observability"]},
        {"category": "technical", "prompt": "Choose an approach for querying or processing a large dataset and explain its performance and correctness trade-offs.", "probes": ["query planning", "complexity", "partitioning", "data quality"]},
    ],
    "systems": [
        {"category": "system_design", "prompt": "Design a reliable service or tool under explicit load, latency, and failure constraints.", "probes": ["interfaces", "resource limits", "concurrency", "failure modes", "operability"]},
        {"category": "debugging", "prompt": "Investigate a failure in a multi-component system, state hypotheses, and identify the smallest safe diagnostic step.", "probes": ["observability", "isolation", "causal reasoning", "risk control"]},
    ],
    "security": [
        {"category": "technical", "prompt": "Review a proposed implementation for security and privacy risks, then prioritize mitigations and explain the trade-offs.", "probes": ["threat modeling", "authorization", "data sensitivity", "defense in depth"]},
    ],
    "testing": [
        {"category": "testing", "prompt": "Describe how you would verify a change, including normal, boundary, failure, and regression cases.", "probes": ["test strategy", "edge cases", "observability", "release confidence"]},
    ],
    "leadership": [
        {"category": "behavioral", "prompt": "Describe a difficult technical decision or disagreement, what you did, what changed, and what you learned.", "probes": ["ownership", "communication", "evidence", "reflection", "outcome"]},
    ],
    "ai": [
        {"category": "ai_assisted", "prompt": "Explain how you would use an AI tool on an engineering task, review its output, and remain accountable for the result.", "probes": ["task decomposition", "verification", "security", "judgment", "transparency"]},
    ],
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    return str(value)


def _slug(value: str) -> str:
    return "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())[:72] or "item"


def _load_json(path: Path | None, default: Any) -> Any:
    if path is None:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _source_type(source: dict[str, Any]) -> str:
    return str(source.get("source_type") or source.get("type") or "unknown").casefold().replace(" ", "_")


def classify_source(source: dict[str, Any]) -> str:
    if source.get("evidence_class") in EVIDENCE_CLASSES:
        return str(source["evidence_class"])
    source_type = _source_type(source)
    if source.get("is_job_description") or source_type in {"job_description", "official_job_description", "recruiter_packet", "recruiter_statement"}:
        return "verified_requirement"
    if source_type in {"official_company_guide", "official_interview_guide", "official_employer_policy", "official_careers_page", "employer_engineering_blog"}:
        return "official_company_signal"
    if source_type in {"candidate_report", "candidate_experience", "interview_report", "repeated_question_report"}:
        return "high_confidence_public_pattern"
    if source_type in {"practitioner_guide", "question_bank", "course", "blog", "forum", "social_post"}:
        return "plausible_requirement_derived"
    return "practice_only"


def normalize_sources(raw_sources: Any) -> list[dict[str, Any]]:
    if isinstance(raw_sources, dict):
        raw_sources = raw_sources.get("sources", raw_sources.get("results", []))
    if not isinstance(raw_sources, list):
        return []
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        item["id"] = str(item.get("id") or f"source-{index}")
        item["evidence_class"] = classify_source(item)
        item["url"] = str(item.get("url") or item.get("source_url") or "")
        item["title"] = str(item.get("title") or item.get("name") or item["id"])
        item["retrieved_at"] = str(item.get("retrieved_at") or "")
        normalized.append(item)
    return normalized


def extract_requirements(job: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "title": job.get("title") or job.get("role") or job.get("job_title"),
        "company": job.get("company") or job.get("employer"),
        "level": job.get("level") or job.get("seniority"),
        "location": job.get("location"),
        "interview_horizon": job.get("interview_horizon") or job.get("interview_date"),
        "ai_policy": job.get("ai_policy") or job.get("interview_ai_policy"),
    }
    sections = []
    for key in ("description", "summary", "requirements", "qualifications", "responsibilities", "technologies", "interview_process", "notes"):
        value = job.get(key)
        if value:
            sections.append((key, _text(value)))
    all_text = " ".join(value for _, value in sections).casefold()
    competencies: list[dict[str, Any]] = []
    for competency, markers in COMPETENCY_RULES.items():
        hits = [marker for marker in markers if marker in all_text]
        if hits:
            competencies.append({"id": competency, "signals": hits, "status": "observed_in_job_input"})
    requirements = []
    for section, value in sections:
        requirements.append({"id": f"req-{_slug(section)}", "section": section, "text": value, "source": "job-input", "evidence_class": "verified_requirement"})
    if not requirements:
        requirements.append({"id": "req-missing", "section": "missing", "text": "No job description or requirement sections were supplied.", "source": "job-input", "evidence_class": "practice_only"})
    return {
        "role": fields,
        "requirements": requirements,
        "competencies": competencies,
        "missing_inputs": [key for key, value in fields.items() if not value and key in {"title", "company", "level", "ai_policy"}],
        "source_policy": "Treat the supplied job requirement as authoritative for this preparation plan; do not replace it with generic assumptions.",
    }


SELF_ASSESSMENT_BANDS = {
    "new": "new",
    "working": "emerging",
    "comfortable": "reliable",
    "strong-uneven": "mixed",
    "freeform": "unknown",
}


def _score_band(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "unknown"
    if value < 1.5:
        return "new"
    if value < 2.5:
        return "emerging"
    if value < 3.5:
        return "reliable"
    return "strong"


def build_skill_profile(self_assessment: Any = None, diagnostics: Any = None) -> dict[str, Any]:
    """Combine a learner hypothesis with small observable diagnostic evidence."""
    if isinstance(self_assessment, str):
        self_assessment = {"level": self_assessment}
    self_assessment = self_assessment if isinstance(self_assessment, dict) else {}
    dimensions: list[dict[str, Any]] = []
    raw_dimensions = self_assessment.get("dimensions") or self_assessment.get("skills") or {}
    if isinstance(raw_dimensions, dict):
        raw_dimensions = [{"name": key, "level": value} for key, value in raw_dimensions.items()]
    if isinstance(raw_dimensions, list):
        for item in raw_dimensions:
            if isinstance(item, str):
                item = {"name": item}
            if not isinstance(item, dict) or not item.get("name"):
                continue
            dimensions.append({
                "name": str(item["name"]),
                "self_reported_level": str(item.get("level") or item.get("confidence") or self_assessment.get("level") or "unknown"),
                "demonstrated_level": "not_yet_measured",
                "evidence": [],
                "status": "self_report_only",
            })
    raw_diagnostics = diagnostics.get("diagnostics", diagnostics) if isinstance(diagnostics, dict) else diagnostics
    if not isinstance(raw_diagnostics, list):
        raw_diagnostics = []
    for index, item in enumerate(raw_diagnostics, start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("dimension") or item.get("skill") or item.get("topic") or f"diagnostic-{index}")
        score = item.get("score")
        evidence = {
            "id": str(item.get("id") or f"diagnostic-{index}"),
            "type": str(item.get("type") or "unknown"),
            "score": score,
            "observation": str(item.get("observation") or item.get("evidence") or ""),
            "status": "observed" if score is not None or item.get("observation") else "unknown",
        }
        match = next((entry for entry in dimensions if entry["name"].casefold() == name.casefold()), None)
        if match is None:
            match = {"name": name, "self_reported_level": "not_reported", "demonstrated_level": "not_yet_measured", "evidence": [], "status": "diagnostic_only"}
            dimensions.append(match)
        match["evidence"].append(evidence)
        if score is not None:
            match["demonstrated_level"] = _score_band(score)
            match["status"] = "demonstrated"
    return {
        "self_assessment": self_assessment,
        "initial_hypothesis": SELF_ASSESSMENT_BANDS.get(str(self_assessment.get("level") or "").casefold(), "unknown"),
        "dimensions": dimensions,
        "diagnostics_received": len(raw_diagnostics),
        "calibration_status": "evidence_calibrated" if raw_diagnostics else "hypothesis_only",
        "policy": "Use self-report to choose the first diagnostic; update the profile from explanations, traces, implementations, debugging, and design defenses. Do not permanently label the learner from one attempt.",
    }


def build_diagnostic_plan(requirements: dict[str, Any], skill_profile: dict[str, Any]) -> list[dict[str, Any]]:
    requested = [item["id"] for item in requirements.get("competencies", [])]
    requested += [item["name"] for item in skill_profile.get("dimensions", []) if item.get("name")]
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for competency in requested:
        key = str(competency).casefold()
        if key in seen:
            continue
        seen.add(key)
        if key in {"frontend", "backend", "data", "systems", "security", "ai"}:
            task_type = "explain_and_trace"
            prompt = f"Explain one important {competency} concept, trace where it appears in a small code or system flow, and name one failure case."
        elif key in {"testing", "debugging"}:
            task_type = "debug_and_verify"
            prompt = f"Review a bounded {competency} scenario, state a hypothesis, choose a diagnostic step, and propose a regression check."
        elif key in {"leadership", "communication"}:
            task_type = "structured_story"
            prompt = "Give a truthful project story with context, your specific action, a decision trade-off, the result, and what you would change."
        else:
            task_type = "transfer_task"
            prompt = f"Solve a small unfamiliar task involving {competency}, explain the approach, and defend the trade-offs."
        selected.append({
            "id": f"diagnostic-{_slug(str(competency))}",
            "dimension": str(competency),
            "type": task_type,
            "prompt": prompt,
            "why": "This is a small diagnostic to calibrate the next stage, not a pass/fail gate or a permanent level label.",
            "required_evidence": ["learner attempt", "explanation", "verification or edge-case reasoning"],
        })
        if len(selected) >= 6:
            break
    if not selected:
        selected.append({
            "id": "diagnostic-general-reasoning",
            "dimension": "general engineering reasoning",
            "type": "explain_and_trace",
            "prompt": "Explain a small technical decision you made, trace its consequences, and describe how you verified it.",
            "why": "No role-specific skill signals are available yet, so begin with a general diagnostic.",
            "required_evidence": ["learner attempt", "explanation", "verification or edge-case reasoning"],
        })
    return selected


def build_search_lanes(requirements: dict[str, Any], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    role = requirements["role"]
    company = str(role.get("company") or "target company")
    title = str(role.get("title") or "software engineer")
    level = str(role.get("level") or "target level")
    competencies = [item["id"] for item in requirements["competencies"]]
    lanes = [
        {"id": "official-role", "query": f"{company} {title} official job description interview process", "purpose": "Verify requirements, level, stages, and company-authored process guidance.", "evidence_class": "verified_requirement_or_official_company_signal"},
        {"id": "official-policy", "query": f"{company} candidate interview AI policy {title}", "purpose": "Find the employer’s current candidate-facing AI and assessment policy.", "evidence_class": "official_company_signal"},
        {"id": "role-patterns", "query": f"{company} {level} {title} interview questions candidate experience", "purpose": "Collect recent attributable reports of question patterns, not guarantees.", "evidence_class": "high_confidence_public_pattern"},
        {"id": "competency-patterns", "query": f"{title} {level} interview {', '.join(competencies[:4]) or 'coding system design debugging'} questions", "purpose": "Find role-relevant patterns and compare them with the supplied requirements.", "evidence_class": "plausible_requirement_derived"},
        {"id": "questioner-preparation", "query": f"{title} interview evaluation rubric tradeoffs debugging communication", "purpose": "Support rubric design for reasoning, verification, and communication.", "evidence_class": "plausible_requirement_derived"},
    ]
    if sources:
        lanes.append({"id": "source-followups", "query": f"Follow links and references from {len(sources)} supplied interview sources", "purpose": "Cross-check supplied sources and resolve role/level/date mismatches.", "evidence_class": "source-dependent"})
    return lanes


def _reported_questions(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in sources:
        questions = source.get("questions") or source.get("reported_questions") or []
        if isinstance(questions, str):
            questions = [questions]
        if not isinstance(questions, list):
            continue
        for number, prompt in enumerate(questions, start=1):
            if isinstance(prompt, dict):
                text = _text(prompt.get("prompt") or prompt.get("question") or prompt.get("text"))
                category = str(prompt.get("category") or "reported")
            else:
                text = _text(prompt)
                category = "reported"
            if not text:
                continue
            items.append({
                "id": f"reported-{_slug(source['id'])}-{number}",
                "prompt": text,
                "category": category,
                "evidence_class": source["evidence_class"],
                "source_ids": [source["id"]],
                "prediction_status": "reported_pattern_not_guarantee",
                "why_this_may_matter": "A public source reports this question or pattern; verify that its role, level, company, and date match before prioritizing it.",
                "probes": [],
            })
    return items


def build_question_bank(requirements: dict[str, Any], sources: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    bank = _reported_questions(sources)
    existing = {item["prompt"] for item in bank}
    for competency in requirements["competencies"]:
        for pattern in QUESTION_PATTERNS.get(competency["id"], []):
            if pattern["prompt"] in existing:
                continue
            bank.append({
                "id": f"derived-{competency['id']}-{len(bank) + 1}",
                "prompt": pattern["prompt"],
                "category": pattern["category"],
                "evidence_class": "plausible_requirement_derived",
                "source_ids": ["job-input"],
                "prediction_status": "derived_from_supplied_requirements_not_guarantee",
                "why_this_may_matter": f"The supplied job input contains signals for {competency['id']}; this practice question trains the associated capability.",
                "probes": pattern["probes"],
            })
    if not bank:
        bank = [{
            "id": "practice-clarify-and-tradeoffs",
            "prompt": "Take an unfamiliar engineering problem, clarify requirements, propose an approach, and explain how you would verify it.",
            "category": "reasoning",
            "evidence_class": "practice_only",
            "source_ids": [],
            "prediction_status": "practice_only",
            "why_this_may_matter": "No role-specific requirement or evidence was supplied, so this is only a generic diagnostic.",
            "probes": ["clarification", "approach", "trade-offs", "verification"],
        }]
    return bank[:max(1, limit)]


def build_blueprint(requirements: dict[str, Any], question_bank: list[dict[str, Any]]) -> list[dict[str, Any]]:
    categories = []
    for question in question_bank:
        if question["category"] not in categories:
            categories.append(question["category"])
    stages = [
        {"id": "stage-01-role-map", "title": "Role and process map", "outcome": "Explain what the target role requires and what evidence each round is likely to seek.", "unlocks": "All later practice is tied to the job input and evidence map."},
        {"id": "stage-02-fundamentals", "title": "Fundamentals and implementation judgment", "outcome": "Solve or reason through one role-relevant technical problem while explaining assumptions, correctness, complexity, and tests.", "unlocks": "Practical and coding drills."},
        {"id": "stage-03-realistic-work", "title": "Code reading, debugging, and practical change", "outcome": "Understand an existing code path, identify a defect or requirement gap, and propose a safe change.", "unlocks": "Multi-file, pair-programming, and take-home simulations."},
        {"id": "stage-04-design", "title": "System or component design", "outcome": "Clarify requirements and defend architecture, trade-offs, failure modes, and operational checks.", "unlocks": "Design mock and follow-up questions."},
        {"id": "stage-05-communication", "title": "Behavioral and project deep dive", "outcome": "Tell truthful, specific stories that show ownership, decisions, outcomes, learning, and collaboration.", "unlocks": "Behavioral mock."},
        {"id": "stage-06-policy-aware-mock", "title": "Policy-aware mock loop", "outcome": "Complete a bounded mock in the target company’s AI-use mode and defend the work without inventing experience.", "unlocks": "Final readiness review."},
    ]
    return [{**stage, "relevant_question_categories": categories} for stage in stages]


def build_feedback_contract(question: dict[str, Any], attempt: dict[str, Any] | None = None, output_mode: str = "inline") -> dict[str, Any]:
    attempt = attempt or {}
    answer = attempt.get("answer") or attempt.get("response") or attempt.get("code") or ""
    return {
        "schema_version": SCHEMA_VERSION,
        "question_id": question.get("id"),
        "attempt_preserved": True,
        "output_mode": output_mode,
        "attempt": {"answer": answer, "language": attempt.get("language"), "submitted_at": attempt.get("submitted_at")},
        "required_feedback": [
            "verdict: pass, partial, needs-review, or blocked",
            "what_the_question_tests",
            "evidence_basis_and_confidence",
            "specific_strengths",
            "first_incorrect_assumption_or_step",
            "why_that_gap_matters",
            "smallest_useful_hint_before_full_correction",
            "acceptable_approaches",
            "trade_offs_and_when_each_approach_is_better",
            "correction_or_improved_answer_at_requested_reveal_level",
            "verification_or_test_plan",
            "one_nearby_follow_up_for_transfer",
        ],
        "rubric": [
            "problem framing and clarification",
            "approach selection and alternatives",
            "correctness and invariant reasoning",
            "complexity or resource reasoning",
            "edge cases and verification",
            "communication and ownership",
        ],
        "correction_policy": "Identify the earliest material gap, explain its consequence, give a hint before a complete correction unless the learner asks for the full answer, and retest the same concept with a nearby variation.",
        "anti_overclaim_policy": "Do not call this the exact upcoming interview question unless the learner supplied an explicit official source; public reports are patterns, not guarantees.",
    }


def build_plan(job: dict[str, Any], raw_sources: Any = None, *, self_assessment: Any = None, diagnostics: Any = None, limit: int = 20) -> dict[str, Any]:
    requirements = extract_requirements(job)
    skill_profile = build_skill_profile(self_assessment, diagnostics)
    diagnostic_plan = build_diagnostic_plan(requirements, skill_profile)
    sources = normalize_sources(raw_sources)
    question_bank = build_question_bank(requirements, sources, limit=limit)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "upstack-interview-preparation",
        "warnings": [
            "No public source can guarantee the exact future interview question unless the employer explicitly supplied it.",
            "Keep official requirements, employer signals, candidate reports, and practice analogues visibly separate.",
            "Research is read-only by default; do not request or use leaked, stolen, private, or confidential interview material.",
        ],
        "job": job,
        "requirement_map": requirements,
        "skill_profile": skill_profile,
        "diagnostic_plan": diagnostic_plan,
        "evidence": sources,
        "search_lanes": build_search_lanes(requirements, sources),
        "question_bank": question_bank,
        "blueprint": build_blueprint(requirements, question_bank),
        "practice_policy": {
            "curriculum": "map_complete_curriculum_generate_one_current_question_or_stage_at_a_time",
            "default_mode": "coached",
            "available_modes": ["coached", "mock", "assessment"],
            "ai_policy": requirements["role"].get("ai_policy") or "unknown_ask_learner_or_recruiter_before_mock",
            "output_modes": ["inline", "markdown", "both"],
        },
    }


def _md(value: Any) -> str:
    return _text(value).replace("\n", " ").strip()


def render_skill_profile(plan: dict[str, Any]) -> str:
    profile = plan["skill_profile"]
    lines = ["# Learner Skill and Knowledge Profile", "", f"- Calibration status: `{profile['calibration_status']}`", f"- Initial hypothesis: `{profile['initial_hypothesis']}`", f"- Diagnostics received: `{profile['diagnostics_received']}`", "", "The self-assessment is a starting hypothesis. Demonstrated evidence is updated by explanations, traces, implementations, debugging, design defenses, and structured stories.", "", "| Dimension | Self-reported | Demonstrated | Status | Evidence |", "| --- | --- | --- | --- | --- |"]
    for item in profile["dimensions"]:
        evidence = "; ".join(_md(entry.get("observation") or entry.get("type")) for entry in item.get("evidence", [])) or "not measured"
        lines.append(f"| {_md(item['name'])} | {_md(item['self_reported_level'])} | {_md(item['demonstrated_level'])} | `{item['status']}` | {_md(evidence)} |")
    lines += ["", f"> {profile['policy']}", "", "## Next diagnostics", ""]
    for item in plan["diagnostic_plan"]:
        lines += [f"### {item['dimension']}", "", f"- Type: `{item['type']}`", f"- Prompt: {item['prompt']}", f"- Why: {item['why']}", f"- Evidence to collect: {', '.join(item['required_evidence'])}", ""]
    return "\n".join(lines)


def render_requirements(plan: dict[str, Any]) -> str:
    role = plan["requirement_map"]["role"]
    lines = [f"# Job Requirements — {_md(role.get('title') or 'Target role')}", "", "## Target", "", f"- Company: {_md(role.get('company') or 'unknown')}", f"- Level: {_md(role.get('level') or 'unknown')}", f"- Location: {_md(role.get('location') or 'unknown')}", f"- Interview horizon: {_md(role.get('interview_horizon') or 'unknown')}", f"- AI policy: {_md(role.get('ai_policy') or 'unknown; verify with recruiter or official process guidance')}", "", "## Observed competencies", ""]
    for competency in plan["requirement_map"]["competencies"]:
        lines.append(f"- **{competency['id']}** — signals: {', '.join(competency['signals'])}; status: `{competency['status']}`")
    lines += ["", "## Supplied requirement sections", ""]
    for item in plan["requirement_map"]["requirements"]:
        lines += [f"### {item['section']}", "", item["text"], "", f"Evidence: `{item['evidence_class']}` from `{item['source']}`.", ""]
    lines += ["## Boundary", "", plan["requirement_map"]["source_policy"]]
    return "\n".join(lines) + "\n"


def render_evidence(plan: dict[str, Any]) -> str:
    lines = ["# Interview Evidence Map", "", "Use evidence classes to prevent a public pattern from becoming a promise.", "", "| Source | Class | Role/level fit | What it supports | URL |", "| --- | --- | --- | --- | --- |"]
    for source in plan["evidence"]:
        fit = f"{source.get('role') or 'unknown'} / {source.get('level') or 'unknown'}"
        support = source.get("evidence_excerpt") or source.get("purpose") or source.get("title")
        lines.append(f"| `{source['id']}` | `{source['evidence_class']}` | {_md(fit)} | {_md(support)} | {source.get('url') or 'not supplied'} |")
    if not plan["evidence"]:
        lines.append("| none supplied | `practice_only` | unknown | Research has not been supplied yet. | — |")
    lines += ["", "> Candidate reports and question banks describe patterns. They are not proof of the exact question that will appear.", ""]
    return "\n".join(lines)


def render_blueprint(plan: dict[str, Any]) -> str:
    lines = ["# Interview Preparation Blueprint", "", "The complete roadmap is mapped first; generate only the current stage or question when requested.", ""]
    for stage in plan["blueprint"]:
        lines += [f"## {stage['title']}", "", f"**Outcome:** {stage['outcome']}", "", f"**Unlocks:** {stage['unlocks']}", "", f"**Relevant question categories:** {', '.join(stage['relevant_question_categories'])}", ""]
    return "\n".join(lines)


def render_question_bank(plan: dict[str, Any]) -> str:
    lines = ["# Interview Question Bank", "", "Each item must be introduced with what it tests, why it was selected, and how certain the source is.", ""]
    for index, question in enumerate(plan["question_bank"], start=1):
        lines += [f"## {index}. {question['prompt']}", "", f"- Category: `{question['category']}`", f"- Evidence: `{question['evidence_class']}`", f"- Status: `{question['prediction_status']}`", f"- Why this may matter: {question['why_this_may_matter']}", f"- Probes: {', '.join(question['probes']) or 'derive from the attempt'}", f"- Source IDs: {', '.join(question['source_ids']) or 'none'}", ""]
    return "\n".join(lines)


def render_feedback(contract: dict[str, Any]) -> str:
    lines = ["# Interview Attempt Feedback", "", "Preserve the learner’s original attempt. Fill every required field after reviewing it; do not silently rewrite authorship.", "", f"- Question ID: `{contract.get('question_id')}`", f"- Output mode: `{contract.get('output_mode')}`", f"- Attempt preserved: `{contract.get('attempt_preserved')}`", "", "## Required feedback", ""]
    lines.extend(f"- [ ] {item}" for item in contract["required_feedback"])
    lines += ["", "## Rubric", ""]
    lines.extend(f"- [ ] {item}" for item in contract["rubric"])
    lines += ["", f"> {contract['correction_policy']}", "", f"> {contract['anti_overclaim_policy']}", ""]
    return "\n".join(lines)


def write_artifacts(plan: dict[str, Any], output_dir: Path, feedback: dict[str, Any] | None = None) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "profile": output_dir / "SKILL_PROFILE.md",
        "requirements": output_dir / "JOB_REQUIREMENTS.md",
        "evidence": output_dir / "EVIDENCE_MAP.md",
        "blueprint": output_dir / "INTERVIEW_BLUEPRINT.md",
        "question_bank": output_dir / "QUESTION_BANK.md",
    }
    files["profile"].write_text(render_skill_profile(plan), encoding="utf-8")
    files["requirements"].write_text(render_requirements(plan), encoding="utf-8")
    files["evidence"].write_text(render_evidence(plan), encoding="utf-8")
    files["blueprint"].write_text(render_blueprint(plan), encoding="utf-8")
    files["question_bank"].write_text(render_question_bank(plan), encoding="utf-8")
    if feedback is not None:
        files["feedback"] = output_dir / "FEEDBACK.md"
        files["feedback"].write_text(render_feedback(feedback), encoding="utf-8")
    return {key: str(path) for key, path in files.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-file", type=Path, required=True, help="JSON containing the supplied job description and target details")
    parser.add_argument("--sources-file", type=Path, help="JSON list/object of host-collected evidence sources and reported questions")
    parser.add_argument("--skill-profile-file", type=Path, help="JSON containing self-reported skill dimensions and level")
    parser.add_argument("--diagnostics-file", type=Path, help="JSON list/object of observed diagnostic attempts")
    parser.add_argument("--attempt-file", type=Path, help="JSON containing one learner attempt for a feedback contract")
    parser.add_argument("--mode", choices=["plan", "search-lanes", "feedback"], default="plan")
    parser.add_argument("--output-mode", choices=["inline", "markdown", "both"], default="inline")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=Path(".upstack/interview"))
    parser.add_argument("--write", action="store_true", help="write Markdown artifacts; never writes without this flag")
    args = parser.parse_args()

    job = _load_json(args.job_file, {})
    sources = normalize_sources(_load_json(args.sources_file, []))
    self_assessment = _load_json(args.skill_profile_file, {})
    diagnostics = _load_json(args.diagnostics_file, [])
    plan = build_plan(job, sources, self_assessment=self_assessment, diagnostics=diagnostics, limit=args.limit)
    feedback = None
    if args.mode == "feedback":
        question = plan["question_bank"][0]
        attempt = _load_json(args.attempt_file, {})
        feedback = build_feedback_contract(question, attempt, args.output_mode)
        result: dict[str, Any] = {"plan_summary": {"role": plan["requirement_map"]["role"], "evidence_count": len(plan["evidence"])}, "feedback_contract": feedback}
    elif args.mode == "search-lanes":
        result = {"search_lanes": plan["search_lanes"], "research_boundary": plan["warnings"]}
    else:
        result = plan
    if args.write:
        result["written_files"] = write_artifacts(plan, args.output_dir, feedback)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
