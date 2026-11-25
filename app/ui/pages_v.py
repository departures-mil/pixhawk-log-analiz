"""v1.1.8 sayfaları: Kendi Grafiğim (alan/formül/parametre seçerek grafik) ve Video ve OSD (video ↔ log eşleme, OSD, birleştirme)."""
from __future__ import annotations
import html, os, time, queue, threading
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QLineEdit, QComboBox, QSpinBox,
                               QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QSplitter, QCheckBox,
                               QFileDialog, QProgressBar, QSlider, QGroupBox, QGridLayout, QRadioButton, QInputDialog, QSizePolicy, QScrollArea, QFrame)
from .i18n import t, lang
from .common import label, button, run_bg, error, info
from .pages_a import Page
from ..core.analysis import fmt_t

E = html.escape

TX = {
    # Kendi grafiğim
    'cc_saved': ('Kayıtlı / hazır grafikler', 'Saved / preset charts', 'رسوم محفوظة / جاهزة'),
    'cc_load': ('Aç', 'Open', 'فتح'), 'cc_save': ('Kaydet', 'Save', 'حفظ'), 'cc_del': ('Sil', 'Delete', 'حذف'),
    'cc_name': ('Grafik adı:', 'Chart name:', 'اسم الرسم:'),
    'cc_fields': ('1) Log alanı seçin (çift tıklayın)', '1) Pick a log field (double-click)', '1) اختر حقلاً من السجل (نقر مزدوج)'),
    'cc_search': ('Ara: ATT.Roll, RCOU, gerilim…', 'Search: ATT.Roll, RCOU, voltage…', 'ابحث: ATT.Roll، RCOU، الجهد…'),
    'cc_expr': ('2) ya da formül yazın', '2) or type a formula', '2) أو اكتب صيغة'),
    'cc_expr_ph': ('ör. RCOU.C3 - RCOU.C1 · BAT.Volt * BAT.Curr · smooth(ATT.Roll, 20)', 'e.g. RCOU.C3 - RCOU.C1 · BAT.Volt * BAT.Curr · smooth(ATT.Roll, 20)',
                   'مثل RCOU.C3 - RCOU.C1 · BAT.Volt * BAT.Curr · smooth(ATT.Roll, 20)'),
    'cc_fn': ('İşlemler: + − × ÷ ** ( ) · abs sqrt deg rad sin cos atan2 hypot min max clip(x,a,b) smooth(x,n) rate(x)=değişim/sn pct(x,a,b)=% · '
              'parametre adı yazılırsa bu logdaki değeri kullanılır (ör. pct(RCOU.C3, SERVO3_MIN, SERVO3_MAX))',
              'Operations: + − × ÷ ** ( ) · abs sqrt deg rad sin cos atan2 hypot min max clip(x,a,b) smooth(x,n) rate(x)=change/s pct(x,a,b)=% · '
              'a parameter name uses its value in this log (e.g. pct(RCOU.C3, SERVO3_MIN, SERVO3_MAX))',
              'العمليات: + − × ÷ ** ( ) · abs sqrt deg rad sin cos atan2 hypot min max clip smooth rate pct · اسم المعامل يستخدم قيمته في هذا السجل'),
    'cc_panel': ('Panel', 'Panel', 'اللوحة'), 'cc_add': ('Ekle', 'Add', 'إضافة'),
    'cc_params': ('3) Parametre ekleyin (eşik çizgisi, çift tıklayın)', '3) Add a parameter (limit line, double-click)', '3) أضف معاملاً (خط حد، نقر مزدوج)'),
    'cc_psearch': ('Ara: SPIN_MAX, AIRSPEED, BATT…', 'Search: SPIN_MAX, AIRSPEED, BATT…', 'ابحث: SPIN_MAX، AIRSPEED، BATT…'),
    'cc_sel': ('Grafikteki çizgiler', 'Lines in the chart', 'الخطوط في الرسم'), 'cc_rm': ('Seçileni çıkar', 'Remove selected', 'إزالة المحدد'),
    'cc_clear': ('Temizle', 'Clear', 'مسح'), 'cc_draw': ('📈 Çiz', '📈 Draw', '📈 ارسم'),
    'cc_line': ('Sabit çizgi (değer)', 'Constant line (value)', 'خط ثابت (قيمة)'),
    'cc_st_h': ('Görünen aralıkta değerler (yakınlaştırınca güncellenir)', 'Values in the visible range (updates when you zoom)', 'القيم في المجال الظاهر (تتحدث عند التكبير)'),
    'cc_c': [('Çizgi', 'Line', 'الخط'), ('En düşük', 'Min', 'الأدنى'), ('Zamanı', 'At', 'عند'), ('En yüksek', 'Max', 'الأعلى'), ('Zamanı', 'At', 'عند'),
             ('Ortalama', 'Mean', 'المتوسط'), ('Eşik', 'Limit', 'الحد'), ('Eşik üstünde', 'Above limit', 'فوق الحد'), ('Eşik altında', 'Below limit', 'تحت الحد')],
    'cc_err': ('Formül hatası: {e}', 'Formula error: {e}', 'خطأ في الصيغة: {e}'),
    'cc_nolog': ('Önce bir log açın.', 'Open a log first.', 'افتح سجلاً أولاً.'),
    'cc_saved_ok': ('Kaydedildi: {n}', 'Saved: {n}', 'تم الحفظ: {n}'),
    'cc_hint': ('İpucu: aynı paneldeki parametre çizgisi, o paneldeki çizgilerin eşiği sayılır; tablo eşiğin üstünde/altında geçen süreyi verir.',
                'Tip: a parameter line in a panel is the limit for that panel\'s lines; the table shows time spent above/below it.',
                'تلميح: خط المعامل في لوحة هو حد خطوط تلك اللوحة؛ يعرض الجدول الزمن فوقه/تحته.'),
    # Video
    'v_main': ('Ana video (kamera / yer çekimi)', 'Main video (camera / ground)', 'الفيديو الرئيسي (كاميرا / من الأرض)'),
    'v_second': ('İkinci video (FPV gözlük / DVR, OSD\'li)', 'Second video (FPV goggles / DVR, with OSD)', 'الفيديو الثاني (نظارة FPV / DVR مع OSD)'),
    'v_open': ('🎞 Video seç…', '🎞 Choose video…', '🎞 اختر فيديو…'), 'v_none': ('(yok)', '(none)', '(لا يوجد)'),
    'v_unset': ('Videoyu kaldır', 'Remove video', 'إزالة الفيديو'),
    'v_edit': ('Eşlemesi ayarlanan:', 'Syncing:', 'المزامنة لـ:'),
    'v_off': ('Ofset (log zamanı − video zamanı, sn)', 'Offset (log time − video time, s)', 'الإزاحة (زمن السجل − زمن الفيديو، ث)'),
    'v_auto': ('⏱ Kayıt saatinden otomatik', '⏱ Auto from recording time', '⏱ تلقائي من وقت التسجيل'),
    'v_ev': ('Videonun şu anı = seçili olay', 'Current video moment = selected event', 'لحظة الفيديو الحالية = الحدث المحدد'),
    'v_cur': ('Videonun şu anı = grafikteki imleç', 'Current video moment = chart cursor', 'لحظة الفيديو الحالية = مؤشر الرسم'),
    'v_auto_ok': ('Ofset {o:+.1f} sn ({s}). Kalkış gibi bir olayla kontrol edin; gerekirse ±0,1 sn düğmeleriyle düzeltin.',
                  'Offset {o:+.1f} s ({s}). Check against an event such as takeoff; fine-tune with the ±0.1 s buttons.',
                  'الإزاحة {o:+.1f} ث ({s}). تحقق بحدث مثل الإقلاع؛ واضبط بأزرار ±0.1 ث.'),
    'v_auto_no': ('Videoda kayıt saati yok ya da logda GPS saati yok. Olay işaretleyerek eşleyin.',
                  'No recording time in the video or no GPS time in the log. Sync by marking an event.',
                  'لا يوجد وقت تسجيل في الفيديو أو وقت GPS في السجل. زامن بتحديد حدث.'),
    'v_play': ('▶ Oynat', '▶ Play', '▶ تشغيل'), 'v_pause': ('⏸ Durdur', '⏸ Pause', '⏸ إيقاف'),
    'v_osd': ('OSD göster', 'Show OSD', 'إظهار OSD'), 'v_osd_items': ('OSD öğeleri', 'OSD items', 'عناصر OSD'),
    'v_follow': ('Grafik, harita ve 3B videoyu izlesin', 'Chart, map and 3D follow the video', 'الرسم والخريطة وثلاثي الأبعاد تتبع الفيديو'),
    'v_chart': ('Alttaki grafik', 'Chart below', 'الرسم أدناه'),
    'v_exp': ('💾 Birleştirilmiş video kaydet (MP4)', '💾 Save merged video (MP4)', '💾 حفظ الفيديو المدمج (MP4)'),
    'v_layout': ('Düzen', 'Layout', 'التخطيط'),
    'v_l_single': ('Yalnız ana video', 'Main video only', 'الفيديو الرئيسي فقط'), 'v_l_pip': ('Resim içinde resim', 'Picture in picture', 'صورة داخل صورة'),
    'v_l_side': ('Yan yana', 'Side by side', 'جنباً إلى جنب'),
    'v_panel': ('Yanına harita + irtifa paneli', 'Map + altitude panel on the side', 'لوحة خريطة + ارتفاع بجانبه'),
    'v_range': ('Aralık', 'Range', 'المجال'), 'v_r_all': ('Videonun tamamı', 'Whole video', 'الفيديو كاملاً'),
    'v_r_flight': ('Yalnız uçuş', 'Flight only', 'الطيران فقط'), 'v_r_root': ('Olay anı ±30 sn', 'Event ±30 s', 'لحظة الحدث ±30 ث'),
    'v_res': ('Genişlik', 'Width', 'العرض'),
    'v_prog': ('Video hazırlanıyor… %{p:.0f} · {n}/{tot} kare · {fps:.0f} kare/sn · kalan ~{eta}',
               'Rendering video… {p:.0f}% · {n}/{tot} frames · {fps:.0f} fps · ~{eta} left',
               'جارٍ تجهيز الفيديو… {p:.0f}% · {n}/{tot} إطار · {fps:.0f} إطار/ث · متبقٍ ~{eta}'),
    'v_done': ('Video kaydedildi: {p}', 'Video saved: {p}', 'تم حفظ الفيديو: {p}'),
    'v_cancel': ('İptal', 'Cancel', 'إلغاء'),
    'v_need': ('Önce bir log açın ve ana videoyu seçin.', 'Open a log and choose the main video first.', 'افتح سجلاً واختر الفيديو الرئيسي أولاً.'),
    'v_out': ('Video bu logun dışında (log {a} – {b}). Ofseti kontrol edin.', 'Video is outside this log (log {a} – {b}). Check the offset.',
              'الفيديو خارج هذا السجل. تحقق من الإزاحة.'),
    'v_info': ('{w}×{h} · {fps:.0f} kare/sn · {d} · kayıt saati: {c}', '{w}×{h} · {fps:.0f} fps · {d} · recorded: {c}', '{w}×{h} · {fps:.0f} إطار/ث · {d} · وقت التسجيل: {c}'),
    'v_help': ('Video ile log aynı zamana oturtulur: önce "Kayıt saatinden otomatik" deneyin; sonra videoda kalkış (ya da motorların çalıştığı an) karesine gidip '
               'listeden aynı olayı seçin ve "Videonun şu anı = seçili olay"a basın. Grafikte tıkladığınız an video da oraya gider.',
               'Video and log are aligned in time: try "Auto from recording time" first; then go to the takeoff (or motor start) frame and choose the same event '
               'in the list and press "Current video moment = selected event". Clicking a chart moves the video there too.',
               'يُطابَق الفيديو مع السجل زمنياً: جرّب "تلقائي من وقت التسجيل" أولاً؛ ثم انتقل إلى إطار الإقلاع واختر الحدث نفسه واضغط "لحظة الفيديو الحالية = الحدث المحدد".'),
}


