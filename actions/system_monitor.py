"""
System Monitor — background metric checks with voice alert support.
Zero subprocess calls on all platforms — uses ctypes/pynvml/psutil/wmi only.
"""
import ctypes
import platform
import time

import psutil

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

DEFAULT_THRESHOLDS = {
    "cpu":  90.0,
    "ram":  90.0,
    "temp": 85.0,
    "gpu":  95.0,
}

_COOLDOWN   = 300
_CPU_STREAK = 3

# ── NVML DLL cache (Windows: nvml.dll, Linux: libnvidia-ml.so.1) ─────────────
_nvml_lib: object = None
_nvml_ok:  object = None   # None=untested  True=works  False=unavailable


def _nvml_gpu() -> float:
    """GPU utilisation via NVML — zero subprocess on all platforms."""
    global _nvml_lib, _nvml_ok
    if _nvml_ok is False:
        return -1.0
    try:
        class _Util(ctypes.Structure):
            _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

        if _nvml_lib is None:
            if _OS == "Windows":
                candidates = ("nvml", r"C:\Windows\System32\nvml.dll")
                _load = ctypes.WinDLL
            else:
                candidates = (
                    "libnvidia-ml.so.1",
                    "libnvidia-ml.so",
                    "libnvidia-ml.dylib",
                )
                _load = ctypes.CDLL
            for name in candidates:
                try:
                    lib = _load(name)
                    lib.nvmlInit_v2()
                    _nvml_lib = lib
                    break
                except Exception:
                    continue

        if _nvml_lib is None:
            _nvml_ok = False
            return -1.0

        dev = ctypes.c_void_p()
        _nvml_lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
        u = _Util()
        _nvml_lib.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(u))
        _nvml_ok = True
        return float(u.gpu)
    except Exception:
        _nvml_ok = False
        return -1.0


