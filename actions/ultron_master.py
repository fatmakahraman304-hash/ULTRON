"""JARVIS-class master control surface for ULTRON.

This action exposes the advanced backend that already ships with the merged
project to the desktop/phone Gemini Live agent. It intentionally routes through
the authenticated local backend instead of duplicating state in the voice
process.

Privacy-sensitive capabilities (continuous vision) are explicit operations.
Destructive restore/clear/delete operations are intentionally NOT exposed here.
"""
from __future__ import annotations

import json
from typing import Any

from integration.bridge import Bridge


def _bridge() -> Bridge:
    return Bridge()


def _ok(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def ultron_master(parameters: dict, **_ctx) -> str:
    op = str(parameters.get("operation", "")).strip().lower()
    query = str(parameters.get("query", "") or "").strip()
    target = str(parameters.get("target", "") or "").strip()
    action = str(parameters.get("action", "") or "").strip().lower()
    value = parameters.get("value")
    b = _bridge()

    # Read-only situational awareness / diagnostics.
    get_routes = {
        "overview": "/api/hud/overview",
        "world": "/api/world",
        "capabilities": "/api/capabilities",
        "skills": "/api/skills",
        "activity": "/api/activity",
        "notifications": "/api/notifications",
        "vision_status": "/api/vision/status",
        "iot_list": "/api/iot/devices",
        "presence_status": "/api/presence/status",
        "tasks": "/api/tasks?limit=30",
        "models": "/api/models/health",
        "security_audit": "/api/sovereign/audit",
        "workspace": "/api/workspace/state",
        "memory_stats": "/api/memory/stats",
        "connectors": "/api/connectors/health",
        "backup_list": "/api/system/backup/list",
        "doctor": "/api/system/doctor",
    }
    if op in get_routes:
        return _ok(b.request(get_routes[op], timeout=45))

    # Safe active operations.
    if op == "self_diagnostic":
        return _ok(b.request("/api/hud/self_diagnostic", {}, timeout=90))
    if op == "vision_scan":
        return _ok(b.request("/api/vision/scan_now", {}, timeout=45))
    if op in {"vision_enable", "vision_disable"}:
        return _ok(b.request(
            "/api/vision/toggle",
            {"enabled": op == "vision_enable"},
            timeout=30,
        ))
    if op == "iot_discover":
        return _ok(b.request("/api/iot/discover", {}, timeout=45))
    if op == "presence_ping":
        return _ok(b.request(
            "/api/presence/ping",
            {"source": query or "voice", "device_id": target or "ultron-voice"},
            timeout=30,
        ))
    if op == "backup_create":
        return _ok(b.request("/api/system/backup/create", {}, timeout=120))

    # Physical-world IoT effects. The model must only call these when the user
    # explicitly asks for the device/scene change.
    if op == "iot_control":
        if not target or action not in {"turn_on", "turn_off", "toggle", "set_value"}:
            return _ok({
                "ok": False,
                "error": "iot_control requires target=device_id and action=turn_on|turn_off|toggle|set_value",
            })
        return _ok(b.request(
            "/api/iot/device/control",
            {"device_id": target, "action": action, "value": value},
            timeout=30,
        ))
    if op == "iot_scene":
        if not target:
            return _ok({"ok": False, "error": "iot_scene requires target=scene_name"})
        return _ok(b.request(
            "/api/iot/scene/activate",
            {"scene_name": target},
            timeout=45,
        ))

    # Long-running supervisor work. Existing backend safety/approval boundaries
    # remain authoritative; this call cannot self-approve dangerous work.
    if op == "long_task":
        goal = query or target
        if not goal:
            return _ok({"ok": False, "error": "long_task requires query"})
        return _ok(b.request(
            "/api/tasks",
            {"goal": goal, "budgets": {}},
            timeout=45,
        ))

    # Deep local agent/planner path. Approval remains server-owned.
    if op == "agent":
        text = query or target
        if not text:
            return _ok({"ok": False, "error": "agent requires query"})
        return _ok(b.ask(text, "agent"))

    if op == "deep_task":
        text = query or target
        if not text:
            return _ok({"ok": False, "error": "deep_task requires query"})
        return _ok(b.ask(text, "task"))

    if op == "multi_reason":
        text = query or target
        if not text:
            return _ok({"ok": False, "error": "multi_reason requires query"})
        return _ok(b.ask(text, "multi"))

    return _ok({
        "ok": False,
        "error": f"unknown operation: {op}",
        "supported": [
            "overview", "world", "capabilities", "skills", "activity",
            "notifications", "doctor", "self_diagnostic", "workspace",
            "models", "security_audit", "memory_stats", "connectors",
            "vision_status", "vision_scan", "vision_enable", "vision_disable",
            "iot_list", "iot_discover", "iot_control", "iot_scene",
            "presence_status", "presence_ping", "backup_create", "backup_list",
            "tasks", "long_task", "agent", "deep_task", "multi_reason",
        ],
    })


TOOL = {
    "name": "ultron_master",
    "description": (
        "JARVIS-class ULTRON master control. Use for whole-system awareness, "
        "world/context status, self-diagnostics, capability/skill discovery, "
        "continuous screen-awareness controls, IoT/smart-home discovery and "
        "explicit device/scene control, presence, backups, long-running "
        "supervisor jobs, deep local agent work, multi-model reasoning, model "
        "health, security/privacy audit, memory/workspace/connectors status. "
        "Use this instead of merely describing a JARVIS-like action when the "
        "requested operation is listed here. Continuous vision must only be "
        "enabled when the user explicitly requests it. iot_control/iot_scene "
        "must only be used for an explicit user request to change that device "
        "or scene; never infer a physical-world change."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "enum": [
                    "overview", "world", "capabilities", "skills", "activity",
                    "notifications", "doctor", "self_diagnostic", "workspace",
                    "models", "security_audit", "memory_stats", "connectors",
                    "vision_status", "vision_scan", "vision_enable", "vision_disable",
                    "iot_list", "iot_discover", "iot_control", "iot_scene",
                    "presence_status", "presence_ping", "backup_create", "backup_list",
                    "tasks", "long_task", "agent", "deep_task", "multi_reason"
                ],
            },
            "query": {
                "type": "STRING",
                "description": "Goal/request for agent, task or reasoning operations.",
            },
            "target": {
                "type": "STRING",
                "description": "Device id, scene name or optional target depending on operation.",
            },
            "action": {
                "type": "STRING",
                "description": "For iot_control: turn_on, turn_off, toggle or set_value.",
            },
            "value": {
                "type": "NUMBER",
                "description": "Optional numeric IoT value such as temperature or brightness.",
            },
        },
        "required": ["operation"],
    },
    "handler": ultron_master,
}