def tx(k):
    from ..core import viz
    v = TX[k]
    return viz.tx(v, lang())


def _err_text(e):
    s = str(e)
    if s.startswith('missing:'): return {'tr': 'logda yok: ', 'en': 'not in log: ', 'ar': 'غير موجود: '}.get(lang(), '') + s[8:]
    if s.startswith('unknown:'): return {'tr': 'bilinmeyen ad: ', 'en': 'unknown name: ', 'ar': 'اسم غير معروف: '}.get(lang(), '') + s[8:]
    return {'syntax': {'tr': 'yazım hatası', 'en': 'syntax error', 'ar': 'خطأ في الصياغة'}, 'no_field': {'tr': 'MESAJ.ALAN gerekli (ör. ATT.Roll)', 'en': 'a MESSAGE.FIELD is needed (e.g. ATT.Roll)', 'ar': 'مطلوب رسالة.حقل'},
            'empty': {'tr': 'boş', 'en': 'empty', 'ar': 'فارغ'}}.get(s, {}).get(lang(), s)


# ====================================================================== Kendi grafiğim
class CustomChartPage(Page):
    def __init__(self, win):
        super().__init__(win)
        from .chartview import ChartView
        h = QHBoxLayout(self); h.setContentsMargins(16, 12, 16, 12)
        left = QWidget(); left.setFixedWidth(400); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(4)
        # kayıtlı
        lv.addWidget(label(tx('cc_saved'), 'h2'))
        r = QHBoxLayout(); self.saved = QComboBox(); r.addWidget(self.saved, 1)
        r.addWidget(button(tx('cc_load'), self._load)); r.addWidget(button(tx('cc_del'), self._delete)); lv.addLayout(r)
        r = QHBoxLayout(); r.addWidget(QLabel(tx('cc_name'))); self.name = QLineEdit(); r.addWidget(self.name, 1)
        r.addWidget(button(tx('cc_save'), self._save)); lv.addLayout(r)
        # alanlar
        lv.addWidget(label(tx('cc_fields'), 'h2'))
        self.fs = QLineEdit(); self.fs.setPlaceholderText(tx('cc_search')); self.fs.textChanged.connect(self._filter_fields); lv.addWidget(self.fs)
        self.fl = QListWidget(); self.fl.itemDoubleClicked.connect(self._add_field); lv.addWidget(self.fl, 3)
        r = QHBoxLayout(); r.addWidget(QLabel(tx('cc_panel'))); self.panel = QSpinBox(); self.panel.setRange(1, 4); r.addWidget(self.panel); r.addStretch(1); lv.addLayout(r)
        lv.addWidget(label(tx('cc_expr'), 'h2'))
        r = QHBoxLayout(); self.expr = QLineEdit(); self.expr.setPlaceholderText(tx('cc_expr_ph')); self.expr.returnPressed.connect(self._add_expr)
        r.addWidget(self.expr, 1); r.addWidget(button(tx('cc_add'), self._add_expr)); lv.addLayout(r)
        lv.addWidget(label(tx('cc_fn'), 'muted', wrap=True))
        lv.addWidget(label(tx('cc_params'), 'h2'))
        self.ps = QLineEdit(); self.ps.setPlaceholderText(tx('cc_psearch')); self.ps.textChanged.connect(self._filter_params); lv.addWidget(self.ps)
        self.pl = QListWidget(); self.pl.itemDoubleClicked.connect(self._add_param); lv.addWidget(self.pl, 2)
        r = QHBoxLayout(); r.addWidget(QLabel(tx('cc_line'))); self.cval = QLineEdit(); self.cval.setFixedWidth(90); r.addWidget(self.cval)
        r.addWidget(button(tx('cc_add'), self._add_line)); r.addStretch(1); lv.addLayout(r)
        lv.addWidget(label(tx('cc_sel'), 'h2'))
        self.sel = QListWidget(); lv.addWidget(self.sel, 2)
        r = QHBoxLayout(); r.addWidget(button(tx('cc_rm'), self._remove)); r.addWidget(button(tx('cc_clear'), self._clear))
        r.addStretch(1); r.addWidget(button(tx('cc_draw'), self.draw, primary=True)); lv.addLayout(r)
        h.addWidget(left)
        sp = QSplitter(Qt.Vertical)
        self.view = ChartView(); self.view.clicked.connect(self._clicked); sp.addWidget(self.view)
        bw = QWidget(); bv = QVBoxLayout(bw); bv.setContentsMargins(0, 0, 0, 0)
        bv.addWidget(label(tx('cc_st_h') + '  ·  ' + tx('cc_hint'), 'muted', wrap=True))
        self.st = QTableWidget(0, 9); self.st.setHorizontalHeaderLabels([self._c(i) for i in range(9)])
        self.st.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.st.verticalHeader().setVisible(False)
        self.st.setEditTriggers(QAbstractItemView.NoEditTriggers); bv.addWidget(self.st, 1)
        sp.addWidget(bw); sp.setSizes([640, 220]); h.addWidget(sp, 1)
        self.A = None; self.cat = []; self.items = []; self.res = []
        self._fill_saved()

    def _c(self, i):
        from ..core import viz
        return viz.tx(TX['cc_c'][i], lang())

    # ------------------------------------------------------------ veri
    def on_analysis(self, A):
        from ..core import customchart as CC
        self.A = A
        try: self.cat = CC.catalog(A.L)
        except Exception: self.cat = []
        self._filter_fields(); self._filter_params()

    def _filter_fields(self, *_):
        from ..core import sources
        q = self.fs.text().strip().lower(); lg = lang()
        self.fl.clear()
        n = 0
        for name, m, f, cnt in self.cat:
            mean = sources.field_meaning(name, lg)
            if q and q not in name.lower() and q not in mean.lower(): continue
            it = QListWidgetItem(f'{name}   — {mean}' if mean else name); it.setData(Qt.UserRole, name); it.setToolTip(f'{name}: {mean} ({cnt})')
            self.fl.addItem(it); n += 1
            if n >= 1500: break

    def _filter_params(self, *_):
        from ..core import sources
        self.pl.clear()
        if self.A is None: return
        q = self.ps.text().strip().upper(); lg = lang(); veh = self.A.vehicle
        n = 0
        for k in sorted(self.A.L.params):
            if q and q not in k: continue
            v = self.A.L.params[k]
            ttl = sources.param_text(k, veh, lg)[0] if n < 400 else ''
            it = QListWidgetItem(f'{k} = {v:g}' + (f'   — {ttl}' if ttl else '')); it.setData(Qt.UserRole, k); self.pl.addItem(it); n += 1
            if n >= 600: break

    # ------------------------------------------------------------ seçim
    def _push(self, d):
        self.items.append(d); self._refresh_sel()

    def _refresh_sel(self):
        self.sel.clear()
        for d in self.items:
            if d['kind'] == 'series': s = f"[P{d['panel']}]  📈 {d['expr']}"
            elif d['kind'] == 'param':
                v = self.A.L.params.get(d['name']) if self.A else None
                s = f"[P{d['panel']}]  ⚙ {d['name']}" + (f' = {v:g}' if v is not None else '')
            else: s = f"[P{d['panel']}]  ─ {d['y']:g}"
            self.sel.addItem(s)

    def _add_field(self, it):
        self._push({'kind': 'series', 'expr': it.data(Qt.UserRole), 'panel': self.panel.value()})

    def _add_expr(self):
        e = self.expr.text().strip()
        if not e: return
        if self.A is not None:
            from ..core import customchart as CC
            try: CC.evaluate(self.A.L, e)
            except CC.ExprError as x: return error(self, tx('cc_err').format(e=_err_text(x)))
        self._push({'kind': 'series', 'expr': e, 'panel': self.panel.value()}); self.expr.clear()

    def _add_param(self, it):
        self._push({'kind': 'param', 'name': it.data(Qt.UserRole), 'panel': self.panel.value()})

    def _add_line(self):
        try: y = float(self.cval.text().replace(',', '.'))
        except ValueError: return
        self._push({'kind': 'line', 'y': y, 'panel': self.panel.value()})

    def _remove(self):
        i = self.sel.currentRow()
        if 0 <= i < len(self.items): self.items.pop(i); self._refresh_sel()

    def _clear(self):
        self.items = []; self._refresh_sel()

    def spec(self):
        return {'title': self.name.text().strip(),
                'series': [{'expr': d['expr'], 'panel': d['panel']} for d in self.items if d['kind'] == 'series'],
                'params': [{'name': d['name'], 'panel': d['panel']} for d in self.items if d['kind'] == 'param'],
                'lines': [{'y': d['y'], 'panel': d['panel']} for d in self.items if d['kind'] == 'line']}

    def set_spec(self, sp):
        self.items = [{'kind': 'series', **s} for s in sp.get('series', [])] + [{'kind': 'param', **p} for p in sp.get('params', [])] + \
                     [{'kind': 'line', **l} for l in sp.get('lines', [])]
        self._refresh_sel()

    # ------------------------------------------------------------ kayıt
    def _store(self):
        return self.win.settings.setdefault('custom_charts', [])

    def _fill_saved(self):
        from ..core import customchart as CC, viz
        self.saved.clear()
        for p in CC.PRESETS: self.saved.addItem('★ ' + viz.tx(p['name'], lang()), ('preset', p))
        for p in self._store(): self.saved.addItem('💾 ' + p.get('title', '?'), ('user', p))

    def _load(self):
        d = self.saved.currentData()
        if not d: return
        kind, p = d
        from ..core import viz
        self.name.setText(viz.tx(p['name'], lang()) if kind == 'preset' else p.get('title', ''))
        self.set_spec(p)
        if self.A is not None: self.draw()

    def _save(self):
        sp = self.spec(); n = sp['title'] or time.strftime('Grafik %H:%M')
        sp['title'] = n; self.name.setText(n)
        st = [x for x in self._store() if x.get('title') != n] + [sp]
        self.win.settings['custom_charts'] = st[-60:]
        try: self.win.settings.save()
        except Exception: pass
        self._fill_saved(); self.win.set_status(tx('cc_saved_ok').format(n=n))

    def _delete(self):
        d = self.saved.currentData()
        if not d or d[0] != 'user': return
        self.win.settings['custom_charts'] = [x for x in self._store() if x.get('title') != d[1].get('title')]
        try: self.win.settings.save()
        except Exception: pass
        self._fill_saved()

    # ------------------------------------------------------------ çizim
    def draw(self):
        from ..core import charts, customchart as CC
        if self.A is None: return error(self, tx('cc_nolog'))
        sp = self.spec()
        if not sp['series'] and not sp['params']: return
        A = self.A; lg = lang()

        def job():
            charts.want_fig(True)
            try: return CC.build(A, sp, lg)
            finally: charts.want_fig(False)

        def done(r):
            fig, res = r; self.res = res
            bad = [x for x in res if x.get('err')]
            if bad: self.win.set_status(tx('cc_err').format(e=f"{bad[0]['expr']}: {_err_text(bad[0]['err'])}"))
            self.view.set_figure(fig, A)
            for ax in getattr(self.view, 'taxes', []):
                ax.callbacks.connect('xlim_changed', lambda a: QTimer.singleShot(0, self._stats))
            self._stats()
        self.view.busy()
        run_bg(job, on_done=done, on_fail=lambda e: self.view.set_message(str(e)))

    def _stats(self):
        from ..core import customchart as CC
        x0 = x1 = None
        if self.view.taxes:
            x0, x1 = self.view.taxes[0].get_xlim()
        rows = []
        thr = {}
        for r in self.res:
            if r.get('param') and r['panel'] not in thr: thr[r['panel']] = (r['param'], r['value'])
        for r in self.res:
            if r.get('t') is None: continue
            th = thr.get(r['panel'])
            s = CC.stats(r['t'], r['y'], x0, x1, th[1] if th else None)
            if not s: continue
            f = lambda v: f'{v:.3g}' if abs(v) < 1e5 else f'{v:.0f}'  # noqa: E731
            rows.append((r['label'], f(s['min']), fmt_t(s['tmin']), f(s['max']), fmt_t(s['tmax']), f(s['mean']),
                         f'{th[0]}={th[1]:g}' if th else '—', fmt_t(s['above']) if th else '—', fmt_t(s['below']) if th else '—', r.get('color')))
        self.st.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, v in enumerate(row[:9]):
                it = QTableWidgetItem(str(v))
                if j == 0 and row[9]: it.setForeground(QColor(row[9]))
                self.st.setItem(i, j, it)
        for j in range(1, 9): self.st.resizeColumnToContents(j)

    def _clicked(self, tt):
        try: self.win.pages['map'].goto_time(tt, switch=False)
        except Exception: pass
        try: self.win.pages['video'].goto_log_time(tt)
        except Exception: pass


