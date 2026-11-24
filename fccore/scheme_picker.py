"""fccore.scheme_picker — renk şeması seçici: her şema kendi renkleriyle boyanan önizleme kutucuğu (zemin · panel · ana renk geçişi · vurgu)."""
from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QLinearGradient, QPainter, QPainterPath, QPen, QBrush
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import style, i18n, icons
from .widgets import label


class Swatch(QWidget):
    def __init__(self, sid):
        super().__init__()
        self.sid = sid
        self.setFixedHeight(30)

    def paintEvent(self, e):
        m = style.effective()
        T = lambda k: style.qcolor(style.tok(k, self.sid, m))  # noqa: E731
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 7, 7)
        p.setClipPath(path)
        p.fillRect(r, T('bg'))
        w = r.width()
        parts = [1, 1, 0.8, 0.6]
        tot = sum(parts)
        xs, x = [], r.left()
        for f in parts:
            xs.append((x, w * f / tot))
            x += w * f / tot
        rtl = self.layoutDirection() == Qt.RightToLeft
        if rtl:
            xs = [(r.left() + r.right() - (a + b), b) for a, b in xs]
        (x0, w0), (x1, w1), (x2, w2), (x3, w3) = xs
        p.fillRect(QRectF(x0, r.top(), w0, r.height()), T('bg'))
        p.fillRect(QRectF(x1, r.top(), w1, r.height()), T('panel-solid'))
        p.setPen(QPen(T('border'), 1))
        p.drawLine(int(x1), int(r.top()), int(x1), int(r.bottom()))
        p.drawLine(int(x1 + w1), int(r.top()), int(x1 + w1), int(r.bottom()))
        g = QLinearGradient(x2, r.top(), x2 + w2, r.bottom())
        g.setColorAt(0, T('primary-1'))
        g.setColorAt(1, T('primary-2'))
        p.fillRect(QRectF(x2, r.top(), w2, r.height()), QBrush(g))
        p.fillRect(QRectF(x3, r.top(), w3, r.height()), T('accent'))
        p.setClipping(False)
        p.setPen(QPen(style.qcolor(style.tok('border')), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.end()


class SchemeButton(QPushButton):
    def __init__(self, sid):
        super().__init__()
        self.sid = sid
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty('fc', 'fc-scheme')
        self.setMinimumHeight(74)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(7)
        self.sw = Swatch(sid)
        v.addWidget(self.sw)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self.name = label(style.scheme_label(sid))
        self.name.setStyleSheet('font-size:%dpx' % round(12.5 * style.scale()))
        self.check = QLabel()
        row.addWidget(self.name, 1)
        row.addWidget(self.check)
        v.addLayout(row)

    def sizeHint(self):
        return QSize(132, 74)

    def draw(self, on):
        self.setChecked(on)
        self.name.setText(style.scheme_label(self.sid))
        if on:
            self.check.setPixmap(icons.pixmap('check', style.tok('accent'), 14))
            self.check.show()
        else:
            self.check.clear()
            self.check.hide()


class SchemePicker(QWidget):
    """Kartın genişliğine göre en az 132 px'lik eşit sütunlara akar (web .fc-schemes: repeat(auto-fill, minmax(132px,1fr)))."""
    picked = Signal(str)
    H = 74

    def __init__(self, min_w=132, gap=8):
        super().__init__()
        self.min_w, self.gap = min_w, gap
        sp = self.sizePolicy()
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)
        self.btns = []
        self.rebuild()
        self._un = [style.on_change(lambda st: self.sync()), i18n.on_change(lambda l: self.sync())]
        self.destroyed.connect(lambda *_: [u() for u in self._un])

    def rebuild(self):
        for b in self.btns:
            b.deleteLater()
        self.btns = []
        for sid in style.schemes():
            b = SchemeButton(sid)
            b.setParent(self)
            b.clicked.connect(lambda _=False, s=sid: (style.set_scheme(s), self.picked.emit(s)))
            b.show()
            self.btns.append(b)
        self.sync()
        self._place()
        self.updateGeometry()

    def _cols(self, w):
        return max(1, int((w + self.gap) // (self.min_w + self.gap)))

    def _place(self):
        w = self.width()
        n = self._cols(w)
        cw = (w - self.gap * (n - 1)) / n
        rtl = self.layoutDirection() == Qt.RightToLeft
        for i, b in enumerate(self.btns):
            r, c = divmod(i, n)
            x = c * (cw + self.gap)
            if rtl:
                x = w - x - cw
            b.setGeometry(int(round(x)), r * (self.H + self.gap), int(round(cw)), self.H)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        n = self._cols(w)
        rows = (len(self.btns) + n - 1) // n
        return rows * self.H + (rows - 1) * self.gap

    def sizeHint(self):
        return QSize(2 * self.min_w + self.gap, self.heightForWidth(2 * self.min_w + self.gap))

    def minimumSizeHint(self):
        return QSize(self.min_w, self.H)

    def sync(self):
        if len(self.btns) != len(style.schemes()):
            return self.rebuild()
        cur = style.scheme()
        for b in self.btns:
            try:
                b.draw(b.sid == cur)
                b.sw.update()
            except RuntimeError:
                pass
