import os, sys

def data_dir():
    base = os.environ.get('APPDATA') or os.path.join(os.path.expanduser('~'), '.local', 'share')
    d = os.path.join(base, 'PixhawkLogAnaliz')
    os.makedirs(d, exist_ok=True)
    return d

def res(*p):
    """Paket içi kaynak yolu (PyInstaller uyumlu)."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if getattr(sys, '_MEIPASS', None):
        base = os.path.join(sys._MEIPASS, 'app')
    return os.path.join(base, *p)
