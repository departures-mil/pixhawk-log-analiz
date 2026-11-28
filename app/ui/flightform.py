"""Uçuş bilgileri formu (log incelemeden önce) ve Ayarlar > Log soruları düzenleyicisi."""
from __future__ import annotations
from PySide6.QtCore import Qt, QRect, QSize, QPoint
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QLineEdit, QRadioButton,
                               QButtonGroup, QCheckBox, QScrollArea, QWidget, QListWidget, QListWidgetItem, QGroupBox, QInputDialog,
                               QLayout, QSizePolicy, QFrame)
from .i18n import t, lang
from .common import button, label, run_bg, error
from ..core import flightinfo as FI

RADIO = {'crashed', 'power', 'stroke', 'airspeed', 'purpose'}   # (v1.1.18'den beri bütün seçmeli sorular liste olarak görünür)
BADGE = {'log': '🔎', 'ai': '🤖', 'prev': '↺'}


class FlowLayout(QLayout):
    """Satır dolunca alta kayan düzen: seçeneklerin hepsi görünür, hiçbiri sağdan taşıp kesilmez."""
    def __init__(self, parent=None, hs=14, vs=4):
        super().__init__(parent); self._it = []; self._hs = hs; self._vs = vs
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item): self._it.append(item)
    def count(self): return len(self._it)
    def itemAt(self, i): return self._it[i] if 0 <= i < len(self._it) else None
    def takeAt(self, i): return self._it.pop(i) if 0 <= i < len(self._it) else None
    def expandingDirections(self): return Qt.Orientations()
    def hasHeightForWidth(self): return False   # yükseklik OptionList.resizeEvent'te ayarlanır (ızgara düzeniyle güvenli)
    def heightForWidth(self, w): return self._do(QRect(0, 0, w, 0), True)
    def setGeometry(self, r): super().setGeometry(r); self._do(r, False)
    def sizeHint(self): return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for it in self._it: s = s.expandedTo(it.minimumSize())
        return s

    def _do(self, r, test):
        rtl = self.parentWidget() is not None and self.parentWidget().layoutDirection() == Qt.RightToLeft
        x, y, lh = r.x(), r.y(), 0
        for it in self._it:
            if it.widget() is not None and not it.widget().isVisibleTo(self.parentWidget()): continue
            sh = it.sizeHint(); nx = x + sh.width() + self._hs
            if nx - self._hs > r.right() + 1 and lh > 0:
                x = r.x(); y += lh + self._vs; nx = x + sh.width() + self._hs; lh = 0
            if not test:
                px = (r.right() - (x - r.x()) - sh.width() + 1) if rtl else x
                it.setGeometry(QRect(QPoint(px, y), sh))
            x = nx; lh = max(lh, sh.height())
        return y + lh - r.y()


