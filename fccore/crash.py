"""fccore.crash — beklenmeyen hataları yöneticiye bildirir (tur:"cokme"); web FC.crash ile aynı kurallar.
    crash.init(app='organizer', version='2.2.0')
sys.excepthook + threading.excepthook + faulthandler (yerel çökme: bir sonraki açılışta raporlanır).
Aynı hata imzası (sürüm başına) bir kez; günde en çok 5 rapor. Yalnız hata metni, yığın, uygulama, sürüm, platform gider;
e-posta, kullanıcı klasörü, URL sorguları, uzun sayılar ve tırnak içi veriler maskelenir."""
import faulthandler
import os
import re
import sys
import threading
import time
import traceback

from . import storage, contact

MAX_DAY = 5
IGNORE = re.compile(r'ResizeObserver loop|^Script error\.?$|Failed to fetch|NetworkError|Load failed|network error|AbortError|'
                    r'The user aborted|permission-denied|QuotaExceeded|ERR_INTERNET_DISCONNECTED|KeyboardInterrupt', re.I)
cfg = {'app': '', 'version': '', 'now': None, 'send': None}
_installed = False
_fault_file = None


def _now():
    return cfg['now']() if cfg.get('now') else time.time()


def day():
    return time.strftime('%Y-%m-%d', time.gmtime(_now()))


def _quoted(m):
    q, inner = m.group(1), m.group(2)
    return m.group(0) if re.fullmatch(r'[\w$.\-\[\]]{0,40}', inner) else q + '…' + q


def sanitize(s, mx=600):
    s = '' if s is None else str(s)
    s = re.sub(r'[\w.+-]+@[\w-]+(\.[\w-]+)+', '<email>', s)
    s = re.sub(r'''(https?://[^\s?#'")]+)[?#][^\s'")]*''', r'\1', s)
    s = re.sub(r'([A-Za-z]:[\\/]Users[\\/])[^\\/\s]+', r'\1<user>', s, flags=re.I)
    s = re.sub(r'(/(?:home|Users)/)[^/\s]+', r'\1<user>', s)
    s = re.sub(r'(/storage/emulated/\d+/)\S*', r'\1<path>', s)
    s = re.sub(r'\d{6,}', '<n>', s)
    s = re.sub(r'''(["'`])((?:(?!\1).){0,400})\1''', _quoted, s)
    return s[:mx]


def djb2(s):
    h = 5381
    for ch in s:
        # JS charCodeAt: UTF-16 kod birimleri
        for u in ([ord(ch)] if ord(ch) < 0x10000 else [0xD800 + ((ord(ch) - 0x10000) >> 10), 0xDC00 + ((ord(ch) - 0x10000) & 0x3FF)]):
            h = ((h << 5) + h + u) & 0xFFFFFFFF
    return format(h, 'x')


def signature(msg, frames):
    """İmza: maskelenmiş ileti + en içteki iki çerçeve (dosya:işlev, satır numarası yok — derleme farkı imzayı bozmasın)."""
    return djb2(sanitize(msg, 300) + '|' + '|'.join(frames[:2]))


def decide(sig):
    """Göndermeli mi? Gönderecekse sayaçları günceller."""
    if storage.get('crash.enabled', True) is False:
        return False
    key = str(cfg.get('version') or '') + ':' + sig
    seen = storage.get('crash.seen', [])
    if not isinstance(seen, list):
        seen = []
    if key in seen:
        return False
    d, today = storage.get('crash.day'), day()
    if not isinstance(d, dict) or d.get('d') != today:
        d = {'d': today, 'n': 0}
    if d['n'] >= MAX_DAY:
        return False
    d['n'] += 1
    storage.set('crash.day', d)
    seen.append(key)
    storage.set('crash.seen', seen[-200:])
    return True


def sent_today():
    d = storage.get('crash.day')
    return d['n'] if isinstance(d, dict) and d.get('d') == day() else 0


def _frames(tb):
    out = []
    for fs in reversed(traceback.extract_tb(tb) if tb else []):
        out.append(os.path.basename(fs.filename) + ':' + fs.name)
    return out


def build(exc_type, exc, tb, source='ui'):
    """→ (imza, metin) ya da None (yok sayılır)."""
    msg = (exc_type.__name__ if exc_type else 'Error') + ': ' + str(exc if exc is not None else '')
    if not str(exc or '') and not exc_type:
        return None
    if IGNORE.search(msg):
        return None
    stack = ''.join(traceback.format_exception(exc_type, exc, tb)) if tb else ''
    sig = signature(msg, _frames(tb))
    text = '[' + source + '] ' + sanitize(msg, 600) + ('\n\n' + sanitize(stack, 1800) if stack else '') + '\n\n#' + sig
    return sig, text


def report(exc_type, exc, tb, source='ui'):
    try:
        r = build(exc_type, exc, tb, source)
        if not r or not decide(r[0]):
            return False
        send = cfg.get('send') or (lambda text: contact.post_async({'tur': 'cokme', 'mesaj': text}, use_mail=False))
        send(r[1])
        return True
    except Exception:
        return False


def report_text(text, source='native'):
    sig = djb2(sanitize(text, 300))
    if not decide(sig):
        return False
    msg = '[' + source + '] ' + sanitize(text, 2400) + '\n\n#' + sig
    (cfg.get('send') or (lambda t: contact.post_async({'tur': 'cokme', 'mesaj': t}, use_mail=False)))(msg)
    return True


def install(fault_dir=None):
    global _installed, _fault_file
    if _installed:
        return
    _installed = True
    prev = sys.excepthook

    def hook(t, e, tb):
        report(t, e, tb, 'ui')
        prev(t, e, tb)
    sys.excepthook = hook
    prev_t = threading.excepthook

    def thook(a):
        if a.exc_type is not SystemExit:
            report(a.exc_type, a.exc_value, a.exc_traceback, 'thread')
        prev_t(a)
    threading.excepthook = thook
    # yerel çökme (segfault vb.): dosyaya yaz, sonraki açılışta raporla
    try:
        d = fault_dir or os.path.dirname(storage.path() or '') or None
        if d:
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, 'cokme-yerel.log')
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                with open(p, 'r', encoding='utf-8', errors='replace') as f:
                    old = f.read()[-4000:]
                lines = [ln for ln in old.splitlines() if ln.strip() and not ln.startswith('Current thread') and 'File' in ln][:6]
                if 'Fatal Python error' in old or lines:
                    head = old.strip().splitlines()[0] if old.strip() else 'native crash'
                    report_text(head + '\n' + '\n'.join(lines))
            _fault_file = open(p, 'w', encoding='utf-8')
            faulthandler.enable(_fault_file, all_threads=True)
    except Exception:
        pass


def init(app=None, version=None, send=None, fault_dir=None):
    if app is not None:
        cfg['app'] = app
    if version is not None:
        cfg['version'] = version
    if send is not None:
        cfg['send'] = send
    install(fault_dir)


def card():
    from .cards import crash_card
    return crash_card()
