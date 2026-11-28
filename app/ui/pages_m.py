"""Motor Yönleri Bankası (Eğitim): ArduPilot'taki bütün çerçevelerin motor numarası, dönüş yönü ve test sırası; resimli galeri + ayrıntı."""
from __future__ import annotations
import html
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QListWidget, QListWidgetItem, QSplitter,
                               QTextBrowser, QListView, QAbstractItemView)
from .i18n import lang
from .common import label, button, ImageView
from .pages_a import Page
from ..core import motororder as MO

E = html.escape
TX = {
    'title': ('Motor Yönleri Bankası', 'Motor Order Bank', 'بنك ترتيب المحركات'),
    'intro': ('ArduPilot\'un desteklediği bütün çerçevelerde motor numarası (MOTn çıkışı), dönüş yönü ve Mission Planner motor testi sırası. '
              'Veriler ArduPilot\'un kendi kaynak kodundaki motor tanımlarından (AP_MotorsMatrix) üretildi.',
              'Motor number (MOTn output), rotation direction and Mission Planner motor-test order for every frame ArduPilot supports. '
              'Generated from the motor definitions in ArduPilot\'s own source code (AP_MotorsMatrix).',
              'رقم المحرك (مخرج MOTn) واتجاه الدوران وترتيب اختبار المحركات في Mission Planner لكل الهياكل التي يدعمها ArduPilot. '
              'مولَّدة من تعريفات المحركات في الشيفرة المصدرية لـ ArduPilot (AP_MotorsMatrix).'),
    'legend': ('🔵 Mavi = saat yönünün tersi (CCW) · 🟢 Yeşil = saat yönü (CW) · ⚪ Gri = yön tanımsız · '
               'Büyük rakam = motor numarası · Harf = motor testi sırası (A, B, C…) · 🔺 Kırmızı ok = ön',
               '🔵 Blue = counter-clockwise (CCW) · 🟢 Green = clockwise (CW) · ⚪ Grey = no defined direction · '
               'Big number = motor number · Letter = motor-test order (A, B, C…) · 🔺 Red arrow = front',
               '🔵 أزرق = عكس عقارب الساعة (CCW) · 🟢 أخضر = مع عقارب الساعة (CW) · ⚪ رمادي = بلا اتجاه محدد · '
               'الرقم الكبير = رقم المحرك · الحرف = ترتيب اختبار المحركات (A، B، C…) · 🔺 السهم الأحمر = الأمام'),
    'all': ('Hepsi', 'All', 'الكل'),
    'search': ('Ara: quad, hexa, X8, Y6, tailsitter, V kuyruk…', 'Search: quad, hexa, X8, Y6, tailsitter, V-tail…', 'ابحث: quad، hexa، X8، Y6، tailsitter…'),
    'mine': ('✈ Açık logdaki çerçeve', '✈ Frame of the open log', '✈ هيكل السجل المفتوح'),
    'mine_none': ('Açık logdaki çerçeve bankada bulunamadı (Q_FRAME_CLASS/TYPE ya da FRAME_CLASS/TYPE).',
                  'The open log\'s frame was not found in the bank (Q_FRAME_CLASS/TYPE or FRAME_CLASS/TYPE).',
                  'لم يُعثر على هيكل السجل المفتوح في البنك (Q_FRAME_CLASS/TYPE أو FRAME_CLASS/TYPE).'),
    'cols': (('Çıkış', 'Konum', 'Dönüş yönü', 'Test', 'SERVOx_FUNCTION'), ('Output', 'Position', 'Rotation', 'Test', 'SERVOx_FUNCTION'),
             ('المخرج', 'الموضع', 'اتجاه الدوران', 'اختبار', 'SERVOx_FUNCTION')),
    'params': ('Parametreler', 'Parameters', 'المعاملات'),
    'tips': ('Kontrol listesi: 1) Pervaneler çıkarılmış hâlde Mission Planner → Kurulum → İsteğe bağlı donanım → Motor Testi ile A, B, C… sırasıyla '
             'her motoru çalıştırın; çalışan motor resimdeki harfle aynı yerde olmalı. 2) Dönüş yönü resimdeki okla aynı olmalı; ters dönen motorda '
             'ESC\'nin iki kablosunu değiştirin (ya da DShot/BLHeli ile yön çevirin). 3) Pervane, dönüş yönüne uygun (CW/CCW) takılmalı. '
             'Yanlış motor sırası ya da yön kalkışta anında devrilmeye ve yaw\'da dönmeye yol açar.',
             'Checklist: 1) With props removed, use Mission Planner → Setup → Optional Hardware → Motor Test to spin each motor in order A, B, C…; '
             'the spinning motor must be where that letter is in the picture. 2) Rotation must match the arrow; swap two ESC wires on a reversed motor '
             '(or reverse it with DShot/BLHeli). 3) Fit the prop matching the rotation (CW/CCW). '
             'A wrong motor order or direction flips the aircraft instantly at take-off or makes it spin in yaw.',
             'قائمة التحقق: 1) بدون المراوح، استخدم Mission Planner ← الإعداد ← العتاد الاختياري ← اختبار المحركات لتشغيل كل محرك بالترتيب A، B، C…؛ '
             'يجب أن يكون المحرك الدائر في موضع ذلك الحرف في الصورة. 2) يجب أن يطابق الدوران السهم؛ بدّل سلكين من ESC للمحرك المعكوس '
             '(أو اعكسه عبر DShot/BLHeli). 3) ركّب المروحة المناسبة للاتجاه (CW/CCW). '
             'ترتيب أو اتجاه خاطئ يقلب الطائرة فور الإقلاع أو يجعلها تدور حول محور الانعراج.'),
    'src': ('Kaynak: ArduPilot libraries/AP_Motors/AP_MotorsMatrix.cpp (master) ve AP_MotorsTri.', 'Source: ArduPilot libraries/AP_Motors/AP_MotorsMatrix.cpp (master) and AP_MotorsTri.',
            'المصدر: ArduPilot libraries/AP_Motors/AP_MotorsMatrix.cpp (master) و AP_MotorsTri.'),
    'count': ('{n} çerçeve', '{n} frames', '{n} هيكل'),
}


