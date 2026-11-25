"""v1.1.11 Sınav sekmesi parçaları: sınav hazırlama (soru sayısı, görselli grafik soruları, açık logdan üretim), kâğıt sınav
(kitapçık · QR'lı cevap anahtarı · optik form), optik okuma (dosya / telefon), telefonla sınav (aynı Wi-Fi) ve yorum puanlama."""
from __future__ import annotations
import html, os, random, time, uuid
from PySide6.QtCore import Qt, QTimer, QItemSelectionModel
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QSplitter, QTextBrowser, QDialog, QFileDialog, QCheckBox, QGridLayout,
                               QPlainTextEdit, QScrollArea, QFormLayout, QMessageBox)
from .i18n import lang, t
from .common import label, button, error, info, run_bg, open_path, ImageView

E = html.escape
TX = {
    'b_tab': ('📝 Sınav hazırla', '📝 Build exam', '📝 إعداد الاختبار'),
    'b_help': ('Soruları soldan seçip sınav kâğıdına ekleyin ya da soru sayısını yazıp "Otomatik doldur" deyin. Görselli grafik soruları gerçek kırım ve normal '
               'uçuşlardan; bir kısmında cevabı ele veren işaretler gizli, bir kısmında programın gerçek işaretli grafiği var. Açık logdan da yeni soru üretebilirsiniz.',
               'Pick questions on the left and add them to the exam paper, or type the number of questions and press "Auto-fill". Chart questions come from real crash '
               'and normal flights; some hide the tell-tale marks, others show the program\'s real annotated chart. You can also generate new questions from the open log.',
               'اختر الأسئلة من اليسار وأضفها إلى ورقة الاختبار، أو اكتب عدد الأسئلة واضغط "ملء تلقائي". أسئلة الرسوم من رحلات حقيقية انتهت بحادث أو طبيعية؛ '
               'بعضها يخفي العلامات الدالة على الجواب وبعضها يعرض رسم البرنامج الحقيقي المعلَّم. ويمكنك توليد أسئلة جديدة من السجل المفتوح.'),
    'title': ('Sınav adı', 'Exam title', 'عنوان الاختبار'), 'class': ('Sınıf', 'Class', 'الصف'), 'n': ('Soru sayısı', 'Number of questions', 'عدد الأسئلة'),
    'time': ('Süre (dk)', 'Time (min)', 'المدة (د)'), 'pass': ('Geçme %', 'Pass %', 'النجاح %'), 'lang': ('Sınav dili', 'Exam language', 'لغة الاختبار'),
    'shuffle': ('Soruları karıştır', 'Shuffle questions', 'خلط الأسئلة'),
    'src': ('Kaynak', 'Source', 'المصدر'),
    's_bank': ('Soru bankası (tümü)', 'Question bank (all)', 'بنك الأسئلة (الكل)'),
    's_vis': ('Görselli grafik soruları', 'Chart questions with images', 'أسئلة الرسوم مع صور'),
    's_gen': ('Üretilen sorular (açık log / senaryo)', 'Generated questions (open log / scenario)', 'الأسئلة المولَّدة (السجل المفتوح / سيناريو)'),
    'all': ('Tümü', 'All', 'الكل'), 'type': ('Tür', 'Type', 'النوع'), 'topic': ('Konu', 'Topic', 'الموضوع'), 'level': ('Seviye', 'Level', 'المستوى'),
    'found': ('{n} soru bulundu', '{n} questions found', 'وُجد {n} سؤالًا'),
    'ty_mc': ('Çoktan seçmeli', 'Multiple choice', 'اختيار من متعدد'), 'ty_open': ('Yorum (yazılı)', 'Interpretation (written)', 'تفسير (كتابي)'),
    'ty_img': ('Görselli', 'With image', 'مع صورة'),
    'case': ('Uçuş', 'Flight', 'الرحلة'), 'c_crash': ('Kırım', 'Crash', 'حادث'), 'c_normal': ('Normal', 'Normal', 'طبيعية'),
    'c_incident': ('Arıza, kırımsız', 'Fault, no crash', 'عطل بلا حادث'),
    'hint': ('İpucu', 'Hint', 'التلميح'), 'h_no': ('İpuçsuz (işaretler gizli)', 'No hint (marks hidden)', 'بلا تلميح (العلامات مخفية)'),
    'h_yes': ('Gerçek işaretli grafik', 'Real annotated chart', 'رسم حقيقي معلَّم'),
    'search': ('Ara…', 'Search…', 'ابحث…'),
    'add': ('Ekle →', 'Add →', '← أضف'), 'auto': ('🎲 Otomatik doldur', '🎲 Auto-fill', '🎲 ملء تلقائي'),
    'gen_log': ('⚙ Açık logdan soru üret', '⚙ Generate from open log', '⚙ توليد من السجل المفتوح'),
    'gen_scen': ('⚙ Senaryodan üret', '⚙ Generate from scenario', '⚙ توليد من سيناريو'),
    'to_bank': ('🗃 Seçilenleri bankaya kaydet', '🗃 Save selected to bank', '🗃 حفظ المحدد في البنك'),
    'paper': ('Sınav kâğıdı', 'Exam paper', 'ورقة الاختبار'), 'paper_n': ('{a} / {n} soru', '{a} / {n} questions', '{a} / {n} سؤالاً'),
    'up': ('▲', '▲', '▲'), 'down': ('▼', '▼', '▼'), 'rm': ('✕ Çıkar', '✕ Remove', '✕ إزالة'), 'clear': ('Temizle', 'Clear', 'مسح'),
    'save': ('💾 Sınavı kaydet', '💾 Save exam', '💾 حفظ الاختبار'),
    'save_paper': ('🖨 Kaydet + kâğıtları hazırla', '🖨 Save + make papers', '🖨 حفظ + إعداد الأوراق'),
    'saved': ('Sınav kaydedildi. Sınav kodu: {c}', 'Exam saved. Exam code: {c}', 'حُفظ الاختبار. رمز الاختبار: {c}'),
    'need_q': ('Sınav kâğıdında soru yok. Soru ekleyin ya da "Otomatik doldur" deyin.', 'The exam paper is empty. Add questions or press "Auto-fill".',
               'ورقة الاختبار فارغة. أضف أسئلة أو اضغط "ملء تلقائي".'),
    'need_class': ('Önce bir sınıf açın.', 'Create a class first.', 'أنشئ صفًا أولًا.'),
    'new_class': ('+ Sınıf', '+ Class', '+ صف'),
    'gen_done': ('{n} görselli soru üretildi (program teşhisine göre; kontrol edip düzenleyebilirsiniz).', '{n} questions with images generated (from the program\'s diagnosis; check and edit them).',
                 'وُلِّد {n} سؤالًا مع صور (حسب تشخيص البرنامج؛ راجعها وعدّلها).'),
    'to_bank_done': ('{n} soru bankaya kaydedildi.', '{n} questions saved to the bank.', 'حُفظ {n} سؤالًا في البنك.'),
    'cols': (('Tür', 'Konu', 'Seviye', 'Soru'), ('Type', 'Topic', 'Level', 'Question'), ('النوع', 'الموضوع', 'المستوى', 'السؤال')),
    'pcols': (('#', 'Tür', 'Soru'), ('#', 'Type', 'Question'), ('#', 'النوع', 'السؤال')),
    'model': ('Örnek cevap', 'Model answer', 'إجابة نموذجية'), 'kw': ('Aranan kavramlar', 'Key concepts', 'المفاهيم المطلوبة'),
    'zoom': ('Görsele tıklayın: büyür', 'Click the image to enlarge', 'انقر على الصورة لتكبيرها'),
    # kâğıt / okuma / telefon
    'p_paper': ('🖨 Kâğıt sınav (kitapçık · cevap anahtarı · optik form)', '🖨 Paper exam (booklet · answer key · answer sheet)', '🖨 اختبار ورقي (كراسة · مفتاح · ورقة إجابة)'),
    'p_scan': ('📷 Optik formları okut', '📷 Scan answer sheets', '📷 قراءة أوراق الإجابة'),
    'p_phone_scan': ('📱 Telefonla okut', '📱 Scan with phone', '📱 قراءة بالهاتف'),
    'p_live': ('📱 Telefonla sınav (aynı Wi-Fi)', '📱 Phone exam (same Wi-Fi)', '📱 اختبار بالهاتف (نفس Wi-Fi)'),
    'p_grade': ('✍ Yorumları puanla', '✍ Grade interpretations', '✍ تصحيح التفسيرات'),
    'p_dir': ('Kâğıtların kaydedileceği klasör', 'Folder for the papers', 'مجلد الأوراق'),
    'p_done': ('Hazır: kitapçık, cevap anahtarı (QR\'ı telefon kamerasıyla okunur) ve optik form.\n{p}',
               'Ready: booklet, answer key (its QR reads with a phone camera) and answer sheet.\n{p}', 'جاهز: الكراسة ومفتاح الإجابة (يُقرأ رمز QR بكاميرا الهاتف) وورقة الإجابة.\n{p}'),
    'p_copies': ('Optik form kopya sayısı', 'Answer sheet copies', 'عدد نسخ ورقة الإجابة'),
    'scan_pick': ('Formların fotoğrafları / taramaları', 'Photos / scans of the sheets', 'صور / مسوحات الأوراق'),
    'scan_done': ('{n} form okundu, {f} okunamadı.', '{n} sheets read, {f} could not be read.', 'قُرئت {n} ورقة وتعذّرت قراءة {f}.'),
    'scan_fail': ('{f}: okunamadı ({e}). Formu düz koyup dört köşe görünecek biçimde yeniden çekin.', '{f}: not read ({e}). Lay the sheet flat and shoot again with all four corners visible.',
                  '{f}: تعذّرت القراءة ({e}). ضع الورقة مستوية وأعد التصوير مع ظهور الزوايا الأربع.'),
    'l_title': ('Telefonla sınav ve okuma', 'Phone exam and scanning', 'الاختبار والقراءة بالهاتف'),
    'l_help_exam': ('Öğrenciler telefonu bu bilgisayarla aynı Wi-Fi ağına bağlayıp QR\'ı okutsun (ya da adresi yazsın), ad, numara ve sınav kodunu girsin. '
                    'Cevaplar her dokunuşta buraya yazılır; süre bitince otomatik teslim edilir.',
                    'Students join the same Wi-Fi as this computer, scan the QR (or type the address) and enter name, number and the exam code. '
                    'Answers are written here on every tap; they are submitted automatically when time runs out.',
                    'يتصل الطلاب بشبكة Wi-Fi نفسها لهذا الحاسوب ويمسحون رمز QR (أو يكتبون العنوان) ويدخلون الاسم والرقم ورمز الاختبار. '
                    'تُكتب الإجابات هنا عند كل لمسة وتُسلَّم تلقائيًا عند انتهاء الوقت.'),
    'l_help_scan': ('Telefonu aynı Wi-Fi ağına bağlayın, QR\'ı okutun, sınav kodunu yazın ve formların fotoğrafını çekin; her fotoğraf hemen puanlanır ve sonuçlara eklenir.',
                    'Connect the phone to the same Wi-Fi, scan the QR, type the exam code and photograph the sheets; each photo is scored at once and added to the results.',
                    'صِل الهاتف بشبكة Wi-Fi نفسها وامسح رمز QR واكتب رمز الاختبار وصوّر الأوراق؛ تُصحَّح كل صورة فورًا وتُضاف إلى النتائج.'),
    'l_code': ('Sınav kodu', 'Exam code', 'رمز الاختبار'),
    'l_cols': (('Ad', 'No', 'Durum', 'Cevaplanan', 'Sayfadan çıkış', '%'), ('Name', 'No', 'Status', 'Answered', 'Left page', '%'), ('الاسم', 'الرقم', 'الحالة', 'المُجاب', 'مغادرة الصفحة', '%')),
    'l_on': ('sınavda', 'in exam', 'في الاختبار'), 'l_done': ('teslim etti', 'submitted', 'سلّم'),
    'l_open': ('Girişe açık', 'Open for entry', 'مفتوح للدخول'), 'l_finish': ('Herkesi bitir', 'Finish everyone', 'إنهاء الجميع'),
    'l_re': ('Yeniden girişe izin ver', 'Allow re-entry', 'السماح بإعادة الدخول'), 'l_stop': ('Durdur', 'Stop', 'إيقاف'),
    'l_scans': ('Telefondan okunan formlar', 'Sheets scanned by phone', 'الأوراق المقروءة بالهاتف'),
    'l_port': ('Sunucu açılamadı (port). Güvenlik duvarı izin vermiyor olabilir.', 'Server could not start (port). A firewall may be blocking it.', 'تعذّر تشغيل الخادم (المنفذ). قد يمنعه جدار الحماية.'),
    'g_title': ('Yorumları puanla', 'Grade interpretations', 'تصحيح التفسيرات'),
    'g_none': ('Bu sonuçta yorum (açık uçlu) sorusu yok.', 'This result has no interpretation (open) questions.', 'لا توجد أسئلة تفسير في هذه النتيجة.'),
    'g_ans': ('Öğrencinin cevabı', 'Student\'s answer', 'إجابة الطالب'), 'g_paper': ('(kâğıt üzerinde — kitapçıktan okuyup puanlayın)', '(on paper — read it in the booklet and grade)', '(على الورق — اقرأها في الكراسة وصحّحها)'),
    'g_auto': ('Kavram önerisi: {s} ({h})', 'Concept suggestion: {s} ({h})', 'اقتراح المفاهيم: {s} ({h})'),
    'g_pts': ('Puan', 'Points', 'الدرجة'), 'g_saved': ('Puanlar kaydedildi: {s}/{n} (%{p})', 'Points saved: {s}/{n} ({p}%)', 'حُفظت الدرجات: {s}/{n} ({p}%)'),
    'g_pick': ('Önce sonuç tablosundan bir öğrenci seçin.', 'Pick a student in the results table first.', 'اختر طالبًا من جدول النتائج أولًا.'),
    'via': ('Yol', 'Via', 'الطريقة'), 'via_omr': ('optik', 'sheet', 'ضوئي'), 'via_phone': ('telefon', 'phone', 'هاتف'), 'via_pc': ('bilgisayar', 'computer', 'حاسوب'),
    'pending': ('Puanlanacak', 'To grade', 'بانتظار التصحيح'),
    'open_q': ('✎ Yorumunuzu yazın: grafikte ne görüyorsunuz, sorun ne zaman ve neden başladı, ne önerirsiniz?',
               '✎ Write your interpretation: what do you see, when and why did the problem start, what do you recommend?',
               '✎ اكتب تفسيرك: ماذا ترى في الرسم، ومتى ولماذا بدأت المشكلة، وما توصيتك؟'),
}


