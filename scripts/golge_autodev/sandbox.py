"""Run generated-code checks without host credentials, network, or user files."""
from __future__ import annotations

import os
import shutil
import site
import subprocess
import sys
from pathlib import Path


class SandboxUnavailable(RuntimeError):
    pass


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def run_sandboxed(command: list[str], *, cwd: Path, env: dict[str, str] | None = None,
                  timeout: int = 30, writable_cwd: bool = False,
                  readonly_paths: tuple[Path, ...] = ()) -> subprocess.CompletedProcess:
    """Execute a bounded test command in a Linux namespace with no network.

    Only the working tree, Python runtime, standard runtime libraries, and
    explicitly listed toolchain directories are mounted. The test checkout is
    read-only by default. Temporary files live on an ephemeral tmpfs.
    """
    bwrap = shutil.which("bwrap")
    if sys.platform != "linux" or not bwrap:
        raise SandboxUnavailable("linux_bubblewrap_required")
    work = cwd.resolve(strict=True)
    runtime = Path(sys.prefix).resolve(strict=True)
    if not work.is_dir() or work == Path("/"):
        raise SandboxUnavailable("sandbox_workdir_invalid")

    args = [bwrap, "--die-with-parent", "--new-session", "--unshare-net",
            "--unshare-pid", "--unshare-ipc"]
    for source in (Path("/usr"), Path("/bin"), Path("/lib"), Path("/lib64"), Path("/etc")):
        if source.exists():
            args.extend(("--ro-bind", str(source), str(source)))
    args.extend(("--proc", "/proc", "--dev", "/dev", "--size", "67108864", "--tmpfs", "/tmp",
                 "--dir", "/tmp/golge", "--dir", "/tmp/golge/tmp",
                 "--dir", "/tmp/golge/home"))
    args.extend(("--bind" if writable_cwd else "--ro-bind", str(work), "/tmp/golge/work"))

    path_maps: list[tuple[str, str]] = [(str(work), "/tmp/golge/work")]
    runtime_is_system = _under(runtime, Path("/usr")) or runtime == Path("/usr")
    if not runtime_is_system:
        args.extend(("--ro-bind", str(runtime), "/tmp/golge/runtime"))
        path_maps.append((str(runtime), "/tmp/golge/runtime"))

    try:
        user_site = Path(site.getusersitepackages()).resolve(strict=True)
    except (OSError, TypeError):
        user_site = None
    if user_site and user_site.is_dir() and not _under(user_site, runtime) and not _under(user_site, Path("/usr")):
        args.extend(("--ro-bind", str(user_site), "/tmp/golge/user-site"))
        path_maps.append((str(user_site), "/tmp/golge/user-site"))

    for index, candidate in enumerate(readonly_paths):
        source = candidate.resolve(strict=True)
        if _under(source, work):
            continue  # already mounted with the workspace
        target = f"/tmp/golge/toolchain-{index}"
        args.extend(("--ro-bind", str(source), target))
        path_maps.append((str(source), target))

    host_env = env or {}
    safe_env = {key: value for key, value in host_env.items()
                if key in {"LANG", "LC_ALL", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
                           "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "MYPY_CACHE_DIR"}}
    if user_site and user_site.is_dir():
        safe_env["PYTHONPATH"] = os.pathsep.join(
            item for item in (safe_env.get("PYTHONPATH", ""), str(user_site)) if item)
    for key, value in list(safe_env.items()):
        if key == "PYTHONPATH":
            safe_env[key] = os.pathsep.join(_map_path(item, path_maps) for item in value.split(os.pathsep) if item)
        elif key == "MYPY_CACHE_DIR":
            safe_env[key] = "/tmp/golge/tmp/mypy"

    safe_path = "/tmp/golge/runtime/bin:/usr/local/bin:/usr/bin:/bin"
    if not runtime_is_system:
        safe_path = "/tmp/golge/runtime/bin:" + safe_path
    args.extend(("--setenv", "HOME", "/tmp/golge/home", "--setenv", "TMPDIR", "/tmp/golge/tmp",
                 "--setenv", "TMP", "/tmp/golge/tmp", "--setenv", "TEMP", "/tmp/golge/tmp",
                 "--setenv", "PATH", safe_path,
                 "--setenv", "PYTHONNOUSERSITE", "1"))
    for key, value in safe_env.items():
        args.extend(("--setenv", key, value))
    mapped_command = [_map_path(str(arg), path_maps) for arg in command]
    args.extend(("--chdir", "/tmp/golge/work", "--", *mapped_command))
    return subprocess.run(args, cwd="/", env={}, capture_output=True, text=True,
                          timeout=timeout, check=False)


def _map_path(value: str, path_maps: list[tuple[str, str]]) -> str:
    for source, target in sorted(path_maps, key=lambda pair: len(pair[0]), reverse=True):
        if value == source:
            return target
        if value.startswith(source + os.sep):
            return target + value[len(source):].replace(os.sep, "/")
    return value
