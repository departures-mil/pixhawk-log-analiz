"""Sayfalar: Analiz, Grafikler, Harita/3B, Zaman çizelgesi, Danışman, Alıştırma."""
from __future__ import annotations
import html, os, time
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextBrowser, QListWidget, QListWidgetItem,
                               QSplitter, QComboBox, QTabWidget, QSlider, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
                               QCheckBox, QRadioButton, QButtonGroup, QPushButton, QFileDialog, QGridLayout, QAbstractItemView)
from PySide6.QtGui import QColor
from .i18n import t, lang
from .common import label, button, ImageView, run_bg, error, info, card
from . import summary_html
from ..core import charts, texts, knowledge as K
from ..core.analysis import fmt_t, hav
from ..core.report import R

E = html.escape


class Page(QWidget):
    def __init__(self, win):
        super().__init__(); self.win = win

    def on_analysis(self, A):  # yeni analiz yüklendiğinde
        pass

    def on_show(self):
        pass


# --------------------------------------------------------------------- Analiz
class AnalysisPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        self.b_open = button('📂 ' + t('open_log'), win.pick_log, primary=True)
        self.b_rep = button('📄 ' + t('export'), win.export_report)
        self.lbl = label('', 'muted'); self.lbl.setMinimumWidth(50)
        from PySide6.QtWidgets import QSizePolicy
        self.lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addWidget(self.b_open); top.addWidget(self.b_rep); top.addWidget(self.lbl, 1)
        v.addLayout(top)
        pr = QHBoxLayout()
        self.prog = QProgressBar(); self.prog.setVisible(False)
        self.b_cancel = button(t('cancel'), win.cancel_load); self.b_cancel.setVisible(False)
        pr.addWidget(self.prog, 1); pr.addWidget(self.b_cancel)
        v.addLayout(pr)
        self.view = QTextBrowser(); self.view.setOpenLinks(False); self.view.anchorClicked.connect(self._link)
        self.view.setHtml(self._welcome())
        v.addWidget(self.view, 1)
        self.setAcceptDrops(True)

    def _link(self, url):
        u = url.toString()
        if u == 'ai:why': return self._ai_why()
        if u.startswith('go:'): return self.win.goto(u[3:])
        if u.startswith('t:'):
            try: self.win.pages['map'].goto_time(float(u[2:])); self.win.goto('map')
            except Exception: pass
        else:
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(url)

    def _ai_why(self):
        A = self.win.A
        if not A: return
        from ..core import why, ai as AI
        from ..core.analysis import fmt_t
        if not AI.available(self.win.settings): return error(self, t('fi_ai_off'))
        self.set_busy(True, '🤖 …'); self.prog.setRange(0, 0)
        def job(): return why.ai_explain(A, self.win.settings, self.win.usage, lang(), fmt_t)
        def ok(txt):
            self.set_busy(False)
            if not txt: return
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser
            dl = QDialog(self); dl.setWindowTitle('🤖 ' + t('why_ai_title')); dl.resize(820, 640)
            vv = QVBoxLayout(dl); tb = QTextBrowser(); tb.setMarkdown(txt); vv.addWidget(tb)
            if lang() == 'ar': tb.setLayoutDirection(Qt.RightToLeft)
            vv.addWidget(button(t('close'), dl.accept)); dl.exec()
        def fail(e): self.set_busy(False); error(self, e)
        run_bg(job, on_done=ok, on_fail=fail)

    def _welcome(self):
        d = 'rtl' if lang() == 'ar' else 'ltr'
        return (f'<div dir="{d}" style="margin:40px"><h1 style="color:#F8FAFC">{E(t("app"))}</h1>'
                f'<p style="font-size:12pt;color:#CBD5E1">{E(t("drop_hint"))}</p>'
                f'<p style="color:#94A3B8">{E(t("scen_intro"))}</p></div>')

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if os.path.isdir(p):
                self.win.goto('batch'); self.win.pages['batch'].run_folder(p); return
            if p.lower().endswith(('.bin', '.tlog', '.log', '.pxloc')):
                self.win.open_log(p); return

    def set_busy(self, busy, text=''):
        self.prog.setVisible(busy); self.b_cancel.setVisible(busy)
        self.b_open.setEnabled(not busy)
        if busy: self.prog.setRange(0, 100); self.prog.setValue(0); self.prog.setFormat(text + '  %p%')

    def set_progress(self, p, text):
        self.prog.setValue(int(p * 100)); self.prog.setFormat(text + '  %p%')

    def on_analysis(self, A):
        L = A.L
        self.lbl.setText(f'{os.path.basename(L.path)}  ·  {L.size / 1e6:.1f} MB  ·  {A.vehicle} {L.version or ""}')
        self.view.setHtml(summary_html.build(A, lang()))