def tx(k, **a):
    v = TX[k]
    if isinstance(v[0], tuple): return v[('tr', 'en', 'ar').index(lang()) if lang() in ('tr', 'en', 'ar') else 0]
    s = v[('tr', 'en', 'ar').index(lang()) if lang() in ('tr', 'en', 'ar') else 0]
    return s.format(**a) if a else s


# ------------------------------------------------------------------ görsel
def zoom(parent, raw):
    dl = QDialog(parent); dl.setWindowTitle(t('app')); dl.resize(1280, 860)
    v = QVBoxLayout(dl); iv = ImageView(); v.addWidget(iv); iv.set_png(raw)
    dl.exec()


class ImgLabel(QLabel):
    """Soru görseli: genişliğe sığar, tıklayınca büyür."""
    def __init__(self, max_h=420):
        super().__init__(); self.raw = None; self.max_h = max_h
        self.setAlignment(Qt.AlignCenter); self.setCursor(Qt.PointingHandCursor); self.setToolTip(tx('zoom'))
        self.setStyleSheet('background:white;border-radius:8px;'); self.setVisible(False)

    def set_ref(self, ref):
        from ..core import qbank as QB
        self.set_raw(QB.img_bytes(ref) if ref else None)

    def set_raw(self, raw):
        self.raw = raw
        if not raw: self.clear(); self.setVisible(False); return
        pm = QPixmap(); pm.loadFromData(raw)
        w = max(320, min(1100, (self.parentWidget().width() if self.parentWidget() else 900) - 40))
        pm = pm.scaledToWidth(w, Qt.SmoothTransformation)
        if pm.height() > self.max_h: pm = pm.scaledToHeight(self.max_h, Qt.SmoothTransformation)
        self.setPixmap(pm); self.setVisible(True)

    def mousePressEvent(self, e):
        if self.raw: zoom(self, self.raw)


