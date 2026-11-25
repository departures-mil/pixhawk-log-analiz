"""Etkileşimli grafik görünümü: yakınlaştırma/kaydırma/PNG (matplotlib araç çubuğu), fareyle üzerine gelince zaman,
gerçek saat, uçuş modu ve TimeUS; tıklayınca ortak imleç (harita/3B ve diğer grafikler aynı ana gider); Shift+tıklama ile
iki nokta arası ölçüm cetveli."""
from __future__ import annotations
import time
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from matplotlib.ticker import FuncFormatter
from .i18n import lang
from ..core import viz
from ..core.analysis import fmt_t

TXT = {
    'hint': ('İpucu: fare tekerleği/araç çubuğu ile yakınlaştırın · tıklayın: imleç (harita ve 3B aynı ana gider) · Shift+tıklama ×2: ölçüm cetveli',
             'Tip: zoom with the toolbar · click: cursor (map and 3D jump to the same moment) · Shift+click ×2: measuring ruler',
             'تلميح: كبّر بشريط الأدوات · انقر: مؤشر (الخريطة وثلاثي الأبعاد ينتقلان للحظة نفسها) · Shift+نقر ×2: مسطرة قياس'),
    'mode': ('Mod', 'Mode', 'الوضع'), 'clock': ('Saat', 'Clock', 'الساعة'),
    'ruler1': ('Cetvel: ikinci noktaya Shift+tıklayın', 'Ruler: Shift+click the second point', 'المسطرة: Shift+انقر النقطة الثانية'),
    'empty': ('Bu grafik için logda veri yok.', 'No data in this log for this chart.', 'لا توجد بيانات لهذا الرسم في السجل.'),
    'busy': ('Grafik hazırlanıyor…', 'Preparing chart…', 'جارٍ تجهيز الرسم…'),
}


def tt(k):
    return viz.tx(TXT[k], lang())


def _is_time_ax(ax):
    return getattr(ax, 'name', '') == 'rectilinear' and isinstance(ax.xaxis.get_major_formatter(), FuncFormatter) \
        and not getattr(ax, '_secondary', False) and ax.get_label() != '<colorbar>'


