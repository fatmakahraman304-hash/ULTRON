"""Idempotent, logged installation. Optional resources never claim success on failure."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tempfile
from urllib.request import urlopen
from .paths import ROOT, BACKEND, LOGS, DATA


def run(args, cwd=ROOT, timeout=1200, optional=False):
    name = ' '.join(map(str, args[:4]))
    print('RUN:', name, flush=True)
    with (LOGS / 'install.log').open('a', encoding='utf-8') as log:
        log.write('\nRUN ' + name + '\n')
        log.flush()
        try:
            result = subprocess.run(list(map(str, args)), cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=timeout, check=False)
            if result.returncode:
                raise RuntimeError(f'exit={result.returncode}')
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            if optional:
                print(f'WARN: {name}: {exc}; logs/install.log', flush=True)
                return False
            raise RuntimeError(f'{name}: {exc}; logs/install.log') from exc
    return True


def ollama_executable():
    executable = shutil.which('ollama')
    if executable:
        return executable
    for p in (
        Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Programs/Ollama/ollama.exe',
        ROOT / 'runtime/ollama/ollama.exe'):
        try:
            if p.is_file():
                return str(p)
        except PermissionError:
            continue
    return None


def prepare_models():
    warnings = []
    settings = json.loads((BACKEND / 'config/settings.json').read_text(encoding='utf-8'))
    ollama = ollama_executable()
    if ollama:
        run([ollama, '--version'], optional=True)
        run([ollama, 'list'], optional=True)
    else:
        warnings.append('Ollama CLI unavailable; checking running API separately')
    try:
        with urlopen('http://127.0.0.1:11434/api/tags', timeout=5) as response:
            installed = {m['name'] for m in json.load(response).get('models', [])}
        desired = {settings['llm']['model']} | {v for k,v in settings['llm']['routing'].items() if k != 'note'}
        for model in sorted(desired - installed):
            if not ollama or not run([ollama, 'pull', model], timeout=1800, optional=True):
                warnings.append('Ollama model: '+model)
    except (OSError, ValueError) as exc:
        warnings.append('Ollama API unavailable: '+str(exc))
    if not run([sys.executable, '-m', 'integration.models'], optional=True, timeout=900):
        warnings.append('Voice model preparation incomplete')
    return warnings


def main():
    os.chdir(ROOT)
    LOGS.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    os.environ['npm_config_cache'] = str(ROOT/'cache/npm')
    os.environ['PIP_CACHE_DIR'] = str(ROOT/'cache/pip')
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT/'cache/playwright')
    try:
        run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'])
        for group in ('requirements.txt', 'requirements-local-ai.txt', 'requirements-dev.txt'):
            run([sys.executable, '-m', 'pip', 'install', '-r', group])
        warnings = []
        if not run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-voice.txt'], optional=True):
            warnings.append('Local voice dependencies incomplete')
        run([sys.executable, '-m', 'pip', 'check'])
        npm = shutil.which('npm.cmd') or shutil.which('npm')
        if not npm:
            raise RuntimeError('Node/npm bulunamadi. Frontend build yapilamadi.')
        for folder in ('frontend', 'frontend-mobile'):
            run([npm, 'ci', '--no-audit', '--no-fund'], cwd=ROOT/'ultron'/folder)
            run([npm, 'run', 'build'], cwd=ROOT/'ultron'/folder)
        if not run([sys.executable, '-m', 'playwright', 'install', 'chromium'], optional=True):
            warnings.append('Playwright browser download failed')
        warnings += prepare_models()
        # Isolate each run from ACLs and locks in another session's pytest temp area.
        test_temp = Path(tempfile.mkdtemp(prefix='install-tests-', dir=ROOT/'cache'))/'run'
        run([sys.executable, '-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider',
             '--basetemp', str(test_temp)], timeout=600)
        run([sys.executable, '-m', 'integration.doctor', '--quick'], timeout=600)
        (LOGS/'install-result.json').write_text(json.dumps({'core':'PASS','warnings':warnings},indent=2),encoding='utf-8')
        print('Kurulum tamamlandi.' if not warnings else 'Kurulum tamamlandi; optional WARN: '+ '; '.join(warnings), flush=True)
        return 0
    except Exception as exc:
        (LOGS/'install-result.json').write_text(json.dumps({'core':'FAIL','error':str(exc)},indent=2),encoding='utf-8')
        print('INSTALL FAIL:', exc, flush=True)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
