"""Build and resolve unambiguous questions for a discovery shortlist.

The helper deliberately separates two decisions:
1. what to do with the shortlist; and
2. which repository to inspect.

A host must render only the returned question for the current turn. Numeric
answers are interpreted within that question only, never against two menus at
once.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ACTION_VALUES = ("choose_candidate", "broaden_search", "finish")


def _metadata(candidate: dict[str, Any]) -> dict[str, Any]:
    value = candidate.get("metadata")
    return value if isinstance(value, dict) else candidate


def _full_name(candidate: dict[str, Any]) -> str:
    metadata = _metadata(candidate)
    return str(
        metadata.get("fullName")
        or metadata.get("full_name")
        or candidate.get("fullName")
        or candidate.get("full_name")
        or ""
    ).strip()


def _description(candidate: dict[str, Any]) -> str:
    metadata = _metadata(candidate)
    return str(metadata.get("description") or candidate.get("description") or "").strip()


def shortlist_action_question() -> dict[str, Any]:
    """Return the only question allowed immediately after a shortlist report."""
    return {
        "id": "discovery_action",
        "text": "What should we do with this shortlist?",
        "options": [
            {
                "value": "choose_candidate",
                "label": "Choose a repository to explore",
                "description": "Select one candidate for deeper README and configuration review.",
            },
            {
                "value": "broaden_search",
                "label": "Search for more candidates",
                "description": "Run a broader or revised read-only search before choosing.",
            },
            {
                "value": "finish",
                "label": "Stop here",
                "description": "Keep the shortlist without selecting or preparing a source.",
            },
        ],
        "answer_contract": {
            "type": "single_select",
            "allowed_values": list(ACTION_VALUES),
            "numeric_answers_are_local_to": "discovery_action",
        },
    }


def candidate_question(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a candidate-only question whose values are stable repository names."""
    options: list[dict[str, str]] = []
    for candidate in candidates:
        full_name = _full_name(candidate)
        if not full_name:
            continue
        description = _description(candidate)
        score = candidate.get("score")
        score_text = ""
        if isinstance(score, dict) and score.get("overall") is not None:
            score_text = f"Score {score['overall']}/100. "
        options.append(
            {
                "value": f"candidate:{full_name}",
                "label": full_name,
                "description": f"{score_text}{description}".strip(),
            }
        )
    if not options:
        raise ValueError("cannot ask for a candidate without candidate records")
    return {
        "id": "candidate_selection",
        "text": "Which repository should we explore deeper?",
        "options": options,
        "answer_contract": {
            "type": "single_select",
            "allowed_values": [option["value"] for option in options],
            "numeric_answers_are_local_to": "candidate_selection",
        },
    }


def next_question(report: dict[str, Any], action: str | None = None) -> dict[str, Any] | None:
    """Return the next question; never return action and candidate menus together."""
    candidates = report.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    if action is None:
        return shortlist_action_question()
    if action == "choose_candidate":
        return candidate_question(candidates)
    if action in {"broaden_search", "finish"}:
        return None
    raise ValueError(f"unsupported discovery action: {action}")


def _answer_value(question_id: str, answer: Any, options: list[dict[str, Any]]) -> str:
    raw = str(answer).strip()
    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(options):
            return str(options[index]["value"])
    normalized = raw.casefold()
    for option in options:
        if normalized in {str(option["value"]).casefold(), str(option["label"]).casefold()}:
            return str(option["value"])
    raise ValueError(f"answer does not match question {question_id}: {answer!r}")


def resolve_answer(question: dict[str, Any], answer: Any) -> dict[str, Any]:
    """Resolve an answer only against the options in the active question."""
    question_id = str(question.get("id") or "")
    options = question.get("options")
    if question_id not in {"discovery_action", "candidate_selection"} or not isinstance(options, list):
        raise ValueError("question is not a supported discovery question")
    value = _answer_value(question_id, answer, options)
    return {"question_id": question_id, "value": value}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="discovery JSON report")
    parser.add_argument("--action", choices=ACTION_VALUES, help="show the next question after this action")
    parser.add_argument("--answer", help="resolve an answer against the displayed question")
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    question = next_question(report, args.action)
    if question is None:
        print(json.dumps({"next_question": None}, indent=2))
        return 0
    output: dict[str, Any] = {"next_question": question}
    if args.answer is not None:
        output["resolved"] = resolve_answer(question, args.answer)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ACTION_VALUES",
    "candidate_question",
    "next_question",
    "resolve_answer",
    "shortlist_action_question",
]