# ====================================================================== Video ve OSD
class VideoPage(Page):
    frame_ready = Signal(object)

    def __init__(self, win):
        super().__init__(win)
        from .chartview import ChartView
        from ..core import vidsync as V, viz
        h = QHBoxLayout(self); h.setContentsMargins(16, 12, 16, 12)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 10, 0); lv.setSpacing(4)
        self.vids = [None, None]; self.off = [0.0, 0.0]; self.lab = []
        for i, k in enumerate(('v_main', 'v_second')):
            lv.addWidget(label(tx(k), 'h2'))
            r = QHBoxLayout(); b = button(tx('v_open'), lambda _=False, i=i: self.choose(i)); r.addWidget(b)
            x = button('✕', lambda _=False, i=i: self.unset(i), tip=tx('v_unset')); x.setMinimumWidth(44); r.addWidget(x)
            l = label(tx('v_none'), 'muted', wrap=True); r.addWidget(l, 1); self.lab.append(l); lv.addLayout(r)
        lv.addWidget(label(tx('v_help'), 'muted', wrap=True))
        r = QHBoxLayout(); r.addWidget(QLabel(tx('v_edit')))
        self.which = QComboBox(); self.which.addItems([tx('v_main'), tx('v_second')]); self.which.currentIndexChanged.connect(self._which)
        r.addWidget(self.which, 1); lv.addLayout(r)
        lv.addWidget(QLabel(tx('v_off')))
        r = QHBoxLayout()
        self.offsp = QDoubleSpinBox(); self.offsp.setRange(-200000, 200000); self.offsp.setDecimals(2); self.offsp.setSingleStep(0.1)
        self.offsp.valueChanged.connect(self._off_changed); r.addWidget(self.offsp, 1); lv.addLayout(r)
        r = QHBoxLayout()
        for d in (-1.0, -0.1, 0.1, 1.0):
            b = button(f'\u200e{d:+g} s', lambda _=False, d=d: self.offsp.setValue(self.offsp.value() + d)); r.addWidget(b, 1)
        lv.addLayout(r)
        lv.addWidget(button(tx('v_auto'), self.auto))
        self.ev = QComboBox(); lv.addWidget(self.ev)
        lv.addWidget(button(tx('v_ev'), self.sync_event)); lv.addWidget(button(tx('v_cur'), self.sync_cursor))
        self.osd_on = QCheckBox(tx('v_osd')); self.osd_on.setChecked(True); self.osd_on.toggled.connect(lambda *_: self._redraw()); lv.addWidget(self.osd_on)
        g = QGroupBox(tx('v_osd_items')); gl = QGridLayout(g); self.osd_cb = {}
        for j, k in enumerate(V.OSD_KEYS):
            c = QCheckBox(viz.tx(V.OSD_LBL[k], lang())); c.setChecked(True); c.toggled.connect(lambda *_: self._redraw()); gl.addWidget(c, j // 2, j % 2); self.osd_cb[k] = c
        lv.addWidget(g)
        self.follow = QCheckBox(tx('v_follow')); self.follow.setChecked(True); lv.addWidget(self.follow)
        # dışa aktarma
        g2 = QGroupBox(tx('v_exp')); g2l = QGridLayout(g2)
        g2l.addWidget(QLabel(tx('v_layout')), 0, 0); self.layout_cb = QComboBox()
        for k, v in (('single', 'v_l_single'), ('pip', 'v_l_pip'), ('side', 'v_l_side')): self.layout_cb.addItem(tx(v), k)
        g2l.addWidget(self.layout_cb, 0, 1)
        g2l.addWidget(QLabel(tx('v_range')), 1, 0); self.range_cb = QComboBox()
        for k, v in (('all', 'v_r_all'), ('flight', 'v_r_flight'), ('root', 'v_r_root')): self.range_cb.addItem(tx(v), k)
        g2l.addWidget(self.range_cb, 1, 1)
        g2l.addWidget(QLabel(tx('v_res')), 2, 0); self.res_cb = QComboBox()
        for w_ in (1280, 1920, 960): self.res_cb.addItem(f'{w_} px', w_)
        g2l.addWidget(self.res_cb, 2, 1)
        self.panel_cb = QCheckBox(tx('v_panel')); g2l.addWidget(self.panel_cb, 3, 0, 1, 2)
        self.b_exp = button(tx('v_exp'), self.export, primary=True); g2l.addWidget(self.b_exp, 4, 0, 1, 2)
        self.prog = QProgressBar(); self.prog.setVisible(False); g2l.addWidget(self.prog, 5, 0, 1, 2)
        self.b_cancel = button(tx('v_cancel'), self._cancel); self.b_cancel.setVisible(False); g2l.addWidget(self.b_cancel, 6, 0, 1, 2)
        g2l.setColumnStretch(1, 1)
        for c_ in (self.layout_cb, self.range_cb, self.res_cb): c_.setMinimumWidth(200)
        lv.addWidget(g2); lv.addStretch(1)
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.NoFrame); sa.setWidget(left); sa.setFixedWidth(440)
        left.setObjectName('vleft'); left.setMaximumWidth(424)
        sa.setStyleSheet('QScrollArea{background:transparent;border:none} QWidget#vleft{background:transparent}')
        sa.viewport().setAutoFillBackground(False)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        h.addWidget(sa)
        # sağ: video + kontroller + grafik
        sp = QSplitter(Qt.Vertical)
        top = QWidget(); tv = QVBoxLayout(top); tv.setContentsMargins(0, 0, 0, 0)
        self.screen = QLabel(); self.screen.setAlignment(Qt.AlignCenter); self.screen.setMinimumHeight(240)
        self.screen.setStyleSheet('background:#000;border-radius:8px'); self.screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tv.addWidget(self.screen, 1)
        r = QHBoxLayout()
        self.b_play = button(tx('v_play'), self.toggle_play); r.addWidget(self.b_play)
        self.speed = QComboBox(); [self.speed.addItem(f'{s}×', s) for s in (0.25, 0.5, 1.0, 2.0, 4.0)]; self.speed.setCurrentIndex(2); r.addWidget(self.speed)
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(0, 1000); self.slider.sliderReleased.connect(self._slider_seek); r.addWidget(self.slider, 1)
        self.tlab = QLabel('—'); self.tlab.setMinimumWidth(320); r.addWidget(self.tlab)
        tv.addLayout(r)
        sp.addWidget(top)
        bw = QWidget(); bv = QVBoxLayout(bw); bv.setContentsMargins(0, 0, 0, 0)
        r = QHBoxLayout(); r.addWidget(QLabel(tx('v_chart'))); self.chart_cb = QComboBox(); r.addWidget(self.chart_cb, 1); bv.addLayout(r)
        self.chart = ChartView(); self.chart.clicked.connect(self.goto_log_time); bv.addWidget(self.chart, 1)
        sp.addWidget(bw); sp.setSizes([560, 330]); h.addWidget(sp, 1)
        self.A = None; self.D = None; self.reader = None; self.q = None; self.vt = 0.0; self.frame = None
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick)
        self.sync_timer = QTimer(self); self.sync_timer.setInterval(250); self.sync_timer.timeout.connect(self._sync_out)
        self.frame_ready.connect(self._show_frame)
        self._export_cancel = False; self._chart_cache = {}
        self.chart_cb.currentIndexChanged.connect(self._chart_changed)

    # ------------------------------------------------------------ log
    def on_analysis(self, A):
        from ..core import vidsync as V, charts
        from .pages_a import CHART_KEYS
        from ..core.report import R
        self.stop(); self.A = A; self.D = None; self._chart_cache = {}
        self.ev.clear()
        for t_, n in V.event_list(A, lang()): self.ev.addItem(f'{fmt_t(t_)}  ·  {n}', t_)
        self.chart_cb.blockSignals(True); self.chart_cb.clear()
        for k in CHART_KEYS:
            if k in ('c_health', 'c_timeline', 'c_overview'): continue
            self.chart_cb.addItem(R(k, lang()), k)
        self.chart_cb.setCurrentIndex(0); self.chart_cb.blockSignals(False)
        self._chart_changed()
        self._restore()
        self._redraw()

    def _osd(self):
        from ..core import vidsync as V
        if self.D is None and self.A is not None: self.D = V.OSDData(self.A, lang())
        return self.D

    def _key(self):
        try: return os.path.basename(self.A.L.path) + f':{int(self.A.L.size)}'
        except Exception: return None

    def _persist(self):
        k = self._key()
        if not k: return
        st = self.win.settings.setdefault('video_sync', {})
        st[k] = {'paths': [v['path'] if v else None for v in self.vids], 'off': list(self.off)}
        if len(st) > 80:
            for kk in list(st)[:-80]: st.pop(kk, None)
        try: self.win.settings.save()
        except Exception: pass

    def _restore(self):
        from ..core import vidsync as V
        k = self._key(); d = (self.win.settings.get('video_sync') or {}).get(k) if k else None
        self.vids = [None, None]; self.off = [0.0, 0.0]
        if d:
            for i, p in enumerate(d.get('paths') or []):
                if p and os.path.isfile(p):
                    try: self.vids[i] = V.probe(p); self.off[i] = float(d['off'][i])
                    except Exception: pass
        self._labels(); self._which()

    def _labels(self):
        import time as _t
        for i, v in enumerate(self.vids):
            if not v: self.lab[i].setText(tx('v_none')); continue
            c = _t.strftime('%Y-%m-%d %H:%M:%S', _t.localtime(v['created'])) if v.get('created') else '—'
            self.lab[i].setText(os.path.basename(v['path']) + '\n' + tx('v_info').format(w=v['w'], h=v['h'], fps=v['fps'], d=fmt_t(v['dur']), c=c))

    # ------------------------------------------------------------ video seçimi ve eşleme
    def choose(self, i):
        from ..core import vidsync as V
        p, _ = QFileDialog.getOpenFileName(self, tx('v_open'), '', 'Video (*.mp4 *.mov *.avi *.mkv *.m4v *.ts *.mts *.webm);;*.*')
        if not p: return
        try: self.vids[i] = V.probe(p)
        except Exception as e: return error(self, str(e))
        self.off[i] = 0.0
        self.which.setCurrentIndex(i); self._which(); self._labels()
        if self.A is not None: self.auto(quiet=True)
        self._persist()
        if i == 0 or self.vids[0] is None: self.seek(0.0)

    def unset(self, i):
        if i == self.which.currentIndex(): self.stop()
        self.vids[i] = None; self._labels(); self._persist(); self._redraw()

    def _which(self, *_):
        i = self.which.currentIndex()
        self.offsp.blockSignals(True); self.offsp.setValue(self.off[i]); self.offsp.blockSignals(False)
        if self.vids[i]: self.seek(self.vt if self.vids[i] else 0.0)

    def cur(self):
        return self.vids[self.which.currentIndex()]

    def _off_changed(self, v):
        self.off[self.which.currentIndex()] = float(v); self._persist(); self._redraw()

    def auto(self, quiet=False):
        from ..core import vidsync as V
        v = self.cur()
        if not v or self.A is None: return
        o, src = V.auto_offset(self.A.L, v)
        if o is None:
            if not quiet: info(self, tx('v_auto_no'))
            return
        self.offsp.setValue(o)
        if not quiet: self.win.set_status(tx('v_auto_ok').format(o=o, s=src))

    def sync_event(self):
        if self.cur() is None or self.ev.currentData() is None: return
        self.offsp.setValue(float(self.ev.currentData()) - self.vt)

    def sync_cursor(self):
        tc = None
        for k in ('charts', 'custom'):
            try:
                c = self.win.pages[k].view.cursor_t
                if c is not None: tc = c; break
            except Exception: pass
        if tc is None: tc = self.chart.cursor_t
        if tc is None or self.cur() is None: return
        self.offsp.setValue(float(tc) - self.vt)

    def log_t(self):
        return self.vt + self.off[self.which.currentIndex()]

    # ------------------------------------------------------------ oynatma
    def goto_log_time(self, lt):
        v = self.cur()
        if v is None: return
        self.seek(float(lt) - self.off[self.which.currentIndex()])

    def seek(self, vt, play=None):
        v = self.cur()
        if v is None: self.screen.clear(); return
        was = self.timer.isActive() if play is None else play
        self.stop()
        self.vt = float(min(max(0.0, vt), max(0.0, v['dur'] - 0.05)))
        self._start_reader(self.vt)
        if was: self.play()
        else: self._next_frame(block=True)

    def _start_reader(self, vt):
        from ..core import vidsync as V
        v = self.cur()
        w = max(480, min(1280, self.screen.width() or 960))
        self.reader = V.FrameReader(v, w, min(30.0, v['fps']), vt)
        self.q = queue.Queue(maxsize=8); r = self.reader; q = self.q

        def pump():
            while True:
                f = r.read()
                try: q.put(f, timeout=30)
                except queue.Full: return
                if f is None: return
        threading.Thread(target=pump, daemon=True).start()

    def _next_frame(self, block=False):
        if self.q is None: return False
        try: f = self.q.get(timeout=3 if block else 0.001)
        except queue.Empty: return True
        if f is None: self.pause(); return False
        self.vt, self.frame = f
        self._redraw(); return True

    def play(self):
        if self.cur() is None: return
        if self.reader is None: self._start_reader(self.vt)
        fps = self.reader.fps; sp = float(self.speed.currentData() or 1.0)
        self.timer.start(max(5, int(1000 / fps / sp)))
        self.sync_timer.start(); self.b_play.setText(tx('v_pause'))

    def pause(self):
        self.timer.stop(); self.sync_timer.stop(); self.b_play.setText(tx('v_play'))

    def stop(self):
        self.pause()
        if self.reader is not None:
            try: self.reader.close()
            except Exception: pass
        self.reader = None; self.q = None

    def toggle_play(self):
        if self.timer.isActive(): self.pause()
        else: self.play()

    def _tick(self):
        self._next_frame()

    def _slider_seek(self):
        v = self.cur()
        if v: self.seek(self.slider.value() / 1000.0 * v['dur'])

    def _sync_out(self):
        if not self.follow.isChecked() or self.A is None: return
        lt = self.log_t()
        self.chart.set_cursor(lt)
        try: self.win.pages['map'].goto_time(lt, switch=False)
        except Exception: pass
        try: self.win.pages['charts'].set_cursor(lt)
        except Exception: pass

    def _show_frame(self, im):
        pass

    def _redraw(self):
        from ..core import vidsync as V
        v = self.cur()
        if v is None or self.frame is None:
            return
        fr = self.frame
        lt = self.log_t()
        if self.osd_on.isChecked() and self.A is not None:
            try:
                D = self._osd(); opts = [k for k, c in self.osd_cb.items() if c.isChecked()]
                fr = np.asarray(V.osd_frame(fr, D.sample(lt), opts, lang(), fmt_t))
            except Exception:
                import traceback; traceback.print_exc()
        fr = np.ascontiguousarray(fr)
        img = QImage(fr.data, fr.shape[1], fr.shape[0], fr.shape[1] * 3, QImage.Format_RGB888).copy()
        pm = QPixmap.fromImage(img).scaled(self.screen.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.screen.setPixmap(pm)
        if not self.slider.isSliderDown(): self.slider.setValue(int(self.vt / max(0.01, v['dur']) * 1000))
        outside = self.A is not None and not (-1 <= lt <= float(self.A.L.duration) + 1)
        self.tlab.setText(f'🎞 {fmt_t(self.vt)}   ·   LOG {fmt_t(lt)}' + ('   ⚠' if outside else ''))
        if not self.timer.isActive(): self.chart.set_cursor(lt)

    # ------------------------------------------------------------ alttaki grafik
    def _chart_changed(self, *_):
        from ..core import charts
        k = self.chart_cb.currentData()
        if not k or self.A is None: return
        if k in self._chart_cache: self.chart.set_figure(self._chart_cache[k], self.A); return
        A = self.A; lg = lang()
        fn = dict(charts.ALL).get(k)

        def job():
            charts.want_fig(True)
            try: return fn(A, lg) if fn else None
            finally: charts.want_fig(False)

        def done(fig):
            self._chart_cache[k] = fig
            if self.chart_cb.currentData() == k: self.chart.set_figure(fig, A)
        self.chart.busy(); run_bg(job, on_done=done, on_fail=lambda e: self.chart.set_message(str(e)))

    # ------------------------------------------------------------ dışa aktarma
    def export(self):
        from ..core import vidsync as V
        if self.A is None or self.vids[0] is None: return error(self, tx('v_need'))
        main = self.vids[0]; A = self.A
        off0 = self.off[0]
        rg = self.range_cb.currentData(); t0 = 0.0; t1 = main['dur']
        if rg == 'flight' and A.flights:
            t0 = A.flights[0][0] - off0 - 5; t1 = A.flights[-1][1] - off0 + 5
        elif rg == 'root':
            c = (A.root or {}).get('t') or (A.flights[-1][1] if A.flights else None)
            if c is not None: t0 = c - off0 - 30; t1 = c - off0 + 30
        t0 = max(0.0, t0); t1 = min(main['dur'], t1)
        if t1 - t0 < 0.5:
            return error(self, tx('v_out').format(a=fmt_t(0), b=fmt_t(A.L.duration)))
        base = os.path.splitext(os.path.basename(main['path']))[0] + '_OSD.mp4'
        out, _ = QFileDialog.getSaveFileName(self, tx('v_exp'), os.path.join(os.path.dirname(main['path']), base), 'MP4 (*.mp4)')
        if not out: return
        if not out.lower().endswith('.mp4'): out += '.mp4'
        self.pause()
        opts = [k for k, c in self.osd_cb.items() if c.isChecked()]
        kw = dict(second=self.vids[1], off_second=self.off[1], layout=self.layout_cb.currentData() if self.vids[1] else 'single',
                  osd=self.osd_on.isChecked(), osd_opts=opts, panel=self.panel_cb.isChecked(), t0=t0, t1=t1,
                  width=int(self.res_cb.currentData() or 1280), lg=lang())
        self._export_cancel = False
        self.prog.setVisible(True); self.prog.setRange(0, 1000); self.prog.setValue(0); self.b_cancel.setVisible(True); self.b_exp.setEnabled(False)
        holder = {}

        def job():
            return V.export(A, out, main, off0, progress=lambda p: holder['w'].progress.emit(p), cancel=lambda: self._export_cancel, **kw)

        def prog(p):
            self.prog.setValue(int(p['p'] * 1000))
            self.prog.setFormat(tx('v_prog').format(p=p['p'] * 100, n=p['n'], tot=p['tot'], fps=p['fps'], eta=fmt_t(p['eta'])))

        def fin(_ok=None, err=None):
            self.prog.setVisible(False); self.b_cancel.setVisible(False); self.b_exp.setEnabled(True)
            if err:
                if 'cancelled' not in str(err): error(self, str(err))
                return
            info(self, tx('v_done').format(p=out))
        holder['w'] = run_bg(job, on_done=lambda r: fin(r), on_fail=lambda e: fin(err=e), on_progress=prog)

    def _cancel(self):
        self._export_cancel = True