class OptionList(QWidget):
    """Bir sorunun bütün seçenekleri aynı anda görünür (tek seçim). Yazılabilir sorularda sonda 'Diğer' kutusu.
    Seçili seçeneğe yeniden tıklamak seçimi kaldırır."""
    def __init__(self, opts, editable=False, on_change=None, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        fl = FlowLayout(self); self.grp = QButtonGroup(self); self.grp.setExclusive(False); self._cb = on_change
        self._extra = {}
        for k, txt in opts:
            rb = QRadioButton(txt); rb.setProperty('val', k); self.grp.addButton(rb); fl.addWidget(rb)
        self.grp.buttonClicked.connect(self._clicked)
        self.edit = None
        if editable:
            self.edit = QLineEdit(); self.edit.setPlaceholderText(t('fi_other')); self.edit.setMinimumWidth(200)
            self.edit.textEdited.connect(self._typed); fl.addWidget(self.edit)

    def _clicked(self, b):
        if b.isChecked():
            for o in self.grp.buttons():
                if o is not b: o.setChecked(False)
            if self.edit is not None: self.edit.clear()
        if self._cb: self._cb()

    def _typed(self, txt):
        if txt.strip():
            for o in self.grp.buttons(): o.setChecked(False)
        if self._cb: self._cb()

    def value(self):
        for b in self.grp.buttons():
            if b.isChecked(): return b.property('val')
        return self.edit.text().strip() if self.edit is not None else ''

    def set_value(self, val):
        hit = False
        for b in self.grp.buttons():
            on = val not in (None, '') and b.property('val') == val; b.setChecked(on); hit = hit or on
        if self.edit is not None:
            self.edit.setText('' if hit or val in (None, '') else str(val))
        elif val not in (None, '') and not hit:                      # listede olmayan eski cevap (seçenek silinmiş): ekle
            rb = QRadioButton(str(val)); rb.setProperty('val', val); self.grp.addButton(rb); self.layout().addWidget(rb); rb.setChecked(True)

    def _fit(self):
        h = self.layout().heightForWidth(max(50, self.width()))
        if h != self.minimumHeight(): self.setMinimumHeight(h)

    def resizeEvent(self, e):
        super().resizeEvent(e); self._fit()

    def showEvent(self, e):
        super().showEvent(e); self._fit()


class FlightInfoDialog(QDialog):
    def __init__(self, win, info, src, parent=None, L=None):
        super().__init__(parent or win)
        self.win = win; self.s = win.settings; self.L = L; self.src = dict(src or {})
        lg = lang(); self.setWindowTitle(t('fi_title')); self.setMinimumSize(860, 680)
        if lg == 'ar': self.setLayoutDirection(Qt.RightToLeft)
        v = QVBoxLayout(self)
        v.addWidget(label(t('fi_intro'), 'muted', wrap=True))
        lg_note = label(t('fi_badges'), 'muted', wrap=True); v.addWidget(lg_note)
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); body = QWidget(); body.setObjectName('root'); self.grid = QGridLayout(body); sa.setWidget(body)
        v.addWidget(sa, 1)
        self.w = {}; self.rows = {}
        r = 0
        for q in FI.questions(self.s):
            qid = q['id']
            lab = QLabel(f"{q.get('icon', '')}  {FI.label(qid, lg)}"); lab.setObjectName('h2' if qid == 'crashed' else '')
            badge = QLabel(''); badge.setObjectName('muted')
            if q['kind'] in ('choice', 'edit'):
                ol = OptionList(FI.options(qid, self.s, lg), editable=q['kind'] == 'edit', on_change=self._dep)
                self.w[qid] = ('list', ol); wid = ol
            else:
                le = QLineEdit(); le.setPlaceholderText(q.get('ph', '')); self.w[qid] = ('line', le); wid = le
            lab.setAlignment(Qt.AlignLeft | Qt.AlignTop); lab.setMinimumHeight(24)
            self.grid.addWidget(lab, r, 0, Qt.AlignTop); self.grid.addWidget(wid, r, 1); self.grid.addWidget(badge, r, 2)
            self.rows[qid] = (lab, wid, badge); r += 1
        self.grid.setColumnStretch(1, 1); self.grid.setRowStretch(r, 1); self.grid.setVerticalSpacing(10)
        self.set_values(info)
        bot = QHBoxLayout()
        self.ask = QCheckBox(t('fi_ask')); self.ask.setChecked(FI.conf(self.s)['ask']); bot.addWidget(self.ask)
        bot.addStretch(1)
        from ..core import ai as AI
        self.b_ai = button('🤖 ' + t('fi_ai'), self._ai); self.b_ai.setEnabled(AI.available(self.s) and L is not None)
        if not AI.available(self.s): self.b_ai.setToolTip(t('fi_ai_off'))
        bot.addWidget(self.b_ai)
        bot.addWidget(button(t('fi_skip'), self._skip))
        bot.addWidget(button('✔ ' + t('fi_ok'), self.accept, primary=True))
        v.addLayout(bot)
        self.skipped = False

    # ------------------------------------------------------------ değerler
    def set_values(self, info):
        for qid, (kind, w) in self.w.items():
            val = (info or {}).get(qid)
            if kind == 'list':
                w.set_value(val)
            elif kind == 'combo':
                i = w.findData(val) if val not in (None, '') else 0
                if i < 0 and val:
                    w.addItem(str(val), str(val)); i = w.count() - 1
                w.setCurrentIndex(max(0, i))
            else:
                w.setText(str(val or ''))
            self.rows[qid][2].setText(BADGE.get(self.src.get(qid), ''))
        self._dep()

    def values(self):
        out = {}
        for qid, (kind, w) in self.w.items():
            if kind == 'list':
                v = w.value()
            elif kind == 'combo':
                v = w.currentData() if w.currentText() == w.itemText(w.currentIndex()) else ''
                if w.isEditable():
                    txt = w.currentText().strip()
                    if txt and txt != '—' and (v in (None, '') or txt != w.itemText(w.currentIndex())): v = txt
                    elif txt and txt != '—' and not v: v = txt
            else:
                v = w.text().strip()
            if v not in (None, ''): out[qid] = v
        return out

    def _dep(self):
        vals = self.values()
        for qid, (lab, wid, badge) in self.rows.items():
            si = FI.QBYID[qid].get('show_if')
            on = (not si) or vals.get(si[0]) in si[1]
            for x in (lab, wid, badge): x.setVisible(on)

    # ------------------------------------------------------------ YZ
    def _ai(self):
        cur = self.values(); self.b_ai.setEnabled(False); self.b_ai.setText('🤖 …')
        def job():
            return FI.ai_fill(self.L, self.s, self.win.usage, cur)
        def ok(d):
            self.b_ai.setText('🤖 ' + t('fi_ai')); self.b_ai.setEnabled(True)
            if not d: return error(self, t('fi_ai_none'))
            for k in d: self.src[k] = 'ai'
            self.set_values({**cur, **d})
        def fail(e):
            self.b_ai.setText('🤖 ' + t('fi_ai')); self.b_ai.setEnabled(True); error(self, e)
        run_bg(job, on_done=ok, on_fail=fail)

    def _skip(self):
        self.skipped = True; self.accept()

    def done(self, r):
        c = FI.conf(self.s); c['ask'] = self.ask.isChecked(); self.s['fi'] = c
        try: self.win.settings.save()
        except Exception: pass
        super().done(r)


