"""Sayfalar: Senaryolar, Toplu analiz, Arşiv/Trend, Kütüphaneler, Doğrulama."""
from __future__ import annotations
import html, io, json, os, time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QTextBrowser, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit, QCheckBox, QComboBox, QFileDialog,
                               QProgressBar, QPlainTextEdit, QSplitter, QMessageBox, QDialog)
from PySide6.QtGui import QColor
from .i18n import t, lang
from .common import label, button, run_bg, error, info, ImageView, open_path, VERDICT_COL
from .pages_a import Page
from ..core import glossary as GL
from ..core import texts
from ..core.analysis import fmt_t
from ..core.paths import res, data_dir

E = html.escape
LI = {'tr': 0, 'en': 1, 'ar': 2}

from ..core.scenarios import SCEN  # noqa: E402


class ScenarioPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout(); top.addWidget(label(t('scen_intro'), 'muted', wrap=True), 1)
        from .pages_p import book_dialog
        top.addWidget(button('📕 ' + t('tb_btn'), lambda: book_dialog(self.win, self), primary=True))
        v.addLayout(top)
        h = QHBoxLayout()
        self.list = QListWidget(); self.list.setFixedWidth(300)
        i = LI[lang()]
        for k, (n, d) in SCEN.items():
            it = QListWidgetItem(n[i]); it.setData(Qt.UserRole, k); self.list.addItem(it)
        self.list.currentItemChanged.connect(self._sel)
        h.addWidget(self.list)
        r = QVBoxLayout()
        self.desc = QTextBrowser(); r.addWidget(self.desc, 1)
        self.b = button('▶ ' + t('scen_load'), self.load, primary=True); r.addWidget(self.b)
        h.addLayout(r, 1); v.addLayout(h, 1)
        self.list.setCurrentRow(0)

    def _sel(self, it, *_):
        if not it: return
        k = it.data(Qt.UserRole); i = LI[lang()]; d = 'rtl' if lang() == 'ar' else 'ltr'
        n, ds = SCEN[k]
        self.desc.setHtml(f'<div dir="{d}"><h2 style="color:#93C5FD">{E(n[i])}</h2><p style="font-size:11.5pt">{E(ds[i])}</p></div>')

    def load(self):
        it = self.list.currentItem()
        if not it: return
        k = it.data(Qt.UserRole)
        from ..core import synth
        d = os.path.join(data_dir(), 'scenarios'); os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f'senaryo_{k}.BIN')
        self.b.setEnabled(False)

        def ok(_):
            self.b.setEnabled(True); self.win.open_log(p, archive=False)
        run_bg(lambda: synth.generate(p, k), on_done=ok, on_fail=lambda e: (self.b.setEnabled(True), error(self, e)))


