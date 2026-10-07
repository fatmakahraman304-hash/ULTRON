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
    for key in ("kind", "color", "label", "template", "title", "subtitle",
                "object_id", "object_label", "camera", "layout", "preset", "animation", "objects_json",
                "motion", "axis", "theme", "keyframe_id", "cinematic", "scene_json",
                "source_id", "target_id", "source_label", "target_label", "link_id", "model_id",
                "position_json", "target_json", "hud_id", "hud_title", "hud_value", "unit",
                "project_name", "project_id", "easing", "object_ids_json", "selection_mode",
                "group_id", "group_name", "align", "parent_id", "parent_label",
                "bookmark_id", "bookmark_name", "asset_name", "physics_mode", "velocity_json"):
        value = parameters.get(key)
        if value not in (None, ""):
            body[key] = str(value)

    for key in ("glow", "speed", "scale", "opacity", "duration", "progress",
                "x", "y", "z", "rx", "ry", "rz", "spin", "explode", "time",
                "motion_speed", "radius", "amplitude", "snap", "clip_speed",
                "dx", "dy", "dz", "drx", "dry", "drz", "scale_factor",
                "spacing", "delta_time", "gravity", "bounce", "floor", "vx", "vy", "vz"):
        value = _num(parameters.get(key))
        if value is not None:
            body[key] = value

    for key in ("rings", "particles", "count"):
        value = parameters.get(key)
        if value is not None:
            try:
                body[key] = int(value)
            except Exception:
                pass

    for key in ("wireframe", "pulse", "auto_orbit", "grid", "loop", "show_labels",
                "show_trails", "audio_reactive", "visible", "locked", "clip_paused"):
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
        "animation video, record the live 3D Scene Lab canvas as a video, convert the current hologram into a video, play/pause "
        "that rendered video, save the current hologram/video, reset the center area, show a screen preview, or "
        "show task progress. This tool changes the actual center UI; do not only "
        "describe the requested visual action. Scene Lab supports multiple selectable objects and object_label can target them naturally by visible name, camera views, layouts, exploded views and animations. Hologram/scene kinds: energy, globe, "
        "network, drone, vehicle, logo, sphere, ring, tower, robot, arm, satellite, aircraft, building, ship, radar, portal, cube and persistent imported custom GLB models. For a request containing several different objects, use scene_batch once with objects_json rather than repeating scene_add. Scene Lab V4 supports multi-select, named groups, batch transforms, align/distribute, arrays/formations, parent-child hierarchy, camera bookmarks and timeline-synced camera keyframes, live drop/launch/zero-G/float physics, holographic distance measurements, a persistent GLB asset library (scene_asset_list/add/delete), duplicate, undo/redo, object motion (orbit/bob/patrol/pulse), multi-object timeline capture/editing, launch/flyby/showcase timeline presets, cinematic camera paths (orbit/flyby/topdown/hero/spiral), themes, visibility and lock. Scene camera: front, top, side, isometric, orbit, close. Layouts: line, grid, orbit. Presets: operations, vehicle_scan, drone_bay, planetary, command_center, city_scan, space_ops, robotics. Video templates: ultron_intro, "
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
                    "hologram_save", "scene_open", "scene_add", "scene_batch", "scene_load", "scene_update",
                    "scene_select", "scene_multi_select", "scene_group_create", "scene_group_select",
                    "scene_group_delete", "scene_batch_transform", "scene_align", "scene_distribute",
                    "scene_array", "scene_parent", "scene_unparent", "scene_asset_list", "scene_asset_add",
                    "scene_asset_delete", "scene_physics", "scene_measure", "scene_measure_clear",
                    "scene_remove", "scene_clear", "scene_camera",
                    "scene_camera_bookmark_save", "scene_camera_bookmark_load", "scene_camera_bookmark_delete",
                    "scene_camera_bookmark_list", "scene_arrange", "scene_preset", "scene_animation", "scene_director", "scene_save",
                    "scene_duplicate", "scene_motion", "scene_theme", "scene_undo",
                    "scene_redo", "scene_focus", "scene_camera_pose", "scene_link", "scene_unlink", "scene_clear_links", "scene_auto_link",
                    "scene_hud_add", "scene_hud_update", "scene_hud_remove", "scene_hud_clear",
                    "scene_project_save", "scene_project_list", "scene_project_load", "scene_project_delete",
                    "scene_cinematic", "scene_record", "timeline_set", "timeline_capture",
                    "timeline_capture_all", "timeline_keyframe_update", "timeline_shift",
                    "camera_keyframe_capture", "camera_keyframe_remove", "camera_track_clear",
                    "timeline_remove_keyframe", "timeline_clear", "timeline_seek",
                    "timeline_play", "timeline_pause", "timeline_preset",
                    "video_create", "video_from_stage", "video_play",
                    "video_pause", "video_save", "task_progress", "screen_preview"
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
            "object_id": {"type": "STRING"},
            "object_label": {"type": "STRING"},
            "camera": {"type": "STRING"},
            "layout": {"type": "STRING"},
            "preset": {"type": "STRING"},
            "animation": {"type": "STRING"},
            "objects_json": {"type": "STRING", "description": "JSON array for scene_batch. Each item may contain kind,label,color,x,y,z,scale,opacity,wireframe,spin,explode."},
            "scene_json": {"type": "STRING", "description": "Complete saved Scene Lab JSON object for scene_load."},
            "x": {"type": "NUMBER"},
            "y": {"type": "NUMBER"},
            "z": {"type": "NUMBER"},
            "rx": {"type": "NUMBER"},
            "ry": {"type": "NUMBER"},
            "rz": {"type": "NUMBER"},
            "spin": {"type": "NUMBER"},
            "explode": {"type": "NUMBER"},
            "time": {"type": "NUMBER"},
            "motion_speed": {"type": "NUMBER"},
            "radius": {"type": "NUMBER"},
            "amplitude": {"type": "NUMBER"},
            "snap": {"type": "NUMBER"},
            "clip_speed": {"type": "NUMBER"},
            "motion": {"type": "STRING"},
            "axis": {"type": "STRING"},
            "theme": {"type": "STRING"},
            "keyframe_id": {"type": "STRING"},
            "cinematic": {"type": "STRING"},
            "source_id": {"type": "STRING"},
            "target_id": {"type": "STRING"},
            "source_label": {"type": "STRING"},
            "target_label": {"type": "STRING"},
            "link_id": {"type": "STRING"},
            "model_id": {"type": "STRING"},
            "position_json": {"type": "STRING"},
            "target_json": {"type": "STRING"},
            "hud_id": {"type": "STRING"},
            "hud_title": {"type": "STRING"},
            "hud_value": {"type": "STRING"},
            "unit": {"type": "STRING"},
            "project_name": {"type": "STRING"},
            "project_id": {"type": "STRING"},
            "easing": {"type": "STRING"},
            "object_ids_json": {"type": "STRING", "description": "JSON array of scene object IDs for multi-select or batch editing."},
            "selection_mode": {"type": "STRING", "description": "replace, add, toggle, all or clear."},
            "group_id": {"type": "STRING"},
            "group_name": {"type": "STRING"},
            "align": {"type": "STRING", "description": "center, min or max."},
            "parent_id": {"type": "STRING"},
            "parent_label": {"type": "STRING"},
            "bookmark_id": {"type": "STRING"},
            "bookmark_name": {"type": "STRING"},
            "asset_name": {"type": "STRING", "description": "Saved GLB asset name or partial name."},
            "physics_mode": {"type": "STRING", "description": "off, drop, launch, zero_g or float."},
            "velocity_json": {"type": "STRING", "description": "Optional JSON [vx,vy,vz] launch/zero-G velocity."},
            "dx": {"type": "NUMBER"}, "dy": {"type": "NUMBER"}, "dz": {"type": "NUMBER"},
            "drx": {"type": "NUMBER"}, "dry": {"type": "NUMBER"}, "drz": {"type": "NUMBER"},
            "scale_factor": {"type": "NUMBER"},
            "spacing": {"type": "NUMBER"},
            "delta_time": {"type": "NUMBER"},
            "gravity": {"type": "NUMBER"},
            "bounce": {"type": "NUMBER"},
            "floor": {"type": "NUMBER"},
            "vx": {"type": "NUMBER"},
            "vy": {"type": "NUMBER"},
            "vz": {"type": "NUMBER"},
            "count": {"type": "INTEGER"},
            "auto_orbit": {"type": "BOOLEAN"},
            "grid": {"type": "BOOLEAN"},
            "loop": {"type": "BOOLEAN"},
            "show_labels": {"type": "BOOLEAN"},
            "show_trails": {"type": "BOOLEAN"},
            "audio_reactive": {"type": "BOOLEAN"},
            "visible": {"type": "BOOLEAN"},
            "locked": {"type": "BOOLEAN"},
            "clip_paused": {"type": "BOOLEAN"},
        },
        "required": ["operation"],
    },
    "handler": ultron_stage,
}