def q_html(q, lg, show_answer=True):
    """Bank sorusunun önizlemesi (görsel ayrı gösterilir)."""
    from ..core import qbank as QB
    d = 'rtl' if lg == 'ar' else 'ltr'
    meta = ' · '.join(x for x in (QB.topic_name(q.get('topic'), lg), QB.level_name(q.get('level'), lg), q.get('src', '')) if x)
    h = [f'<div dir="{d}"><p style="color:#94A3B8">{E(meta)}</p><h3>{E(QB.tx(q["q"], lg))}</h3>']
    if QB.is_open(q):
        if show_answer:
            h.append(f'<p><b>{E(tx("model"))}:</b> {E(QB.tx(q.get("model"), lg))}</p>')
            kw = (q.get('kw') or {}).get(lg) or (q.get('kw') or {}).get('en') or []
            if kw: h.append(f'<p style="color:#94A3B8">{E(tx("kw"))}: {E(" · ".join(g.replace("|", " / ") for g in kw))}</p>')
    else:
        h.append('<ol>')
        for i, o in enumerate(q['opts']):
            ok = show_answer and i == int(q.get('ans', 0))
            h.append(f'<li style="{"color:#4ADE80;font-weight:700" if ok else ""}">{"✔ " if ok else ""}{E(QB.tx(o, lg))}</li>')
        h.append('</ol>')
        if show_answer and q.get('exp'): h.append(f'<p>{E(QB.tx(q.get("exp"), lg))}</p>')
    return ''.join(h) + '</div>'


