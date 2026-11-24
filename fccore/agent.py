"""fccore.agent — Asistan Agent (web FC.agent'ın PySide6 karşılığı).

Motor `_agent_engine.py` (ÜRETİLİR: web/tools/build-agent-py.js; kaynak python/fc_agent_src.py + web/js/agent.js metinleri).
Bu modül motoru fccore'a bağlar: dil = fccore.i18n, veri = fccore deposunun klasörü, yapay zeka = depodaki `ai`
({'provider', 'key', 'model'}; kullanıcının KENDİ anahtarı), görünüm = Falcon kartı/düğmesi, bildirim = tepsi + toast.
Aynı bilgisayardaki bütün programlar (web, Electron, PySide6, .NET) %APPDATA%/FalconCekirdek/agent/ ile sayaç paylaşır.

    core = fccore.init(app, app_id='organizer', ..., agent=True)          # varsayılan açık
    shell.topbar.mount(..., before=[core.agent.button(), core.ann.button()])
    settings.build(...)                                                    # "Asistan Agent" kartını kendisi ekler
    core.agent.track('Kayıt ekle'); core.agent.task('f42', 'start', 'Fatura')   # isteğe bağlı
    LAN eşitlemesi: paket['agent'] = core.agent.export_share()  →  karşıda core.agent.import_share(paket['agent'])
"""
import os

from . import i18n, storage
from . import _agent_engine as E

_inst = None


def _ai_from_storage():
    try:
        a = storage.get('ai') or {}
        if a.get('key') and a.get('provider') in ('gemini', 'openai', 'anthropic', 'groq'):
            return {'provider': a['provider'], 'key': a['key'], 'model': a.get('model')}
    except Exception:
        pass
    return None


