"""Mission Planner entegrasyonu.

* Log klasörü izleme: Mission Planner'ın log klasörleri (ve kullanıcının eklediği klasörler) taranır; yeni ve
  yazımı bitmiş bir .BIN/.tlog gelince program uyarır (istenirse otomatik analiz eder).
* Dosya ilişkilendirme: .BIN ve .tlog dosyalarına çift tıklayınca program açılır (yalnızca bu Windows kullanıcısı
  için, yönetici izni gerekmez).
"""
from __future__ import annotations
import json, os, sys, time
from .paths import data_dir

EXTS = ('.bin', '.tlog')
PROGID = 'PixhawkLogAnaliz.Log'


def default_dirs():
    home = os.path.expanduser('~')
    cands = [os.path.join(home, 'Documents', 'Mission Planner', 'logs'),
             os.path.join(home, 'OneDrive', 'Documents', 'Mission Planner', 'logs'),
             os.path.join(home, 'OneDrive', 'Belgeler', 'Mission Planner', 'logs'),
             os.path.join(home, 'Belgeler', 'Mission Planner', 'logs')]
    for env in ('ProgramFiles(x86)', 'ProgramFiles'):
        if os.environ.get(env): cands.append(os.path.join(os.environ[env], 'Mission Planner', 'logs'))
    return [d for d in dict.fromkeys(cands) if os.path.isdir(d)]


class Watcher:
    def __init__(self, dirs):
        self.dirs = [d for d in dirs if d and os.path.isdir(d)]
        self.path = os.path.join(data_dir(), 'watch_state.json')
        try: self.state = json.load(open(self.path, encoding='utf-8'))
        except Exception: self.state = {'known': {}, 'init': []}
        self.pending = {}

    def _save(self):
        try: json.dump(self.state, open(self.path, 'w', encoding='utf-8'))
        except Exception: pass

    def _files(self, d):
        for root, _, files in os.walk(d):
            if root[len(d):].count(os.sep) > 4: continue
            for f in files:
                if f.lower().endswith(EXTS):
                    yield os.path.join(root, f)

    def scan(self):
        """Yeni ve yazımı tamamlanmış dosyaları döndürür."""
        new = []; now = time.time()
        for d in self.dirs:
            first = d not in self.state['init']
            for p in self._files(d):
                try: st = os.stat(p)
                except OSError: continue
                if first:
                    self.state['known'][p] = st.st_size; continue
                if p in self.state['known'] and self.state['known'][p] == st.st_size: continue
                prev = self.pending.get(p)
                if prev == st.st_size and now - st.st_mtime > 8 and st.st_size > 50_000:
                    self.state['known'][p] = st.st_size; self.pending.pop(p, None); new.append(p)
                else:
                    self.pending[p] = st.st_size
            if first: self.state['init'].append(d)
        if new or any(d not in self.state['init'] for d in self.dirs): self._save()
        else: self._save()
        return new


# ----------------------------------------------------------- dosya ilişkilendirme
def exe_path():
    if getattr(sys, 'frozen', False): return sys.executable
    return None


def associate(exe=None):
    """HKCU altında .BIN/.tlog → bu program. True: kaydedildi."""
    if not sys.platform.startswith('win'): return False
    exe = exe or exe_path()
    if not exe: return False
    import winreg
    base = r'Software\Classes'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + '\\' + PROGID) as k:
        winreg.SetValueEx(k, '', 0, winreg.REG_SZ, 'Pixhawk / ArduPilot Log')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + '\\' + PROGID + r'\DefaultIcon') as k:
        winreg.SetValueEx(k, '', 0, winreg.REG_SZ, f'"{exe}",0')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + '\\' + PROGID + r'\shell\open\command') as k:
        winreg.SetValueEx(k, '', 0, winreg.REG_SZ, f'"{exe}" "%1"')
    for ext in EXTS:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + '\\' + ext) as k:
            try: cur = winreg.QueryValueEx(k, '')[0]
            except OSError: cur = ''
            if not cur or cur == PROGID: winreg.SetValueEx(k, '', 0, winreg.REG_SZ, PROGID)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + '\\' + ext + r'\OpenWithProgids') as k:
            winreg.SetValueEx(k, PROGID, 0, winreg.REG_NONE, b'')
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass
    return True


def is_associated():
    if not sys.platform.startswith('win'): return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\.bin\OpenWithProgids') as k:
            winreg.QueryValueEx(k, PROGID); return True
    except OSError:
        return False
