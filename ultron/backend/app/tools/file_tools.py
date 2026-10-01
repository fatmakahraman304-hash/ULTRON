from pathlib import Path
import shutil

HOME = Path.home()


def _win_desktop():
    """Windows Desktop yolunu Registry üzerinden güvenilir şekilde bulur."""
    import sys as _sys
    if _sys.platform != "win32":
        return HOME / "Desktop"
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders")
        val, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        p = Path(os.path.expandvars(val))
        if p.exists():
            return p
    except Exception:
        pass
    try:
        import ctypes, ctypes.wintypes
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(0, 0, 0, 0, buf)
        if buf.value and Path(buf.value).exists():
            return Path(buf.value)
    except Exception:
        pass
    return HOME / "Desktop"


def known_folder(name):
    n = name.lower().strip()
    desktop = _win_desktop()
    mapping = {
        "masaüstü": desktop, "masaüstüm": desktop, "desktop": desktop,
        "indirilenler": HOME / "Downloads", "downloads": HOME / "Downloads",
        "belgeler": HOME / "Documents",  "documents": HOME / "Documents",
        "müzik": HOME / "Music",         "music": HOME / "Music",
        "resimler": HOME / "Pictures",   "pictures": HOME / "Pictures",
        "videolar": HOME / "Videos",     "videos": HOME / "Videos",
    }
    return mapping.get(n)
def list_directory(root):
    """Klasör içeriğini listeler. Türkçe yer isimleri (masaüstü vb.) destekler."""
    # Önce Türkçe/bilinen klasör adı mı diye kontrol et
    resolved = known_folder(str(root).strip())
    p = Path(resolved) if resolved is not None else Path(root).expanduser()
    
    if not p.exists():
        # Kullanıcıya anlamlı hata
        return {"error": f"Klasör bulunamadı: {p}", "path": str(p),
                "hint": "Lütfen tam yolu belirtin (örn: C:/Users/Boss/Desktop)"}
    if not p.is_dir():
        return {"error": f"Bu bir klasör değil: {p}", "path": str(p)}
    
    items = []
    try:
        for x in sorted(p.iterdir(), key=lambda q: (not q.is_dir(), q.name.lower()))[:300]:
            items.append({"name": x.name, "type": "folder" if x.is_dir() else "file", "path": str(x)})
    except PermissionError as e:
        return {"error": f"Erişim reddedildi: {e}", "path": str(p)}
    return items


def find_files(root, pattern):
    root=Path(root).expanduser()
    if not root.exists(): raise FileNotFoundError(str(root))
    return [str(p) for p in root.rglob(pattern) if p.is_file()][:300]


def find_project(start=None, name_hint="Ultron"):
    roots=[]
    if start: roots.append(Path(start).expanduser())
    roots += [HOME/"Downloads", HOME/"Desktop", HOME/"Documents"]
    seen=set()
    for root in roots:
        if not root.exists(): continue
        try:
            for p in root.rglob("*"):
                if not p.is_dir(): continue
                s=str(p).lower()
                if s in seen: continue
                seen.add(s)
                if name_hint.lower() in p.name.lower():
                    markers=list(p.glob("requirements*.txt"))+list(p.glob("pyproject.toml"))+list(p.glob("tests"))
                    if markers: return str(p)
        except (PermissionError,OSError):
            continue
    return None


def read_text(path):
    p=Path(path); return p.read_text(encoding="utf-8",errors="replace")[:50000]


def _workspace():
    return Path.cwd().resolve()


def _inside(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _write_path(path):
    p=Path(path).expanduser().resolve()
    if not _inside(p, _workspace()): raise PermissionError(f"filesystem write outside workspace rejected: {p}")
    return p


def write_text(path, content):
    p=_write_path(path)
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8"); return str(p)


def copy_path(source, destination):
    src=Path(source).expanduser().resolve(); dst=_write_path(destination)
    if not src.exists(): raise FileNotFoundError(str(src))
    if dst.exists(): raise FileExistsError(str(dst))
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir(): shutil.copytree(src, dst)
    else: shutil.copy2(src, dst)
    return {"source":str(src),"destination":str(dst)}


def move_path(source, destination):
    src=_write_path(source); dst=_write_path(destination)
    if not src.exists(): raise FileNotFoundError(str(src))
    if dst.exists(): raise FileExistsError(str(dst))
    dst.parent.mkdir(parents=True, exist_ok=True)
    result=shutil.move(str(src), str(dst))
    return {"source":str(src),"destination":str(result)}


def rename_path(path, new_name):
    src=_write_path(path)
    if not src.exists(): raise FileNotFoundError(str(src))
    name=Path(new_name).name
    if name != new_name or not name: raise ValueError("new_name yalnızca dosya/klasör adı olmalı")
    dst=src.with_name(name)
    if dst.exists(): raise FileExistsError(str(dst))
    src.rename(dst)
    return {"source":str(src),"destination":str(dst)}


def create_folder(path):
    p=_write_path(path)
    if p.exists(): raise FileExistsError(str(p))
    p.mkdir(parents=True)
    return str(p)


def delete_path(path):
    p=_write_path(path)
    if not p.exists(): raise FileNotFoundError(str(p))
    if p.is_dir(): shutil.rmtree(p)
    else: p.unlink()
    return str(p)