def _type_txt(q):
    from ..core import qbank as QB
    s = '✎' if QB.is_open(q) else '☑'
    if q.get('img'): s += ' 🖼'
    if (q.get('case') or {}).get('hint'): s += ' ⚑'
    return s


def scroll(inner):
    """Tema rengini koruyan (saydam) kaydırma alanı."""
    sa = QScrollArea(); sa.setWidgetResizable(True); sa.setObjectName('fcNavScroll'); sa.setFrameShape(QScrollArea.NoFrame)
    inner.setObjectName('root'); sa.setWidget(inner); sa.viewport().setAutoFillBackground(False)
    return sa


def _tbl(cols, stretch):
    tb = QTableWidget(0, len(cols)); tb.setHorizontalHeaderLabels(list(cols))
    tb.verticalHeader().setVisible(False); tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tb.setSelectionBehavior(QAbstractItemView.SelectRows); tb.setSelectionMode(QAbstractItemView.ExtendedSelection)
    tb.setWordWrap(False); hh = tb.horizontalHeader()
    for i in range(len(cols)): hh.setSectionResizeMode(i, QHeaderView.Stretch if i == stretch else QHeaderView.ResizeToContents)
    return tb


def _select_row(tb, r):
    tb.setCurrentCell(r, 0, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)


