"""v1.1.14 Log Gezgini: Mission Planner 'Review a Log' penceresinin karşılığı + programın analizi ve öğretici katmanı.

Sağda tüm mesajlar (ATT, IMU[0]/[1], XKF1 çekirdekleri, BAT[n], ESC[n]…) ve alt alanları onay kutulu ağaçta; RCOU/RCIN kanalları görev
adıyla. Sol/sağ eksen, Mod/Hatalar/MSG/Olaylar katmanları, programın bulduğu sorunlu bölgeler (kırmızı, tıklayınca açıklama), parametre
eşik çizgileri, kırım anına ±30 sn, veri tablosu, harita, parametreler, hazır görünümler, 'Uzman ne bakardı?' ve alıştırma kipi."""
from __future__ import annotations
import html
import numpy as np
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QTreeWidget, QTreeWidgetItem, QSplitter,
                               QTabWidget, QTextBrowser, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox,
                               QListWidget, QProgressBar, QSizePolicy)
from .i18n import lang
from .common import label, button, run_bg
from .pages_a import Page
from ..core import viz

E = html.escape

TX = {
    'load': ('📂 Log yükle', '📂 Load a log', '📂 تحميل سجل'),
    'preset': ('Hazır görünüm:', 'Preset:', 'عرض جاهز:'),
    'preset_pick': ('— seçin —', '— choose —', '— اختر —'),
    'expert': ('🎓 Uzman ne bakardı?', '🎓 What would an expert check?', '🎓 ماذا سيفحص الخبير؟'),
    'crash': ('💥 Kırım anına git (±30 sn)', '💥 Go to crash (±30 s)', '💥 انتقل إلى لحظة الحادث (±30 ث)'),
    'all': ('↔ Tümü', '↔ All', '↔ الكل'),
    'o_modes': ('Mod', 'Mode', 'الوضع'), 'o_err': ('Hatalar', 'Errors', 'الأخطاء'), 'o_msg': ('MSG', 'MSG', 'MSG'),
    'o_ev': ('Olaylar', 'Events', 'الأحداث'), 'o_prob': ('Sorunlu bölgeler', 'Problem regions', 'مناطق المشاكل'),
    'o_par': ('Parametre çizgileri', 'Parameter lines', 'خطوط المعاملات'), 'o_clock': ('Gerçek saat', 'Clock time', 'الساعة الفعلية'),
    'practice': ('🎯 Alıştırma (cevabı gizle)', '🎯 Practice (hide the answer)', '🎯 تدريب (إخفاء الإجابة)'),
    'search': ('Ara: ATT, Airspeed, kanatçık, titreşim…', 'Search: ATT, Airspeed, aileron, vibration…', 'ابحث: ATT، Airspeed، جنيح، اهتزاز…'),
    'left': ('◀ Sol eksen', '◀ Graph left', '◀ المحور الأيسر'), 'right': ('Sağ eksen ▶', 'Graph right ▶', 'المحور الأيمن ▶'),
    'clear': ('Grafiği temizle', 'Clear graph', 'مسح الرسم'),
    'col_f': ('Mesaj / alan', 'Message / field', 'الرسالة / الحقل'), 'col_u': ('Birim', 'Unit', 'الوحدة'), 'col_s': ('Eksen', 'Axis', 'المحور'),
    'side_L': ('Sol', 'Left', 'يسار'), 'side_R': ('Sağ', 'Right', 'يمين'),
    'reading': ('⏳ Diğer {n} mesaj türü okunuyor… %{p:.0f}', '⏳ Reading {n} more message types… {p:.0f}%', '⏳ جارٍ قراءة {n} نوع رسالة إضافي… {p:.0f}٪'),
    'read_ok': ('Logdaki {n} mesaj türünün tamamı ağaçta.', 'All {n} message types of the log are in the tree.', 'كل أنواع الرسائل الـ{n} في السجل موجودة في الشجرة.'),
    'pending': ('⏳ okunuyor…', '⏳ loading…', '⏳ جارٍ التحميل…'),
    't_info': ('Açıklama', 'Explanation', 'الشرح'), 't_table': ('Veri tablosu', 'Data table', 'جدول البيانات'),
    't_map': ('Harita', 'Map', 'الخريطة'), 't_params': ('Parametreler', 'Params', 'المعاملات'),
    't_expert': ('Uzman adımları', 'Expert steps', 'خطوات الخبير'), 't_practice': ('Alıştırma', 'Practice', 'تدريب'),
    'nolog': ('Önce bir log açın.', 'Open a log first.', 'افتح سجلاً أولاً.'),
    'nocrash': ('Bu logda kırım ya da sorun anı bulunmadı.', 'No crash or problem moment in this log.', 'لا توجد لحظة حادث أو مشكلة في هذا السجل.'),
    'help': ('Sağdaki ağaçtan alanları işaretleyin (çift tık: sol eksen). Bir alanı seçince anlamı, birimi, olağan aralığı ve ilgili parametreleri burada görünür. '
             'Kırmızı bölgeler programın sorun bulduğu yerlerdir; grafikte üzerine tıklayınca açıklaması açılır. Kesikli çizgiler parametre eşikleridir '
             '(ör. AIRSPEED_MIN).',
             'Tick fields in the tree on the right (double-click: left axis). Select a field to see its meaning, unit, normal range and related parameters here. '
             'Red regions are where the program found a problem; click them on the chart to open the explanation. Dashed lines are parameter limits '
             '(e.g. AIRSPEED_MIN).',
             'اختر الحقول من الشجرة على اليمين (نقر مزدوج: المحور الأيسر). عند تحديد حقل يظهر هنا معناه ووحدته ونطاقه الطبيعي والمعاملات المرتبطة. '
             'المناطق الحمراء هي حيث وجد البرنامج مشكلة؛ انقر عليها في الرسم لفتح الشرح. الخطوط المتقطعة حدود المعاملات (مثل AIRSPEED_MIN).'),
    'f_meaning': ('Anlamı', 'Meaning', 'المعنى'), 'f_unit': ('Birim', 'Unit', 'الوحدة'), 'f_normal': ('Olağan aralık', 'Normal range', 'النطاق الطبيعي'),
    'f_params': ('İlgili parametreler (bu logdaki değer)', 'Related parameters (value in this log)', 'المعاملات المرتبطة (القيمة في هذا السجل)'),
    'f_msg': ('Mesaj', 'Message', 'الرسالة'), 'f_mp': ('Mission Planner\'da', 'In Mission Planner', 'في Mission Planner'),
    'f_role': ('Görevi', 'Role', 'الوظيفة'),
    'tb_hint': ('Görünen aralıktaki örnekler (yakınlaştırınca güncellenir, en çok 1500 satır).', 'Samples in the visible range (updates on zoom, max 1500 rows).',
                'العينات في المجال الظاهر (تتحدث عند التكبير، 1500 صف كحد أقصى).'),
    'tb_time': ('Zaman', 'Time', 'الزمن'), 'tb_clock': ('Saat', 'Clock', 'الساعة'), 'tb_mode': ('Mod', 'Mode', 'الوضع'),
    'map_none': ('Bu logda konum verisi yok.', 'No position data in this log.', 'لا توجد بيانات موقع في هذا السجل.'),
    'map_hint': ('Kalın çizgi: grafikte görünen aralık · nokta: imleç', 'Thick line: range visible on the chart · dot: cursor', 'الخط العريض: المجال الظاهر في الرسم · النقطة: المؤشر'),
    'p_search': ('Parametre ara… (çift tık: grafiğe çizgi)', 'Search parameters… (double-click: line on chart)', 'ابحث في المعاملات… (نقر مزدوج: خط على الرسم)'),
    'p_c': [('Parametre', 'Parameter', 'المعامل'), ('Değer', 'Value', 'القيمة'), ('Açıklama', 'Description', 'الوصف')],
    'x_prev': ('◀ Önceki', '◀ Previous', '◀ السابق'), 'x_next': ('Sonraki ▶', 'Next ▶', 'التالي ▶'),
    'x_step': ('Adım {i}/{n}', 'Step {i}/{n}', 'الخطوة {i}/{n}'),
    'x_locked': ('Alıştırma kipinde önce tahmininizi yapın; uzman adımları cevabı ele verir.', 'In practice mode make your guess first; the expert steps give the answer away.',
                 'في وضع التدريب خمّن أولاً؛ خطوات الخبير تكشف الإجابة.'),
    'pr_intro': ('Kırmızı bölgeler ve kırım çizgisi gizlendi. Ağaçtan istediğiniz alanları açıp inceleyin, sonra kök nedeni tahmin edin.',
                 'Red regions and the crash line are hidden. Open any fields from the tree, then guess the root cause.',
                 'أُخفيت المناطق الحمراء وخط الحادث. افتح ما تشاء من الحقول ثم خمّن السبب الجذري.'),
    'pr_guess': ('Tahminim:', 'My guess:', 'تخميني:'), 'pr_check': ('✔ Tahminimi kontrol et', '✔ Check my guess', '✔ تحقق من تخميني'),
    'pr_reveal': ('Cevap açıldı; sorunlu bölgeler yeniden gösteriliyor.', 'Answer revealed; problem regions are shown again.', 'كُشفت الإجابة؛ تظهر مناطق المشاكل مجدداً.'),
    'pr_normal': ('Normal uçuş: kök neden yok', 'Normal flight: no root cause', 'طيران طبيعي: لا يوجد سبب جذري'),
    'probs': ('Programın işaretlediği bölgeler', 'Regions marked by the program', 'المناطق التي حددها البرنامج'),
}