# ---------------------------------------------------------------- Toplu
class BatchPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        self.b = button('📁 ' + t('batch_pick'), self.pick, primary=True); top.addWidget(self.b)
        self.rep = QCheckBox(t('batch_reports')); top.addWidget(self.rep)
        self.b_stop = button(t('cancel'), self.stop); self.b_stop.setEnabled(False); top.addWidget(self.b_stop)
        top.addStretch(1); v.addLayout(top)
        self.prog = QProgressBar(); self.prog.setVisible(False); v.addWidget(self.prog)
        cols = ['col_file', 'col_verdict', 'col_score', 'col_cause', 'col_flight', 'col_status']
        self.tbl = QTableWidget(0, len(cols)); self.tbl.setHorizontalHeaderLabels([t(c) for c in cols])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.verticalHeader().setVisible(False); self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows); self.tbl.setAlternatingRowColors(True)
        self.tbl.doubleClicked.connect(lambda ix: self.win.open_log(self.paths[ix.row()]))
        v.addWidget(self.tbl, 1)
        self.paths = []; self._stop = False

    def pick(self):
        d = QFileDialog.getExistingDirectory(self, t('batch_pick'))
        if d: self.run_folder(d)

    def stop(self):
        self._stop = True

    def run_folder(self, d):
        files = []
        for root, _, fs in os.walk(d):
            for f in fs:
                if f.lower().endswith(('.bin', '.tlog')): files.append(os.path.join(root, f))
        files.sort(); self.paths = files
        self.tbl.setRowCount(len(files))
        for i, f in enumerate(files):
            self.tbl.setItem(i, 0, QTableWidgetItem(os.path.relpath(f, d)))
            for j in range(1, 6): self.tbl.setItem(i, j, QTableWidgetItem(''))
        if not files: return
        self.prog.setVisible(True); self.prog.setRange(0, len(files)); self.prog.setValue(0)
        self.b.setEnabled(False); self.b_stop.setEnabled(True); self._stop = False
        lg = lang(); s = self.win.settings; arc = self.win.archive; mkrep = self.rep.isChecked()
        w = None

        def job():
            from ..core import loader, analysis, archive as AR, report
            for i, f in enumerate(files):
                if self._stop: break
                w.progress.emit((i, None))
                try:
                    L = loader.load(f, cancel=lambda: self._stop)
                    A = analysis.Analysis(L)
                    uid = AR.file_uid(f)
                    arc.add_analysis(uid, A, f, s['device_name'], s.get('archive_copy_logs', True), s.get('archive_copy_max_mb', 200))
                    st = 'OK'
                    if mkrep:
                        rd = report.ReportData(A, lg, None, s.get('online', True), s.get('map_src', 'osm'))
                        out = os.path.splitext(f)[0] + f'_rapor_{lg}.pdf'
                        report.build_pdf(rd, out, s.letterhead())
                        arc.add_report(rd.id, uid, report.file_sha256(out), A.verdict.get('kind'), A.overall, lg, 'pdf', out, s['device_name'], os.path.basename(f))
                        st = '📄 ' + os.path.basename(out)
                    w.progress.emit((i, (A.verdict.get('kind'), A.overall, (A.root or {}).get('cause', ''), A.facts.get('flight_time', 0), st)))
                except Exception as e:
                    w.progress.emit((i, ('err', 0, '', 0, str(e)[:120])))
            return True

        def prog(x):
            i, r = x
            if r is None:
                self.tbl.item(i, 5).setText('…'); self.tbl.scrollToItem(self.tbl.item(i, 0)); return
            self.prog.setValue(i + 1)
            k, sc, cause, ft, st = r
            vals = [texts.T('v_' + k, lang()) if k != 'err' else t('err'), str(sc) if k != 'err' else '-',
                    texts.T('cause_' + cause, lang()) if cause else '', fmt_t(ft) if ft else '-', st]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if j == 0 and k in VERDICT_COL: it.setForeground(QColor(VERDICT_COL[k]))
                self.tbl.setItem(i, j + 1, it)

        def fin(_):
            self.b.setEnabled(True); self.b_stop.setEnabled(False); self.prog.setVisible(False)
            self.win.pages['archive'].refresh()
        w = run_bg(job, on_done=fin, on_fail=lambda e: (fin(None), error(self, e)), on_progress=prog)


