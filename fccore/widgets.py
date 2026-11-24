"""fccore.widgets — küçük Qt yardımcıları (web FC.ui karşılığı): cls(), card(), field(), notice(), Modal, toast(),
ProgressBox, Segmented, Columns (ayarlar ızgarası), Backdrop (ızgaralı/ışıltılı zemin)."""
from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, QSize, Qt, QTimer, Signal, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient, QBrush, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QBoxLayout, QButtonGroup, QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QGraphicsDropShadowEffect)

from . import style, i18n, icons
from .i18n import t


def cls(w, classes):
    """w.setProperty('fc', 'btn primary') + yeniden stil."""
    w.setProperty('fc', classes)
    w.style().unpolish(w)
    w.style().polish(w)
    return w


def has_cls(w, c):
    return c in str(w.property('fc') or '').split()


def toggle_cls(w, c, on):
    s = [x for x in str(w.property('fc') or '').split() if x != c]
    if on:
        s.append(c)
    return cls(w, ' '.join(s))


def label(text='', classes=None, wrap=False, obj=None, rich=False):
    l = QLabel(text)
    if classes:
        l.setProperty('fc', classes)
    if obj:
        l.setObjectName(obj)
    if wrap:
        l.setWordWrap(True)
    l.setTextFormat(Qt.RichText if rich else Qt.PlainText)
    if rich:
        l.setOpenExternalLinks(True)
    return l


class FcButton(QPushButton):
    """Simge ile metin arasında web'deki gibi boşluk bırakan düğme."""
    GAP = '\u2002'   # ~yarım em

    def setText(self, s):
        self._raw = s or ''
        super().setText((self.GAP + self._raw) if self._raw and self.property('fcIcon') else self._raw)

    def text_raw(self):
        return getattr(self, '_raw', self.text())


def button(text='', classes='', icon=None, role=None, slot=None, tip=None):
    b = FcButton()
    if icon:
        b.setProperty('fcIcon', icon)
    b.setText(text)
    b.setCursor(Qt.PointingHandCursor)
    if classes:
        b.setProperty('fc', classes)
    if icon:
        icons.set_icon(b, icon, role or ('on-accent' if 'primary' in classes.split() else 'text'),
                       size=14 if 'small' in classes.split() else 16)
    if slot:
        b.clicked.connect(lambda *_: slot())
    if tip:
        b.setToolTip(tip)
    return b


def hbox(*ws, spacing=10, margins=(0, 0, 0, 0), stretch_end=False):
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(*margins)
    h.setSpacing(spacing)
    for x in ws:
        if x is None:
            h.addStretch(1)
        elif isinstance(x, int):
            h.addSpacing(x)
        else:
            h.addWidget(x)
    if stretch_end:
        h.addStretch(1)
    return w


class Card(QFrame):
    """Ayarlar kartı: başlık (simge + metin), isteğe bağlı açıklama; içerik self.body (QVBoxLayout)."""

    def __init__(self, key='', title='', icon=None, desc=None):
        super().__init__()
        self.setObjectName('card')
        self.setProperty('fcCard', key)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(20, 18, 20, 20)
        self.body.setSpacing(0)
        self.head = QWidget()
        hl = QHBoxLayout(self.head)
        hl.setContentsMargins(0, 0, 0, 6)
        hl.setSpacing(8)
        self.icon = QLabel()
        if icon:
            icons.set_icon(self.icon, icon, 'accent', 18)
        else:
            self.icon.hide()
        self.title = label(title, 'card-title')
        hl.addWidget(self.icon)
        hl.addWidget(self.title, 1)
        self.body.addWidget(self.head)
        self.desc = label(desc or '', 'card-desc', wrap=True)
        self.desc.setVisible(bool(desc))
        self.body.addWidget(self.desc)

    def set_title(self, s):
        self.title.setText(s)

    def set_desc(self, s):
        self.desc.setText(s or '')
        self.desc.setVisible(bool(s))

    def add(self, w, top=0):
        if top:
            self.body.addSpacing(top)
        self.body.addWidget(w)
        return w

    def clear(self):
        """Başlık ve açıklama dışındaki her şeyi kaldırır (dil değişince yeniden çizmek için)."""
        while self.body.count() > 2:
            it = self.body.takeAt(2)
            if it.widget():
                it.widget().deleteLater()


def card(key='', title='', icon=None, desc=None):
    return Card(key, title, icon, desc)


def field(label_text, widget, hint=None, top=12):
    """Etiket + giriş (+ ipucu) dikey grubu (web .field)."""
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, top, 0, 0)
    v.setSpacing(7)
    w.label = label(label_text, 'field-label', wrap=True)
    v.addWidget(w.label)
    v.addWidget(widget)
    if hint is not None:
        w.hint = hint if isinstance(hint, QWidget) else label(hint, 'field-hint', wrap=True)
        v.addWidget(w.hint)
    return w


