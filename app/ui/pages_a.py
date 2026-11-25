"""Sayfalar: Analiz, Grafikler, Harita/3B, Zaman çizelgesi, Danışman, Alıştırma."""
from __future__ import annotations
import html, os, time
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextBrowser, QListWidget, QListWidgetItem,
                               QSplitter, QComboBox, QTabWidget, QSlider, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
                               QCheckBox, QRadioButton, QButtonGroup, QPushButton, QFileDialog, QGridLayout, QAbstractItemView, QSpinBox)
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
        if u == 'fb:why': return self._feedback()
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

    def _feedback(self):
        """'Teşhis doğru muydu?' penceresi: yalnız teşhis özeti (log değil) izinle gönderilir."""
        A = self.win.A
        if not A: return
        from PySide6.QtWidgets import QDialog, QFormLayout, QTextEdit
        from ..core import feedback as FB
        lg = lang(); root = A.root or {}
        dl = QDialog(self); dl.setWindowTitle(t('fb_title')); dl.resize(620, 520)
        if lg == 'ar': dl.setLayoutDirection(Qt.RightToLeft)
        vv = QVBoxLayout(dl)
        it = label(t('fb_intro'), 'muted'); it.setWordWrap(True); vv.addWidget(it)
        vv.addWidget(label(t('fb_prog', v=texts.T('v_' + (A.verdict.get('kind') or 'normal'), lg),
                             c=texts.T('cause_' + root['cause'], lg) if root.get('cause') and root['cause'] != 'unknown' else '-')))
        fm = QFormLayout()
        grp = QButtonGroup(dl); row = QHBoxLayout(); rb = {}
        for k in ('yes', 'part', 'no'):
            r_ = QRadioButton(t('fb_' + k)); grp.addButton(r_); row.addWidget(r_); rb[k] = r_
        rb['yes'].setChecked(True)
        w_ = QWidget(); w_.setLayout(row); fm.addRow(t('fb_q'), w_)
        oc = QComboBox()
        for k in FB.OUTCOMES: oc.addItem(texts.T('v_' + k, lg), k)
        i0 = FB.OUTCOMES.index(A.verdict.get('kind')) if A.verdict.get('kind') in FB.OUTCOMES else 2
        oc.setCurrentIndex(i0); fm.addRow(t('fb_outcome'), oc)
        cc = QComboBox(); cc.addItem(t('fb_unknown'), 'unknown')
        for k in FB.CAUSES[:-1]: cc.addItem(texts.T('cause_' + k, lg), k)
        if root.get('cause') in FB.CAUSES[:-1]: cc.setCurrentIndex(FB.CAUSES.index(root['cause']) + 1)
        fm.addRow(t('fb_cause'), cc)
        vv.addLayout(fm)
        vv.addWidget(label(t('fb_note')))
        note = QTextEdit(); note.setMaximumHeight(120); vv.addWidget(note)
        ok = QCheckBox(t('fb_consent')); vv.addWidget(ok)
        def send():
            if not ok.isChecked(): return error(dl, t('fb_need_consent'))
            vok = next(k for k, r_ in rb.items() if r_.isChecked())
            d = FB.build(A, vok, oc.currentData(), cc.currentData(), note.toPlainText(), lg)
            def done(sent):
                info(self, t('fb_sent') if sent else t('fb_queued')); dl.accept()
            run_bg(FB.send, d, on_done=done, on_fail=lambda e: error(dl, e))
        bb = QHBoxLayout(); bb.addStretch(1)
        bb.addWidget(button(t('close'), dl.reject)); bb.addWidget(button(t('fb_send'), send, primary=True))
        vv.addLayout(bb)
        dl.exec()

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

