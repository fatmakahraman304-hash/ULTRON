"""Exercise real Qt WebChannel, audio-level propagation and specialist window."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from integration.launcher import Services
from integration.web_panel import prepare, LocalPage
console_errors = []
original_console = LocalPage.javaScriptConsoleMessage
def capture_console(self, level, message, line, source):
    if 'error' in str(level).lower() or 'error ' in message.lower():
        console_errors.append(message)
    original_console(self, level, message, line, source)
LocalPage.javaScriptConsoleMessage = capture_console
prepare()
from PyQt6.QtCore import QTimer
from ui import UltronUI
from integration.panel import attach

with Services() as service:
    service.start()
    os.environ.update({k: service.env[k] for k in ('MARK_ULTRON_URL', 'MARK_ULTRON_TOKEN')})
    ui = UltronUI(str(ROOT / 'face.png'))
    attach(ui)
    view, page, profile, channel, native, original, dialogs = ui._dashboard
    result = {'status': 'FAIL'}
    began = time.monotonic()
    phase = [0]
    timer = QTimer()

    def inspect(data):
        if not isinstance(data, dict):
            return
        if phase[0] == 0 and data.get('frames', 0) > 30 and data.get('online') and data.get('native'):
            assert ui._win.windowTitle() == 'ULTRON'
            assert ui._win.centralWidget() is view and not original.isVisible()
            ui.set_state('SPEAKING')
            phase[0] = 1
        elif phase[0] == 1 and data.get('state') == 'SPEAKING' and data.get('amplitude', 0) > .2:
            native.action('hologram')
            phase[0] = 2
        elif phase[0] == 2:
            window = ui._hologram_window
            assert window.isVisible()
            window.close()
            result.update(status='PASS', amplitude=data['amplitude'], frames=data['frames'],
                          checks=['single main window', 'native bridge', 'WebSocket online',
                                  'SPEAKING state', 'audio amplitude to renderer', 'hologram window', 'normal close'])
            ui._win.grab().save(str(ROOT / 'logs/native-final.png'))
            timer.stop()
            native.action('shutdown')

    def tick():
        if time.monotonic() - began > 50:
            timer.stop()
            ui._win.close()
            return
        if phase[0] == 1:
            ui._win.hud.set_audio_level(.8)  # Test input through the production audio-level path.
        page.runJavaScript("""(()=>{const c=document.querySelector('.core-canvas');return c?{
          frames:Number(c.dataset.frames),state:c.dataset.state,amplitude:Number(c.dataset.amplitude),
          online:document.querySelector('.subsystems.left')?.textContent.includes('ONLINE'),
          native:!document.querySelector('.power')?.disabled}:null})()""", inspect)

    timer.timeout.connect(tick)
    timer.start(250)
    ui._app.exec()
    result['console_errors'] = console_errors
    if console_errors:
        result['status'] = 'FAIL'
    (ROOT / 'logs/native-final.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    assert result['status'] == 'PASS', result
print('NATIVE_DASHBOARD_PASS')
