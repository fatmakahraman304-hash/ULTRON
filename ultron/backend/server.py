"""ULTRON V15 backend — aiohttp REST + WebSocket. Real data only."""
import asyncio
import copy
import json
import os
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import unquote

# Windows consoles frequently default to a legacy codepage (e.g. cp1252) that
# cannot encode Turkish/unicode text emitted by doctor/health diagnostics.
# Reconfigure stdio to UTF-8 with a safe fallback so free-form diagnostic text
# never crashes startup (on_startup) with UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

import aiohttp
from aiohttp import web
import uuid

from agent import Agent
from app.code_intel.analyzer import CodeIntel
from app.core.intent import VISION_PROMPT
from app.security.audit import AuditLog
from auth import Auth
from bridge import UltronBridge
from codegen import CodeGen
from app.core import doctor as doctor_mod
from app.core.backup_engine import BackupEngine
from health import build_health, log_health
from memory import MemorySystem
from notifier import Notifier
from telemetry import Telemetry
from tools import ToolRegistry


def get_system_stats_dict() -> dict:
    try:
        from app.telemetry.system_stats import get_system_stats
        return get_system_stats()
    except Exception:
        return {"available": False}
import test_runner

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
WORKSPACE = os.environ.get("ULTRON_WORKSPACE", os.path.dirname(BASE))
OLLAMA_HOST = os.environ.get("ULTRON_OLLAMA_HOST", "http://127.0.0.1:11434")
PERSISTENT = os.environ.get("ULTRON_PERSISTENT_MEMORY", "1") != "0"
VERSION = "15.0.0"


