"""Unified ULTRON capability contract for ULTRON.

This module is intentionally declarative: it describes the complete experience
we are building while distinguishing capabilities that already have a real
local implementation from adapters that still need a provider. It never
claims a capability is available merely because a UI control exists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    layer: str
    status: str
    tools: tuple[str, ...] = ()
    safety: str = "standard"
    description: str = ""


CAPABILITIES: tuple[Capability, ...] = (
    Capability("brain", "Brain / Planner / Supervisor", "core", "implemented", ("planner", "self_awareness"), description="Reasoning, planning, delegation, verification and recovery."),
    Capability("memory", "Persistent Memory", "core", "implemented", ("memory",), description="Long-term and semantic memory with auditability."),
    Capability("autonomous_tasks", "Long Tasks / Autonomous Coding", "core", "implemented", ("autonomous_task", "self_repair", "apply_code_patch"), safety="approval", description="Bounded task loops with checkpoints, tests, rollback and approval."),
    Capability("voice", "Voice / Wake Word / TTS", "input-output", "implemented", ("live_voice", "wake_word", "tts"), description="Continuous voice pipeline with local TTS options."),
    Capability("computer_control", "Computer Control", "automation", "implemented", ("gui_click", "gui_type", "gui_key", "open_application"), safety="approval", description="Mouse, keyboard and application control behind risk gates."),
    Capability("web", "Web Search / Browser Agent", "tools", "implemented", ("search_web", "browser_navigate", "browser_read", "browser_click"), safety="approval", description="Search, navigate, inspect and interact with web pages."),
    Capability("screen_vision", "Screen Vision / OCR", "vision", "implemented", ("screen", "screen_ocr"), description="Screen capture and OCR/vision analysis where local dependencies exist."),
    Capability("camera", "Camera Vision", "vision", "adapter", ("camera",), safety="permission", description="Real camera capture requires an explicit device permission and runtime backend."),
    Capability("image_generation", "Image Generation", "multimodal", "adapter", ("image_generate",), safety="provider", description="Provider-backed image generation adapter; no fake local implementation."),
    Capability("pdf", "PDF Workspace", "multimodal", "implemented", ("pdf_open", "pdf_extract", "pdf_ingest", "pdf_search"), description="Sandbox-bound PDF extraction, chunking, lexical indexing and optional scanned-PDF OCR fallback; document content is untrusted data."),
    Capability("shell", "Shell / PowerShell", "automation", "implemented", ("shell_exec",), safety="approval", description="Workspace-bounded shell execution behind server-side approval and deterministic shell policy."),
    Capability("widgets", "HUD Widgets", "ui", "implemented", ("hud_overview", "hud_trends"), description="Dockable status, memory, automation and monitoring panels."),
    Capability("hud", "ULTRON HUD", "ui", "implemented", ("hud_overview",), description="Cockpit HUD with telemetry, status, activity and operator controls."),
    Capability("three_d", "3D Interface", "ui", "implemented", ("three", "particle_sphere"), description="Three.js cockpit/particle interface and extensible 3D scene layer."),
    Capability("center_stage", "Center Stage / 3D Scene / Animation Studio", "ui", "implemented", ("ultron_stage", "three", "media_recorder"), description="Normal shaded Earth Watch plus professional 3D studio with multi-selection, named groups, batch transforms, arrays, align/distribute, parent-child Scene Graph hierarchy, camera bookmarks, persistent GLB Asset Library, visual physics, live distance measurements, diagnostics and collision-risk overlays, target tracking constraints, waypoint paths, technical render modes, timed Mission Sequences, persistent Snapshot Vault checkpoints, conditional timer/distance/collision Trigger Engine automation, links, HUD cards, motion, eased multi-object timeline/keyframes, cinematic cameras, Scene Director, named projects, screenshots, GLB export and rotatable Earth/coordinate markers/optional live ISS tracking and live Three.js WebM recording."),
    Capability("image_viewer", "Image Viewer / Drop Zone", "ui", "adapter", ("image_view",), description="Visual workspace target for generated and uploaded images."),
    Capability("notifications", "Proactive Notifications", "core", "implemented", ("proactive", "notifications"), description="Proactive monitoring and operator notifications."),
    Capability("security", "Approval / Vault / Audit / Sandbox", "security", "implemented", ("approval_gate", "vault", "audit", "sandbox"), safety="mandatory", description="Dangerous actions require trusted server-side approval; audit and rollback remain enabled."),
    Capability("world_awareness", "World Model / Situational Awareness", "cognitive", "implemented", ("world", "workspace", "presence"), description="Live model of apps, files, system, screen, tasks, devices and events."),
    Capability("research", "Research / Cross-check / Citations", "cognitive", "implemented", ("research_engine", "web_search"), description="Source-ranked research with corroboration, contradiction checks and citations."),
    Capability("predictive", "Predictive Intelligence", "cognitive", "implemented", ("predictive_engine",), description="Task duration, failure risk, anomalies, resource trends and intent prediction from measured history."),
    Capability("decision_support", "Decision / Risk / Simulation", "cognitive", "implemented", ("decision_engine", "simulation"), description="Scored decisions, reversibility/risk authority and dry-run what-if simulation."),
    Capability("goals", "Goal Intelligence", "cognitive", "implemented", ("goal_engine",), description="Persistent goals, subgoals, dependencies, blockers, deadlines and evidence-based completion."),
    Capability("knowledge", "Knowledge Engine", "cognitive", "implemented", ("knowledge_engine",), description="Document ingestion, lexical retrieval, provenance, contradiction and stale-knowledge detection."),
    Capability("context", "Context Engine", "cognitive", "implemented", ("context_engine",), description="Cross-modal working/project/temporal context with prioritization and conflict handling."),
    Capability("supervisor", "Long-running Supervisor", "agent", "implemented", ("task_engine", "supervisor"), safety="approval", description="Persistent long jobs with recovery, checkpoints, verification and approval."),
    Capability("self_diagnostics", "Self Diagnostics / Recovery", "core", "implemented", ("doctor", "self_diagnostic", "backup"), description="System health checks, backup creation and recovery-oriented diagnostics."),
    Capability("iot", "Smart Home / IoT Nexus", "automation", "implemented", ("iot", "scenes"), safety="permission", description="Real Home Assistant/HTTP devices plus explicit scene control; simulated devices are labelled."),
    Capability("presence", "Presence / Room Awareness", "cognitive", "implemented", ("presence",), safety="permission", description="Presence-aware briefings and room/device context where configured."),
    Capability("smart_screen", "Adaptive Screen Awareness", "vision", "implemented", ("smart_screen_watcher",), safety="permission", description="Privacy-first adaptive screen change detection with blacklist protection; explicit enable required."),
    Capability("communications", "Messaging / Communications", "tools", "implemented", ("send_message",), safety="approval", description="Message preparation/sending through available desktop integrations."),
    Capability("scheduling", "Reminders / Monitoring", "core", "implemented", ("reminder", "background_monitor"), description="Reminders, background topic checks and proactive notifications."),
    Capability("developer", "Developer / Code Agent", "agent", "implemented", ("dev_agent", "code_helper", "codegen", "tests"), safety="approval", description="Code analysis, generation, testing, patch proposals and bounded autonomous development."),
    Capability("cross_device", "Phone + Desktop Unified Agent", "connectivity", "implemented", ("cloud_remote", "device_presence", "shared_memory"), description="Phone voice delegates to the full desktop tool stack and receives verified results back."),
    Capability("mesh", "PC / Mobile Mesh", "connectivity", "implemented", ("mesh",), description="Authenticated device capability exchange and sync."),
)


def capability_inventory() -> list[dict]:
    """Return a stable, JSON-friendly inventory for UI/diagnostics."""
    return [asdict(item) for item in CAPABILITIES]


def capability_ids() -> tuple[str, ...]:
    return tuple(item.id for item in CAPABILITIES)


def capabilities_for_layer(layer: str) -> list[dict]:
    return [asdict(item) for item in CAPABILITIES if item.layer == layer]


def validate_inventory(items: Iterable[Capability] = CAPABILITIES) -> None:
    """Fail fast on duplicate ids or invalid lifecycle states."""
    allowed = {"implemented", "adapter", "planned"}
    seen: set[str] = set()
    for item in items:
        if item.id in seen:
            raise ValueError(f"duplicate capability id: {item.id}")
        seen.add(item.id)
        if item.status not in allowed:
            raise ValueError(f"invalid capability status: {item.status}")
        if item.safety not in {"standard", "approval", "permission", "provider", "mandatory"}:
            raise ValueError(f"invalid safety class: {item.safety}")


validate_inventory()