# ---------------------------------------------------------------- Arşiv
class ArchivePage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText(t('ar_search_ph')); self.q.textChanged.connect(self.refresh); top.addWidget(self.q, 1)
        self.f_per = QComboBox(); self.f_per.addItem(t('ar_period') + ': ' + t('ar_all'), 0)
        for d in (7, 30, 90, 365): self.f_per.addItem(t(f'd{d}'), d)
        self.f_ver = QComboBox(); self.f_ver.addItem(t('col_verdict') + ': ' + t('ar_all'), '')
        for k in ('crash', 'incident', 'normal'): self.f_ver.addItem(texts.T('v_' + k, lang()), k)
        self.f_cr = QComboBox(); self.f_cr.addItem('💥 ' + t('fi_crash_mark') + ': ' + t('ar_all'), '')
        self.f_cr.addItem('💥 ' + t('fi_crash_yes'), 'yes'); self.f_cr.addItem('⚠ ' + t('fi_crash_hard'), 'hard')
        self.f_cr.addItem('✅ ' + t('fi_crash_no'), 'no'); self.f_cr.addItem('○ ' + t('fi_crash_none'), 'none')
        self.f_ac = QComboBox(); self.f_pi = QComboBox()
        for w in (self.f_per, self.f_ver, self.f_cr, self.f_ac, self.f_pi): w.currentIndexChanged.connect(self.refresh); top.addWidget(w)
        top.addWidget(button(t('open_sel'), self.open_sel, primary=True))
        top.addWidget(button(t('compare'), self.compare))
        top.addWidget(button('💥 ' + t('fi_mark_btn'), self.toggle_crash))
        top.addWidget(button(t('remove_sel'), self.remove))
        v.addLayout(top)
        self.f_desc = label('', 'muted'); v.addWidget(self.f_desc)
        sp = QSplitter(Qt.Vertical)
        cols = ['col_crash', 'col_date', 'col_file', 'col_vehicle', 'col_verdict', 'col_score', 'col_cause', 'col_flight', 'col_aircraft', 'col_pilot', 'col_notes']
        self.tbl = QTableWidget(0, len(cols)); self.tbl.setHorizontalHeaderLabels([t(c) for c in cols])
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl.verticalHeader().setVisible(False); self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows); self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tbl.itemSelectionChanged.connect(self._sel); self.tbl.doubleClicked.connect(lambda *_: self.open_sel())
        sp.addWidget(self.tbl)
        bot = QWidget(); bh = QHBoxLayout(bot); bh.setContentsMargins(0, 0, 0, 0)
        nv = QVBoxLayout()
        nv.addWidget(label(t('col_notes'), 'h2'))
        self.notes = QPlainTextEdit(); nv.addWidget(self.notes, 1)
        nv.addWidget(button(t('save_notes'), self.save_notes))
        self.reps = QTextBrowser(); self.reps.setOpenLinks(False); self.reps.anchorClicked.connect(lambda u: open_path(u.toLocalFile()))
        nv.addWidget(label(t('reports_of'), 'h2')); nv.addWidget(self.reps, 1)
        bh.addLayout(nv, 1)
        tv = QVBoxLayout(); tv.addWidget(label(t('trend'), 'h2'))
        self.trend = ImageView(); tv.addWidget(self.trend, 1)
        bh.addLayout(tv, 2)
        sp.addWidget(bot); sp.setSizes([400, 360])
        v.addWidget(sp, 1)
        self.rows = []
        self.refresh()

    def on_show(self):
        self.refresh()

    def _fill_filters(self, acn, pin):
        for cb, title, d in ((self.f_ac, t('col_aircraft'), acn), (self.f_pi, t('col_pilot'), pin)):
            cur = cb.currentData(); cb.blockSignals(True); cb.clear(); cb.addItem(title + ': ' + t('ar_all'), '')
            for k, n in sorted(d.items(), key=lambda x: x[1]): cb.addItem(n, k)
            cb.setCurrentIndex(max(0, cb.findData(cur))); cb.blockSignals(False)

    def refresh(self, *_):
        from ..core import search
        a = self.win.archive; lg = lang()
        acn = {x['id']: x.get('name') or x['id'] for x in a.rec_list('aircraft')}
        pin = {x['id']: x['name'] for x in a.rec_list('pilot')}
        self._fill_filters(acn, pin)
        f = search.parse(self.q.text())
        if self.f_per.currentData(): f['days'] = self.f_per.currentData()
        if self.f_ver.currentData(): f['verdict'] = self.f_ver.currentData()
        if self.f_ac.currentData(): f['aircraft'] = self.f_ac.currentData()
        if self.f_pi.currentData(): f['pilot'] = self.f_pi.currentData()
        allr = a.list()
        cr = self.f_cr.currentData()
        if cr: allr = [r for r in allr if (r.get('crash_mark') or 'none') == cr]
        self.rows = search.apply(allr, f, acn, pin)
        dsc = search.describe(f, lg)
        self.f_desc.setText((t('ar_filter', d=dsc) + '  ·  ' if dsc else '') + t('ar_n', n=len(self.rows)))
        self.tbl.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            vals = [{'yes': '💥', 'hard': '⚠', 'no': '✅'}.get(r.get('crash_mark') or '', ''), r['flight_date'] or r['analyzed_at'][:16], r['name'], f"{r['vehicle']} {r['version'] or ''}",
                    texts.T('v_' + (r['verdict'] or 'normal'), lg), str(r['overall']),
                    texts.T('cause_' + r['cause'], lg) if r['cause'] else '', fmt_t(r['flight_time'] or 0),
                    acn.get(r.get('aircraft') or '', r.get('aircraft') or ''), pin.get(r.get('pilot') or '', ''), (r['notes'] or '').replace('\n', ' ')[:60]]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if j == 4: it.setForeground(QColor(VERDICT_COL.get(r['verdict'], '#94A3B8')))
                if j == 0: it.setToolTip(t('fi_crash_' + {'yes': 'yes', 'hard': 'hard', 'no': 'no'}.get(r.get('crash_mark') or '', 'none')))
                self.tbl.setItem(i, j, it)
        self.tbl.resizeColumnsToContents(); self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._trend()

    def toggle_crash(self):
        rs = self._cur()
        if not rs: return
        new = '' if all((r.get('crash_mark') == 'yes') for r in rs) else 'yes'
        for r in rs:
            self.win.archive.set_field(r['uid'], crash_mark=new)
            try:
                inf = json.loads(r.get('info') or '{}')
                if new: inf['crashed'] = 'yes'
                else: inf.pop('crashed', None)
                self.win.archive.set_field(r['uid'], info=json.dumps(inf, ensure_ascii=False))
            except Exception: pass
        self.refresh()

    def _cur(self):
        rs = sorted({i.row() for i in self.tbl.selectedIndexes()})
        return [self.rows[i] for i in rs if i < len(self.rows)]

    def _sel(self):
        c = self._cur()
        if not c: return
        r = c[0]; self.notes.setPlainText(r['notes'] or '')
        reps = self.win.archive.reports(r['uid'])
        self.reps.setHtml(''.join(f'<p>{E(x["created"])} · {x["lang"].upper()} {x["fmt"].upper()} · <b>{E(x["report_id"])}</b>' +
                                  (f' · <a href="file:///{E(x["path"])}">{E(os.path.basename(x["path"]))}</a>' if x['path'] and os.path.exists(x['path']) else '') + '</p>'
                                  for x in reps) or '-')

    def save_notes(self):
        c = self._cur()
        if c: self.win.archive.set_notes(c[0]['uid'], self.notes.toPlainText()); self.refresh()

    def open_sel(self):
        c = self._cur()
        if not c: return
        r = c[0]
        p = r['stored'] if r['stored'] and os.path.exists(r['stored']) else (r['src_path'] if r['src_path'] and os.path.exists(r['src_path']) else None)
        if not p: return error(self, t('not_stored'))
        self.win.open_log(p)

    def remove(self):
        c = self._cur()
        if not c: return
        if QMessageBox.question(self, t('app'), t('confirm_remove')) == QMessageBox.Yes:
            for r in c: self.win.archive.remove(r['uid'])
            self.refresh()

    def _trend(self):
        rows = sorted(self.rows, key=lambda r: r['flight_date'] or r['analyzed_at'])[-60:]
        if not rows: self.trend.set_png(None); return
        from matplotlib.figure import Figure
        fig = Figure(figsize=(8, 3.4), dpi=110); ax = fig.add_subplot(111)
        x = range(len(rows))
        cols = [VERDICT_COL.get(r['verdict'], '#64748B') for r in rows]
        ax.bar(x, [r['overall'] for r in rows], color=cols, alpha=0.85)
        ax.set_ylim(0, 105); ax.set_ylabel('Score / Puan')
        ax2 = ax.twinx(); ax2.plot(list(x), [(r['flight_time'] or 0) / 60 for r in rows], 'o-', color='#2563EB', lw=1.2, ms=3)
        ax2.set_ylabel('min')
        ax.set_xticks(list(x)); ax.set_xticklabels([(r['flight_date'] or r['analyzed_at'])[5:10] for r in rows], rotation=60, fontsize=6)
        ax.grid(axis='y', color='#E5E7EB')
        fig.tight_layout(); b = io.BytesIO(); fig.savefig(b, format='png'); self.trend.set_png(b.getvalue())

    def compare(self):
        c = self._cur()
        if len(c) != 2: return info(self, t('compare_need2'))
        a, b = c; lg = lang()
        ha = json.loads(a['health'] or '{}'); hb = json.loads(b['health'] or '{}')
        fa = json.loads(a['facts'] or '{}'); fb = json.loads(b['facts'] or '{}')
        rows = [(t('col_file'), a['name'], b['name']), (t('col_verdict'), texts.T('v_' + a['verdict'], lg), texts.T('v_' + b['verdict'], lg)),
                (t('col_score'), a['overall'], b['overall']), (t('col_flight'), fmt_t(a['flight_time'] or 0), fmt_t(b['flight_time'] or 0))]
        for k, lab in (('max_alt', 'Max Alt (m)'), ('distance', 'Dist (m)'), ('max_gs', 'Max GS (m/s)'), ('min_volt', 'Min V'), ('used_mah', 'mAh')):
            rows.append((lab, f"{fa.get(k, 0) or 0:.1f}", f"{fb.get(k, 0) or 0:.1f}"))
        for k in sorted(set(ha) | set(hb)):
            rows.append((texts.T('dom_' + k, lg), ha.get(k, '-'), hb.get(k, '-')))
        d = 'rtl' if lg == 'ar' else 'ltr'
        h = f'<div dir="{d}"><table width="100%" cellpadding="6">' + ''.join(
            f'<tr bgcolor="{"#111C33" if i % 2 else "#0F1A30"}"><td><b>{E(str(x))}</b></td><td>{E(str(y))}</td><td>{E(str(z))}</td></tr>' for i, (x, y, z) in enumerate(rows)) + '</table></div>'
        dl = QDialog(self); dl.setWindowTitle(t('compare')); dl.resize(760, 560)
        vv = QVBoxLayout(dl); tb = QTextBrowser(); tb.setHtml(h); vv.addWidget(tb); vv.addWidget(button(t('close'), dl.accept))
        dl.exec()


