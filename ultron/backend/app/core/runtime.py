"""UltronRuntime — tüm bileşenleri başlatan kök sınıf.

Her bileşen ayrı try/except içinde başlatılır; bir tanesinin başarısız
olması diğerlerini engellemez. Başarısız bileşenler None olur ve
kullanan kod getattr(..., None) ile kontrol eder.
"""
import json
import re
import time as _time
from pathlib import Path


def _safe_import(mod: str):
    import importlib
    try:
        return importlib.import_module(mod)
    except Exception:
        return None


class UltronRuntime:
    def __init__(self, settings_path="config/settings.json"):
        self.root = Path.cwd().resolve()
        self.settings_path = settings_path

        # ── Ayarlar ──────────────────────────────────────────────────────
        try:
            self.settings = json.loads(Path(settings_path).read_text(encoding="utf-8"))
        except Exception:
            self.settings = {}

        self.approved = False

        # ── Vault (şifre/API-key kasası) ─────────────────────────────────
        try:
            from app.security.vault import CredentialVault
            self.vault = CredentialVault(audit=None)
        except Exception as e:
            print(f"[WARN] vault: {e}")
            self.vault = _NullVault()

        # ── Brain (Ollama bağdaştırıcısı) ────────────────────────────────
        try:
            from app.core.brain import Brain
            self.brain = Brain(self.settings)
        except Exception as e:
            print(f"[WARN] brain: {e}")
            self.brain = None

        # ── Memory ───────────────────────────────────────────────────────
        try:
            from app.memory.sqlite_memory import Memory
            self.memory = Memory(redact_fn=self.vault.redact)
        except Exception as e:
            print(f"[WARN] memory: {e}")
            self.memory = None

        try:
            from app.memory.semantic_memory import SemanticMemory
            self.semantic_memory = SemanticMemory(self.memory) if self.memory else None
        except Exception as e:
            print(f"[WARN] semantic_memory: {e}")
            self.semantic_memory = None

        try:
            from app.memory.semantic_memory_v2 import SemanticMemoryV2
            self.semv2 = SemanticMemoryV2(self.memory) if self.memory else None
        except Exception as e:
            print(f"[WARN] semv2: {e}")
            self.semv2 = None

        # ── Audit / Permissions ───────────────────────────────────────────
        try:
            from app.security.audit import AuditLog
            self.audit = AuditLog(extra_values_fn=self.vault.all_values)
        except Exception as e:
            print(f"[WARN] audit: {e}")
            self.audit = _NullAudit()

        try:
            from app.security.permissions import PermissionManager
            self.permissions = PermissionManager(self.settings)
        except Exception as e:
            print(f"[WARN] permissions: {e}")
            self.permissions = None

        # ── Sandbox ───────────────────────────────────────────────────────
        try:
            from app.security.sandbox import FilesystemSandbox
            self.sandbox = FilesystemSandbox(self.settings, workspace_root=str(Path.cwd()))
        except Exception as e:
            print(f"[WARN] sandbox: {e}")
            self.sandbox = None

        # ── Tool Registry + Tools ─────────────────────────────────────────
        try:
            from app.core.tool_registry import ToolRegistry
            self.registry = ToolRegistry()
        except Exception as e:
            print(f"[WARN] registry: {e}")
            self.registry = _NullRegistry()

        # ── TTS (Text-to-Speech) ──────────────────────────────────────────
        try:
            from app.voice.tts import TextToSpeech
            self.tts = TextToSpeech()
        except Exception as e:
            print(f"[WARN] tts: {e}")
            self.tts = _NullTTS()

        # ── Vision / GUI ──────────────────────────────────────────────────
        try:
            from app.vision.vision_llm import VisionLLM
            self.vision_llm = VisionLLM(self.brain, self.settings) if self.brain else None
        except Exception as e:
            print(f"[WARN] vision_llm: {e}")
            self.vision_llm = None

        try:
            from app.automation.gui import GUIAutomation
            self.gui = GUIAutomation()
        except Exception as e:
            print(f"[WARN] gui: {e}")
            self.gui = None

        # ── Model Router ──────────────────────────────────────────────────
        self._models_cache = {"ts": 0.0, "models": []}
        try:
            from app.core.model_router import ModelRouter
            self.router = ModelRouter(self.brain, self.settings, self._cached_models) if self.brain else None
        except Exception as e:
            print(f"[WARN] router: {e}")
            self.router = None

        # ── Code Agent / Intel ────────────────────────────────────────────
        try:
            from app.code_agent.code_agent import CodeAgent
            self.code_agent = CodeAgent(self.brain, self.root) if self.brain else None
        except Exception as e:
            print(f"[WARN] code_agent: {e}")
            self.code_agent = None

        try:
            from app.code_intel.analyzer import CodeIntel
            self.code_intel = CodeIntel(str(self.root))
        except Exception as e:
            print(f"[WARN] code_intel: {e}")
            self.code_intel = None

        # ── Register Tools (bağımlılıklar hazırdır artık) ────────────────
        try:
            self._register_tools()
        except Exception as e:
            print(f"[WARN] _register_tools: {e}")

        # ── Executor ──────────────────────────────────────────────────────
        try:
            from app.agent.executor import Executor
            self.executor = Executor(self.registry, self.permissions, self.audit)
        except Exception as e:
            print(f"[WARN] executor: {e}")
            self.executor = None

        # ── Planner / Adaptive Persona / Emotion ──────────────────────────
        try:
            from app.agent.planner import Planner
            self.planner = Planner(
                self.brain, self.registry,
                semantic_memory=self.semantic_memory
            ) if self.brain else None
        except Exception as e:
            print(f"[WARN] planner: {e}")
            self.planner = None

        try:
            from app.agent.adaptive_persona import AdaptivePersona
            self.adaptive = AdaptivePersona()
        except Exception as e:
            print(f"[WARN] adaptive: {e}")
            self.adaptive = None

        try:
            from app.emotion.emotion_engine import EmotionLog
            self.emotion_log = EmotionLog()
        except Exception as e:
            print(f"[WARN] emotion_log: {e}")
            self.emotion_log = None

        # ── Agent ──────────────────────────────────────────────────────────
        self.world_context_fn = None
        try:
            from app.agent.agent import Agent
            self.agent = Agent(
                self.brain, self.executor, self.memory, self.registry,
                self.settings, self.audit, self.tts,
                semantic_memory=self.semantic_memory,
                planner=self.planner,
                vision_llm=self.vision_llm,
                adaptive=self.adaptive,
                router=self.router,
                world_fn=lambda: self.world_context_fn,
                redact_fn=self.vault.redact,
            )
        except Exception as e:
            print(f"[WARN] agent: {e}")
            self.agent = None

        # ── Skills ────────────────────────────────────────────────────────
        try:
            from app.skills import SkillRunner
            self.skills = SkillRunner(
                registry=self.registry,
                executor=self.executor,
                audit=self.audit,
                builtin_dir=str(self.root / "config" / "skills"),
                user_dir=str(self.root / "data" / "skills"),
            )
            if self.executor:
                self.skills.executor = self.executor
        except Exception as e:
            print(f"[WARN] skills: {e}")
            self.skills = None

        # ── Self-Awareness ────────────────────────────────────────────────
        try:
            from app.core.self_awareness import SelfAwareness
            from app.core import doctor as _doc
            self.self_awareness = SelfAwareness(
                registry=self.registry,
                doctor=_doc,
                tts=self.tts,
                brain=self.brain,
            )
        except Exception as e:
            print(f"[WARN] self_awareness: {e}")
            self.self_awareness = None

        # ── Live Voice / Wake Word ────────────────────────────────────────
        try:
            from app.voice.live_voice_v2 import LiveVoiceV2
            self.live_voice = LiveVoiceV2(self.agent, self.tts, self.settings) if self.agent else None
        except Exception as e:
            print(f"[WARN] live_voice_v2: {e}")
            # Fallback: eski LiveVoice
            try:
                from app.voice.live_voice import LiveVoice
                self.live_voice = LiveVoice(self.agent, self.tts, self.settings) if self.agent else None
            except Exception as e2:
                print(f"[WARN] live_voice fallback: {e2}")
                self.live_voice = None

        try:
            from app.voice.wake import WakeWordManager
            self.wake_manager = WakeWordManager(self.settings, vault=self.vault)
        except Exception as e:
            print(f"[WARN] wake_manager: {e}")
            self.wake_manager = None

        # ── Proactive Monitor ─────────────────────────────────────────────
        try:
            from app.proactive.monitor import ProactiveMonitor
            self.proactive = ProactiveMonitor(self.settings, self._proactive_event)
        except Exception as e:
            print(f"[WARN] proactive: {e}")
            self.proactive = None

        # ── Connectors (weather / calendar / email) ───────────────────────
        try:
            from app.connectors import WeatherConnector, CalendarConnector
            self._weather = WeatherConnector()
            self._calendar = CalendarConnector()
        except Exception as e:
            print(f"[WARN] connectors: {e}")
            self._weather = _NullConnector()
            self._calendar = _NullConnector()

        try:
            from app.connectors.email import EmailConnector
            self._email = EmailConnector()
        except Exception as e:
            print(f"[WARN] email connector: {e}")
            self._email = _NullConnector()

        print("[ULTRON-RUNTIME] Başlatma tamamlandı.", flush=True)

    # ── Internal helpers ─────────────────────────────────────────────────
    def _cached_models(self):
        from app.tools.ollama_tools import ollama_status
        now = _time.time()
        if now - self._models_cache["ts"] > 30:
            try:
                self._models_cache["models"] = (
                    ollama_status(self.brain.base_url, self.brain.model) or {}
                ).get("models") or []
            except Exception:
                self._models_cache["models"] = []
            self._models_cache["ts"] = now
        return self._models_cache["models"]

    def _proactive_event(self, message: str) -> None:
        pass  # Bridge tarafından override edilir

    # ── Public API ───────────────────────────────────────────────────────
    def self_awareness_report(self):
        if self.self_awareness:
            return self.self_awareness.report()
        return {"ok": False, "error": "self_awareness unavailable"}

    def self_diagnostic(self):
        from app.telemetry.system_stats import get_system_stats
        from app.tools.ollama_tools import ollama_status
        from app.core import doctor as doctor_mod

        try:
            stats = get_system_stats()
        except Exception as exc:
            stats = {"error": str(exc)}

        data_dir = self.root / "data"
        db_paths = [str(x) for x in data_dir.rglob("*.db")] if data_dir.exists() else []

        doctor = doctor_mod.run_doctor({
            "ollama_host": getattr(self.brain, "base_url", "http://127.0.0.1:11434"),
            "db_paths": db_paths,
            "rules_path": str(self.root / "config/security/master_rules.json"),
            "ports": (8000, 5173, 5174),
            "allow_busy_ports": True,
        }, persona=getattr(self.agent, "persona", None))

        try:
            ollama = ollama_status(
                getattr(self.brain, "base_url", ""),
                getattr(self.brain, "model", ""),
            )
        except Exception as exc:
            ollama = {"connected": False, "error": str(exc), "models": []}

        voice_backend = self.tts.backend() if hasattr(self.tts, "backend") else "unknown"

        checks = {
            "agent": self.agent is not None,
            "tools": bool(getattr(self.registry, "names", lambda: [])()),
            "memory": self.memory is not None,
            "semantic_memory": self.semantic_memory is not None,
            "planner": self.planner is not None,
            "model_router": self.router is not None,
            "local_voice": voice_backend in ("piper-local", "espeak-ng-local"),
            "vision": self.vision_llm is not None,
            "proactive": self.proactive is not None,
        }
        components = {k: {"status": "OK" if v else "WARN"} for k, v in checks.items()}
        components["local_voice"]["backend"] = voice_backend
        components["ollama"] = {
            "status": "OK" if ollama.get("connected") else "WARN",
            "model": getattr(self.brain, "model", "?"),
            "installed": bool(ollama.get("model_installed")),
            "models": ollama.get("models") or [],
        }
        components["doctor"] = {
            "status": {"PASS": "OK", "WARN": "WARN", "FAIL": "ERROR"}.get(doctor.get("overall"), "ERROR"),
            "overall": doctor.get("overall"),
            "summary": doctor.get("summary"),
            "sections": doctor.get("sections", {}),
        }

        recent = self.audit.recent(120) if hasattr(self.audit, "recent") else []
        error_events = {"TOOL_ERROR", "ERROR", "EXCEPTION", "FAIL", "FAILED",
                        "BAŞARISIZ", "HATA", "RUNTIME_ERROR"}
        error_lines = []
        for line in recent:
            parts = [x.strip() for x in line.split("|", 2)]
            event = parts[1].upper() if len(parts) >= 2 else ""
            if event in error_events or event.endswith("_ERROR"):
                error_lines.append(line)
        components["recent_errors"] = {
            "status": "WARN" if error_lines else "OK",
            "count": len(error_lines),
            "latest": error_lines[:5],
        }

        cpu = stats.get("cpu_percent") if isinstance(stats, dict) else None
        ram = stats.get("ram_percent") if isinstance(stats, dict) else None
        disk = stats.get("disk_percent") if isinstance(stats, dict) else None
        components["hardware"] = {
            "status": "WARN" if any(v is not None and v >= 95 for v in (cpu, ram, disk)) else "OK",
            "cpu_percent": cpu, "ram_percent": ram, "disk_percent": disk,
            "gpus": stats.get("gpus", []) if isinstance(stats, dict) else [],
        }

        statuses = [v.get("status") for v in components.values()]
        overall = "ERROR" if "ERROR" in statuses else ("WARN" if "WARN" in statuses else "OK")
        warnings = [k for k, v in components.items() if v.get("status") == "WARN"]
        errors = [k for k, v in components.items() if v.get("status") == "ERROR"]
        headline = {
            "OK": "Tüm çekirdek kontroller geçti.",
            "WARN": "Sistem çalışıyor; bazı bölümlerde uyarı var.",
            "ERROR": "Kritik hata tespit edildi.",
        }[overall]
        report = (
            f"Boss, tam öz-teşhis tamamlandı. Genel durum: {overall}. {headline} "
            f"CPU {cpu if cpu is not None else 'N/A'}%, "
            f"RAM {ram if ram is not None else 'N/A'}%, "
            f"Disk {disk if disk is not None else 'N/A'}%. "
            f"Lokal ses: {voice_backend or 'UNAVAILABLE'}. "
            f"Ollama: {'OK' if ollama.get('connected') else 'WARN'}. "
            f"Son hata taraması: {len(error_lines)}. "
            f"Uyarılar: {', '.join(warnings) if warnings else 'yok'}. "
            f"Hatalar: {', '.join(errors) if errors else 'yok'}."
        )
        result = {
            "ok": overall != "ERROR", "overall": overall,
            "report": report, "ts": _time.time(),
            "components": components, "doctor": doctor, "system": stats,
        }
        if hasattr(self.audit, "write"):
            self.audit.write("SELF_DIAGNOSTIC",
                             f"overall={overall} warnings={len(warnings)} errors={len(errors)}")
        return result

    def _register_tools(self):
        from app.tools.system_tools import system_status
        from app.tools.windows_tools import (
            open_application, open_url, close_application, open_file, open_folder,
        )
        from app.tools.file_tools import (
            find_files, read_text, write_text, list_directory, find_project,
            copy_path, move_path, rename_path, create_folder, delete_path,
        )
        from app.tools.browser_tools import search_web
        from app.tools.diagnostic_tools import run_diagnostic
        from app.tools.calculator import calculate
        from app.tools.ollama_tools import ollama_status
        from app.vision.screen import capture_screen, screen_ocr

        if self.sandbox:
            from app.security.sandbox import (
                sandboxed_read_text, sandboxed_write_text,
                sandboxed_list_directory, sandboxed_find_files,
            )
            _read = lambda path: sandboxed_read_text(self.sandbox, path)
            _write = lambda path, content: sandboxed_write_text(self.sandbox, path, content)
            _list = lambda root: sandboxed_list_directory(self.sandbox, root)
            _find = lambda root, pattern: sandboxed_find_files(self.sandbox, root, pattern)
        else:
            _read = read_text
            _write = write_text
            _list = list_directory
            _find = find_files

        reg = self.registry
        reg.register("system_status", system_status, "Gerçek sistem telemetrisi getirir.")
        reg.register("self_diagnostic", self.self_diagnostic,
                     "ULTRON'un tüm çekirdek modüllerini salt-okunur biçimde teşhis eder.")
        reg.register("self_awareness", self.self_awareness_report,
                     "ULTRON'un gerçek yeteneklerini ve mevcut yerel durumunu salt-okunur bildirir.")
        reg.register("open_application", open_application, "Windows uygulaması açar.",
                     {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]})
        reg.register("open_url", open_url, "URL'yi varsayılan tarayıcıda açar.",
                     {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]})
        reg.register("search_web", search_web, "Web araması açar.",
                     {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]})
        reg.register("calculate", calculate, "Güvenli matematik hesaplar.",
                     {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]})
        reg.register("list_directory", _list, "Klasör içeriğini listeler.",
                     {"type": "object", "properties": {"root": {"type": "string"}}, "required": ["root"]})
        reg.register("find_files", _find, "Dosya arar.",
                     {"type": "object", "properties": {"root": {"type": "string"}, "pattern": {"type": "string"}}, "required": ["root", "pattern"]})
        reg.register("read_text", _read, "Metin/kod dosyası okur.",
                     {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]})
        reg.register("write_text", _write, "Metin dosyası yazar (onay gerekir).",
                     {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, dangerous=True)
        reg.register("copy_path", copy_path, "Dosya/klasör kopyalar.",
                     {"type": "object", "properties": {"source": {"type": "string"}, "destination": {"type": "string"}}, "required": ["source", "destination"]}, dangerous=True)
        reg.register("move_path", move_path, "Dosya/klasör taşır.",
                     {"type": "object", "properties": {"source": {"type": "string"}, "destination": {"type": "string"}}, "required": ["source", "destination"]}, dangerous=True)
        reg.register("rename_path", rename_path, "Yeniden adlandırır.",
                     {"type": "object", "properties": {"path": {"type": "string"}, "new_name": {"type": "string"}}, "required": ["path", "new_name"]}, dangerous=True)
        reg.register("create_folder", create_folder, "Klasör oluşturur.",
                     {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, dangerous=True)
        reg.register("delete_path", delete_path, "Dosya/klasör siler (onay gerekir).",
                     {"type": "object", "properties": {"path": {"type": "string"}, "permanent": {"type": "boolean"}}, "required": ["path"]}, dangerous=True)
        reg.register("capture_screen", capture_screen, "Ekran görüntüsü alır.")
        reg.register("screen_ocr", screen_ocr, "Ekrandan metin okur.")
        reg.register("run_diagnostic", run_diagnostic, "Sistem tanı çalıştırır.")
        reg.register("ollama_status", lambda: ollama_status(
            getattr(self.brain, "base_url", ""), getattr(self.brain, "model", "")
        ), "Ollama AI motor durumunu sorgular.")

        if self.gui:
            from app.automation.gui import (
                gui_click, gui_type, gui_hotkey, gui_screenshot,
                gui_find_window, gui_locate_and_click,
            )
            for name, fn, desc in [
                ("gui_click", gui_click, "Ekrana tıklar (onay gerekir)."),
                ("gui_type", gui_type, "Metin yazar (onay gerekir)."),
                ("gui_hotkey", gui_hotkey, "Kısayol tuşu basar (onay gerekir)."),
                ("gui_screenshot", gui_screenshot, "Ekran görüntüsü alır."),
                ("gui_find_window", gui_find_window, "Pencere bulur."),
                ("gui_locate_and_click", gui_locate_and_click, "Görseli bulur ve tıklar (onay gerekir)."),
            ]:
                dangerous = name not in ("gui_screenshot", "gui_find_window")
                reg.register(name, fn, desc, dangerous=dangerous)

        # ── Eksik tool'lar: process, close_app, open_file, open_folder ─────
        from app.tools.system_tools import process_list, process_info, process_kill, system_settings_view
        from app.tools.windows_tools import close_application, open_file, open_folder
        from app.tools.file_tools import find_project

        reg.register("process_list", process_list, "Çalışan süreçleri listeler.")
        reg.register("process_info", process_info, "Süreç detayı getirir.",
                     {"type": "object", "properties": {"pid": {"type": "integer"}}, "required": ["pid"]})
        reg.register("process_kill", process_kill, "Süreci sonlandırır (onay gerekir).",
                     {"type": "object", "properties": {"pid": {"type": "integer"}}, "required": ["pid"]},
                     dangerous=True)
        reg.register("system_settings_view", system_settings_view, "Sistem ayarlarını görüntüler.")
        reg.register("close_application", close_application, "Uygulamayı kapatır (onay gerekir).",
                     {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
                     dangerous=True)
        reg.register("open_file", open_file, "Dosyayı varsayılan uygulamayla açar.",
                     {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]})
        reg.register("open_folder", open_folder, "Klasörü dosya gezgininde açar.",
                     {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]})
        reg.register("find_project", find_project, "Proje klasörünü bulur.",
                     {"type": "object", "properties": {"name": {"type": "string"}, "root": {"type": "string"}},
                      "required": ["name"]})

        if self.code_agent:
            reg.register("code_agent_run", lambda goal: self.code_agent.run(goal),
                         "Kod yazan/düzelten AI sub-agent'ı tetikler.",
                         {"type": "object", "properties": {"goal": {"type": "string"}}, "required": ["goal"]},
                         dangerous=True)

    # ── ask() — bridge.py'nin çağırdığı ana giriş noktası ───────────────
    def ask(self, text: str, approved: bool = False) -> str:
        """Bridge'in çağırdığı senkron komut işleyici.
        
        Öncelik sırası:
        1. app/agent/agent.py'nin handle() — tool + memory + LLM tam döngüsü
        2. Fallback: brain.ask() — sadece LLM cevabı
        """
        if self.agent is not None:
            try:
                return self.agent.handle(text, approved=approved)
            except Exception as e:
                import logging
                logging.getLogger("ultron.runtime").error("agent.handle hatası: %s", e)
                # Fallback: brain
        if self.brain is not None:
            try:
                return self.brain.ask(text, system="Sen Ultron'sun, JARVIS tarzı AI asistanısın. Türkçe konuş.")
            except Exception as e:
                return f"İşlemi tamamlayamadım: {e}"
        return "Ultron şu anda çevrimdışı — Ollama çalışıyor mu?"

    # ── Live Voice control ───────────────────────────────────────────────
    def start_live_voice(self) -> dict:
        """Wake-word tabanlı sesi başlat (LiveVoiceV2)."""
        if not self.live_voice:
            return {"ok": False, "error": "live_voice bileşeni yok (sounddevice/faster-whisper kurulu mu?)"}
        try:
            result = self.live_voice.start()
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def stop_live_voice(self) -> None:
        """Sesi durdur."""
        if self.live_voice:
            try:
                self.live_voice.stop()
            except Exception:
                pass

    def set_voice_broadcast(self, fn) -> None:
        """WebSocket broadcast fonksiyonunu LiveVoiceV2'ye ilet."""
        if self.live_voice and hasattr(self.live_voice, "set_ws_broadcast"):
            self.live_voice.set_ws_broadcast(fn)

    def shutdown(self) -> None:
        try:
            if self.proactive:
                self.proactive.stop()
        except Exception:
            pass
        try:
            if self.live_voice:
                self.live_voice.stop()
        except Exception:
            pass


# ── Null nesneler (bileşen başarısız olduğunda sistemin çökmesini önler) ──────

class _NullVault:
    def redact(self, text): return text
    def all_values(self): return []
    def get(self, key, default=None): return default
    def set(self, key, value, **kw): return {"ok": False, "error": "vault unavailable"}
    def delete(self, key): return False
    def list_names(self): return []
    def health(self): return {"ok": False}


class _NullAudit:
    def write(self, *a, **kw): pass
    def recent(self, n=20): return []


class _NullTTS:
    def speak(self, text): pass
    def backend(self): return "unavailable"


class _NullRegistry:
    _tools = {}
    def register(self, name, fn, desc="", schema=None, dangerous=False): self._tools[name] = fn
    def get(self, name): return None
    def names(self): return list(self._tools.keys())


class _NullConnector:
    def health(self): return {"ok": False, "error": "connector unavailable"}