# ------------------------------------------------------------------ sınav hazırlama
class ExamBuilder(QWidget):
    def __init__(self, page):
        super().__init__(); self.page = page; self.win = page.win
        from ..core import qbank as QB
        self.B = QB; self.sheet = []; self.gen = []; self.rows = []; self.last_exam = None
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(label(tx('b_help'), 'muted', wrap=True))
        g = QGridLayout(); g.setHorizontalSpacing(8)
        self.ti = QLineEdit(); self.ti.setPlaceholderText(time.strftime('%Y-%m-%d'))
        self.cls = QComboBox(); self.cls.setMinimumWidth(180)
        self.n = QSpinBox(); self.n.setRange(1, 100); self.n.setValue(20); self.n.valueChanged.connect(self._count)
        self.tl = QSpinBox(); self.tl.setRange(0, 300); self.tl.setValue(40)
        self.pm = QSpinBox(); self.pm.setRange(1, 100); self.pm.setValue(70)
        self.lg = QComboBox()
        for code, nm in (('tr', 'Türkçe'), ('en', 'English'), ('ar', 'العربية')): self.lg.addItem(nm, code)
        self.lg.setCurrentIndex(max(0, self.lg.findData(lang())))
        self.shuf = QCheckBox(tx('shuffle'))
        items = [(tx('title'), self.ti), (tx('class'), self.cls), (tx('n'), self.n), (tx('time'), self.tl), (tx('pass'), self.pm), (tx('lang'), self.lg)]
        for i, (k, w) in enumerate(items):
            g.addWidget(QLabel(k), 0, i); g.addWidget(w, 1, i)
        g.addWidget(button(tx('new_class'), self._new_class), 1, len(items)); g.addWidget(self.shuf, 1, len(items) + 1)
        g.setColumnStretch(0, 2); g.setColumnStretch(1, 1)
        v.addLayout(g)
        sp = QSplitter(Qt.Horizontal)
        # --- kaynak
        lw = QWidget(); lv = QVBoxLayout(lw); lv.setContentsMargins(0, 0, 0, 0)
        f1 = QHBoxLayout()
        self.src = QComboBox()
        for k in ('s_vis', 's_bank', 's_gen'): self.src.addItem(tx(k), k)
        self.src.setMinimumWidth(230)
        self.top = QComboBox(); self.top.addItem(f"{tx('topic')}: {tx('all')}", None)
        for k in QB.TOPICS: self.top.addItem(QB.topic_name(k, lang()), k)
        self.lvl = QComboBox(); self.lvl.addItem(f"{tx('level')}: {tx('all')}", None)
        for k in (1, 2, 3): self.lvl.addItem(QB.level_name(k, lang()), k)
        self.typ = QComboBox()
        for k, d in (('all', None), ('ty_mc', 'mc'), ('ty_open', 'open'), ('ty_img', 'img')): self.typ.addItem(f"{tx('type')}: {tx(k)}" if d is None else tx(k), d)
        for w_ in (self.src, self.top, self.lvl, self.typ): f1.addWidget(w_)
        lv.addLayout(f1)
        f2 = QHBoxLayout()
        self.case = QComboBox()
        for k, d in (('all', None), ('c_crash', 'crash'), ('c_normal', 'normal'), ('c_incident', 'incident')): self.case.addItem(f"{tx('case')}: {tx(k)}", d)
        self.hint = QComboBox()
        for k, d in (('all', None), ('h_no', False), ('h_yes', True)): self.hint.addItem(f"{tx('hint')}: {tx(k)}", d)
        self.q = QLineEdit(); self.q.setPlaceholderText(tx('search')); self.q.setClearButtonEnabled(True)
        f2.addWidget(self.case); f2.addWidget(self.hint); f2.addWidget(self.q, 1)
        lv.addLayout(f2)
        self.cand = _tbl(tx('cols'), 3); lv.addWidget(self.cand, 1)
        f3 = QHBoxLayout()
        self.cnt = label('', 'muted'); f3.addWidget(self.cnt); f3.addStretch(1)
        f3.addWidget(button(tx('gen_log'), self._gen_log)); f3.addWidget(button(tx('gen_scen'), self._gen_scen))
        self.b_bank = button(tx('to_bank'), self._to_bank); f3.addWidget(self.b_bank)
        f3.addWidget(button(tx('add'), self._add, primary=True))
        lv.addLayout(f3)
        sp.addWidget(lw)
        # --- kâğıt
        rw = QWidget(); rv = QVBoxLayout(rw); rv.setContentsMargins(0, 0, 0, 0)
        h = QHBoxLayout(); h.addWidget(label(tx('paper'), 'h2')); self.pcnt = label('', 'muted'); h.addWidget(self.pcnt); h.addStretch(1)
        h.addWidget(button(tx('auto'), self._auto, primary=True)); rv.addLayout(h)
        self.ptb = _tbl(tx('pcols'), 2); rv.addWidget(self.ptb, 1)
        h2 = QHBoxLayout()
        for k, fn in (('up', lambda: self._move(-1)), ('down', lambda: self._move(1)), ('rm', self._rm), ('clear', self._clear)): h2.addWidget(button(tx(k), fn))
        h2.addStretch(1); rv.addLayout(h2)
        h3 = QHBoxLayout(); h3.addStretch(1)
        h3.addWidget(button(tx('save'), lambda: self._save(False), primary=True)); h3.addWidget(button(tx('save_paper'), lambda: self._save(True)))
        rv.addLayout(h3)
        sp.addWidget(rw); sp.setSizes([760, 560])
        vs = QSplitter(Qt.Vertical); vs.addWidget(sp)
        pw = QWidget(); pv = QVBoxLayout(pw); pv.setContentsMargins(0, 0, 0, 0)
        inner = QWidget(); iv = QVBoxLayout(inner)
        self.img = ImgLabel(380); self.view = QTextBrowser(); self.view.setMinimumHeight(120)
        iv.addWidget(self.img); iv.addWidget(self.view, 1); pv.addWidget(scroll(inner))
        vs.addWidget(pw); vs.setSizes([430, 420])
        v.addWidget(vs, 1)
        for w_ in (self.src, self.top, self.lvl, self.typ, self.case, self.hint): w_.currentIndexChanged.connect(self.fill)
        self.q.textChanged.connect(self.fill)
        self.cand.itemSelectionChanged.connect(lambda: self._preview(self._cand_cur()))
        self.ptb.itemSelectionChanged.connect(lambda: self._preview(self._paper_cur()))
        self.cand.doubleClicked.connect(lambda *_: self._add())

    # ---------------------------------------------------------------- veri
    def refresh(self):
        cur = self.cls.currentData()
        self.cls.blockSignals(True); self.cls.clear()
        for c in self.win.archive.rec_list('class'): self.cls.addItem(c['name'], c['id'])
        if cur: self.cls.setCurrentIndex(max(0, self.cls.findData(cur)))
        self.cls.blockSignals(False)
        self.fill(); self._paper()

    def _pool(self):
        s = self.src.currentData()
        if s == 's_gen': return list(self.gen)
        qs = self.B.load(self.win.archive)
        if s == 's_vis': qs = [q for q in qs if q.get('img')]
        return qs

    def fill(self, *_):
        from ..core import msgsearch as MS
        lg = lang(); B = self.B
        t_, l_, y_, c_, h_ = self.top.currentData(), self.lvl.currentData(), self.typ.currentData(), self.case.currentData(), self.hint.currentData()
        ws = MS.words(self.q.text()); out = []
        on = {q['id'] for q in self.sheet}
        for q in self._pool():
            if q['id'] in on: continue
            if t_ and q.get('topic') != t_: continue
            if l_ and int(q.get('level', 1)) != l_: continue
            if y_ == 'mc' and B.is_open(q): continue
            if y_ == 'open' and not B.is_open(q): continue
            if y_ == 'img' and not q.get('img'): continue
            cs = q.get('case') or {}
            if c_ and cs.get('label') != c_: continue
            if h_ is not None and bool(cs.get('hint')) != h_: continue
            if ws:
                blob = MS.norm(' '.join([q['id'], q.get('src', '')] + [B.tx(q['q'], x) for x in B.LANGS] + [B.tx(o, x) for o in q.get('opts') or [] for x in B.LANGS]))
                if not all(w in blob for w in ws): continue
            out.append(q)
        self.rows = out
        tb = self.cand; tb.setUpdatesEnabled(False); tb.setRowCount(len(out))
        for i, q in enumerate(out):
            for j, val in enumerate((_type_txt(q), B.topic_name(q.get('topic'), lg), B.level_name(q.get('level'), lg), B.tx(q['q'], lg))):
                it = QTableWidgetItem(val)
                if j == 3: it.setToolTip(val)
                tb.setItem(i, j, it)
        tb.setUpdatesEnabled(True)
        self.cnt.setText(tx('found', n=len(out)))
        self.b_bank.setVisible(self.src.currentData() == 's_gen')

    def _cand_cur(self):
        r = self.cand.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def _paper_cur(self):
        r = self.ptb.currentRow()
        return self.sheet[r] if 0 <= r < len(self.sheet) else None

    def _preview(self, q):
        if not q: return
        lg = self.lg.currentData() or lang()
        self.img.set_ref(q.get('img')); self.view.setHtml(q_html(q, lg))

    def _paper(self):
        lg = lang(); tb = self.ptb; tb.setRowCount(len(self.sheet))
        for i, q in enumerate(self.sheet):
            for j, val in enumerate((str(i + 1), _type_txt(q), self.B.tx(q['q'], lg))):
                it = QTableWidgetItem(val)
                if j == 2: it.setToolTip(val)
                tb.setItem(i, j, it)
        self._count()

    def _count(self, *_):
        a, n = len(self.sheet), self.n.value()
        self.pcnt.setText(tx('paper_n', a=a, n=n)); self.pcnt.setStyleSheet('color:#F87171' if a > n else '')

    # ---------------------------------------------------------------- düzenleme
    def _add(self):
        rs = sorted({ix.row() for ix in self.cand.selectedIndexes()}) or ([self.cand.currentRow()] if self.cand.currentRow() >= 0 else [])
        for r in rs:
            if r < len(self.rows): self.sheet.append(self.rows[r])
        self.fill(); self._paper()
        if self.sheet: _select_row(self.ptb, len(self.sheet) - 1)

    def _auto(self):
        need = self.n.value() - len(self.sheet)
        if need <= 0: return
        pool = list(self.rows)
        by = {}
        for q in pool: by.setdefault((q.get('topic'), (q.get('case') or {}).get('label')), []).append(q)
        rnd = random.Random()
        for v_ in by.values(): rnd.shuffle(v_)
        keys = list(by); rnd.shuffle(keys); pick = []
        while len(pick) < need and any(by.values()):
            for k in keys:
                if by[k] and len(pick) < need: pick.append(by[k].pop())
        self.sheet += pick; self.fill(); self._paper()

    def _move(self, d):
        r = self.ptb.currentRow()
        if not (0 <= r < len(self.sheet)) or not (0 <= r + d < len(self.sheet)): return
        self.sheet[r], self.sheet[r + d] = self.sheet[r + d], self.sheet[r]; self._paper(); _select_row(self.ptb, r + d)

    def _rm(self):
        rs = sorted({ix.row() for ix in self.ptb.selectedIndexes()}, reverse=True)
        for r in rs:
            if r < len(self.sheet): self.sheet.pop(r)
        self.fill(); self._paper()

    def _clear(self):
        self.sheet = []; self.fill(); self._paper()

    def _new_class(self):
        self.page.new_class(); self.refresh()

    # ---------------------------------------------------------------- üretim
    def _gen(self, A, name):
        from ..core import visq
        imgs = {}
        base = 'G-' + uuid.uuid4().hex[:6].upper()
        qs = visq.make(A, base, kind='open', lang=self.lg.currentData() or lang(), name=name, images=imgs)
        for q in qs:
            k = q['img'][1:]; q['img'] = visq.data_uri(imgs[k]) if k in imgs else None
            q['origin'] = 'user'
        return qs

    def _gen_done(self, qs):
        self.gen = qs + self.gen
        self.src.setCurrentIndex(self.src.findData('s_gen')); self.fill()
        info(self, tx('gen_done', n=len(qs)))

    def _gen_log(self):
        A = self.win.A
        if A is None: return error(self, t('no_log'))
        run_bg(self._gen, A, os.path.basename(A.L.path), on_done=self._gen_done, on_fail=lambda e: error(self, e))

    def _gen_scen(self):
        from ..core import synth
        from PySide6.QtWidgets import QInputDialog
        sc, ok = QInputDialog.getItem(self, tx('gen_scen'), tx('src'), synth.SCENARIOS, 1, False)
        if not ok: return

        def job():
            import tempfile
            from ..core import loader, analysis
            p = os.path.join(tempfile.mkdtemp(), sc + '.BIN'); synth.generate(p, sc)
            return self._gen(analysis.Analysis(loader.load(p, use_cache=False)), sc)
        run_bg(job, on_done=self._gen_done, on_fail=lambda e: error(self, e))

    def _to_bank(self):
        rs = sorted({ix.row() for ix in self.cand.selectedIndexes()})
        n = 0
        for r in rs:
            if r < len(self.rows):
                try: self.B.save(self.win.archive, dict(self.rows[r])); n += 1
                except Exception: pass
        info(self, tx('to_bank_done', n=n))

    # ---------------------------------------------------------------- kaydet
    def _save(self, papers):
        from ..core import exam as X
        cid = self.cls.currentData()
        if not cid:
            self.page.new_class(); self.refresh(); cid = self.cls.currentData()
            if not cid: return info(self, tx('need_class'))
        if not self.sheet:
            self._auto()
            if not self.sheet: return info(self, tx('need_q'))
        lg = self.lg.currentData() or lang(); rnd = random.Random()
        src = list(self.sheet)
        if self.shuf.isChecked(): rnd.shuffle(src)
        qs = [self.B.to_item(q, lg, rnd) for q in src]
        title = self.ti.text().strip() or time.strftime('%Y-%m-%d')
        eid = X.create_exam(self.win.archive, cid, title, None, lg, len(qs), self.tl.value(), self.pm.value(), {'type': 'builder', 'n': len(qs)}, questions=qs)
        ex = self.win.archive.rec_get('exam', eid); self.last_exam = ex
        self.page.refresh()
        if papers: make_papers(self, ex, self.win)
        else: info(self, tx('saved', c=ex.get('code', '')))


