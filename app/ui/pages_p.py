"""Parametre Merkezi (Full Parameter List): bütün ArduPilot araç sınıfları, dosya inceleme, karşılaştırma, arşiv,
anahtar/yıldız işaretleri, öğretici kartlar ve yapay zekâ (online) / offline soru-cevap."""
from __future__ import annotations
import html, os, random
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QLineEdit, QCheckBox, QComboBox, QFileDialog, QSplitter, QTabWidget, QDialog,
                               QFormLayout, QPlainTextEdit, QListWidget, QListWidgetItem, QScrollArea, QGridLayout, QMessageBox)
from .i18n import t, lang
from .common import label, button, run_bg, error, info
from .pages_a import Page, _md
from ..core import pcenter as PC, pcritical as CR

E = html.escape
LI = {'tr': 0, 'en': 1, 'ar': 2}
ST_COL = {'changed': '#60A5FA', 'range': '#F87171', 'enum': '#F87171', 'bits': '#FBBF24', 'unknown': '#94A3B8', 'ro': '#94A3B8'}
SEV_COL = {2: '#F87171', 1: '#FBBF24', 0: '#93C5FD'}


def _it(txt, col=None, data=None, center=False):
    it = QTableWidgetItem('' if txt is None else str(txt))
    if col: it.setForeground(QBrush(QColor(col)))
    if data is not None: it.setData(Qt.UserRole, data)
    if center: it.setTextAlignment(Qt.AlignCenter)
    return it


def _tbl(headers, stretch):
    tb = QTableWidget(0, len(headers)); tb.setHorizontalHeaderLabels(headers)
    tb.verticalHeader().setVisible(False); tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tb.setSelectionBehavior(QAbstractItemView.SelectRows); tb.setAlternatingRowColors(True)
    tb.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)
    return tb