class Hub:
    def __init__(self) -> None:
        self.clients: set[web.WebSocketResponse] = set()
        self.activity: deque[dict] = deque(maxlen=30)
        self.notifications: deque[dict] = deque(maxlen=20)
        self.telemetry = Telemetry()
        self.ai_status: dict = {"connected": False, "host": OLLAMA_HOST, "models": [],
                                "primary": None, "vision": None, "embedding": None, "checked_at": 0}
        self.memory = MemorySystem(DATA_DIR, PERSISTENT)
        self.tools = ToolRegistry(WORKSPACE, self.broadcast_tools, self.on_activity, lambda: self.ai_status)
        self.agent = Agent(self.broadcast, self.tools, self.memory, self.telemetry,
                           lambda: self.ai_status, self.on_activity,
                           request_approval=self._request_approval)
        self.bridge: UltronBridge | None = None
        self.pending_task: dict | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.last_command_ts: float = 0.0
        self.scene_history = deque(maxlen=40)
        self.scene_future = deque(maxlen=40)
        self.stage_state: dict = {
            "mode": "core_idle",
            "title": "ULTRON",
            "subtitle": "NEURAL CORE",
            "progress": 0,
            "revision": 1,
            "job_id": None,
            "save_nonce": 0,
            "save_kind": "",
            "record_nonce": 0,
            "record_duration": 8.0,
            "hologram": {
                "kind": "energy", "color": "#ff3047", "glow": 1.0,
                "speed": 1.0, "rings": 4, "particles": 900, "scale": 1.0,
                "opacity": 0.92, "wireframe": False, "pulse": True,
                "label": "ULTRON",
            },
            "scene": {
                "objects": [],
                "links": [],
                "hud": [],
                "selected_id": None,
                "focus_id": None,
                "camera": "isometric",
                "camera_pose": None,
                "project_name": "Untitled",
                "explode": 0.0,
                "auto_orbit": True,
                "grid": True,
                "show_labels": True,
                "show_trails": True,
                "audio_reactive": True,
                "theme": "crimson",
                "snap": 0.25,
                "animation": "idle",
                "timeline": {
                    "duration": 8.0, "cursor": 0.0, "playing": False,
                    "loop": True, "started_at": None, "keyframes": [],
                },
                "cinematic": {
                    "enabled": False, "preset": "orbit", "duration": 8.0,
                    "started_at": None, "loop": True,
                },
            },
            "video": {
                "template": "ultron_intro", "duration": 6.0,
                "title": "ULTRON", "ready": False, "mime": "", "bytes": 0,
            },
        }
        try:
            _stage_saved = json.loads((Path(DATA_DIR) / "center_stage.json").read_text(encoding="utf-8"))
            if isinstance(_stage_saved, dict):
                if isinstance(_stage_saved.get("hologram"), dict):
                    self.stage_state["hologram"].update(_stage_saved["hologram"])
                if isinstance(_stage_saved.get("scene"), dict):
                    self.stage_state["scene"].update(_stage_saved["scene"])
                _saved_mode = str(_stage_saved.get("mode") or "")
                if _saved_mode in {"core_idle", "hologram_lab", "scene_lab"}:
                    self.stage_state["mode"] = _saved_mode
                    self.stage_state["title"] = str(_stage_saved.get("title") or self.stage_state["title"])[:100]
                    self.stage_state["subtitle"] = str(_stage_saved.get("subtitle") or self.stage_state["subtitle"])[:140]
        except Exception:
            pass
        self.audit = AuditLog()
        self.notifier = Notifier(lambda text, level: self._sched_notify(text, level))
        from app.security.sandbox import FilesystemSandbox
        try:
            _cfg = json.loads(Path(BASE, "config", "settings.json").read_text(encoding="utf-8"))
        except Exception:
            _cfg = {}
        self.sandbox = FilesystemSandbox(_cfg, workspace_root=os.path.dirname(BASE))
        self.codegen = CodeGen(Path(os.path.dirname(BASE)), self.audit, self.notifier.notify,
                               sandbox=self.sandbox)
        self.code_intel = CodeIntel(os.path.dirname(BASE))
        from app.security.rate_limit import RateLimiter
        try:
            _rlcfg = json.loads(Path(BASE, "config", "settings.json").read_text(encoding="utf-8"))
        except Exception:
            _rlcfg = {}
        self.rate_limiter = RateLimiter(_rlcfg)
        self.auth = Auth(Path(DATA_DIR) / "auth" / "sessions.json", os.environ.get("ULTRON_AUTH", "0") == "1")
        from app.personal.user_dna import MasterRules, UserDNA
        from app.personal.workspace_sentinel import WorkspaceSentinel
        from app.security.voiceprint_guard import VoiceprintGuard
        self.rules = MasterRules()
        self.voiceprint = VoiceprintGuard()
        self.dna = UserDNA()
        self.sentinel = WorkspaceSentinel()

    def _sched_notify(self, text: str, level: str) -> None:
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.notify(text, level), self.loop)

    def bridge_available_llm(self) -> bool:
        return bool(self.bridge and self.bridge.available and self.ai_status.get("connected"))

    def _request_approval(self, text: str, risks: list[str]) -> str | None:
        """Server-side approval store: create a pending task, return its id.

        The ONLY path that grants `approved=True` to the agent is
        /api/task/approve, which validates a pending task id server-side.
        Client-supplied `approved` flags are never trusted."""
        tid = uuid.uuid4().hex[:8]
        self.pending_task = {
            "id": tid, "text": text, "created": time.time(), "risks": risks,
            "steps": [{"label": r, "tool": "terminal", "dangerous": True} for r in risks],
        }
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._approval_requested(tid, risks))
        except RuntimeError:
            pass
        return tid

    async def _approval_requested(self, tid: str, risks: list[str]) -> None:
        await self.broadcast_task()
        await self.on_activity(f"Approval required (task {tid}): {', '.join(risks)}", "warn")
        self.notifier.notify("approval", f"Onay bekleyen komut: {tid}", "warn", force=True)

    async def _task_event(self, ev: dict) -> None:
        await self.broadcast({"type": "task_engine", "data": ev})

    def tools_list(self) -> list[dict]:
        base = self.tools.list_status()
        return base + (self.bridge.capabilities() if self.bridge else [])

    async def broadcast_tools(self, _payload: dict | None = None) -> None:
        await self.broadcast({"type": "tools", "data": self.tools_list()})

    async def broadcast_task(self) -> None:
        await self.broadcast({"type": "task", "data": self.pending_task})

    # ---------- broadcast / events ----------
    async def broadcast(self, payload: dict) -> None:
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    async def on_activity(self, text: str, kind: str = "info") -> None:
        self.activity.appendleft({"ts": time.time(), "text": text, "kind": kind})
        await self.broadcast({"type": "activity", "data": list(self.activity)})

    async def notify(self, text: str, level: str = "info") -> None:
        self.notifications.appendleft({"ts": time.time(), "text": text, "level": level})
        await self.broadcast({"type": "notifications", "data": list(self.notifications)})

    # ---------- live probes ----------
    async def check_ollama(self) -> dict:
        try:
            timeout = aiohttp.ClientTimeout(total=2.5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(OLLAMA_HOST + "/api/tags") as resp:
                    data = await resp.json()
            models = [m.get("name", "?") for m in data.get("models", [])]
        except Exception:
            new = {"connected": False, "host": OLLAMA_HOST, "models": [],
                   "primary": None, "vision": None, "embedding": None, "checked_at": time.time()}
        else:
            primary = os.environ.get("ULTRON_MODEL") or (models[0] if models else None)
            vision = next((m for m in models if any(k in m.lower() for k in ("llava", "vision"))), None)
            embedding = next((m for m in models if "embed" in m.lower()), None)
            new = {"connected": True, "host": OLLAMA_HOST, "models": models,
                   "primary": primary, "vision": vision, "embedding": embedding, "checked_at": time.time()}
        changed = new["connected"] != self.ai_status.get("connected")
        self.ai_status = new
        self.tools.refresh_sync()
        return {"changed": changed, "status": new}

    def snapshot_all(self) -> dict:
        return {
            "system": self.telemetry.snapshot(),
            "ai": self.ai_status,
            "tools": self.tools_list(),
            "memory": self.memory.status(),
            "activity": list(self.activity),
            "notifications": list(self.notifications),
            "agent": {"state": self.agent.state},
            "stage": self.stage_state,
            "config": self.config(),
        }

    def config(self) -> dict:
        return {
            "version": VERSION,
            "ollama_host": OLLAMA_HOST,
            "primary_model": self.ai_status.get("primary"),
            "persistent_memory": PERSISTENT,
            "workspace": WORKSPACE,
        }


os.chdir(BASE)  # initialize relative databases in backend, independent of caller cwd
hub = Hub()


# ---------------- HTTP routes ----------------
async def api_system(_req: web.Request) -> web.Response:
    return web.json_response(hub.telemetry.snapshot())


async def api_ai(_req: web.Request) -> web.Response:
    res = await hub.check_ollama()
    return web.json_response(res["status"])


async def api_tools(_req: web.Request) -> web.Response:
    return web.json_response(hub.tools_list())


async def api_memory(_req: web.Request) -> web.Response:
    status = hub.memory.status()
    if hub.bridge and hub.bridge.available:
        try:
            status["v16_total"] = hub.bridge.runtime.memory.count()
        except Exception:
            status["v16_total"] = None
    return web.json_response(status)


async def api_audit(_req: web.Request) -> web.Response:
    if hub.bridge and hub.bridge.available:
        return web.json_response(hub.bridge.runtime.audit.recent(30))
    return web.json_response([])


async def api_voice_metrics(_req: web.Request) -> web.Response:
    if hub.bridge:
        return web.json_response(hub.bridge.voice_stack.get_metrics())
    return web.json_response({})


async def api_voice_metrics_history(req: web.Request) -> web.Response:
    try:
        hours = float(req.query.get("hours", "24"))
    except ValueError:
        hours = 24.0
    if hub.bridge:
        return web.json_response(hub.bridge.metrics_store.percentiles(hours))
    return web.json_response({"count": 0})


async def api_system_health(_req: web.Request) -> web.Response:
    h = dict(getattr(hub, "health", {}))
    h["ollama"] = "connected" if hub.ai_status.get("connected") else "offline"
    return web.json_response(h)


# ---------------- Phase-4: sovereign / master / voiceprint / workspace ----------------
async def api_voiceprint_enroll(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    pcm = body.get("pcm_b64", "")
    if not pcm:
        return web.json_response({"ok": False, "error": "pcm_b64 required"}, status=400)
    from app.security.voiceprint_guard import b64_to_pcm
    res = hub.voiceprint.enroll(b64_to_pcm(pcm))
    hub.audit.write("VOICEPRINT_ENROLL", f"dims={res.get('dims')} engine={res.get('engine')}")
    return web.json_response(res)


async def api_voiceprint_verify(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    from app.security.voiceprint_guard import b64_to_pcm
    res = hub.voiceprint.verify(b64_to_pcm(body.get("pcm_b64", "")))
    if not res.get("ok") and not res.get("bypassed"):
        hub.audit.write("VOICEPRINT_REJECT", f"sim={res.get('similarity')} line={res.get('reject_line', '')[:40]}")
    return web.json_response(res)


async def api_master_profile(_req: web.Request) -> web.Response:
    return web.json_response({
        "rules": hub.rules.get(),
        "tampered_restored": hub.rules.tampered,
        "voiceprint": {"enabled": hub.voiceprint.enabled,
                       "threshold": hub.voiceprint.threshold,
                       "enrolled": hub.voiceprint._load() is not None},
        "dna_rows": len(hub.dna.recent(30)),
        "workspace": hub.sentinel.state(),
    })


async def api_master_insights(_req: web.Request) -> web.Response:
    return web.json_response({"insights": hub.dna.insights(7)})


async def api_workspace_state(_req: web.Request) -> web.Response:
    return web.json_response(hub.sentinel.state())


# ---------------- Phase-6: Master HUD ----------------
# ---------------- Neural TTS (edge-tts) ----------------
async def api_tts_speak(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    text = str(body.get("text", "")).strip()
    rt = _rt()
    tts = rt.tts if rt else None
    if tts is None:
        from app.voice.tts import TextToSpeech
        tts = TextToSpeech()
    try:
        audio, fmt = await tts.synthesize(text)
    except Exception as e:  # noqa: BLE001
        return web.json_response({"ok": False, "error": str(e)}, status=503)
    import base64 as _b64
    return web.json_response({"ok": True, "audio_b64": _b64.b64encode(audio).decode("ascii"),
                              "format": fmt, "engine": tts.backend(),
                              "voice": tts.voice, "rate": tts.rate, "pitch": tts.pitch})


async def api_tts_status(_req: web.Request) -> web.Response:
    rt = _rt()
    tts = rt.tts if rt else None
    if tts is None:
        from app.voice.tts import TextToSpeech
        tts = TextToSpeech()
    return web.json_response({"engine": tts.backend(), "voice": tts.voice,
                              "rate": tts.rate, "pitch": tts.pitch})


# ---------------- Phase-12.2: UI theme relay (PC->mobile sync) ----------------
async def api_ui_theme_get(_req: web.Request) -> web.Response:
    return web.json_response(getattr(hub, "ui_theme", {"name": "CRIMSON", "ts": 0}))


async def api_ui_theme_post(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    name = str(body.get("name", "CRIMSON"))
    if name not in ("CRIMSON", "CYAN", "PURPLE", "HYBRID"):
        return web.json_response({"ok": False, "error": "unknown theme"}, status=400)
    hub.ui_theme = {"name": name, "ts": time.time()}
    return web.json_response({"ok": True, **hub.ui_theme})


# ---------------- Phase-11: presence ----------------
async def api_presence_ping(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    snap = hub.telemetry.snapshot()
    briefing = (f"Kısa brifing: CPU %{snap['cpu']['percent']}, RAM %{snap['ram']['percent']}, "
                f"Ollama {'çevrimiçi' if hub.ai_status.get('connected') else 'uykuda'}.")
    res = hub.presence.ping(str(body.get("source", "manual")),
                            str(body.get("device_id", "local")), briefing)
    hub.audit.write("PRESENCE_PING", f"{body.get('source')} welcomed={res['welcomed']}")
    return web.json_response(res)


async def api_presence_status(_req: web.Request) -> web.Response:
    return web.json_response(hub.presence.status())


# ---------------- Phase-10: IoT Nexus ----------------
async def api_iot_devices(_req: web.Request) -> web.Response:
    return web.json_response(hub.iot.list())


async def api_iot_control(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    res = hub.iot.control(str(body.get("device_id", "")),
                          str(body.get("action", "toggle")),
                          body.get("value"))
    if res.get("ok"):
        hub.audit.write("IOT_CONTROL", f"{body.get('device_id')} {body.get('action')}")
    return web.json_response(res)


async def api_iot_scene(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    res = hub.scenes.activate(str(body.get("scene_name", "")))
    hub.audit.write("IOT_SCENE", str(body.get("scene_name")))
    return web.json_response(res)


async def api_iot_discover(_req: web.Request) -> web.Response:
    return web.json_response(hub.iot.discover())


# ---------------- Phase-9: dual-brain mesh ----------------
def _mesh_auth_ok(req: web.Request) -> bool:
    token = req.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if bool(token) and token in hub.auth.sessions:
        return True
    # PHASE 12: mobil düğüm eşleştirme anahtarı (vault 'mesh_node_key' / env)
    key = req.headers.get("X-Mesh-Key", "").strip()
    if not key:
        return False
    import os as _os
    expected = _os.environ.get("ULTRON_MESH_KEY", "")
    rt = _rt()
    if not expected and rt is not None:
        try:
            expected = rt.vault.get("mesh_node_key") or ""
        except Exception:
            expected = ""
    return bool(expected) and key == expected


async def api_mesh_handshake(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    res = hub.mesh_registry.handshake(
        str(body.get("node_id", "unknown")), str(body.get("role", "")),
        str(body.get("version", "0")), _mesh_auth_ok(req),
        caps=body.get("caps") or [])  # PHASE 14: capability declaration
    return web.json_response(res)


async def api_mesh_push(req: web.Request) -> web.Response:
    if not _mesh_auth_ok(req):
        return web.json_response({"ok": False, "error": "unauthorized node"}, status=401)
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    res = hub.mesh_sync.push(body)
    hub.audit.write("MESH_PUSH", str(res)[:100])
    return web.json_response({"ok": True, **res})


async def api_mesh_pull(req: web.Request) -> web.Response:
    if not _mesh_auth_ok(req):
        return web.json_response({"ok": False, "error": "unauthorized node"}, status=401)
    try:
        since = float(req.query.get("since_ts", "0"))
    except ValueError:
        since = 0.0
    return web.json_response(hub.mesh_sync.pull(since))


async def api_mesh_heartbeat(req: web.Request) -> web.Response:
    if not _mesh_auth_ok(req):
        return web.json_response({"ok": False, "error": "unauthorized node"}, status=401)
    node = req.query.get("node_id", "")
    alive = hub.mesh_registry.heartbeat(str(node))
    return web.json_response({"ok": alive,
                              "nodes": hub.mesh_registry.status() if alive else []})


async def api_mesh_nodes(_req: web.Request) -> web.Response:
    return web.json_response({"nodes": hub.mesh_registry.status(),
                              "pc_online": hub.mesh_registry.pc_online(),
                              "mobile_online": hub.mesh_registry.mobile_online()})


# ---------------- Phase-8: doctor + backup ----------------
async def api_system_doctor(_req: web.Request) -> web.Response:
    ctx = {
        "ollama_host": OLLAMA_HOST,
        "db_paths": [str(p) for p in Path(DATA_DIR).rglob("*.db")],
        "allow_busy_ports": True,
        "rules_path": os.path.join(BASE, "config", "security", "master_rules.json"),
    }
    res = doctor_mod.run_doctor(
        ctx, persona=(hub.bridge.runtime.agent.persona
                      if (hub.bridge and hub.bridge.available) else None))
    hub.last_doctor = res
    return web.json_response(res)


async def api_backup_create(_req: web.Request) -> web.Response:
    res = hub.backup.create()
    hub.audit.write("BACKUP_CREATE", f"{res['backup_id']} sha={res['sha256'][:16]}")
    return web.json_response({"ok": True, **res})


async def api_backup_list(_req: web.Request) -> web.Response:
    return web.json_response(hub.backup.list())


async def api_backup_restore(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    try:
        res = hub.backup.restore(str(body.get("backup_id", "")))
    except ValueError as e:
        hub.audit.write("BACKUP_RESTORE_REJECT", str(e)[:60])
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    hub.audit.write("BACKUP_RESTORE", res["backup_id"])
    return web.json_response({"ok": True, **res})


# ---------------- Phase-7: emotion + memory evolution ----------------
def _rt():
    return hub.bridge.runtime if (hub.bridge and hub.bridge.available) else None


async def api_emotion_analyze(req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"ok": False, "error": "runtime unavailable"}, status=503)
    try:
        body = await req.json()
    except Exception:
        body = {}
    from app.emotion.emotion_engine import analyze as em_analyze
    import base64 as _b64
    pcm = _b64.b64decode(body["audio_b64"]) if body.get("audio_b64") else None
    res = em_analyze(pcm=pcm, text=body.get("text"))
    rt.emotion_log.add(res["state"], res["confidence"], res["source"])
    hint = rt.adaptive.adapt(res["state"], res["confidence"])
    return web.json_response({**res, "adapted_hint": hint})


async def api_emotion_history(req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"rows": [], "trend": {}})
    try:
        hours = float(req.query.get("hours", "24"))
    except ValueError:
        hours = 24.0
    return web.json_response(rt.emotion_log.history(hours))


async def api_memory_stats(_req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"ok": False, "error": "runtime unavailable"}, status=503)
    return web.json_response(rt.semv2.stats())


async def api_memory_decay_run(_req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"ok": False, "error": "runtime unavailable"}, status=503)
    n = rt.semv2.decay()
    hub.audit.write("MEMORY_DECAY", f"archived={n}")
    return web.json_response({"ok": True, "archived": n})


async def api_memory_export(_req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"ok": False, "error": "runtime unavailable"}, status=503)
    from app.memory import memory_io
    res = memory_io.export_local(rt.memory, hub.dna, hub.rules)
    hub.audit.write("MEMORY_EXPORT", res["sha256"][:16])
    return web.json_response({"ok": True, **res})


async def api_memory_import(req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"ok": False, "error": "runtime unavailable"}, status=503)
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    from app.memory import memory_io
    try:
        res = memory_io.import_snapshot(rt.memory, hub.dna, body)
    except ValueError as e:
        hub.audit.write("MEMORY_IMPORT_REJECT", str(e)[:60])
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    hub.audit.write("MEMORY_IMPORT", str(res))
    return web.json_response({"ok": True, **res})


async def api_hud_overview(_req: web.Request) -> web.Response:
    return web.json_response(hub.hud.overview())


async def api_hud_audit_recent(req: web.Request) -> web.Response:
    try:
        limit = int(req.query.get("limit", "20"))
    except ValueError:
        limit = 20
    return web.json_response(hub.hud.audit_recent(limit))


async def api_hud_persona_trends(_req: web.Request) -> web.Response:
    return web.json_response(hub.hud.persona_trends(50))


async def api_hud_self_diagnostic(_req: web.Request) -> web.Response:
    rt = _rt()
    if rt:
        res = rt.self_diagnostic()
    else:
        res = hub.hud.self_diagnostic()
    hub.audit.write("SELF_DIAGNOSTIC", res.get("report", "")[:120])
    return web.json_response(res)


async def api_vision_toggle(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    res = hub.vision_control.toggle(bool(body.get("enabled", False)))
    hub.audit.write("VISION_TOGGLE", res["status"])
    return web.json_response({"ok": True, **res})


async def api_vision_status(_req: web.Request) -> web.Response:
    return web.json_response(hub.vision_control.status())


async def api_vision_scan_now(_req: web.Request) -> web.Response:
    return web.json_response(hub.vision_control.scan_now())


async def api_sovereign_audit(_req: web.Request) -> web.Response:
    from app.security import sovereign_privacy as sov
    import importlib.util as _iu
    from health import tts_backend_name
    a = sov.audit(OLLAMA_HOST, tts_backend_name(),
                  _iu.find_spec("faster_whisper") is not None,
                  hub.ai_status.get("connected", False))
    a["sovereign_status"] = sov.sovereign_status(a)
    return web.json_response(a)


async def api_config_reload(_req: web.Request) -> web.Response:
    if not (hub.bridge and hub.bridge.available):
        return web.json_response({"ok": False, "error": "runtime unavailable"}, status=503)
    st = hub.bridge.runtime.reload_config()
    if getattr(hub, "health", None):
        hub.health["persona_guard"]["mode"] = st.get("persona_guard_mode", "reframe")
    await hub.on_activity("Config hot-reload applied", "info")
    return web.json_response({"ok": True, "persona_guard_mode": st.get("persona_guard_mode", "reframe")})



async def api_voice_ptt(req: web.Request) -> web.Response:
    """Push-to-talk fallback — wake-word yetersizse manuel tetikleme."""
    try:
        body = await req.json()
    except Exception:
        body = {}
    seconds = float(body.get("seconds", 6.0))
    if not hub.bridge or not hub.bridge.runtime:
        return web.json_response({"ok": False, "error": "runtime unavailable"})
    lv = getattr(hub.bridge.runtime, "live_voice", None)
    if lv is None:
        return web.json_response({"ok": False, "error": "live_voice unavailable"})
    # LiveVoiceV2'yi tek seferlik tetikle
    import threading
    def _trigger():
        try:
            lv._on_wake()
        except Exception as e:
            import logging
            logging.getLogger("ultron.ptt").error("PTT hata: %s", e)
    threading.Thread(target=_trigger, daemon=True, name="ptt-trigger").start()
    return web.json_response({"ok": True, "mode": "ptt", "seconds": seconds})


async def api_capabilities(req: web.Request) -> web.Response:
    """Frontend capabilities paneli için yetenek listesi."""
    caps = []
    if hub.bridge:
        try:
            caps = hub.bridge.capabilities()
        except Exception as e:
            caps = [{"id": "error", "label": "Error", "status": "ERROR", "detail": str(e)}]
    return web.json_response(caps)

async def api_voice_live(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    on = bool(body.get("on"))
    if not (hub.bridge and hub.bridge.available):
        return web.json_response({"ok": False, "error": "V16 runtime unavailable"})
    import importlib.util as _iu
    if not (_iu.find_spec("sounddevice") and _iu.find_spec("faster_whisper")):
        return web.json_response({"ok": False, "error": "sounddevice + faster-whisper not installed"})
    if on:
        result = hub.bridge.start_live_voice_wake()
        mode = result.get("note", "wake-word")
        await hub.on_activity(f"Ses dinleme başladı ({mode})", "info")
        return web.json_response({"ok": result.get("ok", True), "mode": "wake-word", "result": result})
    else:
        hub.bridge.runtime.stop_live_voice()
        await hub.on_activity("Ses dinleme durduruldu", "info")
        return web.json_response({"ok": True})


# ---------------- Dynamic Center Stage ----------------
_STAGE_MODES = {"core_idle", "hologram_lab", "scene_lab", "video_rendering", "video_preview",
                "task_progress", "screen_preview"}


def _stage_number(value, default, low, high):
    try:
        return max(low, min(high, float(value)))
    except Exception:
        return default


def _stage_int(value, default, low, high):
    try:
        return max(low, min(high, int(value)))
    except Exception:
        return default


async def _stage_publish() -> None:
    hub.stage_state["revision"] = int(hub.stage_state.get("revision", 0)) + 1
    try:
        mode = hub.stage_state.get("mode")
        persistent_mode = mode if mode in {"core_idle","hologram_lab","scene_lab"} else (
            "scene_lab" if (hub.stage_state.get("scene") or {}).get("objects") else "core_idle"
        )
        if persistent_mode == "core_idle":
            persistent_title, persistent_subtitle = "ULTRON", "NEURAL CORE"
        elif persistent_mode == "hologram_lab":
            _holo = hub.stage_state.get("hologram") or {}
            persistent_title = str(_holo.get("label") or "HOLOGRAM")[:100]
            persistent_subtitle = f"{str(_holo.get('kind') or 'energy').upper()} / LIVE"
        else:
            _scene = hub.stage_state.get("scene") or {}
            persistent_title = "SCENE LAB"
            persistent_subtitle = f"{len(_scene.get('objects') or [])} OBJECTS / SAVED"
        persistent = {
            "version": 3,
            "mode": persistent_mode,
            "title": persistent_title,
            "subtitle": persistent_subtitle,
            "hologram": hub.stage_state.get("hologram"),
            "scene": hub.stage_state.get("scene"),
            "saved_at": time.time(),
        }
        (Path(DATA_DIR) / "center_stage.json").write_text(
            json.dumps(persistent, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
    await hub.broadcast({"type": "stage", "data": hub.stage_state})


def _scene_checkpoint() -> None:
    hub.scene_history.append(copy.deepcopy(hub.stage_state.get("scene") or {}))
    hub.scene_future.clear()


def _scene_defaults() -> dict:
    return {
        "objects": [], "links": [], "hud": [], "groups": [], "camera_bookmarks": [], "measurements": [],
        "selected_id": None, "selected_ids": [], "focus_id": None, "target_id": None, "camera": "isometric",
        "camera_pose": None, "camera_track": [], "project_name": "Untitled", "explode": 0.0, "auto_orbit": True, "grid": True,
        "show_labels": True, "show_trails": True, "audio_reactive": True, "collision_overlay": False, "render_mode": "hologram", "theme": "crimson", "snap": 0.25,
        "animation": "idle",
        "sequence": {
            "name": "", "steps": [], "playing": False, "loop": False,
            "started_at": None, "run_id": 0, "duration": 0.0,
        },
        "timeline": {
            "duration": 8.0, "cursor": 0.0, "playing": False,
            "loop": True, "started_at": None, "keyframes": [],
        },
        "cinematic": {
            "enabled": False, "preset": "orbit", "duration": 8.0,
            "started_at": None, "loop": True,
        },
    }


def _scene_ensure(scene: dict) -> dict:
    defaults = _scene_defaults()
    for key, value in defaults.items():
        if key not in scene:
            scene[key] = copy.deepcopy(value)
    if not isinstance(scene.get("objects"), list): scene["objects"] = []
    if not isinstance(scene.get("links"), list): scene["links"] = []
    if not isinstance(scene.get("hud"), list): scene["hud"] = []
    if not isinstance(scene.get("groups"), list): scene["groups"] = []
    if not isinstance(scene.get("camera_bookmarks"), list): scene["camera_bookmarks"] = []
    if not isinstance(scene.get("camera_track"), list): scene["camera_track"] = []
    if not isinstance(scene.get("measurements"), list): scene["measurements"] = []
    if not isinstance(scene.get("selected_ids"), list): scene["selected_ids"] = []
    if not isinstance(scene.get("timeline"), dict): scene["timeline"] = copy.deepcopy(defaults["timeline"])
    if not isinstance(scene.get("cinematic"), dict): scene["cinematic"] = copy.deepcopy(defaults["cinematic"])
    if not isinstance(scene.get("sequence"), dict): scene["sequence"] = copy.deepcopy(defaults["sequence"])
    seq=dict(scene.get("sequence") or {});steps=[]
    allowed_seq_ops={"scene_select","scene_target_lock","scene_target_clear","scene_render_mode","scene_animation",
                     "scene_cinematic","scene_camera","scene_focus","scene_physics","scene_path_play","scene_path_stop",
                     "scene_constraint","timeline_play","timeline_pause","scene_hud_add","scene_hud_clear"}
    for step in (seq.get("steps") or [])[:64]:
        if not isinstance(step,dict): continue
        sop=str(step.get("operation") or "").strip().lower()
        if sop not in allowed_seq_ops: continue
        args=step.get("args") if isinstance(step.get("args"),dict) else {}
        safe_args={}
        for k,v in list(args.items())[:24]:
            if isinstance(v,(str,int,float,bool)) or v is None: safe_args[str(k)[:40]]=v
        steps.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(step.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                      "at":_stage_number(step.get("at",0),0,0,120),
                      "operation":sop,"args":safe_args,"label":str(step.get("label") or sop)[:60]})
    steps.sort(key=lambda x:float(x.get("at",0)))
    seq["steps"]=steps;seq["duration"]=max([float(x.get("at",0)) for x in steps],default=0.0)
    seq["playing"]=bool(seq.get("playing",False));seq["loop"]=bool(seq.get("loop",False))
    seq["run_id"]=_stage_int(seq.get("run_id",0),0,0,2_000_000_000)
    scene["sequence"]=seq
    for obj in scene.get("objects") or []:
        if not isinstance(obj, dict):
            continue
        if "motion" not in obj:
            obj["motion"] = {"type": "none", "speed": 1.0, "radius": 1.5, "amplitude": .5, "axis": "y"}
        if "visible" not in obj:
            obj["visible"] = True
        if "locked" not in obj:
            obj["locked"] = False
        if "clip_speed" not in obj:
            obj["clip_speed"] = 1.0
        if "clip_paused" not in obj:
            obj["clip_paused"] = False
        if "parent_id" not in obj:
            obj["parent_id"] = None
        if "physics" not in obj or not isinstance(obj.get("physics"), dict):
            obj["physics"] = {"mode":"off","gravity":9.81,"velocity":[0.0,0.0,0.0],"bounce":.45,"floor":-1.3,"started_at":None}
        if "constraint" not in obj or not isinstance(obj.get("constraint"), dict):
            obj["constraint"] = {"type":"none","target_id":None,"distance":2.0,"speed":1.0,"offset":[0.0,0.0,0.0]}
        if "path" not in obj or not isinstance(obj.get("path"), dict):
            obj["path"] = {"points":[],"speed":1.0,"loop":True,"started_at":None}
    ids = {str(o.get("id")) for o in scene.get("objects") or [] if isinstance(o, dict)}
    for obj in scene.get("objects") or []:
        if not isinstance(obj, dict): continue
        parent = str(obj.get("parent_id") or "")
        if parent not in ids or parent == str(obj.get("id")):
            obj["parent_id"] = None
    for obj in scene.get("objects") or []:
        if not isinstance(obj,dict): continue
        constraint=dict(obj.get("constraint") or {})
        target=str(constraint.get("target_id") or "")
        if target not in ids or target==str(obj.get("id")):
            constraint["target_id"]=None
            if str(constraint.get("type") or "none")!="none": constraint["type"]="none"
        obj["constraint"]=constraint
        path=dict(obj.get("path") or {});points=[]
        for point in (path.get("points") or [])[:32]:
            if not isinstance(point,list): continue
            p=list(point)
            while len(p)<3:p.append(0)
            points.append([_stage_number(p[0],0,-12,12),_stage_number(p[1],0,-8,8),_stage_number(p[2],0,-12,12)])
        path["points"]=points;obj["path"]=path
    if str(scene.get("target_id") or "") not in ids: scene["target_id"]=None
    scene["selected_ids"] = [str(x) for x in scene.get("selected_ids") or [] if str(x) in ids][:16]
    selected = str(scene.get("selected_id") or "")
    if selected and selected in ids and selected not in scene["selected_ids"]:
        scene["selected_ids"].insert(0, selected)
    if not selected and scene["selected_ids"]:
        scene["selected_id"] = scene["selected_ids"][0]
    # Keep only valid group memberships/bookmarks.
    clean_groups = []
    for group in scene.get("groups") or []:
        if not isinstance(group, dict): continue
        members = [str(x) for x in group.get("members") or [] if str(x) in ids]
        if members:
            clean_groups.append({"id": str(group.get("id") or uuid.uuid4().hex[:8])[:24],
                                 "name": str(group.get("name") or "GROUP")[:60],
                                 "members": members[:16]})
    scene["groups"] = clean_groups[:16]
    scene["camera_bookmarks"] = [b for b in (scene.get("camera_bookmarks") or []) if isinstance(b, dict)][:12]
    return scene


def _scene_resolve_object(scene: dict, value=None, label=None, fallback=None) -> str:
    raw = str(value or "").strip()
    label_raw = str(label or "").strip()
    objects = scene.get("objects") or []
    if raw:
        exact = next((str(o.get("id")) for o in objects if str(o.get("id")) == raw), None)
        if exact: return exact
    needle = label_raw or raw
    if needle:
        exact_label = next((str(o.get("id")) for o in objects if str(o.get("label") or "").lower() == needle.lower()), None)
        if exact_label: return exact_label
        partial = next((str(o.get("id")) for o in objects if needle.lower() in str(o.get("label") or "").lower()), None)
        if partial: return partial
    return str(fallback or "")


async def api_stage_model_upload(req: web.Request) -> web.Response:
    name = unquote(str(req.headers.get("X-Model-Name") or "model.glb")).replace("\\", "_").replace("/", "_").strip() or "model.glb"
    if not name.lower().endswith(".glb"):
        return web.json_response({"ok":False,"error":"glb_required"}, status=400)
    data = await req.read()
    if not data or len(data) > 50 * 1024 * 1024:
        return web.json_response({"ok":False,"error":"invalid_model_size"}, status=413)
    if data[:4] != b"glTF":
        return web.json_response({"ok":False,"error":"invalid_glb_header"}, status=400)
    model_id = uuid.uuid4().hex
    directory = Path(DATA_DIR) / "scene_models"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{model_id}.glb"
    path.write_bytes(data)
    meta = {"id":model_id,"name":name[:160],"bytes":len(data),"created_at":time.time()}
    (directory / f"{model_id}.json").write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
    await hub.on_activity(f"Scene model imported: {name[:80]}", "success")
    return web.json_response({"ok":True,"model_id":model_id,"name":name[:160],"bytes":len(data)})


async def api_stage_model_get(req: web.Request) -> web.StreamResponse:
    model_id = re.sub(r"[^A-Za-z0-9_-]","",str(req.match_info.get("model_id") or ""))[:48]
    path = Path(DATA_DIR) / "scene_models" / f"{model_id}.glb"
    if not model_id or not path.exists():
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers={"Content-Type":"model/gltf-binary","Cache-Control":"private, max-age=3600"})


async def api_stage_models_list(_req: web.Request) -> web.Response:
    directory = Path(DATA_DIR) / "scene_models"
    models = []
    if directory.exists():
        for meta_path in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                model_id = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("id") or meta_path.stem))[:48]
                glb = directory / f"{model_id}.glb"
                if not glb.exists():
                    continue
                models.append({"id":model_id,"name":str(data.get("name") or "model.glb")[:160],
                               "bytes":int(data.get("bytes") or glb.stat().st_size),
                               "created_at":float(data.get("created_at") or glb.stat().st_mtime)})
            except Exception:
                continue
    return web.json_response({"ok":True,"models":models[:100]})


async def api_stage_model_delete(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    model_id = re.sub(r"[^A-Za-z0-9_-]", "", str(body.get("model_id") or ""))[:48]
    if not model_id:
        return web.json_response({"ok":False,"error":"model_id_required"}, status=400)
    in_use = [o for o in (hub.stage_state.get("scene",{}).get("objects") or [])
              if str(o.get("model_id") or "") == model_id]
    if in_use:
        return web.json_response({"ok":False,"error":"model_in_use"}, status=409)
    directory = Path(DATA_DIR) / "scene_models"
    removed = False
    for suffix in (".glb",".json"):
        path = directory / f"{model_id}{suffix}"
        if path.exists():
            path.unlink()
            removed = True
    if not removed:
        return web.json_response({"ok":False,"error":"model_not_found"}, status=404)
    await hub.on_activity(f"Scene model removed: {model_id[:12]}", "info")
    return web.json_response({"ok":True,"deleted":model_id})


async def api_stage_get(_req: web.Request) -> web.Response:
    return web.json_response({"ok": True, **hub.stage_state})


async def api_stage_command(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    op = str(body.get("operation", "")).strip().lower()
    state = hub.stage_state
    if isinstance(state.get("scene"), dict):
        state["scene"] = _scene_ensure(state["scene"])
    if op.startswith("scene_") and op not in {"scene_open", "scene_select", "scene_multi_select", "scene_group_select", "scene_save", "scene_undo", "scene_redo", "scene_project_list", "scene_project_load", "scene_camera_bookmark_list", "scene_asset_list", "scene_asset_add", "scene_asset_delete", "scene_diagnostics", "scene_collision_overlay", "scene_target_lock", "scene_target_clear",
 "scene_sequence_play", "scene_sequence_stop", "scene_snapshot_list"}:
        _scene_checkpoint()

    if op in {"reset", "core", "core_idle"}:
        state.update({"mode": "core_idle", "title": "ULTRON",
                      "subtitle": "NEURAL CORE", "progress": 0, "job_id": None})
    elif op in {"hologram_create", "hologram", "hologram_show"}:
        holo = dict(state.get("hologram") or {})
        kind = str(body.get("kind") or holo.get("kind") or "energy").strip().lower()
        allowed = {"energy", "globe", "network", "drone", "vehicle", "logo", "sphere"}
        if kind not in allowed:
            kind = "energy"
        holo.update({
            "kind": kind,
            "color": str(body.get("color") or holo.get("color") or "#ff3047")[:24],
            "glow": _stage_number(body.get("glow", holo.get("glow", 1.0)), 1.0, 0.0, 3.0),
            "speed": _stage_number(body.get("speed", holo.get("speed", 1.0)), 1.0, 0.05, 5.0),
            "rings": _stage_int(body.get("rings", holo.get("rings", 4)), 4, 0, 12),
            "particles": _stage_int(body.get("particles", holo.get("particles", 900)), 900, 0, 5000),
            "scale": _stage_number(body.get("scale", holo.get("scale", 1.0)), 1.0, 0.25, 2.5),
            "opacity": _stage_number(body.get("opacity", holo.get("opacity", .92)), .92, .08, 1.0),
            "wireframe": bool(body.get("wireframe", holo.get("wireframe", False))),
            "pulse": bool(body.get("pulse", holo.get("pulse", True))),
            "label": str(body.get("label") or holo.get("label") or "ULTRON")[:80],
        })
        state["hologram"] = holo
        state.update({"mode": "hologram_lab", "title": holo["label"],
                      "subtitle": f"{kind.upper()} / LIVE", "progress": 100})
    elif op in {"hologram_update", "hologram_control"}:
        holo = dict(state.get("hologram") or {})
        if "kind" in body:
            kind = str(body.get("kind") or "").strip().lower()
            if kind in {"energy", "globe", "network", "drone", "vehicle", "logo", "sphere"}:
                holo["kind"] = kind
        if "color" in body: holo["color"] = str(body.get("color"))[:24]
        if "glow" in body: holo["glow"] = _stage_number(body.get("glow"), holo.get("glow", 1.0), 0.0, 3.0)
        if "speed" in body: holo["speed"] = _stage_number(body.get("speed"), holo.get("speed", 1.0), .05, 5.0)
        if "rings" in body: holo["rings"] = _stage_int(body.get("rings"), holo.get("rings", 4), 0, 12)
        if "particles" in body: holo["particles"] = _stage_int(body.get("particles"), holo.get("particles", 900), 0, 5000)
        if "scale" in body: holo["scale"] = _stage_number(body.get("scale"), holo.get("scale", 1.0), .25, 2.5)
        if "opacity" in body: holo["opacity"] = _stage_number(body.get("opacity"), holo.get("opacity", .92), .08, 1.0)
        if "wireframe" in body: holo["wireframe"] = bool(body.get("wireframe"))
        if "pulse" in body: holo["pulse"] = bool(body.get("pulse"))
        if "label" in body: holo["label"] = str(body.get("label"))[:80]
        state["hologram"] = holo
        state.update({"mode": "hologram_lab", "title": holo.get("label") or "HOLOGRAM",
                      "subtitle": f"{str(holo.get('kind','energy')).upper()} / LIVE"})
    elif op == "scene_load":
        raw = body.get("scene")
        if raw is None and body.get("scene_json"):
            try:
                raw = json.loads(str(body.get("scene_json")))
            except Exception:
                raw = None
        if not isinstance(raw, dict) or not isinstance(raw.get("objects"), list):
            return web.json_response({"ok": False, "error":"scene_invalid"}, status=400)
        allowed = {"energy","globe","network","drone","vehicle","logo","sphere","ring","tower","robot","arm","satellite","aircraft","building","ship","radar","portal","cube","custom"}
        loaded = _scene_defaults()
        objects = []
        used = set()
        for index,spec in enumerate(raw.get("objects")[:16]):
            if not isinstance(spec, dict):
                continue
            kind = str(spec.get("kind") or "energy").lower()
            if kind not in allowed: kind="energy"
            oid = re.sub(r"[^A-Za-z0-9_-]","",str(spec.get("id") or ""))[:24] or uuid.uuid4().hex[:8]
            if oid in used: oid=uuid.uuid4().hex[:8]
            used.add(oid)
            pos=list(spec.get("position") or [0,0,0]);rot=list(spec.get("rotation") or [0,0,0])
            while len(pos)<3:pos.append(0)
            while len(rot)<3:rot.append(0)
            motion=dict(spec.get("motion") or {})
            objects.append({
                "id":oid,"kind":kind,"label":str(spec.get("label") or f"{kind.upper()} {index+1}")[:60],
                "model_id":re.sub(r"[^A-Za-z0-9_-]","",str(spec.get("model_id") or ""))[:48] or None,
                "color":str(spec.get("color") or "#ff3047")[:24],
                "position":[_stage_number(pos[0],0,-6,6),_stage_number(pos[1],0,-4,4),_stage_number(pos[2],0,-6,6)],
                "rotation":[_stage_number(rot[0],0,-6.3,6.3),_stage_number(rot[1],0,-6.3,6.3),_stage_number(rot[2],0,-6.3,6.3)],
                "scale":_stage_number(spec.get("scale",1),1,.2,3),
                "opacity":_stage_number(spec.get("opacity",.9),.9,.08,1),
                "wireframe":bool(spec.get("wireframe",True)),"spin":_stage_number(spec.get("spin",.5),.5,-4,4),
                "explode":_stage_number(spec.get("explode",0),0,0,2),"visible":bool(spec.get("visible",True)),
                "locked":bool(spec.get("locked",False)),"clip_speed":_stage_number(spec.get("clip_speed",1),1,0,4),
                "clip_paused":bool(spec.get("clip_paused",False)),
                "parent_id":re.sub(r"[^A-Za-z0-9_-]","",str(spec.get("parent_id") or ""))[:24] or None,
                "physics":dict(spec.get("physics") or {"mode":"off","gravity":9.81,"velocity":[0,0,0],"bounce":.45,"floor":-1.3,"started_at":None}),
                "constraint":dict(spec.get("constraint") or {"type":"none","target_id":None,"distance":2.0,"speed":1.0,"offset":[0,0,0]}),
                "path":dict(spec.get("path") or {"points":[],"speed":1.0,"loop":True,"started_at":None}),
                "motion":{"type":str(motion.get("type") or "none"),"speed":_stage_number(motion.get("speed",1),1,.05,5),
                          "radius":_stage_number(motion.get("radius",1.5),1.5,.1,6),"amplitude":_stage_number(motion.get("amplitude",.5),.5,.05,4),
                          "axis":str(motion.get("axis") or "y")},
            })
        loaded["objects"]=objects
        selected=str(raw.get("selected_id") or "")
        loaded["selected_id"]=selected if any(o["id"]==selected for o in objects) else (objects[0]["id"] if objects else None)
        raw_selected = raw.get("selected_ids") if isinstance(raw.get("selected_ids"), list) else []
        loaded["selected_ids"] = [str(x) for x in raw_selected if str(x) in used][:16]
        if loaded["selected_id"] and loaded["selected_id"] not in loaded["selected_ids"]:
            loaded["selected_ids"].insert(0, loaded["selected_id"])
        focus=str(raw.get("focus_id") or "");loaded["focus_id"]=focus if any(o["id"]==focus for o in objects) else None
        target_id=str(raw.get("target_id") or "");loaded["target_id"]=target_id if any(o["id"]==target_id for o in objects) else None
        render_mode=str(raw.get("render_mode") or "hologram").lower();loaded["render_mode"]=render_mode if render_mode in {"hologram","blueprint","xray","solid","thermal"} else "hologram"
        loaded["camera"]=str(raw.get("camera") or "isometric") if str(raw.get("camera") or "isometric") in {"front","top","side","isometric","orbit","close","custom"} else "isometric"
        pose=raw.get("camera_pose")
        if isinstance(pose,dict):
            p=list(pose.get("position") or [6,4.2,7.2]);target=list(pose.get("target") or [0,0,0])
            while len(p)<3:p.append(0)
            while len(target)<3:target.append(0)
            loaded["camera_pose"]={"position":[_stage_number(p[0],6,-30,30),_stage_number(p[1],4.2,-30,30),_stage_number(p[2],7.2,-30,30)],
                                   "target":[_stage_number(target[0],0,-10,10),_stage_number(target[1],0,-10,10),_stage_number(target[2],0,-10,10)]}
        loaded["project_name"]=str(raw.get("project_name") or "Untitled")[:80]
        loaded["explode"]=_stage_number(raw.get("explode",0),0,0,2)
        loaded["auto_orbit"]=bool(raw.get("auto_orbit",True));loaded["grid"]=bool(raw.get("grid",True));loaded["show_labels"]=bool(raw.get("show_labels",True));loaded["show_trails"]=bool(raw.get("show_trails",True));loaded["audio_reactive"]=bool(raw.get("audio_reactive",True))
        loaded["theme"]=str(raw.get("theme") or "crimson") if str(raw.get("theme") or "crimson") in {"crimson","cyan","purple","amber","mono"} else "crimson"
        loaded["snap"]=_stage_number(raw.get("snap",.25),.25,0,2);loaded["animation"]=str(raw.get("animation") or "idle")
        links=[]
        for link in (raw.get("links") or [])[:64]:
            if not isinstance(link,dict): continue
            a,b=str(link.get("source") or ""),str(link.get("target") or "")
            if a in used and b in used and a!=b:
                links.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(link.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                              "source":a,"target":b,"label":str(link.get("label") or "")[:40],
                              "color":str(link.get("color") or "#35ffe4")[:24]})
        loaded["links"]=links
        hud=[]
        for card in (raw.get("hud") or [])[:32]:
            if not isinstance(card,dict): continue
            object_id=str(card.get("object_id") or "")
            if object_id and object_id not in used: continue
            hud.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(card.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                        "object_id":object_id or None,"title":str(card.get("title") or "DATA")[:40],
                        "value":str(card.get("value") or "")[:80],"unit":str(card.get("unit") or "")[:16],
                        "color":str(card.get("color") or "#35ffe4")[:24]})
        loaded["hud"]=hud
        groups=[]
        for group in (raw.get("groups") or [])[:16]:
            if not isinstance(group,dict): continue
            members=[str(x) for x in (group.get("members") or []) if str(x) in used]
            if members:
                groups.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(group.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                               "name":str(group.get("name") or "GROUP")[:60],"members":members[:16]})
        loaded["groups"]=groups
        bookmarks=[]
        for mark in (raw.get("camera_bookmarks") or [])[:12]:
            if not isinstance(mark,dict): continue
            pose=mark.get("pose")
            if not isinstance(pose,dict): continue
            p=list(pose.get("position") or [6,4.2,7.2]);target=list(pose.get("target") or [0,0,0])
            while len(p)<3:p.append(0)
            while len(target)<3:target.append(0)
            bookmarks.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(mark.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                              "name":str(mark.get("name") or "CAMERA")[:60],
                              "pose":{"position":[_stage_number(p[0],6,-30,30),_stage_number(p[1],4.2,-30,30),_stage_number(p[2],7.2,-30,30)],
                                      "target":[_stage_number(target[0],0,-10,10),_stage_number(target[1],0,-10,10),_stage_number(target[2],0,-10,10)]}})
        loaded["camera_bookmarks"]=bookmarks
        camera_track=[]
        for shot in (raw.get("camera_track") or [])[:64]:
            if not isinstance(shot,dict): continue
            p=list(shot.get("position") or [6,4.2,7.2]);target=list(shot.get("target") or [0,0,0])
            while len(p)<3:p.append(0)
            while len(target)<3:target.append(0)
            easing=str(shot.get("easing") or "ease_in_out")
            if easing not in {"linear","ease_in","ease_out","ease_in_out"}:easing="ease_in_out"
            camera_track.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(shot.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                                 "time":_stage_number(shot.get("time",0),0,0,60),
                                 "position":[_stage_number(p[0],6,-30,30),_stage_number(p[1],4.2,-30,30),_stage_number(p[2],7.2,-30,30)],
                                 "target":[_stage_number(target[0],0,-10,10),_stage_number(target[1],0,-10,10),_stage_number(target[2],0,-10,10)],
                                 "easing":easing})
        loaded["camera_track"]=sorted(camera_track,key=lambda x:float(x.get("time",0)))
        measurements=[]
        for m in (raw.get("measurements") or [])[:24]:
            if not isinstance(m,dict): continue
            a,b=str(m.get("source") or ""),str(m.get("target") or "")
            if a in used and b in used and a!=b:
                measurements.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(m.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                                     "source":a,"target":b,"label":str(m.get("label") or "DIST")[:40],
                                     "color":str(m.get("color") or "#ffd43b")[:24]})
        loaded["measurements"]=measurements
        rt=dict(raw.get("timeline") or {});duration=_stage_number(rt.get("duration",8),8,1,60);frames=[]
        for frame in (rt.get("keyframes") or [])[:128]:
            if not isinstance(frame,dict) or str(frame.get("object_id")) not in used: continue
            pos=list(frame.get("position") or [0,0,0]);rot=list(frame.get("rotation") or [0,0,0])
            while len(pos)<3:pos.append(0)
            while len(rot)<3:rot.append(0)
            frames.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(frame.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                           "time":_stage_number(frame.get("time",0),0,0,duration),"object_id":str(frame.get("object_id")),
                           "position":[_stage_number(pos[0],0,-6,6),_stage_number(pos[1],0,-4,4),_stage_number(pos[2],0,-6,6)],
                           "rotation":[_stage_number(rot[0],0,-6.3,6.3),_stage_number(rot[1],0,-6.3,6.3),_stage_number(rot[2],0,-6.3,6.3)],
                           "scale":_stage_number(frame.get("scale",1),1,.2,3),
                           "easing":str(frame.get("easing") or "ease_in_out") if str(frame.get("easing") or "ease_in_out") in {"linear","ease_in","ease_out","ease_in_out"} else "ease_in_out"})
        loaded["timeline"]={"duration":duration,"cursor":_stage_number(rt.get("cursor",0),0,0,duration),"playing":False,
                            "loop":bool(rt.get("loop",True)),"started_at":None,"keyframes":frames}
        rc=dict(raw.get("cinematic") or {});loaded["cinematic"]={"enabled":False,"preset":str(rc.get("preset") or "orbit"),
                            "duration":_stage_number(rc.get("duration",8),8,2,30),"started_at":None,"loop":bool(rc.get("loop",True))}
        raw_seq=dict(raw.get("sequence") or {});seq_steps=[]
        allowed_seq_ops={"scene_select","scene_target_lock","scene_target_clear","scene_render_mode","scene_animation",
                         "scene_cinematic","scene_camera","scene_focus","scene_physics","scene_path_play","scene_path_stop",
                         "scene_constraint","timeline_play","timeline_pause","scene_hud_add","scene_hud_clear"}
        for step in (raw_seq.get("steps") or [])[:64]:
            if not isinstance(step,dict): continue
            sop=str(step.get("operation") or "").lower()
            if sop not in allowed_seq_ops: continue
            args=step.get("args") if isinstance(step.get("args"),dict) else {}
            safe_args={str(k)[:40]:v for k,v in list(args.items())[:24] if isinstance(v,(str,int,float,bool)) or v is None}
            seq_steps.append({"id":re.sub(r"[^A-Za-z0-9_-]","",str(step.get("id") or ""))[:24] or uuid.uuid4().hex[:8],
                              "at":_stage_number(step.get("at",0),0,0,120),"operation":sop,
                              "args":safe_args,"label":str(step.get("label") or sop)[:60]})
        seq_steps.sort(key=lambda x:float(x.get("at",0)))
        loaded["sequence"]={"name":str(raw_seq.get("name") or "")[:80],"steps":seq_steps,"playing":False,
                            "loop":bool(raw_seq.get("loop",False)),"started_at":None,"run_id":0,
                            "duration":max([float(x.get("at",0)) for x in seq_steps],default=0.0)}
        state["scene"]=loaded
        state.update({"mode":"scene_lab","title":"SCENE LAB","subtitle":f"{len(objects)} OBJECTS / LOADED","progress":100})
    elif op == "scene_batch":
        scene = dict(state.get("scene") or {})
        raw = body.get("objects")
        if raw is None and body.get("objects_json"):
            try:
                raw = json.loads(str(body.get("objects_json")))
            except Exception:
                raw = None
        if not isinstance(raw, list) or not raw:
            return web.json_response({"ok": False, "error": "scene_objects_required"}, status=400)
        allowed = {"energy","globe","network","drone","vehicle","logo","sphere","ring","tower","robot","arm","satellite","aircraft","building","ship","radar","portal","cube","custom"}
        objects = []
        for index, spec in enumerate(raw[:16]):
            if not isinstance(spec, dict):
                continue
            kind = str(spec.get("kind") or "energy").lower()
            if kind not in allowed: kind = "energy"
            pos = spec.get("position") if isinstance(spec.get("position"), list) else [spec.get("x",0),spec.get("y",0),spec.get("z",0)]
            while len(pos)<3: pos.append(0)
            objects.append({
                "id": uuid.uuid4().hex[:8], "kind": kind,
                "label": str(spec.get("label") or f"{kind.upper()} {index+1}")[:60],
                "model_id": re.sub(r"[^A-Za-z0-9_-]","",str(spec.get("model_id") or ""))[:48] or None,
                "color": str(spec.get("color") or "#ff3047")[:24],
                "position": [_stage_number(pos[0],0,-6,6),_stage_number(pos[1],0,-4,4),_stage_number(pos[2],0,-6,6)],
                "rotation": [0.0,0.0,0.0],
                "scale": _stage_number(spec.get("scale",1),1,.2,3),
                "opacity": _stage_number(spec.get("opacity",.9),.9,.08,1),
                "wireframe": bool(spec.get("wireframe",True)),
                "spin": _stage_number(spec.get("spin",.5),.5,-4,4),
                "explode": _stage_number(spec.get("explode",0),0,0,2),
                "visible": bool(spec.get("visible", True)),
                "locked": bool(spec.get("locked", False)),
                "clip_speed": _stage_number(spec.get("clip_speed",1),1,0,4),
                "clip_paused": bool(spec.get("clip_paused",False)),
                "parent_id": re.sub(r"[^A-Za-z0-9_-]","",str(spec.get("parent_id") or ""))[:24] or None,
                "physics": {"mode":"off","gravity":9.81,"velocity":[0.0,0.0,0.0],"bounce":.45,"floor":-1.3,"started_at":None},
                "constraint": {"type":"none","target_id":None,"distance":2.0,"speed":1.0,"offset":[0.0,0.0,0.0]},
                "path": {"points":[],"speed":1.0,"loop":True,"started_at":None},
                "motion": {
                    "type": str(spec.get("motion") or "none"),
                    "speed": _stage_number(spec.get("motion_speed",1),1,.05,5),
                    "radius": _stage_number(spec.get("radius",1.5),1.5,.1,6),
                    "amplitude": _stage_number(spec.get("amplitude",.5),.5,.05,4),
                    "axis": str(spec.get("axis") or "y"),
                },
            })
        if not objects:
            return web.json_response({"ok": False, "error": "scene_objects_invalid"}, status=400)
        scene.update({"objects":objects,"selected_id":objects[0]["id"],"selected_ids":[objects[0]["id"]],
                      "camera":str(body.get("camera") or "isometric"),
                      "auto_orbit":bool(body.get("auto_orbit",True)),
                      "grid":bool(body.get("grid",True)),
                      "animation":str(body.get("animation") or "idle")})
        state["scene"] = scene
        state.update({"mode":"scene_lab","title":"SCENE LAB",
                      "subtitle":f"{len(objects)} OBJECTS / LIVE","progress":100})
    elif op in {"scene_open", "scene_add"}:
        scene = dict(state.get("scene") or {})
        objects = list(scene.get("objects") or [])
        if op == "scene_open":
            state.update({"mode": "scene_lab", "title": "SCENE LAB",
                          "subtitle": f"{len(objects)} OBJECTS / LIVE", "progress": 100})
        else:
            if len(objects) >= 16:
                return web.json_response({"ok": False, "error": "scene_object_limit"}, status=409)
            allowed = {"energy", "globe", "network", "drone", "vehicle", "logo", "sphere", "ring", "tower",
                       "robot", "arm", "satellite", "aircraft", "building", "ship", "radar", "portal", "cube", "custom"}
            kind = str(body.get("kind") or "energy").strip().lower()
            if kind not in allowed:
                kind = "energy"
            oid = uuid.uuid4().hex[:8]
            pos = body.get("position") if isinstance(body.get("position"), list) else [
                _stage_number(body.get("x", 0), 0, -6, 6),
                _stage_number(body.get("y", 0), 0, -4, 4),
                _stage_number(body.get("z", 0), 0, -6, 6),
            ]
            while len(pos) < 3: pos.append(0)
            obj = {
                "id": oid,
                "kind": kind,
                "label": str(body.get("label") or kind.upper())[:60],
                "model_id": re.sub(r"[^A-Za-z0-9_-]","",str(body.get("model_id") or ""))[:48] or None,
                "color": str(body.get("color") or "#ff3047")[:24],
                "position": [_stage_number(pos[0], 0, -6, 6), _stage_number(pos[1], 0, -4, 4), _stage_number(pos[2], 0, -6, 6)],
                "rotation": [0.0, 0.0, 0.0],
                "scale": _stage_number(body.get("scale", 1), 1, .2, 3),
                "opacity": _stage_number(body.get("opacity", .9), .9, .08, 1),
                "wireframe": bool(body.get("wireframe", True)),
                "spin": _stage_number(body.get("spin", .5), .5, -4, 4),
                "explode": _stage_number(body.get("explode", 0), 0, 0, 2),
                "visible": bool(body.get("visible", True)),
                "locked": bool(body.get("locked", False)),
                "clip_speed": _stage_number(body.get("clip_speed",1),1,0,4),
                "clip_paused": bool(body.get("clip_paused",False)),
                "parent_id": re.sub(r"[^A-Za-z0-9_-]","",str(body.get("parent_id") or ""))[:24] or None,
                "physics": {"mode":"off","gravity":9.81,"velocity":[0.0,0.0,0.0],"bounce":.45,"floor":-1.3,"started_at":None},
                "constraint": {"type":"none","target_id":None,"distance":2.0,"speed":1.0,"offset":[0.0,0.0,0.0]},
                "path": {"points":[],"speed":1.0,"loop":True,"started_at":None},
                "motion": {
                    "type": str(body.get("motion") or "none"),
                    "speed": _stage_number(body.get("motion_speed",1),1,.05,5),
                    "radius": _stage_number(body.get("radius",1.5),1.5,.1,6),
                    "amplitude": _stage_number(body.get("amplitude",.5),.5,.05,4),
                    "axis": str(body.get("axis") or "y"),
                },
            }
            objects.append(obj)
            scene.update({"objects": objects, "selected_id": oid, "selected_ids": [oid]})
            state["scene"] = scene
            state.update({"mode": "scene_lab", "title": "SCENE LAB",
                          "subtitle": f"{len(objects)} OBJECTS / LIVE", "progress": 100})
    elif op in {"scene_update", "scene_move", "scene_rotate", "scene_scale",
                "scene_color", "scene_explode"}:
        scene = dict(state.get("scene") or {})
        objects = list(scene.get("objects") or [])
        target = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"), scene.get("selected_id"))
        changed = False
        for i, item in enumerate(objects):
            if str(item.get("id")) != target:
                continue
            obj = dict(item)
            if "kind" in body and str(body["kind"]).lower() in {"energy","globe","network","drone","vehicle","logo","sphere","ring","tower","robot","arm","satellite","aircraft","building","ship","radar","portal","cube","custom"}:
                obj["kind"] = str(body["kind"]).lower()
            if "label" in body: obj["label"] = str(body["label"])[:60]
            if "model_id" in body: obj["model_id"] = re.sub(r"[^A-Za-z0-9_-]","",str(body["model_id"]))[:48] or None
            if "color" in body: obj["color"] = str(body["color"])[:24]
            if "scale" in body: obj["scale"] = _stage_number(body["scale"], obj.get("scale",1), .2, 3)
            if "opacity" in body: obj["opacity"] = _stage_number(body["opacity"], obj.get("opacity",.9), .08, 1)
            if "wireframe" in body: obj["wireframe"] = bool(body["wireframe"])
            if "spin" in body: obj["spin"] = _stage_number(body["spin"], obj.get("spin",.5), -4, 4)
            if "explode" in body: obj["explode"] = _stage_number(body["explode"], obj.get("explode",0), 0, 2)
            if "visible" in body: obj["visible"] = bool(body["visible"])
            if "locked" in body: obj["locked"] = bool(body["locked"])
            if "clip_speed" in body: obj["clip_speed"] = _stage_number(body["clip_speed"], obj.get("clip_speed",1), 0, 4)
            if "clip_paused" in body: obj["clip_paused"] = bool(body["clip_paused"])
            if any(k in body for k in ("motion","motion_speed","radius","amplitude","axis")):
                motion = dict(obj.get("motion") or {})
                if "motion" in body: motion["type"] = str(body["motion"]).lower()
                if "motion_speed" in body: motion["speed"] = _stage_number(body["motion_speed"], motion.get("speed",1), .05, 5)
                if "radius" in body: motion["radius"] = _stage_number(body["radius"], motion.get("radius",1.5), .1, 6)
                if "amplitude" in body: motion["amplitude"] = _stage_number(body["amplitude"], motion.get("amplitude",.5), .05, 4)
                if "axis" in body: motion["axis"] = str(body["axis"]).lower()
                obj["motion"] = motion
            pos = list(obj.get("position") or [0,0,0])
            rot = list(obj.get("rotation") or [0,0,0])
            while len(pos)<3: pos.append(0)
            while len(rot)<3: rot.append(0)
            if "x" in body: pos[0] = _stage_number(body["x"], pos[0], -6, 6)
            if "y" in body: pos[1] = _stage_number(body["y"], pos[1], -4, 4)
            if "z" in body: pos[2] = _stage_number(body["z"], pos[2], -6, 6)
            if "rx" in body: rot[0] = _stage_number(body["rx"], rot[0], -6.3, 6.3)
            if "ry" in body: rot[1] = _stage_number(body["ry"], rot[1], -6.3, 6.3)
            if "rz" in body: rot[2] = _stage_number(body["rz"], rot[2], -6.3, 6.3)
            obj["position"], obj["rotation"] = pos, rot
            objects[i] = obj
            changed = True
            break
        if not changed:
            return web.json_response({"ok": False, "error": "scene_object_not_found"}, status=404)
        scene["objects"] = objects
        state["scene"] = scene
        state.update({"mode":"scene_lab","title":"SCENE LAB",
                      "subtitle":f"{len(objects)} OBJECTS / LIVE"})
    elif op == "scene_select":
        scene = dict(state.get("scene") or {})
        target = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"))
        if not any(str(o.get("id")) == target for o in scene.get("objects") or []):
            return web.json_response({"ok": False, "error": "scene_object_not_found"}, status=404)
        scene["selected_id"] = target
        scene["selected_ids"] = [target]
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_multi_select":
        scene = dict(state.get("scene") or {})
        ids = body.get("object_ids")
        if ids is None and body.get("object_ids_json"):
            try: ids = json.loads(str(body.get("object_ids_json")))
            except Exception: ids = None
        if not isinstance(ids, list):
            one = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"))
            ids = [one] if one else []
        valid = {str(o.get("id")) for o in scene.get("objects") or []}
        incoming = [str(x) for x in ids if str(x) in valid]
        mode = str(body.get("selection_mode") or "replace").lower()
        current = [str(x) for x in scene.get("selected_ids") or [] if str(x) in valid]
        if mode == "add":
            selected = current + [x for x in incoming if x not in current]
        elif mode == "toggle":
            selected = list(current)
            for x in incoming:
                if x in selected: selected.remove(x)
                else: selected.append(x)
        elif mode == "all":
            selected = [str(o.get("id")) for o in scene.get("objects") or []]
        elif mode == "clear":
            selected = []
        else:
            selected = incoming
        scene["selected_ids"] = selected[:16]
        scene["selected_id"] = scene["selected_ids"][-1] if scene["selected_ids"] else None
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_group_create":
        scene = dict(state.get("scene") or {})
        ids = body.get("object_ids")
        if ids is None and body.get("object_ids_json"):
            try: ids = json.loads(str(body.get("object_ids_json")))
            except Exception: ids = None
        valid = {str(o.get("id")) for o in scene.get("objects") or []}
        members = [str(x) for x in (ids if isinstance(ids,list) else scene.get("selected_ids") or []) if str(x) in valid]
        if len(members) < 2:
            return web.json_response({"ok":False,"error":"group_requires_two_objects"},status=400)
        groups = list(scene.get("groups") or [])
        gid = uuid.uuid4().hex[:8]
        groups.append({"id":gid,"name":str(body.get("group_name") or body.get("label") or f"GROUP {len(groups)+1}")[:60],
                       "members":members[:16]})
        scene["groups"] = groups[:16]
        scene["selected_ids"] = members[:16]
        scene["selected_id"] = members[-1]
        state["scene"] = scene
        state["mode"] = "scene_lab"
        state["group_result"] = groups[-1]
    elif op == "scene_group_select":
        scene = dict(state.get("scene") or {})
        groups = list(scene.get("groups") or [])
        raw = str(body.get("group_id") or body.get("group_name") or body.get("label") or "").strip()
        group = next((g for g in groups if str(g.get("id")) == raw or str(g.get("name") or "").lower() == raw.lower()), None)
        if group is None and raw:
            group = next((g for g in groups if raw.lower() in str(g.get("name") or "").lower()), None)
        if not group:
            return web.json_response({"ok":False,"error":"scene_group_not_found"},status=404)
        valid = {str(o.get("id")) for o in scene.get("objects") or []}
        members = [str(x) for x in group.get("members") or [] if str(x) in valid]
        scene["selected_ids"] = members
        scene["selected_id"] = members[-1] if members else None
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_group_delete":
        scene = dict(state.get("scene") or {})
        raw = str(body.get("group_id") or body.get("group_name") or body.get("label") or "").strip()
        scene["groups"] = [g for g in (scene.get("groups") or []) if str(g.get("id")) != raw and str(g.get("name") or "").lower() != raw.lower()]
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_batch_transform":
        scene = dict(state.get("scene") or {})
        valid = {str(o.get("id")) for o in scene.get("objects") or []}
        ids = body.get("object_ids")
        if ids is None and body.get("object_ids_json"):
            try: ids = json.loads(str(body.get("object_ids_json")))
            except Exception: ids = None
        targets = [str(x) for x in (ids if isinstance(ids,list) else scene.get("selected_ids") or []) if str(x) in valid]
        if not targets and scene.get("selected_id"): targets=[str(scene.get("selected_id"))]
        if not targets:
            return web.json_response({"ok":False,"error":"scene_selection_empty"},status=400)
        dx=_stage_number(body.get("dx",0),0,-12,12);dy=_stage_number(body.get("dy",0),0,-8,8);dz=_stage_number(body.get("dz",0),0,-12,12)
        drx=_stage_number(body.get("drx",0),0,-6.3,6.3);dry=_stage_number(body.get("dry",0),0,-6.3,6.3);drz=_stage_number(body.get("drz",0),0,-6.3,6.3)
        factor=_stage_number(body.get("scale_factor",1),1,.1,10)
        objects=[]
        for item in scene.get("objects") or []:
            obj=dict(item)
            if str(obj.get("id")) in targets and not bool(obj.get("locked",False)):
                pos=list(obj.get("position") or [0,0,0]);rot=list(obj.get("rotation") or [0,0,0])
                while len(pos)<3:pos.append(0)
                while len(rot)<3:rot.append(0)
                obj["position"]=[_stage_number(pos[0]+dx,0,-6,6),_stage_number(pos[1]+dy,0,-4,4),_stage_number(pos[2]+dz,0,-6,6)]
                obj["rotation"]=[_stage_number(rot[0]+drx,0,-6.3,6.3),_stage_number(rot[1]+dry,0,-6.3,6.3),_stage_number(rot[2]+drz,0,-6.3,6.3)]
                obj["scale"]=_stage_number(float(obj.get("scale",1))*factor,1,.2,3)
                if "color" in body: obj["color"]=str(body.get("color") or "#ff3047")[:24]
                if "visible" in body: obj["visible"]=bool(body["visible"])
                if "wireframe" in body: obj["wireframe"]=bool(body["wireframe"])
            objects.append(obj)
        scene["objects"]=objects
        scene["selected_ids"]=targets[:16]
        scene["selected_id"]=targets[-1]
        state["scene"]=scene
        state["mode"]="scene_lab"
    elif op == "scene_align":
        scene = dict(state.get("scene") or {})
        selected = [str(x) for x in scene.get("selected_ids") or []]
        objects=[dict(o) for o in scene.get("objects") or []]
        chosen=[o for o in objects if str(o.get("id")) in selected]
        if len(chosen)<2:
            return web.json_response({"ok":False,"error":"align_requires_two_objects"},status=400)
        axis=str(body.get("axis") or "x").lower()
        idx={"x":0,"y":1,"z":2}.get(axis,0)
        values=[float((o.get("position") or [0,0,0])[idx]) for o in chosen]
        mode=str(body.get("align") or "center").lower()
        target=min(values) if mode=="min" else max(values) if mode=="max" else sum(values)/len(values)
        for obj in objects:
            if str(obj.get("id")) in selected and not bool(obj.get("locked",False)):
                pos=list(obj.get("position") or [0,0,0])
                while len(pos)<3:pos.append(0)
                pos[idx]=target;obj["position"]=pos
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_distribute":
        scene=dict(state.get("scene") or {});selected=[str(x) for x in scene.get("selected_ids") or []]
        objects=[dict(o) for o in scene.get("objects") or []];axis=str(body.get("axis") or "x").lower();idx={"x":0,"y":1,"z":2}.get(axis,0)
        chosen=[o for o in objects if str(o.get("id")) in selected]
        if len(chosen)<3:return web.json_response({"ok":False,"error":"distribute_requires_three_objects"},status=400)
        chosen.sort(key=lambda o:float((o.get("position") or [0,0,0])[idx]));lo=float((chosen[0].get("position") or [0,0,0])[idx]);hi=float((chosen[-1].get("position") or [0,0,0])[idx]);step=(hi-lo)/(len(chosen)-1)
        byid={str(o.get("id")):lo+i*step for i,o in enumerate(chosen)}
        for obj in objects:
            oid=str(obj.get("id"))
            if oid in byid and not bool(obj.get("locked",False)):
                pos=list(obj.get("position") or [0,0,0])
                while len(pos)<3:pos.append(0)
                pos[idx]=byid[oid];obj["position"]=pos
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_array":
        scene=dict(state.get("scene") or {});objects=list(scene.get("objects") or [])
        target=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"))
        src=next((copy.deepcopy(o) for o in objects if str(o.get("id"))==target),None)
        if not src:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        count=_stage_int(body.get("count",4),4,2,12);available=max(0,16-len(objects));count=min(count,available+1)
        if count<=1:return web.json_response({"ok":False,"error":"scene_object_limit"},status=409)
        pattern=str(body.get("layout") or "line").lower();spacing=_stage_number(body.get("spacing",1.2),1.2,.2,6);radius=_stage_number(body.get("radius",2.4),2.4,.5,6)
        base=list(src.get("position") or [0,0,0]);created=[target]
        for i in range(1,count):
            clone=copy.deepcopy(src);clone["id"]=uuid.uuid4().hex[:8];clone["label"]=(str(src.get("label") or src.get("kind") or "OBJECT")+f" {i+1}")[:60]
            if pattern in {"radial","orbit","circle"}:
                angle=(i/count)*math.pi*2;clone["position"]=[_stage_number(base[0]+math.cos(angle)*radius,0,-6,6),base[1],_stage_number(base[2]+math.sin(angle)*radius,0,-6,6)]
            elif pattern=="grid":
                cols=max(2,int(math.ceil(math.sqrt(count))));clone["position"]=[_stage_number(base[0]+(i%cols)*spacing,0,-6,6),base[1],_stage_number(base[2]+(i//cols)*spacing,0,-6,6)]
            else:
                clone["position"]=[_stage_number(base[0]+i*spacing,0,-6,6),base[1],base[2]]
            objects.append(clone);created.append(clone["id"])
        scene["objects"]=objects;scene["selected_ids"]=created;scene["selected_id"]=created[-1]
        state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_parent":
        scene=dict(state.get("scene") or {});objects=[dict(o) for o in scene.get("objects") or []]
        child=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"))
        parent=_scene_resolve_object(scene,body.get("parent_id"),body.get("parent_label"))
        if not child or not parent or child==parent:return web.json_response({"ok":False,"error":"invalid_parent"},status=400)
        byid={str(o.get("id")):o for o in objects}
        if child not in byid or parent not in byid:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        cursor=parent;seen=set()
        while cursor and cursor not in seen:
            if cursor==child:return web.json_response({"ok":False,"error":"parent_cycle"},status=400)
            seen.add(cursor);cursor=str(byid.get(cursor,{}).get("parent_id") or "")
        child_obj=byid[child];parent_obj=byid[parent]
        cp=list(child_obj.get("position") or [0,0,0]);pp=list(parent_obj.get("position") or [0,0,0])
        cr=list(child_obj.get("rotation") or [0,0,0]);pr=list(parent_obj.get("rotation") or [0,0,0])
        while len(cp)<3:cp.append(0)
        while len(pp)<3:pp.append(0)
        while len(cr)<3:cr.append(0)
        while len(pr)<3:pr.append(0)
        ps=max(.001,float(parent_obj.get("scale",1)))
        child_obj["position"]=[(cp[0]-pp[0])/ps,(cp[1]-pp[1])/ps,(cp[2]-pp[2])/ps]
        child_obj["rotation"]=[cr[0]-pr[0],cr[1]-pr[1],cr[2]-pr[2]]
        child_obj["scale"]=_stage_number(float(child_obj.get("scale",1))/ps,1,.2,3)
        child_obj["parent_id"]=parent
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_unparent":
        scene=dict(state.get("scene") or {});objects=[dict(o) for o in scene.get("objects") or []]
        child=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"))
        byid={str(o.get("id")):o for o in objects};found=False
        for obj in objects:
            if str(obj.get("id"))!=child:continue
            parent_id=str(obj.get("parent_id") or "");parent_obj=byid.get(parent_id)
            if parent_obj:
                cp=list(obj.get("position") or [0,0,0]);pp=list(parent_obj.get("position") or [0,0,0])
                cr=list(obj.get("rotation") or [0,0,0]);pr=list(parent_obj.get("rotation") or [0,0,0])
                while len(cp)<3:cp.append(0)
                while len(pp)<3:pp.append(0)
                while len(cr)<3:cr.append(0)
                while len(pr)<3:pr.append(0)
                ps=float(parent_obj.get("scale",1))
                obj["position"]=[pp[0]+cp[0]*ps,pp[1]+cp[1]*ps,pp[2]+cp[2]*ps]
                obj["rotation"]=[pr[0]+cr[0],pr[1]+cr[1],pr[2]+cr[2]]
                obj["scale"]=_stage_number(float(obj.get("scale",1))*ps,1,.2,3)
            obj["parent_id"]=None;found=True;break
        if not found:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_camera_bookmark_save":
        scene=dict(state.get("scene") or {});pose=body.get("pose")
        if pose is None and body.get("position_json") and body.get("target_json"):
            try:pose={"position":json.loads(str(body["position_json"])),"target":json.loads(str(body["target_json"]))}
            except Exception:pose=None
        if pose is None:pose=scene.get("camera_pose")
        if not isinstance(pose,dict):
            preset=str(scene.get("camera") or "isometric")
            positions={"front":[0,1.2,9],"top":[0,9,.01],"side":[9,1.2,0],"close":[0,.8,5.2],"orbit":[6,4.2,7.2],"isometric":[6,4.2,7.2]}
            pose={"position":positions.get(preset,[6,4.2,7.2]),"target":[0,0,0]}
        p=list(pose.get("position") or [6,4.2,7.2]);target=list(pose.get("target") or [0,0,0])
        while len(p)<3:p.append(0)
        while len(target)<3:target.append(0)
        bookmark={"id":uuid.uuid4().hex[:8],"name":str(body.get("bookmark_name") or body.get("label") or "CAMERA")[:60],
                  "pose":{"position":[_stage_number(p[0],6,-30,30),_stage_number(p[1],4.2,-30,30),_stage_number(p[2],7.2,-30,30)],
                          "target":[_stage_number(target[0],0,-10,10),_stage_number(target[1],0,-10,10),_stage_number(target[2],0,-10,10)]}}
        marks=list(scene.get("camera_bookmarks") or []);marks.append(bookmark);scene["camera_bookmarks"]=marks[-12:]
        state["scene"]=scene;state["mode"]="scene_lab";state["bookmark_result"]=bookmark
    elif op == "scene_camera_bookmark_load":
        scene=dict(state.get("scene") or {});raw=str(body.get("bookmark_id") or body.get("bookmark_name") or body.get("label") or "")
        mark=next((b for b in scene.get("camera_bookmarks") or [] if str(b.get("id"))==raw or str(b.get("name") or "").lower()==raw.lower()),None)
        if not mark:return web.json_response({"ok":False,"error":"camera_bookmark_not_found"},status=404)
        scene["camera"]="custom";scene["auto_orbit"]=False;scene["camera_pose"]=copy.deepcopy(mark.get("pose"));state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_camera_bookmark_delete":
        scene=dict(state.get("scene") or {});raw=str(body.get("bookmark_id") or body.get("bookmark_name") or body.get("label") or "")
        scene["camera_bookmarks"]=[b for b in scene.get("camera_bookmarks") or [] if str(b.get("id"))!=raw and str(b.get("name") or "").lower()!=raw.lower()]
        state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_camera_bookmark_list":
        scene=dict(state.get("scene") or {});state["bookmark_result"]={"bookmarks":scene.get("camera_bookmarks") or []};state["mode"]="scene_lab"
    elif op == "scene_remove":
        scene = dict(state.get("scene") or {})
        target = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"), scene.get("selected_id"))
        objects = [o for o in (scene.get("objects") or []) if str(o.get("id")) != target]
        scene["objects"] = objects
        scene["links"] = [l for l in (scene.get("links") or []) if target not in {str(l.get("source")),str(l.get("target"))}]
        scene["measurements"] = [m for m in (scene.get("measurements") or []) if target not in {str(m.get("source")),str(m.get("target"))}]
        scene["selected_ids"] = [str(x) for x in scene.get("selected_ids") or [] if str(x) != target]
        scene["selected_id"] = scene["selected_ids"][-1] if scene["selected_ids"] else (str(objects[-1].get("id")) if objects else None)
        clean_groups=[]
        for group in scene.get("groups") or []:
            g=dict(group);g["members"]=[str(x) for x in g.get("members") or [] if str(x)!=target]
            if g["members"]:clean_groups.append(g)
        scene["groups"]=clean_groups
        for obj in objects:
            if str(obj.get("parent_id") or "")==target: obj["parent_id"]=None
            constraint=dict(obj.get("constraint") or {})
            if str(constraint.get("target_id") or "")==target:
                obj["constraint"]={"type":"none","target_id":None,"distance":2.0,"speed":1.0,"offset":[0,0,0]}
        if str(scene.get("focus_id") or "") == target: scene["focus_id"] = None
        if str(scene.get("target_id") or "") == target: scene["target_id"] = None
        state["scene"] = scene
        state.update({"mode":"scene_lab","title":"SCENE LAB",
                      "subtitle":f"{len(objects)} OBJECTS / LIVE"})
    elif op == "scene_clear":
        state["scene"] = _scene_defaults()
        state.update({"mode":"scene_lab","title":"SCENE LAB","subtitle":"0 OBJECTS / LIVE"})
    elif op == "scene_camera":
        scene = dict(state.get("scene") or {})
        camera = str(body.get("camera") or "isometric").lower()
        if camera not in {"front","top","side","isometric","orbit","close","custom"}:
            camera = "isometric"
        scene["camera"] = camera
        if camera != "custom":
            scene["camera_pose"] = None
        if "auto_orbit" in body: scene["auto_orbit"] = bool(body["auto_orbit"])
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_arrange":
        scene = dict(state.get("scene") or {})
        objects = [dict(o) for o in (scene.get("objects") or [])]
        layout = str(body.get("layout") or "orbit").lower()
        n = max(1, len(objects))
        for i, obj in enumerate(objects):
            if layout == "line":
                obj["position"] = [(i-(n-1)/2)*2.0, 0, 0]
            elif layout == "grid":
                cols = max(1, int(n ** .5 + .999))
                obj["position"] = [((i%cols)-(cols-1)/2)*2.0, 0, ((i//cols)-((n-1)//cols)/2)*1.8]
            else:
                angle = (i / n) * 6.28318530718
                radius = 2.6 if n > 1 else 0
                obj["position"] = [math.cos(angle)*radius, 0, math.sin(angle)*radius]
            objects[i] = obj
        scene["objects"] = objects
        state["scene"] = scene
        state.update({"mode":"scene_lab","title":"SCENE LAB",
                      "subtitle":f"{len(objects)} OBJECTS / {layout.upper()}"})
    elif op == "scene_preset":
        scene = dict(state.get("scene") or {})
        preset = str(body.get("preset") or "operations").lower()
        presets = {
            "operations": [
                ("globe","EARTH","#35ffe4",0,0,0,1.15),
                ("network","NETWORK","#ff3047",-2.7,.2,0,.75),
                ("energy","CORE","#ff3047",2.7,.2,0,.75),
            ],
            "vehicle_scan": [
                ("vehicle","VEHICLE","#ff3047",0,0,0,1.25),
                ("ring","SCAN A","#35ffe4",0,0,0,1.55),
                ("ring","SCAN B","#ff3047",0,0,0,1.95),
            ],
            "drone_bay": [
                ("drone","DRONE 01","#ff3047",-2,0,0,.8),
                ("drone","DRONE 02","#35ffe4",0,0,0,.8),
                ("drone","DRONE 03","#ff3047",2,0,0,.8),
            ],
            "planetary": [
                ("globe","EARTH","#35ffe4",0,0,0,1.1),
                ("sphere","MOON","#dbe6ff",2.7,.4,0,.35),
                ("ring","ORBIT","#ff3047",0,0,0,1.7),
            ],
            "command_center": [
                ("energy","CORE","#ff3047",0,0,0,1.0),
                ("network","NETWORK","#35ffe4",-2.5,.3,0,.75),
                ("radar","RADAR","#ff3047",2.5,.1,0,.75),
                ("drone","DRONE A","#35ffe4",-1.7,.7,-2,.55),
                ("drone","DRONE B","#ff3047",1.7,.7,-2,.55),
            ],
            "city_scan": [
                ("building","TOWER A","#ff3047",-2.4,0,0,.8),
                ("building","TOWER B","#35ffe4",0,0,-.8,1.15),
                ("building","TOWER C","#ff3047",2.4,0,.2,.7),
                ("vehicle","VEHICLE","#dbe6ff",0,-.8,2,.55),
                ("drone","SCAN DRONE","#35ffe4",0,1.5,0,.5),
            ],
            "space_ops": [
                ("globe","PLANET","#35ffe4",0,0,0,1.1),
                ("satellite","SAT-01","#ff3047",-2.8,.8,0,.55),
                ("ship","SHIP","#dbe6ff",2.8,.2,0,.7),
                ("ring","ORBIT","#ff3047",0,0,0,1.9),
            ],
            "robotics": [
                ("robot","ROBOT","#ff3047",0,0,0,.9),
                ("arm","ARM L","#35ffe4",-2.4,0,0,.75),
                ("arm","ARM R","#35ffe4",2.4,0,0,.75),
                ("network","CONTROL","#ff3047",0,1.6,-1,.5),
            ],
        }
        spec = presets.get(preset, presets["operations"])
        objects = []
        for kind,label,color,x,y,z,scale in spec:
            objects.append({"id":uuid.uuid4().hex[:8],"kind":kind,"label":label,"color":color,
                            "position":[x,y,z],"rotation":[0,0,0],"scale":scale,"opacity":.9,
                            "wireframe":True,"spin":.45,"explode":0.0,
                            "visible":True,"locked":False,"clip_speed":1.0,"clip_paused":False,
                            "motion":{"type":"none","speed":1.0,"radius":1.5,"amplitude":.5,"axis":"y"}})
        scene = _scene_ensure(scene)
        scene.update({"objects":objects,"selected_id":objects[0]["id"] if objects else None,
                      "selected_ids":[objects[0]["id"]] if objects else [],
                      "groups":[],"camera":"isometric","auto_orbit":True,"grid":True,"animation":"idle"})
        state["scene"] = scene
        state.update({"mode":"scene_lab","title":"SCENE LAB",
                      "subtitle":f"{preset.upper()} / {len(objects)} OBJECTS","progress":100})
    elif op == "scene_link":
        scene = dict(state.get("scene") or {})
        links = list(scene.get("links") or [])
        objects = list(scene.get("objects") or [])
        def _resolve(value, fallback=""):
            raw = str(value or "").strip()
            if not raw: return str(fallback or "")
            exact = next((str(o.get("id")) for o in objects if str(o.get("id")) == raw or str(o.get("label") or "").lower() == raw.lower()), None)
            if exact: return exact
            partial = next((str(o.get("id")) for o in objects if raw.lower() in str(o.get("label") or "").lower()), None)
            return partial or raw
        source = _resolve(body.get("source_id") or body.get("source_label"), scene.get("selected_id"))
        target = _resolve(body.get("target_id") or body.get("target_label"))
        ids = {str(o.get("id")) for o in objects}
        if source not in ids or target not in ids or source == target:
            return web.json_response({"ok":False,"error":"invalid_scene_link"}, status=400)
        if not any({str(l.get("source")),str(l.get("target"))} == {source,target} for l in links):
            links.append({"id":uuid.uuid4().hex[:8],"source":source,"target":target,
                          "label":str(body.get("label") or "")[:40],
                          "color":str(body.get("color") or "#35ffe4")[:24]})
        scene["links"]=links[:64]
        state["scene"]=scene
        state["mode"]="scene_lab"
    elif op == "scene_clear_links":
        scene = dict(state.get("scene") or {})
        scene["links"] = []
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_unlink":
        scene = dict(state.get("scene") or {})
        link_id = str(body.get("link_id") or "")
        if link_id:
            scene["links"]=[l for l in (scene.get("links") or []) if str(l.get("id")) != link_id]
        else:
            target=str(body.get("object_id") or scene.get("selected_id") or "")
            scene["links"]=[l for l in (scene.get("links") or []) if target not in {str(l.get("source")),str(l.get("target"))}]
        state["scene"]=scene
        state["mode"]="scene_lab"
    elif op == "scene_auto_link":
        scene = dict(state.get("scene") or {})
        objects=list(scene.get("objects") or [])
        mode=str(body.get("layout") or "star").lower()
        links=[]
        if len(objects)>1:
            if mode=="chain":
                pairs=[(objects[i],objects[i+1]) for i in range(len(objects)-1)]
            else:
                center=next((o for o in objects if str(o.get("id"))==str(scene.get("selected_id") or "")),objects[0])
                pairs=[(center,o) for o in objects if o is not center]
            for a,b in pairs:
                links.append({"id":uuid.uuid4().hex[:8],"source":a["id"],"target":b["id"],
                              "label":"","color":str(body.get("color") or "#35ffe4")[:24]})
        scene["links"]=links[:64]
        state["scene"]=scene
        state["mode"]="scene_lab"
    elif op == "scene_camera_pose":
        scene = dict(state.get("scene") or {})
        position = body.get("position")
        target = body.get("target")
        if position is None and body.get("position_json"):
            try: position = json.loads(str(body.get("position_json")))
            except Exception: position = None
        if target is None and body.get("target_json"):
            try: target = json.loads(str(body.get("target_json")))
            except Exception: target = None
        if not isinstance(position,list) or not isinstance(target,list):
            return web.json_response({"ok":False,"error":"camera_pose_required"}, status=400)
        while len(position)<3: position.append(0)
        while len(target)<3: target.append(0)
        scene["camera"]="custom"
        scene["auto_orbit"]=False
        scene["camera_pose"]={
            "position":[_stage_number(position[0],6,-30,30),_stage_number(position[1],4.2,-30,30),_stage_number(position[2],7.2,-30,30)],
            "target":[_stage_number(target[0],0,-10,10),_stage_number(target[1],0,-10,10),_stage_number(target[2],0,-10,10)],
        }
        state["scene"]=scene
        state["mode"]="scene_lab"
    elif op == "scene_hud_add":
        scene = dict(state.get("scene") or {})
        hud=list(scene.get("hud") or [])
        object_id=str(body.get("object_id") or scene.get("selected_id") or "")
        ids={str(o.get("id")) for o in scene.get("objects") or []}
        if object_id and object_id not in ids:
            return web.json_response({"ok":False,"error":"scene_object_not_found"}, status=404)
        card={"id":uuid.uuid4().hex[:8],"object_id":object_id or None,
              "title":str(body.get("hud_title") or body.get("title") or "DATA")[:40],
              "value":str(body.get("hud_value") or body.get("value") or "")[:80],
              "unit":str(body.get("unit") or "")[:16],
              "color":str(body.get("color") or "#35ffe4")[:24]}
        hud.append(card);scene["hud"]=hud[:32];state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_hud_update":
        scene=dict(state.get("scene") or {});hud=list(scene.get("hud") or []);hid=str(body.get("hud_id") or "")
        found=False
        for i,card in enumerate(hud):
            if str(card.get("id")) != hid: continue
            item=dict(card)
            if "hud_title" in body or "title" in body: item["title"]=str(body.get("hud_title") or body.get("title") or "")[:40]
            if "hud_value" in body or "value" in body: item["value"]=str(body.get("hud_value") or body.get("value") or "")[:80]
            if "unit" in body: item["unit"]=str(body.get("unit") or "")[:16]
            if "color" in body: item["color"]=str(body.get("color") or "#35ffe4")[:24]
            hud[i]=item;found=True;break
        if not found: return web.json_response({"ok":False,"error":"hud_not_found"}, status=404)
        scene["hud"]=hud;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_hud_remove":
        scene=dict(state.get("scene") or {});hid=str(body.get("hud_id") or "")
        scene["hud"]=[x for x in (scene.get("hud") or []) if str(x.get("id")) != hid]
        state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_hud_clear":
        scene=dict(state.get("scene") or {});scene["hud"]=[];state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_project_save":
        scene=copy.deepcopy(state.get("scene") or {})
        name=str(body.get("project_name") or scene.get("project_name") or "Scene")[:80].strip() or "Scene"
        slug=re.sub(r"[^A-Za-z0-9_-]+","_",name).strip("_")[:60] or "scene"
        project_id=str(body.get("project_id") or f"{slug}_{uuid.uuid4().hex[:8]}")
        project_id=re.sub(r"[^A-Za-z0-9_-]","",project_id)[:80]
        scene["project_name"]=name
        directory=Path(DATA_DIR)/"scene_projects";directory.mkdir(parents=True,exist_ok=True)
        payload={"id":project_id,"name":name,"updated_at":time.time(),"scene":scene}
        (directory/f"{project_id}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        state["scene"]=scene;state["mode"]="scene_lab";state["project_result"]=payload
    elif op == "scene_project_list":
        directory=Path(DATA_DIR)/"scene_projects";projects=[]
        if directory.exists():
            for path in sorted(directory.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True)[:50]:
                try:
                    data=json.loads(path.read_text(encoding="utf-8"))
                    projects.append({"id":str(data.get("id") or path.stem),"name":str(data.get("name") or path.stem),
                                     "updated_at":float(data.get("updated_at") or path.stat().st_mtime)})
                except Exception: continue
        state["project_result"]={"projects":projects}
    elif op == "scene_project_load":
        project_id=re.sub(r"[^A-Za-z0-9_-]","",str(body.get("project_id") or ""))[:80]
        path=Path(DATA_DIR)/"scene_projects"/f"{project_id}.json"
        if not project_id or not path.exists():
            return web.json_response({"ok":False,"error":"project_not_found"},status=404)
        try: payload=json.loads(path.read_text(encoding="utf-8"))
        except Exception: return web.json_response({"ok":False,"error":"project_invalid"},status=400)
        scene=payload.get("scene")
        if not isinstance(scene,dict): return web.json_response({"ok":False,"error":"project_invalid"},status=400)
        # Reuse the regular scene_load path by validating the project scene inline.
        body={"operation":"scene_load","scene":scene}
        class _ProjectReq:
            async def json(self): return body
        return await api_stage_command(_ProjectReq())
    elif op == "scene_project_delete":
        project_id=re.sub(r"[^A-Za-z0-9_-]","",str(body.get("project_id") or ""))[:80]
        path=Path(DATA_DIR)/"scene_projects"/f"{project_id}.json"
        if path.exists(): path.unlink()
        state["project_result"]={"deleted":project_id}
    elif op == "scene_asset_list":
        directory=Path(DATA_DIR)/"scene_models";models=[]
        if directory.exists():
            for meta_path in sorted(directory.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True)[:100]:
                try:
                    data=json.loads(meta_path.read_text(encoding="utf-8"))
                    mid=re.sub(r"[^A-Za-z0-9_-]","",str(data.get("id") or meta_path.stem))[:48]
                    glb=directory/f"{mid}.glb"
                    if not glb.exists():continue
                    models.append({"id":mid,"name":str(data.get("name") or "model.glb")[:160],
                                   "bytes":int(data.get("bytes") or glb.stat().st_size),
                                   "created_at":float(data.get("created_at") or glb.stat().st_mtime)})
                except Exception:continue
        state["asset_result"]={"models":models};state["mode"]="scene_lab"
    elif op == "scene_asset_add":
        directory=Path(DATA_DIR)/"scene_models";raw=str(body.get("model_id") or body.get("asset_name") or body.get("label") or "").strip()
        match=None
        if directory.exists():
            for meta_path in directory.glob("*.json"):
                try:
                    data=json.loads(meta_path.read_text(encoding="utf-8"));mid=str(data.get("id") or meta_path.stem);name=str(data.get("name") or "")
                    if raw==mid or raw.lower()==name.lower() or (raw and raw.lower() in name.lower()):
                        match={"id":mid,"name":name};break
                except Exception:continue
        if not match:return web.json_response({"ok":False,"error":"asset_not_found"},status=404)
        body={"operation":"scene_add","kind":"custom","model_id":match["id"],"label":str(body.get("label") or match["name"]).replace(".glb","")[:60],
              "color":str(body.get("color") or "#ff3047"),"wireframe":bool(body.get("wireframe",True))}
        class _AssetReq:
            async def json(self):return body
        return await api_stage_command(_AssetReq())
    elif op == "scene_asset_delete":
        model_id=re.sub(r"[^A-Za-z0-9_-]","",str(body.get("model_id") or ""))[:48]
        if not model_id:return web.json_response({"ok":False,"error":"model_id_required"},status=400)
        if any(str(o.get("model_id") or "")==model_id for o in (state.get("scene",{}).get("objects") or [])):
            return web.json_response({"ok":False,"error":"model_in_use"},status=409)
        directory=Path(DATA_DIR)/"scene_models";removed=False
        for suffix in (".glb",".json"):
            path=directory/f"{model_id}{suffix}"
            if path.exists():path.unlink();removed=True
        if not removed:return web.json_response({"ok":False,"error":"asset_not_found"},status=404)
        state["asset_result"]={"deleted":model_id};state["mode"]="scene_lab"
    elif op == "scene_constraint":
        scene=dict(state.get("scene") or {});objects=[dict(o) for o in scene.get("objects") or []]
        source=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"))
        kind=str(body.get("constraint") or body.get("constraint_type") or "none").lower()
        if kind not in {"none","follow","look_at","orbit_target"}:kind="none"
        target=_scene_resolve_object(scene,body.get("target_id"),body.get("target_label"))
        if kind!="none" and (not target or target==source):
            return web.json_response({"ok":False,"error":"constraint_target_required"},status=400)
        found=False
        for obj in objects:
            if str(obj.get("id"))!=source:continue
            offset=body.get("offset")
            if offset is None and body.get("offset_json"):
                try:offset=json.loads(str(body.get("offset_json")))
                except Exception:offset=None
            if not isinstance(offset,list):offset=[_stage_number(body.get("dx",0),0,-8,8),_stage_number(body.get("dy",0),0,-6,6),_stage_number(body.get("dz",0),0,-8,8)]
            while len(offset)<3:offset.append(0)
            obj["constraint"]={"type":kind,"target_id":target if kind!="none" else None,
                               "distance":_stage_number(body.get("distance",2),2,.2,8),
                               "speed":_stage_number(body.get("constraint_speed",body.get("speed",1)),1,.05,5),
                               "offset":[_stage_number(offset[0],0,-8,8),_stage_number(offset[1],0,-6,6),_stage_number(offset[2],0,-8,8)]}
            found=True;break
        if not found:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_waypoint_add":
        scene=dict(state.get("scene") or {});objects=[dict(o) for o in scene.get("objects") or []]
        target=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"));found=False
        for obj in objects:
            if str(obj.get("id"))!=target:continue
            path=dict(obj.get("path") or {});points=list(path.get("points") or [])
            current=list(obj.get("position") or [0,0,0])
            while len(current)<3:current.append(0)
            point=body.get("point")
            if point is None and body.get("point_json"):
                try:point=json.loads(str(body.get("point_json")))
                except Exception:point=None
            if not isinstance(point,list):point=[body.get("x",current[0]),body.get("y",current[1]),body.get("z",current[2])]
            while len(point)<3:point.append(0)
            points.append([_stage_number(point[0],0,-12,12),_stage_number(point[1],0,-8,8),_stage_number(point[2],0,-12,12)])
            path.update({"points":points[-32:],"speed":_stage_number(body.get("path_speed",path.get("speed",1)),1,.05,5),
                         "loop":bool(body.get("loop",path.get("loop",True)))})
            obj["path"]=path;found=True;break
        if not found:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_waypoint_clear":
        scene=dict(state.get("scene") or {});objects=[dict(o) for o in scene.get("objects") or []]
        target=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"));found=False
        for obj in objects:
            if str(obj.get("id"))==target:
                obj["path"]={"points":[],"speed":1.0,"loop":True,"started_at":None};found=True;break
        if not found:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_path_play":
        scene=dict(state.get("scene") or {});objects=[dict(o) for o in scene.get("objects") or []]
        target=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"));found=False
        for obj in objects:
            if str(obj.get("id"))!=target:continue
            path=dict(obj.get("path") or {});points=list(path.get("points") or [])
            if len(points)<2:return web.json_response({"ok":False,"error":"path_requires_two_waypoints"},status=400)
            path["speed"]=_stage_number(body.get("path_speed",path.get("speed",1)),1,.05,5)
            if "loop" in body:path["loop"]=bool(body["loop"])
            path["started_at"]=time.time();obj["path"]=path;found=True;break
        if not found:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_path_stop":
        scene=dict(state.get("scene") or {});objects=[dict(o) for o in scene.get("objects") or []]
        target=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"));found=False
        for obj in objects:
            if str(obj.get("id"))==target:
                path=dict(obj.get("path") or {});path["started_at"]=None;obj["path"]=path;found=True;break
        if not found:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_target_lock":
        scene=dict(state.get("scene") or {});target=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"))
        if not target:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        scene["target_id"]=target;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_target_clear":
        scene=dict(state.get("scene") or {});scene["target_id"]=None;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_render_mode":
        scene=dict(state.get("scene") or {});mode=str(body.get("render_mode") or body.get("preset") or "hologram").lower()
        if mode not in {"hologram","blueprint","xray","solid","thermal"}:mode="hologram"
        scene["render_mode"]=mode
        if mode=="blueprint":scene.update({"theme":"cyan","grid":True,"show_labels":True,"audio_reactive":False})
        elif mode=="xray":scene.update({"theme":"cyan","grid":True,"audio_reactive":False})
        elif mode=="thermal":scene.update({"theme":"amber","grid":False,"audio_reactive":False})
        state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_physics":
        scene=dict(state.get("scene") or {});objects=[dict(o) for o in scene.get("objects") or []]
        target=_scene_resolve_object(scene,body.get("object_id"),body.get("object_label"),scene.get("selected_id"))
        mode=str(body.get("physics_mode") or body.get("preset") or "off").lower()
        if mode not in {"off","drop","launch","zero_g","float"}:mode="off"
        found=False
        for obj in objects:
            if str(obj.get("id"))!=target:continue
            velocity=body.get("velocity")
            if velocity is None and body.get("velocity_json"):
                try:velocity=json.loads(str(body.get("velocity_json")))
                except Exception:velocity=None
            if not isinstance(velocity,list):velocity=[_stage_number(body.get("vx",0),0,-20,20),_stage_number(body.get("vy",0 if mode!="launch" else 4),0,-20,20),_stage_number(body.get("vz",0),0,-20,20)]
            while len(velocity)<3:velocity.append(0)
            obj["physics"]={"mode":mode,"gravity":_stage_number(body.get("gravity",9.81),9.81,0,30),
                            "velocity":[_stage_number(velocity[0],0,-20,20),_stage_number(velocity[1],0,-20,20),_stage_number(velocity[2],0,-20,20)],
                            "bounce":_stage_number(body.get("bounce",.45),.45,0,1),"floor":_stage_number(body.get("floor",-1.3),-1.3,-4,4),
                            "started_at":time.time() if mode!="off" else None}
            found=True;break
        if not found:return web.json_response({"ok":False,"error":"scene_object_not_found"},status=404)
        scene["objects"]=objects;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_measure":
        scene=dict(state.get("scene") or {});objects=list(scene.get("objects") or [])
        source=_scene_resolve_object(scene,body.get("source_id"),body.get("source_label"),(scene.get("selected_ids") or [scene.get("selected_id")])[0] if (scene.get("selected_ids") or [scene.get("selected_id")]) else None)
        target=_scene_resolve_object(scene,body.get("target_id"),body.get("target_label"),(scene.get("selected_ids") or [None,None])[-1])
        byid={str(o.get("id")):o for o in objects}
        if source not in byid or target not in byid or source==target:return web.json_response({"ok":False,"error":"measurement_requires_two_objects"},status=400)
        a=list(byid[source].get("position") or [0,0,0]);b=list(byid[target].get("position") or [0,0,0])
        while len(a)<3:a.append(0)
        while len(b)<3:b.append(0)
        distance=math.sqrt(sum((float(a[i])-float(b[i]))**2 for i in range(3)))
        m={"id":uuid.uuid4().hex[:8],"source":source,"target":target,
           "label":str(body.get("label") or "DIST")[:40],"color":str(body.get("color") or "#ffd43b")[:24]}
        measurements=list(scene.get("measurements") or []);measurements.append(m);scene["measurements"]=measurements[-24:]
        state["measurement_result"]={"id":m["id"],"distance":distance,"source":source,"target":target}
        state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_measure_clear":
        scene=dict(state.get("scene") or {});scene["measurements"]=[];state["scene"]=scene;state["mode"]="scene_lab";state["measurement_result"]={"cleared":True}
    elif op == "scene_focus":
        scene = dict(state.get("scene") or {})
        target = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"), scene.get("selected_id"))
        if target and not any(str(o.get("id")) == target for o in scene.get("objects") or []):
            return web.json_response({"ok":False,"error":"scene_object_not_found"}, status=404)
        scene["focus_id"] = target or None
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_duplicate":
        scene = dict(state.get("scene") or {})
        objects = list(scene.get("objects") or [])
        target = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"), scene.get("selected_id"))
        src = next((dict(o) for o in objects if str(o.get("id")) == target), None)
        if not src:
            return web.json_response({"ok": False, "error": "scene_object_not_found"}, status=404)
        clone = copy.deepcopy(src)
        clone["id"] = uuid.uuid4().hex[:8]
        clone["label"] = (str(src.get("label") or src.get("kind") or "OBJECT") + " COPY")[:60]
        pos = list(clone.get("position") or [0,0,0])
        while len(pos) < 3: pos.append(0)
        pos[0] = _stage_number(pos[0] + .6, 0, -6, 6)
        pos[2] = _stage_number(pos[2] + .4, 0, -6, 6)
        clone["position"] = pos
        objects.append(clone)
        scene["objects"] = objects
        scene["selected_id"] = clone["id"]
        scene["selected_ids"] = [clone["id"]]
        state["scene"] = scene
        state.update({"mode":"scene_lab","title":"SCENE LAB","subtitle":f"{len(objects)} OBJECTS / LIVE"})
    elif op == "scene_motion":
        scene = dict(state.get("scene") or {})
        objects = list(scene.get("objects") or [])
        target = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"), scene.get("selected_id"))
        motion_type = str(body.get("motion") or "none").lower()
        if motion_type not in {"none","orbit","bob","patrol","pulse"}:
            motion_type = "none"
        found = False
        for i,item in enumerate(objects):
            if str(item.get("id")) != target:
                continue
            obj = dict(item)
            obj["motion"] = {
                "type": motion_type,
                "speed": _stage_number(body.get("motion_speed",1),1,.05,5),
                "radius": _stage_number(body.get("radius",1.5),1.5,.1,6),
                "amplitude": _stage_number(body.get("amplitude",.5),.5,.05,4),
                "axis": str(body.get("axis") or "y").lower(),
            }
            objects[i] = obj
            found = True
            break
        if not found:
            return web.json_response({"ok": False, "error":"scene_object_not_found"}, status=404)
        scene["objects"] = objects
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_collision_overlay":
        scene=dict(state.get("scene") or {})
        scene["collision_overlay"]=bool(body.get("enabled", not bool(scene.get("collision_overlay",False))))
        state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_diagnostics":
        scene=_scene_ensure(dict(state.get("scene") or {}));objects=[o for o in scene.get("objects") or [] if isinstance(o,dict)]
        ids=[str(o.get("id")) for o in objects];idset=set(ids);byid={str(o.get("id")):o for o in objects}
        issues=[]
        if len(ids)!=len(idset):issues.append({"type":"duplicate_id","detail":"Duplicate scene object IDs detected."})
        for obj in objects:
            oid=str(obj.get("id"));parent=str(obj.get("parent_id") or "")
            if parent and parent not in idset:issues.append({"type":"invalid_parent","object":oid,"parent":parent})
            constraint=dict(obj.get("constraint") or {});constraint_target=str(constraint.get("target_id") or "")
            if str(constraint.get("type") or "none")!="none" and constraint_target not in idset:
                issues.append({"type":"invalid_constraint","object":oid,"target":constraint_target})
            model_id=str(obj.get("model_id") or "")
            if model_id:
                path=Path(DATA_DIR)/"scene_models"/f"{re.sub(r'[^A-Za-z0-9_-]','',model_id)[:48]}.glb"
                if not path.exists():issues.append({"type":"missing_asset","object":oid,"model_id":model_id})
        for link in scene.get("links") or []:
            if str(link.get("source")) not in idset or str(link.get("target")) not in idset:
                issues.append({"type":"invalid_link","id":str(link.get("id") or "")})
        for measurement in scene.get("measurements") or []:
            if str(measurement.get("source")) not in idset or str(measurement.get("target")) not in idset:
                issues.append({"type":"invalid_measurement","id":str(measurement.get("id") or "")})
        for frame in (scene.get("timeline") or {}).get("keyframes") or []:
            if str(frame.get("object_id")) not in idset:issues.append({"type":"dangling_keyframe","id":str(frame.get("id") or "")})
        # Approximate world transforms for collision diagnostics. Bounding spheres are orientation-independent.
        def _world_transform(oid,seen=None):
            seen=set(seen or ())
            if oid in seen:return ([0.0,0.0,0.0],1.0)
            seen.add(oid);obj=byid.get(oid) or {};pos=list(obj.get("position") or [0,0,0])
            while len(pos)<3:pos.append(0)
            scale=float(obj.get("scale",1) or 1);parent=str(obj.get("parent_id") or "")
            if parent and parent in byid:
                pp,ps=_world_transform(parent,seen)
                return ([pp[0]+float(pos[0])*ps,pp[1]+float(pos[1])*ps,pp[2]+float(pos[2])*ps],scale*ps)
            return ([float(pos[0]),float(pos[1]),float(pos[2])],scale)
        radii={"vehicle":1.45,"drone":1.35,"globe":1.2,"robot":1.05,"arm":1.0,"aircraft":1.5,"ship":1.45,
               "building":1.1,"satellite":1.2,"network":1.1,"tower":1.15,"ring":1.25,"portal":1.25,"custom":1.0}
        collisions=[]
        visible=[o for o in objects if o.get("visible",True) is not False]
        for i,a in enumerate(visible):
            aid=str(a.get("id"));ap,ascale=_world_transform(aid);ar=radii.get(str(a.get("kind") or ""),1.0)*abs(ascale)
            for b in visible[i+1:]:
                bid=str(b.get("id"));bp,bscale=_world_transform(bid);br=radii.get(str(b.get("kind") or ""),1.0)*abs(bscale)
                dist=math.sqrt(sum((ap[k]-bp[k])**2 for k in range(3)));threshold=(ar+br)*.72
                if dist<threshold:
                    collisions.append({"a":aid,"a_label":str(a.get("label") or aid),"b":bid,"b_label":str(b.get("label") or bid),
                                       "distance":round(dist,3),"threshold":round(threshold,3)})
        result={"ok":not issues,"health":"warning" if issues or collisions else "ok","objects":len(objects),
                "groups":len(scene.get("groups") or []),"links":len(scene.get("links") or []),"hud":len(scene.get("hud") or []),
                "measurements":len(scene.get("measurements") or []),"object_keyframes":len((scene.get("timeline") or {}).get("keyframes") or []),
                "camera_keyframes":len(scene.get("camera_track") or []),"issues":issues[:40],"collisions":collisions[:40]}
        state["diagnostics_result"]=result;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "scene_theme":
        scene = dict(state.get("scene") or {})
        theme = str(body.get("theme") or "crimson").lower()
        if theme not in {"crimson","cyan","purple","amber","mono"}:
            theme = "crimson"
        scene["theme"] = theme
        if "grid" in body: scene["grid"] = bool(body["grid"])
        if "show_labels" in body: scene["show_labels"] = bool(body["show_labels"])
        if "show_trails" in body: scene["show_trails"] = bool(body["show_trails"])
        if "audio_reactive" in body: scene["audio_reactive"] = bool(body["audio_reactive"])
        if "snap" in body: scene["snap"] = _stage_number(body.get("snap"), scene.get("snap",.25), 0, 2)
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_undo":
        if hub.scene_history:
            current = copy.deepcopy(state.get("scene") or {})
            hub.scene_future.append(current)
            state["scene"] = _scene_ensure(hub.scene_history.pop())
        state.update({"mode":"scene_lab","title":"SCENE LAB","subtitle":"UNDO"})
    elif op == "scene_redo":
        if hub.scene_future:
            current = copy.deepcopy(state.get("scene") or {})
            hub.scene_history.append(current)
            state["scene"] = _scene_ensure(hub.scene_future.pop())
        state.update({"mode":"scene_lab","title":"SCENE LAB","subtitle":"REDO"})
    elif op == "timeline_set":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        timeline["duration"] = _stage_number(body.get("duration", timeline.get("duration",8)), 8, 1, 60)
        if "loop" in body: timeline["loop"] = bool(body["loop"])
        scene["timeline"] = timeline
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "camera_keyframe_capture":
        scene=dict(state.get("scene") or {});timeline=dict(scene.get("timeline") or {})
        duration=max(1.0,float(timeline.get("duration",8)));at=_stage_number(body.get("time",timeline.get("cursor",0)),timeline.get("cursor",0),0,duration)
        pose=body.get("pose")
        if pose is None and body.get("position_json") and body.get("target_json"):
            try:pose={"position":json.loads(str(body["position_json"])),"target":json.loads(str(body["target_json"]))}
            except Exception:pose=None
        if pose is None:pose=scene.get("camera_pose")
        if not isinstance(pose,dict):
            preset=str(scene.get("camera") or "isometric");positions={"front":[0,1.2,9],"top":[0,9,.01],"side":[9,1.2,0],"close":[0,.8,5.2],"orbit":[6,4.2,7.2],"isometric":[6,4.2,7.2]}
            pose={"position":positions.get(preset,[6,4.2,7.2]),"target":[0,0,0]}
        p=list(pose.get("position") or [6,4.2,7.2]);target=list(pose.get("target") or [0,0,0])
        while len(p)<3:p.append(0)
        while len(target)<3:target.append(0)
        easing=str(body.get("easing") or "ease_in_out")
        if easing not in {"linear","ease_in","ease_out","ease_in_out"}:easing="ease_in_out"
        shots=[s for s in (scene.get("camera_track") or []) if abs(float(s.get("time",0))-at)>=.001]
        shot={"id":uuid.uuid4().hex[:8],"time":at,
              "position":[_stage_number(p[0],6,-30,30),_stage_number(p[1],4.2,-30,30),_stage_number(p[2],7.2,-30,30)],
              "target":[_stage_number(target[0],0,-10,10),_stage_number(target[1],0,-10,10),_stage_number(target[2],0,-10,10)],
              "easing":easing}
        shots.append(shot);scene["camera_track"]=sorted(shots,key=lambda x:float(x.get("time",0)))[:64]
        timeline["cursor"]=at;scene["timeline"]=timeline;state["scene"]=scene;state["mode"]="scene_lab";state["camera_keyframe_result"]=shot
    elif op == "camera_keyframe_remove":
        scene=dict(state.get("scene") or {});kid=str(body.get("keyframe_id") or body.get("camera_keyframe_id") or "")
        scene["camera_track"]=[s for s in (scene.get("camera_track") or []) if str(s.get("id"))!=kid]
        state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "camera_track_clear":
        scene=dict(state.get("scene") or {});scene["camera_track"]=[];state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "timeline_capture":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        frames = list(timeline.get("keyframes") or [])
        target = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"), scene.get("selected_id"))
        obj = next((o for o in scene.get("objects") or [] if str(o.get("id")) == target), None)
        if not obj:
            return web.json_response({"ok": False, "error":"scene_object_not_found"}, status=404)
        duration = float(timeline.get("duration",8))
        at = _stage_number(body.get("time", timeline.get("cursor",0)), timeline.get("cursor",0), 0, duration)
        frames.append({
            "id": uuid.uuid4().hex[:8], "time": at, "object_id": target,
            "position": copy.deepcopy(obj.get("position") or [0,0,0]),
            "rotation": copy.deepcopy(obj.get("rotation") or [0,0,0]),
            "scale": float(obj.get("scale",1)),
            "easing": str(body.get("easing") or "ease_in_out") if str(body.get("easing") or "ease_in_out") in {"linear","ease_in","ease_out","ease_in_out"} else "ease_in_out",
        })
        frames = sorted(frames, key=lambda x: (str(x.get("object_id")), float(x.get("time",0))))[:128]
        timeline["keyframes"] = frames
        timeline["cursor"] = at
        scene["timeline"] = timeline
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "timeline_capture_all":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        frames = list(timeline.get("keyframes") or [])
        duration = float(timeline.get("duration",8))
        at = _stage_number(body.get("time", timeline.get("cursor",0)), timeline.get("cursor",0), 0, duration)
        selected = [str(x) for x in scene.get("selected_ids") or []]
        capture_all = str(body.get("selection_mode") or "").lower() == "all" or not selected
        targets = [o for o in scene.get("objects") or [] if capture_all or str(o.get("id")) in selected]
        easing = str(body.get("easing") or "ease_in_out")
        if easing not in {"linear","ease_in","ease_out","ease_in_out"}: easing="ease_in_out"
        for obj in targets:
            oid=str(obj.get("id"))
            # Replace a same-time keyframe for this object instead of stacking duplicates.
            frames=[k for k in frames if not (str(k.get("object_id"))==oid and abs(float(k.get("time",0))-at)<.001)]
            frames.append({"id":uuid.uuid4().hex[:8],"time":at,"object_id":oid,
                           "position":copy.deepcopy(obj.get("position") or [0,0,0]),
                           "rotation":copy.deepcopy(obj.get("rotation") or [0,0,0]),
                           "scale":float(obj.get("scale",1)),"easing":easing})
        timeline["keyframes"]=sorted(frames,key=lambda x:(float(x.get("time",0)),str(x.get("object_id"))))[:256]
        timeline["cursor"]=at
        scene["timeline"]=timeline;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "timeline_keyframe_update":
        scene=dict(state.get("scene") or {});timeline=dict(scene.get("timeline") or {});frames=list(timeline.get("keyframes") or [])
        kid=str(body.get("keyframe_id") or "");found=False;duration=float(timeline.get("duration",8))
        for i,kf in enumerate(frames):
            if str(kf.get("id"))!=kid:continue
            item=dict(kf)
            if "time" in body:item["time"]=_stage_number(body.get("time"),item.get("time",0),0,duration)
            if "easing" in body:
                easing=str(body.get("easing") or "ease_in_out");item["easing"]=easing if easing in {"linear","ease_in","ease_out","ease_in_out"} else "ease_in_out"
            frames[i]=item;found=True;break
        if not found:return web.json_response({"ok":False,"error":"keyframe_not_found"},status=404)
        timeline["keyframes"]=sorted(frames,key=lambda x:(float(x.get("time",0)),str(x.get("object_id"))))
        scene["timeline"]=timeline;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "timeline_shift":
        scene=dict(state.get("scene") or {});timeline=dict(scene.get("timeline") or {});duration=float(timeline.get("duration",8))
        delta=_stage_number(body.get("delta_time",0),0,-60,60);selected=[str(x) for x in scene.get("selected_ids") or []]
        all_frames=str(body.get("selection_mode") or "").lower()=="all" or not selected
        frames=[]
        for kf in timeline.get("keyframes") or []:
            item=dict(kf)
            if all_frames or str(item.get("object_id")) in selected:
                item["time"]=_stage_number(float(item.get("time",0))+delta,0,0,duration)
            frames.append(item)
        timeline["keyframes"]=sorted(frames,key=lambda x:(float(x.get("time",0)),str(x.get("object_id"))))
        scene["timeline"]=timeline;state["scene"]=scene;state["mode"]="scene_lab"
    elif op == "timeline_remove_keyframe":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        kid = str(body.get("keyframe_id") or "")
        timeline["keyframes"] = [k for k in (timeline.get("keyframes") or []) if str(k.get("id")) != kid]
        scene["timeline"] = timeline
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "timeline_clear":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        timeline.update({"keyframes":[],"cursor":0.0,"playing":False,"started_at":None})
        scene["timeline"] = timeline
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "timeline_seek":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        duration = max(1.0,float(timeline.get("duration",8)))
        cursor = _stage_number(body.get("time",0),0,0,duration)
        timeline["cursor"] = cursor
        if timeline.get("playing"):
            timeline["started_at"] = time.time() - cursor
        scene["timeline"] = timeline
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "timeline_play":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        cursor = float(timeline.get("cursor",0))
        timeline["playing"] = True
        timeline["started_at"] = time.time() - cursor
        scene["timeline"] = timeline
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "timeline_pause":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        duration = max(1.0,float(timeline.get("duration",8)))
        started = timeline.get("started_at")
        if timeline.get("playing") and started:
            elapsed = max(0.0,time.time()-float(started))
            timeline["cursor"] = elapsed % duration if timeline.get("loop",True) else min(duration,elapsed)
        timeline["playing"] = False
        timeline["started_at"] = None
        scene["timeline"] = timeline
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "timeline_preset":
        scene = dict(state.get("scene") or {})
        timeline = dict(scene.get("timeline") or {})
        target = _scene_resolve_object(scene, body.get("object_id"), body.get("object_label"), scene.get("selected_id"))
        obj = next((o for o in scene.get("objects") or [] if str(o.get("id")) == target), None)
        if not obj:
            return web.json_response({"ok": False, "error":"scene_object_not_found"}, status=404)
        duration = _stage_number(body.get("duration", timeline.get("duration",8)),8,2,30)
        preset = str(body.get("preset") or "showcase").lower()
        p = list(obj.get("position") or [0,0,0]); r = list(obj.get("rotation") or [0,0,0]); s=float(obj.get("scale",1))
        while len(p)<3: p.append(0)
        while len(r)<3: r.append(0)
        def _kf(at,pos,rot,scale):
            return {"id":uuid.uuid4().hex[:8],"time":at,"object_id":target,"position":pos,"rotation":rot,"scale":scale,"easing":"ease_in_out"}
        if preset == "launch":
            frames=[_kf(0,p,r,s),_kf(duration,[p[0],min(4,p[1]+3),p[2]],[r[0],r[1]+6.283,r[2]],max(.2,s*.8))]
        elif preset == "flyby":
            frames=[_kf(0,[max(-6,p[0]-3),p[1],p[2]],r,s),_kf(duration,[min(6,p[0]+3),p[1],p[2]],[r[0],r[1]+3.14,r[2]],s)]
        else:
            frames=[_kf(0,p,r,s),_kf(duration/2,[p[0],min(4,p[1]+.8),p[2]],[r[0],r[1]+3.14,r[2]],min(3,s*1.25)),_kf(duration,p,[r[0],r[1]+6.283,r[2]],s)]
        timeline.update({"duration":duration,"cursor":0.0,"keyframes":frames,"playing":False,"started_at":None})
        scene["timeline"] = timeline
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_cinematic":
        scene = dict(state.get("scene") or {})
        cinematic = dict(scene.get("cinematic") or {})
        preset = str(body.get("cinematic") or body.get("preset") or "orbit").lower()
        if preset in {"off","stop","none"}:
            cinematic["enabled"] = False
            cinematic["started_at"] = None
        else:
            if preset not in {"orbit","flyby","topdown","hero","spiral"}:
                preset = "orbit"
            cinematic.update({
                "enabled": True, "preset": preset,
                "duration": _stage_number(body.get("duration",8),8,2,30),
                "started_at": time.time(),
                "loop": bool(body.get("loop",True)),
            })
        scene["cinematic"] = cinematic
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_director":
        scene = _scene_ensure(dict(state.get("scene") or {}))
        preset = str(body.get("preset") or "showcase").lower()
        if preset not in {"showcase","analysis","battle","presentation","launch"}:
            preset = "showcase"
        theme = {"showcase":"purple","analysis":"cyan","battle":"crimson","presentation":"amber","launch":"crimson"}[preset]
        camera = {"showcase":"hero","analysis":"topdown","battle":"flyby","presentation":"orbit","launch":"spiral"}[preset]
        scene["theme"] = theme
        scene["show_labels"] = True
        scene["show_trails"] = preset in {"analysis","battle","launch"}
        scene["grid"] = preset != "presentation"
        scene["animation"] = "scan" if preset in {"analysis","battle"} else "idle"
        duration = _stage_number(body.get("duration",10),10,3,30)
        scene["cinematic"] = {"enabled":True,"preset":camera,"duration":duration,"started_at":time.time(),"loop":True}
        objects=[]
        for item in scene.get("objects") or []:
            obj=dict(item);kind=str(obj.get("kind") or "")
            if preset=="analysis":
                mtype="bob" if kind in {"drone","satellite","aircraft"} else "pulse"
            elif preset=="battle":
                mtype="orbit" if kind in {"drone","aircraft","satellite"} else ("patrol" if kind in {"vehicle","ship","robot"} else "pulse")
            elif preset=="launch":
                mtype="bob" if kind in {"ship","aircraft","drone","satellite"} else "pulse"
            elif preset=="presentation":
                mtype="none"
            else:
                mtype="orbit" if kind in {"drone","satellite"} else "pulse"
            obj["motion"]={"type":mtype,"speed":1.0 if preset!="battle" else 1.5,
                           "radius":1.4,"amplitude":.55,"axis":"y"}
            objects.append(obj)
        scene["objects"]=objects
        state["scene"]=scene
        state.update({"mode":"scene_lab","title":"SCENE DIRECTOR",
                      "subtitle":f"{preset.upper()} / LIVE","progress":100})
    elif op == "scene_animation":
        scene = dict(state.get("scene") or {})
        animation = str(body.get("animation") or "idle").lower()
        if animation not in {"idle","spin","scan","explode","assemble"}: animation="idle"
        scene["animation"] = animation
        if animation == "explode": scene["explode"] = 1.0
        elif animation == "assemble": scene["explode"] = 0.0
        if "explode" in body: scene["explode"] = _stage_number(body.get("explode"), scene.get("explode",0), 0, 2)
        state["scene"] = scene
        state["mode"] = "scene_lab"
    elif op == "scene_record":
        duration = _stage_number(body.get("duration",8),8,2,30)
        job_id = uuid.uuid4().hex[:10]
        state["record_nonce"] = int(state.get("record_nonce",0)) + 1
        state["record_duration"] = duration
        state["job_id"] = job_id
        state["video"] = {
            "template":"live_scene","duration":duration,
            "title":str(body.get("title") or "ULTRON SCENE")[:100],
            "ready":False,"mime":"","bytes":0,
            "source_hologram":False,"source_scene":True,
        }
        state.update({"mode":"scene_lab","title":"LIVE SCENE RECORD",
                      "subtitle":f"{duration:.1f}s / 3D CANVAS","progress":0})
    elif op in {"video_create", "video_from_stage"}:
        source_hologram = op == "video_from_stage"
        source_scene = source_hologram and state.get("mode") == "scene_lab"
        duration = _stage_number(body.get("duration", 6), 6, 2, 15)
        template = str(body.get("template") or ("hologram_capture" if source_hologram else "ultron_intro")).strip().lower()
        if template not in {"ultron_intro", "logo_reveal", "energy_core",
                            "system_activation", "task_complete", "hologram_capture"}:
            template = "ultron_intro"
        job_id = uuid.uuid4().hex[:10]
        state["video"] = {
            "template": template, "duration": duration,
            "title": str(body.get("title") or state.get("hologram", {}).get("label") or "ULTRON")[:100],
            "ready": False, "mime": "", "bytes": 0,
            "source_hologram": source_hologram,
            "source_scene": source_scene,
        }
        state.update({"mode": "video_rendering", "title": "VIDEO RENDER",
                      "subtitle": template.replace("_", " ").upper(),
                      "progress": 0, "job_id": job_id})
    elif op == "scene_save":
        state["save_nonce"] = int(state.get("save_nonce", 0)) + 1
        state["save_kind"] = "scene"
    elif op == "hologram_save":
        state["save_nonce"] = int(state.get("save_nonce", 0)) + 1
        state["save_kind"] = "hologram"
    elif op == "video_save":
        if not bool((state.get("video") or {}).get("ready")):
            return web.json_response({"ok": False, "error": "video_not_ready"}, status=409)
        state["save_nonce"] = int(state.get("save_nonce", 0)) + 1
        state["save_kind"] = "video"
    elif op in {"video_play", "play"}:
        if bool((state.get("video") or {}).get("ready")):
            state["mode"] = "video_preview"
            state["video_paused"] = False
    elif op in {"video_pause", "pause"}:
        state["video_paused"] = True
    elif op == "task_progress":
        state.update({"mode": "task_progress",
                      "title": str(body.get("title") or "GÖREV ÇALIŞIYOR")[:100],
                      "subtitle": str(body.get("subtitle") or "ULTRON TASK ENGINE")[:140],
                      "progress": _stage_number(body.get("progress", 0), 0, 0, 100)})
    elif op == "screen_preview":
        state.update({"mode": "screen_preview", "title": "SCREEN PREVIEW",
                      "subtitle": "LIVE DESKTOP VISION", "progress": 100})
    else:
        return web.json_response({"ok": False, "error": "unknown_stage_operation"}, status=400)

    await _stage_publish()
    await hub.on_activity(f"Center Stage: {op}", "info")
    return web.json_response({"ok": True, **state})


async def api_stage_control(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    body = dict(body or {})
    body["operation"] = "hologram_update"

    class _StageReq:
        async def json(self):
            return body

    return await api_stage_command(_StageReq())


async def api_stage_video_ready(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    job_id = str(body.get("job_id", ""))
    if not job_id or job_id != str(hub.stage_state.get("job_id") or ""):
        return web.json_response({"ok": False, "error": "stale_video_job"}, status=409)
    video = dict(hub.stage_state.get("video") or {})
    video.update({"ready": True,
                  "mime": str(body.get("mime") or "video/webm")[:80],
                  "bytes": _stage_int(body.get("bytes", 0), 0, 0, 500_000_000)})
    hub.stage_state["video"] = video
    hub.stage_state.update({"mode": "video_preview", "progress": 100,
                            "title": "VIDEO READY", "subtitle": "LOCAL RENDER COMPLETE"})
    await _stage_publish()
    return web.json_response({"ok": True, **hub.stage_state})


async def api_activity(_req: web.Request) -> web.Response:
    return web.json_response(list(hub.activity))


async def api_notifications(_req: web.Request) -> web.Response:
    return web.json_response(list(hub.notifications))


async def api_config(_req: web.Request) -> web.Response:
    return web.json_response(hub.config())


async def api_agent_state(_req: web.Request) -> web.Response:
    return web.json_response({"state": hub.agent.state})


async def api_command(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    text = str(body.get("text", "")).strip()
    hub.last_command_ts = time.time()
    if not text:
        return web.json_response({"ok": False, "error": "empty command"}, status=400)
    if hub.agent.busy:
        return web.json_response({"ok": False, "error": "agent busy"}, status=409)
    # SECURITY: client-supplied `approved` flag is NEVER trusted. Approval is
    # granted only server-side via /api/task/approve (validates pending id)
    # or the codegen proposal endpoints (validate proposal id).
    asyncio.create_task(hub.agent.run(text, approved=False))
    return web.json_response({"ok": True})


async def api_task_pending(_req: web.Request) -> web.Response:
    return web.json_response(hub.pending_task or {})


async def api_task_approve(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    pid = str(body.get("id", ""))
    task = hub.pending_task
    if not task or task.get("id") != pid:
        return web.json_response({"ok": False, "error": "no such pending task"}, status=404)
    if time.time() - float(task.get("created", 0)) > 900:
        hub.pending_task = None
        await hub.broadcast_task()
        await hub.agent.set_state("IDLE", f"Task {pid} approval expired (TTL 15 min).")
        return web.json_response({"ok": False, "error": "approval expired"}, status=410)
    text = task["text"]
    hub.pending_task = None
    await hub.broadcast_task()
    await hub.on_activity(f"Task {pid} APPROVED", "success")
    asyncio.create_task(hub.agent.run(text, approved=True))
    return web.json_response({"ok": True})


async def api_task_reject(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    pid = str(body.get("id", ""))
    if hub.pending_task and hub.pending_task.get("id") == pid:
        hub.pending_task = None
        await hub.broadcast_task()
        await hub.agent.set_state("IDLE", f"Task {pid} rejected.")
        await hub.on_activity(f"Task {pid} REJECTED", "warn")
        return web.json_response({"ok": True})
    return web.json_response({"ok": False, "error": "no such pending task"}, status=404)


async def api_voice_report(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False}, status=400)
    hub.tools.report_voice(bool(body.get("available")), str(body.get("detail", "")))
    await hub.broadcast_tools()
    return web.json_response({"ok": True})


async def api_action_screenshot(_req: web.Request) -> web.Response:
    res = await hub.tools.execute("screen")
    return web.json_response(res)


async def api_action_browser(_req: web.Request) -> web.Response:
    res = await hub.tools.execute("browser", "https://www.google.com")
    return web.json_response(res)


async def api_action_system_check(_req: web.Request) -> web.Response:
    snap = hub.telemetry.snapshot()
    await hub.on_activity("System status checked", "info")
    return web.json_response({"ok": True, "output": snap})


async def api_action_clear_memory(_req: web.Request) -> web.Response:
    hub.memory.clear_all()
    await hub.broadcast({"type": "memory", "data": hub.memory.status()})
    await hub.on_activity("Memory cleared", "warn")
    return web.json_response({"ok": True})


# ---------------- code intelligence / codegen / tests ----------------
async def api_codeintel_analyze(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    target = str(body.get("target", "all"))
    rep = await asyncio.to_thread(hub.code_intel.analyze, target)
    await hub.on_activity(
        f"Code analysis [{target}]: {rep['summary']['files']} files, {len(rep['issues'])} issues", "info")
    return web.json_response(rep)


async def api_codeintel_explain(req: web.Request) -> web.Response:
    return web.json_response(await asyncio.to_thread(hub.code_intel.explain_file, req.query.get("file", "")))


async def api_codegen_propose(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    goal = str(body.get("goal", "")).strip()
    if not goal:
        return web.json_response({"ok": False, "error": "empty goal"}, status=400)
    brain = None
    if hub.bridge and hub.bridge.available and hub.ai_status.get("connected"):
        brain = hub.bridge.runtime.brain
    res = await hub.codegen.propose(goal, brain=brain)
    if res.get("ok"):
        await hub.agent.set_state("WAITING_APPROVAL",
                                  f"Patch {res['proposal']['id']} hazır — onay bekleniyor")
        await hub.broadcast({"type": "patch", "data": res["proposal"]})
        hub.notifier.notify("approval", f"Onay bekleyen patch: {res['proposal']['id']}", "warn", force=True)
    return web.json_response(res)


async def _test_emit(name: str, status: str, detail: str) -> None:
    await hub.broadcast({"type": "tests", "data": {"name": name, "status": status, "detail": detail[:200]}})


async def api_codegen_apply(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    pid = str(body.get("id", ""))
    res = await hub.codegen.apply(pid, run_tests=lambda quick=True: test_runner.run_all(_test_emit, quick=quick))
    if res.get("ok"):
        await hub.agent.set_state("DONE", f"Patch {pid} uygulandı, testler geçti.")
    else:
        await hub.agent.set_state("ERROR", f"Patch {pid}: {res.get('error')} (rollback: {res.get('rolled_back')})")
    await hub.broadcast({"type": "patch", "data": None})
    return web.json_response(res)


async def api_codegen_reject(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    res = hub.codegen.reject(str(body.get("id", "")))
    if not hub.codegen.pending():
        await hub.agent.set_state("IDLE")
    await hub.broadcast({"type": "patch", "data": None})
    return web.json_response(res)


async def api_codegen_pending(_req: web.Request) -> web.Response:
    return web.json_response(hub.codegen.pending())


async def api_tests_run(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    quick = bool(body.get("quick", False))
    results = await test_runner.run_all(_test_emit, quick=quick)
    failed = [r["name"] for r in results if not r["ok"]]
    await hub.on_activity(f"Test suite: {len(results) - len(failed)}/{len(results)} passed",
                          "success" if not failed else "error")
    if failed:
        hub.notifier.notify("tests", f"Testler başarısız: {', '.join(failed)}", "error", force=True)
    return web.json_response({"results": results, "failed": failed})


# ---------------- memory v16 management ----------------
def _v16_mem():
    if hub.bridge and hub.bridge.available:
        return hub.bridge.runtime.memory
    return None


async def api_memory_v16(req: web.Request) -> web.Response:
    mem = _v16_mem()
    if not mem:
        return web.json_response({"ok": False, "error": "V16 runtime unavailable"}, status=503)
    limit = int(req.query.get("limit", "50"))
    return web.json_response({"rows": mem.recent_full(limit), "kinds": mem.kind_counts()})


async def api_memory_v16_add(req: web.Request) -> web.Response:
    mem = _v16_mem()
    if not mem:
        return web.json_response({"ok": False, "error": "V16 runtime unavailable"}, status=503)
    body = await req.json()
    kind = str(body.get("kind", "FACT")).upper()[:16]
    text = str(body.get("text", "")).strip()
    if not text:
        return web.json_response({"ok": False, "error": "empty text"}, status=400)
    rid = mem.add(kind, text[:500])
    await hub.broadcast({"type": "memory", "data": hub.memory.status()})
    await hub.on_activity(f"Memory +{kind}: {text[:50]}", "info")
    return web.json_response({"ok": True, "id": rid})


async def api_memory_v16_delete(req: web.Request) -> web.Response:
    mem = _v16_mem()
    if not mem:
        return web.json_response({"ok": False, "error": "V16 runtime unavailable"}, status=503)
    body = await req.json()
    ok = mem.delete(body.get("id"))
    await hub.broadcast({"type": "memory", "data": hub.memory.status()})
    return web.json_response({"ok": ok})


async def api_memory_v16_clear(_req: web.Request) -> web.Response:
    mem = _v16_mem()
    if not mem:
        return web.json_response({"ok": False, "error": "V16 runtime unavailable"}, status=503)
    mem.clear()
    await hub.broadcast({"type": "memory", "data": hub.memory.status()})
    await hub.on_activity("V16 long-term memory cleared", "warn")
    return web.json_response({"ok": True})


async def api_memory_v16_search(req: web.Request) -> web.Response:
    mem = _v16_mem()
    if not mem:
        return web.json_response({"ok": False, "error": "V16 runtime unavailable"}, status=503)
    q = req.query.get("q", "")
    hits = hub.bridge.runtime.semantic_memory.search(q, limit=10)
    return web.json_response([{"score": round(s, 2), "kind": k, "content": c} for s, k, c, _ in hits])


# (V17.1 geçici debug endpoint'leri kaldırıldı — PHASE 14; gerçek tanı: /api/system/doctor)
# ---------------- mobile vision preview (additive) ----------------
async def api_vision_last(_req: web.Request) -> web.Response:
    d = Path(BASE) / "data" / "logs"
    files = []
    if d.exists():
        files = sorted(d.glob("screen_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return web.json_response({"exists": False})
    p = files[0]
    return web.json_response({"exists": True, "name": p.name, "size": p.stat().st_size, "ts": p.stat().st_mtime})


async def api_vision_preview(req: web.Request) -> web.Response:
    name = req.query.get("name", "")
    if not re.fullmatch(r"screen_[\w.\-]+\.png", name):
        return web.json_response({"ok": False, "error": "bad name"}, status=400)
    p = Path(BASE) / "data" / "logs" / name
    if not p.exists():
        return web.json_response({"ok": False, "error": "not found"}, status=404)
    return web.FileResponse(p)


# ---------------- shared-brain auth ----------------
async def api_auth_handshake(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        body = {}
    try:
        result = hub.auth.handshake(str(body.get("device", "client")), str(body.get("pairing_secret", "")))
    except PermissionError as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=401)
    return web.json_response(result)


async def api_auth_devices(_req: web.Request) -> web.Response:
    return web.json_response({"enabled": hub.auth.enabled(), "devices": hub.auth.devices()})


# ---------------- Credential vault ----------------
def _vault():
    rt = _rt()
    return rt.vault if rt else None


async def api_vault_list(_req: web.Request) -> web.Response:
    v = _vault()
    if not v:
        return web.json_response({"ok": False, "error": "vault unavailable (runtime)"}, status=503)
    return web.json_response({"ok": True, "entries": v.list_names(), "health": v.health()})


async def api_vault_set(req: web.Request) -> web.Response:
    v = _vault()
    if not v:
        return web.json_response({"ok": False, "error": "vault unavailable (runtime)"}, status=503)
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    name = str(body.get("name", "")).strip()
    value = str(body.get("value", ""))
    meta = str(body.get("meta", ""))
    if not name or not value:
        return web.json_response({"ok": False, "error": "name and value required"}, status=400)
    try:
        res = v.set(name, value, meta=meta)
    except Exception as e:  # noqa: BLE001
        return web.json_response({"ok": False, "error": str(e)}, status=503)
    hub.audit.write("VAULT_API_SET", f"name={name}")  # value never logged
    return web.json_response(res)


async def api_vault_delete(req: web.Request) -> web.Response:
    v = _vault()
    if not v:
        return web.json_response({"ok": False, "error": "vault unavailable (runtime)"}, status=503)
    try:
        body = await req.json()
    except Exception:
        body = {}
    ok = v.delete(str(body.get("name", "")))
    return web.json_response({"ok": ok})


# ---------------- Skills & connectors ----------------
async def api_wake_status(_req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"ok": False, "error": "runtime yok"}, status=503)
    wm = getattr(rt, "wake_manager", None)
    if wm is None:
        return web.json_response({"ok": True, "available": False,
                                  "engines": [], "note": "wake modülü yüklenemedi"})
    return web.json_response({"ok": True, **wm.status()})


async def api_skills(_req: web.Request) -> web.Response:
    rt = _rt()
    if not rt or not getattr(rt, "skills", None):
        return web.json_response({"ok": False, "error": "runtime yok"}, status=503)
    return web.json_response({"ok": True, "skills": rt.skills.list()})


async def api_connectors_health(_req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"ok": False, "error": "runtime yok"}, status=503)
    return web.json_response({"ok": True,
                              "weather": rt._weather.health(),
                              "calendar": rt._calendar.health(),
                              "email": rt._email.health()})


# ---------------- Long-running tasks / supervisor / model health ----------------
async def api_tasks_list(req: web.Request) -> web.Response:
    engine = getattr(hub, "task_engine", None)
    if not engine:
        return web.json_response({"tasks": []})
    status = req.query.get("status")
    try:
        limit = int(req.query.get("limit", "50"))
    except ValueError:
        limit = 50
    rows = engine.list(limit=max(1, min(limit, 500)))
    if status:
        rows = [row for row in rows if row.get('status') == status]
    slim = [{k: t.get(k) for k in ("id", "goal", "kind", "status", "priority",
                                   "current_step", "error", "created_at", "updated_at")}
            | {"steps_total": len(t.get("steps", [])),
               "steps_done": sum(1 for s in t.get("steps", []) if s.get("status") == "SUCCESS")}
            for t in rows if t]
    return web.json_response({"tasks": slim})


async def api_tasks_get(req: web.Request) -> web.Response:
    engine = getattr(hub, "task_engine", None)
    if not engine:
        return web.json_response({"ok": False, "error": "task engine unavailable"}, status=503)
    t = engine.get(req.match_info["id"])
    if not t:
        return web.json_response({"ok": False, "error": "no such task"}, status=404)
    return web.json_response(t)


async def api_tasks_create(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400)
    goal = str(body.get("goal", "")).strip()
    if not goal:
        return web.json_response({"ok": False, "error": "empty goal"}, status=400)
    sup = getattr(hub, "supervisor", None)
    if not sup:
        return web.json_response({"ok": False, "error": "supervisor unavailable"}, status=503)
    budgets = body.get("budgets") or {}
    task = await sup.submit(goal, budgets=budgets, spawn=True)
    return web.json_response({"ok": True, "task_id": task["id"], "status": task["status"]})


async def api_tasks_cancel(req: web.Request) -> web.Response:
    engine = getattr(hub, "task_engine", None)
    if not engine:
        return web.json_response({"ok": False, "error": "task engine unavailable"}, status=503)
    res = engine.cancel(req.match_info["id"])
    return web.json_response(res, status=200 if res.get("ok") else 400)


async def api_tasks_pause(req: web.Request) -> web.Response:
    engine = getattr(hub, "task_engine", None)
    if not engine:
        return web.json_response({"ok": False, "error": "task engine unavailable"}, status=503)
    res = engine.pause(req.match_info["id"])
    return web.json_response(res, status=200 if res.get("ok") else 400)


async def api_tasks_approve(req: web.Request) -> web.Response:
    """Server-side approval for a task waiting in WAITING_APPROVAL, then resume."""
    engine = getattr(hub, "task_engine", None)
    sup = getattr(hub, "supervisor", None)
    if not engine:
        return web.json_response({"ok": False, "error": "task engine unavailable"}, status=503)
    res = engine.approve(req.match_info["id"])
    if res.get("ok") and sup:
        t = engine.get(req.match_info["id"])
        if t and t.get("kind") == "supervisor":
            engine.spawn(t["id"], sup._runner)
        hub.audit.write("TASK_APPROVE", req.match_info["id"])
    return web.json_response(res, status=200 if res.get("ok") else 400)


async def api_world(_req: web.Request) -> web.Response:
    world = getattr(hub, "world", None)
    if not world:
        return web.json_response({"ok": False, "error": "world model unavailable"}, status=503)
    snap = world.snapshot()
    snap["llm_context"] = world.context_for_llm()
    return web.json_response(snap)


async def api_models_health(_req: web.Request) -> web.Response:
    rt = _rt()
    if not rt:
        return web.json_response({"ok": False, "error": "runtime unavailable"}, status=503)
    return web.json_response({
        "configured": rt.brain.model,
        "installed": hub.ai_status.get("models", []),
        "router_health": rt.router.health()})


# ---------------- WebSocket ----------------
async def ws_handler(req: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=15)
    await ws.prepare(req)
    hub.clients.add(ws)
    try:
        await ws.send_json({"type": "hello", **hub.snapshot_all()})
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception:
                    continue
                if data.get("type") == "voice_report":
                    hub.tools.report_voice(bool(data.get("available")), str(data.get("detail", "")))
                    await hub.broadcast_tools()
                elif data.get("type") == "mic":
                    active = bool(data.get("active"))
                    if active and hub.agent.state == "IDLE":
                        await hub.agent.set_state("LISTENING", "Microphone active")
                    elif not active and hub.agent.state == "LISTENING":
                        await hub.agent.set_state("IDLE")
                elif data.get("type") == "tts" and hub.bridge:
                    # client TTS activity feeds the barge-in detector
                    if bool(data.get("active")):
                        hub.bridge.voice_stack.tts_start()
                    else:
                        hub.bridge.voice_stack.tts_stop()
            elif msg.type == web.WSMsgType.ERROR:
                break
    finally:
        hub.clients.discard(ws)
    return ws


# ---------------- background loops ----------------
async def telemetry_loop(_app: web.Application) -> None:
    while True:
        await asyncio.sleep(2)
        await hub.broadcast({"type": "system", "data": hub.telemetry.snapshot()})
        await hub.broadcast({"type": "memory", "data": hub.memory.status()})


async def ollama_loop(_app: web.Application) -> None:
    while True:
        res = await hub.check_ollama()
        await hub.broadcast({"type": "ai", "data": res["status"]})
        await hub.broadcast_tools()
        if res["changed"]:
            if res["status"]["connected"]:
                hub.notifier.notify("ollama", f"Ollama connected · {OLLAMA_HOST}", "success", force=True)
            else:
                hub.notifier.notify("ollama", "Ollama connection lost", "error", force=True)
                if hub.bridge:  # CRITICAL severity → spoken (policy cooldown applies)
                    hub.bridge.policy.handle("ollama", "Ollama connection lost", "error")
        await asyncio.sleep(10)


async def on_startup(app: web.Application) -> None:
    await hub.telemetry.start()
    first = await hub.check_ollama()
    hub.ai_status = first["status"]
    # V16 runtime behind the V15.1 API/WS layer
    hub.loop = asyncio.get_running_loop()
    hub.bridge = UltronBridge(hub, os.path.join(BASE, "config", "settings.json"), asyncio.get_running_loop())
    if hub.bridge.available:
        hub.audit.extra_values_fn = hub.bridge.runtime.vault.all_values
        hub.agent.fallback = hub.bridge.run  # GENERAL_CONVERSATION → Ollama
        hub.agent.vision_check = hub.bridge.is_vision_flow  # screenshot→LLaVA pipeline
        hub.agent.composite = hub.bridge.run_orchestrated  # Agent 2.0 planner
        if os.environ.get("MARK_AUDIO_OWNER") != "mark":
            hub.bridge.start_proactive()
        # ── Wake-word otomatik başlatma ───────────────────────────────────
        # config'de live_voice_auto_start: true ise başlar (varsayılan: true)
        auto_start = hub.bridge.runtime.settings.get("live_voice_auto_start", True) and os.environ.get("MARK_AUDIO_OWNER") != "mark"
        if auto_start:
            import asyncio as _aio
            async def _delayed_wake_start():
                await _aio.sleep(2.0)  # backend tamamen hazır olsun
                try:
                    result = hub.bridge.start_live_voice_wake()
                    if result.get("ok"):
                        await hub.on_activity("Wake-word dinleme başladı (ULTRON de...)", "info")
                    else:
                        err = result.get("error", "bilinmeyen")
                        if "sounddevice" in err.lower() or "faster" in err.lower() or "portaudio" in err.lower():
                            await hub.on_activity(f"Wake-word: ses bağımlılıkları eksik ({err[:60]}). Frontend'den başlatabilirsiniz.", "warn")
                        else:
                            await hub.on_activity(f"Wake-word başlatılamadı: {err}", "warn")
                except Exception as exc:
                    await hub.on_activity(f"Wake-word başlatma hatası: {exc}", "error")
            _aio.create_task(_delayed_wake_start())
        await hub.notify("V16 runtime online (agent/memory/audit/proactive).", "success")
    else:
        await hub.notify(f"V16 runtime unavailable: {hub.bridge.error}", "error")
    await hub.on_activity("ULTRON backend online", "success")
    await hub.notify("System is running smoothly.", "success")
    if not first["status"]["connected"]:
        await hub.notify(f"Ollama offline at {OLLAMA_HOST}", "warn")
    # V2.1 startup health check
    hub.health = build_health(
        stack=(hub.bridge.voice_stack if hub.bridge else None),
        runtime=(hub.bridge.runtime if hub.bridge and hub.bridge.available else None),
        ollama_connected=first["status"]["connected"],
        persona_mode=(hub.bridge.runtime.settings.get("persona_guard_mode", "reframe")
                      if hub.bridge and hub.bridge.available else "reframe"),
        db_paths=[os.path.join(BASE, "data", "metrics", "voice_metrics.db"),
                  os.path.join(BASE, "data", "memory", "ultron.db"),
                  os.path.join(BASE, "data", "metrics", "persona_drift.db")])
    # Phase-4: voiceprint config + sovereign audit + sentinel loop
    if hub.bridge and hub.bridge.available:
        st0 = hub.bridge.runtime.settings
        hub.voiceprint.enabled = bool(st0.get("voiceprint_lock_enabled", False))
        hub.voiceprint.threshold = float(st0.get("voiceprint_threshold", 0.75))
    from app.security import sovereign_privacy as sov
    import importlib.util as _iu
    from health import tts_backend_name
    sova = sov.audit(OLLAMA_HOST, tts_backend_name(),
                     _iu.find_spec("faster_whisper") is not None, first["status"]["connected"])
    hub.health["sovereign"] = sova
    hub.health["sovereign_status"] = sov.sovereign_status(sova)
    log_health(hub.health)
    # Phase-8: backup engine + boot doctor
    hub.backup = BackupEngine(
        root=os.path.join(BASE, "backups"),
        sources=[
            ("memory/ultron.db", os.path.join(BASE, "data", "memory", "ultron.db")),
            ("dna/user_dna.db", os.path.join(BASE, "data", "dna", "user_dna.db")),
            ("metrics/voice_metrics.db", os.path.join(BASE, "data", "metrics", "voice_metrics.db")),
            ("metrics/persona_drift.db", os.path.join(BASE, "data", "metrics", "persona_drift.db")),
            ("master_rules.json", os.path.join(BASE, "config", "security", "master_rules.json")),
            ("settings.json", os.path.join(BASE, "config", "settings.json")),
        ])
    hub.last_doctor = doctor_mod.run_doctor(
        {"ollama_host": OLLAMA_HOST,
         "db_paths": [os.path.join(BASE, "data", "memory", "ultron.db")],
         "rules_path": os.path.join(BASE, "config", "security", "master_rules.json")},
        persona=(hub.bridge.runtime.agent.persona if (hub.bridge and hub.bridge.available) else None))
    print(f"[ULTRON-DOCTOR] overall={hub.last_doctor['overall']} :: {hub.last_doctor['summary']}", flush=True)
    # Phase-9: dual-brain mesh
    from app.mesh.dual_node_engine import NodeRegistry
    from app.mesh.mesh_sync import MeshSync
    hub.mesh_registry = NodeRegistry()
    hub.mesh_sync = MeshSync(hub.bridge.runtime.memory, hub.dna, hub.rules)
    # Phase-10: IoT Nexus + scenes
    from app.iot.iot_nexus import IoTNexus
    from app.iot.scenes_engine import ScenesEngine
    hub.iot = IoTNexus(db_path=os.path.join(BASE, "data", "iot", "iot_devices.db"),
                       ha_url=os.environ.get("ULTRON_HA_URL"),
                       vault=(hub.bridge.runtime.vault
                              if (hub.bridge and hub.bridge.available) else None))
    hub.scenes = ScenesEngine(hub.iot, sentinel=hub.sentinel,
                              persona=(hub.bridge.runtime.agent.persona
                                       if (hub.bridge and hub.bridge.available) else None))
    # Phase-11: room presence & welcome
    from app.presence.room_presence import RoomPresence

    def _presence_speak(text: str) -> None:
        asyncio.run_coroutine_threadsafe(
            hub.broadcast({"type": "proactive_speech", "text": text}), hub.loop)

    hub.presence = RoomPresence(scenes=hub.scenes, speak_cb=_presence_speak,
                                persona=(hub.bridge.runtime.agent.persona
                                         if (hub.bridge and hub.bridge.available) else None))
    from app.personal.workspace_sentinel import BREAK_LINE
    import threading as _th
    hub.sentinel.on_break = (lambda m: asyncio.run_coroutine_threadsafe(
        hub.notify(BREAK_LINE.format(min=m), "warn"), hub.loop))
    _th.Thread(target=_sentinel_loop, daemon=True).start()
    # Phase-5: smart screen watcher (default OFF, privacy-first)
    from app.vision.smart_screen_watcher import SmartScreenWatcher, DEFAULT_TARGETS, DEFAULT_BLACKLIST
    from app.vision.visual_context_engine import VisualContextEngine
    from app.vision.vision_control import VisionControl
    stv = hub.bridge.runtime.settings if (hub.bridge and hub.bridge.available) else {}
    hub.watcher = SmartScreenWatcher(
        title_fn=lambda: hub.sentinel.title,
        enabled=bool(stv.get("vision_enabled", False)),
        targets=stv.get("vision_targets", DEFAULT_TARGETS),
        blacklist=stv.get("vision_blacklist", DEFAULT_BLACKLIST))
    hub.vision_engine = VisualContextEngine(
        policy=(hub.bridge.policy if hub.bridge else None),
        persona=(hub.bridge.runtime.agent.persona if (hub.bridge and hub.bridge.available) else None))
    hub.watcher.on_change = hub.vision_engine.on_change
    hub.vision_control = VisionControl(hub.watcher, hub.vision_engine,
                                       enabled_default=bool(stv.get("vision_enabled", False)))
    _th.Thread(target=hub.watcher.loop,
               kwargs={"idle_fn": lambda: hub.sentinel.mode == "IDLE_MODE"},
               daemon=True).start()
    # PHASE 2/3: long-running task engine + supervisor agent + recovery
    from app.tasks.engine import TaskEngine
    from app.agent.supervisor import (
        CodeAnalysisWorker, DiagnosticWorker, ReportWorker,
        SupervisorAgent, TestWorker, VerificationWorker,
    )
    hub.task_engine = TaskEngine(db_path=os.path.join(BASE, "data", "tasks", "tasks.db"))

    def _task_event(ev: dict) -> None:
        try:
            asyncio.get_event_loop().create_task(hub._task_event(ev))
        except RuntimeError:
            pass

    hub.task_engine.event_cb = _task_event
    workers = {
        "code_analysis": CodeAnalysisWorker(hub.code_intel),
        "tests": TestWorker(Path(os.path.dirname(BASE))),
        "verification": VerificationWorker(),
        "report": ReportWorker(
            router=(hub.bridge.runtime.router if hub.bridge and hub.bridge.available else None),
            llm_available=hub.bridge_available_llm),
    }
    if hub.bridge and hub.bridge.available:
        workers["diagnostic"] = DiagnosticWorker(hub.bridge.runtime)
    hub.supervisor = SupervisorAgent(hub.task_engine, workers, event_cb=_task_event)
    recovered = hub.task_engine.recover_incomplete()
    for tid in recovered:
        t = hub.task_engine.get(tid)
        if t and t.get("kind") == "supervisor":
            hub.task_engine.spawn(tid, hub.supervisor._runner)
            await hub.on_activity(f"Task {tid} recovered and resumed", "info")
    # PHASE 4: World Model — live environment state (current, not historical)
    from app.world.model import WorldModel

    def _world_apps():
        try:
            import pygetwindow as gw
            titles = [t for t in gw.getAllTitles() if t][:20]
            return {"available": True, "titles": titles}
        except Exception:
            return {"available": False}

    def _world_screen():
        try:
            st = hub.watcher  # may not exist on headless; degrade below
            base = {"available": True, "status": st.status()["status"],
                    "diff": st.last_diff, "analyses": st.analyses}
        except Exception:
            base = {"available": False}
        try:
            logs = Path(BASE) / "data" / "logs"
            shots = sorted(logs.glob("screen_*.png"), key=lambda x: x.stat().st_mtime,
                           reverse=True) if logs.exists() else []
            if shots:
                base["age_s"] = max(0.0, time.time() - shots[0].stat().st_mtime)
        except Exception:
            pass
        return base

    def _world_task():
        try:
            for t in hub.task_engine.list(limit=20):
                if t and t.get("status") in ("RUNNING", "WAITING_APPROVAL", "RECOVERING"):
                    return {"available": True, "goal": t["goal"], "status": t["status"],
                            "current_step": t["current_step"], "steps_total": len(t["steps"])}
        except Exception:
            pass
        return {"available": False}

    def _world_files():
        try:
            root = Path(os.path.dirname(BASE))
            cands = []
            for p in root.rglob("*"):
                if not p.is_file():
                    continue
                if any(part in (".git", "node_modules", "data", "__pycache__", "dist",
                                ".venv", "backups") for part in p.parts):
                    continue
                if p.suffix not in (".py", ".ts", ".tsx", ".json", ".md", ".bat"):
                    continue
                cands.append(p)
            cands.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return {"available": True, "files": [str(c.relative_to(root)) for c in cands[:5]]}
        except Exception:
            return {"available": False}

    def _world_iot():
        try:
            devices = hub.iot.list()
            return {"available": True, "devices": len(devices),
                    "active": sum(1 for d in devices if d["state"] == "on"),
                    "last_scene": hub.scenes.last_scene}
        except Exception:
            return {"available": False}

    def _world_events():
        try:
            latest = hub.notifications[0]["text"] if hub.notifications else None
            return {"available": True, "latest": latest}
        except Exception:
            return {"available": False}

    hub.world = WorldModel(sources={
        "presence": lambda: (hub.presence.status() | {"confidence": getattr(hub.presence, "last_confidence", None)}
                             if getattr(hub, "presence", None) else {"available": False}),
        "workspace": lambda: hub.sentinel.state() if getattr(hub, "sentinel", None) else {"available": False},
        "screen": _world_screen,
        "task": _world_task,
        "system": lambda: get_system_stats_dict(),
        "apps": _world_apps,
        "files": _world_files,
        "iot": _world_iot,
        "events": _world_events,
    })
    if hub.bridge and hub.bridge.available:
        hub.bridge.runtime.world_context_fn = hub.world.context_for_llm

    # Phase-6: Master HUD collector
    from app.observability.master_hud import MasterHUDCollector
    from app.security import sovereign_privacy as _sov
    hub.hud = MasterHUDCollector(
        health_fn=lambda: hub.health,
        metrics_store=(hub.bridge.metrics_store if hub.bridge else None),
        persona=(hub.bridge.runtime.agent.persona if (hub.bridge and hub.bridge.available) else None),
        voiceprint=hub.voiceprint,
        sentinel=hub.sentinel,
        vision_engine=getattr(hub, "vision_engine", None),
        dna=hub.dna,
        memory=(hub.bridge.runtime.memory if (hub.bridge and hub.bridge.available) else None),
        audit=hub.audit,
        sovereign_fn=lambda: _sov.audit(OLLAMA_HOST, None, False,
                                        hub.ai_status.get("connected", False)),
        emotion_fn=lambda: (hub.bridge.runtime.emotion_log.history(24)
                            if (hub.bridge and hub.bridge.available) else {}),
        memory_health_fn=lambda: (hub.bridge.runtime.semv2.stats()
                                  if (hub.bridge and hub.bridge.available) else {}),
        doctor_fn=lambda: hub.last_doctor,
        backup_fn=lambda: (hub.backup.list()[-1] if hub.backup.list() else None),
        mesh_fn=lambda: {"nodes": hub.mesh_registry.status(),
                         "pc_online": hub.mesh_registry.pc_online(),
                         "mobile_online": hub.mesh_registry.mobile_online(),
                         "last_sync": hub.mesh_sync.last_sync_ts},
        iot_fn=lambda: {
            "devices": len(hub.iot.list()),
            "active": sum(1 for d in hub.iot.list() if d["state"] == "on"),
            "last_scene": hub.scenes.last_scene},
        presence_fn=lambda: hub.presence.status())
    app["loops"] = [asyncio.create_task(telemetry_loop(app)), asyncio.create_task(ollama_loop(app))]


def _sentinel_loop() -> None:
    import time as _t
    while True:
        try:
            hub.sentinel.sample()
        except Exception:
            pass
        _t.sleep(30)


async def on_shutdown(app: web.Application) -> None:
    # Close persistent clients before aiohttp waits for active request handlers.
    await asyncio.gather(*(ws.close(code=1001, message=b'ULTRON shutdown')
                           for ws in list(hub.clients)), return_exceptions=True)


async def on_cleanup(app: web.Application) -> None:
    for t in app.get("loops", []):
        t.cancel()
    if hub.bridge:
        try:
            hub.bridge.runtime.shutdown()
        except Exception:
            pass
        hub.bridge.stop()
    await hub.telemetry.stop()


@web.middleware
async def auth_middleware(req: web.Request, handler):
    # PHASE 10: per-IP rate limit (auth handshake daha sıkı)
    client_ip = req.remote or "unknown"
    _tok = req.headers.get("Authorization", "").replace("Bearer ", "").strip()
    allowed, retry_after = hub.rate_limiter.check(
        client_ip, req.path, authenticated=bool(_tok) and _tok in hub.auth.sessions)
    if not allowed:
        return web.json_response(
            {"ok": False, "error": "rate limit aşıldı"},
            status=429, headers={"Retry-After": str(max(1, int(retry_after) + 1))})
    if hub.auth.required and (req.path.startswith("/api/") or req.path == "/ws"):
        if req.path != "/api/auth/handshake":
            token = req.headers.get("Authorization", "").replace("Bearer ", "").strip()
            if not token and req.path == "/ws":
                token = req.query.get("token", "").strip()  # browsers can't set WS headers
            if not hub.auth.valid(token or None):
                return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
    return await handler(req)


@web.middleware
async def cors_middleware(req: web.Request, handler):
    # Secure default: no wildcard. Same-origin clients (vite proxy) need nothing.
    # Cross-origin access only via explicit ULTRON_CORS_ORIGINS comma-list.
    if req.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(req)
    allowed = os.environ.get("ULTRON_CORS_ORIGINS", "")
    origin = req.headers.get("Origin", "")
    if allowed and origin and origin in [o.strip() for o in allowed.split(",") if o.strip()]:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp


def main() -> None:
    os.chdir(BASE)  # V16 relative data paths (data/memory, data/logs, data/vault)
    app = web.Application(middlewares=[auth_middleware, cors_middleware], client_max_size=12*1024*1024)
    from merged_api import install
    install(app, hub)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.on_cleanup.append(on_cleanup)
    app.router.add_get("/api/system", api_system)
    app.router.add_get("/api/ai", api_ai)
    app.router.add_get("/api/tools", api_tools)
    app.router.add_get("/api/memory", api_memory)
    app.router.add_get("/api/audit", api_audit)
    app.router.add_post("/api/voice/ptt", api_voice_ptt)
    app.router.add_get("/api/capabilities", api_capabilities)
    app.router.add_post("/api/capabilities", api_capabilities)
    app.router.add_post("/api/voice/live", api_voice_live)
    app.router.add_get("/api/voice/metrics", api_voice_metrics)
    app.router.add_get("/api/voice/metrics/history", api_voice_metrics_history)
    app.router.add_get("/api/system/health", api_system_health)
    app.router.add_post("/api/config/reload", api_config_reload)
    app.router.add_post("/api/security/voiceprint/enroll", api_voiceprint_enroll)
    app.router.add_post("/api/security/voiceprint/verify", api_voiceprint_verify)
    app.router.add_get("/api/master/profile", api_master_profile)
    app.router.add_get("/api/master/dna/insights", api_master_insights)
    app.router.add_get("/api/workspace/state", api_workspace_state)
    app.router.add_get("/api/sovereign/audit", api_sovereign_audit)
    app.router.add_post("/api/vision/toggle", api_vision_toggle)
    app.router.add_get("/api/vision/status", api_vision_status)
    app.router.add_post("/api/vision/scan_now", api_vision_scan_now)
    app.router.add_get("/api/hud/overview", api_hud_overview)
    app.router.add_get("/api/hud/audit/recent", api_hud_audit_recent)
    app.router.add_get("/api/hud/persona/trends", api_hud_persona_trends)
    app.router.add_post("/api/hud/self_diagnostic", api_hud_self_diagnostic)
    app.router.add_get("/api/system/doctor", api_system_doctor)
    app.router.add_post("/api/mesh/handshake", api_mesh_handshake)
    app.router.add_post("/api/mesh/sync/push", api_mesh_push)
    app.router.add_get("/api/mesh/sync/pull", api_mesh_pull)
    app.router.add_get("/api/mesh/nodes", api_mesh_nodes)
    app.router.add_post("/api/mesh/heartbeat", api_mesh_heartbeat)
    app.router.add_get("/api/iot/devices", api_iot_devices)
    app.router.add_post("/api/iot/device/control", api_iot_control)
    app.router.add_post("/api/iot/scene/activate", api_iot_scene)
    app.router.add_post("/api/iot/discover", api_iot_discover)
    app.router.add_post("/api/presence/ping", api_presence_ping)
    app.router.add_get("/api/presence/status", api_presence_status)
    app.router.add_get("/api/ui/theme", api_ui_theme_get)
    app.router.add_post("/api/ui/theme", api_ui_theme_post)
    app.router.add_post("/api/tts/speak", api_tts_speak)
    app.router.add_get("/api/tts/status", api_tts_status)
    app.router.add_post("/api/system/backup/create", api_backup_create)
    app.router.add_get("/api/system/backup/list", api_backup_list)
    app.router.add_post("/api/system/backup/restore", api_backup_restore)
    app.router.add_post("/api/emotion/analyze", api_emotion_analyze)
    app.router.add_get("/api/emotion/history", api_emotion_history)
    app.router.add_get("/api/memory/stats", api_memory_stats)
    app.router.add_post("/api/memory/decay/run", api_memory_decay_run)
    app.router.add_get("/api/memory/export", api_memory_export)
    app.router.add_post("/api/memory/import", api_memory_import)
    app.router.add_get("/api/stage", api_stage_get)
    app.router.add_post("/api/stage/model", api_stage_model_upload)
    app.router.add_get("/api/stage/models", api_stage_models_list)
    app.router.add_post("/api/stage/model/delete", api_stage_model_delete)
    app.router.add_get("/api/stage/model/{model_id}", api_stage_model_get)
    app.router.add_post("/api/stage/command", api_stage_command)
    app.router.add_post("/api/stage/control", api_stage_control)
    app.router.add_post("/api/stage/video-ready", api_stage_video_ready)

    app.router.add_get("/api/activity", api_activity)
    app.router.add_get("/api/notifications", api_notifications)
    app.router.add_get("/api/config", api_config)
    app.router.add_get("/api/agent", api_agent_state)
    app.router.add_post("/api/agent/command", api_command)
    app.router.add_post("/api/tools/voice", api_voice_report)
    app.router.add_post("/api/actions/screenshot", api_action_screenshot)
    app.router.add_post("/api/actions/browser", api_action_browser)
    app.router.add_post("/api/actions/system-check", api_action_system_check)
    app.router.add_post("/api/actions/clear-memory", api_action_clear_memory)
    app.router.add_post("/api/codeintel/analyze", api_codeintel_analyze)
    app.router.add_get("/api/codeintel/explain", api_codeintel_explain)
    app.router.add_post("/api/codegen/propose", api_codegen_propose)
    app.router.add_post("/api/codegen/apply", api_codegen_apply)
    app.router.add_post("/api/codegen/reject", api_codegen_reject)
    app.router.add_get("/api/codegen/pending", api_codegen_pending)
    app.router.add_post("/api/tests/run", api_tests_run)
    app.router.add_get("/api/memory/v16", api_memory_v16)
    app.router.add_post("/api/memory/v16/add", api_memory_v16_add)
    app.router.add_post("/api/memory/v16/delete", api_memory_v16_delete)
    app.router.add_post("/api/memory/v16/clear", api_memory_v16_clear)
    app.router.add_get("/api/memory/v16/search", api_memory_v16_search)
    app.router.add_get("/api/task/pending", api_task_pending)
    app.router.add_post("/api/task/approve", api_task_approve)
    app.router.add_post("/api/task/reject", api_task_reject)
    app.router.add_post("/api/auth/handshake", api_auth_handshake)
    app.router.add_get("/api/auth/devices", api_auth_devices)
    app.router.add_get("/api/vision/last", api_vision_last)
    app.router.add_get("/api/vision/preview", api_vision_preview)
    app.router.add_get("/api/tasks", api_tasks_list)
    app.router.add_post("/api/tasks", api_tasks_create)
    app.router.add_get("/api/tasks/{id}", api_tasks_get)
    app.router.add_post("/api/tasks/{id}/cancel", api_tasks_cancel)
    app.router.add_post("/api/tasks/{id}/pause", api_tasks_pause)
    app.router.add_post("/api/tasks/{id}/approve", api_tasks_approve)
    app.router.add_get("/api/models/health", api_models_health)
    app.router.add_get("/api/world", api_world)
    app.router.add_get("/api/vault", api_vault_list)
    app.router.add_get("/api/skills", api_skills)
    app.router.add_get("/api/voice/wake", api_wake_status)
    app.router.add_get("/api/connectors/health", api_connectors_health)
    app.router.add_post("/api/vault/set", api_vault_set)
    app.router.add_post("/api/vault/delete", api_vault_delete)
    app.router.add_get("/ws", ws_handler)
    port = int(os.environ.get("ULTRON_PORT", "8000"))
    bind_host = os.environ.get("ULTRON_BIND_HOST", "127.0.0.1")
    if bind_host not in {"127.0.0.1", "localhost", "::1"} and not hub.auth.required:
        raise RuntimeError("ULTRON_BIND_HOST is non-local but ULTRON_AUTH is disabled. Enable ULTRON_AUTH=1 before exposing ULTRON to a network.")
    web.run_app(app, host=bind_host, port=port, print=lambda *_: None)


if __name__ == "__main__":
    main()
