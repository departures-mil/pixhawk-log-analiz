"""✂ Log kesme penceresi: logun tamamı grafikte, kayıtlar numaralı; fareyle sürükleyerek ya da bir kayda tıklayarak aralık seç."""
from __future__ import annotations
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QPushButton, QWidget, QSizePolicy,
                               QCheckBox, QScrollArea, QFrame)
from .i18n import t, lang
from .common import button, label, error
from ..core import logcut as LC

SEL = '#2563EB'; HID = '#94A3B8'


class LogCutDialog(QDialog):
    """Sonuç: self.result_range = (t0, t1) asıl log saniyesi, ya da 'restore'. None = iptal."""
    def __init__(self, win, full, cur=None, remember=True):
        super().__init__(win)
        self.full = full; self.result_range = None
        self.setWindowTitle(t('cut_title')); self.resize(1180, 720)
        if lang() == 'ar': self.setLayoutDirection(Qt.RightToLeft)
        v = QVBoxLayout(self)
        v.addWidget(label(t('cut_intro'), 'muted', wrap=True))
        self.recs = LC.records(full)
        dur = float(full.duration or 1.0)
        if cur: a, b = cur
        else:
            fl = [r for r in self.recs if r['flew']]
            a, b = LC.record_range(full, fl[-1]) if len(self.recs) > 1 and fl else (0.0, dur)
        # grafik
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        self.fig = Figure(figsize=(10, 3.6), dpi=100); self.fig.patch.set_facecolor('white')
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig); self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(320)
        v.addWidget(self.canvas, 1)
        self._plot()
        from matplotlib.widgets import SpanSelector
        self.span = SpanSelector(self.ax, self._spanned, 'horizontal', useblit=False, minspan=1.0, interactive=False,
                                 props=dict(alpha=0.18, facecolor=SEL))
        # kayıt düğmeleri
        if self.recs:
            v.addWidget(label(t('cut_records'), 'h2'))
            rw = QWidget(); rw.setObjectName('root'); rh = QHBoxLayout(rw); rh.setContentsMargins(0, 0, 0, 0)
            for r in self.recs:
                txt = (t('cut_rec', i=r['i']) + f"\n{LC.fmt(r['t0'])} – {LC.fmt(r['t1'])}  ·  {LC.fmt(r['dur'])}\n"
                       + (('✈ ' + t('cut_flew')) if r['flew'] else ('⏸ ' + t('cut_ground')))
                       + (('  ·  ' + t('cut_alt', a=f"{r['alt_max']:.0f}")) if r.get('alt_max') is not None else ''))
                b_ = QPushButton(txt); b_.setMinimumHeight(64)
                b_.clicked.connect(lambda _=False, r=r: self._set(*LC.record_range(full, r)))
                rh.addWidget(b_)
            rh.addStretch(1)
            sa = QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.NoFrame); sa.setWidget(rw)
            sa.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); sa.setMaximumHeight(96)
            v.addWidget(sa)
        # başlangıç / bitiş
        h = QHBoxLayout()
        self.s0 = QDoubleSpinBox(); self.s1 = QDoubleSpinBox()
        for sp in (self.s0, self.s1):
            sp.setRange(0.0, dur); sp.setDecimals(1); sp.setSuffix(' s'); sp.setSingleStep(1.0); sp.setMinimumWidth(130)
            sp.valueChanged.connect(lambda *_: self._changed())
        h.addWidget(QLabel(t('cut_start'))); h.addWidget(self.s0); h.addSpacing(16)
        h.addWidget(QLabel(t('cut_end'))); h.addWidget(self.s1); h.addSpacing(16)
        self.info = QLabel(''); self.info.setObjectName('h2'); h.addWidget(self.info, 1)
        v.addLayout(h)
        bot = QHBoxLayout()
        self.rem = QCheckBox(t('cut_remember')); self.rem.setChecked(remember); bot.addWidget(self.rem)
        bot.addStretch(1)
        self.b_restore = button(t('cut_restore'), self._restore); self.b_restore.setEnabled(bool(cur)); bot.addWidget(self.b_restore)
        bot.addWidget(button(t('cancel'), self.reject))
        bot.addWidget(button(t('cut_do'), self._ok, primary=True))
        v.addLayout(bot)
        self._busy = False
        self._set(a, b)

    # ------------------------------------------------------------ grafik
    def _plot(self):
        L = self.full; ax = self.ax; ax.clear()
        tt, alt, src = LC._alt_series(L)
        if tt is not None:
            ax.plot(tt, alt, color='#0F172A', lw=1.0)
            ax.set_ylabel(t('cut_alt_axis'))
        g = L.s('GPS')
        if g.has('Spd'):
            ax2 = getattr(self, 'ax2', None)
            if ax2 is None: self.ax2 = ax2 = ax.twinx()
            ax2.clear(); ax2.plot(g.t, g['Spd'], color='#16A34A', lw=0.8, alpha=0.7); ax2.set_ylabel(t('cut_spd_axis'), color='#16A34A'); ax2.yaxis.set_label_position('right'); ax2.yaxis.tick_right()
            ax2.set_zorder(ax.get_zorder() - 1); ax.patch.set_visible(False)
        for r in self.recs:
            ax.axvspan(r['t0'], r['t1'], color='#F59E0B', alpha=0.10, lw=0)
            ax.text((r['t0'] + r['t1']) / 2, 0.98, str(r['i']), transform=ax.get_xaxis_transform(), ha='center', va='top',
                    fontsize=12, fontweight='bold', color='#B45309')
        ax.set_xlim(0, max(1.0, float(L.duration)))
        from matplotlib.ticker import FuncFormatter
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: LC.fmt(x)))
        ax.set_xlabel(t('cut_time_axis')); ax.grid(alpha=0.25)
        self._shade = []
        self.fig.tight_layout()

    def _draw_sel(self):
        for p in self._shade:
            try: p.remove()
            except Exception: pass
        a, b = self.s0.value(), self.s1.value(); d = float(self.full.duration)
        ax = self.ax
        self._shade = [ax.axvspan(0, a, color=HID, alpha=0.45, lw=0, hatch='//'), ax.axvspan(b, d, color=HID, alpha=0.45, lw=0, hatch='//'),
                       ax.axvline(a, color=SEL, lw=2), ax.axvline(b, color=SEL, lw=2)]
        self.canvas.draw_idle()

    # ------------------------------------------------------------ seçim
    def _spanned(self, x0, x1):
        self._set(min(x0, x1), max(x0, x1))

    def _set(self, a, b):
        self._busy = True
        self.s0.setValue(max(0.0, a)); self.s1.setValue(min(float(self.full.duration), b))
        self._busy = False; self._changed()

    def _changed(self):
        if self._busy: return
        a, b = self.s0.value(), self.s1.value()
        self.info.setText(t('cut_len', a=LC.fmt(a), b=LC.fmt(b), d=LC.fmt(max(0, b - a))))
        self._draw_sel()

    def _ok(self):
        a, b = self.s0.value(), self.s1.value()
        if b - a < 5: return error(self, t('cut_too_short'))
        if a <= 0.5 and b >= float(self.full.duration) - 0.5:
            self.result_range = 'restore'
        else:
            self.result_range = (a, b)
        self.accept()

    def _restore(self):
        self.result_range = 'restore'; self.accept()