class ParamCenterPage(Page):
    def __init__(self, win):
        super().__init__(win)
        self.db = None; self.cur = {'params': {}, 'name': '', 'src': ''}; self.marks = {}
        self.names = []; self._loaded = False
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        top = QHBoxLayout()
        top.addWidget(label('🧩 ' + t('pc_title'), 'h1'))
        top.addSpacing(16); top.addWidget(label(t('pc_vehicle')))
        self.veh = QComboBox(); self.veh.setMinimumWidth(320); self.veh.currentIndexChanged.connect(self._veh_changed); top.addWidget(self.veh)
        top.addStretch(1)
        self.src_lbl = label('', 'muted'); top.addWidget(self.src_lbl)
        v.addLayout(top)
        self.cur_lbl = label('', 'muted', wrap=True); v.addWidget(self.cur_lbl)
        self.tabs = QTabWidget(); v.addWidget(self.tabs, 1)
        self._build_browse(); self._build_inspect(); self._build_compare(); self._build_archive(); self._build_learn(); self._build_ask()
        self._build_preflight(); self._build_tuning()

    # ================================================================ yükleme
    def on_show(self):
        if self._loaded: return
        self._loaded = True
        self.src_lbl.setText(t('loading'))
        run_bg(PC.PDB.get, on_done=self._ready, on_fail=lambda e: error(self, e))

    def _ready(self, db):
        self.db = db
        self.marks = PC.marks(self.win.archive)
        self.db.user_tx = self.win.settings.get('pc_ai_tx', {}) or {}
        lg = lang()
        self.veh.blockSignals(True); self.veh.clear()
        for vv in db.vehicles: self.veh.addItem(f'{PC.vname(vv, lg)}  ·  {db.count(vv)}', vv)
        want = self.win.settings.get('pc_vehicle') or (PC.vehicle_from_log(self.win.A.vehicle) if self.win.A else 'Plane')
        i = self.veh.findData(want); self.veh.setCurrentIndex(max(0, i)); self.veh.blockSignals(False)
        src = t('pc_src_full', d=db.built or '-') if db.full else t('pc_src_old')
        self.src_lbl.setText(src)
        self._veh_changed()
        if self.win.A and not self.cur['params']: self.from_log(silent=True)
        self._fill_archive()

    def vehicle(self):
        return self.veh.currentData() or 'Plane'

    def _veh_changed(self, *_):
        if not self.db: return
        self.win.settings['pc_vehicle'] = self.vehicle(); self.win.settings.save()
        g = self.grp; g.blockSignals(True); g.clear(); g.addItem(t('all'), '')
        lg = lang()
        for name, n in self.db.groups(self.vehicle()):
            g.addItem(f'{name} ({n}) — {self.db.group_text(name, lg)[:46]}', name)
        g.blockSignals(False)
        self.fill(); self._fill_learn_cats(); self._refresh_inspect()

    def on_analysis(self, A):
        if self.db: self.from_log(silent=True)
        self._tune_res = None
        if hasattr(self, 'tune_view'): self._refresh_tuning()

    # ================================================================ 1) Gezgin
    def _build_browse(self):
        w = QWidget(); v = QVBoxLayout(w)
        bar = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText(t('pc_search_ph')); self.q.textChanged.connect(self.fill); bar.addWidget(self.q, 2)
        self.grp = QComboBox(); self.grp.setMaximumWidth(380); self.grp.currentIndexChanged.connect(self.fill); bar.addWidget(self.grp, 1)
        self.flt = QComboBox()
        for k in ('all', 'star', 'key', 'crit', 'std', 'adv', 'inset', 'changed', 'risky', 'notes'): self.flt.addItem(t('pc_f_' + k), k)
        self.flt.currentIndexChanged.connect(self.fill); bar.addWidget(self.flt)
        self.cnt = label('', 'muted'); bar.addWidget(self.cnt)
        v.addLayout(bar)
        sp = QSplitter(Qt.Horizontal)
        self.tbl = _tbl(['⭐', '🔑', t('p_name'), t('p_desc'), t('pc_value'), t('pc_default'), t('pc_unit')], 3)
        self.tbl.currentCellChanged.connect(lambda r, *_: self._show(r))
        sp.addWidget(self.tbl)
        rw = QWidget(); rv = QVBoxLayout(rw); rv.setContentsMargins(6, 0, 0, 0)
        self.view = QTextBrowser(); self.view.setOpenExternalLinks(True); rv.addWidget(self.view, 3)
        # değer hesaplayıcı (seçenek / bitmask)
        self.calc_box = QScrollArea(); self.calc_box.setWidgetResizable(True); self.calc_box.setMaximumHeight(230)
        rv.addWidget(self.calc_box, 2)
        b1 = QHBoxLayout()
        self.b_star = button('⭐ ' + t('pc_star'), lambda: self._toggle('star')); b1.addWidget(self.b_star)
        self.b_key = button('🔑 ' + t('pc_key'), lambda: self._toggle('key')); b1.addWidget(self.b_key)
        b1.addWidget(button('📝 ' + t('pc_note'), self._note))
        rv.addLayout(b1)
        b2 = QHBoxLayout()
        b2.addWidget(button('🌐 ' + t('ai_translate'), self._ai_tx))
        b2.addWidget(button('🤖 ' + t('pc_ask_this'), self._ask_this, primary=True))
        rv.addLayout(b2)
        sp.addWidget(rw); sp.setSizes([820, 620])
        v.addWidget(sp, 1)
        self.tabs.addTab(w, '📚 ' + t('pc_tab_browse'))

    def _crit_set(self):
        return {p for _, p, _ in CR.critical(self.vehicle())}

    def fill(self, *_):
        if not self.db: return
        vv = self.vehicle(); db = self.db; q = self.q.text().strip(); g = self.grp.currentData(); f = self.flt.currentData()
        P = self.cur['params']; crit = self._crit_set()
        if q:
            names = [k for k, _ in PC.search(q, vv, 600)]
        else:
            names = db.names(vv)
        out = []
        risky = {x.get('param') for x in self._risks} if f == 'risky' else set()
        for k in names:
            m = db.P[k]
            if g and m.get('g') != g: continue
            mk = self.marks.get(k, {})
            if f == 'star' and not mk.get('star'): continue
            if f == 'key' and not (mk.get('key') or k in crit): continue
            if f == 'crit' and k not in crit: continue
            if f == 'std' and m.get('usr') != 'Standard': continue
            if f == 'adv' and m.get('usr') == 'Standard': continue
            if f == 'inset' and k not in P: continue
            if f == 'notes' and not (mk.get('note') or mk.get('cat')): continue
            if f == 'changed':
                d = db.default(k, vv)
                if k not in P or not isinstance(d, (int, float)) or abs(float(d) - P[k]) < 1e-6 * max(1, abs(float(d))): continue
            if f == 'risky' and k not in risky: continue
            out.append(k)
        self.names = out[:4000]
        lg = lang()
        self.tbl.setUpdatesEnabled(False); self.tbl.setRowCount(len(self.names))
        for i, k in enumerate(self.names):
            m = db.meta(k, vv) or {}; mk = self.marks.get(k, {})
            dn, _d, src = db.text(k, vv, lg)
            self.tbl.setItem(i, 0, _it('⭐' if mk.get('star') else '', center=True))
            self.tbl.setItem(i, 1, _it('🔑' if mk.get('key') else ('🗝' if k in crit else ''), center=True))
            self.tbl.setItem(i, 2, _it(k, '#93C5FD' if m.get('usr') == 'Standard' else None))
            self.tbl.setItem(i, 3, _it(dn))
            val = P.get(k); d = m.get('default')
            ch = val is not None and isinstance(d, (int, float)) and abs(float(d) - val) > 1e-6 * max(1, abs(float(d)))
            self.tbl.setItem(i, 4, _it(PC.fmt(val), '#FBBF24' if ch else None))
            self.tbl.setItem(i, 5, _it(PC.fmt(d)))
            self.tbl.setItem(i, 6, _it(m.get('u', '')))
        self.tbl.setUpdatesEnabled(True)
        for c in (0, 1): self.tbl.setColumnWidth(c, 34)
        self.tbl.resizeColumnToContents(2)
        self.cnt.setText(t('count', n=len(out)))
        if self.names: self.tbl.setCurrentCell(0, 2); self._show(0)
        else: self.view.setHtml('')

    def goto_param(self, name):
        self.tabs.setCurrentIndex(0)
        self.flt.setCurrentIndex(0); self.grp.setCurrentIndex(0); self.q.setText(name)
        if name in self.names:
            r = self.names.index(name); self.tbl.setCurrentCell(r, 2); self._show(r)

    def _cur_name(self):
        r = self.tbl.currentRow()
        return self.names[r] if 0 <= r < len(self.names) else None

    def _show(self, r):
        if not self.db or not (0 <= r < len(self.names)): return
        k = self.names[r]; vv = self.vehicle(); db = self.db; lg = lang(); d_ = 'rtl' if lg == 'ar' else 'ltr'
        m = db.meta(k, vv) or {}; dn, desc, src = db.text(k, vv, lg); mk = self.marks.get(k, {})
        val = self.cur['params'].get(k)
        h = [f'<div dir="{d_}"><h2 style="color:#93C5FD">{"⭐ " if mk.get("star") else ""}{"🔑 " if mk.get("key") else ""}{E(k)}</h2>',
             f'<p style="font-size:12pt"><b>{E(dn)}</b></p><p style="font-size:10.5pt">{E(desc)}</p>']
        if src == 'mt': h.append(f'<p style="color:#64748B;font-size:8.5pt">{E(t("pc_src_mt"))}</p>')
        if src == 'ai': h.append(f'<p style="color:#64748B;font-size:8.5pt">{E(t("pc_src_ai"))}</p>')
        if lg != 'en' and m.get('d'): h.append(f'<p style="color:#94A3B8;font-size:9pt"><b>EN:</b> {E(m.get("dn", ""))} — {E(m["d"])}</p>')
        cat, why = CR.why(k, lg)
        if why: h.append(f'<p style="background:#1E293B;padding:6px;color:#FDE68A">🗝 <b>{E(t("pc_why"))}</b> {E(why)}</p>')
        rows = []
        if val is not None:
            lab = PC.value_label(val, m.get('vals'))
            rows.append((t('pc_value'), f'<b style="color:#FBBF24">{E(PC.fmt(val))}</b>' + (f' = {E(db.lbl(lab, lg))}' if lab else '')))
        if m.get('default') is not None:
            lab = PC.value_label(m['default'], m.get('vals'))
            rows.append((t('pc_default'), E(PC.fmt(m['default'])) + (f' = {E(db.lbl(lab, lg))}' if lab else '') + f' <span style="color:#64748B">({E(t("pc_def_note"))})</span>'))
        if m.get('u'): rows.append((t('pc_unit'), E(m['u'])))
        if m.get('r'): rows.append((t('pc_range'), f'{E(PC.fmt(m["r"][0]))} … {E(PC.fmt(m["r"][1]))}'))
        if m.get('inc') is not None: rows.append((t('pc_inc'), E(PC.fmt(m['inc']))))
        rows.append((t('pc_level'), E({'Standard': t('pc_std'), 'Advanced': t('pc_adv')}.get(m.get('usr'), m.get('usr') or '-'))))
        if m.get('rb'): rows.append(('⚠', E(t('pc_reboot'))))
        if m.get('ro'): rows.append(('🔒', E(t('pc_readonly'))))
        rows.append((t('pc_vehicles'), E(', '.join(m.get('v', [])))))
        h.append('<table cellpadding="3">' + ''.join(f'<tr><td style="color:#94A3B8">{E(a)}</td><td>{b}</td></tr>' for a, b in rows) + '</table>')
        if m.get('vals'):
            h.append(f'<p><b>{E(t("pc_options"))}</b></p><table cellpadding="2">')
            for kk, lab in m['vals'].items():
                on = val is not None and PC._num(kk) is not None and abs(PC._num(kk) - val) < 1e-6
                tl = db.lbl(lab, lg)
                h.append(f'<tr><td style="color:{"#FBBF24" if on else "#93C5FD"}"><b>{E(kk)}</b></td><td>{"▶ " if on else ""}{E(tl)}'
                         + (f' <span style="color:#64748B">({E(lab)})</span>' if tl != lab else '') + '</td></tr>')
            h.append('</table>')
        if m.get('bits'):
            h.append(f'<p><b>{E(t("pc_bits"))}</b></p><table cellpadding="2">')
            for b, lab, on in PC.decode_bits(val, m['bits']):
                tl = db.lbl(lab, lg)
                h.append(f'<tr><td style="color:{"#34D399" if on else "#64748B"}">{"☑" if on else "☐"} bit {b} (={1 << b})</td><td>{E(tl)}'
                         + (f' <span style="color:#64748B">({E(lab)})</span>' if tl != lab else '') + '</td></tr>')
            h.append('</table>')
        if mk.get('cat') or mk.get('note'):
            h.append(f'<p style="background:#172033;padding:6px">📝 <b>{E(mk.get("cat", ""))}</b> {E(mk.get("note", ""))}</p>')
        h.append(f'<p><a href="https://ardupilot.org/{ {"Plane": "plane", "Copter": "copter", "Heli": "copter", "Rover": "rover", "Sub": "sub", "Blimp": "blimp", "Tracker": "antennatracker", "Periph": "dev"}.get(vv, "plane") }/docs/parameters.html#{k.lower().replace("_", "-")}" '
                 f'style="color:#60A5FA">ardupilot.org ↗</a></p></div>')
        self.view.setHtml(''.join(h))
        self._calc(k, m, val)

    # ---- seçenek / bitmask hesaplayıcı
    def _calc(self, k, m, val):
        w = QWidget(); w.setObjectName('calc'); w.setStyleSheet('#calc { background: #0F1A30; }')
        g = QGridLayout(w); g.setContentsMargins(4, 4, 4, 4); g.setAlignment(Qt.AlignTop)
        lg = lang()
        self._calc_val = val
        res = label('', 'h2')
        if m.get('bits'):
            g.addWidget(label(t('pc_calc_bits'), 'muted', wrap=True), 0, 0, 1, 2)
            boxes = []
            for i, (b, lab, on) in enumerate(PC.decode_bits(val, m['bits'])):
                cb = QCheckBox(f'{b}: {self.db.lbl(lab, lg)}'); cb.setChecked(on); cb.bit = b; boxes.append(cb)
                g.addWidget(cb, 1 + i // 2, i % 2)

            def upd():
                s = sum(1 << c.bit for c in boxes if c.isChecked() and c.bit >= 0)
                self._calc_val = s; res.setText(f'{k} = {s}')
            for c in boxes: c.toggled.connect(upd)
            upd()
        elif m.get('vals'):
            g.addWidget(label(t('pc_calc_vals'), 'muted', wrap=True), 0, 0, 1, 2)
            cb = QComboBox()
            for kk, lab in m['vals'].items(): cb.addItem(f'{kk} = {self.db.lbl(lab, lg)}', PC._num(kk))
            if val is not None:
                for i in range(cb.count()):
                    if cb.itemData(i) is not None and abs(cb.itemData(i) - val) < 1e-6: cb.setCurrentIndex(i)

            def upd2(*_):
                self._calc_val = cb.currentData(); res.setText(f'{k} = {PC.fmt(cb.currentData())}')
            cb.currentIndexChanged.connect(upd2); upd2()
            g.addWidget(cb, 1, 0, 1, 2)
        else:
            g.addWidget(label(t('pc_calc_num'), 'muted', wrap=True), 0, 0, 1, 2)
            ed = QLineEdit(PC.fmt(val) if val is not None else PC.fmt(m.get('default')))

            def upd3(*_):
                self._calc_val = PC._num(ed.text().replace(',', '.'))
                c = PC.check_value(self._calc_val, m) if self._calc_val is not None else None
                res.setText(f'{k} = {PC.fmt(self._calc_val)}' + ('   ⚠ ' + t('pc_out_range') if c == 'range' else ''))
            ed.textChanged.connect(upd3); upd3(); g.addWidget(ed, 1, 0, 1, 2)
        row = g.rowCount()
        g.addWidget(res, row, 0)
        g.addWidget(button('✔ ' + t('pc_apply_set'), lambda: self._apply_val(k)), row, 1)
        self.calc_box.setWidget(w)

    def _apply_val(self, k):
        if self._calc_val is None: return
        self.cur['params'][k] = float(self._calc_val)
        if not self.cur['name']: self.cur['name'] = t('pc_new_set'); self.cur['src'] = 'edit'
        self._cur_changed(); r = self.tbl.currentRow(); self.fill()
        if k in self.names: self.tbl.setCurrentCell(self.names.index(k), 2)
        self.win.set_status(t('pc_applied', k=k, v=PC.fmt(self._calc_val)))

    # ---- işaretler
    def _toggle(self, what):
        k = self._cur_name()
        if not k: return
        cur = self.marks.get(k, {})
        r = PC.set_mark(self.win.archive, k, **{what: not cur.get(what)})
        if r: self.marks[k] = r
        else: self.marks.pop(k, None)
        row = self.tbl.currentRow()
        self.tbl.setItem(row, 0, _it('⭐' if (r or {}).get('star') else '', center=True))
        self.tbl.setItem(row, 1, _it('🔑' if (r or {}).get('key') else ('🗝' if k in self._crit_set() else ''), center=True))
        self._show(row); self._fill_learn_cats()

    def _note(self):
        k = self._cur_name()
        if not k: return
        cur = self.marks.get(k, {})
        dl = QDialog(self); dl.setWindowTitle(f'📝 {k}'); dl.setMinimumWidth(460); f = QFormLayout(dl)
        cats = sorted({m.get('cat') for m in self.marks.values() if m.get('cat')})
        cat = QComboBox(); cat.setEditable(True); cat.addItems([''] + cats); cat.setCurrentText(cur.get('cat', ''))
        f.addRow(t('pc_cat'), cat)
        note = QPlainTextEdit(cur.get('note', '')); note.setMinimumHeight(110); f.addRow(t('pc_note'), note)
        star = QCheckBox('⭐ ' + t('pc_star')); star.setChecked(bool(cur.get('star'))); f.addRow(star)
        key = QCheckBox('🔑 ' + t('pc_key')); key.setChecked(bool(cur.get('key'))); f.addRow(key)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted: return
        r = PC.set_mark(self.win.archive, k, cat=cat.currentText().strip(), note=note.toPlainText().strip(), star=star.isChecked(), key=key.isChecked())
        if r: self.marks[k] = r
        else: self.marks.pop(k, None)
        self._show(self.tbl.currentRow()); self._fill_learn_cats()

    # ---- yapay zekâ
    def _ai_tx(self):
        k = self._cur_name(); lg = lang()
        if not k or lg == 'en': return
        from ..core import ai as AI
        s = self.win.settings
        m = self.db.meta(k, self.vehicle()) or {}

        def job():
            from ..core import ceviri as CV
            return CV.translate_text(f"{m.get('dn', '')}\n|||\n{m.get('d', '')}", 'en', lg, s, self.win.usage)[0]

        def ok(out):
            parts = out.split('|||')
            v_ = [parts[0].strip(), (parts[1] if len(parts) > 1 else '').strip()]
            s.setdefault('pc_ai_tx', {}).setdefault(lg, {})[k] = v_; s.save()
            self.db.user_tx = s['pc_ai_tx']; self.db._blob.pop((k, self.vehicle()), None)
            self._show(self.tbl.currentRow())
        self.win.set_status(t('pc_working'))
        run_bg(job, on_done=ok, on_fail=lambda e: error(self, e))

    def _ask_this(self):
        k = self._cur_name()
        if not k: return
        self.tabs.setCurrentIndex(5)
        self.ask_q.setPlainText(t('pc_ask_tpl', k=k)); self.ask(names=[k])

    # ================================================================ 2) Dosya inceleme
    def _build_inspect(self):
        w = QWidget(); v = QVBoxLayout(w)
        bar = QHBoxLayout()
        bar.addWidget(button('📂 ' + t('pc_open_file'), self.open_file, primary=True))
        bar.addWidget(button('🛩 ' + t('pc_from_log'), self.from_log))
        bar.addWidget(button('💾 ' + t('pc_save_arch'), self.save_archive))
        bar.addWidget(button('⬇ ' + t('pc_export'), self.export_cur))
        bar.addWidget(button('📄 ' + t('pc_report'), self.report_cur))
        bar.addStretch(1)
        self.only_changed = QCheckBox(t('pc_only_changed')); self.only_changed.toggled.connect(self._refresh_inspect); bar.addWidget(self.only_changed)
        v.addLayout(bar)
        sp = QSplitter(Qt.Vertical)
        self.risk_view = QTextBrowser(); sp.addWidget(self.risk_view)
        self.itbl = _tbl([t('p_name'), t('pc_value'), t('pc_default'), t('pc_status'), t('p_desc')], 4)
        self.itbl.cellDoubleClicked.connect(lambda r, c: self.goto_param(self.itbl.item(r, 0).text()))
        sp.addWidget(self.itbl); sp.setSizes([260, 600])
        v.addWidget(sp, 1)
        self.tabs.addTab(w, '📂 ' + t('pc_tab_inspect'))
        self._risks = []

    def _set_cur(self, params, name, src, vehicle=None):
        self.cur = {'params': dict(params), 'name': name, 'src': src}
        if self.db:
            vv = PC.detect_vehicle(params, vehicle)
            i = self.veh.findData(vv)
            if i >= 0 and i != self.veh.currentIndex():
                self.veh.setCurrentIndex(i); self._cur_changed(); return
        self._cur_changed(); self.fill()

    def _cur_changed(self):
        c = self.cur
        self.cur_lbl.setText(t('pc_cur', n=c['name'] or '-', c=len(c['params'])) if c['params'] else t('pc_cur_none'))
        self._refresh_inspect(); self._refresh_preflight()

    def open_file(self):
        p, _ = QFileDialog.getOpenFileName(self, t('pc_open_file'), '', 'ArduPilot params (*.param *.parm *.params *.txt *.csv);;All (*.*)')
        if not p: return
        d = PC.read_file(p)
        if not d: return error(self, t('pc_bad_file'))
        self._set_cur(d, os.path.basename(p), 'file')
        self.tabs.setCurrentIndex(1)

    def from_log(self, silent=False):
        A = self.win.A
        if not A or not A.L.params:
            if not silent: error(self, t('no_log'))
            return
        self._set_cur(A.L.params, os.path.basename(A.L.path), 'log', PC.vehicle_from_log(A.vehicle))

    def _refresh_inspect(self, *_):
        if not self.db: return
        vv = self.vehicle(); P = self.cur['params']; lg = lang(); d_ = 'rtl' if lg == 'ar' else 'ltr'
        if not P:
            self.risk_view.setHtml(f'<div dir="{d_}"><p>{E(t("pc_inspect_help"))}</p></div>'); self.itbl.setRowCount(0); self._risks = []; return
        rows = PC.inspect(P, vv); self._risks = PC.risks(P, vv, lg)
        n_ch = sum('changed' in r['st'] for r in rows); n_unk = sum('unknown' in r['st'] for r in rows)
        n_bad = sum(any(s in r['st'] for s in ('range', 'enum', 'bits')) for r in rows)
        h = [f'<div dir="{d_}"><h3 style="color:#93C5FD">{E(self.cur["name"])} · {E(PC.vname(vv, lg))}</h3>',
             f'<p>{E(t("pc_summary", n=len(rows), ch=n_ch, u=n_unk, b=n_bad, r=sum(1 for x in self._risks if x["sev"] >= 1)))}</p>']
        if self._risks:
            h.append('<ul>')
            for x in self._risks:
                h.append(f'<li style="color:{SEV_COL.get(x["sev"], "#CBD5E1")}">{"⛔" if x["sev"] >= 2 else "⚠" if x["sev"] == 1 else "ℹ"} {E(x["text"])}</li>')
            h.append('</ul>')
        else:
            h.append(f'<p style="color:#34D399">✔ {E(t("pc_no_risk"))}</p>')
        h.append('</div>')
        self.risk_view.setHtml(''.join(h))
        if self.only_changed.isChecked(): rows = [r for r in rows if r['st'] and r['st'] != ['ro']]
        self.itbl.setUpdatesEnabled(False); self.itbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            st = r['st']; col = ST_COL.get(st[0]) if st else None
            dn = self.db.text(r['name'], vv, lg)[0] if 'unknown' not in st else ''
            self.itbl.setItem(i, 0, _it(r['name'], col))
            self.itbl.setItem(i, 1, _it(PC.fmt(r['value']), col))
            self.itbl.setItem(i, 2, _it(PC.fmt(r['default'])))
            self.itbl.setItem(i, 3, _it(', '.join(t('pc_st_' + s) for s in st), col))
            self.itbl.setItem(i, 4, _it(dn))
        self.itbl.setUpdatesEnabled(True); self.itbl.resizeColumnToContents(0)

    def save_archive(self):
        if not self.cur['params']: return error(self, t('pc_cur_none'))
        dl = QDialog(self); dl.setWindowTitle('💾 ' + t('pc_save_arch')); dl.setMinimumWidth(460); f = QFormLayout(dl)
        nm = QLineEdit(os.path.splitext(self.cur['name'])[0]); f.addRow(t('fl_name'), nm)
        ac = QComboBox(); ac.setEditable(True)
        ac.addItems([''] + [a.get('name', '') for a in self.win.archive.rec_list('aircraft')])
        f.addRow(t('pc_aircraft'), ac)
        note = QPlainTextEdit(); note.setMaximumHeight(90); f.addRow(t('pc_note'), note)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted: return
        PC.save_pset(self.win.archive, self.cur['params'], nm.text().strip() or self.cur['name'], self.vehicle(), note.toPlainText().strip(),
                     ac.currentText().strip(), self.cur['src'])
        self._fill_archive(); self.win.set_status(t('saved_archive'))

    def _export(self, params, name):
        p, flt = QFileDialog.getSaveFileName(self, t('pc_export'), os.path.splitext(name or 'params')[0] + '.param',
                                             'Mission Planner (*.param);;QGroundControl (*.params);;CSV (*.csv)')
        if not p: return
        fm = 'qgc' if p.lower().endswith('.params') or 'QGround' in flt else 'csv' if p.lower().endswith('.csv') or 'CSV' in flt else 'mp'
        PC.write_file(params, p, fm, self.vehicle(), name)
        info(self, t('pc_exported', p=p))

    def export_cur(self):
        if not self.cur['params']: return error(self, t('pc_cur_none'))
        self._export(self.cur['params'], self.cur['name'])

    def report_cur(self):
        if not self.cur['params']: return error(self, t('pc_cur_none'))
        p, _ = QFileDialog.getSaveFileName(self, t('pc_report'), os.path.splitext(self.cur['name'] or 'params')[0] + '_param_raporu.pdf', 'PDF (*.pdf)')
        if not p: return
        from ..core import textbook
        lh = self.win.settings.letterhead(); lg = lang(); P = dict(self.cur['params']); vv = self.vehicle(); nm = self.cur['name']
        run_bg(textbook.param_report, P, vv, nm, lg, p, lh, on_done=lambda r: (info(self, t('pc_exported', p=p))), on_fail=lambda e: error(self, e))

    # ================================================================ 3) Karşılaştırma
    def _build_compare(self):
        w = QWidget(); v = QVBoxLayout(w)
        bar = QHBoxLayout()
        self.ca = QComboBox(); self.cb = QComboBox()
        for c in (self.ca, self.cb): c.setMinimumWidth(280)
        bar.addWidget(label('A:')); bar.addWidget(self.ca); bar.addWidget(button('📂', lambda: self._cmp_file(self.ca)))
        bar.addSpacing(10)
        bar.addWidget(label('B:')); bar.addWidget(self.cb); bar.addWidget(button('📂', lambda: self._cmp_file(self.cb)))
        bar.addWidget(button('⚖ ' + t('pc_compare'), self.compare, primary=True))
        self.c_diff = QCheckBox(t('pc_only_diff')); self.c_diff.setChecked(True); self.c_diff.toggled.connect(self.compare); bar.addWidget(self.c_diff)
        bar.addStretch(1)
        v.addLayout(bar)
        self.c_sum = label('', 'muted', wrap=True); v.addWidget(self.c_sum)
        self.ctbl = _tbl([t('p_name'), 'A', 'B', t('pc_status'), t('p_desc')], 4)
        self.ctbl.cellDoubleClicked.connect(lambda r, c: self.goto_param(self.ctbl.item(r, 0).text()))
        v.addWidget(self.ctbl, 1)
        self.tabs.addTab(w, '⚖ ' + t('pc_tab_compare'))
        self._files = {}

    def _cmp_sources(self):
        out = [('cur', t('pc_src_cur'))]
        if self.win.A and self.win.A.L.params: out.append(('log', t('pc_src_log') + ': ' + os.path.basename(self.win.A.L.path)))
        out.append(('def', t('pc_src_def')))
        for s in PC.psets(self.win.archive): out.append(('set:' + s['id'], f"🗄 {s.get('date', '')} · {s.get('name', '')} ({s.get('n', 0)})"))
        for k, (n, _) in self._files.items(): out.append(('file:' + k, '📂 ' + n))
        return out

    def _fill_cmp(self):
        for c in (self.ca, self.cb):
            cur = c.currentData(); c.blockSignals(True); c.clear()
            for k, n in self._cmp_sources(): c.addItem(n, k)
            i = c.findData(cur); c.setCurrentIndex(max(0, i)); c.blockSignals(False)

    def _cmp_file(self, combo):
        p, _ = QFileDialog.getOpenFileName(self, t('pc_open_file'), '', 'ArduPilot params (*.param *.parm *.params *.txt *.csv);;All (*.*)')
        if not p: return
        d = PC.read_file(p)
        if not d: return error(self, t('pc_bad_file'))
        k = str(len(self._files) + 1); self._files[k] = (os.path.basename(p), d)
        self._fill_cmp(); combo.setCurrentIndex(combo.findData('file:' + k))

    def _src_params(self, key):
        if key == 'cur': return self.cur['params']
        if key == 'log': return self.win.A.L.params if self.win.A else {}
        if key == 'def':
            vv = self.vehicle(); keys = set(self.cur['params']) or set(self.db.names(vv))
            return {k: float(self.db.default(k, vv)) for k in keys if isinstance(self.db.default(k, vv), (int, float))}
        if key and key.startswith('set:'):
            r = self.win.archive.rec_get('pset', key[4:]); return (r or {}).get('params', {})
        if key and key.startswith('file:'): return self._files.get(key[5:], ('', {}))[1]
        return {}

    def compare(self, *_):
        if not self.db: return
        a = self._src_params(self.ca.currentData()); b = self._src_params(self.cb.currentData())
        rows = PC.compare(a, b); vv = self.vehicle(); lg = lang()
        n = {s: sum(1 for r in rows if r['st'] == s) for s in ('diff', 'only_a', 'only_b', 'same')}
        self.c_sum.setText(t('pc_cmp_sum', d=n['diff'], a=n['only_a'], b=n['only_b'], s=n['same']))
        if self.c_diff.isChecked(): rows = [r for r in rows if r['st'] != 'same']
        col = {'diff': '#FBBF24', 'only_a': '#60A5FA', 'only_b': '#A78BFA'}
        self.ctbl.setUpdatesEnabled(False); self.ctbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            c = col.get(r['st'])
            self.ctbl.setItem(i, 0, _it(r['name'], c)); self.ctbl.setItem(i, 1, _it(PC.fmt(r['a'])))
            self.ctbl.setItem(i, 2, _it(PC.fmt(r['b']))); self.ctbl.setItem(i, 3, _it(t('pc_cmp_' + r['st']), c))
            self.ctbl.setItem(i, 4, _it(self.db.text(r['name'], vv, lg)[0] if self.db.P.get(r['name']) else ''))
        self.ctbl.setUpdatesEnabled(True); self.ctbl.resizeColumnToContents(0)

    # ================================================================ 4) Arşiv
    def _build_archive(self):
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(label(t('pc_arch_help'), 'muted', wrap=True))
        bar = QHBoxLayout()
        for txt, fn in (('📂 ' + t('pc_load'), self.arch_load), ('⬇ ' + t('pc_restore'), self.arch_export), ('📝 ' + t('pc_note'), self.arch_note),
                        ('⚖ A', lambda: self.arch_cmp('a')), ('⚖ B', lambda: self.arch_cmp('b')), ('🗑 ' + t('fl_del'), self.arch_del)):
            bar.addWidget(button(txt, fn))
        bar.addStretch(1); v.addLayout(bar)
        self.atbl = _tbl([t('pc_date'), t('fl_name'), t('pc_vehicle'), t('pc_aircraft'), t('pc_count'), t('pc_note')], 5)
        self.atbl.cellDoubleClicked.connect(lambda *_: self.arch_load())
        v.addWidget(self.atbl, 1)
        self.tabs.addTab(w, '🗄 ' + t('pc_tab_archive'))
        self._sets = []

    def _fill_archive(self):
        self._sets = PC.psets(self.win.archive)
        self.atbl.setRowCount(len(self._sets))
        for i, s in enumerate(self._sets):
            for j, x in enumerate((s.get('date'), s.get('name'), s.get('vehicle'), s.get('aircraft'), s.get('n'), s.get('note'))):
                self.atbl.setItem(i, j, _it(x))
        self.atbl.resizeColumnsToContents()
        self._fill_cmp()

    def _sel_set(self):
        r = self.atbl.currentRow()
        return self._sets[r] if 0 <= r < len(self._sets) else None

    def arch_load(self):
        s = self._sel_set()
        if s: self._set_cur(s.get('params', {}), s.get('name', ''), 'archive', s.get('vehicle')); self.tabs.setCurrentIndex(1)

    def arch_export(self):
        s = self._sel_set()
        if s: self._export(s.get('params', {}), s.get('name', ''))

    def arch_note(self):
        s = self._sel_set()
        if not s: return
        dl = QDialog(self); dl.setWindowTitle('📝'); dl.setMinimumWidth(420); f = QFormLayout(dl)
        nm = QLineEdit(s.get('name', '')); f.addRow(t('fl_name'), nm)
        ac = QLineEdit(s.get('aircraft', '')); f.addRow(t('pc_aircraft'), ac)
        note = QPlainTextEdit(s.get('note', '')); f.addRow(t('pc_note'), note)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted: return
        s = dict(s); s.update(name=nm.text().strip(), aircraft=ac.text().strip(), note=note.toPlainText().strip()); rid = s.pop('id')
        self.win.archive.rec_put('pset', rid, s); self._fill_archive()

    def arch_cmp(self, side):
        s = self._sel_set()
        if not s: return
        c = self.ca if side == 'a' else self.cb
        c.setCurrentIndex(max(0, c.findData('set:' + s['id'])))
        self.tabs.setCurrentIndex(2); self.compare()

    def arch_del(self):
        s = self._sel_set()
        if not s: return
        if QMessageBox.question(self, '🗑', t('fl_del_q', n=s.get('name', ''))) != QMessageBox.Yes: return
        self.win.archive.rec_del('pset', s['id']); self._fill_archive()

    # ================================================================ 5) Öğren (anahtar parametreler)
    def _build_learn(self):
        w = QWidget(); h = QHBoxLayout(w)
        lv = QVBoxLayout()
        lv.addWidget(label(t('pc_learn_help'), 'muted', wrap=True))
        self.cats = QListWidget(); self.cats.setMaximumWidth(330); self.cats.currentRowChanged.connect(self._learn_cat); lv.addWidget(self.cats, 1)
        h.addLayout(lv)
        mid = QVBoxLayout()
        self.lst = QListWidget(); self.lst.currentRowChanged.connect(self._learn_show); mid.addWidget(self.lst, 1)
        fb = QHBoxLayout()
        fb.addWidget(button('🎴 ' + t('pc_card'), self.card))
        self.b_reveal = button('👁 ' + t('pc_reveal'), self._reveal); fb.addWidget(self.b_reveal)
        fb.addWidget(button('📚 ' + t('pc_open_lib'), lambda: self.goto_param(self.lst.currentItem().data(Qt.UserRole)) if self.lst.currentItem() else None))
        mid.addLayout(fb)
        h.addLayout(mid, 1)
        self.lview = QTextBrowser(); h.addWidget(self.lview, 2)
        self.tabs.addTab(w, '🔑 ' + t('pc_tab_learn'))
        self._cat_keys = []; self._hidden = False

    def _fill_learn_cats(self):
        if not self.db: return
        lg = lang(); cur = self.cats.currentRow()
        self.cats.blockSignals(True); self.cats.clear(); self._cat_keys = []
        crit = CR.critical(self.vehicle())
        for c, nm in CR.CATS.items():
            n = sum(1 for cc, _, _ in crit if cc == c)
            if n: self.cats.addItem(f'🗝 {nm[LI.get(lg, 0)]} ({n})'); self._cat_keys.append(('crit', c))
        mine_star = [k for k, m in self.marks.items() if m.get('star')]; mine_key = [k for k, m in self.marks.items() if m.get('key')]
        self.cats.addItem(f'⭐ {t("pc_my_star")} ({len(mine_star)})'); self._cat_keys.append(('star', None))
        self.cats.addItem(f'🔑 {t("pc_my_key")} ({len(mine_key)})'); self._cat_keys.append(('key', None))
        for c in sorted({m.get('cat') for m in self.marks.values() if m.get('cat')}):
            self.cats.addItem(f'📁 {c} ({sum(1 for m in self.marks.values() if m.get("cat") == c)})'); self._cat_keys.append(('cat', c))
        self.cats.blockSignals(False)
        self.cats.setCurrentRow(cur if 0 <= cur < self.cats.count() else 0)

    def _learn_names(self, i):
        if not (0 <= i < len(self._cat_keys)): return []
        kind, c = self._cat_keys[i]; vv = self.vehicle()
        if kind == 'crit': return [p for cc, p, _ in CR.critical(vv) if cc == c and self.db.P.get(p)]
        if kind == 'star': return sorted(k for k, m in self.marks.items() if m.get('star'))
        if kind == 'key': return sorted(k for k, m in self.marks.items() if m.get('key'))
        return sorted(k for k, m in self.marks.items() if m.get('cat') == c)

    def _learn_cat(self, i):
        self.lst.blockSignals(True); self.lst.clear()
        lg = lang(); vv = self.vehicle()
        for k in self._learn_names(i):
            dn = self.db.text(k, vv, lg)[0] if self.db.P.get(k) else ''
            it = QListWidgetItem(f'{k}  —  {dn}'); it.setData(Qt.UserRole, k); self.lst.addItem(it)
        self.lst.blockSignals(False)
        if self.lst.count(): self.lst.setCurrentRow(0)
        else: self.lview.setHtml('')

    def _learn_show(self, r, hidden=False):
        it = self.lst.item(r)
        if not it: return
        k = it.data(Qt.UserRole); vv = self.vehicle(); lg = lang(); d_ = 'rtl' if lg == 'ar' else 'ltr'
        m = self.db.meta(k, vv) or {}; dn, desc, _ = self.db.text(k, vv, lg); cat, why = CR.why(k, lg); mk = self.marks.get(k, {})
        if hidden:
            self.lview.setHtml(f'<div dir="{d_}" style="text-align:center"><h1 style="color:#FBBF24">{E(k)}</h1><p style="font-size:12pt">{E(t("pc_card_q"))}</p></div>'); return
        h = [f'<div dir="{d_}"><h2 style="color:#93C5FD">{E(k)}</h2><p style="font-size:12pt"><b>{E(dn)}</b></p>']
        if why: h.append(f'<p style="background:#1E293B;padding:6px;color:#FDE68A">🗝 <b>{E(t("pc_why"))}</b> {E(why)}</p>')
        h.append(f'<p>{E(desc)}</p>')
        if m.get('default') is not None: h.append(f'<p>{E(t("pc_default"))}: <b>{E(PC.fmt(m["default"]))}</b> {E(m.get("u", ""))}</p>')
        if m.get('vals'):
            h.append('<p>' + '<br>'.join(f'<b>{E(kk)}</b> = {E(self.db.lbl(v_, lg))}' for kk, v_ in list(m['vals'].items())[:20]) + '</p>')
        val = self.cur['params'].get(k)
        if val is not None: h.append(f'<p>{E(t("pc_value"))}: <b style="color:#FBBF24">{E(PC.fmt(val))}</b></p>')
        if mk.get('note'): h.append(f'<p style="background:#172033;padding:6px">📝 {E(mk["note"])}</p>')
        h.append('</div>')
        self.lview.setHtml(''.join(h))

    def card(self):
        n = self.lst.count()
        if not n: return
        self.lst.blockSignals(True); r = random.randrange(n); self.lst.setCurrentRow(r); self.lst.blockSignals(False)
        self._hidden = True; self._learn_show(r, hidden=True)

    def _reveal(self):
        self._hidden = False; self._learn_show(self.lst.currentRow())

    # ================================================================ 6) Sor (YZ / offline)
    def _build_ask(self):
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(label(t('pc_ask_help'), 'muted', wrap=True))
        ex = QHBoxLayout()
        for q in t('pc_examples').split('|'):
            b = button(q, lambda _=False, q=q: (self.ask_q.setPlainText(q), self.ask())); ex.addWidget(b)
        ex.addStretch(1); v.addLayout(ex)
        h = QHBoxLayout()
        self.ask_q = QPlainTextEdit(); self.ask_q.setMaximumHeight(80); self.ask_q.setPlaceholderText(t('pc_ask_ph')); h.addWidget(self.ask_q, 1)
        bv = QVBoxLayout()
        self.b_ask = button('🤖 ' + t('pc_ask_btn'), self.ask, primary=True); bv.addWidget(self.b_ask)
        self.offl = QCheckBox(t('pc_offline')); bv.addWidget(self.offl)
        h.addLayout(bv); v.addLayout(h)
        self.ans = QTextBrowser(); self.ans.setOpenLinks(False); self.ans.anchorClicked.connect(lambda u: self.goto_param(u.toString().split(':')[-1]))
        v.addWidget(self.ans, 1)
        self.tabs.addTab(w, '🤖 ' + t('pc_tab_ask'))

    def ask(self, names=None):
        q = self.ask_q.toPlainText().strip()
        if not q or not self.db: return
        vv = self.vehicle(); lg = lang(); d_ = 'rtl' if lg == 'ar' else 'ltr'
        from ..core import ai as AI
        s = self.win.settings
        cur = self.cur['params'] or None
        off = PC.offline_answer(q, vv, lg, names)
        ctx_names = names or [k for k, _ in PC.search(q, vv, 8)]
        links = ' · '.join(f'<a href="p:{k}" style="color:#60A5FA">{E(k)}</a>' for k in ctx_names)

        def show(txt, online):
            tag = t('pc_ans_online') if online else t('pc_ans_offline')
            self.ans.setHtml(f'<div dir="{d_}"><p style="color:#64748B">{E(tag)}</p>{_md(txt)}<hr><p>{E(t("pc_related"))}: {links}</p></div>')
            self.b_ask.setEnabled(True)
        if self.offl.isChecked() or not AI.available(s):
            show(off, False); return
        self.b_ask.setEnabled(False); self.ans.setHtml(f'<p>{E(t("pc_working"))}</p>')
        run_bg(PC.ai_question, s, self.win.usage, q, vv, lg, cur, names, on_done=lambda r: show(r or off, bool(r)),
               on_fail=lambda e: show(off + '\n\n' + t('pc_ai_fail', e=str(e)[:200]), False))


    # ================================================================ 7) Uçuş öncesi kontrol listesi
    def _build_preflight(self):
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(label(t('pf_help'), 'muted', wrap=True))
        bar = QHBoxLayout()
        bar.addWidget(button('📂 ' + t('pc_open_file'), self.open_file))
        bar.addWidget(button('🛩 ' + t('pc_from_log'), self.from_log))
        bar.addSpacing(12); bar.addWidget(label(t('pf_cells')))
        self.pf_cells = QComboBox(); self.pf_cells.addItem(t('pf_auto'), 0)
        for n in range(1, 15): self.pf_cells.addItem(f'{n}S', n)
        self.pf_cells.currentIndexChanged.connect(self._refresh_preflight); bar.addWidget(self.pf_cells)
        self.pf_chem = QComboBox(); self.pf_chem.addItem('LiPo', 'lipo'); self.pf_chem.addItem('Li-ion', 'liion')
        self.pf_chem.currentIndexChanged.connect(self._refresh_preflight); bar.addWidget(self.pf_chem)
        bar.addStretch(1)
        bar.addWidget(button('🛠 ' + t('pf_fix'), self._pf_fix, primary=True))
        bar.addWidget(button('💾 ' + t('pf_save'), self._pf_save))
        v.addLayout(bar)
        self.pf_view = QTextBrowser(); v.addWidget(self.pf_view, 1)
        self.tabs.addTab(w, '✅ ' + t('pc_tab_pre'))
        self._pf = None

    def _refresh_preflight(self, *_):
        if not hasattr(self, 'pf_view'): return
        from ..core import preflight as PF
        P = self.cur['params']; lg = lang(); d_ = 'rtl' if lg == 'ar' else 'ltr'
        if not P:
            self.pf_view.setHtml(f'<div dir="{d_}"><p>{E(t("pf_none"))}</p></div>'); self._pf = None; return
        vv = self.vehicle() if self.db else PC.detect_vehicle(P)
        r = PF.checklist(P, vv, lg, {'cells': self.pf_cells.currentData() or None, 'chem': self.pf_chem.currentData()})
        self._pf = r
        col = {'go': '#34D399', 'caution': '#FBBF24', 'nogo': '#F87171'}[r['status']]
        ic = {'fail': '⛔', 'warn': '⚠', 'pass': '✔', 'na': '–'}; cc = {'fail': '#F87171', 'warn': '#FBBF24', 'pass': '#34D399', 'na': '#94A3B8'}
        h = [f'<div dir="{d_}"><h2 style="color:{col}">{E(r["summary"])}</h2><p>{E(r["counts_t"])} · {E(PC.vname(r["vehicle"], lg))}</p>',
             '<table cellspacing="0" cellpadding="5" width="100%">']
        for it in r['items']:
            fx = ''.join(f'<br><span style="color:#93C5FD">→ {E(k)} = {E(PC.fmt(val))}</span>' for k, val in it.get('fix') or [])
            h.append(f'<tr><td width="28" style="color:{cc[it["st"]]};font-size:13pt">{ic[it["st"]]}</td>'
                     f'<td width="190" style="color:#94A3B8">{E(it["cat_t"])}</td><td><b>{E(it["title"])}</b><br>{E(it["text"])}{fx}</td></tr>')
        h.append('</table>')
        h.append(f'<p style="color:#64748B">{E(t("pf_note"))}</p></div>')
        self.pf_view.setHtml(''.join(h))

    def _pf_fix(self):
        from ..core import preflight as PF
        if not self._pf: return error(self, t('pc_cur_none'))
        fixes = [(it['title'], k, val) for it in self._pf['items'] for k, val in it.get('fix') or []]
        if not fixes: return info(self, t('pf_nofix'))
        txt = '\n'.join(f'• {a}: {k} = {PC.fmt(val)}' for a, k, val in fixes)
        if QMessageBox.question(self, t('pf_fix'), t('pf_fix_q', x=txt)) != QMessageBox.Yes: return
        newp = PF.apply_fixes(self.cur['params'], self._pf)
        self._export(newp, os.path.splitext(self.cur['name'] or 'params')[0] + '_duzeltilmis')

    def _pf_save(self):
        from ..core import preflight as PF
        if not self._pf: return error(self, t('pc_cur_none'))
        p, _ = QFileDialog.getSaveFileName(self, t('pf_save'), os.path.splitext(self.cur['name'] or 'params')[0] + '_ucus_oncesi.txt', 'Text (*.txt)')
        if not p: return
        open(p, 'w', encoding='utf-8').write(PF.to_text(self._pf)); info(self, t('pc_exported', p=p))

    # ================================================================ 8) PID / TECS ayar önerileri
    def _build_tuning(self):
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(label(t('tu_help'), 'muted', wrap=True))
        bar = QHBoxLayout()
        bar.addWidget(button('🔄 ' + t('tu_run'), lambda: self._refresh_tuning(force=True), primary=True))
        bar.addWidget(button('⬇ ' + t('tu_export'), self._tu_export))
        bar.addWidget(button('📋 ' + t('tu_copy'), self._tu_copy))
        bar.addStretch(1); v.addLayout(bar)
        sp = QSplitter(Qt.Vertical)
        self.tune_view = QTextBrowser(); sp.addWidget(self.tune_view)
        self.ttbl = _tbl(['✓', t('tu_axis'), t('p_name'), t('tu_cur'), t('tu_new'), t('tu_conf'), t('tu_why')], 6)
        sp.addWidget(self.ttbl); sp.setSizes([420, 260]); v.addWidget(sp, 1)
        self.tabs.addTab(w, '🎛 ' + t('pc_tab_tune'))
        self._tune_res = None
        self._refresh_tuning()

    def _refresh_tuning(self, force=False):
        lg = lang(); d_ = 'rtl' if lg == 'ar' else 'ltr'; A = self.win.A
        if not A:
            self.tune_view.setHtml(f'<div dir="{d_}"><p>{E(t("tu_nolog"))}</p></div>'); self.ttbl.setRowCount(0); return
        from ..core import tuning as TU
        if force or self._tune_res is None or self._tune_res.get('_lg') != lg:
            try:
                self._tune_res = TU.analyze(A, lg); self._tune_res['_lg'] = lg
            except Exception as e:
                self.tune_view.setHtml(f'<p style="color:#F87171">{E(str(e))}</p>'); return
        r = self._tune_res
        cc = {'good': '#34D399', 'warn': '#FBBF24', 'bad': '#F87171', 'na': '#94A3B8', 'lowexc': '#94A3B8'}
        h = [f'<div dir="{d_}"><h3 style="color:#93C5FD">{E(t("pc_tab_tune"))} · {E(os.path.basename(A.L.path))}</h3>']
        if r.get('note'): h.append(f'<p style="color:#FBBF24">{E(r["note"])}</p>')
        for a in r['axes']:
            h.append(f'<h4 style="color:{cc.get(a.get("status"), "#CBD5E1")}">{E(a["title"])}</h4>')
            if a.get('metrics_text'): h.append(f'<p style="color:#CBD5E1">{E(a["metrics_text"])}</p>')
            for n_ in a.get('notes', []): h.append(f'<p>• {E(n_)}</p>')
            for x in a.get('recs', []): h.append(f'<p style="color:#FDE68A">→ <b>{E(x["param"])}</b>: {E(PC.fmt(x["cur"]))} → <b>{E(PC.fmt(x["new"]))}</b> — {E(x["why"])}</p>')
        h.append(f'<p style="color:#64748B">⚠ {E(r["disclaimer"])}</p></div>')
        self.tune_view.setHtml(''.join(h))
        recs = r['recs']; self.ttbl.setRowCount(len(recs))
        for i, x in enumerate(recs):
            ck = QTableWidgetItem(); ck.setFlags(ck.flags() | Qt.ItemIsUserCheckable); ck.setCheckState(Qt.Checked if x['conf'] != 'c_lo' else Qt.Unchecked)
            self.ttbl.setItem(i, 0, ck); self.ttbl.setItem(i, 1, _it(x['axis'])); self.ttbl.setItem(i, 2, _it(x['param'], '#FBBF24'))
            self.ttbl.setItem(i, 3, _it(PC.fmt(x['cur']))); self.ttbl.setItem(i, 4, _it(PC.fmt(x['new']), '#34D399'))
            self.ttbl.setItem(i, 5, _it(x['conf_t'])); self.ttbl.setItem(i, 6, _it(x['why']))

    def _tu_selected(self):
        r = self._tune_res or {}
        return [x for i, x in enumerate(r.get('recs', [])) if self.ttbl.item(i, 0) and self.ttbl.item(i, 0).checkState() == Qt.Checked]

    def _tu_export(self):
        sel = self._tu_selected()
        if not sel: return info(self, t('tu_none_sel'))
        from ..core import tuning as TU
        p, _ = QFileDialog.getSaveFileName(self, t('tu_export'), 'ayar_onerileri.param', 'Mission Planner (*.param)')
        if not p: return
        open(p, 'w', encoding='utf-8').write(TU.param_file({'recs': sel}, self.vehicle()))
        info(self, t('tu_exported', p=p))

    def _tu_copy(self):
        from PySide6.QtWidgets import QApplication
        sel = self._tu_selected()
        QApplication.clipboard().setText('\n'.join(f"{x['param']}: {PC.fmt(x['cur'])} -> {PC.fmt(x['new'])}  ({x['why']})" for x in sel))
        self.win.set_status(t('tu_copied', n=len(sel)))


# ====================================================================== Gerçek kaza logları
class CrashLibPage(Page):
    """Gerçek kaza logları + uzman tecrübeleri: her gerçek konuda uzmanların teşhisi, dersler ve logda nereye bakılacağı."""
    def __init__(self, win):
        super().__init__(win)
        from ..core import crashlib, expert as EX
        self.EX = EX
        self.D = crashlib.load(); self.cases = self.D.get('cases') or []
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        v.addWidget(label('💥 ' + t('nav_crashlib'), 'h1'))
        v.addWidget(label(t('cl_help'), 'muted', wrap=True))
        s = self.D.get('score')
        if s:
            v.addWidget(label(t('cl_score', a=s['accuracy'] * 100, r=s['recall_crash'] * 100, s=s['specificity'] * 100, c=s['cause_acc'] * 100, n=s['n'])
                              + (f"  ·  {self.D.get('date', '')}" if self.D.get('date') else ''), 'h2', wrap=True))
        self.tabs = QTabWidget(); v.addWidget(self.tabs, 1)
        # --- sekme 1: gerçek konular
        w1 = QWidget(); v1 = QVBoxLayout(w1); v1.setContentsMargins(0, 6, 0, 0)
        bar = QHBoxLayout()
        self.b_open = button('⬇ ' + t('cl_open'), self.open_case, primary=True); bar.addWidget(self.b_open)
        bar.addWidget(button('🌐 ' + t('cl_forum'), self.forum))
        self.f_les = QComboBox(); self.f_les.addItem('🎓 ' + t('ex_all'), None)
        for k in self._lesson_keys(): self.f_les.addItem(f"{EX.L[k]['icon']} {EX.txt(k, 'title', lang())}", k)
        self.f_les.currentIndexChanged.connect(self.fill); bar.addWidget(self.f_les)
        self.q = QLineEdit(); self.q.setPlaceholderText(t('search')); self.q.textChanged.connect(self.fill); bar.addWidget(self.q, 1)
        self.st = label('', 'muted'); bar.addWidget(self.st)
        v1.addLayout(bar)
        # süzgeçler: araç · uzman etiketi · kök neden (uzman/program) · programın sonucu — birlikte çalışır
        fb = QHBoxLayout()
        self.f_veh = QComboBox(); self.f_veh.addItem(t('clf_all_veh'), None)
        for vv in sorted({c.get('vehicle') for c in self.cases if c.get('vehicle')}): self.f_veh.addItem(vv, vv)
        self.f_lab = QComboBox()
        for k, d in ((None, 'clf_all_lab'), ('crash', 'clf_crash'), ('normal', 'clf_normal')): self.f_lab.addItem(t(d), k)
        self.f_cz = QComboBox(); self.f_cz.addItem(t('clf_all_cause'), None)
        for c in EX.CAUSE_ORDER[:-1] + ['unknown']:
            if any(x.get('cause_hint') == c or x.get('got_cause') == c for x in self.cases):
                self.f_cz.addItem(self._cz(c) if c != 'unknown' else t('clf_unknown'), c)
        self.f_czw = QComboBox()
        for k, d in (('any', 'clf_cw_any'), ('exp', 'clf_cw_exp'), ('prog', 'clf_cw_prog'), ('both', 'clf_cw_both')): self.f_czw.addItem(t(d), k)
        self.f_res = QComboBox()
        for k, d in ((None, 'clf_all_res'), ('ok', 'clf_ok'), ('bad', 'clf_bad')): self.f_res.addItem(t(d), k)
        for w_ in (self.f_veh, self.f_lab, self.f_cz, self.f_czw, self.f_res):
            w_.currentIndexChanged.connect(self.fill); fb.addWidget(w_)
        fb.addWidget(button('✖ ' + t('clf_clear'), self.clear_filters)); fb.addStretch(1)
        v1.addLayout(fb)
        sp = QSplitter(Qt.Horizontal)
        self.tb = _tbl([t('cl_title'), 'Araç' if lang() == 'tr' else 'Vehicle' if lang() == 'en' else 'المركبة', t('cl_label'), t('cl_got'), t('cl_cause'), t('cl_hint'), 'MB'], 0)
        self.tb.cellDoubleClicked.connect(lambda *_: self.open_case())
        self.sort_col, self.sort_desc = None, False
        hh = self.tb.horizontalHeader(); hh.setSectionsClickable(True); hh.sectionClicked.connect(self.sort_by)
        hh.setToolTip(t('clf_sort_tip'))
        self.tb.currentCellChanged.connect(lambda *_: self.show_case())
        sp.addWidget(self.tb)
        self.det = QTextBrowser(); self.det.setOpenExternalLinks(True); sp.addWidget(self.det)
        sp.setStretchFactor(0, 5); sp.setStretchFactor(1, 2); sp.setSizes([1000, 420])
        v1.addWidget(sp, 1)
        self.tabs.addTab(w1, '📂 ' + t('ex_tab_cases'))
        # --- sekme 2: uzman tecrübeleri
        w2 = QWidget(); v2 = QVBoxLayout(w2); v2.setContentsMargins(0, 6, 0, 0)
        gold = QTextBrowser(); gold.setMaximumHeight(170)
        gold.setHtml(self._dir() + f"<b>⭐ {E(t('ex_golden'))}</b><ol>" + ''.join(f'<li>{E(g)}</li>' for g in EX.golden(lang())) + '</ol></div>')
        v2.addWidget(gold)
        b2 = QHBoxLayout()
        self.f_cause = QComboBox(); self.f_cause.addItem(t('ex_all_causes'), '*')
        for c in EX.CAUSE_ORDER:
            if any(L_['cause'] == c for L_ in EX.L.values()): self.f_cause.addItem(self._cz(c) if c else t('ex_general'), c)
        self.f_cause.currentIndexChanged.connect(self.fill_lessons); b2.addWidget(self.f_cause)
        b2.addStretch(1)
        self.b_ex = button('📂 ' + t('ex_show_cases'), self.show_examples); b2.addWidget(self.b_ex)
        v2.addLayout(b2)
        sp2 = QSplitter(Qt.Horizontal)
        self.ls = QListWidget(); self.ls.currentRowChanged.connect(lambda *_: self.show_lesson()); sp2.addWidget(self.ls)
        self.ld = QTextBrowser(); self.ld.setOpenExternalLinks(True); sp2.addWidget(self.ld)
        sp2.setStretchFactor(0, 2); sp2.setStretchFactor(1, 3)
        v2.addWidget(sp2, 1)
        v2.addWidget(label(t('ex_src'), 'muted', wrap=True))
        self.tabs.addTab(w2, '🎓 ' + t('ex_tab_lessons'))
        self.fill(); self.fill_lessons()

    # ---------------------------------------------------------------- yardımcılar
    def _dir(self):
        return '<div dir="rtl" style="text-align:right">' if lang() == 'ar' else '<div>'

    def _lesson_keys(self):
        st = self.EX.stats()
        return sorted(self.EX.L, key=lambda k: -st.get(k, 0))

    def _cz(self, c):
        from ..core import texts as TX
        if not c: return '-'
        if c == 'motor': return ('Motor / ESC / pervane', 'Motor / ESC / prop', 'المحرك / ESC / المروحة')[LI.get(lang(), 0)]
        try: return TX.T('cause_' + c, lang())
        except Exception: return c

    def _lesson_html(self, k, short=False):
        EX = self.EX; lg = lang(); n = EX.stats().get(k)
        h = [f"<h3>{EX.L[k]['icon']} {E(EX.txt(k, 'title', lg))}</h3>"]
        if n: h.append(f"<i>{E(t('ex_seen', n=n))}</i>")
        h.append(f"<p><b>🎓 {E(t('ex_rule'))}:</b> {E(EX.txt(k, 'rule', lg))}</p>")
        if not short:
            h.append(f"<p><b>🔎 {E(t('ex_look'))}:</b> {E(EX.txt(k, 'look', lg))}</p>")
            h.append(f"<p><b>🛠 {E(t('ex_fix'))}:</b> {E(EX.txt(k, 'fix', lg))}</p>")
            if EX.L[k]['params']: h.append(f"<p><b>⚙ {E(t('ex_params'))}:</b> <code>{E(', '.join(EX.L[k]['params']))}</code></p>")
        return ''.join(h)

    # ---------------------------------------------------------------- sekme 1
    def fill(self, *_):
        q = self.q.text().strip().lower(); les = self.f_les.currentData()
        veh, lab, cz, czw, res = (w_.currentData() for w_ in (self.f_veh, self.f_lab, self.f_cz, self.f_czw, self.f_res))

        def cz_ok(c):
            if not cz: return True
            e, p_ = c.get('cause_hint') == cz, (c.get('got_cause') or 'unknown') == cz
            return {'exp': e, 'prog': p_, 'both': e and p_}.get(czw, e or p_)
        self.rows = [c for c in self.cases if (not q or q in (c.get('title') or '').lower() or q in str(c.get('got_cause')).lower())
                     and (not les or les in (self.EX.case_lessons(c.get('id')).get('lessons') or []))
                     and (not veh or c.get('vehicle') == veh) and (not lab or c.get('label') == lab) and cz_ok(c)
                     and (not res or (self._ok(c) == (res == 'ok')))]
        if self.sort_col is not None:
            self.rows.sort(key=lambda c: self._skey(c, self.sort_col), reverse=self.sort_desc)
            self.tb.horizontalHeader().setSortIndicatorShown(True)
            self.tb.horizontalHeader().setSortIndicator(self.sort_col, Qt.DescendingOrder if self.sort_desc else Qt.AscendingOrder)
        self.tb.setRowCount(len(self.rows))
        from ..core import texts as TX
        lg = lang(); li = LI.get(lg, 0)
        lbl = {k: (TX.T('v_' + k, 'tr'), TX.T('v_' + k, 'en'), TX.T('v_' + k, 'ar')) for k in ('crash', 'normal', 'incident', 'noflight')}
        for i, c in enumerate(self.rows):
            ok = self._ok(c)
            self.tb.setItem(i, 0, _it(c.get('title')))
            self.tb.setItem(i, 1, _it(c.get('vehicle')))
            self.tb.setItem(i, 2, _it(lbl.get(c.get('label'), ('', '', ''))[li]))
            self.tb.setItem(i, 3, _it(('✅ ' if ok else '❌ ') + lbl.get(c.get('got'), (str(c.get('got')),) * 3)[li], '#34D399' if ok else '#F87171'))
            self.tb.setItem(i, 4, _it(self._cz(c.get('got_cause'))))
            self.tb.setItem(i, 5, _it(self._cz(c.get('cause_hint'))))
            self.tb.setItem(i, 6, _it(c.get('mb')))
        self.st.setText(t('cl_empty') if not self.rows else str(len(self.rows)))
        self.tb.resizeColumnsToContents(); self.tb.setColumnWidth(0, min(360, self.tb.columnWidth(0)))
        if self.rows: self.tb.setCurrentCell(0, 0)
        self.show_case()

    @staticmethod
    def _ok(c):
        return (c.get('got') in ('crash', 'incident')) == (c.get('label') == 'crash')

    def _skey(self, c, col):
        if col == 6:
            try: return (0, float(c.get('mb') or 0))
            except Exception: return (1, 0.0)
        v = {0: c.get('title'), 1: c.get('vehicle'), 2: c.get('label'), 3: ('0' if self._ok(c) else '1') + str(c.get('got')),
             4: self._cz(c.get('got_cause')) if c.get('got_cause') else '', 5: self._cz(c.get('cause_hint')) if c.get('cause_hint') else ''}.get(col)
        v = (v or '').lower()
        return (v == '' or v == '-', v)          # boşlar her zaman sonda (artan sırada)

    def sort_by(self, col):
        if self.sort_col == col: self.sort_desc = not self.sort_desc
        else: self.sort_col, self.sort_desc = col, False
        self.fill()

    def clear_filters(self):
        for w_ in (self.f_veh, self.f_lab, self.f_cz, self.f_czw, self.f_res, self.f_les): w_.blockSignals(True); w_.setCurrentIndex(0); w_.blockSignals(False)
        self.q.blockSignals(True); self.q.clear(); self.q.blockSignals(False)
        self.fill()

    def show_case(self):
        c = self._cur()
        if not c: return self.det.clear()
        from ..core import texts as TX
        EX = self.EX; lg = lang(); x = EX.case_lessons(c.get('id'))
        h = [self._dir(), f"<h3>{E(c.get('title') or '')}</h3>"]
        if x.get('experts'): h.append(f"<i>👥 {E(t('ex_experts_n', n=x['experts']))}</i><br>")
        if c.get('label') == 'crash':
            if c.get('cause_hint'):
                h.append(f"<p><b>🎓 {E(t('ex_case_diag'))}:</b> {E(self._cz(c['cause_hint']))}</p>")
                if x.get('alt'): h.append(f"<p><b>{E(t('ex_case_alt'))}:</b> {E(', '.join(self._cz(a) for a in x['alt']))}</p>")
            else:
                h.append(f"<p>{E(t('ex_case_none'))}</p>")
        else:
            h.append(f"<p><b>🎓 {E(t('ex_case_diag'))}:</b> {E(TX.T('v_' + (c.get('label') or 'normal'), lg))}</p>")
        got = c.get('got')
        h.append(f"<p><b>🤖 {E(t('ex_case_prog'))}:</b> {E(TX.T('v_' + got, lg) if got in ('crash', 'normal', 'incident', 'noflight') else str(got))}"
                 + (f" · {E(self._cz(c.get('got_cause')))}" if c.get('got_cause') and c.get('got_cause') != 'unknown' else '') + '</p>')
        ok = (got in ('crash', 'incident')) == (c.get('label') == 'crash') and (
            c.get('label') != 'crash' or not c.get('cause_hint') or c.get('got_cause') in {c['cause_hint'], *(x.get('alt') or [])})
        h.append(f"<p>{'✅ ' + E(t('ex_case_ok')) if ok else '⚠ ' + E(t('ex_case_bad'))}</p>")
        if x.get('lessons'):
            h.append(f"<hr><h3>📚 {E(t('ex_case_lessons'))}</h3>")
            for k in x['lessons']: h.append(self._lesson_html(k, short=k not in x['lessons'][:2]))
        if c.get('url'): h.append(f"<p><a style=\"color:#60A5FA\" href=\"{E(c['url'])}\">🌐 {E(t('ex_read'))}</a></p>")
        h.append('</div>')
        self.det.setHtml(''.join(h))

    # ---------------------------------------------------------------- sekme 2
    def fill_lessons(self, *_):
        EX = self.EX; c = self.f_cause.currentData(); st = EX.stats()
        self.lkeys = [k for k in self._lesson_keys() if c == '*' or EX.L[k]['cause'] == c]
        self.ls.clear()
        for k in self.lkeys:
            n = st.get(k)
            self.ls.addItem(f"{EX.L[k]['icon']} {EX.txt(k, 'title', lang())}" + (f"  ({n})" if n else ''))
        if self.lkeys: self.ls.setCurrentRow(0)

    def show_lesson(self):
        r = self.ls.currentRow()
        if not (0 <= r < len(self.lkeys)): return self.ld.clear()
        k = self.lkeys[r]
        ex = [c for c in self.cases if k in (self.EX.case_lessons(c.get('id')).get('lessons') or [])]
        h = [self._dir(), self._lesson_html(k)]
        if ex:
            h.append(f"<hr><b>📂 {E(t('ex_show_cases'))} ({len(ex)})</b><ul>")
            for c in ex[:8]:
                h.append(f"<li><a style=\"color:#60A5FA\" href=\"{E(c.get('url') or '')}\">{E(c.get('title') or '')}</a> — {E(self._cz(c.get('cause_hint')) if c.get('label') == 'crash' else c.get('label') or '')}</li>")
            h.append('</ul>')
        h.append('</div>')
        self.ld.setHtml(''.join(h))

    def show_examples(self, k=None):
        r = self.ls.currentRow()
        k = k or (self.lkeys[r] if 0 <= r < len(self.lkeys) else None)
        if not k: return
        self.f_les.setCurrentIndex(max(0, self.f_les.findData(k))); self.tabs.setCurrentIndex(0)

    def _cur(self):
        r = self.tb.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def forum(self):
        c = self._cur()
        if c:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(c['url']))

    def open_case(self):
        c = self._cur()
        if not c: return
        from ..core import crashlib
        self.b_open.setEnabled(False)
        w = None

        def job():
            return crashlib.download(c, progress=lambda mb: w.progress.emit(mb))

        def done(p):
            self.b_open.setEnabled(True); self.st.setText(''); self.win.open_log(p)

        def fail(e):
            self.b_open.setEnabled(True); self.st.setText(''); error(self, str(e))
        w = run_bg(job, on_done=done, on_fail=fail, on_progress=lambda mb: self.st.setText(t('cl_dl', d=mb)))


