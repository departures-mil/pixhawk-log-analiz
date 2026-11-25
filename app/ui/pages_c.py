"""v1.0.2 sayfaları: Filo takibi, Pilot kartları, Sınav ve sertifika."""
from __future__ import annotations
import html, json, os, time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QSplitter, QTextBrowser, QComboBox, QLineEdit, QDialog, QFormLayout, QDoubleSpinBox, QSpinBox,
                               QPlainTextEdit, QFileDialog, QInputDialog, QMessageBox, QRadioButton, QButtonGroup, QListWidget,
                               QListWidgetItem, QTabWidget, QDateEdit, QProgressBar, QScrollArea)
from .i18n import t, lang
from .common import label, button, run_bg, error, info, open_path, card, ImageView, VERDICT_COL
from .pages_a import Page
from ..core import fleet, texts, profiles
from ..core.analysis import fmt_t

E = html.escape


def _tbl(cols, stretch=1):
    tb = QTableWidget(0, len(cols)); tb.setHorizontalHeaderLabels(cols)
    tb.verticalHeader().setVisible(False); tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tb.setSelectionBehavior(QAbstractItemView.SelectRows); tb.setSelectionMode(QAbstractItemView.SingleSelection)
    tb.setAlternatingRowColors(True); tb.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)
    return tb


def _fill(tb, rows, colors=None):
    tb.setRowCount(len(rows))
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            it = QTableWidgetItem(str(v))
            if colors and colors[i] and colors[i][j]: it.setForeground(QColor(colors[i][j]))
            tb.setItem(i, j, it)
    tb.resizeColumnsToContents()