# ------------------------------------------------------------------ Grafikler
CHART_KEYS = [k for k, _ in charts.ALL] + ['c_health', 'c_timeline']


class ChartsPage(Page):
    def __init__(self, win):
        super().__init__(win)
        h = QHBoxLayout(self); h.setContentsMargins(16, 12, 16, 12)
        self.list = QListWidget(); self.list.setFixedWidth(260)
        for k in CHART_KEYS:
            it = QListWidgetItem(R(k, lang())); it.setData(Qt.UserRole, k); self.list.addItem(it)
        self.list.currentItemChanged.connect(self._show)
        h.addWidget(self.list)
        r = QVBoxLayout()
        self.img = ImageView(); r.addWidget(self.img, 3)
        self.lesson = QTextBrowser(); self.lesson.setMaximumHeight(230); r.addWidget(self.lesson, 1)
        h.addLayout(r, 1)
        self.cache = {}

    def on_analysis(self, A):
        self.cache = {}
        lg = lang()

        def make():
            out = {}
            for k, fn in charts.ALL:
                try: out[k] = fn(A, lg)
                except Exception: out[k] = None
            out['c_health'] = charts.chart_health(A, lg); out['c_timeline'] = charts.chart_timeline(A, lg)
            return out
        run_bg(make, on_done=self._ready)

    def _ready(self, d):
        self.cache = d
        if self.list.currentRow() < 0: self.list.setCurrentRow(0)
        else: self._show(self.list.currentItem())

    def _show(self, it, *_):
        if not it: return
        k = it.data(Qt.UserRole)
        self.img.set_png(self.cache.get(k))
        self.lesson.setHtml(summary_html.lesson_html(k, lang()))

    def show_key(self, k, t_=None, span=None):
        """Grafiği seç; t_/span verilirse ilgili an turuncu işaretli çizilir (alıştırma / ders rehberi)."""
        if k not in CHART_KEYS: return
        i = CHART_KEYS.index(k)
        self.list.blockSignals(True); self.list.setCurrentRow(i); self.list.blockSignals(False)
        self.lesson.setHtml(summary_html.lesson_html(k, lang()))
        A = self.win.A
        if A is None: return
        if t_ is None and span is None: self.img.set_png(self.cache.get(k)); return
        lg = lang()
        run_bg(charts.render_marked, k, A, lg, t_, span, on_done=lambda b: self.img.set_png(b) if b else None)


