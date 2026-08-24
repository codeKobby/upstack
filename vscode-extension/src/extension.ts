import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as vscode from 'vscode';

interface VideoSegment {
  lesson_key?: string;
  title?: string;
  summary?: string;
  timestamp?: string;
  timestamp_url?: string;
  start_seconds?: number;
  repository_paths?: string[];
  lesson_path?: string;
  concepts?: string[];
}

interface VideoEvidence {
  video?: {
    url?: string;
    canonical_url?: string;
    video_id?: string;
    title?: string;
    channel?: string;
  };
  repository?: {
    full_name?: string;
    url?: string;
  };
  learning?: {
    focus?: string[];
    concepts?: string[];
  };
  segments?: VideoSegment[];
}

interface ProgressRecord {
  updated_at: string;
  completed_segments: string[];
  active_segment?: string;
}

const MAP_SETTING = 'upstackVideo.videoMap';
const PROGRESS_FILE = '.upstack/sources/video-progress.json';
const YOUTUBE_ID_RE = /^[A-Za-z0-9_-]{6,}$/;

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('upstackVideo.open', () => openCompanion(context)),
    vscode.commands.registerCommand('upstackVideo.generateMap', () => generateMapInstructions()),
  );
}

async function openCompanion(context: vscode.ExtensionContext): Promise<void> {
  const workspace = vscode.workspace.workspaceFolders?.[0];
  if (!workspace) {
    void vscode.window.showWarningMessage('Upstack Video Companion needs an open workspace.');
    return;
  }
  const configured = vscode.workspace.getConfiguration().get<string>(MAP_SETTING) || '.upstack/sources/video-map.json';
  const mapPath = path.resolve(workspace.uri.fsPath, configured);
  if (!isInsideWorkspace(mapPath, workspace.uri.fsPath)) {
    void vscode.window.showErrorMessage('The configured Upstack video map must be inside the workspace.');
    return;
  }
  let evidence: VideoEvidence;
  try {
    evidence = JSON.parse(await fs.readFile(mapPath, 'utf8')) as VideoEvidence;
  } catch {
    void vscode.window.showInformationMessage(
      `No video map found at ${configured}. Generate one with Upstack: Generate Video Map, then reopen the companion.`,
    );
    return;
  }
  const progressPath = path.resolve(workspace.uri.fsPath, PROGRESS_FILE);
  const progress = await readProgress(progressPath);
  const allowRemotePlayer = vscode.workspace.getConfiguration().get<boolean>('upstackVideo.allowRemotePlayer', true);
  const panel = vscode.window.createWebviewPanel(
    'upstackVideoCompanion',
    `Upstack: ${evidence.video?.title || 'Video Companion'}`,
    vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true },
  );
  panel.webview.html = renderPanel(panel.webview, evidence, progress, allowRemotePlayer);
  panel.webview.onDidReceiveMessage(async (message: unknown) => {
    if (!isMessage(message)) return;
    if (message.type === 'openFile') {
      await openWorkspaceFile(workspace.uri.fsPath, message.path);
    } else if (message.type === 'openExternal') {
      await openExternalUrl(message.url);
    } else if (message.type === 'saveProgress') {
      const next: ProgressRecord = {
        updated_at: new Date().toISOString(),
        completed_segments: progress.completed_segments,
        active_segment: message.lessonKey,
      };
      if (message.completed && !next.completed_segments.includes(message.lessonKey)) {
        next.completed_segments.push(message.lessonKey);
      }
      if (!message.completed) {
        next.completed_segments = next.completed_segments.filter((key) => key !== message.lessonKey);
      }
      progress.completed_segments = next.completed_segments;
      progress.active_segment = next.active_segment;
      await writeProgress(progressPath, next);
      panel.webview.postMessage({ type: 'progressSaved', progress: next });
    }
  }, undefined, context.subscriptions);
}

