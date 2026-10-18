"""Launch an already-installed ComfyUI with a bounded RTX 2050 profile.

Does not install code, download weights, change CUDA or expose a network listener.
"""

import os
from pathlib import Path
import subprocess
import sys

FLAGS = [
    "--listen",
    "127.0.0.1",
    "--port",
    "8188",
    "--disable-dynamic-vram",
    "--lowvram",
    "--reserve-vram",
    "1",
    "--cpu-vae",
    "--preview-method",
    "none",
    "--disable-all-custom-nodes",
]


def command(env=None):
    env = os.environ if env is None else env
    root = Path(env.get("GOLGE_COMFYUI_HOME", "")).resolve()
    python = Path(
        env.get("GOLGE_COMFYUI_PYTHON", str(root / ".venv" / "Scripts" / "python.exe"))
    ).resolve()
    if not (root / "main.py").is_file() or not python.is_file():
        raise ValueError(
            "Existing ComfyUI installation and its Python are required; no automatic install."
        )
    return [str(python), "-s", str(root / "main.py"), *FLAGS], root


if __name__ == "__main__":
    try:
        args, cwd = command()
        if "--print-command" in sys.argv:
            print(subprocess.list2cmdline(args))
        else:
            raise SystemExit(subprocess.call(args, cwd=cwd))
    except ValueError as exc:
        print("GÖLGE: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