class FcAgent(E.Agent):
    """Motor + Falcon görünümü."""

    def __init__(self, app_id, version='', ai=None, sync=True):
        try:
            data = os.path.join(os.path.dirname(storage.path()), 'agent')
        except Exception:
            data = None
        super().__init__(app_id, version, lang=i18n.lang, ai=ai or _ai_from_storage, data_dir=data, sync=sync)
        self._icon_btns = []
        i18n.on_change(lambda *_: self._emit())

    # ---- üst çubuk düğmesi (duyurular düğmesiyle aynı biçim, okunmamış rozeti)
    def button(self):
        from .widgets import button
        b = button('', 'icon-btn agent-btn', icon='sparkles', role='muted', slot=lambda *_: self.show())
        b.setProperty('fcAgent', True)
        b.attach_badge = lambda host: self._attach(b, host)
        self._icon_btns.append(b)
        self._draw()
        return b

    def _attach(self, b, host):
        from .window import _Badge
        b.badge = _Badge(b, host)
        self._draw()

    def _draw(self):
        super()._draw()
        c, n = self.config(), self.unread()
        for b in list(self._icon_btns):
            try:
                b.setVisible(bool(c['on'] and c['panel']))
                b.setToolTip(self.T('title') + (' (%d)' % n if n else ''))
                if getattr(b, 'badge', None):
                    b.badge.set(n if n else '')
            except RuntimeError:
                self._icon_btns.remove(b)

    # ---- ayarlar kartı: fccore bileşenleriyle (web kartıyla aynı içerik ve sıra)
    def card(self, parent=None, header=True):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QCheckBox, QComboBox, QVBoxLayout, QWidget
        from .widgets import Card, button, field, hbox, label, modal, toast
        c = Card('agent', '', 'sparkles', '')
        c.setProperty('fcAgent', True)
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        c.add(body, 8)

        def chk(text, on, slot, hint=None):
            cb = QCheckBox()
            cb.setChecked(bool(on))
            cb.setProperty('fcAgent', True)
            lab = label(text, wrap=True)
            lab.mousePressEvent = lambda e: cb.toggle()
            row = hbox(cb, lab, spacing=8)
            row.layout().setStretch(1, 1)
            cb.toggled.connect(slot)
            bl.addWidget(row)
            if hint:
                bl.addWidget(label(hint, 'field-hint', wrap=True))
            return cb

        def build():
            while bl.count():
                it = bl.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
            o = self.config()
            c.set_title(self.T('title'))
            c.set_desc(self.T('desc'))

            def setter(k):
                return lambda on: self.configure(**{k: bool(on)})
            chk(self.T('on'), o['on'], setter('on'))
            if o['on']:
                chk(self.T('notify'), o['notify'], setter('notify'))
                chk(self.T('panel'), o['panel'], setter('panel'))
                chk(self.T('ai'), o['ai'], setter('ai'), self.T('noKey') if o['ai'] and not self._ai_cfg() else None)
                cmb = QComboBox()
                for f in E.FREQ:
                    cmb.addItem(self.T('freq.' + f), f)
                cmb.setCurrentIndex(E.FREQ.index(o['freq']))
                cmb.currentIndexChanged.connect(lambda i: self.configure(freq=E.FREQ[i]))
                bl.addWidget(field(self.T('freq'), cmb, top=6))
                bl.addWidget(label(self.T('apps'), 'field-label', wrap=True))
                apps = self.known_apps()
                for a in apps:
                    def ach(on, a=a):
                        cur = [x for x in (self.config()['apps'] or list(apps)) if x != a]
                        if on:
                            cur.append(a)
                        self.configure(apps=None if len(cur) >= len(self.known_apps()) else cur)
                    chk(self.app_name(a), not o['apps'] or a in o['apps'], ach)
                bl.addWidget(label(self.T('appsHint'), 'field-hint', wrap=True))
                sm = self.summary()
                bl.addWidget(label(self.T('status', t=self.hm(sm['tot']['w']), n=len(self.d['notes']), a=self.ai_calls_today(),
                                          m=self.ai_per_day), 'field-hint', wrap=True))
                b1 = button(self.T('analyze'), 'btn small primary', icon='zap')

                def an():
                    b1.setEnabled(False)
                    f = self.analyze(True, wait=True)
                    toast(self.T('newNotes', n=len(f)) if f else self.T('nothing'), 'info')
                b1.clicked.connect(lambda *_: an())
                b2 = button(self.T('showNotes'), 'btn small', icon='sparkles', slot=lambda: self.show(c.window()))

                def clr():
                    modal(title=self.T('clear'), body=label(self.T('clearQ'), wrap=True),
                          buttons=[{'label': i18n.t('fc.cancel')}, 'spacer', {'label': self.T('clear'), 'cls': 'primary', 'on_click': lambda *_: self.clear()}])
                b3 = button(self.T('clear'), 'btn small', slot=clr)
                for b in (b1, b2, b3):
                    b.setProperty('fcAgent', True)
                    bl.addWidget(hbox(b, stretch_end=True))
            bl.addWidget(label(self.T('privacy'), 'field-hint', wrap=True))
        build()
        self.cards.append(build)
        c.destroyed.connect(lambda *_: build in self.cards and self.cards.remove(build))
        return c

    # ---- panel: fccore modalı (haftalık özet + yorumlar)
    def show(self, parent=None):
        from datetime import datetime
        from PySide6.QtWidgets import QFrame, QProgressBar, QScrollArea, QVBoxLayout, QWidget
        from .widgets import hbox, label, modal
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        sc.setMinimumSize(520, 460)
        sc.setWidget(body)
        sc.setStyleSheet('QScrollArea{background:transparent;border:none}')
        sc.viewport().setAutoFillBackground(False)
        body.setObjectName('fcAgentBody')
        body.setStyleSheet('#fcAgentBody{background:transparent}')

        def render():
            while bl.count():
                it = bl.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
            sm = self.summary()
            t = sm['tot']
            bl.addWidget(label(' · '.join([self.T('week', t=self.hm(t['w'])), self.T('days', n=len(t['days'])),
                                           self.T('open', n=len(t['tasks']))]), 'field-label', wrap=True))
            names = sorted([n for n in sm['apps'] if sm['apps'][n]['w'] > 0], key=lambda n: -sm['apps'][n]['w'])[:8]
            mx = sm['apps'][names[0]]['w'] if names else 1
            for n in names:
                w = sm['apps'][n]['w']
                pb = QProgressBar()
                pb.setRange(0, 100)
                pb.setValue(max(4, round(w / mx * 100)))
                pb.setTextVisible(False)
                pb.setFixedHeight(8)
                nm = label(self.app_name(n))
                nm.setMinimumWidth(140)
                row = hbox(nm, pb, label(self.hm(w), 'field-hint'), spacing=10)
                row.layout().setStretch(1, 1)
                bl.addWidget(row)
            bl.addWidget(label(self.T('notes'), 'field-label'))
            if not self.d['notes']:
                bl.addWidget(label(self.T('none'), 'field-hint', wrap=True))
            for n in self.d['notes'][:30]:
                fr = QFrame()
                fr.setObjectName('card')
                fl = QVBoxLayout(fr)
                fl.setContentsMargins(12, 10, 12, 10)
                fl.setSpacing(4)
                tag = self.T('srcAi' if n.get('src') == 'ai' else 'srcOff')
                fl.addWidget(label(tag + ' · ' + datetime.fromtimestamp(n['t'] / 1000).strftime('%d.%m %H:%M'), 'field-hint'))
                tx = label(self.note_text(n), wrap=True)
                if not n.get('read'):
                    tx.setStyleSheet('font-weight:600')
                fl.addWidget(tx)
                bl.addWidget(fr)
            bl.addStretch(1)
        render()

        def analyze_now(m=None):
            self.analyze(True, wait=True)
            render()
            return False   # pencere açık kalsın
        m = modal(parent=parent, title=self.T('title'), icon='sparkles', body=sc, on_close=lambda *_: self._mark_read(),
                  buttons=[{'label': self.T('analyze'), 'icon': 'zap', 'cls': 'primary', 'on_click': analyze_now}, 'spacer',
                           {'label': i18n.t('fc.close')}])
        self._dlg = m
        return m

    # ---- bildirim: tepsi (varsa) + program içi toast
    def _notify(self, title, body):
        shown = super()._notify(title, body)
        try:
            from .widgets import toast
            toast('✦ ' + title + ': ' + body, 'info', 7000)
            return True
        except Exception:
            return shown


def start(app, app_id, version='', window=None, ai=None, sync=True, first_delay_ms=20000):
    """fccore.init çağırır. Pencere verilirse yüzen düğme yerine üst çubuk düğmesi önerilir (button())."""
    global _inst
    if _inst is None:
        _inst = FcAgent(app_id, version, ai=ai, sync=sync)
        _inst.start(app, window, first_delay_ms=first_delay_ms, button=False)
    return _inst


def instance():
    return _inst


def _reset():
    global _inst
    _inst = None
