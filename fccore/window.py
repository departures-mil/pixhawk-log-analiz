"""fccore.window — çerçevesiz ana pencere + Falcon kabuğu (kenar çubuğu, üst çubuk, sayfalar).

    win = FcWindow()                 # her açılışta tam ekran; Orta = çalışma alanının %50×%50'si, ortada; tekrar → tam ekran
    shell = Shell(win, name='Organizer', tag='Ajanda ve kayıtlar', version='2.2.0', logo='zap')
    shell.nav_group('nav.main'); shell.page('home', 'nav.home', 'home', widget, sub='sub.home')
    tb = shell.topbar.mount(sync={'on_click': app.sync}, lan={'on_click': app.lan}, update=ctl, before=[ann_button])
    tb.set_sync('idle'|'syncing'|'error'|'off'|'offline', bekleyen); tb.set_lan('on'|'off'|'busy')
    win.start()                      # showFullScreen + "açıldım" işareti

Üst çubuk sırası (LTR): [ek] · Eşitle · Wi-Fi · Güncelle · Tema · Dil | Küçült · Orta · Tam ekran · Kapat.
Arapçada QApplication RTL olduğu için sıra kendiliğinden aynalanır. Üst çubuğun boş alanından pencere sürüklenir."""
from PySide6.QtCore import QObject, QEvent, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea,
                               QSizeGrip, QStackedWidget, QVBoxLayout, QWidget, QSizePolicy)

from . import i18n, style, icons
from .i18n import t
from .widgets import Backdrop, ProgressBox, button, cls, label, toggle_cls