# ------------------------------------------------------- Log mesajları kütüphanesi
class MsgLibPage(Page):
    def __init__(self, win):
        super().__init__(win)
        self.M = json.load(open(res('data', 'logmsgs.json'), encoding='utf-8'))
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText(t('search') + ' (VIBE, GPS, Volt, titreşim…)'); self.q.textChanged.connect(self.fill)
        top.addWidget(self.q, 1)
        self.core = QCheckBox(t('core_only')); self.core.setChecked(True); self.core.toggled.connect(self.fill); top.addWidget(self.core)
        self.inlog = QCheckBox(t('in_log')); self.inlog.toggled.connect(self.fill); top.addWidget(self.inlog)
        self.cnt = label('', 'muted'); top.addWidget(self.cnt)
        v.addLayout(top)
        h = QHBoxLayout()
        self.list = QListWidget(); self.list.setFixedWidth(330); self.list.currentItemChanged.connect(self._show); h.addWidget(self.list)
        self.view = QTextBrowser(); h.addWidget(self.view, 1)
        v.addLayout(h, 1)
        self.fill()

    def on_analysis(self, A):
        self.fill()

    def fill(self, *_):
        q = self.q.text().strip().lower(); lg = lang()
        seen = set(x.split('[')[0] for x in (self.win.A.L.types_seen if self.win.A else []))
        self.list.clear(); n = 0
        for k in sorted(self.M):
            m = self.M[k]
            if self.core.isChecked() and not m.get('core') and not q: continue
            if self.inlog.isChecked() and k not in seen: continue
            d = GL.lt(m['desc'], lg)
            if q:
                blob = (k + ' ' + d + ' ' + ' '.join(f + ' ' + GL.lt(x, lg) for f, x in m.get('fields', {}).items())).lower()
                if q not in blob: continue
            it = QListWidgetItem(f'{k}  —  {d[:60]}'); it.setData(Qt.UserRole, k)
            if k in seen: it.setForeground(QColor('#4ADE80'))
            self.list.addItem(it); n += 1
        self.cnt.setText(t('count', n=n))
        if n: self.list.setCurrentRow(0)

    def _show(self, it, *_):
        if not it: return
        k = it.data(Qt.UserRole); m = self.M[k]; lg = lang(); d = 'rtl' if lg == 'ar' else 'ltr'
        desc = GL.lt(m['desc'], lg)
        h = [f'<div dir="{d}"><h2 style="color:#93C5FD">{E(k)}</h2><p style="font-size:11pt">{E(desc)}</p>']
        if lg != 'en' and m['desc'].get('en'): h.append(f'<p style="color:#94A3B8">EN: {E(m["desc"]["en"])}</p>')
        h.append(f'<h3>{E(t("msg_fields"))}</h3><table width="100%" cellpadding="5" cellspacing="0">')
        for i, (f, x) in enumerate(m.get('fields', {}).items()):
            bg = '#111C33' if i % 2 else '#0F1A30'
            tx = GL.lt(x, lg)
            extra = f'<br><span style="color:#64748B">{E(x.get("en", ""))}</span>' if lg != 'en' and x.get('en') and GL.lt(x, lg) != x.get('en') else ''
            h.append(f'<tr bgcolor="{bg}"><td nowrap><b>{E(f)}</b></td><td>{E(tx)}{extra}</td></tr>')
        h.append('</table>')
        A = self.win.A
        if A:
            s = A.L.s(k)
            if s and 't' in s and len(s['t']):
                import numpy as np
                h.append(f'<h3>{E(t("in_log"))}: {len(s["t"])} ×</h3><table cellpadding="4">')
                for f, arr in s.items():
                    if f == 't' or not hasattr(arr, 'dtype') or arr.dtype.kind not in 'fiu': continue
                    try: h.append(f'<tr><td><b>{E(f)}</b></td><td>min {np.nanmin(arr):.3g}</td><td>max {np.nanmax(arr):.3g}</td><td>ort {np.nanmean(arr):.3g}</td></tr>')
                    except Exception: pass
                h.append('</table>')
        h.append('</div>')
        self.view.setHtml(''.join(h))