def tx(k, **a):
    v = TX[k][MO.L3.get(lang(), 0)]
    return v.format(**a) if a else v


class MotorBankPage(Page):
    def __init__(self, win):
        super().__init__(win)
        lg = lang()
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        v.addWidget(label(tx('title'), 'h1'))
        v.addWidget(label(tx('intro'), 'muted', wrap=True))
        lg_l = label(tx('legend'), wrap=True); v.addWidget(lg_l)
        top = QHBoxLayout()
        self.grp = QComboBox(); self.grp.addItem(tx('all'), '')
        for gid, names in MO.GROUPS: self.grp.addItem(names[MO.L3.get(lg, 0)], gid)
        self.grp.setCurrentIndex(1)
        self.grp.currentIndexChanged.connect(lambda *_: self._fill())
        self.q = QLineEdit(); self.q.setPlaceholderText(tx('search')); self.q.textChanged.connect(lambda *_: self._fill())
        self.b_mine = button(tx('mine'), self._mine); self.b_mine.setEnabled(False)
        self.cnt = label('', 'muted')
        top.addWidget(self.grp); top.addWidget(self.q, 1); top.addWidget(self.b_mine); top.addWidget(self.cnt)
        v.addLayout(top)
        sp = QSplitter(Qt.Horizontal)
        self.gal = QListWidget(); self.gal.setViewMode(QListView.IconMode); self.gal.setResizeMode(QListView.Adjust)
        self.gal.setMovement(QListView.Static); self.gal.setIconSize(QSize(170, 170)); self.gal.setGridSize(QSize(205, 250))
        self.gal.setWordWrap(True); self.gal.setSpacing(6); self.gal.setUniformItemSizes(True)
        self.gal.setSelectionMode(QAbstractItemView.SingleSelection)
        self.gal.currentItemChanged.connect(lambda *_: self._show())
        sp.addWidget(self.gal)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(8, 0, 0, 0)
        self.d_title = label('', 'h2'); self.d_title.setWordWrap(True); rv.addWidget(self.d_title)
        self.img = ImageView(); self.img.setMinimumHeight(300); rv.addWidget(self.img, 3)
        self.det = QTextBrowser(); self.det.setOpenExternalLinks(True); rv.addWidget(self.det, 2)
        sp.addWidget(right); sp.setStretchFactor(0, 3); sp.setStretchFactor(1, 2)
        v.addWidget(sp, 1)
        self._icons = {}
        self._fill()

    def _frames(self):
        g = self.grp.currentData(); q = self.q.text().strip().lower(); lg = lang()
        out = []
        for f in MO.bank()['frames']:
            if g and f['group'] != g: continue
            if q:
                hay = ' '.join([MO.title(f, l) for l in ('tr', 'en', 'ar')] + [f.get('cls_name', ''), f.get('type_name', ''), f.get('params', ''),
                                                                               f.get('ap_string', '')]).lower()
                if not all(w in hay for w in q.split()): continue
            out.append(f)
        return out

    def _icon(self, fid):
        ic = self._icons.get(fid)
        if ic is None:
            ic = QIcon(QPixmap(MO.image(fid))); self._icons[fid] = ic
        return ic

    def _fill(self, select=None):
        lg = lang()
        cur = select or (self.gal.currentItem().data(Qt.UserRole) if self.gal.currentItem() else None)
        self.gal.blockSignals(True); self.gal.clear()
        fr = self._frames(); hit = None
        for f in fr:
            it = QListWidgetItem(self._icon(f['id']), MO.title(f, lg)); it.setData(Qt.UserRole, f['id'])
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop); it.setToolTip(f.get('params', ''))
            self.gal.addItem(it)
            if f['id'] == cur: hit = it
        self.gal.blockSignals(False)
        self.cnt.setText(tx('count', n=len(fr)))
        if hit is None and self.gal.count(): hit = self.gal.item(0)
        if hit is not None: self.gal.setCurrentItem(hit); self.gal.scrollToItem(hit)
        self._show()

    def _show(self):
        it = self.gal.currentItem()
        if it is None:
            self.d_title.setText(''); self.det.setHtml(''); return
        fid = it.data(Qt.UserRole); f = next((x for x in MO.bank()['frames'] if x['id'] == fid), None)
        if f is None: return
        lg = lang()
        self.d_title.setText(MO.title(f, lg))
        try:
            with open(MO.image(fid), 'rb') as fh: self.img.set_png(fh.read())
        except Exception:
            self.img.set_png(b'')
        cols = TX['cols'][MO.L3.get(lg, 0)]
        rows = ''.join('<tr>' + ''.join(f'<td style="padding:3px 8px">{E(str(c))}</td>' for c in r) + '</tr>' for r in MO.rows(f, lg))
        h = (f'<p><b>{tx("params")}:</b> <code>{E(f.get("params", ""))}</code></p>'
             + (f'<p>⚠ {E(MO.note(f, lg))}</p>' if MO.note(f, lg) else '')
             + '<table border="1" cellspacing="0" style="border-collapse:collapse">'
             + '<tr>' + ''.join(f'<th style="padding:3px 8px">{E(c)}</th>' for c in cols) + '</tr>' + rows + '</table>'
             + f'<p>{E(tx("tips"))}</p><p style="color:#64748B">{E(tx("src"))}</p>')
        if lg == 'ar': h = f'<div dir="rtl">{h}</div>'
        self.det.setHtml(h)

    # -------------------------------------------------- açık log
    def on_analysis(self, A):
        self._mine_f = None
        try: self._mine_f = MO.find_for_params(A.L.params, A.vehicle)
        except Exception: pass
        self.b_mine.setEnabled(True)

    def _mine(self):
        f = getattr(self, '_mine_f', None)
        if not f:
            from .common import info
            return info(self, tx('mine_none'))
        self.q.blockSignals(True); self.q.clear(); self.q.blockSignals(False)
        i = self.grp.findData(f['group']); self.grp.blockSignals(True); self.grp.setCurrentIndex(max(0, i)); self.grp.blockSignals(False)
        self._fill(select=f['id'])