# ------------------------------------------------------------------ Ayarlar
class QuestionEditor(QGroupBox):
    """Ayarlar > Log soruları: soruları aç/kapat, seçenek ekle/çıkar."""
    def __init__(self, win):
        super().__init__(t('fi_set_title'))
        self.win = win; lg = lang()
        v = QVBoxLayout(self)
        v.addWidget(label(t('fi_set_desc'), 'muted', wrap=True))
        c = FI.conf(win.settings)
        top = QHBoxLayout()
        self.ask = QCheckBox(t('fi_ask')); self.ask.setChecked(c['ask']); self.ask.toggled.connect(self._save); top.addWidget(self.ask)
        self.aif = QCheckBox(t('fi_ai_auto')); self.aif.setChecked(c['ai_fill']); self.aif.toggled.connect(self._save); top.addWidget(self.aif)
        top.addStretch(1); v.addLayout(top)
        h = QHBoxLayout()
        self.qs = QListWidget(); self.qs.setMaximumWidth(300)
        for q in FI.QUESTIONS:
            it = QListWidgetItem(f"{q.get('icon', '')} {FI.label(q['id'], lg)}"); it.setData(Qt.UserRole, q['id'])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Unchecked if q['id'] in c['off'] else Qt.Checked)
            self.qs.addItem(it)
        self.qs.itemChanged.connect(lambda *_: self._save()); self.qs.currentItemChanged.connect(lambda *_: self._fill())
        h.addWidget(self.qs)
        rv = QVBoxLayout()
        self.opts = QListWidget(); rv.addWidget(self.opts, 1)
        bh = QHBoxLayout()
        bh.addWidget(button('＋ ' + t('fi_add'), self._add)); bh.addWidget(button('－ ' + t('fi_del'), self._del))
        bh.addWidget(button('↺ ' + t('fi_reset'), self._reset)); bh.addStretch(1)
        rv.addLayout(bh); h.addLayout(rv, 1); v.addLayout(h)
        self.qs.setCurrentRow(0)

    def _qid(self):
        it = self.qs.currentItem(); return it.data(Qt.UserRole) if it else None

    def _fill(self):
        self.opts.clear(); qid = self._qid()
        if not qid: return
        has = FI.QBYID[qid].get('opts') is not None
        for k, txt in FI.options(qid, self.win.settings, lang()):
            it = QListWidgetItem(txt); it.setData(Qt.UserRole, k); self.opts.addItem(it)
        self.opts.setEnabled(has)

    def _save(self):
        c = FI.conf(self.win.settings)
        c['ask'] = self.ask.isChecked(); c['ai_fill'] = self.aif.isChecked()
        c['off'] = [self.qs.item(i).data(Qt.UserRole) for i in range(self.qs.count()) if self.qs.item(i).checkState() != Qt.Checked]
        self.win.settings['fi'] = c
        try: self.win.settings.save()
        except Exception: pass

    def _add(self):
        qid = self._qid()
        if not qid or FI.QBYID[qid].get('opts') is None: return
        txt, ok = QInputDialog.getText(self, t('fi_add'), FI.label(qid, lang()))
        txt = (txt or '').strip()
        if not ok or not txt: return
        c = FI.conf(self.win.settings)
        c['add'].setdefault(qid, [])
        if txt not in c['add'][qid]: c['add'][qid].append(txt)
        if txt in c['del'].get(qid, []): c['del'][qid].remove(txt)
        self.win.settings['fi'] = c; self._save(); self._fill()

    def _del(self):
        qid = self._qid(); it = self.opts.currentItem()
        if not qid or not it: return
        k = it.data(Qt.UserRole); c = FI.conf(self.win.settings)
        if k in c['add'].get(qid, []): c['add'][qid].remove(k)
        else: c['del'].setdefault(qid, []).append(k)
        self.win.settings['fi'] = c; self._save(); self._fill()

    def _reset(self):
        qid = self._qid()
        if not qid: return
        c = FI.conf(self.win.settings); c['add'].pop(qid, None); c['del'].pop(qid, None)
        self.win.settings['fi'] = c; self._save(); self._fill()