# ------------------------------------------------------------------ kâğıt sınav
def make_papers(parent, ex, win):
    from ..core import paper
    d = QFileDialog.getExistingDirectory(parent, tx('p_dir'), os.path.expanduser('~'))
    if not d: return
    from PySide6.QtWidgets import QInputDialog
    cp, ok = QInputDialog.getInt(parent, tx('p_paper'), tx('p_copies'), 30, 1, 300)
    if not ok: return
    safe = ''.join(c for c in ex.get('title', 'sinav') if c not in '\\/:*?"<>|').strip()[:50] or 'sinav'
    base = os.path.join(d, f"{safe}_{ex.get('code', '')}")
    lh = win.settings.letterhead()

    def job():
        paper.booklet_pdf(ex, base + '_kitapcik.pdf', lh)
        paper.key_pdf(ex, base + '_cevap_anahtari.pdf', lh)
        paper.sheet_pdf(ex, base + '_optik_form.pdf', (lh or {}).get('org', ''), cp)
        return d
    run_bg(job, on_done=lambda p: (info(parent, tx('p_done', p=p)), open_path(p)), on_fail=lambda e: error(parent, e))


def scan_files(parent, ex, win, on_done=None):
    from ..core import exam as X
    ex = X.ensure_code(win.archive, ex)
    fs, _ = QFileDialog.getOpenFileNames(parent, tx('scan_pick'), os.path.expanduser('~'), 'Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)')
    if not fs: return
    cl = win.archive.rec_get('class', ex.get('class_id')) or {}

    def job():
        from ..core import omr, paper
        n_opts = max([len(q['opts']) for q in ex['questions'] if q.get('type') != 'open'] or [4])
        ok = 0; bad = []
        for f in fs:
            r = omr.read(f, len(ex['questions']), n_opts)
            if not r['ok']: bad.append((os.path.basename(f), r['err'])); continue
            paper.grade_sheet(win.archive, ex, r, cl.get('students', [])); ok += 1
        return ok, bad

    def done(res):
        ok, bad = res
        msg = tx('scan_done', n=ok, f=len(bad))
        if bad: msg += '\n\n' + '\n'.join(tx('scan_fail', f=f, e=e) for f, e in bad[:12])
        info(parent, msg)
        if on_done: on_done()
    run_bg(job, on_done=done, on_fail=lambda e: error(parent, e))