# ------------------------------------------------------------------ Filo
class FleetPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        top.addWidget(label(t('fl_title'), 'h1')); top.addStretch(1)
        top.addWidget(button('➕ ' + t('fl_add'), self.add_ac, primary=True))
        top.addWidget(button('✏ ' + t('fl_edit'), self.edit_ac))
        top.addWidget(button('🛠 ' + t('fl_maint'), self.add_maint))
        top.addWidget(button('🗑 ' + t('fl_del'), self.del_ac))
        v.addLayout(top)
        self.warn = QTextBrowser(); self.warn.setMaximumHeight(110); v.addWidget(self.warn)
        sp = QSplitter(Qt.Vertical)
        self.tb = _tbl([t('fl_name'), t('fl_serial'), t('fl_profile'), t('fl_flights'), t('fl_hours'), t('fl_next'), t('fl_motor'), t('fl_bat'), t('fl_last')], 0)
        self.tb.itemSelectionChanged.connect(self._sel); sp.addWidget(self.tb)
        bot = QWidget(); bh = QHBoxLayout(bot); bh.setContentsMargins(0, 0, 0, 0)
        self.det = QTextBrowser(); bh.addWidget(self.det, 1)
        mv = QVBoxLayout(); mv.addWidget(label(t('fl_maint_log'), 'h2'))
        self.mt = _tbl([t('col_date'), t('fl_kind'), t('fl_hours_at'), t('col_notes')], 3); mv.addWidget(self.mt, 1)
        bh.addLayout(mv, 1)
        sp.addWidget(bot); sp.setSizes([330, 330]); v.addWidget(sp, 1)
        self.acs = []

    def on_show(self):
        self.refresh()

    def on_analysis(self, A):
        self.refresh()

    def refresh(self):
        a = self.win.archive; lg = lang()
        self.acs = a.rec_list('aircraft')
        rows = []; cols = []
        for ac in self.acs:
            st = fleet.stats(a, ac['id'])
            nd = st['next_due_h']
            rows.append([ac.get('name', ''), ac.get('serial', ac['id']), profiles.name(ac.get('profile', 'plane'), lg), st['flights'], f"{st['hours']:.1f}",
                         f"{nd:.1f} h" if nd > 0 else t('fl_overdue', h=f'{-nd:.1f}'), f"{st['motor_hours']:.1f}/{st['motor_life']:.0f}",
                         f"{st['battery_cycles']}/{st['battery_limit']}", st['last_flight'][:16]])
            sev = max([w[1] for w in st['warnings']], default=0)
            cols.append([None] * 5 + ['#F87171' if nd <= 0 else ('#FBBF24' if sev else '#4ADE80'), None, None, None])
        _fill(self.tb, rows, cols)
        ws = fleet.all_warnings(a, lg)
        d = 'rtl' if lg == 'ar' else 'ltr'
        if ws:
            self.warn.setHtml(f'<div dir="{d}">' + ''.join(f'<p style="color:{"#F87171" if s >= 2 else "#FBBF24"}">⚠ <b>{E(ac.get("name", ""))}</b>: {E(x)}</p>' for ac, s, x in ws) + '</div>')
        else:
            self.warn.setHtml(f'<div dir="{d}"><p style="color:#4ADE80">✔ {E(t("fl_no_warn"))}</p><p style="color:#94A3B8">{E(t("fl_help"))}</p></div>')
        self._sel()

    def _cur(self):
        r = self.tb.currentRow()
        return self.acs[r] if 0 <= r < len(self.acs) else None

    def _sel(self):
        ac = self._cur(); a = self.win.archive; lg = lang()
        if not ac: self.det.setHtml(''); self.mt.setRowCount(0); return
        st = fleet.stats(a, ac['id'])
        d = 'rtl' if lg == 'ar' else 'ltr'
        h = [f'<div dir="{d}"><h3>{E(ac.get("name", ""))}</h3><p style="color:#94A3B8">{E(t("fl_serial"))}: {E(ac.get("serial", ""))} · {E(profiles.name(ac.get("profile", "plane"), lg))}</p>',
             f'<p>{E(t("fl_flights"))}: <b>{st["flights"]}</b> · {E(t("fl_hours"))}: <b>{st["hours"]:.2f}</b> · {E(t("fl_crashes"))}: <b>{st["crashes"]}</b> · '
             f'{E(t("fl_incidents"))}: <b>{st["incidents"]}</b> · {E(t("fl_avg"))}: <b>{(st["avg_score"] or 0):.0f}</b></p>',
             f'<p>{E(t("fl_since"))}: {st["since_inspection"]:.1f} h / {E(t("fl_interval"))} {float(ac.get("maint_interval_h") or 25):.0f} h</p>']
        for w in st['warnings']:
            h.append(f'<p style="color:{"#F87171" if w[1] >= 2 else "#FBBF24"}">⚠ {E(fleet.warn_text(w, lg))}</p>')
        fl = fleet.flights_of(a, ac['id'])[:15]
        if fl:
            h.append('<table width="100%" cellpadding="3">')
            for r in fl:
                h.append(f'<tr><td>{E((r.get("flight_date") or r.get("analyzed_at") or "")[:16])}</td><td>{E(r["name"])}</td>'
                         f'<td style="color:{VERDICT_COL.get(r["verdict"], "#94A3B8")}">{E(texts.T("v_" + (r["verdict"] or "normal"), lg))}</td><td>{r["overall"]}</td><td>{fmt_t(r["flight_time"] or 0)}</td></tr>')
            h.append('</table>')
        if ac.get('notes'): h.append(f'<p style="color:#94A3B8">{E(ac["notes"])}</p>')
        self.det.setHtml(''.join(h) + '</div>')
        _fill(self.mt, [[m.get('date', ''), fleet.kname(m.get('kind'), lg), f"{m.get('hours_at', 0):.1f}", (m.get('note') or '') + (f" ({m['by']})" if m.get('by') else '')] for m in reversed(st['maint'])])

    def _dialog(self, ac=None):
        ac = dict(ac or {**fleet.DEFAULTS, 'profile': 'plane'})
        dl = QDialog(self); dl.setWindowTitle(t('fl_add') if 'id' not in ac else t('fl_edit')); dl.setMinimumWidth(460); f = QFormLayout(dl)
        nm = QLineEdit(ac.get('name', '')); f.addRow(t('fl_name'), nm)
        sn = QLineEdit(ac.get('serial', '')); sn.setReadOnly('id' in ac); f.addRow(t('fl_serial'), sn)
        pr = QComboBox()
        for p in ('plane', 'vtol', 'copter', 'heli', 'rover'): pr.addItem(profiles.name(p, lang()), p)
        pr.setCurrentIndex(max(0, pr.findData(ac.get('profile', 'plane')))); f.addRow(t('fl_profile'), pr)
        iv = QDoubleSpinBox(); iv.setRange(1, 1000); iv.setValue(float(ac.get('maint_interval_h') or 25)); f.addRow(t('fl_interval') + ' (h)', iv)
        ml = QDoubleSpinBox(); ml.setRange(1, 5000); ml.setValue(float(ac.get('motor_life_h') or 200)); f.addRow(t('fl_motor_life') + ' (h)', ml)
        pl = QDoubleSpinBox(); pl.setRange(1, 2000); pl.setValue(float(ac.get('prop_life_h') or 50)); f.addRow(t('fl_prop_life') + ' (h)', pl)
        bl = QSpinBox(); bl.setRange(1, 5000); bl.setValue(int(ac.get('battery_cycles') or 300)); f.addRow(t('fl_bat_life'), bl)
        no = QPlainTextEdit(ac.get('notes', '')); no.setMaximumHeight(80); f.addRow(t('col_notes'), no)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted: return None
        sid = ac.get('id') or (sn.text().strip() or nm.text().strip().upper().replace(' ', '_')[:20] or time.strftime('AC%Y%m%d%H%M%S'))
        ac.update(id=sid, serial=sn.text().strip() or sid, name=nm.text().strip() or sid, profile=pr.currentData(), maint_interval_h=iv.value(),
                  motor_life_h=ml.value(), prop_life_h=pl.value(), battery_cycles=bl.value(), notes=no.toPlainText().strip())
        ac.setdefault('created', time.strftime('%Y-%m-%d'))
        self.win.archive.rec_put('aircraft', sid, ac); self.refresh()
        return sid

    def add_ac(self):
        self._dialog()

    def edit_ac(self):
        ac = self._cur()
        if ac: self._dialog(ac)

    def del_ac(self):
        ac = self._cur()
        if ac and QMessageBox.question(self, t('app'), t('fl_del_q', n=ac.get('name', ''))) == QMessageBox.Yes:
            self.win.archive.rec_del('aircraft', ac['id']); self.refresh()

    def add_maint(self):
        ac = self._cur()
        if not ac: return info(self, t('fl_pick'))
        dl = QDialog(self); dl.setWindowTitle(t('fl_maint')); dl.setMinimumWidth(420); f = QFormLayout(dl)
        kd = QComboBox()
        for k in fleet.MAINT_KINDS: kd.addItem(fleet.kname(k, lang()), k)
        f.addRow(t('fl_kind'), kd)
        from PySide6.QtCore import QDate
        de = QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); de.setDisplayFormat('yyyy-MM-dd'); f.addRow(t('col_date'), de)
        by = QLineEdit(); f.addRow(t('fl_by'), by)
        no = QPlainTextEdit(); no.setMaximumHeight(90); f.addRow(t('col_notes'), no)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted: return
        fleet.add_maint(self.win.archive, ac['id'], kd.currentData(), de.date().toString('yyyy-MM-dd'), no.toPlainText().strip(), by.text().strip())
        self.refresh()


