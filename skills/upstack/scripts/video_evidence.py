"""Build timestamped, repository-linked learning evidence from a video source.

This helper does not download or execute media. It consumes metadata, chapters,
transcript segments, and repository anchors supplied by an approved host/API or
learner, then writes a portable Markdown map with clickable timestamp links.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


VIDEO_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
TIMESTAMP_RE = re.compile(r"^(?:(?P<h>\d+)h)?\s*(?:(?P<m>\d+)m)?\s*(?:(?P<s>\d+(?:\.\d+)?)s?)?$", re.IGNORECASE)
TOKEN_RE = re.compile(r"[a-z0-9+#.-]{3,}", re.IGNORECASE)


def parse_seconds(value: Any) -> int | None:
    """Parse seconds, clock notation, or YouTube-style h/m/s notation."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return max(0, round(float(value)))
    text = str(value).strip().lower()
    if text.isdigit() or re.fullmatch(r"\d+(?:\.\d+)?", text):
        return max(0, round(float(text)))
    if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", text):
        parts = [int(part) for part in text.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    match = TIMESTAMP_RE.fullmatch(text.replace(" ", ""))
    if match and any(match.group(name) for name in ("h", "m", "s")):
        return round(float(match.group("h") or 0) * 3600 + float(match.group("m") or 0) * 60 + float(match.group("s") or 0))
    return None


def format_seconds(seconds: Any) -> str:
    value = parse_seconds(seconds) or 0
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def video_identity(url: str) -> dict[str, str | None]:
    """Return a canonical watch URL and stable ID for common YouTube URLs."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    video_id: str | None = None
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0] or None
    elif host in {"youtube.com", "m.youtube.com"}:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id:
            video_id = query_id
        else:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
                video_id = parts[1]
    if video_id:
        canonical = f"https://www.youtube.com/watch?v={video_id}"
        return {"platform": "youtube", "video_id": video_id, "canonical_url": canonical}
    return {"platform": host or "unknown", "video_id": None, "canonical_url": url}


def timestamp_url(url: str, seconds: Any) -> str:
    """Create a start-time link without discarding the source video identity."""
    start = parse_seconds(seconds) or 0
    identity = video_identity(url)
    if identity["platform"] == "youtube" and identity["video_id"]:
        params = {"v": identity["video_id"], "t": f"{start}s"}
        return f"https://www.youtube.com/watch?{urlencode(params)}"
    parsed = urlparse(url)
    fragment = f"t={start}s"
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, fragment))


def _terms(text: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(text or "")}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _safe_relative_path(value: str) -> str:
    path = value.replace("\\", "/").strip()
    while path.startswith("./"):
        path = path[2:]
    if not path or path.startswith("/") or ".." in path.split("/"):
        return ""
    return path


def _markdown_escape(value: str) -> str:
    return value.replace("[", "\\[").replace("]", "\\]").replace("|", "\\|")


def normalize_segment(segment: dict[str, Any], index: int) -> dict[str, Any] | None:
    start = parse_seconds(segment.get("start") if "start" in segment else segment.get("start_seconds"))
    if start is None:
        return None
    end = parse_seconds(segment.get("end") if "end" in segment else segment.get("end_seconds"))
    title = _clean_text(segment.get("title") or segment.get("topic") or segment.get("text") or f"Segment {index + 1}")
    summary = _clean_text(segment.get("summary") or segment.get("text") or "")
    concepts = [_clean_text(item) for item in segment.get("concepts", []) if _clean_text(item)]
    repo_paths = [_safe_relative_path(str(item)) for item in segment.get("repository_paths", segment.get("repo_paths", []))]
    repo_paths = [item for item in repo_paths if item]
    lesson_path = _safe_relative_path(str(segment.get("lesson_path") or segment.get("lesson_file") or ""))
    return {
        "index": index,
        "start_seconds": start,
        "end_seconds": end if end is None or end >= start else start,
        "title": title,
        "summary": summary,
        "concepts": concepts,
        "repository_paths": repo_paths,
        "lesson_path": lesson_path,
        "evidence_basis": _clean_text(segment.get("evidence_basis") or "provided timestamp"),
    }


def normalize_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [item for index, item in enumerate(segments) if isinstance(item, dict) for item in [normalize_segment(item, index)] if item]
    normalized.sort(key=lambda item: (item["start_seconds"], item["title"].casefold()))
    for index, item in enumerate(normalized):
        item["index"] = index
    return normalized


def infer_repository_paths(segments: list[dict[str, Any]], repository_paths: list[str], focus: list[str], concepts: list[str]) -> list[dict[str, Any]]:
    """Attach explicit repository anchors when provided; never invent source paths."""
    valid_paths = [_safe_relative_path(path) for path in repository_paths]
    valid_paths = [path for path in valid_paths if path]
    criteria = _terms(" ".join(focus + concepts))
    for segment in segments:
        if segment["repository_paths"]:
            continue
        segment_terms = _terms(" ".join([segment["title"], segment["summary"], " ".join(segment["concepts"]) ]))
        candidates = []
        for path in valid_paths:
            path_terms = _terms(path)
            fit = len((segment_terms | criteria) & path_terms)
            candidates.append((fit, path))
        if candidates:
            best_fit, best_path = max(candidates)
            if best_fit > 0:
                segment["repository_paths"] = [best_path]
                segment["evidence_basis"] = "provided repository path matched to segment terms"
    return segments


def build_evidence(
    video: dict[str, Any],
    *,
    segments: list[dict[str, Any]] | None = None,
    repository: dict[str, Any] | None = None,
    focus: list[str] | None = None,
    concepts: list[str] | None = None,
    query: str = "",
) -> dict[str, Any]:
    focus = focus or []
    concepts = concepts or []
    url = _clean_text(video.get("url") or video.get("canonical_url"))
    if not url:
        raise ValueError("video metadata must include url")
    identity = video_identity(url)
    raw_segments = segments if segments is not None else video.get("chapters") or video.get("segments") or video.get("transcript_segments") or []
    normalized = normalize_segments(raw_segments if isinstance(raw_segments, list) else [])
    repo = repository or {}
    repo_name = _clean_text(repo.get("full_name") or repo.get("fullName") or repo.get("name"))
    repo_url = _clean_text(repo.get("url") or "")
    repo_paths = repo.get("paths") or repo.get("repository_paths") or []
    normalized = infer_repository_paths(normalized, [str(path) for path in repo_paths], focus, concepts)
    for segment in normalized:
        segment["timestamp_url"] = timestamp_url(url, segment["start_seconds"])
        segment["timestamp"] = format_seconds(segment["start_seconds"])
        segment["lesson_key"] = f"video-{identity['video_id'] or 'source'}-{segment['index'] + 1:02d}"
    evidence_status = "timestamped" if normalized else "metadata_only"
    return {
        "version": 1,
        "video": {
            "url": url,
            "canonical_url": identity["canonical_url"],
            "platform": identity["platform"],
            "video_id": identity["video_id"],
            "title": _clean_text(video.get("title") or "Untitled video"),
            "channel": _clean_text(video.get("channel") or video.get("channelTitle") or video.get("author")),
            "published_at": video.get("published_at") or video.get("publishedAt"),
            "description": _clean_text(video.get("description") or video.get("text")),
        },
        "repository": {"full_name": repo_name, "url": repo_url, "paths": [str(path) for path in repo_paths if _safe_relative_path(str(path))]},
        "learning": {"query": query, "focus": focus, "concepts": concepts},
        "segments": normalized,
        "status": evidence_status,
        "provenance": {"basis": "metadata and timestamp/segment data supplied by an approved host, API, or learner", "transcript_downloaded": False},
        "side_effects": [],
    }


def render_markdown(evidence: dict[str, Any], *, repo_link_prefix: str = "../../") -> str:
    video = evidence["video"]
    repository = evidence.get("repository") or {}
    learning = evidence.get("learning") or {}
    lines = [
        f"# {video.get('title') or 'Video learning map'}",
        "",
        f"**Source:** [{video.get('title') or 'Watch video'}]({video.get('canonical_url') or video.get('url')})",
    ]
    if video.get("channel"):
        lines.append(f"**Channel/author:** {_markdown_escape(video['channel'])}")
    if repository.get("url"):
        label = repository.get("full_name") or repository["url"]
        lines.append(f"**Repository:** [{_markdown_escape(label)}]({repository['url']})")
    if learning.get("focus"):
        lines.append(f"**Focus:** {_markdown_escape(', '.join(learning['focus']))}")
    if learning.get("concepts"):
        lines.append(f"**Concepts:** {_markdown_escape(', '.join(learning['concepts']))}")
    lines.extend(["", "> Timestamps are evidence links, not claims that the video teaches every mapped concept. Verify the segment against the repository and label inferred mappings honestly.", ""])
    segments = evidence.get("segments") or []
    if not segments:
        lines.extend(["## Timestamp map", "", "No verified chapter or transcript timestamps were supplied. Keep the video link, then add timestamps only from chapters, a transcript, or a learner-reviewed marker list.", ""])
        return "\n".join(lines)
    lines.extend(["## Timestamp map", "", "| Time | Segment | Repository anchor | Lesson artifact | Learning use |", "| --- | --- | --- | --- | --- |"])
    for segment in segments:
        title = _markdown_escape(segment["title"])
        time_link = f"[{segment['timestamp']}]({segment['timestamp_url']})"
        anchors = []
        for path in segment.get("repository_paths") or []:
            anchors.append(f"[`{_markdown_escape(path)}`]({repo_link_prefix}{path})")
        anchor_text = ", ".join(anchors) or "—"
        lesson_path = segment.get("lesson_path") or ""
        lesson_text = f"[`{_markdown_escape(lesson_path)}`]({repo_link_prefix}{lesson_path})" if lesson_path else "—"
        use = _markdown_escape(segment.get("summary") or ", ".join(segment.get("concepts") or []) or "Review and explain this segment")
        lines.append(f"| {time_link} | {title} | {anchor_text} | {lesson_text} | {use} |")
    lines.extend(["", "## Suggested workflow", "", "1. Open the timestamp link and follow the segment without copying blindly.", "2. Open the repository anchor and identify the corresponding implementation or missing seam.", "3. Write a short explanation or attempt in the learner workspace.", "4. Ask Upstack or Overflow for a source-cited lesson, hint, or assessment using the segment key.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_url")
    parser.add_argument("--metadata-file", type=Path)
    parser.add_argument("--segments-file", type=Path)
    parser.add_argument("--repository-file", type=Path)
    parser.add_argument("--focus", action="append", default=[])
    parser.add_argument("--concept", action="append", default=[])
    parser.add_argument("--query", default="")
    parser.add_argument("--repo-link-prefix", default="../../")
    parser.add_argument("--output", type=Path, required=True, help="write the portable Markdown map")
    parser.add_argument("--json-output", type=Path, help="also write structured video evidence JSON for the VS Code companion")
    args = parser.parse_args()
    video: dict[str, Any] = {"url": args.video_url}
    if args.metadata_file:
        video.update(json.loads(args.metadata_file.read_text(encoding="utf-8")))
        video["url"] = args.video_url
    segments = None
    if args.segments_file:
        payload = json.loads(args.segments_file.read_text(encoding="utf-8"))
        segments = payload.get("segments", payload.get("chapters", payload)) if isinstance(payload, dict) else payload
    repository = None
    if args.repository_file:
        repository = json.loads(args.repository_file.read_text(encoding="utf-8"))
    evidence = build_evidence(video, segments=segments, repository=repository, focus=args.focus, concepts=args.concept, query=args.query)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(evidence, repo_link_prefix=args.repo_link_prefix), encoding="utf-8")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "json_output": str(args.json_output) if args.json_output else None, "status": evidence["status"], "segments": len(evidence["segments"]), "video_id": evidence["video"]["video_id"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