CT = {
    'tab_info': ('Açıklama', 'Explanation', 'الشرح'), 'tab_modes': ('Uçuş modları', 'Flight modes', 'أوضاع الطيران'),
    'tab_mp': ('Mission Planner', 'Mission Planner', 'Mission Planner'),
    'tab_src': ('Kaynak: log alanı + parametre', 'Source: log field + parameter', 'المصدر: حقل السجل + المعامل'),
    'm_desc': ('Mod ne yapar', 'What the mode does', 'ماذا يفعل الوضع'),
    'm_help': ('Satıra tıklayın: imleç o ana gider · çift tıklayın: grafik o moda yakınlaşır', 'Click a row: cursor jumps there · double-click: chart zooms to that mode',
               'انقر صفاً: ينتقل المؤشر · انقر مرتين: يقترب الرسم من ذلك الوضع'),
    'mp_fields': ('Review Log\'da işaretlenecek alanlar', 'Fields to tick in Review Log', 'الحقول التي تُحدَّد في Review Log'),
    'mp_params': ('İlgili ayarlar (bu logdaki değerler)', 'Related parameters (values in this log)', 'المعاملات المرتبطة (القيم في هذا السجل)'),
    'mp_times': ('Önemli anlar (TimeUS ile Review Log\'da bulun)', 'Key moments (find them by TimeUS in Review Log)', 'لحظات مهمة (ابحث عنها بـ TimeUS)'),
    'mp_copy': ('Alanları kopyala', 'Copy fields', 'نسخ الحقول'), 'mp_copyp': ('Ayarları kopyala', 'Copy parameters', 'نسخ المعاملات'),
    'mp_xml': ('Mission Planner grafik dosyası kaydet', 'Save Mission Planner graph file', 'حفظ ملف رسوم Mission Planner'),
    'mp_xml_ok': ('Kaydedildi: {p}\n\nMission Planner kurulum klasöründeki "graphs" klasörüne kopyalayın (ör. C:\\Program Files (x86)\\Mission Planner\\graphs). '
                  'Review Log\'da sağ tık menüsündeki hazır grafikler arasında "Pixhawk Log Analiz" başlığıyla görünür. Aynı dosya MAVExplorer ile de çalışır.',
                  'Saved: {p}\n\nCopy it into the "graphs" folder of the Mission Planner install (e.g. C:\\Program Files (x86)\\Mission Planner\\graphs). '
                  'In Review Log it appears among the preset graphs (right-click) under "Pixhawk Log Analiz". The same file works with MAVExplorer.',
                  'تم الحفظ: {p}\n\nانسخه إلى مجلد "graphs" في مجلد تثبيت Mission Planner. يظهر في Review Log ضمن الرسوم الجاهزة (النقر الأيمن) باسم "Pixhawk Log Analiz".'),
    'mp_copied': ('Panoya kopyalandı', 'Copied to clipboard', 'نُسخ إلى الحافظة'),
    't_mode': ('Mod değişimi', 'Mode change', 'تغيير الوضع'), 't_crash': ('Kırım/son', 'Crash/end', 'التحطم/النهاية'),
    't_root': ('İlk belirti (kök neden)', 'First symptom (root cause)', 'أول عرض (السبب الجذري)'), 't_motor': ('Motor olayı', 'Motor event', 'حدث محرك'),
}


def ct(k):
    from ..core import viz
    return viz.tx(CT[k], lang())


