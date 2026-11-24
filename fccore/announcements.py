"""fccore.announcements — yönetici duyuruları (departures-mil/duyurular duyurular.json; istemci/duyuru_istemci.py ile aynı kurallar,
çekirdek tasarımıyla). 30 dk'da bir yenilenir; çevrimdışıyken önbellek. Yeni duyuru bir kez kendiliğinden açılır.
    ann = announcements.start(app='organizer', version='2.2.0', on_update=ctl.run)
    topbar.mount(before=[ann.button()], ...)
Alanlar: id, tarih, baslik{tr,en,ar}, metin{…}, hedef['*'|uygulama], aktif, baslangic, bitis, altSurum, ustSurum, link, onem:'onemli', guncellemeDugmesi."""
import json
import threading
import time
import urllib.request
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QFrame

from . import storage, i18n, icons
from .i18n import t

SRC = 'https://raw.githubusercontent.com/departures-mil/duyurular/main/duyurular.json'


def cmp_loose(a, b):
    def p(v):
        return [int(x) if x.isdigit() else 0 for x in str(v).lstrip('vV').lstrip('.').split('.')]
    x, y = p(a), p(b)
    n = max(len(x), len(y))
    x += [0] * (n - len(x))
    y += [0] * (n - len(y))
    return (x > y) - (x < y)


def _ts(s):
    try:
        return datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp()
    except Exception:
        return None


def fits(d, app, version, now=None):
    if not isinstance(d, dict) or not d.get('id') or d.get('aktif') is False:
        return False
    h = d.get('hedef') or ['*']
    if '*' not in h and app not in h:
        return False
    now = now or time.time()
    b, e = _ts(d.get('baslangic')), _ts(d.get('bitis'))
    if (d.get('baslangic') and b and b > now) or (d.get('bitis') and e and e < now):
        return False
    if d.get('altSurum') and cmp_loose(version, d['altSurum']) < 0:
        return False
    if d.get('ustSurum') and cmp_loose(version, d['ustSurum']) > 0:
        return False
    return True


class Announcements(QObject):
    _got = Signal(list)
    changed = Signal()

    def __init__(self, app='', version='0.0.0', on_update=None, source=SRC, interval_min=30, auto_open=True, fetch=None):
        super().__init__()
        self.app, self.version, self.on_update = app, str(version), on_update
        self.source, self.auto_open, self.fetch = source, auto_open, fetch
        self.list, self.queue, self.open_, self.btns = [], [], False, []
        self._got.connect(self.ingest, Qt.QueuedConnection)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(max(5, interval_min) * 60000)

    def seen(self):
        a = storage.get('ann.seen', [])
        return a if isinstance(a, list) else []

    def mark_seen(self, i):
        a = self.seen()
        if i not in a:
            a.append(i)
            storage.set('ann.seen', a[-300:])

    def unread(self):
        s = self.seen()
        return len([d for d in self.list if d['id'] not in s])

    def refresh(self):
        def w():
            try:
                if self.fetch:
                    j = self.fetch(self.source)
                else:
                    req = urllib.request.Request(self.source + '?t=%d' % (time.time() // 60), headers={'User-Agent': 'FalconCekirdek-Qt/1.0', 'Cache-Control': 'no-cache'})
                    with urllib.request.urlopen(req, timeout=20) as r:
                        j = json.loads(r.read().decode('utf-8'))
                a = (j or {}).get('duyurular') or []
                storage.set('ann.cache', a)
            except Exception:
                a = storage.get('ann.cache', []) or []
            self._got.emit(a)
        threading.Thread(target=w, name='fc-ann', daemon=True).start()

    def ingest(self, all_):
        self.list = sorted([d for d in all_ or [] if fits(d, self.app, self.version)], key=lambda d: str(d.get('tarih', '')), reverse=True)
        s = self.seen()
        for d in reversed(self.list):
            if d['id'] not in s and not any(q['id'] == d['id'] for q in self.queue):
                self.queue.append(d)
        self.draw()
        if self.auto_open:
            self.next()

    def _item(self, d):
        from .widgets import label, link
        box = QFrame()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 8, 0, 8)
        v.setSpacing(4)
        h = QHBoxLayout()
        h.setSpacing(8)
        if d.get('onem') == 'onemli':
            h.addWidget(label(t('fc.ann.important'), 'fc-tag'))
        ti = label(i18n.pick(d.get('baslik')), wrap=True)
        ti.setStyleSheet('font-weight:700')
        h.addWidget(ti, 1)
        v.addLayout(h)
        try:
            dt = datetime.fromisoformat(str(d.get('tarih')).replace('Z', '+00:00'))
            ds = dt.strftime('%d.%m.%Y') if i18n.lang() == 'tr' else dt.strftime('%m/%d/%Y') if i18n.lang() == 'en' else dt.strftime('%d/%m/%Y')
        except Exception:
            ds = ''
        v.addWidget(label(ds, 'field-hint'))
        v.addWidget(label(i18n.pick(d.get('metin')), wrap=True))
        if d.get('link'):
            v.addWidget(link('↗ ' + t('fc.ann.link'), d['link']))
        return box

    def next(self):
        from .widgets import Modal, _top
        if self.open_ or not self.queue or _top() is None:
            return
        d = self.queue.pop(0)
        self.open_ = True
        b = []
        if d.get('guncellemeDugmesi') and self.on_update:
            b.append({'label': t('fc.ann.update'), 'icon': 'download', 'on_click': lambda m: self.on_update()})
        b.append({'label': t('fc.ok'), 'cls': 'primary'})

        def closed():
            self.mark_seen(d['id'])
            self.open_ = False
            self.draw()
            QTimer.singleShot(300, self.next)
        Modal(title=t('fc.ann.title'), icon='bell', size='small', body=self._item(d), buttons=b, on_close=closed)

    def show_list(self):
        from .widgets import Modal, label
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 0, 0)
        if self.list:
            for d in self.list:
                v.addWidget(self._item(d))
        else:
            v.addWidget(label(t('fc.ann.none'), 'muted'))
        for d in self.list:
            self.mark_seen(d['id'])
        self.draw()
        return Modal(title=t('fc.ann.title'), icon='bell', body=body, buttons=[{'label': t('fc.close'), 'cls': 'primary'}])

    def button(self):
        from .widgets import button
        b = button('', 'icon-btn ann-btn', icon='bell', role='muted', slot=self.show_list)
        b.attach_badge = lambda host: self._attach(b, host)
        self.btns.append(b)
        i18n.on_change(lambda l: self.draw())
        self.draw()
        return b

    def _attach(self, b, host):
        from .window import _Badge
        b.badge = _Badge(b, host)
        self.draw()

    def draw(self):
        n = self.unread()
        for b in self.btns:
            try:
                b.setToolTip(t('fc.ann.title') + (' (%d)' % n if n else ''))
                if getattr(b, 'badge', None):
                    b.badge.set(n if n else '')
            except RuntimeError:
                pass


_inst = None


def start(app='', version='0.0.0', on_update=None, first_delay_ms=4000, **kw):
    global _inst
    _inst = Announcements(app, version, on_update, **kw)
    QTimer.singleShot(first_delay_ms, _inst.refresh)
    return _inst


def instance():
    return _inst
