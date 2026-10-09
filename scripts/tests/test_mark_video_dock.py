"""Tests for the ORIGINAL MARK QMediaPlayer mounted inside ULTRON's CORE.

Pure geometry and native action tests run on Linux CI without Qt. A Windows
Qt WebEngine video decode smoke still requires a real desktop session.
"""
import importlib
import pathlib
import tempfile
import threading
import unittest
from unittest.mock import patch

from integration.video_dock import center_stage_rect

ROOT = pathlib.Path(__file__).resolve().parents[2]


class GeometryTests(unittest.TestCase):
    def test_css_scale_matches_qt_webengine_view(self):
        box = dict(x=250, y=160, width=1400, height=720, vw=1920, vh=1080)
        self.assertEqual(center_stage_rect(box, 960, 540), (125, 80, 700, 360))

    def test_clamped_center_never_covers_sidepanels(self):
        box = dict(x=-400, y=-2, width=99999, height=99999, vw=1920, vh=1080)
        x, y, w, h = center_stage_rect(box, 960, 540)
        self.assertEqual((x, y), (0, 0))
        self.assertLessEqual(x + w, 960)
        self.assertLessEqual(y + h, 540)

    def test_malformed_dpi_or_nan_falls_back_safely(self):
        for bounds in (None, {}, {"x": "NaN", "y": 0, "width": 1,
                                  "height": 1, "vw": 1920, "vh": 1080}):
            x, y, w, h = center_stage_rect(bounds, 960, 540)
            self.assertTrue(0 <= x < 960 and 0 <= y < 540)
            self.assertTrue(0 < w <= 960-x and 0 < h <= 540-y)


class Player:
    def __init__(self):
        self.playing = False
        self.events = []

    def video_is_playing(self):
        return self.playing

    def show_video(self, source, title, muted=True, audio_source=""):
        self.events.append(("show", source, title, muted, audio_source))
        self.playing = True

    def stop_video(self):
        self.events.append(("stop",))
        self.playing = False

    def set_video_muted(self, muted):
        self.events.append(("mute", muted))

    def set_video_paused(self, paused):
        self.events.append(("pause", paused))


class MarkEngineTests(unittest.TestCase):
    def setUp(self):
        self.tool = importlib.import_module("actions.video_player")
        self.p = Player()

    def test_original_local_clip_plays_muted(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "animation.webm"
            f.write_bytes(b"test placeholder - UI playback not asserted")
            result = self.tool.video_player({"action": "play", "source": str(f)},
                                            player=self.p)
            self.assertIn("Playing", result)
            self.assertEqual(self.p.events[0][:2], ("show", str(f)))
            self.assertTrue(self.p.events[0][3])

    def test_direct_video_url_does_not_pop_a_browser(self):
        result = self.tool.video_player({
            "action": "play", "source": "https://example.org/animation.mp4",
        }, player=self.p)
        self.assertIn("Playing", result)
        self.assertEqual(self.p.events[0][0], "show")
        self.assertTrue(self.p.events[0][3])

    def test_pause_resume_mute_stop_on_same_original_player(self):
        self.p.playing = True
        for action, event in [("pause", ("pause", True)),
                              ("resume", ("pause", False)),
                              ("unmute", ("mute", False)),
                              ("mute", ("mute", True)),
                              ("stop", ("stop",))]:
            self.tool.video_player({"action": action}, player=self.p)
            self.assertEqual(self.p.events[-1], event)

    def test_replacing_file_invalidates_pending_youtube(self):
        token = self.tool._begin_open()
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "new-video.mp4"
            f.write_bytes(b"new video")
            self.tool.video_player({"action": "play", "source": str(f)},
                                   player=self.p)
            self.assertFalse(self.tool._still_wanted(token))


class IntegrationContractTests(unittest.TestCase):
    def test_no_second_qt_video_dialog_or_video_widget(self):
        code = (ROOT / "integration/web_panel.py").read_text(encoding="utf-8")
        dock = (ROOT / "integration/video_dock.py").read_text(encoding="utf-8")
        self.assertNotIn("video_dialog=QDialog", code)
        self.assertIn("ui._video_dock = MarkVideoDock(view, page, win)", code)
        self.assertIn("self.video = window._video_cont", dock)
        self.assertIn("self.video.setParent(view)", dock)
        self.assertIn(".reactor-panel .center-stage", dock)
        self.assertIn("self.video.raise_()", dock)

    def test_gemini_video_engine_still_uses_old_mark_capability(self):
        code = (ROOT / "actions/video_player.py").read_text(encoding="utf-8")
        bridge = (ROOT / "integration/web_panel.py").read_text(encoding="utf-8")
        self.assertIn("def _resolve_youtube(", code)
        self.assertIn("audio_source=audio_url", code)
        self.assertIn("from actions.video_player import video_player", bridge)
        self.assertIn("videoRequest(self, action, source)", bridge)
        self.assertIn("_begin_open()", code)

    def test_video_image_fits_panel_and_split_audio_sound_defaults_muted(self):
        ui = (ROOT / "ui.py").read_text(encoding="utf-8")
        self.assertIn("QGraphicsVideoItem()", ui)
        self.assertIn("QMediaPlayer()", ui)
        self.assertIn("self._video_audio.setMuted(True)", ui)
        self.assertIn("self._video_sound_out.setMuted(True)", ui)
        self.assertIn("self._video_item.setSize(QSizeF(w, h))", ui)
        self.assertIn("output = self._video_sound_out if self._video_split else self._video_audio", ui)
        self.assertIn("self._video_pause_sig.connect(self._on_video_pause)", ui)
        self.assertIn("self._video_player.mediaStatusChanged.connect(self._on_video_media_status)", ui)
        self.assertIn("status == QMediaPlayer.MediaStatus.EndOfMedia", ui)
        self.assertIn("self.stop_video()  # emit the signal:", ui)

    def test_frontend_binds_native_typed_commands(self):
        dash = (ROOT / "ultron/frontend/src/dashboard/Dashboard.tsx").read_text(encoding="utf-8")
        runtime = (ROOT / "ultron/frontend/src/dashboard/runtime.ts").read_text(encoding="utf-8")
        self.assertIn("markVideoIntent(text)", dash)
        self.assertIn("u.native.videoRequest('open_file','')", dash)
        self.assertIn("videoRequest?:(action:string,source:string)=>void", runtime)


if __name__ == "__main__":
    unittest.main()