# ====================================================================== ders kitabı / video pencereleri
def _lang_combo():
    cb = QComboBox()
    for k, n in (('tr', 'Türkçe'), ('en', 'English'), ('ar', 'العربية')): cb.addItem(n, k)
    cb.setCurrentIndex(max(0, cb.findData(lang())))
    return cb


def book_dialog(win, parent):
    from ..core import textbook
    dl = QDialog(parent); dl.setWindowTitle('📕 ' + t('tb_title')); dl.setMinimumWidth(520); f = QFormLayout(dl)
    f.addRow(label(t('tb_help'), 'muted', wrap=True))
    lg = _lang_combo(); f.addRow(t('tb_lang'), lg)
    boxes = {}
    for s in textbook.SECTIONS:
        cb = QCheckBox(t('tb_sec_' + s)); cb.setChecked(True); boxes[s] = cb; f.addRow(t("tb_sections") if len(boxes) == 1 else "", cb)
    h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button('📕 ' + t('tb_make'), dl.accept, primary=True)); f.addRow(h)
    if dl.exec() != QDialog.Accepted: return
    L = lg.currentData()
    name = {'tr': 'Pixhawk_Egitim_Kitabi', 'en': 'Pixhawk_Training_Book', 'ar': 'Pixhawk_Training_Book_AR'}[L] + '.pdf'
    p, _ = QFileDialog.getSaveFileName(parent, t('tb_title'), os.path.join(os.path.expanduser('~'), 'Desktop', name), 'PDF (*.pdf)')
    if not p: return
    secs = [s for s, cb in boxes.items() if cb.isChecked()]
    lh = win.settings.letterhead()
    win.set_status(t('tb_working'))
    w = None

    def prog(x):
        win.upd_bar.setVisible(True); win.upd_bar.setRange(0, 100); win.upd_bar.setValue(int(x * 100)); win.upd_bar.setFormat(t('tb_working') + '  %p%')

    def done(r):
        win.upd_bar.setVisible(False); win.set_status(t('tb_done', p=p))
        from .common import open_path
        open_path(p)

    def fail(e):
        win.upd_bar.setVisible(False); error(parent, e)
    w = run_bg(lambda: textbook.build_book(p, L, lh, secs, progress=lambda x: w.progress.emit(x)), on_done=done, on_fail=fail, on_progress=prog)


