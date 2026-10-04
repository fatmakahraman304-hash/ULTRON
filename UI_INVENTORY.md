# ULTRON UI migration inventory

Inspected before implementation, 2026-10-04.

| Capability | Existing implementation / contract | Migration |
|---|---|---|
| Startup | START.bat → main.py → integration.launcher.Services → mark_app.py | Retain process ownership, audio and shutdown |
| Desktop | ui.py + integration/panel.py + mission_control.py | Replace dashboard presentation with one embedded React entry; retain runtime callbacks and specialist dialogs |
| React/Vite | ultron/frontend/src/main.tsx → App.tsx; build currently hologram only | Build index.html and specialist hologram.html |
| Old UI | LegacyApp, cockpit, components/* HUD, frontend-mobile, static mission-control | Remove after checking import graph |
| Three.js | hologram/HologramScene, gestures, hand.worker, project | Preserve model lab; new independent Core scene |
| HTTP | ultron/backend/server.py (aiohttp), merged_api.py | Keep same-origin cookie boundary and token bootstrap |
| WebSocket | /ws: hello, system, ai, agent, memory, activity, notifications, patch, task, tests, barge_in, proactive_speech | Use these events, reconnect with cleanup; no duplicate sockets |
| AI | /api/ai, /api/models/health, /api/merged/invoke; ModelRouter | Use installed model list; add validated per-request selection |
| Voice | core/gemini.py and Qt callbacks own audio; backend PTT/live intentionally blocked while desktop owns audio | Preserve microphone ownership; Qt bridge carries actual HUD state and audio amplitude |
| Memory | /api/memory/v16, add/delete/search; semantic_memory, SQLite | Bind UI without changing storage |
| Files | /api/merged/document, /api/merged/tool → executor list_directory/read_text | Retain sandbox and approval |
| Terminal/browser | /api/agent/command → agent/approval; browser automation and shell tools | Requests through existing agent, never approved=True |
| Vision | /api/actions/screenshot, /api/vision/last/preview, screen_ocr, VisionLLM | Reuse capture/OCR; image upload adapter for existing VisionLLM |
| Tasks | /api/tasks, /{id}, /pause, /cancel, /approve | Real list/detail/start/pause/cancel + explicit approvals |
| Settings | /api/config, native audio/reconfiguration callbacks | Expose current config and native settings dialog |
| Security | PermissionManager, ApprovalGate, pending task IDs, patch review | Preserve; show pending requests with explicit approve/reject |

The existing merged local-model endpoint returns complete replies, not a token stream. Do not simulate streaming. Native voice transcripts arrive through the existing Qt signal bridge. Agent state/telemetry arrive through /ws. Model absence, disconnected service and missing sensors must remain visible, never replaced by random values.