class FcWindow(QMainWindow):
    state_changed = Signal(dict)

    def __init__(self, title=''):
        super().__init__()
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowTitle(title)
        self.half = False
        self.root = Backdrop()
        self.root.setMinimumSize(320, 240)   # içerik en küçük boyutu pencereyi büyütmesin (Orta = yarım ekran)
        self.setCentralWidget(self.root)
        self.grip = QSizeGrip(self.root)
        self.grip.setFixedSize(16, 16)
        self.grip.hide()

    # ---- durum (web host.window karşılığı)
    def state(self):
        return {'fullscreen': self.isFullScreen(), 'half': self.half}

    def _emit(self):
        self.grip.setVisible(self.half)
        self.state_changed.emit(self.state())

    def start(self):
        """Her açılış tam ekran."""
        self.showFullScreen()
        self._emit()

    def minimize(self):
        self.showMinimized()

    def work_area(self):
        scr = self.screen() or QGuiApplication.primaryScreen()
        return scr.availableGeometry()

    def toggle_half(self):
        if self.half:
            self.half = False
            self.showFullScreen()
        else:
            wa = self.work_area()
            w, h = wa.width() // 2, wa.height() // 2
            self.showNormal()
            self.setGeometry(wa.x() + (wa.width() - w) // 2, wa.y() + (wa.height() - h) // 2, w, h)
            self.half = True
        self._emit()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.half = False
            self.showMaximized()
        else:
            self.half = False
            self.showFullScreen()
        self._emit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        r = self.root.rect()
        self.grip.move(r.left() if i18n.is_rtl() else r.right() - 16, r.bottom() - 16)
        self.grip.raise_()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.WindowStateChange:
            self._emit()


class _Badge(QLabel):
    """Düğmenin üst-son köşesine taşan sayı rozeti (üst çubuk kırpmasın diye üst çubuğun çocuğu)."""

    def __init__(self, target, host, kind='sync-badge'):
        super().__init__(host)
        self.target, self.host, self.kind = target, host, kind
        self.setProperty('fc', kind)
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        target.installEventFilter(self)
        self.hide()

    _val = ''

    def eventFilter(self, o, e):
        if e.type() in (QEvent.Move, QEvent.Resize, QEvent.Show, QEvent.LayoutDirectionChange):
            QTimer.singleShot(0, self.place)
        if e.type() == QEvent.Hide:
            self.hide()
        return False

    def set(self, text):
        self._val = str(text or '')
        if self.kind == 'update-dot':
            self.setFixedSize(12, 12)
        else:
            self.setText(self._val)
            self.setFixedHeight(18)
            self.setMinimumWidth(18)
            self.adjustSize()
        self.place()

    def place(self):
        try:
            vis = bool(self._val) and self.target.isVisible()
        except RuntimeError:
            return
        self.setVisible(vis)
        if not vis:
            return
        p = self.target.mapTo(self.host, QPoint(0, 0))
        tw = self.target.width()
        off = -7 if self.kind != 'update-dot' else -3
        rtl = self.target.layoutDirection() == Qt.RightToLeft
        x = p.x() + off if rtl else p.x() + tw - self.width() - off
        self.move(x, p.y() + off)
        self.raise_()


class UpdateFloat(QFrame):
    """Güncelle düğmesinin altında açılan Falcon .update-float."""

    def __init__(self, host):
        super().__init__(host)
        self.setObjectName('fcUpdateFloat')
        self.setAttribute(Qt.WA_StyledBackground, True)
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        self.box = ProgressBox()
        v.addWidget(self.box)
        self.btns = QHBoxLayout()
        self.btns.setContentsMargins(0, 0, 0, 0)
        self.btns.addStretch(1)
        v.addLayout(self.btns)
        self.setFixedWidth(300)
        self.hide()

    def clear_buttons(self):
        while self.btns.count() > 1:
            it = self.btns.takeAt(1)
            if it.widget():
                it.widget().deleteLater()

    def add_button(self, b):
        self.btns.addWidget(b)

    def place(self, anchor, root):
        self.adjustSize()
        p = anchor.mapTo(root, QPoint(0, anchor.height() + 8))
        if anchor.layoutDirection() == Qt.RightToLeft:
            x = p.x()
        else:
            x = p.x() + anchor.width() - self.width()
        x = max(12, min(x, root.width() - self.width() - 12))
        self.move(x, p.y())
        self.raise_()


class TopBar(QFrame):
    """Sağ üst sıra + sol başlık. mount() ile düğmeler kurulur."""
    title_dbl = Signal()

    def __init__(self, win=None):
        super().__init__()
        self.setObjectName('fcTopbar')
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.win = win
        self.h = QHBoxLayout(self)
        self.h.setContentsMargins(32, 16, 24, 16)
        self.h.setSpacing(20)
        tl = QVBoxLayout()
        tl.setSpacing(4)
        tl.setContentsMargins(0, 0, 0, 0)
        self.title = label('', obj='fcPageTitle')
        self.sub = label('', obj='fcPageSub')
        tl.addWidget(self.title)
        tl.addWidget(self.sub)
        self.h.addLayout(tl, 1)
        self.actions = QWidget()
        self.al = QHBoxLayout(self.actions)
        self.al.setContentsMargins(0, 0, 0, 0)
        self.al.setSpacing(8)
        self.h.addWidget(self.actions, 0, Qt.AlignVCenter)
        self._redraws = []
        self._drag = None
        self.sync_state, self.sync_badge, self.lan_state = 'off', 0, 'off'
        i18n.on_change(lambda l: self.redraw())

    def set_title(self, title, sub=''):
        self.title.setText(title)
        self.sub.setText(sub or '')
        self.sub.setVisible(bool(sub))

    def layoutDirectionChanged(self):
        pass

    # ---- kur
    def mount(self, sync=None, lan=None, update=None, before=None, theme=True, lang=True, window_controls=True):
        """sync/lan: {'on_click': f(durum), 'state': ...} ya da False (gizli). update: UpdateController ya da None."""
        for w in before or []:
            self.al.addWidget(w)
            if hasattr(w, 'attach_badge'):
                w.attach_badge(self)
        if sync is not False:
            sync = sync or {}
            self.sync_state = sync.get('state', 'off')
            self.sync_btn = button('', 'btn small top-act sync-act')
            self.sync_btn.clicked.connect(lambda: sync.get('on_click') and sync['on_click'](self.sync_state))
            self.al.addWidget(self.sync_btn)
            self.sync_b = _Badge(self.sync_btn, self)
            self._redraws.append(self._draw_sync)
        if lan is not False:
            lan = lan or {}
            self.lan_state = lan.get('state', 'off')
            self.lan_btn = button('', 'icon-btn lan-act')
            self.lan_btn.clicked.connect(lambda: lan.get('on_click') and lan['on_click'](self.lan_state))
            self.al.addWidget(self.lan_btn)
            self._redraws.append(self._draw_lan)
        if update is not None:
            self.ctl = update
            self.upd_btn = button('', 'btn small top-act update-act')
            self.al.addWidget(self.upd_btn)
            self.upd_dot = _Badge(self.upd_btn, self, 'update-dot')
            self.float = UpdateFloat(self.window_root())
            self.show_result = False
            self._hide_t = QTimer(self)
            self._hide_t.setSingleShot(True)
            self._hide_t.timeout.connect(self._auto_hide)
            self.upd_btn.clicked.connect(self._upd_click)
            update.state_changed.connect(lambda s: self._draw_update())
            self._redraws.append(self._draw_update)
        if theme:
            self.theme_btn = button('', 'icon-btn theme-btn', slot=style.toggle)
            self.al.addWidget(self.theme_btn)
            self._redraws.append(self._draw_theme)
            style.on_change(lambda st: self._draw_theme())
        if lang:
            self.al.addWidget(self._lang_switch())
        if window_controls and self.win is not None:
            sep = QFrame()
            sep.setProperty('fc', 'topbar-sep')
            self.al.addSpacing(4)
            self.al.addWidget(sep)
            self.al.addSpacing(4)
            wc = QWidget()
            wl = QHBoxLayout(wc)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(6)
            self.b_min = button('', 'icon-btn', icon='minus', role='muted', slot=self.win.minimize)
            self.b_half = button('', 'icon-btn', icon='half', role='muted', slot=self.win.toggle_half)
            self.b_full = button('', 'icon-btn', icon='full', role='muted', slot=self.win.toggle_fullscreen)
            self.b_close = button('', 'icon-btn danger', icon='x', role='muted', slot=self.win.close)
            for b, n in ((self.b_min, 'minimize'), (self.b_half, 'half'), (self.b_full, 'fullscreen'), (self.b_close, 'close')):
                b.setProperty('fcWin', n)
                b.setFocusPolicy(Qt.NoFocus)
                wl.addWidget(b)
            self.al.addWidget(wc)
            self.win.state_changed.connect(lambda s: self._draw_win())
            self._redraws.append(self._draw_win)
        for b in self.actions.findChildren(QPushButton):
            b.setFocusPolicy(Qt.NoFocus)
        self.redraw()
        return self

    def window_root(self):
        return self.win.root if self.win is not None else self.parentWidget()

    def redraw(self):
        for f in self._redraws:
            f()

    # ---- Eşitle
    def set_sync(self, state, badge=0):
        self.sync_state, self.sync_badge = state or 'off', int(badge or 0)
        self._draw_sync()

    def _draw_sync(self):
        b, s, n = self.sync_btn, self.sync_state, self.sync_badge
        b.setText(t('fc.sync'))
        cls(b, 'btn small top-act sync-act ' + s)
        role = {'idle': 'ok-text', 'syncing': 'accent', 'error': 'danger-text'}.get(s, 'muted')
        icons.set_icon(b, 'cloudOff' if s in ('off', 'offline') else 'sync', role, 14)
        tip = t('fc.sync.' + s) + (' · ' + t('fc.sync.pending', {'n': n}) if n > 0 else '')
        b.setToolTip(tip)
        b.setAccessibleName(tip)
        b.setEnabled(s != 'syncing')
        self.sync_b.set(('99+' if n > 99 else n) if n > 0 else '')

    # ---- Wi-Fi
    def set_lan(self, state):
        self.lan_state = state or 'off'
        self._draw_lan()

    def _draw_lan(self):
        s = self.lan_state
        cls(self.lan_btn, 'icon-btn lan-act ' + s)
        icons.set_icon(self.lan_btn, 'wifiOff' if s == 'off' else 'wifi', 'ok-text' if s == 'on' else 'accent' if s == 'busy' else 'muted', 16)
        tip = t('fc.lan.on' if s == 'on' else 'fc.lan.busy' if s == 'busy' else 'fc.lan.off')
        self.lan_btn.setToolTip(tip)
        self.lan_btn.setAccessibleName(tip)

    # ---- tema / dil
    def _draw_theme(self):
        light = style.effective() == 'light'
        icons.set_icon(self.theme_btn, 'moon' if light else 'sun', 'muted', 16)
        self.theme_btn.setToolTip(t('fc.theme.toggle'))

    def _lang_switch(self):
        box = QFrame()
        box.setProperty('fc', 'lang-switch')
        h = QHBoxLayout(box)
        h.setContentsMargins(3, 3, 3, 3)
        h.setSpacing(2)
        g = QButtonGroup(box)
        self.lang_btns = {}
        for l in i18n.LANGS:
            b = button(i18n.SHORT[l], 'lang-btn', tip=i18n.NAMES[l])
            b.setCheckable(True)
            b.setFocusPolicy(Qt.NoFocus)
            if l == 'ar':
                b.setFont(style.font(13, 600, 'ar'))
            g.addButton(b)
            h.addWidget(b)
            b.clicked.connect(lambda _=False, l=l: i18n.set(l))
            self.lang_btns[l] = b

        def sync():
            for l, b in self.lang_btns.items():
                b.setChecked(l == i18n.lang())
        self._redraws.append(sync)
        return box

    # ---- pencere düğmeleri
    def _draw_win(self):
        st = self.win.state()
        for b, k in ((self.b_min, 'fc.win.minimize'), (self.b_half, 'fc.win.restore' if st['half'] else 'fc.win.half'),
                     (self.b_full, 'fc.win.fullscreen'), (self.b_close, 'fc.win.close')):
            b.setToolTip(t(k))
            b.setAccessibleName(t(k))

    # ---- Güncelle
    def _busy(self, s):
        return s in ('downloading', 'verifying', 'installing', 'restarting')

    def _upd_click(self):
        st = self.ctl.state
        if st['status'] in ('available', 'ready'):
            self.show_result = False
            self.ctl.run()
        else:
            self.show_result = True
            self.ctl.check()
        self._draw_update()

    def _auto_hide(self):
        self.show_result = False
        self.float.hide()

    def _draw_update(self):
        us = self.ctl.state
        s, p = us['status'], us.get('plan')
        b, fl, box = self.upd_btn, self.float, self.float.box
        bg = bool(us.get('bg')) and not self.show_result and (self._busy(s) or s == 'queued')   # arka plan indirmesi: rahatsız etme
        av = s in ('available', 'ready')
        cls(b, 'btn small top-act update-act' + (' avail' if av else '') + (' busy' if (self._busy(s) and not bg) or s == 'checking' else ''))
        b.setEnabled(not self._busy(s) or bool(us.get('bg')))
        b.setText(t('fc.update'))
        icons.set_icon(b, 'sync' if s == 'checking' else 'download', 'accent' if av else 'text', 14)
        tip = t('fc.update.ready', {'v': p['version']}) if s == 'ready' and p else t('fc.update.avail', {'v': p['version']}) if s == 'available' and p else t('fc.update.none', {'v': us.get('current')}) if s == 'none' else t('fc.update.check')
        b.setToolTip(tip)
        self.upd_dot.set('•' if av else '')
        fl.clear_buttons()
        show = False
        if bg:
            show = False
        elif s == 'ready' and p:
            if not getattr(self, '_ready_shown', False) or self.show_result:
                self._ready_shown = True
                show = True
                box.busy(t('fc.update.ready', {'v': p['version']}))
                box.bar.hide()
                fl.add_button(button(t('fc.update.now'), 'btn small primary', icon='download', slot=self.ctl.run))
                self._hide_t.start(10000)
        elif self._busy(s):
            show = True
            if s == 'downloading' and us.get('progress'):
                box.set_title(t('fc.update.fallback') if us.get('fallback') else t('fc.update.downloading') + (' v' + p['version'] if p else ''))
                box.set(us['progress'], patch=us.get('mode') == 'patch')
            else:
                box.busy(t('fc.update.' + s))
        elif s == 'done':
            show = True
            box.busy(t('fc.update.done'))
            box.bar.hide()
            self._hide_t.start(6000)
        elif self.show_result:
            show = True
            from .progress import mb
            if s == 'checking':
                box.busy(t('fc.update.checking'))
            elif s == 'available' and p:
                box.busy(t('fc.update.avail', {'v': p['version']}))
                box.bar.hide()
                box.detail.setText(t('fc.update.press') + ' · ' + mb(p['size']) + (' · ' + t('fc.update.patchMode') if p['mode'] == 'patch' else ''))
                ub = button(t('fc.update'), 'btn small primary', icon='download', slot=self.ctl.run)
                fl.add_button(ub)
            elif s == 'none':
                box.busy(t('fc.update.none', {'v': us.get('current')}))
                box.bar.hide()
            elif s == 'error' or us.get('error'):
                box.busy(self.ctl.error_text(us.get('error')))
                box.bar.hide()
                fl.add_button(button(t('fc.retry'), 'btn small', slot=lambda: self.ctl.check()))
            if s not in ('checking', 'available'):
                self._hide_t.start(5000)
        fl.setVisible(show)
        if show:
            fl.place(b, self.window_root())

    # ---- sürükleme (çerçevesiz pencere)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.win is not None and not self.win.isFullScreen():
            wh = self.win.windowHandle()
            if wh is not None and wh.startSystemMove():
                return
            self._drag = e.globalPosition().toPoint() - self.win.frameGeometry().topLeft()
        if self.show_result_visible():
            self._auto_hide()

    def show_result_visible(self):
        return getattr(self, 'float', None) is not None and self.float.isVisible() and getattr(self, 'show_result', False)

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton and self.win is not None:
            self.win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        if self.win is not None:
            self.win.toggle_half()


class Shell(QObject):
    """Kenar çubuğu + üst çubuk + sayfalar. Metinler i18n anahtarı ya da düz metin olabilir (dil değişince yenilenir)."""
    page_changed = Signal(str)

    def __init__(self, win, name='', tag='', version='', logo='zap'):
        super().__init__(win)
        self.win = win
        self.name, self.tag, self.version = name, tag, version
        lay = QHBoxLayout(win.root)
        lay.setSizeConstraint(QHBoxLayout.SetNoConstraint)   # Orta (yarım) boyut içerikten küçük olabilir
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        # kenar çubuğu
        self.sidebar = QFrame()
        self.sidebar.setObjectName('fcSidebar')
        self.sidebar.setFixedWidth(264)
        sv = QVBoxLayout(self.sidebar)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        brand = QFrame()
        brand.setObjectName('fcBrand')
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(20, 22, 20, 18)
        bl.setSpacing(12)
        self.logo = QLabel()
        self.logo.setObjectName('fcBrandLogo')
        self.logo.setFixedSize(38, 38)
        self.logo.setAlignment(Qt.AlignCenter)
        icons.set_icon(self.logo, logo, 'on-accent', 18)
        names = QVBoxLayout()
        names.setSpacing(2)
        self.brand_name = label(name, obj='fcBrandName')
        self.brand_tag = label('', obj='fcBrandTag', wrap=True)
        names.addWidget(self.brand_name)
        names.addWidget(self.brand_tag)
        self.vbadge = label('v' + str(version) if version else '', 'version-badge')  # tam sürüm vX.Y.Z (kısaltma yok)
        bl.addWidget(self.logo, 0, Qt.AlignTop)
        bl.addLayout(names, 1)
        bl.addWidget(self.vbadge, 0, Qt.AlignTop)
        sv.addWidget(brand)
        self.nav = QWidget()
        self.nav_l = QVBoxLayout(self.nav)
        self.nav_l.setContentsMargins(12, 12, 12, 20)
        self.nav_l.setSpacing(2)
        self.nav_l.addStretch(1)
        sv.addWidget(self.nav, 1)
        lay.addWidget(self.sidebar)
        # ana
        main = QWidget()
        mv = QVBoxLayout(main)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(0)
        self.topbar = TopBar(win)
        mv.addWidget(self.topbar)
        self.stack = QStackedWidget()
        self.stack.setObjectName('fcPages')
        mv.addWidget(self.stack, 1)
        lay.addWidget(main, 1)
        self.pages = {}
        self.groups = []
        self.current = None
        self.nav_group_btns = QButtonGroup(self)
        self.nav_group_btns.setExclusive(True)
        i18n.on_change(lambda l: self.retranslate())

    def nav_group(self, title):
        l = label(self._grp(title), 'nav-title')
        l.setProperty('fcKey', title)
        if self.groups or self.pages:
            self.nav_l.insertSpacing(self.nav_l.count() - 1, 10)
        self.nav_l.insertWidget(self.nav_l.count() - 1, l)
        self.groups.append(l)
        return l

    def page(self, key, title, icon, widget, sub='', scroll=True):
        b = button(t(title), 'nav-item', icon=icon, role='nav-text')
        b.setCheckable(True)
        b.setFocusPolicy(Qt.NoFocus)
        b.setIconSize(QSize(18, 18))
        self.nav_group_btns.addButton(b)
        b.clicked.connect(lambda: self.show_page(key))
        self.nav_l.insertWidget(self.nav_l.count() - 1, b)
        if scroll:
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.NoFrame)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            host = QWidget()
            host.setObjectName('fcContent')
            hv = QVBoxLayout(host)
            hv.setContentsMargins(32, 28, 32, 40)
            hv.addWidget(widget)
            hv.addStretch(1)
            sa.setWidget(host)
            sa.viewport().setAutoFillBackground(False)
            host.setAutoFillBackground(False)
            holder = sa
        else:
            holder = widget
        self.stack.addWidget(holder)
        self.pages[key] = {'title': title, 'sub': sub, 'icon': icon, 'btn': b, 'w': holder}
        if self.current is None:
            self.show_page(key)
        return b

    def show_page(self, key):
        p = self.pages.get(key)
        if not p:
            return
        self.current = key
        self.stack.setCurrentWidget(p['w'])
        for k, q in self.pages.items():
            q['btn'].setChecked(k == key)
            icons.set_icon(q['btn'], q['icon'], 'accent' if k == key else 'nav-text', 18)
        self.topbar.set_title(t(p['title']), t(p['sub']) if p['sub'] else '')
        self.page_changed.emit(key)

    def retranslate(self):
        for l in self.groups:
            l.setText(self._grp(l.property('fcKey')))
        for k, p in self.pages.items():
            p['btn'].setText(t(p['title']))
        self.brand_tag.setText(t(self.tag) if self.tag else '')
        self.brand_tag.setVisible(bool(self.tag))
        if self.current:
            self.show_page(self.current)

    @staticmethod
    def _grp(k):
        s = t(k)
        return s if i18n.is_rtl() else s.upper()

    def set_tag(self, tag):
        self.tag = tag
        self.retranslate()
