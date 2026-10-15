import os
from pathlib import Path
import subprocess
import sys

from integration.launcher import _ensure_runtime_import_paths
from integration.paths import BACKEND, ROOT


def test_runtime_import_paths_keep_existing_entries_and_expose_repository_root():
    original = {"PYTHONPATH": str(BACKEND)}
    updated = _ensure_runtime_import_paths(dict(original))
    entries = updated["PYTHONPATH"].split(os.pathsep)

    assert Path(entries[0]).resolve() == ROOT.resolve()
    assert Path(entries[1]).resolve() == BACKEND.resolve()
    assert original["PYTHONPATH"] == str(BACKEND)
    assert len(entries) == 2
    assert len({os.path.normcase(str(Path(entry).resolve())) for entry in entries}) == len(entries)


def test_backend_working_directory_can_import_cloud_persona_package():
    env = _ensure_runtime_import_paths({"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(BACKEND)})
    result = subprocess.run(
        [sys.executable, "-c", "from ultron.cloud_service.conversation_persona import classify_intent; print('OK')"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "OK"