def tx(k):
    return viz.tx(TX[k], lang())


class _Tree(QTreeWidget):
    """İpucu (alan anlamı, birim, olağan aralık, parametre) yalnız fare üzerine gelince hesaplanır."""
    tipper = None

    def viewportEvent(self, e):
        if e.type() == QEvent.ToolTip and self.tipper is not None:
            it = self.itemAt(e.pos())
            if it is not None and not it.toolTip(0):
                try:
                    tip = self.tipper(it)
                    if tip:
                        for c in range(3): it.setToolTip(c, tip)
                except Exception:
                    pass
        return super().viewportEvent(e)


class LogBrowserPage(Page):
    def __init__(self, win):
        super().__init__(win)
        from .chartview import ChartView
        v = QVBoxLayout(self); v.setContentsMargins(12, 8, 12, 8); v.setSpacing(4)
        # ------------------------------------------------ üst çubuk
        r = QHBoxLayout()
        r.addWidget(button(tx('load'), win.pick_log, primary=True))
        r.addWidget(QLabel(tx('preset')))
        self.preset = QComboBox(); self.preset.setMinimumWidth(230); self.preset.activated.connect(self._preset_chosen); r.addWidget(self.preset)
        self.b_exp = button(tx('expert'), self.start_expert); r.addWidget(self.b_exp)
        self.b_crash = button(tx('crash'), self.goto_crash); r.addWidget(self.b_crash)
        r.addWidget(button(tx('all'), self.zoom_all))
        r.addStretch(1)
        self.c_prac = QCheckBox(tx('practice')); self.c_prac.toggled.connect(self._practice_toggled); r.addWidget(self.c_prac)
        v.addLayout(r)
        r = QHBoxLayout()
        self.opt = {}
        for k, key in (('modes', 'o_modes'), ('errors', 'o_err'), ('msg', 'o_msg'), ('events', 'o_ev'), ('problems', 'o_prob'), ('params', 'o_par'), ('clock', 'o_clock')):
            c = QCheckBox(tx(key)); c.setChecked(k != 'clock'); c.toggled.connect(lambda *_: self.redraw()); r.addWidget(c); self.opt[k] = c
        r.addStretch(1)
        self.st = label('', 'muted'); r.addWidget(self.st)
        v.addLayout(r)
        # ------------------------------------------------ gövde
        sp = QSplitter(Qt.Horizontal)
        lsp = QSplitter(Qt.Vertical)
        self.view = ChartView(); self.view.clicked.connect(self._clicked); lsp.addWidget(self.view)
        self.tabs = QTabWidget()
        self.info = QTextBrowser(); self.info.setOpenLinks(False); self.info.anchorClicked.connect(self._anchor); self.tabs.addTab(self.info, tx('t_info'))
        tw = QWidget(); tv = QVBoxLayout(tw); tv.setContentsMargins(0, 0, 0, 0)
        tv.addWidget(label(tx('tb_hint'), 'muted'))
        self.table = QTableWidget(0, 0); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.verticalHeader().setVisible(False)
        tv.addWidget(self.table, 1); self.tabs.addTab(tw, tx('t_table'))
        mw = QWidget(); self.map_l = QVBoxLayout(mw); self.map_l.setContentsMargins(0, 0, 0, 0)
        self.map_l.addWidget(label(tx('map_hint'), 'muted')); self.map_canvas = None; self.tabs.addTab(mw, tx('t_map'))
        pw = QWidget(); pv = QVBoxLayout(pw); pv.setContentsMargins(0, 0, 0, 0)
        self.psearch = QLineEdit(); self.psearch.setPlaceholderText(tx('p_search')); self.psearch.textChanged.connect(self._fill_params); pv.addWidget(self.psearch)
        self.ptab = QTableWidget(0, 3); self.ptab.setHorizontalHeaderLabels([viz.tx(x, lang()) for x in TX['p_c']])
        self.ptab.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch); self.ptab.verticalHeader().setVisible(False)
        self.ptab.setEditTriggers(QAbstractItemView.NoEditTriggers); self.ptab.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ptab.cellDoubleClicked.connect(self._param_line); pv.addWidget(self.ptab, 1); self.tabs.addTab(pw, tx('t_params'))
        xw = QWidget(); xv = QVBoxLayout(xw); xv.setContentsMargins(0, 0, 0, 0)
        xh = QHBoxLayout(); self.xsteps = QListWidget(); self.xsteps.setMaximumWidth(260); self.xsteps.currentRowChanged.connect(self._step)
        xh.addWidget(self.xsteps); self.xtext = QTextBrowser(); xh.addWidget(self.xtext, 1); xv.addLayout(xh, 1)
        xb = QHBoxLayout(); self.xlbl = label('', 'muted'); xb.addWidget(self.xlbl); xb.addStretch(1)
        xb.addWidget(button(tx('x_prev'), lambda: self._step_move(-1))); xb.addWidget(button(tx('x_next'), lambda: self._step_move(1), primary=True))
        xv.addLayout(xb); self.tabs.addTab(xw, tx('t_expert'))
        qw = QWidget(); qv = QVBoxLayout(qw); qv.setContentsMargins(0, 0, 0, 0)
        qv.addWidget(label(tx('pr_intro'), 'muted', wrap=True))
        qh = QHBoxLayout(); qh.addWidget(QLabel(tx('pr_guess'))); self.guess = QComboBox(); qh.addWidget(self.guess, 1)
        qh.addWidget(button(tx('pr_check'), self.check_guess, primary=True)); qv.addLayout(qh)
        self.gres = QTextBrowser(); qv.addWidget(self.gres, 1); self.tabs.addTab(qw, tx('t_practice'))
        self.tabs.currentChanged.connect(lambda *_: self._tab_changed())
        lsp.addWidget(self.tabs); lsp.setSizes([620, 260])
        sp.addWidget(lsp)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0); rv.setSpacing(4)
        self.q = QLineEdit(); self.q.setPlaceholderText(tx('search')); self.q.textChanged.connect(self._filter); rv.addWidget(self.q)
        self.tree = _Tree(); self.tree.setColumnCount(3); self.tree.setHeaderLabels([tx('col_f'), tx('col_u'), tx('col_s')])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch); self.tree.header().setStretchLastSection(False)
        self.tree.setColumnWidth(1, 70); self.tree.setColumnWidth(2, 58)
        self.tree.tipper = self._tip
        self.tree.itemChanged.connect(self._item_changed); self.tree.itemDoubleClicked.connect(self._dbl)
        self.tree.currentItemChanged.connect(lambda cur, _p: self._show_field(cur))
        self.tree.itemExpanded.connect(self._expanded)
        rv.addWidget(self.tree, 1)
        self.prog = QProgressBar(); self.prog.setMaximumHeight(8); self.prog.setTextVisible(False); self.prog.hide(); rv.addWidget(self.prog)
        self.rd = label('', 'muted', wrap=True); rv.addWidget(self.rd)
        rb = QHBoxLayout(); rb.addWidget(button(tx('left'), lambda: self._side_cur('L'))); rb.addWidget(button(tx('right'), lambda: self._side_cur('R')))
        rv.addLayout(rb)
        rv.addWidget(button(tx('clear'), self.clear_graph))
        sp.addWidget(right); sp.setStretchFactor(0, 4); sp.setStretchFactor(1, 1); sp.setSizes([1100, 380])
        v.addWidget(sp, 1)
        # ------------------------------------------------ durum
        self.A = None; self.sel = []; self.items = {}; self.info_d = {}; self.extra_params = []
        self._dirty = False; self._busy = False; self._reading = False; self._keep_x = None; self._steps = []; self._revealed = False
        self._timer = QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(260); self._timer.timeout.connect(self._draw_now)
        self._xt = QTimer(self); self._xt.setSingleShot(True); self._xt.setInterval(220); self._xt.timeout.connect(self._xlim_changed)
        self._blk = False
        for b in (self.info, self.xtext, self.gres): b.document().setDefaultStyleSheet('a{color:#60A5FA}')
        self.info.setHtml(f'<p>{E(tx("help"))}</p>')

    # ================================================================ log
    def on_analysis(self, A):
        self.A = A; self.sel = []; self.extra_params = []; self._steps = []; self._revealed = False; self._keep_x = None
        self._dirty = True
        if self.isVisible(): self.on_show()

    def on_show(self):
        if not self._dirty or self.A is None: return
        self._dirty = False
        from ..core import logbrowse as LB
        A = self.A
        self._fill_presets(); self._fill_guess(); self._fill_params(); self.xsteps.clear(); self.xtext.clear(); self.gres.clear()
        self.sel = LB.preset_sel(A, LB.PRESETS[0])
        self._build_tree()
        self.redraw()
        miss = LB.missing(A.L)
        if miss and A.L.kind == 'bin' and not getattr(A.L, '_browse_done', False):
            self._read_rest(len(miss))
        else:
            self.rd.setText(tx('read_ok').format(n=self.tree.topLevelItemCount()))

    def _read_rest(self, n):
        from ..core import logbrowse as LB
        A = self.A; self._reading = True
        self.prog.show(); self.prog.setRange(0, 100); self.rd.setText(tx('reading').format(n=n, p=0))
        holder = {}

        def job():
            def pr(f):
                holder['p'] = f
            return LB.ensure_all(A.L, progress=pr)

        tick = QTimer(self); tick.setInterval(250)
        tick.timeout.connect(lambda: (self.prog.setValue(int(holder.get('p', 0) * 100)),
                                      self.rd.setText(tx('reading').format(n=n, p=holder.get('p', 0) * 100))))
        tick.start()

        def done(_r):
            tick.stop(); self.prog.hide(); self._reading = False
            if A is not self.A: return
            self._build_tree()
            if self.sel:
                self.set_selection(self.sel); self.redraw()
            self.rd.setText(tx('read_ok').format(n=self.tree.topLevelItemCount()))

        def fail(e):
            tick.stop(); self.prog.hide(); self._reading = False; self.rd.setText(str(e))
        run_bg(job, on_done=done, on_fail=fail)

    # ================================================================ ağaç
    def _build_tree(self):
        from ..core import logbrowse as LB
        A = self.A; lg = lang()
        self._blk = True
        exp = {self.tree.topLevelItem(i).data(0, Qt.UserRole + 1) for i in range(self.tree.topLevelItemCount()) if self.tree.topLevelItem(i).isExpanded()}
        self.tree.clear(); self.items = {}
        chosen = {s['key']: s['side'] for s in self.sel}
        bold = self.tree.font(); bold.setBold(True)
        for nd in LB.tree(A, lg):
            top = QTreeWidgetItem([f"{nd['base']}   ({nd['count']})" if nd['count'] else nd['base'], '', ''])
            top.setData(0, Qt.UserRole + 1, nd['base']); top.setFont(0, bold)
            top.setData(0, Qt.UserRole + 2, (nd['base'] + ' ' + (nd['desc'] or '')).lower())
            self.tree.addTopLevelItem(top)
            if not nd['loaded']:
                ph = QTreeWidgetItem([tx('pending'), '', '']); ph.setForeground(0, QBrush(QColor('#94A3B8'))); top.addChild(ph)
                continue
            multi = len(nd['insts']) > 1 or (nd['insts'] and nd['insts'][0]['key'] != nd['base'])
            for ins in nd['insts']:
                par = top
                if multi:
                    par = QTreeWidgetItem([ins['label'], '', '']); par.setData(0, Qt.UserRole + 1, ins['key']); top.addChild(par)
                    par.setData(0, Qt.UserRole + 2, ins['label'].lower())
                for f in ins['fields']:
                    lab = f['label'] if f['label'] == f['name'] else f['label']
                    it = QTreeWidgetItem([lab, f['unit'], ''])
                    it.setData(0, Qt.UserRole, f['key'])
                    it.setData(0, Qt.UserRole + 2, (f['key'] + ' ' + f['label']).lower())
                    it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                    side = chosen.get(f['key'])
                    it.setCheckState(0, Qt.Checked if side else Qt.Unchecked)
                    if side: it.setText(2, tx('side_' + side))
                    par.addChild(it); self.items[f['key']] = it
                if multi and any(f['key'] in chosen for f in ins['fields']): par.setExpanded(True)
            if nd['base'] in exp or any(k.split('.')[0].split('[')[0] == nd['base'] for k in chosen): top.setExpanded(True)
        self._blk = False
        self._filter()

    def _expanded(self, it):
        pass

    def _tip(self, it):
        from ..core import logbrowse as LB, sources
        key = it.data(0, Qt.UserRole)
        if key: return LB.tooltip(self.A, key, lang())
        b = it.data(0, Qt.UserRole + 1)
        if b:
            d = sources.msg_meaning(str(b).split('[')[0], lang())
            return f'<b>{E(str(b))}</b><br>{E(d)}' if d else ''
        return ''

    def _filter(self, *_):
        q = self.q.text().strip().lower()
        try:
            from ..core.msgsearch import norm as fold
        except Exception:
            fold = lambda s: s  # noqa: E731
        qf = fold(q) if q else ''

        def match(it):
            s = it.data(0, Qt.UserRole + 2) or ''
            if not qf: return True
            if qf in fold(s): return True
            key = it.data(0, Qt.UserRole)
            if key:
                from ..core import sources
                m = sources.field_meaning(key, lang()).lower()
                return qf in fold(m)
            return False

        def walk(it):
            n = it.childCount()
            if n == 0:
                ok = match(it); it.setHidden(not ok); return ok
            own = match(it)
            any_c = False
            for i in range(n):
                c = it.child(i)
                if own and qf:
                    c.setHidden(False)
                    for j in range(c.childCount()): c.child(j).setHidden(False)
                    any_c = True
                else:
                    any_c = walk(c) or any_c
            it.setHidden(not (own or any_c))
            if qf and any_c and not own: it.setExpanded(True)
            return own or any_c
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))

    def _item_changed(self, it, col):
        if self._blk or col != 0: return
        key = it.data(0, Qt.UserRole)
        if not key: return
        on = it.checkState(0) == Qt.Checked
        cur = next((s for s in self.sel if s['key'] == key), None)
        if on and cur is None:
            self.sel.append({'key': key, 'side': 'L'}); self._set_side_text(key, 'L')
        elif not on and cur is not None:
            self.sel.remove(cur); self._set_side_text(key, None)
        self.redraw()

    def _set_side_text(self, key, side):
        it = self.items.get(key)
        if it is None: return
        self._blk = True
        it.setText(2, tx('side_' + side) if side else '')
        it.setCheckState(0, Qt.Checked if side else Qt.Unchecked)
        self._blk = False

    def _dbl(self, it, _col):
        key = it.data(0, Qt.UserRole)
        if not key: return
        cur = next((s for s in self.sel if s['key'] == key), None)
        if cur is None: self.sel.append({'key': key, 'side': 'L'}); self._set_side_text(key, 'L')
        else: self.sel.remove(cur); self._set_side_text(key, None)
        self.redraw()

    def _side_cur(self, side):
        it = self.tree.currentItem()
        key = it.data(0, Qt.UserRole) if it is not None else None
        if not key: return
        cur = next((s for s in self.sel if s['key'] == key), None)
        if cur is None: self.sel.append({'key': key, 'side': side})
        else: cur['side'] = side
        self._set_side_text(key, side); self.redraw()

    def clear_graph(self):
        """Seçili alanları VE bütün arka planı (mod renkleri, hata/olay çizgileri, MSG yazıları, sorunlu bölgeler,
        parametre çizgileri) temizler; arka plan katmanları üstteki kutucuklarla tek tek geri açılır."""
        for s in list(self.sel): self._set_side_text(s['key'], None)
        self.sel = []; self.extra_params = []
        for k, c in self.opt.items():
            if k == 'clock': continue
            c.blockSignals(True); c.setChecked(False); c.blockSignals(False)
        self.redraw()

    def show_keys(self, keys):
        """Dışarıdan (ör. Motor Yönleri Bankası) verilen alanları sol eksende çizer; henüz okunmamış türler okununca yeniden çizilir."""
        if self.A is None: return 0
        L = self.A.L; seen = set(L.types_seen or {})
        ok = [k for k in keys if k.split('.', 1)[0] in L.msgs or k.split('[', 1)[0].split('.', 1)[0] in seen]
        if not ok: return 0
        self.on_show()
        self.set_selection([{'key': k, 'side': 'L'} for k in ok])
        self._keep_x = None; self.redraw(keep_x=False)
        return len(ok)

    def set_selection(self, sel):
        for s in list(self.sel): self._set_side_text(s['key'], None)
        self.sel = [dict(s) for s in sel]
        for s in self.sel:
            self._set_side_text(s['key'], s['side'])
            it = self.items.get(s['key'])
            if it is not None:
                p = it.parent()
                while p is not None: p.setExpanded(True); p = p.parent()

    # ================================================================ açıklama
    def _show_field(self, it):
        if it is None or self.A is None: return
        key = it.data(0, Qt.UserRole)
        if not key: return
        from ..core import logbrowse as LB, analysis
        d = LB.field_info(self.A, key, lang())
        h = [f'<h3>{E(key)}' + (f" <small>[{E(d['unit'])}]</small>" if d['unit'] else '') + '</h3>']
        if d['role']: h.append(f"<p><b>{E(tx('f_role'))}:</b> {E(d['role'])}</p>")
        if d['meaning']: h.append(f"<p><b>{E(tx('f_meaning'))}:</b> {E(d['meaning'])}</p>")
        if d['normal']: h.append(f"<p><b>✅ {E(tx('f_normal'))}:</b> {E(d['normal'])}</p>")
        r = LB.series(self.A.L, key)
        if r is not None:
            y = r[1][np.isfinite(r[1])]
            if len(y):
                h.append(f'<p>min {y.min():.4g} · max {y.max():.4g} · ' + ('ort' if lang() == 'tr' else ('mean' if lang() == 'en' else 'متوسط')) +
                         f' {y.mean():.4g} · n={len(y)}</p>')
        if d['params']:
            h.append(f"<p><b>⚙ {E(tx('f_params'))}:</b></p><ul>" + ''.join(f'<li><b>{E(n)}</b> = {v:g}' + (f' — {E(t)}' if t else '') + '</li>'
                                                                         for n, v, t in d['params']) + '</ul>')
        if d['msg']: h.append(f"<p><b>{E(tx('f_msg'))}:</b> {E(d['msg'])}</p>")
        if d['mp']: h.append(f"<p><i>{E(tx('f_mp'))}: {E(d['mp'])}</i></p>")
        self.info.setHtml(''.join(h))

    def _problems_html(self):
        ps = self.info_d.get('problems') or []
        if not ps: return ''
        from ..core.analysis import fmt_t
        return f"<h3>{E(tx('probs'))}</h3><ul>" + ''.join(f"<li><a href='p:{p['id']}'>⚠{p['id']}</a> {fmt_t(p['t0'])} · {E(p['title'])}</li>" for p in ps) + '</ul>'

    def _anchor(self, u):
        s = u.toString()
        if s.startswith('p:'):
            p = next((x for x in self.info_d.get('problems') or [] if str(x['id']) == s[2:]), None)
            if p is not None:
                self.info.setHtml(p['html'] + self._problems_html())
                self.view.zoom_to(p['t0'] - 15, p['t1'] + 15); self.view.set_cursor((p['t0'] + p['t1']) / 2)
                self._keep_x = (p['t0'] - 15, p['t1'] + 15)
        elif s.startswith('go:'):
            self.win.goto(s[3:])

    # ================================================================ çizim
    def _opts(self):
        o = {k: c.isChecked() for k, c in self.opt.items()}
        o['quiz'] = self.c_prac.isChecked() and not self._revealed
        return o

    def redraw(self, keep_x=True):
        if self.A is None: return
        if keep_x and self.view.taxes:
            try:
                x0, x1 = self.view.taxes[0].get_xlim()
                full = (0, max(1.0, float(self.A.L.duration or 1)))
                self._keep_x = None if (abs(x0 - full[0]) < 1e-6 and abs(x1 - full[1]) < 1e-6) else (x0, x1)
            except Exception: pass
        self._timer.start()

    def _draw_now(self):
        if self.A is None: return
        if self._busy:
            self._timer.start(); return
        from ..core import charts, logbrowse as LB
        A = self.A; sel = [dict(s) for s in self.sel]; o = self._opts(); lg = lang(); keep = self._keep_x
        ex = list(self.extra_params)
        self._busy = True

        def job():
            charts.want_fig(True)
            try:
                fig, info = LB.build(A, sel, o, lg)
                if ex and fig.axes:
                    from ..core import charts2 as C2
                    for n in ex:
                        if n in A.L.params: C2._plim(fig.axes[0], float(A.L.params[n]), f'{n}={A.L.params[n]:g}', '#0F766E', ls='-.', lw=0.8, x=0.3)
                return fig, info
            finally: charts.want_fig(False)

        def done(r):
            self._busy = False
            if A is not self.A: return
            fig, info = r; self.info_d = info
            self.view.set_figure(fig, A)
            if keep:
                for ax in self.view.taxes: ax.set_xlim(*keep)
                self.view.canvas.draw_idle()
            for ax in self.view.taxes[:1]:
                ax.callbacks.connect('xlim_changed', lambda a: self._xt.start())
            self._xlim_changed()

        def fail(e):
            self._busy = False; self.view.set_message(str(e))
        run_bg(job, on_done=done, on_fail=fail)

    def _vis(self):
        if self.view.taxes:
            try: return self.view.taxes[0].get_xlim()
            except Exception: pass
        return None, None

    def _xlim_changed(self):
        i = self.tabs.currentIndex()
        if i == 1: self._fill_table()
        elif i == 2: self._draw_map()

    def _tab_changed(self):
        self._xlim_changed()

    def zoom_all(self):
        self._keep_x = None
        if self.view.taxes and self.A is not None:
            for ax in self.view.taxes: ax.set_xlim(0, max(1.0, float(self.A.L.duration or 1)))
            self.view.canvas.draw_idle()

    def goto_crash(self):
        from ..core import logbrowse as LB
        if self.A is None: return self.st.setText(tx('nolog'))
        ct = LB.crash_t(self.A)
        if ct is None:
            self.st.setText(tx('nocrash')); return
        self.view.zoom_to(ct - 30, ct + 30); self.view.set_cursor(ct)
        self._keep_x = (ct - 30, ct + 30)

    def _clicked(self, t):
        from ..core import logbrowse as LB
        p = LB.problem_at(self.info_d, t)
        if p is not None:
            self.info.setHtml(p['html'] + self._problems_html()); self.tabs.setCurrentIndex(0)
        if self.tabs.currentIndex() == 2: self._draw_map(cursor=t)
        try: self.win.pages['map'].goto_time(t, switch=False)
        except Exception: pass
        try: self.win.pages['video'].goto_log_time(t)
        except Exception: pass

    # ================================================================ tablo / harita / parametreler
    def _fill_table(self):
        from ..core import logbrowse as LB
        if self.A is None: return
        x0, x1 = self._vis()
        hd, rows = LB.table(self.A, [s['key'] for s in self.sel], x0, x1)
        if not hd:
            self.table.setRowCount(0); self.table.setColumnCount(0); return
        names = [tx('tb_time'), tx('tb_clock'), tx('tb_mode')] + hd[3:]
        self.table.setColumnCount(len(names)); self.table.setHorizontalHeaderLabels(names); self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(v if isinstance(v, str) else (f'{v:.5g}' if np.isfinite(v) else '')))
        self.table.resizeColumnsToContents()

    def _draw_map(self, cursor=None):
        A = self.A
        if A is None: return
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        if self.map_canvas is not None:
            self.map_l.removeWidget(self.map_canvas); self.map_canvas.setParent(None); self.map_canvas.deleteLater(); self.map_canvas = None
        tr = A.track
        fig = Figure(figsize=(6, 3), dpi=100); fig.patch.set_facecolor('white'); ax = fig.add_subplot(111)
        if tr is None or not len(tr.get('t', [])):
            ax.text(0.5, 0.5, tx('map_none'), ha='center', va='center', transform=ax.transAxes); ax.axis('off')
        else:
            t = np.asarray(tr['t']); la = np.asarray(tr['lat']); lo = np.asarray(tr['lon'])
            k = np.cos(np.radians(np.nanmean(la)))
            for s in viz.segments(A, lang()):
                m = (t >= s['t0']) & (t <= s['t1'])
                if m.any(): ax.plot(lo[m] * k, la[m], color=s['col'], lw=1.0, alpha=0.6)
            x0, x1 = self._vis()
            if x0 is not None:
                m = (t >= x0) & (t <= x1)
                if m.any(): ax.plot(lo[m] * k, la[m], color='#1D4ED8', lw=2.6)
            c = cursor if cursor is not None else self.view.cursor_t
            if c is not None:
                i = int(np.clip(np.searchsorted(t, c), 0, len(t) - 1)); ax.plot([lo[i] * k], [la[i]], 'o', color='#F59E0B', ms=8, mec='black')
            from ..core import logbrowse as LB
            ct = LB.crash_t(A) if not self._opts()['quiz'] else None
            if ct is not None:
                i = int(np.clip(np.searchsorted(t, ct), 0, len(t) - 1)); ax.plot([lo[i] * k], [la[i]], 'X', color='#DC2626', ms=10)
            ax.set_aspect('equal', adjustable='datalim'); ax.set_xticks([]); ax.set_yticks([])
        fig.tight_layout()
        self.map_canvas = FigureCanvasQTAgg(fig); self.map_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.map_l.addWidget(self.map_canvas, 1)

    def _fill_params(self, *_):
        from ..core import sources
        self.ptab.setRowCount(0)
        if self.A is None: return
        q = self.psearch.text().strip().upper(); P = self.A.L.params
        ks = [k for k in sorted(P) if not q or q in k][:800]
        self.ptab.setRowCount(len(ks))
        for i, k in enumerate(ks):
            self.ptab.setItem(i, 0, QTableWidgetItem(k)); self.ptab.setItem(i, 1, QTableWidgetItem(f'{P[k]:g}'))
            self.ptab.setItem(i, 2, QTableWidgetItem(sources.param_text(k, self.A.vehicle, lang())[0] if i < 300 or q else ''))
        self.ptab.resizeColumnToContents(0)

    def _param_line(self, r, _c):
        it = self.ptab.item(r, 0)
        if it is None: return
        n = it.text()
        if n in self.extra_params: self.extra_params.remove(n)
        else: self.extra_params.append(n)
        self.redraw()

    # ================================================================ hazır görünümler
    def _fill_presets(self):
        from ..core import logbrowse as LB
        self.preset.clear(); self.preset.addItem(tx('preset_pick'), None)
        for p in LB.presets(self.A):
            if LB.preset_sel(self.A, p): self.preset.addItem(viz.tx(p['name'], lang()), p['id'])

    def apply_preset(self, pid, zoom=None):
        from ..core import logbrowse as LB
        p = next((x for x in LB.PRESETS if x['id'] == pid), None)
        if p is None or self.A is None: return
        self.set_selection(LB.preset_sel(self.A, p))
        i = self.preset.findData(pid)
        if i >= 0: self.preset.setCurrentIndex(i)
        self.info.setHtml(f"<h3>{E(viz.tx(p['name'], lang()))}</h3><p>{E(viz.tx(p['look'], lang()))}</p>" + self._problems_html())
        ct = LB.crash_t(self.A) if zoom == 'crash' else None
        self._keep_x = (ct - 30, ct + 30) if ct is not None else None
        self.redraw(keep_x=False)

    def _preset_chosen(self, i):
        pid = self.preset.itemData(i)
        if pid: self.apply_preset(pid); self.tabs.setCurrentIndex(0)

    # ================================================================ uzman adımları
    def start_expert(self):
        from ..core import logbrowse as LB
        if self.A is None: return self.st.setText(tx('nolog'))
        self.tabs.setCurrentIndex(4)
        if self.c_prac.isChecked() and not self._revealed:
            self.xsteps.clear(); self.xtext.setPlainText(tx('x_locked')); return
        self._steps = LB.expert_steps(self.A, lang())
        self.xsteps.blockSignals(True); self.xsteps.clear()
        for i, s in enumerate(self._steps): self.xsteps.addItem(f'{i + 1}. {s["title"]}')
        self.xsteps.blockSignals(False)
        self.xsteps.setCurrentRow(0)

    def _step(self, i):
        if not (0 <= i < len(self._steps)): return
        s = self._steps[i]
        self.xlbl.setText(tx('x_step').format(i=i + 1, n=len(self._steps)))
        self.xtext.setHtml(f"<h3>{E(s['title'])}</h3>" + ''.join(f'<p>{E(p)}</p>' for p in s['text'].split('\n') if p.strip()))
        cur = self.tabs.currentIndex()
        self.apply_preset(s['preset'], s['zoom'])
        self.tabs.setCurrentIndex(cur)

    def _step_move(self, d):
        if not self._steps: return self.start_expert()
        self.xsteps.setCurrentRow(max(0, min(len(self._steps) - 1, self.xsteps.currentRow() + d)))

    # ================================================================ alıştırma
    def _fill_guess(self):
        from ..core import logbrowse as LB
        self.guess.clear()
        for c in LB.practice_causes(self.A):
            self.guess.addItem(LB._cause_name(c, lang()), c)

    def _practice_toggled(self, on):
        self._revealed = False
        if on: self.tabs.setCurrentIndex(5); self.gres.clear()
        self.redraw()

    def check_guess(self):
        from ..core import logbrowse as LB
        if self.A is None: return
        r = LB.check_guess(self.A, self.guess.currentData(), lang())
        self.gres.setHtml(r['html'] + f"<p><i>{E(tx('pr_reveal'))}</i></p>")
        self._revealed = True
        self.redraw()
