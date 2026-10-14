"""Run generated-code checks in a resource-bounded, networkless container."""
from __future__ import annotations

import os
import shutil
import site
import subprocess
import sys
import sysconfig
import time
from pathlib import Path

SANDBOX_IMAGE = "ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55"
_DOCKER_READY: bool | None = None


class SandboxUnavailable(RuntimeError):
    pass


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _docker_ready(docker: str) -> bool:
    global _DOCKER_READY
    if _DOCKER_READY is not None:
        return _DOCKER_READY
    try:
        daemon = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"],
                                capture_output=True, text=True, timeout=10, check=False)
        image = subprocess.run([docker, "image", "inspect", SANDBOX_IMAGE],
                              capture_output=True, text=True, timeout=10, check=False)
        _DOCKER_READY = daemon.returncode == 0 and image.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        _DOCKER_READY = False
    return _DOCKER_READY


def run_sandboxed(command: list[str], *, cwd: Path, env: dict[str, str] | None = None,
                  timeout: int = 30, writable_cwd: bool = False,
                  readonly_paths: tuple[Path, ...] = ()) -> subprocess.CompletedProcess:
    """Run a command with no network, host home, inherited secrets, or host writes.

    The pinned Ubuntu image receives only the disposable checkout, Python
    runtime, and explicitly listed read-only tools. The checkout is read-only
    unless a trusted compiler needs a disposable output directory. The
    container has no capabilities, a bounded PID/memory/CPU budget, and a
    64 MiB temporary filesystem. Missing Docker/image fails closed.
    """
    docker = shutil.which("docker")
    if sys.platform != "linux" or not docker or not _docker_ready(docker):
        raise SandboxUnavailable("pinned_docker_sandbox_unavailable")
    work = cwd.resolve(strict=True)
    runtime = Path(sys.prefix).resolve(strict=True)
    if not work.is_dir() or work == Path("/"):
        raise SandboxUnavailable("sandbox_workdir_invalid")

    args = [docker, "run", "--rm", "--network=none", "--read-only",
            "--security-opt=no-new-privileges", "--cap-drop=ALL", "--pids-limit=64",
            "--memory=1g", "--cpus=1", "--user", f"{os.getuid()}:{os.getgid()}",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=67108864,mode=1777"]
    container_name = f"golge-check-{os.getpid()}-{time.monotonic_ns()}"
    args.extend(("--name", container_name))
    work_mode = "rw" if writable_cwd else "ro"
    args.extend(("--volume", f"{work}:/tmp/golge/work:{work_mode}",
                 "--volume", f"{runtime}:{runtime}:ro"))
    multiarch = sysconfig.get_config_var("MULTIARCH")
    if isinstance(multiarch, str) and multiarch:
        for library_dir in (Path("/usr/lib") / multiarch, Path("/lib") / multiarch):
            if library_dir.is_dir():
                args.extend(("--volume", f"{library_dir}:{library_dir}:ro"))
    path_maps: list[tuple[str, str]] = [(str(work), "/tmp/golge/work")]
    try:
        user_site = Path(site.getusersitepackages()).resolve(strict=True)
    except (OSError, TypeError):
        user_site = None
    if user_site and user_site.is_dir() and not _under(user_site, runtime):
        args.extend(("--volume", f"{user_site}:/tmp/golge/user-site:ro"))
        path_maps.append((str(user_site), "/tmp/golge/user-site"))

    for index, candidate in enumerate(readonly_paths):
        source = candidate.resolve(strict=True)
        if _under(source, work):
            continue
        target = f"/tmp/golge/toolchain-{index}"
        args.extend(("--volume", f"{source}:{target}:ro"))
        path_maps.append((str(source), target))

    safe_env = {key: value for key, value in (env or {}).items()
                if key in {"LANG", "LC_ALL", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
                           "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "MYPY_CACHE_DIR"}}
    if user_site and user_site.is_dir():
        safe_env["PYTHONPATH"] = os.pathsep.join(
            item for item in (safe_env.get("PYTHONPATH", ""), str(user_site)) if item)
    for key, value in list(safe_env.items()):
        if key == "PYTHONPATH":
            safe_env[key] = os.pathsep.join(_map_path(item, path_maps)
                                            for item in value.split(os.pathsep) if item)
        elif key == "MYPY_CACHE_DIR":
            safe_env[key] = "/tmp/mypy"

    runtime_bin = str(runtime / "bin")
    container_path = f"{runtime_bin}:/usr/local/bin:/usr/bin:/bin"
    base_env = {"HOME": "/tmp", "TMPDIR": "/tmp", "TMP": "/tmp", "TEMP": "/tmp",
                "PATH": container_path, "PYTHONNOUSERSITE": "1"}
    base_env.update(safe_env)
    for key, value in base_env.items():
        args.extend(("--env", f"{key}={value}"))
    mapped_command = [_map_path(str(arg), path_maps) for arg in command]
    args.extend(("--workdir", "/tmp/golge/work", SANDBOX_IMAGE, *mapped_command))
    try:
        return subprocess.run(args, cwd="/", env=os.environ.copy(), capture_output=True,
                              text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        subprocess.run([docker, "rm", "-f", container_name], cwd="/", env=os.environ.copy(),
                       capture_output=True, text=True, timeout=10, check=False)
        raise


def _map_path(value: str, path_maps: list[tuple[str, str]]) -> str:
    for source, target in sorted(path_maps, key=lambda pair: len(pair[0]), reverse=True):
        if value == source:
            return target
        if value.startswith(source + os.sep):
            return target + value[len(source):].replace(os.sep, "/")
    return value