function renderPanel(webview: vscode.Webview, evidence: VideoEvidence, progress: ProgressRecord, allowRemotePlayer: boolean): string {
  const nonce = createNonce();
  const video = evidence.video || {};
  const videoId = safeVideoId(video.video_id, video.canonical_url || video.url || '');
  const embedUrl = allowRemotePlayer && videoId
    ? `https://www.youtube-nocookie.com/embed/${videoId}?enablejsapi=1&playsinline=1&rel=0`
    : '';
  const payload = JSON.stringify({ evidence, progress, embedUrl })
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
  const csp = [
    "default-src 'none'",
    `img-src ${webview.cspSource} https: data:`,
    "style-src 'unsafe-inline'",
    `script-src 'nonce-${nonce}' https://www.youtube.com`,
    'frame-src https://www.youtube-nocookie.com https://www.youtube.com',
    'connect-src https://www.youtube-nocookie.com https://www.youtube.com',
  ].join('; ');
  const apiScript = videoId ? '<script src="https://www.youtube.com/iframe_api"><\\/script>' : '';
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<title>Upstack Video Companion</title>
<style>
:root { color-scheme: light dark; }
body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); padding: 16px; line-height: 1.45; }
header { display: flex; justify-content: space-between; gap: 16px; align-items: start; margin-bottom: 16px; }
h1 { font-size: 1.35rem; margin: 0 0 4px; }
.meta { color: var(--vscode-descriptionForeground); font-size: .9rem; }
button, a.action { color: var(--vscode-button-foreground); background: var(--vscode-button-background); border: 0; border-radius: 3px; padding: 6px 10px; cursor: pointer; text-decoration: none; font: inherit; }
button:hover, a.action:hover { background: var(--vscode-button-hoverBackground); }
.player { aspect-ratio: 16 / 9; background: #111; margin-bottom: 18px; }
.player iframe { width: 100%; height: 100%; border: 0; }
.no-player { padding: 32px 16px; text-align: center; color: var(--vscode-descriptionForeground); }
.segment { border: 1px solid var(--vscode-panel-border); border-radius: 4px; margin: 8px 0; padding: 10px; }
.segment.active { border-color: var(--vscode-focusBorder); }
.segment.done { opacity: .72; }
.segment-head { display: flex; align-items: baseline; gap: 8px; }
.segment-title { font-weight: 600; flex: 1; }
.segment-time { color: var(--vscode-textLink-foreground); }
.segment-summary { color: var(--vscode-descriptionForeground); margin: 5px 0; }
.segment-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.segment-actions button { font-size: .85rem; }
.path { font-family: var(--vscode-editor-font-family); }
#status { min-height: 1.3em; color: var(--vscode-descriptionForeground); margin: 8px 0; }
</style>
</head>
<body>
<header><div><h1 id="title"></h1><div id="meta" class="meta"></div></div><button id="open-video">Open video</button></header>
<div id="player" class="player"></div>
<div id="status" role="status"></div>
<section><h2>Follow-along segments</h2><div id="segments"></div></section>
${apiScript}
<script nonce="${nonce}">
const vscode = acquireVsCodeApi();
const model = ${payload};
const evidence = model.evidence || {};
const video = evidence.video || {};
const segments = Array.isArray(evidence.segments) ? evidence.segments : [];
let progress = model.progress || { completed_segments: [] };
let ytPlayer = null;
window.onYouTubeIframeAPIReady = () => {
  const iframe = document.getElementById('youtube-player');
  if (!iframe || !window.YT) return;
  ytPlayer = new window.YT.Player(iframe, { events: { onReady: () => status.textContent = 'Video ready. Select a segment to follow along.' } });
};
const title = document.getElementById('title');
const meta = document.getElementById('meta');
const status = document.getElementById('status');
title.textContent = video.title || 'Video Companion';
meta.textContent = [video.channel, (evidence.repository || {}).full_name].filter(Boolean).join(' · ');
document.getElementById('open-video').addEventListener('click', () => {
  if (video.canonical_url || video.url) vscode.postMessage({ type: 'openExternal', url: video.canonical_url || video.url });
});
const player = document.getElementById('player');
if (model.embedUrl) {
  const iframe = document.createElement('iframe');
  iframe.id = 'youtube-player';
  iframe.title = 'Learning video';
  iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
  iframe.allowFullscreen = true;
  iframe.src = model.embedUrl;
  player.appendChild(iframe);
} else {
  const empty = document.createElement('div');
  empty.className = 'no-player';
  empty.textContent = 'No supported YouTube video ID was found. Use Open video to follow the source link.';
  player.appendChild(empty);
}
function seek(seconds) {
  if (!Number.isFinite(seconds)) return;
  if (ytPlayer && typeof ytPlayer.seekTo === 'function') {
    ytPlayer.seekTo(seconds, true);
    if (typeof ytPlayer.playVideo === 'function') ytPlayer.playVideo();
    return;
  }
  const iframe = document.getElementById('youtube-player');
  if (!iframe) return;
  iframe.contentWindow.postMessage(JSON.stringify({ event: 'command', func: 'seekTo', args: [seconds, true] }), 'https://www.youtube-nocookie.com');
  iframe.contentWindow.postMessage(JSON.stringify({ event: 'command', func: 'playVideo', args: [] }), 'https://www.youtube-nocookie.com');
}
function syncCurrentSegment(seconds) {
  if (!Number.isFinite(seconds)) return;
  let current = null;
  for (const segment of segments) {
    if (Number(segment.start_seconds) <= seconds) current = segment;
    else break;
  }
  const key = current && (current.lesson_key || 'segment-' + (segments.indexOf(current) + 1));
  if (key && key !== progress.active_segment) select(key);
}
setInterval(() => { if (ytPlayer && typeof ytPlayer.getCurrentTime === 'function') syncCurrentSegment(ytPlayer.getCurrentTime()); }, 1000);
function renderSegments() {
  const root = document.getElementById('segments');
  root.replaceChildren();
  if (!segments.length) {
    const empty = document.createElement('p');
    empty.className = 'meta';
    empty.textContent = 'No verified timestamps are available yet. Add reviewed chapters or transcript markers to the video evidence JSON.';
    root.appendChild(empty);
    return;
  }
  segments.forEach((segment, index) => {
    const key = segment.lesson_key || 'segment-' + (index + 1);
    const card = document.createElement('article');
    card.className = 'segment' + (progress.active_segment === key ? ' active' : '') + (progress.completed_segments.includes(key) ? ' done' : '');
    const head = document.createElement('div');
    head.className = 'segment-head';
    const time = document.createElement('a');
    time.className = 'segment-time';
    time.href = segment.timestamp_url || '#';
    time.textContent = segment.timestamp || 'timestamp';
    time.addEventListener('click', (event) => { event.preventDefault(); seek(Number(segment.start_seconds)); select(key); });
    const label = document.createElement('span');
    label.className = 'segment-title';
    label.textContent = segment.title || 'Untitled segment';
    head.append(time, label);
    card.appendChild(head);
    if (segment.summary) { const summary = document.createElement('p'); summary.className = 'segment-summary'; summary.textContent = segment.summary; card.appendChild(summary); }
    if (Array.isArray(segment.concepts) && segment.concepts.length) { const concepts = document.createElement('div'); concepts.className = 'meta'; concepts.textContent = 'Concepts: ' + segment.concepts.join(', '); card.appendChild(concepts); }
    const actions = document.createElement('div'); actions.className = 'segment-actions';
    const play = document.createElement('button'); play.textContent = 'Play segment'; play.addEventListener('click', () => { seek(Number(segment.start_seconds)); select(key); }); actions.appendChild(play);
    (segment.repository_paths || []).forEach((file) => { const open = document.createElement('button'); open.className = 'path'; open.textContent = 'Open ' + file; open.addEventListener('click', () => vscode.postMessage({ type: 'openFile', path: file })); actions.appendChild(open); });
    if (segment.lesson_path) { const lesson = document.createElement('button'); lesson.className = 'path'; lesson.textContent = 'Open lesson'; lesson.addEventListener('click', () => vscode.postMessage({ type: 'openFile', path: segment.lesson_path })); actions.appendChild(lesson); }
    const done = document.createElement('button'); done.textContent = progress.completed_segments.includes(key) ? 'Mark incomplete' : 'Mark complete'; done.addEventListener('click', () => { const completed = !progress.completed_segments.includes(key); vscode.postMessage({ type: 'saveProgress', lessonKey: key, completed }); }); actions.appendChild(done);
    card.appendChild(actions); root.appendChild(card);
  });
}
function select(key) {
  progress.active_segment = key;
  renderSegments();
  status.textContent = 'Active segment: ' + key;
  vscode.postMessage({ type: 'saveProgress', lessonKey: key, completed: progress.completed_segments.includes(key) });
}
window.addEventListener('message', (event) => { if (event.data && event.data.type === 'progressSaved') { progress = event.data.progress; renderSegments(); status.textContent = 'Progress saved locally in .upstack/sources/video-progress.json'; } });
renderSegments();
</script>
</body>
</html>`;
}

function safeVideoId(value: string | undefined, url: string): string | undefined {
  if (value && YOUTUBE_ID_RE.test(value)) return value;
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase().replace(/^www\\./, '');
    if (!['youtube.com', 'm.youtube.com', 'youtu.be'].includes(host)) return undefined;
    const candidate = host === 'youtu.be' ? parsed.pathname.slice(1) : parsed.searchParams.get('v') || parsed.pathname.split('/').filter(Boolean).pop();
    return candidate && YOUTUBE_ID_RE.test(candidate) ? candidate : undefined;
  } catch {
    return undefined;
  }
}

function isInsideWorkspace(candidate: string, workspace: string): boolean {
  const relative = path.relative(workspace, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

async function openWorkspaceFile(workspace: string, relativePath: string): Promise<void> {
  const clean = relativePath.replace(/\\/g, '/');
  const candidate = path.resolve(workspace, clean);
  if (!isInsideWorkspace(candidate, workspace)) {
    void vscode.window.showErrorMessage('The video map requested a file outside the workspace.');
    return;
  }
  try {
    const document = await vscode.workspace.openTextDocument(vscode.Uri.file(candidate));
    await vscode.window.showTextDocument(document, { preview: false });
  } catch {
    void vscode.window.showWarningMessage(`Could not open repository anchor: ${clean}`);
  }
}

async function openExternalUrl(value: string): Promise<void> {
  try {
    const url = new URL(value);
    if (!['https:', 'http:'].includes(url.protocol)) throw new Error('unsupported protocol');
    await vscode.env.openExternal(vscode.Uri.parse(url.toString()));
  } catch {
    void vscode.window.showWarningMessage('Only valid HTTP(S) source links can be opened.');
  }
}

async function readProgress(progressPath: string): Promise<ProgressRecord> {
  try {
    const value = JSON.parse(await fs.readFile(progressPath, 'utf8')) as Partial<ProgressRecord>;
    return { updated_at: value.updated_at || '', completed_segments: Array.isArray(value.completed_segments) ? value.completed_segments : [], active_segment: value.active_segment };
  } catch {
    return { updated_at: '', completed_segments: [] };
  }
}

async function writeProgress(progressPath: string, progress: ProgressRecord): Promise<void> {
  await fs.mkdir(path.dirname(progressPath), { recursive: true });
  await fs.writeFile(progressPath, JSON.stringify(progress, null, 2) + '\n', 'utf8');
}

function isMessage(value: unknown): value is { type: string; path: string; url: string; lessonKey: string; completed: boolean } {
  if (!value || typeof value !== 'object') return false;
  const message = value as Record<string, unknown>;
  if (typeof message.type !== 'string') return false;
  if (message.type === 'openFile') return typeof message.path === 'string';
  if (message.type === 'openExternal') return typeof message.url === 'string';
  if (message.type === 'saveProgress') return typeof message.lessonKey === 'string' && typeof message.completed === 'boolean';
  return false;
}

function createNonce(): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  return Array.from({ length: 32 }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join('');
}

async function generateMapInstructions(): Promise<void> {
  const terminal = vscode.window.createTerminal('Upstack Video Companion');
  terminal.show(true);
  terminal.sendText('python3 scripts/video_evidence.py "VIDEO_URL" --segments-file /tmp/video-segments.json --repository-file /tmp/repository-anchors.json --output .upstack/sources/video-map.md --json-output .upstack/sources/video-map.json', false);
  void vscode.window.showInformationMessage('Replace VIDEO_URL and the input paths, then run the displayed command to create the companion map.');
}

export function deactivate(): void {}