# ------------------------------------------------------------------ telefon
def canli_of(win):
    from ..core import canli, paths
    if getattr(win, '_canli', None) is None:
        win._canli = canli.Canli(win.archive, paths.data_dir())
    return win._canli


def _qr_pix(text, size=220):
    import io, qrcode
    q = qrcode.QRCode(box_size=8, border=2); q.add_data(text); q.make(fit=True)
    b = io.BytesIO(); q.make_image(fill_color='black', back_color='white').save(b, format='PNG')
    pm = QPixmap(); pm.loadFromData(b.getvalue())
    return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class LiveDialog(QDialog):
    """Telefonla sınav (mode='exam') ya da telefonla optik okuma (mode='scan') paneli."""
    def __init__(self, parent, win, ex, mode='exam', on_change=None):
        super().__init__(parent); self.win = win; self.ex = ex; self.mode = mode; self.on_change = on_change
        self.setWindowTitle(tx('l_title')); self.resize(980, 680)
        from ..core import exam as X
        self.ex = X.ensure_code(win.archive, ex)
        cl = win.archive.rec_get('class', self.ex.get('class_id')) or {}
        self.C = canli_of(win)
        try:
            if mode == 'exam': self.C.start(self.ex, cl.get('students', []))
            else: self.C.set_scan(self.ex, cl.get('students', []))
        except OSError:
            error(parent, tx('l_port')); QTimer.singleShot(0, self.reject); return
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.qr = QLabel(); self.qr.setStyleSheet('background:white;border-radius:8px;padding:6px'); top.addWidget(self.qr)
        tv = QVBoxLayout()
        tv.addWidget(label(self.ex.get('title', ''), 'h1'))
        self.code = label('', 'h1'); tv.addWidget(self.code)
        self.url = label('', sel=True); self.url.setTextInteractionFlags(Qt.TextSelectableByMouse); tv.addWidget(self.url)
        tv.addWidget(label(tx('l_help_exam' if mode == 'exam' else 'l_help_scan'), 'muted', wrap=True)); tv.addStretch(1)
        top.addLayout(tv, 1); v.addLayout(top)
        if mode == 'exam':
            self.tb = _tbl(tx('l_cols'), 0); v.addWidget(self.tb, 1)
            h = QHBoxLayout()
            self.chk = QCheckBox(tx('l_open')); self.chk.setChecked(True); self.chk.toggled.connect(self.C.set_open); h.addWidget(self.chk)
            h.addWidget(button(tx('l_re'), self._re)); h.addStretch(1)
            h.addWidget(button(tx('l_finish'), self._finish)); h.addWidget(button(tx('l_stop'), self.accept, primary=True))
            v.addLayout(h)
        else:
            v.addWidget(label(tx('l_scans'), 'h2'))
            self.log = QTextBrowser(); v.addWidget(self.log, 1)
            h = QHBoxLayout(); h.addStretch(1); h.addWidget(button(tx('l_stop'), self.accept, primary=True)); v.addLayout(h)
        self.tm = QTimer(self); self.tm.setInterval(1500); self.tm.timeout.connect(self._tick); self.tm.start()
        self._last = None; self._tick()

    def _tick(self):
        st = self.C.status(); urls = st['urls']
        u = (urls[0] if urls else '') + ('' if self.mode == 'exam' else 'okut')
        if u != getattr(self, '_u', None):
            self._u = u; self.qr.setPixmap(_qr_pix(u or 'http://'))
        self.url.setText('  ·  '.join(x + ('' if self.mode == 'exam' else 'okut') for x in urls))
        self.code.setText(f"{tx('l_code')}: {self.ex.get('code', '')}")
        sig = repr((st['session'] or {}).get('students')) + repr(st['scans'])
        if sig == self._last: return
        self._last = sig
        if self.mode == 'exam' and st['session']:
            S = st['session']['students']; self.students = S
            self.tb.setRowCount(len(S))
            for i, s in enumerate(S):
                vals = (s['ad'], s['no'], tx('l_done') if s['done'] else tx('l_on'), f"{s['answered']}/{st['session']['n']}", str(s.get('olay') or ''),
                        '' if s.get('pct') is None else f"{s['pct']:.0f}")
                for j, val in enumerate(vals):
                    it = QTableWidgetItem(val)
                    if j == 2: it.setForeground(QColor('#4ADE80' if s['done'] else '#60A5FA'))
                    if j == 4 and s.get('olay'): it.setForeground(QColor('#FBBF24'))
                    self.tb.setItem(i, j, it)
        elif self.mode == 'scan':
            rows = []
            for x in reversed(st['scans']):
                tt = time.strftime('%H:%M:%S', time.localtime(x['t']))
                rows.append(f"<p style='color:#4ADE80'>{tt} ✅ {E(x['student'])} — {x['score']}/{x['total']} (%{x['pct']:.0f})</p>" if x['ok']
                            else f"<p style='color:#F87171'>{tt} ✘ {E(x.get('err', ''))}</p>")
            self.log.setHtml(''.join(rows))
        if self.on_change: self.on_change()

    def _re(self):
        r = self.tb.currentRow()
        if 0 <= r < len(getattr(self, 'students', [])): self.C.allow_re(self.students[r]['id'], True)

    def _finish(self):
        if QMessageBox.question(self, t('app'), tx('l_finish') + '?') == QMessageBox.Yes: self.C.finish_all()

    def done(self, r):
        try:
            self.tm.stop()
            if self.mode == 'exam': self.C.finish_all() if QMessageBox.question(self, t('app'), tx('l_finish') + '?') == QMessageBox.Yes else None
            self.C.stop()
        except Exception:
            pass
        if self.on_change: self.on_change()
        super().done(r)