# ------------------------------------------------------------------ Pilotlar
class PilotsPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout(); top.addWidget(label(t('pi_title'), 'h1')); top.addStretch(1)
        top.addWidget(button('➕ ' + t('pi_add'), self.add, primary=True))
        top.addWidget(button('🔗 ' + t('pi_assign'), self.assign))
        top.addWidget(button('📄 ' + t('pi_pdf'), self.pdf))
        top.addWidget(button('🗑 ' + t('fl_del'), self.delete))
        v.addLayout(top)
        v.addWidget(label(t('pi_help'), 'muted', wrap=True))
        sp = QSplitter(Qt.Horizontal)
        self.tb = _tbl([t('pi_name'), t('pi_license'), t('fl_flights'), t('fl_hours'), t('pi_score'), t('pi_trend')], 0)
        self.tb.itemSelectionChanged.connect(self._sel); sp.addWidget(self.tb)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        self.radar = ImageView(); rv.addWidget(self.radar, 2)
        self.det = QTextBrowser(); rv.addWidget(self.det, 2)
        sp.addWidget(right); sp.setSizes([520, 600]); v.addWidget(sp, 1)
        self.ps = []

    def on_show(self):
        self.refresh()

    def on_analysis(self, A):
        self.refresh()

    def refresh(self):
        a = self.win.archive
        self.ps = a.rec_list('pilot'); rows = []
        for p in self.ps:
            c = fleet.pilot_card(a, p['id'])
            rows.append([p['name'], p.get('license', ''), c['n'], f"{c['hours']:.1f}", f"{c['overall']:.0f}" if c['overall'] is not None else '-',
                         f"{c['trend']:+.1f}" if c['trend'] is not None else '-'])
        _fill(self.tb, rows)
        self._sel()

    def _cur(self):
        r = self.tb.currentRow()
        return self.ps[r] if 0 <= r < len(self.ps) else None

    def _sel(self):
        p = self._cur(); lg = lang()
        if not p: self.radar.set_png(None); self.det.setHtml(f'<p style="color:#94A3B8">{E(t("pi_help"))}</p>'); return
        c = fleet.pilot_card(self.win.archive, p['id'])
        self.radar.set_png(fleet.radar_png(c['avg'], lg, p['name']))
        d = 'rtl' if lg == 'ar' else 'ltr'
        h = [f'<div dir="{d}"><h3>{E(p["name"])}</h3>']
        if c['strongest']: h.append(f'<p>💪 {E(t("pi_strong"))}: <b>{E(fleet.sname(c["strongest"], lg))}</b> ({c["avg"][c["strongest"]]:.0f})</p>')
        if c['weakest']: h.append(f'<p>🎯 {E(t("pi_weak"))}: <b>{E(fleet.sname(c["weakest"], lg))}</b> ({c["avg"][c["weakest"]]:.0f})</p>')
        h.append('<table width="100%" cellpadding="3">')
        for f in reversed(c['flights'][-25:]):
            h.append(f'<tr><td>{E(f["date"][:16])}</td><td>{E(f["name"] or "")}</td><td style="color:{VERDICT_COL.get(f["verdict"], "#94A3B8")}">{E(texts.T("v_" + (f["verdict"] or "normal"), lg))}</td>'
                     f'<td><b>{f["overall"] if f["overall"] is not None else "-"}</b></td></tr>')
        h.append('</table></div>')
        self.det.setHtml(''.join(h))

    def add(self):
        n, ok = QInputDialog.getText(self, t('pi_add'), t('pi_name'))
        if ok and n.strip():
            lic, _ = QInputDialog.getText(self, t('pi_add'), t('pi_license'))
            fleet.add_pilot(self.win.archive, n.strip(), (lic or '').strip()); self.refresh()

    def delete(self):
        p = self._cur()
        if p and QMessageBox.question(self, t('app'), t('fl_del_q', n=p['name'])) == QMessageBox.Yes:
            self.win.archive.rec_del('pilot', p['id']); self.refresh()

    def assign(self):
        """Açık logu (veya arşivde seçilecek uçuşları) bu pilota bağla."""
        p = self._cur()
        if not p: return info(self, t('pi_pick'))
        rows = self.win.archive.list()
        dl = QDialog(self); dl.setWindowTitle(t('pi_assign')); dl.resize(720, 520); vv = QVBoxLayout(dl)
        vv.addWidget(label(t('pi_assign_help', n=p['name']), 'muted', wrap=True))
        lw = QListWidget(); vv.addWidget(lw, 1)
        for r in rows:
            it = QListWidgetItem(f"{(r.get('flight_date') or r.get('analyzed_at') or '')[:16]} · {r['name']} · {texts.T('v_' + (r['verdict'] or 'normal'), lang())}")
            it.setData(Qt.UserRole, r['uid']); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if r.get('pilot') == p['id'] else Qt.Unchecked); lw.addItem(it)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); vv.addLayout(h)
        if dl.exec() != QDialog.Accepted: return
        for i in range(lw.count()):
            it = lw.item(i); uid = it.data(Qt.UserRole); r = rows[i]
            if it.checkState() == Qt.Checked and r.get('pilot') != p['id']: self.win.archive.set_field(uid, pilot=p['id'])
            elif it.checkState() != Qt.Checked and r.get('pilot') == p['id']: self.win.archive.set_field(uid, pilot='')
        self.refresh()

    def pdf(self):
        p = self._cur()
        if not p: return info(self, t('pi_pick'))
        out, _ = QFileDialog.getSaveFileName(self, t('pi_pdf'), f"pilot_{p['name'].replace(' ', '_')}.pdf", 'PDF (*.pdf)')
        if not out: return
        s = self.win.settings
        run_bg(fleet.pilot_pdf, self.win.archive, p['id'], out, s.get('report_lang', lang()), s.letterhead(),
               on_done=lambda x: open_path(x), on_fail=lambda e: error(self, e))