# ------------------------------------------------------- Parametre kütüphanesi
class ParamLibPage(Page):
    def __init__(self, win):
        super().__init__(win)
        D = json.load(open(res('data', 'params.json'), encoding='utf-8'))
        self.P = D['params']; self.G = D['groups']
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText(t('search') + ' (ARMING_CHECK, BATT_, failsafe, batarya…)'); self.q.textChanged.connect(self.fill)
        top.addWidget(self.q, 1)
        self.grp = QComboBox(); self.grp.addItem(t('all'), '')
        lg = lang()
        for g in sorted(self.G): self.grp.addItem(f'{g} — {(self.G[g].get(lg) or self.G[g].get("en") or "")[:40]}', g)
        self.grp.currentIndexChanged.connect(self.fill); self.grp.setMaximumWidth(360); top.addWidget(self.grp)
        self.only = QCheckBox(t('only_log_params')); self.only.toggled.connect(self.fill); top.addWidget(self.only)
        self.cnt = label('', 'muted'); top.addWidget(self.cnt)
        v.addLayout(top)
        h = QHBoxLayout()
        self.tbl = QTableWidget(0, 3); self.tbl.setHorizontalHeaderLabels([t('p_name'), t('p_val'), t('p_desc')])
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch); self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers); self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setAlternatingRowColors(True); self.tbl.currentCellChanged.connect(lambda r, *_: self._show(r))
        h.addWidget(self.tbl, 3)
        r = QVBoxLayout()
        self.view = QTextBrowser(); r.addWidget(self.view, 1)
        self.b_tx = button('🌐 ' + t('ai_translate'), self.ai_tx); r.addWidget(self.b_tx)
        h.addLayout(r, 2)
        v.addLayout(h, 1)
        self.names = []
        self.fill()

    def on_analysis(self, A):
        self.fill()

    def _tx(self, k):
        lg = lang(); p = self.P[k]
        if lg == 'en': return p.get('en') or ['', '']
        c = self.win.settings.get('param_tx_cache', {}).get(f'{k}|{lg}')
        return p.get(lg) or c or None

    def fill(self, *_):
        q = self.q.text().strip().lower(); g = self.grp.currentData(); lg = lang()
        lp = self.win.A.L.params if self.win.A else {}
        names = []
        for k in sorted(self.P):
            p = self.P[k]
            if g and p.get('g') != g: continue
            if self.only.isChecked() and k not in lp: continue
            if q:
                tx = self._tx(k) or ['', '']
                blob = (k + ' ' + ' '.join(p.get('en') or []) + ' ' + ' '.join(tx)).lower()
                if q not in blob: continue
            names.append(k)
        if self.only.isChecked():
            names += [k for k in sorted(lp) if k not in self.P and (not q or q in k.lower()) and not g]
        self.names = names[:3000]
        self.tbl.setRowCount(len(self.names))
        for i, k in enumerate(self.names):
            p = self.P.get(k, {}); tx = self._tx(k) if p else None
            d = (tx or p.get('en') or ['', ''])[0] if p else '—'
            it0 = QTableWidgetItem(k)
            if p.get('old'): it0.setForeground(QColor('#94A3B8'))
            self.tbl.setItem(i, 0, it0)
            self.tbl.setItem(i, 1, QTableWidgetItem(f'{lp[k]:g}' if k in lp else ''))
            self.tbl.setItem(i, 2, QTableWidgetItem(d))
        self.tbl.resizeColumnToContents(0); self.tbl.resizeColumnToContents(1)
        self.cnt.setText(t('count', n=len(names)))
        if self.names: self.tbl.setCurrentCell(0, 0); self._show(0)

    def _show(self, r):
        if r < 0 or r >= len(self.names): return
        k = self.names[r]; p = self.P.get(k); lg = lang(); d = 'rtl' if lg == 'ar' else 'ltr'
        lp = self.win.A.L.params if self.win.A else {}
        if not p:
            self.view.setHtml(f'<h2>{E(k)}</h2><p>{lp.get(k, "")}</p>'); return
        tx = self._tx(k); en = p.get('en') or ['', '']
        h = [f'<div dir="{d}"><h2 style="color:#93C5FD">{E(k)}</h2>']
        if k in lp: h.append(f'<p style="font-size:12pt">{E(t("p_val"))}: <b style="color:#FBBF24">{lp[k]:g}</b></p>')
        if tx:
            h.append(f'<p style="font-size:11.5pt"><b>{E(tx[0])}</b></p><p>{E(tx[1])}</p>')
            if lg != 'en': h.append(f'<p style="color:#94A3B8"><b>EN:</b> {E(en[0])} — {E(en[1])}</p>')
        else:
            h.append(f'<p style="font-size:11.5pt"><b>{E(en[0])}</b></p><p>{E(en[1])}</p><p style="color:#FBBF24">{E(t("no_tx"))}</p>')
        h.append('<table cellpadding="4">')
        g = p.get('g', '')
        rows = [(t('group'), f"{g} — {(self.G.get(g, {}).get(lg) or self.G.get(g, {}).get('en') or '')}"), (t('p_units'), p.get('u', '')),
                (t('p_range'), p.get('r', '')), (t('p_vehicles'), ', '.join(p.get('v', [])))]
        for a, b in rows:
            if b: h.append(f'<tr><td style="color:#94A3B8">{E(a)}</td><td>{E(str(b))}</td></tr>')
        h.append('</table>')
        if p.get('vals'):
            h.append(f'<h3>{E(t("p_values"))}</h3><table cellpadding="3">')
            for it in str(p['vals']).split(','):
                if ':' in it:
                    a, b = it.split(':', 1)
                    cur = ' style="color:#FBBF24;font-weight:700"' if k in lp and a.strip().lstrip('-').replace('.', '').isdigit() and float(a) == lp[k] else ''
                    h.append(f'<tr{cur}><td>{E(a)}</td><td>{E(b)}</td></tr>')
            h.append('</table>')
        if p.get('bm'):
            h.append(f'<h3>{E(t("p_bits"))}</h3><table cellpadding="3">')
            val = int(lp[k]) if k in lp else None
            for it in str(p['bm']).split(','):
                if ':' in it:
                    a, b = it.split(':', 1)
                    on = val is not None and a.strip().isdigit() and (val >> int(a)) & 1
                    h.append(f'<tr><td>{"☑" if on else "☐"} {E(a)}</td><td>{E(b)}</td></tr>')
            h.append('</table>')
        if p.get('old'): h.append(f'<p style="color:#94A3B8">⚠ {E(t("p_legacy"))}</p>')
        if p.get('rb'): h.append(f'<p style="color:#FBBF24">⟳ {E(t("p_reboot"))}</p>')
        h.append('</div>')
        self.view.setHtml(''.join(h))
        self.b_tx.setVisible(lg != 'en' and not p.get(lg))

    def ai_tx(self):
        r = self.tbl.currentRow()
        if r < 0: return
        k = self.names[r]; p = self.P.get(k); lg = lang()
        from ..core import ai as AI
        s = self.win.settings
        if not p or lg == 'en': return
        if not AI.available(s): return error(self, t('need_key').split('.')[0])
        en = p.get('en') or ['', '']
        txt = f'{en[0]}\n|||\n{en[1]}'
        self.b_tx.setEnabled(False)

        def job():
            return AI.translate(s, self.win.usage, txt, lg)

        def ok(out):
            self.b_tx.setEnabled(True)
            parts = out.split('|||')
            v = [parts[0].strip(), (parts[1] if len(parts) > 1 else '').strip()]
            self.win.settings.setdefault('param_tx_cache', {})[f'{k}|{lg}'] = v; self.win.settings.save()
            self._show(r)
        run_bg(job, on_done=ok, on_fail=lambda e: (self.b_tx.setEnabled(True), error(self, e)))