# --------------------------------------------------------------- Harita + 3B
class MapPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        self.tabs = QTabWidget(); v.addWidget(self.tabs)
        # Harita
        mw = QWidget(); mv = QVBoxLayout(mw)
        bar = QHBoxLayout()
        bar.addWidget(label(t('map_src')))
        self.src = QComboBox()
        for s in ('osm', 'sat', 'topo'): self.src.addItem(t('src_' + s), s)
        i = self.src.findData(win.settings.get('map_src', 'osm')); self.src.setCurrentIndex(max(0, i))
        bar.addWidget(self.src)
        bar.addWidget(button(t('refresh'), self.render_map))
        self.b_pre = button('⬇ ' + t('prefetch'), self.prefetch); bar.addWidget(self.b_pre)
        self.pp = QProgressBar(); self.pp.setVisible(False); bar.addWidget(self.pp, 1)
        bar.addStretch(0)
        mv.addLayout(bar)
        self.map = ImageView(); mv.addWidget(self.map, 1)
        self.map_lesson = QTextBrowser(); self.map_lesson.setMaximumHeight(150); mv.addWidget(self.map_lesson)
        self.tabs.addTab(mw, '🗺 ' + R('c_map', lang()))
        # 3B
        rw = QWidget(); rv = QVBoxLayout(rw)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(8, 6), facecolor='#0F172A')
        self.canvas = FigureCanvasQTAgg(self.fig)
        rv.addWidget(self.canvas, 1)
        ctl = QHBoxLayout()
        self.b_play = button(t('play'), self.toggle_play); ctl.addWidget(self.b_play)
        self.slider = QSlider(Qt.Horizontal); self.slider.valueChanged.connect(self._frame); ctl.addWidget(self.slider, 1)
        ctl.addWidget(label(t('speed')))
        self.spd = QComboBox()
        for x in ('1x', '2x', '5x', '10x', '20x'): self.spd.addItem(x)
        self.spd.setCurrentIndex(2); ctl.addWidget(self.spd)
        from .pages_p import video_dialog
        ctl.addWidget(button('🎬 ' + t('vd_btn'), lambda: video_dialog(self.win, self), primary=True))
        rv.addLayout(ctl)
        self.info = label('', wrap=True); rv.addWidget(self.info)
        from PySide6.QtWidgets import QSplitter
        sp3 = QSplitter(Qt.Horizontal); sp3.addWidget(rw)
        gw = QWidget(); gv = QVBoxLayout(gw); gv.setContentsMargins(6, 0, 0, 0)
        gh = QHBoxLayout(); gh.addWidget(label(t('ls_title'), 'h2')); gh.addStretch(1)
        self.b_guide = button(t('ls_play'), self.guide_play, primary=True); gh.addWidget(self.b_guide); gv.addLayout(gh)
        gv.addWidget(label(t('ls_help'), 'muted', wrap=True))
        self.steps = QListWidget(); self.steps.currentRowChanged.connect(self._step); gv.addWidget(self.steps, 2)
        self.step_txt = QTextBrowser(); gv.addWidget(self.step_txt, 2)
        self.step_img = ImageView(); gv.addWidget(self.step_img, 3)
        sp3.addWidget(gw); sp3.setSizes([900, 520])
        self.tabs.addTab(sp3, '✈ 3D')
        self.lsteps = []; self.gtimer = QTimer(self); self.gtimer.setInterval(6500); self.gtimer.timeout.connect(self._guide_next)
        self.timer = QTimer(self); self.timer.setInterval(50); self.timer.timeout.connect(self._tick)
        self.A = None; self.tr = None

    def on_analysis(self, A):
        self.A = A
        self.map_lesson.setHtml(summary_html.lesson_html('c_map', lang()))
        self.render_map()
        self._setup3d()
        self._lessons()

    # ------------------------------------------------------------ ders rehberi
    def _lessons(self):
        from ..core import lessons
        self.gtimer.stop(); self.b_guide.setText(t('ls_play'))
        try: self.lsteps = lessons.build(self.A, lang())
        except Exception: self.lsteps = []
        self.steps.blockSignals(True); self.steps.clear()
        for st in self.lsteps: self.steps.addItem(f"{st['time']}  ·  {st['title']}")
        self.steps.blockSignals(False)
        self.step_txt.setHtml(''); self.step_img.set_png(None)

    def goto_time(self, tt):
        if self.tr is None: return
        self.tabs.setCurrentIndex(1)
        i = int(np.clip(np.searchsorted(self.tr['t'], tt), 0, len(self.tr['t']) - 1))
        self.slider.setValue(i)

    def _step(self, i):
        if not (0 <= i < len(self.lsteps)): return
        st = self.lsteps[i]; lg = lang(); d = 'rtl' if lg == 'ar' else 'ltr'
        self.step_txt.setHtml(f'<div dir="{d}"><h3 style="color:#FBBF24">{E(st["time"])} · {E(st["title"])}</h3><p style="font-size:11pt">{E(st["text"])}</p></div>')
        if self.tr is not None:
            j = int(np.clip(np.searchsorted(self.tr['t'], st['t']), 0, len(self.tr['t']) - 1)); self.slider.setValue(j)
        A = self.A; span = (st['t'], st['t1']) if st.get('t1') else None
        run_bg(charts.render_marked, st['chart'], A, lg, st['t'], span, on_done=lambda b: self.step_img.set_png(b) if b else None)

    def guide_play(self):
        if self.gtimer.isActive():
            self.gtimer.stop(); self.b_guide.setText(t('ls_play')); return
        if not self.lsteps: return
        self.b_guide.setText(t('ls_stop'))
        if self.steps.currentRow() < 0 or self.steps.currentRow() >= len(self.lsteps) - 1: self.steps.setCurrentRow(0)
        else: self._step(self.steps.currentRow())
        self.gtimer.start()

    def _guide_next(self):
        i = self.steps.currentRow() + 1
        if i >= len(self.lsteps): self.gtimer.stop(); self.b_guide.setText(t('ls_play')); return
        self.steps.setCurrentRow(i)

    def render_map(self):
        if not self.A: return
        A = self.A; lg = lang(); src = self.src.currentData(); online = self.win.settings.get('online', True)
        self.win.settings['map_src'] = src; self.win.settings.save()
        run_bg(lambda: charts.chart_map(A, lg, online=online, src=src), on_done=lambda b: self.map.set_png(b) if b else None)

    def prefetch(self):
        if not self.A or self.A.track is None: return error(self, t('no_log'))
        tr = self.A.track; src = self.src.currentData()
        la0, la1 = float(np.nanmin(tr['lat'])), float(np.nanmax(tr['lat'])); lo0, lo1 = float(np.nanmin(tr['lon'])), float(np.nanmax(tr['lon']))
        pad = max(la1 - la0, lo1 - lo0) * 0.3 + 0.003
        from ..core import tiles
        self.pp.setVisible(True); self.pp.setRange(0, 100); self.b_pre.setEnabled(False)
        w = None

        def job():
            return tiles.prefetch(la0 - pad, la1 + pad, lo0 - pad, lo1 + pad, 10, 17, src,
                                  progress=lambda d, n: w.progress.emit((d, n)))

        def prog(x):
            d, n = x; self.pp.setValue(int(100 * d / max(n, 1))); self.pp.setFormat(f'{d}/{n}  %p%')

        def fin(_):
            self.pp.setVisible(False); self.b_pre.setEnabled(True); info(self, t('done'))
        w = run_bg(job, on_done=fin, on_fail=lambda e: (self.pp.setVisible(False), self.b_pre.setEnabled(True), error(self, e)), on_progress=prog)

    # ------------------------------------------------------------- 3B tekrar
    def _setup3d(self):
        A = self.A; self.fig.clear(); self.tr = None
        if A.track is None:
            self.canvas.draw_idle(); return
        tr = A.track
        n = len(tr['t']); step = max(1, n // 3000)
        t_ = tr['t'][::step]; lat = tr['lat'][::step]; lon = tr['lon'][::step]; alt = tr['rel'][::step]
        x = hav(lat[0], lon[0], lat[0], lon) * np.sign(lon - lon[0])
        y = hav(lat[0], lon[0], lat, lon[0]) * np.sign(lat - lat[0])
        att = A.L.s('ATT'); gps = A.L.s('GPS')
        self.tr = {'t': t_, 'x': x, 'y': y, 'z': alt,
                   'roll': np.interp(t_, att['t'], att['Roll']) if att.has('Roll') else np.zeros_like(t_),
                   'pitch': np.interp(t_, att['t'], att['Pitch']) if att.has('Pitch') else np.zeros_like(t_),
                   'gs': np.interp(t_, gps['t'], gps['Spd']) if gps.has('Spd') else np.zeros_like(t_)}
        ax = self.fig.add_subplot(111, projection='3d'); self.ax = ax
        ax.set_facecolor('#0F172A')
        for a in (ax.xaxis, ax.yaxis, ax.zaxis):
            a.set_pane_color((0.07, 0.1, 0.18, 1)); a.label.set_color('#CBD5E1')
        ax.tick_params(colors='#94A3B8', labelsize=7)
        ax.plot(x, y, np.zeros_like(alt), color='#334155', lw=0.8)
        ax.plot(x, y, alt, color='#3B82F6', lw=1.2)
        if A.verdict.get('kind') == 'crash':
            ax.scatter([x[-1]], [y[-1]], [alt[-1]], color='#DC2626', s=60, marker='X')
        ax.scatter([0], [0], [0], color='#16A34A', s=40, marker='^')
        ax.set_xlabel('E (m)', fontsize=8); ax.set_ylabel('N (m)', fontsize=8); ax.set_zlabel('Alt (m)', fontsize=8)
        self.pt = ax.plot([x[0]], [y[0]], [alt[0]], 'o', color='#F59E0B', ms=9)[0]
        self.stem = ax.plot([x[0], x[0]], [y[0], y[0]], [0, alt[0]], color='#F59E0B', lw=0.8, ls=':')[0]
        self.trail = ax.plot([], [], [], color='#F59E0B', lw=2.2)[0]
        self.fig.tight_layout()
        self.slider.blockSignals(True); self.slider.setRange(0, len(t_) - 1); self.slider.setValue(0); self.slider.blockSignals(False)
        self._frame(0)

    def toggle_play(self):
        if self.timer.isActive():
            self.timer.stop(); self.b_play.setText(t('play'))
        elif self.tr is not None:
            if self.slider.value() >= self.slider.maximum(): self.slider.setValue(0)
            self.timer.start(); self.b_play.setText(t('pause'))
            self._last = time.time()

    def _tick(self):
        tr = self.tr
        if tr is None: return
        mult = float(self.spd.currentText()[:-1])
        i = self.slider.value()
        now = time.time(); dt = (now - getattr(self, '_last', now)) * mult; self._last = now
        target = tr['t'][i] + dt
        j = int(np.searchsorted(tr['t'], target))
        if j <= i: j = i + 1
        if j >= len(tr['t']):
            self.slider.setValue(len(tr['t']) - 1); self.toggle_play(); return
        self.slider.setValue(j)

    def _frame(self, i):
        tr = self.tr
        if tr is None: return
        x, y, z = tr['x'][i], tr['y'][i], tr['z'][i]
        self.pt.set_data_3d([x], [y], [z])
        self.stem.set_data_3d([x, x], [y, y], [0, z])
        k0 = max(0, i - 60)
        self.trail.set_data_3d(tr['x'][k0:i + 1], tr['y'][k0:i + 1], tr['z'][k0:i + 1])
        self.canvas.draw_idle()
        tt = tr['t'][i]
        m = '-'
        for mt, n, _, _ in self.A.L.modes:
            if mt <= tt: m = K.mode_name(self.A.vehicle, n)
        self.info.setText(t('replay_info', t=fmt_t(tt), a=float(z), s=float(tr['gs'][i]), r=float(tr['roll'][i]), p=float(tr['pitch'][i]), m=m))


# ----------------------------------------------------------- Zaman çizelgesi
class TimelinePage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        bar = QHBoxLayout()
        bar.addWidget(label(t('filter')))
        self.cat = QComboBox(); self.cat.addItem(t('all'), '')
        for c in ('flight', 'mode', 'err', 'ev', 'msg'): self.cat.addItem(R('cat_' + c, lang()), c)
        self.cat.currentIndexChanged.connect(self.fill); bar.addWidget(self.cat)
        self.sev = QCheckBox(R('sev1', lang()) + ' / ' + R('sev2', lang())); self.sev.toggled.connect(self.fill); bar.addWidget(self.sev)
        self.q = QLineEdit(); self.q.setPlaceholderText(t('search')); self.q.textChanged.connect(self.fill); bar.addWidget(self.q, 1)
        v.addLayout(bar)
        self.img = ImageView(); self.img.setMaximumHeight(260); v.addWidget(self.img)
        self.tbl = QTableWidget(0, 3); self.tbl.setHorizontalHeaderLabels([R('e_time', lang()), R('e_type', lang()), R('e_text', lang())])
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl.verticalHeader().setVisible(False); self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True); self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        v.addWidget(self.tbl, 1)
        self.A = None

    def on_analysis(self, A):
        self.A = A; lg = lang()
        run_bg(lambda: charts.chart_timeline(A, lg), on_done=self.img.set_png)
        self.fill()

    def fill(self, *_):
        if not self.A: return
        lg = lang(); c = self.cat.currentData(); q = self.q.text().strip().lower()
        rows = []
        for e in self.A.events:
            if c and e['cat'] != c: continue
            if self.sev.isChecked() and e['sev'] == 0: continue
            txt = texts.render(e['text'], lg)
            if q and q not in txt.lower(): continue
            rows.append((e, txt))
        self.tbl.setRowCount(len(rows))
        cols = {1: QColor('#713F12'), 2: QColor('#7F1D1D')}
        for i, (e, txt) in enumerate(rows):
            for j, val in enumerate((fmt_t(e['t']), R('cat_' + e['cat'], lg), txt)):
                it = QTableWidgetItem(val)
                if e['sev'] in cols: it.setBackground(cols[e['sev']])
                self.tbl.setItem(i, j, it)
        self.tbl.resizeColumnToContents(0); self.tbl.resizeColumnToContents(1)