class ChartsPage(Page):
    def __init__(self, win):
        super().__init__(win)
        from PySide6.QtWidgets import QApplication
        from .chartview import ChartView
        h = QHBoxLayout(self); h.setContentsMargins(16, 12, 16, 12)
        self.list = QListWidget(); self.list.setFixedWidth(300)
        for k in CHART_KEYS:
            it = QListWidgetItem(R(k, lang())); it.setData(Qt.UserRole, k); self.list.addItem(it)
        self.list.currentItemChanged.connect(self._show)
        h.addWidget(self.list)
        sp = QSplitter(Qt.Vertical)
        self.view = ChartView(); self.view.clicked.connect(self._clicked); sp.addWidget(self.view)
        self.tabs = QTabWidget()
        self.lesson = QTextBrowser(); self.tabs.addTab(self.lesson, 'ⓘ ' + ct('tab_info'))
        self.src = QTextBrowser(); self.tabs.addTab(self.src, '🔎 ' + ct('tab_src'))
        mw = QWidget(); mv = QVBoxLayout(mw); mv.setContentsMargins(4, 4, 4, 4)
        mv.addWidget(label(ct('m_help'), 'muted', wrap=True))
        self.mt = QTableWidget(0, 7)
        self.mt.setHorizontalHeaderLabels([R(k, lang()) for k in ('m_start', 'm_clock', 'm_end', 'm_dur', 'm_mode', 'm_why')] + [ct('m_desc')])
        self.mt.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.mt.verticalHeader().setVisible(False); self.mt.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mt.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mt.cellClicked.connect(self._mode_click); self.mt.cellDoubleClicked.connect(self._mode_dbl)
        mv.addWidget(self.mt, 1)
        self.mt_src = label('', 'muted', wrap=True); self.mt_src.setTextInteractionFlags(Qt.TextSelectableByMouse); mv.addWidget(self.mt_src)
        self.tabs.addTab(mw, '🎛 ' + ct('tab_modes'))
        pw = QWidget(); pv = QVBoxLayout(pw); pv.setContentsMargins(4, 4, 4, 4)
        pb = QHBoxLayout()
        pb.addWidget(button('📋 ' + ct('mp_copy'), self._copy_fields)); pb.addWidget(button('📋 ' + ct('mp_copyp'), self._copy_params))
        pb.addWidget(button('💾 ' + ct('mp_xml'), self._save_xml, primary=True)); pb.addStretch(1)
        pv.addLayout(pb)
        self.mp = QTextBrowser(); pv.addWidget(self.mp, 1)
        self.tabs.addTab(pw, '🛩 ' + ct('tab_mp'))
        sp.addWidget(self.tabs); sp.setSizes([680, 260])
        h.addWidget(sp, 1)
        self.cache = {}; self.A = None; self.segs = []; self._fields = []; self._params = []; self._pending = None

    def on_analysis(self, A):
        self.cache = {}; self.A = A
        from ..core import viz
        self.segs = viz.segments(A, lang())
        self._fill_modes()
        if self.list.currentRow() < 0: self.list.setCurrentRow(0)
        else: self._show(self.list.currentItem())

    # ------------------------------------------------------------ grafik üretimi (arka planda, Figure olarak)
    def _make(self, k, t_=None, span=None):
        A = self.A; lg = lang()

        def job():
            charts.want_fig(True)
            try:
                if t_ is not None or span is not None: return charts.render_marked(k, A, lg, t_, span)
                fn = dict(list(charts.ALL) + [('c_health', charts.chart_health), ('c_timeline', charts.chart_timeline)]).get(k)
                return fn(A, lg) if fn else None
            finally:
                charts.want_fig(False)

        def done(fig):
            if t_ is None and span is None: self.cache[k] = fig
            cur = self.list.currentItem()
            if cur and cur.data(Qt.UserRole) == k: self.view.set_figure(fig, A)

        self.view.busy()
        run_bg(job, on_done=done, on_fail=lambda e: self.view.set_message(str(e)))

    def _show(self, it, *_):
        if not it: return
        k = it.data(Qt.UserRole)
        self.lesson.setHtml(summary_html.lesson_html(k, lang()) + self._extra_html(k)); self.src.setHtml(self._src_html(k))
        self._fill_mp(k)
        if self.A is None: return
        if k in self.cache: self.view.set_figure(self.cache[k], self.A)
        else: self._make(k)

    def show_key(self, k, t_=None, span=None):
        """Grafiği seç; t_/span verilirse ilgili an turuncu işaretli çizilir (alıştırma / ders rehberi)."""
        if k not in CHART_KEYS: return
        i = CHART_KEYS.index(k)
        self.list.blockSignals(True); self.list.setCurrentRow(i); self.list.blockSignals(False)
        self.lesson.setHtml(summary_html.lesson_html(k, lang()) + self._extra_html(k)); self.src.setHtml(self._src_html(k)); self._fill_mp(k)
        if self.A is None: return
        if t_ is None and span is None:
            if k in self.cache: self.view.set_figure(self.cache[k], self.A)
            else: self._make(k)
            return
        self._make(k, t_, span)

    # ------------------------------------------------------------ imleç eşitleme
    def _clicked(self, t):
        try: self.win.pages['map'].goto_time(t, switch=False)
        except Exception: pass
        try: self.win.pages['video'].goto_log_time(t)
        except Exception: pass

    def set_cursor(self, t):
        self.view.set_cursor(t)

    # ------------------------------------------------------------ mod tablosu
    def _fill_modes(self):
        from ..core import viz
        from ..core.report import mode_rows, _tint
        lg = lang(); rows = mode_rows(self.A, lg)
        self.mt.setRowCount(len(rows))
        for i, (r, s_) in enumerate(zip(rows, self.segs)):
            vals = r[:6] + [viz.mode_desc(s_['name'], lg)]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if j == 4:
                    it.setBackground(QColor(s_['col'])); it.setForeground(QColor('white'))
                    f = it.font(); f.setBold(True); it.setFont(f)
                if j == 5 and s_['fs']: it.setBackground(QColor('#7F1D1D'))
                self.mt.setItem(i, j, it)
        for j in range(6): self.mt.resizeColumnToContents(j)
        from ..core import sources
        try: self.mt_src.setText('🔎 ' + sources.short(self.A, 'sec_modes', lg) + '\n' + sources.t('pix', lg))
        except Exception: self.mt_src.setText('')
        tips = {0: 'MODE.TimeUS', 1: 'GPS.GWk + GPS.GMS', 2: 'MODE.TimeUS', 4: 'MODE.Mode · MODE.ModeNum', 5: 'MODE.Rsn'}
        for j, tip in tips.items():
            h_ = self.mt.horizontalHeaderItem(j)
            if h_: h_.setToolTip(tip)

    def _mode_click(self, r, _c):
        if 0 <= r < len(self.segs):
            t = self.segs[r]['t0']; self.view.set_cursor(t); self._clicked(t)

    def _mode_dbl(self, r, _c):
        if 0 <= r < len(self.segs):
            s_ = self.segs[r]; self.view.zoom_to(s_['t0'], s_['t1'])

    # ------------------------------------------------------------ Mission Planner
    def _extra_html(self, k):
        if k != 'c_motors' or self.A is None: return ''
        from ..core import viz
        lg = lang()
        try: ev = viz.motor_events(self.A, lg)
        except Exception: return ''
        M = viz.motors(self.A, lg)
        rows = ''.join(f'<tr><td><b>{E(m["name"])}</b></td><td>{E(m["ch"])}</td><td>{E(str(m["kind"]))}</td></tr>' for m in M)
        evs = ''.join(f'<li style="color:#F87171"><b>{E(viz.event_text(self.A, e, lg))}</b></li>' for e in ev.get('events', [])[:10])
        d = 'rtl' if lg == 'ar' else 'ltr'
        return (f'<div dir="{d}"><p><b>{E(viz.frame_text(self.A, lg))}</b></p>' + (f'<ul>{evs}</ul>' if evs else '') +
                f'<table cellpadding="3">{rows}</table></div>')

    def _src_html(self, k):
        if self.A is None: return ''
        from ..core import sources
        try:
            return sources.html(self.A, k, lang(), dark=True)
        except Exception:
            return ''

    def _fill_mp(self, k):
        from ..core import viz
        A = self.A; lg = lang(); d = 'rtl' if lg == 'ar' else 'ltr'
        if A is None: self.mp.setHtml(''); return
        f, pv = viz.mp_info(A, k)
        self._fields = f; self._params = pv
        moments = []
        for s_ in self.segs[1:30]:
            moments.append((s_['t0'], f"{ct('t_mode')}: {s_['prev']} → {s_['name']} ({s_['why']})"))
        root = (A.root or {}).get('t')
        if root is not None: moments.append((root, ct('t_root')))
        if A.verdict.get('kind') == 'crash' and A.flights: moments.append((A.flights[-1][1], ct('t_crash')))
        if k in ('c_motors', 'c_rcou', 'c_esc'):
            try:
                for e in viz.motor_events(A, lg).get('events', [])[:6]:
                    moments.append((e['t'], f"{ct('t_motor')}: {viz.event_text(A, e, lg)}"))
            except Exception: pass
        moments.sort()
        tm = ''.join(f'<tr><td>{fmt_t(t_)}</td><td>{E(viz.clock(A, t_) or "-")}</td><td><code>{viz.time_us(A, t_)}</code></td><td>{E(x)}</td></tr>' for t_, x in moments)
        pr = ''.join(f'<tr><td><code>{E(n)}</code></td><td>{v:g}</td></tr>' for n, v in pv)
        self.mp.setHtml(f'<div dir="{d}"><p><b>{E(ct("mp_fields"))}</b><br><code style="font-size:11pt">{E("  ".join(f)) or "-"}</code></p>'
                        f'<p><b>{E(ct("mp_params"))}</b></p><table cellpadding="2">{pr}</table>'
                        f'<p><b>{E(ct("mp_times"))}</b></p><table cellpadding="2"><tr><th>t</th><th>🕘</th><th>TimeUS</th><th></th></tr>{tm}</table></div>')

    def _copy_fields(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(' '.join(self._fields)); self.win.set_status(ct('mp_copied'))

    def _copy_params(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText('\n'.join(f'{n},{v:g}' for n, v in self._params)); self.win.set_status(ct('mp_copied'))

    def _save_xml(self):
        from ..core import viz
        if self.A is None: return error(self, t('no_log'))
        start = os.path.join(os.path.expanduser('~'), 'Documents', 'pixhawk_log_analiz_graphs.xml')
        for cand in (r'C:\Program Files (x86)\Mission Planner\graphs', r'C:\Program Files\Mission Planner\graphs'):
            if os.path.isdir(cand) and os.access(cand, os.W_OK): start = os.path.join(cand, 'pixhawk_log_analiz_graphs.xml'); break
        p, _ = QFileDialog.getSaveFileName(self, ct('mp_xml'), start, 'XML (*.xml)')
        if not p: return
        try:
            with open(p, 'w', encoding='utf-8') as fh: fh.write(viz.mavgraphs_xml(self.A, lang()))
            info(self, ct('mp_xml_ok').format(p=p))
        except Exception as e:
            error(self, e)


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
        from ..core import viz as _viz
        self.mcol = QComboBox()
        self.mcol.addItem(_viz.tx(('Renk: uçuş modu', 'Colour: flight mode', 'اللون: وضع الطيران'), lang()), 'mode')
        self.mcol.addItem(_viz.tx(('Renk: irtifa', 'Colour: altitude', 'اللون: الارتفاع'), lang()), 'alt')
        self.mcol.currentIndexChanged.connect(lambda *_: self.render_map()); bar.addWidget(self.mcol)
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
        from .chartview import StickView
        r3 = QHBoxLayout(); r3.addWidget(self.canvas, 1)
        self.sticks = StickView(); r3.addWidget(self.sticks)
        rv.addLayout(r3, 1)
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
        self.A = None; self.tr = None; self.rc = None; self.segs = []

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

    def goto_time(self, tt, switch=True):
        if self.tr is None: return
        if switch: self.tabs.setCurrentIndex(1)
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
        col = self.mcol.currentData() if hasattr(self, 'mcol') else 'mode'
        run_bg(lambda: charts.chart_map(A, lg, online=online, src=src, color=col), on_done=lambda b: self.map.set_png(b) if b else None)

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
        from ..core import viz
        segs = viz.segments(A, lang()); self.segs = segs
        drawn = False
        for sg in segs:
            k = (t_ >= sg['t0']) & (t_ <= sg['t1'] + 1e-6)
            if k.sum() >= 2: ax.plot(x[k], y[k], alt[k], color=sg['col'], lw=1.5); drawn = True
        if not drawn: ax.plot(x, y, alt, color='#3B82F6', lw=1.2)
        rc = A.L.s('RCIN'); m = viz.rc_map(A)
        self.rc = None
        if rc.has(f"C{m['roll']}") and viz.rc_active(A):
            g = lambda k, c=True: np.interp(t_, rc['t'], viz.stick_norm(A, m[k], rc[f"C{m[k]}"], centred=c)) if rc.has(f"C{m[k]}") else np.zeros_like(t_)
            self.rc = {'roll': g('roll'), 'pitch': g('pitch'), 'thr': g('thr', False), 'yaw': g('yaw')}
        self.sticks.set_values(None)
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
        from ..core import viz
        ck = viz.clock(self.A, tt)
        if ck: m = f'{m}  ·  🕘 {ck}'
        if self.rc is not None:
            self.sticks.set_values((self.rc['yaw'][i], self.rc['thr'][i] * 2 - 100, self.rc['roll'][i], -self.rc['pitch'][i]))
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
        from ..core import qbank as QB
        from .pages_q import tx as qtx
        v = QVBoxLayout(self); v.setContentsMargins(24, 16, 24, 16)
        top = QHBoxLayout()
        top.addWidget(button('🔄 ' + t('new_q'), self.new, primary=True))
        # v1.1.10: soru kaynağı (log + banka), konu, seviye
        self.srcsel = QComboBox()
        for k in ('mix', 'bank', 'log', 'wrong'): self.srcsel.addItem(qtx('pr_' + k), k)
        self.topsel = QComboBox(); self.topsel.addItem(qtx('all_t'), None)
        for k in QB.TOPICS: self.topsel.addItem(QB.topic_name(k, lang()), k)
        self.lvlsel = QComboBox(); self.lvlsel.addItem(qtx('all_l'), None)
        for n_ in (1, 2, 3): self.lvlsel.addItem(QB.level_name(n_, lang()), n_)
        self.nsel = QSpinBox(); self.nsel.setRange(5, 50); self.nsel.setValue(10); self.nsel.setSuffix(' ' + qtx('pr_q'))
        for w_ in (self.srcsel, self.topsel, self.lvlsel, self.nsel): top.addWidget(w_)
        self.score_l = label('', 'h2'); top.addWidget(self.score_l, 1)
        top.addWidget(button('🗃 ' + qtx('title'), lambda: self.win.goto('qbank')))
        v.addLayout(top)
        self.src_l = label(t('practice_src'), 'muted', wrap=True); v.addWidget(self.src_l)
        c = card(); cv = QVBoxLayout(c); cv.setContentsMargins(20, 18, 20, 18)
        self.meta = label('', 'muted'); cv.addWidget(self.meta)
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
        self.qs = []; self.i = 0; self.ok = 0; self.answered = 0; self._ids = None
        for w_ in (self.srcsel, self.topsel, self.lvlsel): w_.currentIndexChanged.connect(lambda *_: (setattr(self, '_ids', None), self.new()))
        self.new()

    def on_analysis(self, A):
        self.new()

    def start_bank(self, ids=None):
        """Soru Bankası sayfasından: verilen soru kimlikleriyle alıştırma."""
        self._ids = set(ids) if ids else None
        self.srcsel.blockSignals(True); self.srcsel.setCurrentIndex(self.srcsel.findData('bank')); self.srcsel.blockSignals(False)
        self.new()

    def new(self):
        from ..core.practice import generate
        from ..core import qbank as QB
        from .pages_q import tx as qtx
        import random as _r
        src = self.srcsel.currentData(); n = self.nsel.value(); lg = lang(); seed = int(time.time() * 1000) % 2 ** 31
        topics = {self.topsel.currentData()} if self.topsel.currentData() else None
        levels = {self.lvlsel.currentData()} if self.lvlsel.currentData() else None
        qs = []
        if src in ('mix', 'bank', 'wrong'):
            bank = QB.load(self.win.archive)
            st = self.win.settings.get('qbank_stats', {}) or {}
            if src == 'wrong':
                w = {k: (v[1] - v[0]) / max(1, v[1]) + 0.1 * (v[1] - v[0]) for k, v in st.items() if v[1] > v[0]}
                pick = QB.pick(bank, topics, levels, n, seed, ids=set(w), weights=w)
            else:
                nb = n if src == 'bank' or self.win.A is None else max(1, n - n // 3)
                pick = QB.pick(bank, topics, levels, nb, seed, ids=self._ids)
            rnd = _r.Random(seed)
            qs = [QB.to_item(q, lg, rnd) for q in pick]
        if src in ('mix', 'log') and self.win.A is not None and (src == 'log' or not topics):
            lq = [x for x in generate(self.win.A, lg, n, seed) if not x.get('lib')]
            qs = (qs + lq[:max(0, n - len(qs)) if src == 'mix' else n])
            _r.Random(seed).shuffle(qs)
        elif src == 'log' and not qs:
            qs = generate(self.win.A, lg, n, seed)
        self.src_l.setText(qtx('pr_src_' + src) if not (src == 'wrong' and not qs) else qtx('pr_no_wrong'))
        self.qs = qs[:n]; self.i = 0; self.ok = 0; self.answered = 0
        self._show()

    def _show(self):
        from ..core import qbank as QB
        self._score()
        if not self.qs:
            self.ql.setText('-'); self.meta.setText('')
            for r in self.opts: r.setVisible(False)
            return
        q = self.qs[self.i]
        self.ql.setText(f'{self.i + 1}/{len(self.qs)} · {q["q"]}')
        m = []
        if q.get('topic'): m.append(QB.topic_name(q['topic'], lang()))
        if q.get('level'): m.append(QB.level_name(q['level'], lang()))
        if q.get('src'): m.append('⌁ ' + q['src'])
        self.meta.setText('  ·  '.join(m) if m else '')
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
        if q.get('bank_id'):  # soru başına doğru/toplam (yanlışlarımı tekrar et)
            st = dict(self.win.settings.get('qbank_stats', {}) or {}); a_ = st.get(q['bank_id'], [0, 0])
            st[q['bank_id']] = [a_[0] + int(good), a_[1] + 1]; self.win.settings['qbank_stats'] = st
            try: self.win.settings.save()
            except Exception: pass
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