def notice(text, kind=''):
    l = label(text, ('notice ' + kind).strip(), wrap=True)
    return l


class Segmented(QFrame):
    changed = Signal(str)

    def __init__(self, items, current=None):
        """items: [(değer, metin, simge)]"""
        super().__init__()
        self.setProperty('fc', 'segmented')
        h = QHBoxLayout(self)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(4)
        self.group = QButtonGroup(self)
        self.btns = {}
        for val, text, ic in items:
            b = FcButton()
            if ic:
                b.setProperty('fcIcon', ic)
            b.setText(text)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            if ic:
                b.setProperty('fcIcon', ic)
            self.group.addButton(b)
            h.addWidget(b, 1)
            self.btns[val] = b
            b.clicked.connect(lambda _=False, v=val: self.changed.emit(v))
        self.set(current)

    def set(self, val):
        for v, b in self.btns.items():
            b.setChecked(v == val)
            if b.property('fcIcon'):
                icons.set_icon(b, b.property('fcIcon'), 'accent' if v == val else 'muted', 15)


class Columns(QWidget):
    """CSS `columns: 3 320px` karşılığı: kartlar sırayla, dengeli sütunlara akar (son kart hep en sonda kalır)."""

    def __init__(self, min_col=320, gap=18, max_cols=3):
        super().__init__()
        self.items = []
        self.min_col, self.gap, self.max_cols = min_col, gap, max_cols
        self._h = 0
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

    def add(self, w, before=None):
        w.setParent(self)
        if before is not None and before in self.items:
            self.items.insert(self.items.index(before), w)
        else:
            self.items.append(w)
        w.show()
        w.installEventFilter(self)
        self.relayout()
        return w

    def remove(self, w):
        if w in self.items:
            self.items.remove(w)
            w.setParent(None)
            self.relayout()

    def eventFilter(self, o, e):
        if e.type() in (QEvent.LayoutRequest, QEvent.Show, QEvent.Hide):
            QTimer.singleShot(0, self.relayout)
        return False

    def _ncols(self, width):
        n = max(1, min(self.max_cols, int((width + self.gap) // (self.min_col + self.gap))))
        return n

    @staticmethod
    def _hfw(w, cw):
        lay = w.layout()
        if lay is not None and lay.hasHeightForWidth():
            return lay.totalHeightForWidth(cw)
        if w.hasHeightForWidth():
            return w.heightForWidth(cw)
        return w.sizeHint().height()

    def _plan(self, width):
        vis = [w for w in self.items if not w.isHidden()]
        n = self._ncols(width)
        cw = int((width - self.gap * (n - 1)) / n)
        hs = [self._hfw(w, cw) for w in vis]
        # en büyük sütun yüksekliğini en aza indiren ardışık bölme (CSS sütun dengelemesi)
        best = None
        for lim in sorted(set(sum(hs[i:j]) + self.gap * (j - i - 1) for i in range(len(hs)) for j in range(i + 1, len(hs) + 1))):
            cols, cur, used = [[]], 0, 0
            ok = True
            for w, h in zip(vis, hs):
                need = h if not cols[-1] else cur + self.gap + h
                if need <= lim or not cols[-1]:
                    if h > lim:
                        ok = False
                        break
                    cols[-1].append((w, h))
                    cur = need
                else:
                    if len(cols) == n:
                        ok = False
                        break
                    cols.append([(w, h)])
                    cur = h
            if ok:
                best = cols
                break
        return best or [list(zip(vis, hs))], cw

    def relayout(self):
        width = self.width() or 960
        cols, cw = self._plan(width)
        rtl = self.layoutDirection() == Qt.RightToLeft
        hmax = 0
        for ci, col in enumerate(cols):
            x = ci * (cw + self.gap)
            if rtl:
                x = width - x - cw
            y = 0
            for w, h in col:
                w.setGeometry(x, y, cw, h)
                y += h + self.gap
            hmax = max(hmax, y - self.gap)
        if hmax != self._h:
            self._h = hmax
            self.setMinimumHeight(hmax)
            self.updateGeometry()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.relayout()

    def sizeHint(self):
        return QSize(960, self._h)


class Backdrop(QWidget):
    """Pencere zemini: bg + 40 px ızgara + iki yumuşak ışıltı (web body arka planı)."""

    def __init__(self):
        super().__init__()
        self.setObjectName('fcRoot')
        self.setAttribute(Qt.WA_StyledBackground, False)
        style.on_change(lambda st: self.update())

    def paintEvent(self, e):
        p = QPainter(self)
        r = self.rect()
        p.fillRect(r, style.qcolor(style.tok('bg')))
        w, h = r.width(), r.height()
        for (cx, cy, rx, ry, key) in ((0.85 * w, -0.10 * h - 0, 1200, 600, 'glow-1'), (-0.10 * w, 1.10 * h, 900, 500, 'glow-2')):
            c = style.qcolor(style.tok(key))
            if c.alpha() == 0:
                continue
            g = QRadialGradient(QPointF(0, 0), 1.0)
            g.setColorAt(0, c)
            c2 = QColor(c)
            c2.setAlpha(0)
            g.setColorAt(0.6, c2)
            g.setColorAt(1, c2)
            p.save()
            p.translate(cx, cy)
            p.scale(rx, ry)
            p.fillRect(QRectF(-1, -1, 2, 2), QBrush(g))
            p.restore()
        gc = style.qcolor(style.tok('bg-grid'))
        if gc.alpha():
            p.setPen(QPen(gc, 1))
            for x in range(0, w, 40):
                p.drawLine(x, 0, x, h)
            for y in range(0, h, 40):
                p.drawLine(0, y, w, y)
        p.end()


class ProgressBox(QWidget):
    """Başlık + yama etiketi + çubuk + ayrıntı satırı (web FC.progress.box)."""

    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        self.title = label('', wrap=True)
        f = self.title.font()
        self.title.setStyleSheet('font-weight:600')
        self.mode = label('', 'update-mode')
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.detail = label('', 'update-detail', wrap=True)
        for w in (self.title, self.mode, self.bar, self.detail):
            v.addWidget(w)
        self.mode.hide()

    def set_title(self, s):
        self.title.setText(s)

    def set(self, p, patch=False):
        from . import progress
        f = progress.format(p, patch=patch)
        if f['percent'] is None:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 100)
            self.bar.setValue(int(f['percent']))
        self.bar.show()
        self.detail.setText(f['detail'].replace(' MB', '\u00a0MB').replace(' م.ب', '\u00a0م.ب'))
        self.mode.setText(f['modeText'])
        self.mode.setVisible(bool(f['modeText']))

    def busy(self, s):
        self.title.setText(s)
        self.bar.setRange(0, 0)
        self.bar.show()
        self.detail.setText('')
        self.mode.hide()


class Modal(QWidget):
    """Pencere içi modal (web .modal-backdrop + .modal): Modal(parent, title, icon, body, buttons, size).
    buttons: [{'label', 'cls', 'icon', 'on_click': f(modal) → False ile açık kalır}] ya da 'spacer'."""
    closed = Signal()
    SIZES = {'small': 460, None: 640, 'wide': 880}

    def __init__(self, parent=None, title='', icon=None, body=None, buttons=None, size=None, dismiss=True, on_close=None):
        parent = parent or _top()
        super().__init__(parent)
        self.setObjectName('fcBackdrop')
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.dismiss, self.on_close, self._closed = dismiss, on_close, False
        self.box = QFrame(self)
        self.box.setObjectName('fcModal')
        sh = QGraphicsDropShadowEffect(self.box)
        sh.setBlurRadius(60)
        sh.setOffset(0, 24)
        sh.setColor(QColor(0, 0, 0, 120))
        self.box.setGraphicsEffect(sh)
        self.width_ = self.SIZES.get(size, 640)
        v = QVBoxLayout(self.box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        head = QFrame()
        head.setObjectName('fcModalHeader')
        hl = QHBoxLayout(head)
        hl.setContentsMargins(22, 16, 16, 16)
        hl.setSpacing(8)
        self.ticon = QLabel()
        self.title = QLabel(title)
        self.title.setObjectName('fcModalTitle')
        hl.addWidget(self.ticon)
        hl.addWidget(self.title, 1)
        if dismiss:
            x = button('', 'icon-btn', icon='x', role='muted', slot=self.close_modal, tip=t('fc.close'))
            hl.addWidget(x)
        v.addWidget(head)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet('QScrollArea{background:transparent}')
        self.body_host = QWidget()
        self.body_host.setObjectName('fcContent')
        self.body = QVBoxLayout(self.body_host)
        self.body.setContentsMargins(22, 20, 22, 20)
        self.body.setSpacing(10)
        self.scroll.setWidget(self.body_host)
        v.addWidget(self.scroll, 1)
        self.foot = QFrame()
        self.foot.setObjectName('fcModalFooter')
        self.fl = QHBoxLayout(self.foot)
        self.fl.setContentsMargins(22, 14, 22, 14)
        self.fl.setSpacing(10)
        v.addWidget(self.foot)
        self.set_title(title, icon)
        if body is not None:
            self.set_body(body)
        self.set_buttons(buttons if buttons is not None else [{'label': t('fc.ok'), 'cls': 'primary'}])
        parent.installEventFilter(self)
        self._fit()
        self.show()
        self.raise_()
        self.setFocus()

    def set_title(self, s, icon=None):
        self.title.setText(s)
        if icon:
            icons.set_icon(self.ticon, icon, 'accent', 20)
            self.ticon.show()
        else:
            self.ticon.hide()

    def set_body(self, w):
        while self.body.count():
            it = self.body.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if isinstance(w, str):
            w = label(w, wrap=True)
        self.body.addWidget(w)
        self.body.addStretch(1)
        self._fit()
        QTimer.singleShot(0, self._fit)
        QTimer.singleShot(60, self._fit)

    def set_buttons(self, lst):
        while self.fl.count():
            it = self.fl.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not lst:
            self.foot.hide()
            return
        self.foot.show()
        if not any(b == 'spacer' for b in lst):
            self.fl.addStretch(1)
        for b in lst:
            if b == 'spacer':
                self.fl.addStretch(1)
                continue
            btn = button(b['label'], ('btn ' + b.get('cls', '')).strip(), icon=b.get('icon'))
            btn.setEnabled(not b.get('disabled'))

            def go(_=False, b=b):
                r = b['on_click'](self) if b.get('on_click') else None
                if r is not False:
                    self.close_modal()
            btn.clicked.connect(go)
            self.fl.addWidget(btn)

    def _fit(self):
        p = self.parentWidget()
        if not p:
            return
        self.setGeometry(p.rect())
        W = min(self.width_, p.width() - 60)
        self.body_host.setFixedWidth(W - 2)
        self.body_host.ensurePolished()
        for c in self.body_host.findChildren(QWidget):
            c.ensurePolished()
        self.body_host.layout().activate()
        bh = self.body_host.layout().totalHeightForWidth(W - 2) if self.body_host.layout().hasHeightForWidth() else self.body_host.sizeHint().height()
        hh = self.box.layout().itemAt(0).widget().sizeHint().height()
        fh = self.foot.sizeHint().height() if self.foot.isVisible() else 0
        H = min(hh + bh + fh + 4, p.height() - 60)
        self.box.setGeometry((p.width() - W) // 2, (p.height() - H) // 2, W, H)
        self.body_host.setMinimumWidth(0)
        self.body_host.setMaximumWidth(16777215)

    def eventFilter(self, o, e):
        if o is self.parentWidget() and e.type() == QEvent.Resize:
            self._fit()
        return False

    def mousePressEvent(self, e):
        if self.dismiss and not self.box.geometry().contains(e.position().toPoint()):
            self.close_modal()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self.dismiss:
            self.close_modal()
        else:
            super().keyPressEvent(e)

    def close_modal(self):
        if self._closed:
            return
        self._closed = True
        if self.parentWidget():
            self.parentWidget().removeEventFilter(self)
        self.hide()
        self.deleteLater()
        if self.on_close:
            try:
                self.on_close()
            except Exception:
                import traceback
                traceback.print_exc()
        self.closed.emit()


def _top():
    app = QApplication.instance()
    w = app.activeWindow() if app else None
    if w:
        return w
    for w in (app.topLevelWidgets() if app else []):
        if w.isVisible() and w.isWindow() and w.objectName() != 'fcBackdrop':
            return w
    return None


def modal(**kw):
    return Modal(**kw)


def toast(msg, kind='', ms=4200, parent=None):
    """Sağ altta (RTL'de sol altta) kısa bildirim."""
    parent = parent or _top()
    if parent is None:
        return None
    l = label(msg, ('toast ' + kind).strip(), wrap=True)
    l.setParent(parent)
    l.setMaximumWidth(460)
    l.adjustSize()
    stack = [c for c in parent.children() if isinstance(c, QLabel) and has_cls(c, 'toast') and c is not l and c.isVisible()]
    y = parent.height() - 24 - l.height() - sum(c.height() + 10 for c in stack)
    x = 24 if i18n.is_rtl() else parent.width() - 24 - l.width()
    l.move(x, y)
    l.show()
    l.raise_()
    QTimer.singleShot(ms, l.deleteLater)
    return l


def open_url(u):
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl(u))


def link(text, url):
    l = QLabel('<a href="%s" style="color:%s;text-decoration:none">%s</a>' % (url, style.tok('accent'), _esc(text)))
    l.setTextFormat(Qt.RichText)
    l.setOpenExternalLinks(True)
    l.setCursor(Qt.PointingHandCursor)
    return l


def _esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