# ---------------------------------------------------------- Rapor doğrulama
class VerifyPage(Page):
    def __init__(self, win):
        super().__init__(win)
        v = QVBoxLayout(self); v.setContentsMargins(24, 16, 24, 16)
        v.addWidget(label(t('verify_drop'), 'h2', wrap=True))
        h = QHBoxLayout()
        h.addWidget(button('📄 ' + t('verify_file'), self.pick, primary=True))
        self.id = QLineEdit(); self.id.setPlaceholderText(t('verify_id')); self.id.returnPressed.connect(self.by_id); h.addWidget(self.id, 1)
        h.addWidget(button('✔', self.by_id))
        v.addLayout(h)
        self.out = QTextBrowser(); v.addWidget(self.out, 1)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls(): self.check_file(u.toLocalFile()); return

    def pick(self):
        p, _ = QFileDialog.getOpenFileName(self, t('verify_file'), '', 'Report (*.pdf *.docx)')
        if p: self.check_file(p)

    def check_file(self, p):
        from ..core.report import file_sha256
        sha = file_sha256(p); r = self.win.archive.find_report(sha=sha)
        self._out(r, t('verify_ok') if r else t('verify_bad'), f'SHA-256: {sha}')

    def by_id(self):
        x = self.id.text().strip()
        if not x: return
        if x.startswith(('PLA1|', 'PLACERT|')): x = x.split('|')[1]
        from ..core import exam as X
        c = X.find_certificate(self.win.archive, x)
        if c:
            ex = self.win.archive.rec_get('exam', c.get('exam_id', '')) or {}
            return self._out({k: c.get(k) for k in ('cert_id', 'student', 'score', 'total', 'pct', 'date') if k in c} | {'exam': ex.get('title', '')},
                             t('ver_cert', s=c['student'], e=ex.get('title', ''), p=int(round(c.get('pct', 0))), d=c.get('date', '')), '')
        r = self.win.archive.find_report(rid=x)
        self._out(r, t('verify_id_ok') if r else t('verify_bad'), '')

    def _out(self, r, msg, extra):
        col = '#4ADE80' if r else '#F87171'; d = 'rtl' if lang() == 'ar' else 'ltr'
        h = f'<div dir="{d}"><h2 style="color:{col}">{E(msg)}</h2><p style="color:#94A3B8">{E(extra)}</p>'
        if r:
            h += '<table cellpadding="5">' + ''.join(f'<tr><td style="color:#94A3B8">{E(k)}</td><td>{E(str(v))}</td></tr>' for k, v in r.items() if k != 'sha256') + '</table>'
        self.out.setHtml(h + '</div>')
