"""Actual Qt QWidget parentage and responsive video-dock smoke (offscreen).

This test exercises real PyQt6 signals, QWidget visibility, and geometry,
without requiring a running MARK model or actual GPU/video decoding. True
Windows hardware media decode is a separate manual validation.
"""
from __future__ import annotations

import os
import unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from integration.video_dock import MarkVideoDock


class FakePage(QObject):
    loadFinished = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.bounds = {"x": 180, "y": 110, "width": 730,
                       "height": 450, "vw": 1100, "vh": 650}

    def runJavaScript(self, script, callback):
        assert ".reactor-panel .center-stage" in script
        callback(self.bounds)


class FakeWindow(QObject):
    _video_open_sig = pyqtSignal(str, str, bool, str)
    _video_close_sig = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.original_parent = QWidget()
        self._video_cont = QWidget(self.original_parent)
        layout = QVBoxLayout(self._video_cont)
        layout.addWidget(QWidget(self._video_cont))
        self._video_on = False
        self.fits = 0

    def _fit_video(self):
        self.fits += 1


class QtDockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = QWidget()
        self.view.resize(1100, 650)
        self.view.show()
        self.page = FakePage()
        self.win = FakeWindow()
        self.dock = MarkVideoDock(self.view, self.page, self.win)
        self.app.processEvents()

    def tearDown(self):
        self.dock.close()
        self.view.close()
        self.win.original_parent.close()
        self.app.processEvents()

    def test_existing_mark_video_is_child_of_main_view(self):
        self.assertIs(self.win._video_cont.parentWidget(), self.view)
        self.assertFalse(self.dock.active)
        self.assertFalse(self.win._video_cont.isVisible())

    def test_signal_shows_and_sizes_video_inside_center_only(self):
        self.win._video_on = True
        self.win._video_open_sig.emit("C:/media/demo.mp4", "Demo", True, "")
        self.app.processEvents()
        self.assertTrue(self.win._video_cont.isVisible())
        self.assertTrue(self.dock.active)
        self.assertEqual(self.win._video_cont.geometry().getRect(),
                         (180, 110, 730, 450))
        self.assertGreaterEqual(self.win.fits, 1)
        # Responsive page geometry (the React app is scaled to viewport).
        self.page.bounds = {"x": 100, "y": 80, "width": 1000,
                            "height": 500, "vw": 2200, "vh": 1300}
        self.dock.sync_geometry()
        self.app.processEvents()
        self.assertEqual(self.win._video_cont.geometry().getRect(),
                         (50, 40, 500, 250))
        self.win._video_close_sig.emit()
        self.assertFalse(self.win._video_cont.isVisible())
        self.assertFalse(self.dock.active)
        self.assertFalse(self.dock.timer.isActive())

    def test_delayed_page_callbacks_cannot_resurrect_closed_video(self):
        self.win._video_on = True
        self.win._video_open_sig.emit("C:/media/demo.mp4", "Demo", True, "")
        self.win._video_close_sig.emit()
        self.dock.sync_geometry()
        self.app.processEvents()
        self.assertFalse(self.win._video_cont.isVisible())

    def test_missing_decoder_does_not_show_blank_widget(self):
        self.win._video_on = False
        self.win._video_open_sig.emit("bad.mov", "bad", True, "")
        self.app.processEvents()
        self.assertFalse(self.dock.active)
        self.assertFalse(self.win._video_cont.isVisible())


if __name__ == "__main__":
    unittest.main()