# ------------------------------------------------------------------ yorum puanlama
class GradeDialog(QDialog):
    def __init__(self, parent, win, result):
        super().__init__(parent); self.win = win; self.r = result
        from ..core import exam as X
        self.X = X; self.ex = win.archive.rec_get('exam', result['exam_id']) or {}
        self.setWindowTitle(tx('g_title') + ' — ' + result.get('student', '')); self.resize(1100, 820)
        v = QVBoxLayout(self); inner = QWidget(); iv = QVBoxLayout(inner)
        self.combos = {}
        auto = result.get('auto') or X.auto_scores(self.ex, result.get('answers', []))
        man = result.get('manual') or {}
        lg = self.ex.get('lang', lang())
        for i, q in enumerate(self.ex.get('questions', [])):
            if q.get('type') != 'open': continue
            k = str(i)
            iv.addWidget(label(f"{i + 1}. {q['q']}", 'h2', wrap=True))
            if q.get('img'):
                im = ImgLabel(260); iv.addWidget(im); im.set_ref(q['img'])
            ans = (result.get('answers') or [''] * (i + 1))[i] if i < len(result.get('answers') or []) else ''
            ans = ans if isinstance(ans, str) else ''
            iv.addWidget(label(f"<b>{E(tx('g_ans'))}:</b> " + (E(ans) if ans.strip() else f"<i>{E(tx('g_paper'))}</i>"), wrap=True))
            iv.addWidget(label(f"<b>{E(tx('model'))}:</b> {E(q.get('model') or q.get('exp', ''))}", 'muted', wrap=True))
            a = auto.get(k) or {}
            if ans.strip():
                iv.addWidget(label(tx('g_auto', s=f"{a.get('pts', 0):g}", h=' · '.join(g.split('|')[0] for g in a.get('hit', [])) or '-'), 'muted', wrap=True))
            h = QHBoxLayout(); h.addWidget(QLabel(tx('g_pts')))
            cb = QComboBox()
            for p in (0.0, 0.5, 1.0): cb.addItem(f'{p:g}', p)
            cur = float(man[k]) if k in man else float(a.get('pts', 0) if ans.strip() else 0)
            cb.setCurrentIndex(max(0, cb.findData(cur))); h.addWidget(cb); h.addStretch(1); iv.addLayout(h)
            self.combos[k] = cb
            sep = QLabel(); sep.setFixedHeight(1); sep.setStyleSheet('background:#334155'); iv.addWidget(sep)
        if not self.combos: iv.addWidget(label(tx('g_none'), 'muted'))
        iv.addStretch(1); v.addWidget(scroll(inner), 1)
        h = QHBoxLayout(); h.addStretch(1); h.addWidget(button(t('cancel'), self.reject)); h.addWidget(button(t('save'), self._ok, primary=True)); v.addLayout(h)
        if lg == 'ar': inner.setLayoutDirection(Qt.RightToLeft)

    def _ok(self):
        man = {k: cb.currentData() for k, cb in self.combos.items()}
        r = self.X.regrade(self.win.archive, self.r, man)
        info(self, tx('g_saved', s=r['score'], n=r['total'], p=int(round(r['pct']))))
        self.accept()
