"""fccore.storage — kalıcı anahtar/değer deposu (web FC.storage karşılığı; anahtarlar aynı: lang, theme, scheme, fontScale, …).

Tek JSON dosyası, atomik yazma (geçici dosya + os.replace). Yazılamazsa bellekte tutar; program bu yüzden asla çökmez.
Varsayılan yer: Windows %APPDATA%\\FalconCekirdek\\<uygulama>\\fccore.json, macOS ~/Library/Application Support/…,
Linux $XDG_CONFIG_HOME (~/.config)/FalconCekirdek/<uygulama>/. Uygulama kendi veri klasörünü verebilir: storage.use(yol).
"""
import json
import os
import sys
import tempfile
import threading

_lock = threading.RLock()
_mem = {}
_path = None
_volatile = False


def default_dir(app='fccore'):
    if sys.platform.startswith('win'):
        base = os.environ.get('APPDATA') or os.path.expanduser('~\\AppData\\Roaming')
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(base, 'FalconCekirdek', app or 'fccore')


def use(path=None, app=None):
    """Depo dosyasını seç. path klasörse içine fccore.json yazılır. path=None → bellek kipi (testler)."""
    global _path, _mem, _volatile
    with _lock:
        _mem = {}
        if path is None and app is None:
            _path, _volatile = None, True
            return
        if path is None:
            path = default_dir(app)
        if os.path.isdir(path) or not path.endswith('.json'):
            path = os.path.join(path, 'fccore.json')
        _path, _volatile = path, False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
            if isinstance(d, dict):
                _mem = d
        except (OSError, ValueError):
            pass


def path():
    return _path


def volatile():
    return _path is None or _volatile


def _flush():
    global _volatile
    if not _path:
        return False
    try:
        os.makedirs(os.path.dirname(_path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.fccore-', suffix='.tmp', dir=os.path.dirname(_path))
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(_mem, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _path)
        return True
    except OSError:
        _volatile = True
        return False


def get(key, default=None):
    with _lock:
        if _path is None and not _volatile:
            use(app='fccore')
        v = _mem.get(key, None)
        return default if v is None else json.loads(json.dumps(v))


def set(key, value):  # noqa: A001 — web ile aynı ad
    with _lock:
        if _path is None and not _volatile:
            use(app='fccore')
        _mem[key] = json.loads(json.dumps(value))
        return _flush()


def remove(key):
    with _lock:
        _mem.pop(key, None)
        _flush()


def all_items():
    with _lock:
        return dict(_mem)
