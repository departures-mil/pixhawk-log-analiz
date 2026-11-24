"""Çökme / hata raporu (v1.1.0'dan beri ortak çekirdek fccore.crash ile).

fccore.crash yakalar, imzalar (aynı hata bir kez, günde en çok 5), maskeler ve tek gelen kutusuna (tur: cokme) gönderir.
Pixhawk'a özgü ek: son işlemler izi (`note()`), maskelenip rapora eklenir; ayrıca hata metni yerelde
%APPDATA%/PixhawkLogAnaliz/crashes/ altına kaydedilir. Log dosyası, API anahtarı ya da kişisel veri gönderilmez.
"""
from __future__ import annotations
import collections, os, platform, re, sys, threading, time, traceback
from .paths import data_dir

TRAIL = collections.deque(maxlen=40)   # son işlemler
_hook = {'cb': None}
KEY_RE = re.compile(r'(sk-ant-|ghp_|github_pat_|AIza|AQ\.)[A-Za-z0-9_\-\.]{8,}')


def note(s):
    TRAIL.append(f"{time.strftime('%H:%M:%S')} {s}")


def _dir():
    d = os.path.join(data_dir(), 'crashes'); os.makedirs(d, exist_ok=True); return d


def mask(txt):
    return KEY_RE.sub(r'\1***', txt or '')


def build_report(tb_text, title='Unhandled exception'):
    from ..version import VERSION, APP_NAME
    lines = [f'{APP_NAME} v{VERSION} — {title}', f'Zaman: {time.strftime("%Y-%m-%d %H:%M:%S")}',
             f'OS: {platform.platform()} · Python {platform.python_version()} · frozen={bool(getattr(sys, "frozen", False))}', '',
             tb_text.strip(), '', 'Son işlemler:'] + list(TRAIL)
    return mask('\n'.join(lines))


def save(report):
    p = os.path.join(_dir(), time.strftime('crash_%Y%m%d_%H%M%S.txt'))
    with open(p, 'w', encoding='utf-8') as f: f.write(report)
    return p


def trail_text(n=12):
    """Rapora eklenecek son işlemler: dosya adları ve uzun sayılar fccore.crash.sanitize ile maskelenir."""
    from fccore.crash import sanitize
    return '\n'.join(sanitize(mask(x), 120) for x in list(TRAIL)[-n:])


def send_core(text):
    """fccore.crash gönderim işlevi: maskelenmiş metin + son işlemler → admin gelen kutusu (tur: cokme)."""
    from fccore import contact
    tr = trail_text()
    msg = mask(text) + (('\n\nSon işlemler:\n' + tr) if tr else '')
    contact.post_async({'tur': 'cokme', 'mesaj': msg[:4800]}, use_mail=False)


def install(on_crash=None):
    """Yerel kayıt + arayüze bildirim. fccore.crash.init bundan SONRA çağrılır ve bu kancayı sarar
    (önce çekirdek raporlar, sonra bu kanca yerel kaydı yazar)."""
    _hook['cb'] = on_crash

    def exc(t, v, tb):
        if issubclass(t, KeyboardInterrupt): return
        txt = ''.join(traceback.format_exception(t, v, tb))
        try: sys.__stderr__ and sys.__stderr__.write(txt)
        except Exception: pass
        try: p = save(build_report(txt))
        except Exception: p = ''
        if _hook['cb']:
            try: _hook['cb'](p)
            except Exception: pass
    sys.excepthook = exc
    threading.excepthook = lambda a: exc(a.exc_type, a.exc_value, a.exc_traceback)


def set_callback(on_crash):
    _hook['cb'] = on_crash


def shutdown():
    pass
