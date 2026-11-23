"""Çökme / hata raporu: beklenmeyen hatalar kaydedilir ve tek tıkla admin'e gönderilir.

Rapor yalnızca teknik bilgi içerir (hata izi, sürüm, işletim sistemi, son işlemler); log dosyası,
API anahtarı veya kişisel veri gönderilmez.
"""
from __future__ import annotations
import collections, faulthandler, os, platform, sys, threading, time, traceback
from .paths import data_dir

TRAIL = collections.deque(maxlen=40)   # son işlemler
_hook = {'cb': None}
_fault_f = None


def note(s):
    TRAIL.append(f"{time.strftime('%H:%M:%S')} {s}")


def _dir():
    d = os.path.join(data_dir(), 'crashes'); os.makedirs(d, exist_ok=True); return d


def build_report(tb_text, title='Unhandled exception'):
    from ..version import VERSION, APP_NAME
    lines = [f'{APP_NAME} v{VERSION} — {title}', f'Zaman: {time.strftime("%Y-%m-%d %H:%M:%S")}',
             f'OS: {platform.platform()} · Python {platform.python_version()} · frozen={bool(getattr(sys, "frozen", False))}', '',
             tb_text.strip(), '', 'Son işlemler:'] + list(TRAIL)
    txt = '\n'.join(lines)
    for k in ('api_key', 'gh_token', 'gemini_key'):
        pass
    # Olası anahtar/token kalıplarını maskele
    import re
    txt = re.sub(r'(sk-ant-|ghp_|github_pat_|AIza|AQ\.)[A-Za-z0-9_\-\.]{8,}', r'\1***', txt)
    return txt


def save(report):
    p = os.path.join(_dir(), time.strftime('crash_%Y%m%d_%H%M%S.txt'))
    with open(p, 'w', encoding='utf-8') as f: f.write(report)
    return p


def pending():
    """Gönderilmemiş raporlar (önceki oturumdan) + sert çökme kaydı."""
    out = []
    d = _dir()
    for f in sorted(os.listdir(d)):
        if f.startswith('crash_') and f.endswith('.txt'): out.append(os.path.join(d, f))
    fl = os.path.join(d, 'fault.log')
    if os.path.exists(fl) and os.path.getsize(fl) > 0 and not _fault_f:
        p = save(build_report(open(fl, encoding='utf-8', errors='replace').read()[-6000:], 'Fatal error (previous session)'))
        try: os.remove(fl)
        except Exception: pass
        out.append(p)
    return out


def send(paths, lang='tr', note_text=''):
    from .contact import send as csend
    body = (note_text.strip() + '\n\n' if note_text else '') + '\n\n=====\n\n'.join(open(p, encoding='utf-8').read()[-7000:] for p in paths)
    ok = csend('[ÇÖKME RAPORU / CRASH REPORT]\n' + body[:3900], name='crash-report', lang=lang)
    if ok:
        for p in paths:
            try: os.replace(p, p.replace('crash_', 'sent_'))
            except Exception: pass
    return ok


def install(on_crash=None):
    """Global yakalayıcılar. on_crash(report_path) ana iş parçacığında çağrılmalı (Qt sinyali ile)."""
    global _fault_f
    _hook['cb'] = on_crash
    try:
        # Önceki oturumdan kalan sert çökme kaydını önce raporla
        pending()
        _fault_f = open(os.path.join(_dir(), 'fault.log'), 'w', encoding='utf-8')
        faulthandler.enable(_fault_f)
    except Exception:
        pass

    def exc(t, v, tb):
        if issubclass(t, KeyboardInterrupt): return
        txt = ''.join(traceback.format_exception(t, v, tb))
        try: sys.__stderr__ and sys.__stderr__.write(txt)
        except Exception: pass
        p = save(build_report(txt))
        if _hook['cb']:
            try: _hook['cb'](p)
            except Exception: pass
    sys.excepthook = exc
    threading.excepthook = lambda a: exc(a.exc_type, a.exc_value, a.exc_traceback)


def shutdown():
    """Normal kapanışta sert çökme kaydını temizle."""
    global _fault_f
    try:
        faulthandler.disable()
        if _fault_f: _fault_f.close(); os.remove(os.path.join(_dir(), 'fault.log'))
    except Exception:
        pass
    _fault_f = None
