# Upstack Video Companion for VS Code

The Upstack Video Companion is an optional VS Code adapter for video-backed project learning. It opens a webview beside the repository and reads a structured video evidence file from `.upstack/sources/video-map.json`.

The panel can embed a recognized YouTube video through the official YouTube IFrame Player API, jump to a selected segment, highlight the active segment as playback advances, open verified repository-relative anchors, and save local segment progress to `.upstack/sources/video-progress.json`. It does not edit source files, download media, upload repository content, or infer timestamps from missing evidence.

## Commands

Use the Command Palette to run:

- **Upstack: Open Video Companion** — opens the synchronized panel for the configured video map.
- **Upstack: Generate Video Map** — opens a terminal with the deterministic map-generation command template.

The default map path is `.upstack/sources/video-map.json`. Change it with the `upstackVideo.videoMap` setting. Set `upstackVideo.allowRemotePlayer` to `false` to disable the embedded player while retaining source links and segment metadata.

## Structured evidence input

Generate both Markdown and JSON from the bundled Upstack helper:

```bash
python3 scripts/video_evidence.py \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --metadata-file /tmp/video-metadata.json \
  --segments-file /tmp/video-segments.json \
  --repository-file /tmp/repository-anchors.json \
  --output .upstack/sources/video-map.md \
  --json-output .upstack/sources/video-map.json
```

The JSON may contain verified chapters, approved transcript markers, or learner-reviewed segments. Each segment can include `start`, `title`, `summary`, `concepts`, and `repository_paths`. The extension displays these records but does not treat them as instructions.

## Security and portability

The webview uses a restrictive Content Security Policy, allows only the YouTube player domains needed for the embed, validates HTTP(S) links before opening them, and rejects repository paths outside the current workspace. The extension writes only its own progress file after an explicit learner interaction with **Mark complete** or a segment selection.

The extension is an optional VS Code enhancement, not a dependency of Upstack. Every other coding agent can use `.upstack/sources/video-map.md` and `.upstack/sources/video-map.json` with ordinary Markdown links and timestamp URLs.