def _get_gpu_usage() -> float:
    # pynvml — subprocess-free, works everywhere if installed
    try:
        import pynvml  # type: ignore
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        return float(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
    except Exception:
        pass

    return _nvml_gpu()


def _get_cpu_temp() -> float:
    # psutil — works on Linux; occasionally Windows with proper drivers
    try:
        temps = psutil.sensors_temperatures()
        for name in ["coretemp", "k10temp", "cpu_thermal", "acpitz",
                     "cpu-thermal", "zenpower", "it8688"]:
            if name in temps and temps[name]:
                return temps[name][0].current
        for entries in temps.values():
            if entries:
                return entries[0].current
    except Exception:
        pass

    # Windows: wmi module (pure Python COM, zero subprocess)
    if _OS == "Windows":
        try:
            import wmi  # type: ignore
            w = wmi.WMI(namespace="root/wmi")
            tz = w.MSAcpi_ThermalZoneTemperature()
            if tz:
                return (tz[0].CurrentTemperature / 10.0) - 273.15
        except Exception:
            pass

    return -1.0



def _windows_system_facts() -> dict:
    """Read-only Windows facts. Unknown values remain None, never guessed."""
    if platform.system() != "Windows":
        return {}
    import os
    import sys
    facts = {
        "os_name": None, "os_version": None, "cpu_model": None,
        "timezone": None, "drive_letters": [], "default_browser": None,
        "network_interface": None, "network_type": None,
        "active_windows": [], "running_processes": [],
        "default_microphone": None,
    }
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            facts["cpu_model"] = str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    except (OSError, ValueError):
        pass
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            name = str(winreg.QueryValueEx(key, "ProductName")[0])
            build = int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
            if build >= 22000 and name.lower().startswith("windows 10"):
                name = name.replace("Windows 10", "Windows 11", 1)
            facts["os_name"] = name
            facts["os_version"] = str(build)
    except (OSError, ValueError, TypeError):
        pass
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation") as key:
            facts["timezone"] = str(winreg.QueryValueEx(key, "TimeZoneKeyName")[0])
    except (OSError, ValueError):
        pass
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice") as key:
            progid = str(winreg.QueryValueEx(key, "ProgId")[0])
            identifiers = {"chromehtml": "Google Chrome", "msedgehtm": "Microsoft Edge",
                           "firefoxurl": "Mozilla Firefox", "bravehtml": "Brave",
                           "operastable": "Opera"}
            lowered = progid.casefold()
            facts["default_browser"] = next(
                (label for prefix, label in identifiers.items() if prefix in lowered), None
            )
    except (OSError, ValueError):
        pass
    try:
        partitions = psutil.disk_partitions(all=False)
        facts["drive_letters"] = sorted({
            p.mountpoint[:2].upper() for p in partitions
            if len(p.mountpoint) >= 2 and p.mountpoint[1] == ":"
        })
    except (OSError, ValueError):
        pass
    try:
        import socket
        interfaces = psutil.net_if_stats()
        addresses = psutil.net_if_addrs()
        candidates = []
        for name, stat in interfaces.items():
            if not stat.isup or name not in addresses:
                continue
            if not any(a.family == socket.AF_INET and
                       not a.address.startswith("169.254.") for a in addresses[name]):
                continue
            lower = name.casefold()
            kind = ("Wi-Fi" if any(token in lower for token in ("wi-fi", "wifi", "wlan"))
                    else "Ethernet" if "ethernet" in lower else None)
            if kind:
                candidates.append((name, kind))
        # Multiple active adapters: cannot infer the default internet route.
        if len(candidates) == 1:
            facts["network_interface"], facts["network_type"] = candidates[0]
    except (OSError, ValueError):
        pass
    try:
        names = {p.info["name"] for p in psutil.process_iter(["name"])
                 if p.info.get("name")}
        facts["running_processes"] = sorted(names, key=str.casefold)[:120]
    except (OSError, ValueError):
        pass
    try:
        user32 = ctypes.windll.user32
        windows = []
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @callback_type
        def collect(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if not 0 < length <= 512:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value:
                windows.append(buf.value)
            return len(windows) < 40

        user32.EnumWindows(collect, 0)
        facts["active_windows"] = windows
    except (AttributeError, OSError, ValueError):
        pass
    try:
        import sounddevice as sd
        index = sd.default.device[0]
        if index is not None and int(index) >= 0:
            device = sd.query_devices(int(index))
            if device.get("max_input_channels", 0) > 0:
                facts["default_microphone"] = str(device["name"])
    except (ImportError, OSError, ValueError, TypeError, IndexError):
        pass
    return facts


def get_system_status(*, include_details: bool = False) -> dict:
    """Snapshot of current system metrics for the system_status tool."""
    cpu  = psutil.cpu_percent(interval=0.2)
    ram  = psutil.virtual_memory()
    temp = _get_cpu_temp()
    gpu  = _get_gpu_usage()

    boot_time   = psutil.boot_time()
    uptime_secs = time.time() - boot_time
    uptime_h    = int(uptime_secs // 3600)
    uptime_m    = int((uptime_secs % 3600) // 60)

    return {
        "cpu_percent":   round(cpu, 1),
        "ram_percent":   round(ram.percent, 1),
        "ram_used_gb":   round(ram.used   / 1024 ** 3, 1),
        "ram_total_gb":  round(ram.total  / 1024 ** 3, 1),
        "cpu_temp_c":    round(temp, 1) if temp > 0 else None,
        "gpu_percent":   round(gpu,  1) if gpu  >= 0 else None,
        "uptime":        f"{uptime_h}h {uptime_m}m",
        "process_count": len(psutil.pids()),
        # Facts used by speech/chat must come from the owner's actual Windows
        # session rather than the language model's guesses.
        **(_windows_system_facts() if include_details else {}),
    }


class SystemMonitor:
    """
    Stateful monitor — cooldown state persists across session reconnections.
    Call check() periodically; returns a [SYSTEM_ALERT] string or None.
    """

    def __init__(self, thresholds: dict | None = None):
        self.thresholds   = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._last_alert: dict[str, float] = {}
        self._cpu_streak  = 0

    def _can_alert(self, key: str) -> bool:
        return (time.monotonic() - self._last_alert.get(key, 0)) > _COOLDOWN

    def _record(self, key: str):
        self._last_alert[key] = time.monotonic()

    def check(self) -> str | None:
        try:
            cpu  = psutil.cpu_percent(interval=None)
            ram  = psutil.virtual_memory().percent
            temp = _get_cpu_temp()
            gpu  = _get_gpu_usage()
        except Exception:
            return None

        alerts: list[str] = []

        if cpu >= self.thresholds["cpu"]:
            self._cpu_streak += 1
            if self._cpu_streak >= _CPU_STREAK and self._can_alert("cpu"):
                alerts.append(
                    f"[SYSTEM_ALERT] CPU usage has been critically high ({cpu:.0f}%) "
                    "for several seconds. Warn the user in their language and suggest "
                    "closing heavy applications."
                )
                self._record("cpu")
                self._cpu_streak = 0
        else:
            self._cpu_streak = 0

        if ram >= self.thresholds["ram"] and self._can_alert("ram"):
            alerts.append(
                f"[SYSTEM_ALERT] RAM is at {ram:.0f}% — nearly exhausted. "
                "Warn the user in their language and suggest freeing memory."
            )
            self._record("ram")

        if temp > 0 and temp >= self.thresholds["temp"] and self._can_alert("temp"):
            alerts.append(
                f"[SYSTEM_ALERT] CPU temperature is {temp:.0f}°C — above the safe limit. "
                "Warn the user in their language and advise reducing system load "
                "or checking cooling."
            )
            self._record("temp")

        if gpu >= 0 and gpu >= self.thresholds["gpu"] and self._can_alert("gpu"):
            alerts.append(
                f"[SYSTEM_ALERT] GPU load is at {gpu:.0f}%. "
                "Briefly inform the user in their language."
            )
            self._record("gpu")

        return " ".join(alerts) if alerts else None
