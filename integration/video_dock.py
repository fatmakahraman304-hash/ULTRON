"""In-cockpit MARK QMediaPlayer dock.

The original MARK avatar HUD already owns a QGraphicsVideoItem/QMediaPlayer,
including a second audio player for YouTube's split streams. Reparent that
existing QWidget into ULTRON's center stage, never into a QDialog or a second
native video window. Qt and WebEngine must share the same GUI thread.

All geometry coming from the web page is clamped to the WebEngine viewport.
"""
from __future__ import annotations

import math
from typing import Any


def center_stage_rect(bounds: Any, viewport_width: int, viewport_height: int) -> tuple[int, int, int, int]:
    """Scale DOM CSS pixels to Qt widget units; fail closed to center fallback."""
    w = max(1, int(viewport_width))
    h = max(1, int(viewport_height))
    fallback = (max(0, w // 5), max(0, h // 6),
                max(1, w - 2 * (w // 5)), max(1, h - 2 * (h // 6)))
    if not isinstance(bounds, dict):
        return fallback
    try:
        numbers = [float(bounds[name]) for name in ("x", "y", "width", "height", "vw", "vh")]
        if not all(math.isfinite(number) for number in numbers):
            return fallback
        x, y, width, height, css_w, css_h = numbers
        if css_w <= 0 or css_h <= 0 or width <= 0 or height <= 0:
            return fallback
        # Responsive and Windows DPI-aware. Clamp to the Qt view so native
        # playback can never cover the surrounding telemetry/chat controls.
        x = max(0, min(w - 1, round(x * w / css_w)))
        y = max(0, min(h - 1, round(y * h / css_h)))
        width = max(1, min(w - x, round(width * w / css_w)))
        height = max(1, min(h - y, round(height * h / css_h)))
        return x, y, width, height
    except (KeyError, TypeError, ValueError, OverflowError):
        return fallback


class MarkVideoDock:
    """Qt-only adapter, with lazy imports so geometry can be tested in CI."""

    _RECT_SCRIPT = """(() => {
      const el = document.querySelector('.reactor-panel .center-stage');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {x:r.x, y:r.y, width:r.width, height:r.height,
              vw:window.innerWidth, vh:window.innerHeight};
    })()"""

    def __init__(self, view, page, window):
        from PyQt6.QtCore import QTimer
        self.view = view
        self.page = page
        self.window = window
        self.video = window._video_cont  # MARK's real native player, no duplicate.
        self.video.setParent(view)
        self.video.setObjectName("ultron-center-native-mark-video")
        self.video.hide()
        self.active = False
        self._request_id = 0
        self.timer = QTimer(view)
        self.timer.setInterval(550)
        self.timer.timeout.connect(self.sync_geometry)

        # _on_video_open is connected by MARK's MainWindow before this point.
        window._video_open_sig.connect(self.open)
        window._video_close_sig.connect(self.close)
        # Window size and DOM navigation may change while a video is playing.
        page.loadFinished.connect(lambda _ok: self.sync_geometry() if self.active else None)

    def open(self, *_args):
        # Absent Qt multimedia backend must not leave a blank modal/overlay.
        if not self.window._video_on:
            return
        self.active = True
        self.video.show()
        self.video.raise_()
        self.sync_geometry()
        self.timer.start()

    def close(self, *_args):
        self.active = False
        self._request_id += 1  # discard delayed JS geometry callbacks
        self.timer.stop()
        self.video.hide()

    def sync_geometry(self):
        if not self.active or not self.video.isVisible():
            return
        self._request_id += 1
        request_id = self._request_id

        def apply(bounds):
            if not self.active or not self.video.isVisible() or request_id != self._request_id:
                return
            x, y, w, h = center_stage_rect(bounds, self.view.width(), self.view.height())
            if self.video.geometry().getRect() != (x, y, w, h):
                self.video.setGeometry(x, y, w, h)
                # The native QGraphicsVideoItem must letterbox *again* when the
                # central stage changes size, not just on nativeSizeChanged.
                QTimer = self.timer.__class__
                QTimer.singleShot(0, self.window._fit_video)
            self.video.raise_()

        self.page.runJavaScript(self._RECT_SCRIPT, apply)