class ChartView(QWidget):
    clicked = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(2)
        self.bar = QHBoxLayout(); self.bar.setContentsMargins(0, 0, 0, 0); v.addLayout(self.bar)
        self.hint = QLabel(tt('hint')); self.hint.setObjectName('muted'); self.hint.setWordWrap(True)
        v.addWidget(self.hint)
        self.body = QVBoxLayout(); self.body.setContentsMargins(0, 0, 0, 0); v.addLayout(self.body, 1)
        self.status = QLabel(' '); self.status.setObjectName('muted'); self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.status)
        self.canvas = None; self.tb = None; self.fig = None; self.A = None
        self.msg = QLabel(''); self.msg.setAlignment(Qt.AlignCenter); self.msg.setStyleSheet('background:white;color:#374151;border-radius:8px;font-size:12pt')
        self.body.addWidget(self.msg)
        self.cursor_t = None; self._hover = []; self._cur = []; self._ruler = None; self._rul_art = []; self._last = 0.0; self._segs = []

    # ---------------------------------------------------------------- içerik
    def _clear(self):
        if self.canvas is not None:
            self.body.removeWidget(self.canvas); self.canvas.setParent(None); self.canvas.deleteLater(); self.canvas = None
        if self.tb is not None:
            self.bar.removeWidget(self.tb); self.tb.setParent(None); self.tb.deleteLater(); self.tb = None
        self.fig = None; self._hover = []; self._cur = []; self._rul_art = []; self._ruler = None

    def busy(self):
        self._clear(); self.msg.setText(tt('busy')); self.msg.show()

    def set_message(self, txt):
        self._clear(); self.msg.setText(txt); self.msg.show()

    def set_figure(self, fig, A):
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
        self._clear()
        if fig is None:
            self.msg.setText(tt('empty')); self.msg.show(); return
        self.msg.hide()
        self.fig = fig; self.A = A
        self._segs = viz.segments(A, lang()) if A is not None else []
        for ax in fig.axes:
            if ax.__class__.__name__.startswith('SecondaryAxis'): ax._secondary = True
        self.canvas = FigureCanvasQTAgg(fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.body.addWidget(self.canvas, 1)
        self.tb = NavigationToolbar2QT(self.canvas, self, coordinates=False)
        self.tb.setIconSize(self.tb.iconSize() * 0.8)
        self.tb.setStyleSheet('QToolBar{background:#F8FAFC;border-radius:6px} QToolButton{background:transparent}')
        self.bar.addWidget(self.tb); self.bar.addStretch(1)
        self.canvas.mpl_connect('motion_notify_event', self._move)
        self.canvas.mpl_connect('button_press_event', self._press)
        self.canvas.mpl_connect('scroll_event', self._scroll)
        self.taxes = [ax for ax in fig.axes if _is_time_ax(ax)]
        for ax in self.taxes:
            self._hover.append(ax.axvline(0, color='#0F172A', lw=0.7, alpha=0.0, zorder=20))
        self._draw_cursor()
        self.canvas.draw_idle()

    # ---------------------------------------------------------------- imleç
    def set_cursor(self, t):
        self.cursor_t = t; self._draw_cursor()
        if self.canvas is not None: self.canvas.draw_idle()

    def _draw_cursor(self):
        for a in self._cur:
            try: a.remove()
            except Exception: pass
        self._cur = []
        if self.cursor_t is None or self.fig is None: return
        for ax in self.taxes:
            self._cur.append(ax.axvline(self.cursor_t, color='#F59E0B', lw=1.8, alpha=0.9, zorder=21))

    def zoom_to(self, t0, t1):
        if not self.taxes: return
        pad = max(1.0, (t1 - t0) * 0.05)
        for ax in self.taxes: ax.set_xlim(t0 - pad, t1 + pad)
        self.canvas.draw_idle()

    def _describe(self, t):
        A = self.A
        if A is None: return ''
        parts = [f'⏱ {fmt_t(t)}']
        c = viz.clock(A, t)
        if c: parts.append(f"🕘 {tt('clock')} {c}")
        s = viz.mode_at(A, t, self._segs)
        if s: parts.append(f"{tt('mode')}: {s['name']} ({s['why']})")
        parts.append(f'TimeUS {viz.time_us(A, t)}')
        return '   ·   '.join(parts)

    def _move(self, e):
        if e.inaxes is None or e.inaxes not in self.taxes or e.xdata is None: return
        now = time.time()
        if now - self._last < 0.03: return
        self._last = now
        t = float(e.xdata)
        y = f'   ·   y = {e.ydata:.2f}' if e.ydata is not None else ''
        extra = ''
        if self._ruler is not None:
            t0, y0 = self._ruler
            extra = f"   ·   📏 Δt = {abs(t - t0):.1f} s" + (f', Δy = {e.ydata - y0:+.2f}' if e.ydata is not None else '')
        self.status.setText(self._describe(t) + y + extra)
        for ln in self._hover:
            ln.set_xdata([t, t]); ln.set_alpha(0.45)
        self.canvas.draw_idle()

    def _press(self, e):
        if e.inaxes is None or e.xdata is None or e.inaxes not in self.taxes: return
        if self.tb is not None and self.tb.mode: return     # yakınlaştırma/kaydırma araçları açıkken imleç koyma
        t = float(e.xdata)
        if e.key == 'shift':
            if self._ruler is None:
                self._ruler = (t, e.ydata or 0.0)
                for a in self._rul_art:
                    try: a.remove()
                    except Exception: pass
                self._rul_art = [ax.axvline(t, color='#7C3AED', lw=1, ls='--') for ax in self.taxes]
                self.status.setText(tt('ruler1')); self.canvas.draw_idle(); return
            t0, y0 = self._ruler; self._ruler = None
            for ax in self.taxes:
                self._rul_art.append(ax.axvspan(min(t0, t), max(t0, t), color='#7C3AED', alpha=0.12, zorder=19))
            self.status.setText(f'📏 {fmt_t(min(t0, t))} → {fmt_t(max(t0, t))}   Δt = {abs(t - t0):.1f} s' +
                                (f'   Δy = {(e.ydata or 0) - y0:+.2f}' if e.ydata is not None else ''))
            self.canvas.draw_idle(); return
        if e.button == 1:
            self.set_cursor(t); self.clicked.emit(t)

    def _scroll(self, e):
        ax = e.inaxes
        if ax is None or ax not in self.taxes or e.xdata is None: return
        k = 0.8 if e.button == 'up' else 1.25
        x0, x1 = ax.get_xlim(); c = e.xdata
        nx0, nx1 = c - (c - x0) * k, c + (x1 - c) * k
        for a in self.taxes: a.set_xlim(nx0, nx1)
        self.canvas.draw_idle()


class StickView(QWidget):
    """İki kumanda çubuğu (Mode 2): sol = gaz/yaw, sağ = pitch/roll; 3B tekrar ile birlikte oynar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(170); self.v = None

    def set_values(self, v):
        self.v = v; self.update()

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QColor, QPen, QFont
        import math
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W = self.width(); s = 70; gap = 10; y0 = 40
        p.setPen(QColor('#CBD5E1')); f = QFont(); f.setPointSize(8); p.setFont(f)
        p.drawText(0, 14, W, 16, Qt.AlignCenter, viz.tx(('Kumanda çubukları', 'Sticks', 'عصي التحكم'), lang()))
        for j, lab in enumerate((viz.tx(('Gaz / Yaw', 'Thr / Yaw', 'الخانق / الانعراج'), lang()), viz.tx(('Pitch / Roll', 'Pitch / Roll', 'الميلان / الدوران'), lang()))):
            x0 = 5 + j * (s + gap)
            p.setPen(QPen(QColor('#475569'), 1)); p.setBrush(QColor('#0F172A')); p.drawRoundedRect(x0, y0, s, s, 8, 8)
            p.setPen(QPen(QColor('#334155'), 1, Qt.DashLine)); p.drawLine(x0 + s // 2, y0 + 4, x0 + s // 2, y0 + s - 4); p.drawLine(x0 + 4, y0 + s // 2, x0 + s - 4, y0 + s // 2)
            p.setPen(QColor('#94A3B8')); p.drawText(x0 - 4, y0 + s + 4, s + 8, 16, Qt.AlignCenter, lab)
            if self.v is None:
                p.setPen(QColor('#64748B')); p.drawText(x0, y0, s, s, Qt.AlignCenter, '—'); continue
            hx, hy = (self.v[0], self.v[1]) if j == 0 else (self.v[2], self.v[3])
            if hx is None or hy is None or (isinstance(hx, float) and math.isnan(hx)) or (isinstance(hy, float) and math.isnan(hy)): continue
            cx = x0 + s / 2 + max(-1, min(1, hx / 100)) * (s / 2 - 8); cy = y0 + s / 2 - max(-1, min(1, hy / 100)) * (s / 2 - 8)
            p.setPen(QPen(QColor('#F59E0B'), 2)); p.setBrush(QColor('#FBBF24')); p.drawEllipse(int(cx) - 6, int(cy) - 6, 12, 12)
        p.end()