# ----------------------------------------------------------------- Danışman
class AdvisorPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        self.use_ai = QCheckBox(t('use_ai')); self.use_ai.setChecked(bool(win.settings.get('online', True)))
        self.use_ai.toggled.connect(self._mode); top.addWidget(self.use_ai)
        self.mode = label('', 'muted'); top.addWidget(self.mode, 1)
        top.addWidget(button('🧹', self.clear, tip='Clear'))
        v.addLayout(top)
        self.chat = QTextBrowser(); self.chat.setOpenExternalLinks(True); v.addWidget(self.chat, 1)
        v.addWidget(label(t('suggest') + ':', 'muted'))
        sg = QGridLayout(); sg.setSpacing(6)
        for i, s in enumerate(t('sugg')):
            b = QPushButton(s); b.setCursor(Qt.PointingHandCursor); b.clicked.connect(lambda _=False, s=s: self.ask(s)); sg.addWidget(b, i // 4, i % 4)
        v.addLayout(sg)
        inp = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText(t('ask')); self.q.returnPressed.connect(lambda: self.ask(self.q.text()))
        inp.addWidget(self.q, 1)
        self.b_send = button(t('send'), lambda: self.ask(self.q.text()), primary=True); inp.addWidget(self.b_send)
        v.addLayout(inp)
        self.status = label('', 'muted'); v.addWidget(self.status)
        self.A = None; self.adv = None; self.hist = []
        self._mode()

    def _mode(self):
        self.mode.setText(t('mode_online') if self.use_ai.isChecked() else t('mode_offline'))

    def clear(self):
        self.hist = []; self.adv = None; self._render()

    def on_analysis(self, A):
        self.A = A; self.adv = None; self.hist = []; self._render()

    def _render(self):
        d = 'rtl' if lang() == 'ar' else 'ltr'
        out = [f'<div dir="{d}">']
        for who, txt in self.hist:
            if who == 'u':
                out.append(f'<p style="margin-top:12px"><b style="color:#93C5FD">{E(t("you"))}:</b> {E(txt)}</p>')
            else:
                out.append(f'<div style="background:#111C33;padding:8px"><b style="color:#34D399">{E(t("advisor"))}:</b><br>{_md(txt)}</div>')
        out.append('</div>')
        self.chat.setHtml(''.join(out))
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def ask(self, q):
        q = (q or '').strip()
        if not q: return
        if not self.A: return error(self, t('no_log'))
        self.q.clear(); self.hist.append(('u', q)); self._render()
        from ..core.advisor import offline_answer
        from ..core import ai as AI
        lg = lang(); A = self.A; s = self.win.settings
        key = AI.available(s)
        if not self.use_ai.isChecked():
            self.hist.append(('a', offline_answer(A, q, lg))); self._render(); return
        if not key:
            self.hist.append(('a', t('need_key') + '\n\n' + offline_answer(A, q, lg))); self._render(); return
        if self.adv is None or self.adv.lang != lg:
            try:
                self.adv = AI.make_advisor(A, s, lg, self.win.usage)
            except Exception as e:
                self.hist.append(('a', t('ai_fail', e=e) + '\n\n' + offline_answer(A, q, lg))); self._render(); return
        self.b_send.setEnabled(False); self.status.setText(t('thinking', x='…'))
        adv = self.adv
        w = None

        def job():
            return adv.ask(q, on_status=lambda n: w.progress.emit(n))

        def ok(ans):
            self.b_send.setEnabled(True); self.status.setText(''); self.hist.append(('a', ans)); self._render()

        def fail(e):
            self.b_send.setEnabled(True); self.status.setText('')
            # Yarım kalmış tur geçmişini temizle
            msgs = getattr(adv, 'messages', None) or getattr(adv, 'contents', None)
            if msgs and msgs[-1].get('role') == 'user': msgs.clear()
            self.hist.append(('a', t('ai_fail', e=e[:200]) + '\n\n' + offline_answer(A, q, lg))); self._render()
        w = run_bg(job, on_done=ok, on_fail=fail, on_progress=lambda n: self.status.setText(t('thinking', x=n)))


def _md(txt):
    """Basit markdown → HTML (kalın, başlık, liste)."""
    import re
    out = []
    for line in txt.splitlines():
        s = E(line)
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
        if s.startswith('### ') or s.startswith('## ') or s.startswith('# '):
            out.append(f'<p><b style="color:#93C5FD">{s.lstrip("# ")}</b></p>')
        elif s.lstrip().startswith(('- ', '* ', '• ')):
            out.append('&nbsp;&nbsp;• ' + s.lstrip()[2:] + '<br>')
        elif not s.strip():
            out.append('<br>')
        else:
            out.append(s + '<br>')
    return ''.join(out)


# ---------------------------------------------------------------- Alıştırma
class PracticePage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(24, 16, 24, 16)
        top = QHBoxLayout()
        top.addWidget(button('🔄 ' + t('new_q'), self.new, primary=True))
        self.score_l = label('', 'h2'); top.addWidget(self.score_l, 1)
        v.addLayout(top)
        v.addWidget(label(t('practice_src'), 'muted', wrap=True))
        c = card(); cv = QVBoxLayout(c); cv.setContentsMargins(20, 18, 20, 18)
        self.ql = label('', 'h1', wrap=True); cv.addWidget(self.ql)
        self.grp = QButtonGroup(self); self.opts = []
        for i in range(4):
            r = QRadioButton(); r.setStyleSheet('font-size:11pt; padding:6px'); self.grp.addButton(r, i); self.opts.append(r); cv.addWidget(r)
        self.res = label('', wrap=True); cv.addWidget(self.res)
        row = QHBoxLayout()
        self.b_check = button(t('check'), self.check, primary=True); self.b_next = button(t('next'), self.next_q)
        self.b_chart = button(t('go_chart'), self.go_chart); self.b_lib = button(t('go_lib'), self.go_lib)
        self.b_chart.setVisible(False); self.b_lib.setVisible(False)
        row.addWidget(self.b_check); row.addWidget(self.b_next); row.addWidget(self.b_chart); row.addWidget(self.b_lib); row.addStretch(1); cv.addLayout(row)
        v.addWidget(c); v.addStretch(1)
        self.qs = []; self.i = 0; self.ok = 0; self.answered = 0
        self.new()

    def on_analysis(self, A):
        self.new()

    def new(self):
        from ..core.practice import generate
        self.qs = generate(self.win.A, lang(), 10, int(time.time())); self.i = 0; self.ok = 0; self.answered = 0
        self._show()

    def _show(self):
        self._score()
        if not self.qs: self.ql.setText('-'); return
        q = self.qs[self.i]
        self.ql.setText(f'{self.i + 1}/{len(self.qs)} · {q["q"]}')
        self.grp.setExclusive(False)
        for k, r in enumerate(self.opts):
            r.setChecked(False); r.setVisible(k < len(q['opts'])); r.setEnabled(True)
            if k < len(q['opts']): r.setText(q['opts'][k])
            r.setStyleSheet('font-size:11pt; padding:6px')
        self.grp.setExclusive(True)
        self.res.setText(''); self.b_check.setEnabled(True); self.b_chart.setVisible(False); self.b_lib.setVisible(False)

    def _score(self):
        best = self.win.settings.get('practice_best', 0)
        self.score_l.setText(t('score', a=self.ok, b=self.answered, best=best))

    def check(self):
        if not self.qs: return
        k = self.grp.checkedId()
        if k < 0: return
        q = self.qs[self.i]; good = k == q['ans']
        self.answered += 1; self.ok += good
        for j, r in enumerate(self.opts):
            r.setEnabled(False)
            if j == q['ans']: r.setStyleSheet('font-size:11pt; padding:6px; color:#4ADE80; font-weight:700')
            elif j == k: r.setStyleSheet('font-size:11pt; padding:6px; color:#F87171')
        txt = (t('correct') if good else t('wrong', c=q['opts'][q['ans']])) + '\n' + q.get('exp', '')
        we = q.get('wexp') or []
        if not good and k < len(we) and we[k]: txt += '\n\n❓ ' + t('why_wrong') + ' ' + we[k]
        self.res.setText(txt)
        self.b_chart.setVisible(bool(q.get('chart') and self.win.A)); self.b_lib.setVisible(bool(q.get('lib')))
        self.b_check.setEnabled(False)
        if self.ok > self.win.settings.get('practice_best', 0):
            self.win.settings['practice_best'] = self.ok; self.win.settings.save()
        self._score()

    def go_chart(self):
        q = self.qs[self.i] if self.qs else None
        if not q or not q.get('chart'): return
        self.win.goto('charts'); self.win.pages['charts'].show_key(q['chart'], q.get('t'))

    def go_lib(self):
        q = self.qs[self.i] if self.qs else None
        if not q or not q.get('lib'): return
        pg = self.win.pages[q['lib']]; self.win.goto(q['lib'])
        try: pg.q.setText(q['key'])
        except Exception: pass

    def next_q(self):
        if not self.qs: return
        if self.i + 1 >= len(self.qs): return self.new()
        self.i += 1; self._show()