def video_dialog(win, parent):
    A = win.A
    if not A: return error(parent, t('no_log'))
    if A.track is None: return error(parent, t('vd_no_track'))
    from ..core import video
    dl = QDialog(parent); dl.setWindowTitle('🎬 ' + t('vd_title')); dl.setMinimumWidth(520); f = QFormLayout(dl)
    f.addRow(label(t('vd_help'), 'muted', wrap=True))
    lg = _lang_combo(); f.addRow(t('tb_lang'), lg)
    ln = QComboBox()
    for s_ in (90, 180, 300, 480): ln.addItem(f'{s_ // 60}:{s_ % 60:02d}', s_)
    ln.setCurrentIndex(1); f.addRow(t('vd_len'), ln)
    vo = QComboBox()
    for k in ('auto', 'offline', 'none'): vo.addItem(t('vd_voice_' + k), k)
    f.addRow(t('vd_voice'), vo)
    rs = QComboBox(); rs.addItem('1280 × 720 (HD)', (1280, 720)); rs.addItem('1920 × 1080 (Full HD)', (1920, 1080)); f.addRow(t('vd_res'), rs)
    h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button('🎬 ' + t('vd_make'), dl.accept, primary=True)); f.addRow(h)
    if dl.exec() != QDialog.Accepted: return
    L = lg.currentData()
    base = os.path.splitext(os.path.basename(A.L.path))[0]
    p, _ = QFileDialog.getSaveFileName(parent, t('vd_title'), os.path.join(os.path.expanduser('~'), 'Desktop', f'{base}_ders_{L}.mp4'), 'MP4 (*.mp4)')
    if not p: return
    org = (win.settings.letterhead() or {}).get('org', '')
    args = dict(lang=L, target_s=ln.currentData(), voice=vo.currentData(), size=rs.currentData(), fps=20, org=org)
    win._cancel = False
    w = None

    def prog(x):
        win.upd_bar.setVisible(True); win.upd_bar.setRange(0, 100); win.upd_bar.setValue(int(x * 100)); win.upd_bar.setFormat(t('vd_working', p=x * 100))

    def done(r):
        win.upd_bar.setVisible(False); win.set_status(t('vd_done', p=p))
        from .common import open_path
        open_path(p)

    def fail(e):
        win.upd_bar.setVisible(False); error(parent, e)
    w = run_bg(lambda: video.export(A, p, progress=lambda x: w.progress.emit(x), cancel=lambda: win._cancel, **args),
               on_done=done, on_fail=fail, on_progress=prog)
