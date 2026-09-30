import argparse
import contextlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import secrets
import socket
import subprocess
import sys
import time
from .paths import ROOT, BACKEND, DATA, LOGS
from .bridge import Bridge


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class Services:
    def __init__(self):
        self.backend = None
        self.ui = None
        self.streams = []
        self.bridge = None
        self.lock = None

    def __enter__(self):
        DATA.mkdir(exist_ok=True)
        LOGS.mkdir(exist_ok=True)
        # Windows byte lock is released even after a killed launcher.
        self.lock = (DATA / 'instance.lock').open('a+b')
        self.lock.seek(0)
        self.lock.write(b'0')
        self.lock.flush()
        self.lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                self.lock.close()
                raise RuntimeError('Birleşik uygulama zaten çalışıyor.') from exc
        return self

    def start(self):
        # Dynamic loopback port avoids fixed 8000 collisions.
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = os.environ.copy()
        env.update(ULTRON_PORT=str(port), ULTRON_BIND_HOST='127.0.0.1',
                   MARK_ULTRON_TOKEN=secrets.token_urlsafe(32), MARK_AUDIO_OWNER='mark',
                   MARK_ULTRON_URL=f'http://127.0.0.1:{port}', PYTHONUTF8='1',
                   PATH=str(ROOT / '.venv' / 'Scripts') + os.pathsep + env.get('PATH', ''))
        self.env = env
        self.bridge = Bridge(env['MARK_ULTRON_URL'], env['MARK_ULTRON_TOKEN'])
        self.backend = self.spawn([sys.executable, '-u', str(BACKEND / 'server.py')], BACKEND, 'backend.log')
        deadline = time.monotonic() + 75
        last_error = None
        while time.monotonic() < deadline:
            if self.backend.poll() is not None:
                raise RuntimeError('ULTRON başlatılamadı; logs/backend.log dosyasına bakın.')
            try:
                status = self.bridge.health()
                if status.get('ok') and status.get('service') == 'mark-ultron':
                    return status
                last_error = str(status.get('components'))
            except (OSError, ValueError) as exc:
                last_error = type(exc).__name__
            time.sleep(0.3)
        raise RuntimeError(f'ULTRON sağlık kontrolü tamamlanamadı: {last_error}')

    def spawn(self, args, cwd, name):
        path = LOGS / name
        if path.exists() and path.stat().st_size > 5_000_000:
            path.replace(path.with_suffix('.previous.log'))
        output = path.open('ab')
        self.streams.append(output)
        return subprocess.Popen(args, cwd=cwd, env=self.env, stdout=output, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    def __exit__(self, *args):
        stop_process(self.ui)
        if self.backend and self.backend.poll() is None and self.bridge:
            try:
                self.bridge.request('/api/merged/shutdown', {}, timeout=3)
                self.backend.wait(timeout=15)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                logging.exception('Graceful shutdown failed; terminating owned backend')
        stop_process(self.backend)
        for stream in self.streams:
            stream.close()
        if self.lock and not self.lock.closed:
            self.lock.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--backend-only', action='store_true')
    args = parser.parse_args(argv)
    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(
        LOGS / 'launcher.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')])
    try:
        with Services() as services:
            health = services.start()
            print('ULTRON hazır; MARK arayüzü açılıyor.', flush=True)
            if not args.backend_only:
                cmd = [sys.executable, '-u', str(ROOT / 'mark_app.py')]
                if args.smoke:
                    services.env['MARK_SMOKE_SECONDS'] = '8'
                services.ui = services.spawn(cmd, ROOT, 'mark.log')
            if args.smoke:
                if services.ui:
                    code = services.ui.wait(timeout=40)
                    if code:
                        raise RuntimeError('MARK arayüz testi başarısız; logs/mark.log dosyasına bakın.')
                (LOGS / 'startup.json').write_text(json.dumps(health, indent=2), encoding='utf-8')
            elif services.ui:
                return services.ui.wait()
            else:
                services.backend.wait()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        logging.exception('Startup failed')
        print(f'HATA: {exc}\nAyrıntılar: {LOGS / "launcher.log"}', flush=True)
        return 1