# ------------------------------------------------------------------ Sınav
class ExamPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        self.tabs = QTabWidget(); v.addWidget(self.tabs)
        from . import pages_x as PX
        self.PX = PX
        self.builder = PX.ExamBuilder(self); self.tabs.addTab(self.builder, PX.tx('b_tab'))
        # --- Eğitimci
        tw = QWidget(); tv = QVBoxLayout(tw)
        r1 = QHBoxLayout()
        r1.addWidget(button('🏫 ' + t('ex_new_class'), self.new_class, primary=True))
        r1.addWidget(button('📝 ' + t('ex_new_exam'), self.new_exam, primary=True))
        r1.addWidget(button('📤 ' + t('ex_export'), self.export_pkg))
        r1.addWidget(button('📥 ' + t('ex_import'), self.import_pkg))
        r1.addWidget(button('📊 ' + t('ex_export_res'), self.export_res))
        r1.addStretch(1); tv.addLayout(r1)
        tv.addWidget(label(t('ex_help'), 'muted', wrap=True))
        sp = QSplitter(Qt.Horizontal)
        lv = QVBoxLayout(); lw = QWidget(); lw.setLayout(lv); lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(label(t('ex_classes'), 'h2'))
        self.cls = QListWidget(); self.cls.currentRowChanged.connect(self._cls_sel); lv.addWidget(self.cls, 1)
        lv.addWidget(label(t('ex_exams'), 'h2'))
        self.exs = QListWidget(); self.exs.currentRowChanged.connect(self._ex_sel); lv.addWidget(self.exs, 1)
        sp.addWidget(lw)
        rw = QWidget(); rv = QVBoxLayout(rw); rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(label(t('ex_results'), 'h2'))
        self.ex_info = label('', 'muted', wrap=True); rv.addWidget(self.ex_info)
        ph = QHBoxLayout()
        ph.addWidget(button(PX.tx('p_paper'), self.p_paper, primary=True)); ph.addWidget(button(PX.tx('p_scan'), self.p_scan))
        ph.addWidget(button(PX.tx('p_phone_scan'), lambda: self.p_live('scan'))); ph.addWidget(button(PX.tx('p_live'), lambda: self.p_live('exam')))
        ph.addStretch(1); rv.addLayout(ph)
        self.res = _tbl([t('ex_student'), t('pi_score'), '%', t('ex_passed'), t('ex_time'), t('col_date'), PX.tx('via'), PX.tx('pending'), t('ex_cert')], 0)
        self.res.doubleClicked.connect(lambda *_: self.p_grade()); rv.addWidget(self.res, 1)
        rh = QHBoxLayout(); rh.addWidget(button(PX.tx('p_grade'), self.p_grade)); rh.addWidget(button('🎓 ' + t('ex_cert_pdf'), self.cert_pdf)); rh.addStretch(1); rv.addLayout(rh)
        sp.addWidget(rw); sp.setSizes([380, 700]); tv.addWidget(sp, 1)
        self.tabs.addTab(tw, '👩‍🏫 ' + t('ex_teacher'))
        # --- Öğrenci
        sw = QWidget(); sv = QVBoxLayout(sw)
        sh = QHBoxLayout()
        sh.addWidget(label(t('ex_pick')))
        self.s_exam = QComboBox(); self.s_exam.currentIndexChanged.connect(self._students); sh.addWidget(self.s_exam, 1)
        sh.addWidget(label(t('ex_student')))
        self.s_name = QComboBox(); self.s_name.setEditable(True); self.s_name.setMinimumWidth(220); sh.addWidget(self.s_name)
        self.b_start = button('▶ ' + t('ex_start'), self.start, primary=True); sh.addWidget(self.b_start)
        sv.addLayout(sh)
        self.timer_l = label('', 'h2'); sv.addWidget(self.timer_l)
        c = card(); cv = QVBoxLayout(c); cv.setContentsMargins(20, 18, 20, 18)
        self.ql = label(t('ex_pick_help'), 'h1', wrap=True); cv.addWidget(self.ql)
        self.s_img = PX.ImgLabel(400); cv.addWidget(self.s_img)
        self.s_open_l = label(PX.tx('open_q'), 'muted', wrap=True); self.s_open_l.setVisible(False); cv.addWidget(self.s_open_l)
        self.s_open = QPlainTextEdit(); self.s_open.setMinimumHeight(130); self.s_open.setVisible(False); cv.addWidget(self.s_open)
        self.grp = QButtonGroup(self); self.opts = []
        for i in range(5):
            rb = QRadioButton(); rb.setStyleSheet('font-size:11pt; padding:6px'); rb.setVisible(False); self.grp.addButton(rb, i); self.opts.append(rb); cv.addWidget(rb)
        nav = QHBoxLayout()
        self.b_prev = button('◀ ' + t('ex_prev'), lambda: self._go(-1)); self.b_next = button(t('next') + ' ▶', lambda: self._go(1))
        self.b_finish = button('✔ ' + t('ex_finish'), self.finish, primary=True)
        for b in (self.b_prev, self.b_next, self.b_finish): b.setEnabled(False); nav.addWidget(b)
        nav.addStretch(1); cv.addLayout(nav)
        self.s_res = label('', wrap=True); cv.addWidget(self.s_res)
        sv.addWidget(c); sv.addStretch(1)
        self.tabs.addTab(PX.scroll(sw), '🧑‍🎓 ' + t('ex_student_tab'))
        self.clk = QTimer(self); self.clk.setInterval(1000); self.clk.timeout.connect(self._tick)
        self.classes = []; self.exams = []; self.cur_exam = None; self.answers = []; self.qi = 0; self.t0 = 0

    def on_show(self):
        self.refresh()
        role = getattr(self.win, 'role', 'admin')
        self.tabs.setTabEnabled(0, role != 'student'); self.tabs.setTabEnabled(1, role != 'student')
        if role == 'student': self.tabs.setCurrentIndex(2)

    # ---------- eğitimci
    def refresh(self):
        a = self.win.archive
        self.classes = a.rec_list('class'); self.cls.blockSignals(True); self.cls.clear()
        for c in self.classes: self.cls.addItem(f"{c['name']} · {c.get('instructor', '')} ({len(c.get('students', []))})")
        self.cls.blockSignals(False)
        if self.classes and self.cls.currentRow() < 0: self.cls.setCurrentRow(0)
        self._cls_sel()
        self.builder.refresh()
        allex = a.rec_list('exam')
        cur = self.s_exam.currentData()
        self.s_exam.blockSignals(True); self.s_exam.clear()
        for e in allex: self.s_exam.addItem(f"{e['title']} · {e.get('n', 0)} {t('ex_q')} · {e.get('time_limit_min')} {t('ex_min')}", e['id'])
        if cur: self.s_exam.setCurrentIndex(max(0, self.s_exam.findData(cur)))
        self.s_exam.blockSignals(False)
        self._students()

    def _students(self, *_):
        a = self.win.archive; e = a.rec_get('exam', self.s_exam.currentData() or '')
        self.s_name.clear()
        if e:
            c = a.rec_get('class', e.get('class_id')) or {}
            self.s_name.addItems(c.get('students', []))

    def _cur_class(self):
        r = self.cls.currentRow()
        return self.classes[r] if 0 <= r < len(self.classes) else None

    def _cls_sel(self, *_):
        c = self._cur_class(); a = self.win.archive
        self.exams = [e for e in a.rec_list('exam') if c and e.get('class_id') == c['id']]
        self.exs.blockSignals(True); self.exs.clear()
        for e in self.exams: self.exs.addItem(' · '.join(str(x) for x in (e['title'], ('#' + e['code']) if e.get('code') else '', e.get('log_name', ''), e.get('created', '')) if x))
        self.exs.blockSignals(False)
        if self.exams: self.exs.setCurrentRow(0)
        self._ex_sel()

    def _cur_exam(self):
        r = self.exs.currentRow()
        return self.exams[r] if 0 <= r < len(self.exams) else None

    def _ex_sel(self, *_):
        e = self._cur_exam()
        if not e: self.res.setRowCount(0); self.ex_info.setText(''); self.results = []; return
        from ..core import exam as X
        PX = self.PX; n_open = sum(1 for q in e.get('questions', []) if X.is_open(q)); n_img = sum(1 for q in e.get('questions', []) if q.get('img'))
        self.ex_info.setText(f"{PX.tx('l_code')}: {e.get('code', '-')}  ·  {len(e.get('questions', []))} {t('ex_q')} (☑ {len(e.get('questions', [])) - n_open} · ✎ {n_open} · 🖼 {n_img})"
                             f"  ·  {e.get('time_limit_min')} {t('ex_min')}  ·  %{e.get('pass_mark')}")
        self.results = X.results_of(self.win.archive, e['id'])
        via = {'omr': PX.tx('via_omr'), 'phone': PX.tx('via_phone')}
        pend = [X.pending(e, r) for r in self.results]
        _fill(self.res, [[r['student'], f"{r['score']:g}/{r['total']}", f"{r['pct']:.0f}", '✔' if r['passed'] else '✘', f"{r['duration_s'] // 60}:{r['duration_s'] % 60:02d}",
                          r.get('date', ''), via.get(r.get('via'), PX.tx('via_pc')), str(p) if p else '', r.get('cert_id', '')] for r, p in zip(self.results, pend)],
              [[None, None, None, '#4ADE80' if r['passed'] else '#F87171', None, None, None, '#FBBF24' if p else None, None] for r, p in zip(self.results, pend)])

    def _need_exam(self):
        e = self._cur_exam()
        if not e: info(self, t('ex_need_exam'))
        return e

    def p_paper(self):
        e = self._need_exam()
        if e:
            from ..core import exam as X
            self.PX.make_papers(self, X.ensure_code(self.win.archive, e), self.win)

    def p_scan(self):
        e = self._need_exam()
        if e: self.PX.scan_files(self, e, self.win, self._ex_sel)

    def p_live(self, mode):
        e = self._need_exam()
        if e: self.PX.LiveDialog(self, self.win, e, mode, self._ex_sel).exec(); self._ex_sel()

    def p_grade(self):
        r = self.res.currentRow()
        if not (0 <= r < len(getattr(self, 'results', []))): return info(self, self.PX.tx('g_pick'))
        if self.PX.GradeDialog(self, self.win, self.results[r]).exec(): self._ex_sel()

    def new_class(self):
        dl = QDialog(self); dl.setWindowTitle(t('ex_new_class')); dl.setMinimumWidth(460); f = QFormLayout(dl)
        nm = QLineEdit(); f.addRow(t('ex_class_name'), nm)
        ins = QLineEdit(getattr(self.win, 'user_name', '') or ''); f.addRow(t('ex_instructor'), ins)
        st = QPlainTextEdit(); st.setPlaceholderText(t('ex_students_ph')); f.addRow(t('ex_students'), st)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted or not nm.text().strip(): return
        from ..core import exam as X
        X.create_class(self.win.archive, nm.text().strip(), ins.text().strip(), [x.strip() for x in st.toPlainText().splitlines() if x.strip()])
        self.refresh()

    def new_exam(self):
        c = self._cur_class()
        if not c: return info(self, t('ex_need_class'))
        dl = QDialog(self); dl.setWindowTitle(t('ex_new_exam')); dl.setMinimumWidth(520); f = QFormLayout(dl)
        ti = QLineEdit(); f.addRow(t('ex_exam_title'), ti)
        src = QComboBox(); src.addItem(t('ex_src_open'), 'open')
        from ..core import synth
        for sc in synth.SCENARIOS if hasattr(synth, 'SCENARIOS') else ['normal', 'gps_loss', 'battery', 'vibration', 'radio_loss', 'stall', 'compass']:
            src.addItem(t('ex_src_scen') + ': ' + sc, 'scen:' + sc)
        src.addItem(t('ex_src_file'), 'file')
        from .pages_q import tx as qtx
        from ..core import qbank as QB
        src.insertItem(0, '🗃 ' + qtx('ex_bank'), 'bank'); src.insertItem(1, '🗃 ' + qtx('ex_bank_log'), 'bank_log'); src.setCurrentIndex(0)
        f.addRow(t('ex_source'), src)
        btop = QComboBox(); btop.addItem(qtx('all_t'), None)
        for k in QB.TOPICS: btop.addItem(QB.topic_name(k, lang()), k)
        blvl = QComboBox(); blvl.addItem(qtx('all_l'), None)
        for n_ in (1, 2, 3): blvl.addItem(QB.level_name(n_, lang()), n_)
        f.addRow(qtx('ed_topic'), btop); f.addRow(qtx('ed_level'), blvl)
        src.currentIndexChanged.connect(lambda *_: (btop.setEnabled(src.currentData() in ('bank', 'bank_log')), blvl.setEnabled(src.currentData() in ('bank', 'bank_log'))))
        n = QSpinBox(); n.setRange(3, 100); n.setValue(20); f.addRow(t('ex_nq'), n)
        tl = QSpinBox(); tl.setRange(1, 240); tl.setValue(20); f.addRow(t('ex_limit'), tl)
        pm = QSpinBox(); pm.setRange(1, 100); pm.setValue(70); f.addRow(t('ex_pass'), pm)
        lc = QComboBox()
        for code, nme in (('tr', 'Türkçe'), ('en', 'English'), ('ar', 'العربية')): lc.addItem(nme, code)
        lc.setCurrentIndex(lc.findData(lang())); f.addRow(t('rep_lang'), lc)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted: return
        s = src.currentData(); path = None
        if s in ('open', 'bank_log') and not self.win.A: return error(self, t('no_log'))
        bt = {btop.currentData()} if btop.currentData() else None; bl = {blvl.currentData()} if blvl.currentData() else None
        if s == 'file':
            path, _ = QFileDialog.getOpenFileName(self, t('open_log'), '', 'Pixhawk log (*.bin *.BIN *.tlog)')
            if not path: return
        title = ti.text().strip() or time.strftime('Sınav %Y-%m-%d')
        A0 = self.win.A; arc = self.win.archive

        def job():
            from ..core import exam as X, loader, analysis
            if s in ('bank', 'bank_log'):
                qs = X.bank_questions(arc, lc.currentData(), n.value(), bt, bl, A0, s == 'bank_log')
                source = {'type': 'bank', 'topics': sorted(bt) if bt else 'all', 'levels': sorted(bl) if bl else 'all'}
                return X.create_exam(arc, c['id'], title, A0 if s == 'bank_log' else None, lc.currentData(), n.value(), tl.value(), pm.value(), source, questions=qs)
            if s == 'open': A = A0; source = {'type': 'open', 'name': os.path.basename(A.L.path)}
            elif s == 'file': A = analysis.Analysis(loader.load(path)); source = {'type': 'file', 'name': os.path.basename(path)}
            else:
                import tempfile
                p = os.path.join(tempfile.mkdtemp(), s[5:] + '.BIN'); synth.generate(p, s[5:])
                A = analysis.Analysis(loader.load(p, use_cache=False)); source = {'type': 'scenario', 'name': s[5:]}
            return X.create_exam(arc, c['id'], title, A, lc.currentData(), n.value(), tl.value(), pm.value(), source)
        run_bg(job, on_done=lambda _: (self.refresh(), info(self, t('ex_created'))), on_fail=lambda e: error(self, e))

    def _pw(self, title):
        pw, ok = QInputDialog.getText(self, title, t('ex_pw'), QLineEdit.Password)
        return pw if ok else None

    def export_pkg(self):
        e = self._cur_exam()
        if not e: return info(self, t('ex_need_exam'))
        out, _ = QFileDialog.getSaveFileName(self, t('ex_export'), f"{e['title']}.pxexam", 'Pixhawk exam (*.pxexam)')
        if not out: return
        pw = self._pw(t('ex_export'))
        if pw is None: return
        from ..core import exam as X
        X.export_package(self.win.archive, e['id'], out, pw); info(self, t('done') + '\n' + out)

    def export_res(self):
        e = self._cur_exam()
        if not e: return info(self, t('ex_need_exam'))
        out, _ = QFileDialog.getSaveFileName(self, t('ex_export_res'), f"{e['title']}_sonuclar.pxres", 'Results (*.pxres)')
        if not out: return
        pw = self._pw(t('ex_export_res'))
        if pw is None: return
        from ..core import exam as X
        X.export_results(self.win.archive, e['id'], out, pw); info(self, t('done') + '\n' + out)

    def import_pkg(self):
        p, _ = QFileDialog.getOpenFileName(self, t('ex_import'), '', 'Pixhawk exam / results (*.pxexam *.pxres)')
        if not p: return
        from ..core import exam as X, security
        pw = ''
        if security.is_encrypted(open(p, 'rb').read(8)):
            pw = self._pw(t('ex_import'))
            if pw is None: return
        try:
            kind, n = X.import_file(self.win.archive, p, pw)
        except Exception as e:
            return error(self, t('ex_bad_pw') + f'\n{e}')
        self.refresh(); info(self, t('ex_imported', n=n))

    def cert_pdf(self):
        r = self.res.currentRow()
        if not (0 <= r < len(getattr(self, 'results', []))): return info(self, t('ex_pick_res'))
        res = self.results[r]
        if not res['passed']: return info(self, t('ex_not_passed'))
        out, _ = QFileDialog.getSaveFileName(self, t('ex_cert_pdf'), f"sertifika_{res['student'].replace(' ', '_')}.pdf", 'PDF (*.pdf)')
        if not out: return
        from ..core import exam as X
        s = self.win.settings
        run_bg(X.certificate_pdf, self.win.archive, res, out, s.get('report_lang', lang()), s.letterhead(), on_done=open_path, on_fail=lambda e: error(self, e))

    # ---------- öğrenci
    def start(self):
        eid = self.s_exam.currentData(); name = self.s_name.currentText().strip()
        if not eid: return info(self, t('ex_need_exam'))
        if not name: return info(self, t('ex_need_name'))
        self.cur_exam = self.win.archive.rec_get('exam', eid); self.student = name
        self.answers = ['' if q.get('type') == 'open' else -1 for q in self.cur_exam['questions']]; self.qi = 0; self.t0 = time.time()
        for b in (self.b_prev, self.b_next, self.b_finish): b.setEnabled(True)
        self.b_start.setEnabled(False); self.s_res.setText(''); self.clk.start(); self._show_q(); self._tick()

    def _show_q(self):
        e = self.cur_exam; q = e['questions'][self.qi]
        self.ql.setText(f"{self.qi + 1}/{len(e['questions'])} · {q['q']}")
        self.s_img.set_ref(q.get('img'))
        op = q.get('type') == 'open'
        self.s_open_l.setVisible(op); self.s_open.setVisible(op)
        if op: self.s_open.setPlainText(self.answers[self.qi] if isinstance(self.answers[self.qi], str) else '')
        self.grp.setExclusive(False)
        for k, rb in enumerate(self.opts):
            vis = not op and k < len(q['opts'])
            rb.setVisible(vis); rb.setChecked(False)
            if vis: rb.setText(q['opts'][k])
        a = self.answers[self.qi]
        if not op and isinstance(a, int) and 0 <= a < len(self.opts): self.opts[a].setChecked(True)
        self.grp.setExclusive(True)

    def _save_ans(self):
        if self.cur_exam is None: return
        q = self.cur_exam['questions'][self.qi]
        self.answers[self.qi] = self.s_open.toPlainText().strip() if q.get('type') == 'open' else self.grp.checkedId()

    def _go(self, d):
        if not self.cur_exam: return
        self._save_ans()
        self.qi = max(0, min(len(self.answers) - 1, self.qi + d)); self._show_q()

    def _tick(self):
        if not self.cur_exam: return
        left = self.cur_exam['time_limit_min'] * 60 - (time.time() - self.t0)
        if left <= 0: self.timer_l.setText(t('ex_timeup')); self.finish(force=True); return
        self.timer_l.setText(f"⏱ {int(left // 60)}:{int(left % 60):02d}  ·  {self.student}")

    def finish(self, force=False):
        if not self.cur_exam: return
        self._save_ans()
        blank = sum(1 for a in self.answers if a == -1 or a == '')
        if not force and blank and QMessageBox.question(self, t('app'), t('ex_unanswered', n=blank)) != QMessageBox.Yes:
            return
        from ..core import exam as X
        self.clk.stop()
        r = X.save_result(self.win.archive, self.cur_exam, self.student, self.answers, self.t0, time.time())
        lg = lang(); qs = self.cur_exam['questions']
        d = 'rtl' if lg == 'ar' else 'ltr'
        h = [f'<div dir="{d}"><h2 style="color:{"#4ADE80" if r["passed"] else "#F87171"}">{E(t("ex_result", s=r["score"], n=r["total"], p=int(round(r["pct"]))))} — '
             f'{E(t("ex_pass_txt") if r["passed"] else t("ex_fail_txt"))}</h2>']
        for i, (q, a) in enumerate(zip(qs, self.answers)):
            if q.get('type') == 'open':
                pts = ((r.get('auto') or {}).get(str(i)) or {}).get('pts', 0)
                h.append(f'<p><b>{i + 1}.</b> {E(q["q"])}<br><span style="color:#FBBF24">✎ {E(a or "-")}</span><br>'
                         f'<span style="color:#CBD5E1"><b>{E(self.PX.tx("model"))}:</b> {E(q.get("model") or q.get("exp", ""))}</span>'
                         f'<br><span style="color:#94A3B8">{E(self.PX.tx("g_auto", s=f"{pts:g}", h=self.PX.tx("pending")))}</span></p>')
                continue
            ok = a == q['ans']
            h.append(f'<p><b>{i + 1}.</b> {E(q["q"])}<br><span style="color:{"#4ADE80" if ok else "#F87171"}">{"✔" if ok else "✘"} '
                     f'{E(q["opts"][a]) if a >= 0 else "-"}</span>' + ('' if ok else f' → <b>{E(q["opts"][q["ans"]])}</b><br><span style="color:#CBD5E1">'
                                                                         f'{E((q.get("wexp") or [""] * 4)[a] if a >= 0 else q.get("exp", ""))}</span>') + '</p>')
        self.s_res.setText(''.join(h) + '</div>'); self.s_res.setTextFormat(Qt.RichText)
        self.ql.setText(t('ex_done'))
        for rb in self.opts: rb.setVisible(False)
        self.s_img.set_raw(None); self.s_open.setVisible(False); self.s_open_l.setVisible(False)
        for b in (self.b_prev, self.b_next, self.b_finish): b.setEnabled(False)
        self.b_start.setEnabled(True); self.cur_exam = None
        self.refresh()
        if r['passed'] and QMessageBox.question(self, t('app'), t('ex_cert_q')) == QMessageBox.Yes:
            out, _ = QFileDialog.getSaveFileName(self, t('ex_cert_pdf'), f"sertifika_{r['student'].replace(' ', '_')}.pdf", 'PDF (*.pdf)')
            if out:
                s = self.win.settings
                run_bg(X.certificate_pdf, self.win.archive, r, out, s.get('report_lang', lg), s.letterhead(), on_done=open_path, on_fail=lambda e: error(self, e))
