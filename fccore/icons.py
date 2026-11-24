"""fccore.icons — web ui.js ile aynı çizgi simgeleri (SVG yolları _icons.py'de, web'den üretilir).
    icons.icon('sync', '#22d3ee', 18) → QIcon
    icons.set_icon(btn, 'download', role='accent')   # tema/şema değişince kendiliğinden yeniden boyanır
role bir token adıdır (text, muted, accent, ok-text, danger-text, on-accent …)."""
from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap, QTransform
from PySide6.QtSvg import QSvgRenderer

from ._icons import PATHS
from . import style

_cache = {}


def svg(name, color, stroke=1.9):
    """color: CSS rengi (#rrggbbaa dahil) → QtSvg'nin anladığı stroke + stroke-opacity."""
    r, g, b, a = style.rgba(color)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#%02x%02x%02x" stroke-opacity="%.3f" '
            'stroke-width="%s" stroke-linecap="round" stroke-linejoin="round">%s</svg>' % (r, g, b, a / 255, stroke, PATHS.get(name, '')))


def svg_file(name, color=None, stroke=1.9):
    """QSS image: url(...) için önbellek klasörüne SVG yazar (onay işareti, açılır ok)."""
    import hashlib, os, tempfile
    d = os.path.join(tempfile.gettempdir(), 'fccore-icons')
    os.makedirs(d, exist_ok=True)
    body = svg(name, color, stroke) if name in PATHS else name
    p = os.path.join(d, hashlib.sha1((body).encode()).hexdigest()[:16] + '.svg')
    if not os.path.exists(p):
        with open(p, 'w', encoding='utf-8') as f:
            f.write(body)
    return p.replace(os.sep, '/')


def pixmap(name, color, size=18, dpr=2.0, flip=False):
    key = (name, color, size, dpr, flip)
    pm = _cache.get(key)
    if pm is None:
        n = int(round(size * dpr))
        pm = QPixmap(n, n)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        QSvgRenderer(QByteArray(svg(name, color).encode())).render(p, QRectF(0, 0, n, n))
        p.end()
        if flip:
            pm = pm.transformed(QTransform().scale(-1, 1))
        pm.setDevicePixelRatio(dpr)
        _cache[key] = pm
    return pm


def icon(name, color=None, size=18):
    color = color or style.tok('text')
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size))
    return ic


def set_icon(w, name, role='text', size=None, disabled_role=None):
    """Düğmeye/etikete tema uyumlu simge koyar; style.apply() sonrası refresh_all() yeniler."""
    w.setProperty('fcIcon', name)
    w.setProperty('fcIconRole', role)
    if size:
        w.setProperty('fcIconSize', size)
    _paint(w)


def _paint(w):
    name = w.property('fcIcon')
    if not name:
        return
    role = w.property('fcIconRole') or 'text'
    size = int(w.property('fcIconSize') or 16)
    c = style.tok(role) if not str(role).startswith('#') else role
    if hasattr(w, 'setIcon'):
        w.setIcon(icon(name, c, size))
        w.setIconSize(QSize(size, size))
    elif hasattr(w, 'setPixmap'):
        w.setPixmap(pixmap(name, c, size))


def refresh_all():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        return
    for w in app.allWidgets():
        if w.property('fcIcon'):
            _paint(w)


style.on_change(lambda st: refresh_all())
