"""fccore.i18n — tr / en / ar sözlükleri (web FC.i18n ile AYNI anahtarlar ve metinler; _strings.py web'den üretilir).

    from fccore import i18n
    i18n.add({'tr': {...}, 'en': {...}, 'ar': {...}})   # uygulama sözlüğü (birleştirilir)
    i18n.t('fc.update.avail', {'v': '1.2.0'})
    i18n.set('ar')                                       # kalıcı; QApplication RTL olur, on_change aboneleri çağrılır
Eksik anahtarda en → tr → anahtarın kendisi döner. Arapçada teknik sayılar Batı rakamlarıyla yazılır (num()).
"""
import copy
import locale as _locale
import os
import re
from decimal import Decimal, ROUND_HALF_UP

from . import storage
from ._strings import STRINGS

LANGS = ['tr', 'en', 'ar']
NAMES = {'tr': 'Türkçe', 'en': 'English', 'ar': 'العربية'}
SHORT = {'tr': 'TR', 'en': 'EN', 'ar': 'ع'}
D = copy.deepcopy(STRINGS)
_cur = None
_subs = []


def norm(l):
    l = str(l or '')[:2].lower()
    return l if l in LANGS else None


def detect():
    s = norm(storage.get('lang'))
    if s:
        return s
    for v in (os.environ.get('LANG'), os.environ.get('LANGUAGE')):
        if norm(v):
            return norm(v)
    try:
        from PySide6.QtCore import QLocale
        n = norm(QLocale.system().name())
        if n:
            return n
    except Exception:
        pass
    try:
        return norm((_locale.getlocale()[0] or '')) or 'tr'
    except Exception:
        return 'tr'


def add(d):
    for l in LANGS:
        for k, v in (d or {}).get(l, {}).items():
            D[l][k] = v


def lang():
    global _cur
    if not _cur:
        _cur = detect()
    return _cur


def is_rtl(l=None):
    return (norm(l) or lang()) == 'ar'


def t(key, vars=None, l=None):  # noqa: A002
    l = norm(l) or lang()
    s = D[l].get(key)
    if s is None:
        s = D['en'].get(key)
    if s is None:
        s = D['tr'].get(key)
    if s is None:
        return key
    if vars:
        s = re.sub(r'\{(\w+)\}', lambda m: str(vars[m.group(1)]) if m.group(1) in vars and vars[m.group(1)] is not None else m.group(0), str(s))
    return s


def set(l):  # noqa: A001
    global _cur
    l = norm(l)
    if not l:
        return
    changed = l != _cur
    _cur = l
    storage.set('lang', l)
    apply()
    if changed:
        for f in list(_subs):
            try:
                f(l)
            except Exception:
                import traceback
                traceback.print_exc()


def on_change(f):
    _subs.append(f)
    return lambda: _subs.remove(f) if f in _subs else None


def apply(app=None):
    """QApplication yönü (ar → sağdan sola). style.apply() yazı tipini ayrıca ayarlar."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        app = app or QApplication.instance()
        if app:
            app.setLayoutDirection(Qt.RightToLeft if is_rtl() else Qt.LeftToRight)
    except Exception:
        pass


def locale_name(l=None):
    l = norm(l) or lang()
    return 'ar-u-nu-latn' if l == 'ar' else 'en-US' if l == 'en' else 'tr-TR'


def num(n, digits=0, l=None):
    """Number.toLocaleString(locale(l), {min/maxFractionDigits: digits}) ile aynı çıktı (yarım yukarı yuvarlama)."""
    l = norm(l) or lang()
    try:
        d = Decimal(repr(float(n))) if not isinstance(n, int) else Decimal(n)
    except Exception:
        return str(n)
    q = d.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    neg = q < 0
    s = format(abs(q), 'f')
    ip, _, fp = s.partition('.')
    grp, dec = ('.', ',') if l == 'tr' else (',', '.')
    ip = re.sub(r'(?<=\d)(?=(\d{3})+$)', grp, ip)
    out = ip + (dec + fp if digits else '')
    if neg and q != 0:
        out = ('‎-' if l == 'ar' else '-') + out
    return out


def pick(obj, l=None):
    if not obj:
        return ''
    if isinstance(obj, str):
        return obj
    l = norm(l) or lang()
    return obj.get(l) or obj.get('en') or obj.get('tr') or obj.get('ar') or ''


def _reset():
    global _cur, _subs
    _cur = None
    _subs = []
