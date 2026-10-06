"""Voice/tool bridge for the dynamic ULTRON Center Stage."""
from __future__ import annotations

import json
from typing import Any

from integration.bridge import Bridge


def _num(value: Any):
    return value if isinstance(value, (int, float)) else None


def ultron_stage(parameters: dict, **_ctx) -> str:
    operation = str(parameters.get("operation", "")).strip().lower()
    if not operation:
        return json.dumps({"ok": False, "error": "operation required"}, ensure_ascii=False)

    body: dict[str, Any] = {"operation": operation}
    for key in ("kind", "color", "label", "template", "title", "subtitle"):
        value = parameters.get(key)
        if value not in (None, ""):
            body[key] = str(value)

    for key in ("glow", "speed", "scale", "opacity", "duration", "progress"):
        value = _num(parameters.get(key))
        if value is not None:
            body[key] = value

    for key in ("rings", "particles"):
        value = parameters.get(key)
        if value is not None:
            try:
                body[key] = int(value)
            except Exception:
                pass

    for key in ("wireframe", "pulse"):
        value = parameters.get(key)
        if isinstance(value, bool):
            body[key] = value

    bridge = Bridge()
    try:
        if operation == "status":
            result = bridge.request("/api/stage", timeout=20)
        else:
            result = bridge.request("/api/stage/command", body, timeout=30)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps(
            {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
            ensure_ascii=False,
        )


TOOL = {
    "name": "ultron_stage",
    "description": (
        "Control the main visual Center Stage in the ULTRON desktop UI. Use it "
        "whenever the user asks to create/show/control a hologram, create a short "
        "animation video, convert the current hologram into a video, play/pause "
        "that rendered video, reset the center area, show a screen preview, or "
        "show task progress. This tool changes the actual center UI; do not only "
        "describe the requested visual action. Hologram kinds: energy, globe, "
        "network, drone, vehicle, logo, sphere. Video templates: ultron_intro, "
        "logo_reveal, energy_core, system_activation, task_complete, "
        "hologram_capture. For 'make this bigger/brighter/faster/red' after a "
        "hologram request, use hologram_update with only the changed fields."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "enum": [
                    "status", "reset", "hologram_create", "hologram_update",
                    "video_create", "video_from_stage", "video_play",
                    "video_pause", "task_progress", "screen_preview"
                ],
            },
            "kind": {"type": "STRING"},
            "color": {"type": "STRING"},
            "label": {"type": "STRING"},
            "glow": {"type": "NUMBER"},
            "speed": {"type": "NUMBER"},
            "rings": {"type": "INTEGER"},
            "particles": {"type": "INTEGER"},
            "scale": {"type": "NUMBER"},
            "opacity": {"type": "NUMBER"},
            "wireframe": {"type": "BOOLEAN"},
            "pulse": {"type": "BOOLEAN"},
            "template": {"type": "STRING"},
            "duration": {"type": "NUMBER"},
            "title": {"type": "STRING"},
            "subtitle": {"type": "STRING"},
            "progress": {"type": "NUMBER"},
        },
        "required": ["operation"],
    },
    "handler": ultron_stage,
}
