"""Çeviri merkezi: metin, belge (DOCX/PDF/görüntü/TXT), OCR, havacılık sözlüğü, çevrimdışı paketler — TR / EN / AR."""
from __future__ import annotations
import html, os, time
from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPlainTextEdit, QTabWidget, QCheckBox, QSplitter,
                               QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QProgressBar, QAbstractItemView, QFrame)
from .i18n import lang
from .common import label, button, error, info, open_path, ImageView
from .pages_a import Page
from ..core import ceviri as CV, paketler as PK

L3 = {'tr': 0, 'en': 1, 'ar': 2}
TX = {
    'title': ('Çeviri Merkezi', 'Translation Centre', 'مركز الترجمة'),
    'intro': ('Metin, belge (Word, PDF, TXT), ekran görüntüsü ve taranmış bakım formlarını Türkçe, İngilizce ve Arapça arasında havacılık '
              'literatürüne uygun resmî dille çevirir. Önce çevrimiçi en kaliteli motor (kendi Gemini/Claude anahtarınız, yoksa anahtarsız '
              'yapay zekâ ve Google), internet yoksa bilgisayarınızdaki çevrimdışı NLLB-200 modeli kullanılır. Havacılık sözlüğü, sayı ve '
              'parametre adı denetimi her motorda uygulanır; resimler ve biçim korunur, Arapça sağdan sola yazılır.',
              'Translates text, documents (Word, PDF, TXT), screenshots and scanned maintenance forms between Turkish, English and Arabic in '
              'formal language faithful to aviation terminology. The best online engine is used first (your own Gemini/Claude key, otherwise '
              'key-free AI and Google); without internet the offline NLLB-200 model on your computer is used. The aviation glossary, number and '
              'parameter-name checks apply to every engine; images and formatting are kept and Arabic is written right-to-left.',
              'يترجم النصوص والمستندات (Word وPDF وTXT) ولقطات الشاشة ونماذج الصيانة الممسوحة ضوئياً بين التركية والإنجليزية والعربية بلغة '
              'رسمية ملتزمة بمصطلحات الطيران. يُستخدم أولاً أفضل محرك متصل (مفتاح Gemini/Claude الخاص بك، وإلا الذكاء الاصطناعي المجاني وGoogle)، '
              'ودون إنترنت يُستخدم نموذج NLLB-200 غير المتصل على حاسوبك. يُطبَّق قاموس الطيران وتدقيق الأرقام وأسماء المعاملات على كل محرك؛ '
              'وتُحفظ الصور والتنسيق وتُكتب العربية من اليمين إلى اليسار.'),
    'tab_text': ('📝 Metin', '📝 Text', '📝 النص'), 'tab_doc': ('📄 Belge', '📄 Document', '📄 مستند'),
    'tab_ocr': ('📷 Görüntü / OCR', '📷 Image / OCR', '📷 صورة / OCR'), 'tab_gl': ('📚 Sözlük ve hafıza', '📚 Glossary & memory', '📚 القاموس والذاكرة'),
    'tab_pk': ('⬇ Çevrimdışı paketler', '⬇ Offline packs', '⬇ الحزم غير المتصلة'),
    'auto': ('Dili algıla', 'Detect language', 'كشف اللغة'),
    'l_tr': ('Türkçe', 'Turkish', 'التركية'), 'l_en': ('İngilizce', 'English', 'الإنجليزية'), 'l_ar': ('Arapça', 'Arabic', 'العربية'),
    'go': ('🌐 Çevir', '🌐 Translate', '🌐 ترجم'), 'swap': ('⇄', '⇄', '⇄'), 'copy': ('📋 Kopyala', '📋 Copy', '📋 نسخ'),
    'save_fix': ('✔ Düzeltmemi hafızaya kaydet', '✔ Save my correction to memory', '✔ احفظ تصحيحي في الذاكرة'),
    'fix_saved': ('Düzeltmeniz kaydedildi; aynı metin bundan sonra her motordan önce böyle çevrilir.',
                  'Your correction is saved; the same text will be translated this way before any engine from now on.',
                  'حُفظ تصحيحك؛ سيُترجم النص نفسه هكذا قبل أي محرك من الآن.'),
    'src_ph': ('Çevrilecek metni yazın ya da yapıştırın…', 'Type or paste the text to translate…', 'اكتب النص المراد ترجمته أو الصقه…'),
    'mode': ('Çalışma şekli', 'Mode', 'نمط العمل'),
    'm_auto': ('Otomatik: önce çevrimiçi, yoksa çevrimdışı', 'Automatic: online first, offline otherwise', 'تلقائي: المتصل أولاً ثم غير المتصل'),
    'm_off': ('Yalnız çevrimdışı (gizli belge, sunucuya gönderilmez)', 'Offline only (confidential, nothing is sent)', 'غير متصل فقط (مستند سري، لا يُرسل شيء)'),
    'm_on': ('Yalnız çevrimiçi', 'Online only', 'متصل فقط'),
    'quality': ('Kalite', 'Quality', 'الجودة'),
    'q_max': ('En yüksek: çeviri + havacılık editörü denetimi', 'Highest: translation + aviation editor review', 'الأعلى: ترجمة + مراجعة محرر طيران'),
    'q_std': ('Standart (daha hızlı)', 'Standard (faster)', 'قياسي (أسرع)'),
    'google': ('Google Translate yedeği', 'Google Translate fallback', 'الاحتياط عبر Google Translate'),
    'st_online': ('Çevrimiçi: {x}', 'Online: {x}', 'متصل: {x}'), 'st_offline': ('Çevrimdışı: {x}', 'Offline: {x}', 'غير متصل: {x}'),
    'st_none': ('kurulu değil — “Çevrimdışı paketler” sekmesinden indirin', 'not installed — download it in “Offline packs”',
                'غير مثبت — نزّله من تبويب “الحزم غير المتصلة”'),
    'st_noweb': ('internet yok', 'no internet', 'لا يوجد إنترنت'),
    'st_key': ('{p} (kendi anahtarınız)', '{p} (your own key)', '{p} (مفتاحك الخاص)'),
    'st_free': ('anahtarsız yapay zekâ + Google', 'key-free AI + Google', 'ذكاء اصطناعي مجاني + Google'),
    'working': ('Çevriliyor… {d}/{n} · {e}', 'Translating… {d}/{n} · {e}', 'جارٍ الترجمة… {d}/{n} · {e}'),
    'done': ('Bitti.', 'Done.', 'تم.'),
    'no_engine': ('Çeviri motoru yok: internet bağlantısı yok ve çevrimdışı paket kurulu değil. “Çevrimdışı paketler” sekmesinden NLLB-200 paketini indirin.',
                  'No translation engine: no internet and no offline pack installed. Download the NLLB-200 pack in “Offline packs”.',
                  'لا يوجد محرك ترجمة: لا إنترنت ولا حزمة غير متصلة مثبتة. نزّل حزمة NLLB-200 من تبويب “الحزم غير المتصلة”.'),
    'doc_pick': ('📂 Belge seç (Word, PDF, TXT, görüntü)', '📂 Choose a document (Word, PDF, TXT, image)', '📂 اختر مستنداً (Word، PDF، TXT، صورة)'),
    'doc_drop': ('Belgeyi buraya sürükleyip bırakabilirsiniz.', 'You can drag and drop the document here.', 'يمكنك سحب المستند وإفلاته هنا.'),
    'doc_hdr': ('Üst bilgi / alt bilgi metinlerini de çevir (antet görselleri korunur)', 'Also translate header / footer text (letterhead images are kept)',
                'ترجم نصوص الرأس والتذييل أيضاً (تُحفظ صور الترويسة)'),
    'doc_out': ('Çıktı: {p}', 'Output: {p}', 'الناتج: {p}'),
    'doc_go': ('🌐 Belgeyi çevir', '🌐 Translate document', '🌐 ترجم المستند'),
    'open': ('Aç', 'Open', 'افتح'), 'folder': ('Klasörü aç', 'Open folder', 'افتح المجلد'),
    'doc_ok': ('Çeviri kaydedildi: {p}', 'Translation saved: {p}', 'حُفظت الترجمة: {p}'),
    'doc_rules': ('Word: resimler, tablolar, antet ve paragraf içi biçim korunur; Arapçada sağdan sola. PDF: metin aynı yere aynı punto ve renkle '
                  'yazılır, görseller kalır; taranmış sayfa OCR ile okunur ve çevirisi arkasına eklenir. Görüntü: OCR + çeviri, görüntüyle birlikte Word.',
                  'Word: images, tables, letterhead and in-paragraph formatting are kept; right-to-left in Arabic. PDF: text is written in the same place '
                  'with the same size and colour, graphics stay; a scanned page is read by OCR and its translation is added after it. Image: OCR + '
                  'translation in Word together with the image.',
                  'Word: تُحفظ الصور والجداول والترويسة وتنسيق الفقرة؛ ومن اليمين إلى اليسار في العربية. PDF: يُكتب النص في المكان نفسه بالحجم واللون '
                  'نفسيهما وتبقى الرسومات؛ وتُقرأ الصفحة الممسوحة ضوئياً بالتعرف الضوئي وتُضاف ترجمتها بعدها. الصورة: تعرف ضوئي + ترجمة في Word مع الصورة.'),
    'ocr_open': ('📂 Görüntü aç', '📂 Open image', '📂 افتح صورة'), 'ocr_paste': ('📋 Panodan yapıştır', '📋 Paste from clipboard', '📋 الصق من الحافظة'),
    'ocr_read': ('🔎 Metni oku (OCR)', '🔎 Read text (OCR)', '🔎 اقرأ النص (OCR)'),
    'ocr_tx': ('🌐 Okunan metni çevir', '🌐 Translate the text read', '🌐 ترجم النص المقروء'),
    'ocr_doc': ('📄 Görüntü + çeviri Word olarak kaydet', '📄 Save image + translation as Word', '📄 احفظ الصورة والترجمة كملف Word'),
    'ocr_lang': ('Görüntüdeki dil', 'Language in image', 'لغة الصورة'),
    'ocr_none': ('Panoda görüntü yok.', 'No image on the clipboard.', 'لا توجد صورة في الحافظة.'),
    'ocr_eng': ('Okuyan: {e}', 'Read by: {e}', 'القارئ: {e}'),
    'ocr_ph': ('Okunan metin burada görünür; düzeltebilirsiniz.', 'The text read appears here; you can correct it.', 'يظهر النص المقروء هنا؛ ويمكنك تصحيحه.'),
    'ocr_off': ('Çevrimdışı OCR paketi kurulu değil ve internet yok. “Çevrimdışı paketler” sekmesinden Tesseract OCR paketini indirin.',
                'Offline OCR pack is not installed and there is no internet. Download the Tesseract OCR pack in “Offline packs”.',
                'حزمة التعرف الضوئي غير المتصلة غير مثبتة ولا يوجد إنترنت. نزّل حزمة Tesseract OCR من تبويب “الحزم غير المتصلة”.'),
    'gl_search': ('Sözlükte ara…', 'Search the glossary…', 'ابحث في القاموس…'),
    'gl_cols': (('İngilizce', 'Türkçe', 'Arapça', 'Kaynak'), ('English', 'Turkish', 'Arabic', 'Source'), ('الإنجليزية', 'التركية', 'العربية', 'المصدر')),
    'gl_builtin': ('gömülü', 'built-in', 'مدمج'), 'gl_user': ('sizin', 'yours', 'خاص بك'),
    'gl_add': ('➕ Terim ekle', '➕ Add term', '➕ أضف مصطلحاً'), 'gl_del': ('🗑 Seçili terimi sil', '🗑 Delete selected term', '🗑 احذف المصطلح المحدد'),
    'gl_note': ('Kendi terimleriniz bütün motorlarda (çevrimiçi ve çevrimdışı) gömülü sözlükten önce uygulanır. Üç dili de doldurun.',
                'Your own terms are applied before the built-in glossary in every engine (online and offline). Fill in all three languages.',
                'تُطبَّق مصطلحاتك قبل القاموس المدمج في كل المحركات (المتصلة وغير المتصلة). املأ اللغات الثلاث.'),
    'gl_need3': ('Üç dili de doldurun.', 'Fill in all three languages.', 'املأ اللغات الثلاث.'),
    'tm_title': ('Kaydettiğiniz düzeltmeler (çeviri hafızası)', 'Your saved corrections (translation memory)', 'تصحيحاتك المحفوظة (ذاكرة الترجمة)'),
    'tm_cols': (('Yön', 'Kaynak', 'Çeviriniz'), ('Direction', 'Source', 'Your translation'), ('الاتجاه', 'المصدر', 'ترجمتك')),
    'tm_del': ('🗑 Seçili düzeltmeyi sil', '🗑 Delete selected correction', '🗑 احذف التصحيح المحدد'),
    'tm_clear': ('Önbelleği temizle (düzeltmeleriniz kalır)', 'Clear cache (your corrections stay)', 'امسح الذاكرة المؤقتة (تبقى تصحيحاتك)'),
    'pk_intro': ('İnternet yokken çeviri ve OCR için bu paketleri bir kez indirin. Boyut önemsenmeden en kaliteli modeller seçildi: Meta NLLB-200 '
                 '3.3B (200 dil, Türkçe–Arapça doğrudan) ve Tesseract 5 LSTM tessdata_best (Türkçe, İngilizce, Arapça). İndirme yarıda kalırsa '
                 'kaldığı yerden devam eder; her parça SHA-256 ile doğrulanır.',
                 'Download these packs once to translate and OCR without internet. The highest-quality models were chosen regardless of size: Meta '
                 'NLLB-200 3.3B (200 languages) and Tesseract 5 LSTM tessdata_best (Turkish, English, Arabic). An interrupted download resumes '
                 'where it stopped; every part is verified with SHA-256.',
                 'نزّل هذه الحزم مرة واحدة للترجمة والتعرف الضوئي دون إنترنت. اختيرت أعلى النماذج جودة بغض النظر عن الحجم: Meta NLLB-200 3.3B '
                 '(200 لغة) وTesseract 5 LSTM tessdata_best (التركية والإنجليزية والعربية). يُستأنف التنزيل المتقطع من حيث توقف، ويُتحقق من كل جزء بـ SHA-256.'),
    'pk_cols': (('Paket', 'Durum', 'Boyut'), ('Pack', 'Status', 'Size'), ('الحزمة', 'الحالة', 'الحجم')),
    'pk_inst': ('✔ kurulu', '✔ installed', '✔ مثبت'), 'pk_not': ('kurulu değil', 'not installed', 'غير مثبت'),
    'pk_best': (' (önerilen, en yüksek kalite)', ' (recommended, highest quality)', ' (موصى به، أعلى جودة)'),
    'pk_dl': ('⬇ Seçili paketi indir', '⬇ Download selected pack', '⬇ نزّل الحزمة المحددة'),
    'pk_all': ('⬇ Önerilenlerin hepsini indir', '⬇ Download all recommended', '⬇ نزّل كل الموصى به'),
    'pk_rm': ('🗑 Kaldır', '🗑 Remove', '🗑 أزل'), 'pk_cancel': ('Durdur', 'Stop', 'أوقف'),
    'pk_dling': ('{n} indiriliyor', 'Downloading {n}', 'جارٍ تنزيل {n}'),
    'pk_ok': ('{n} kuruldu.', '{n} installed.', 'ثُبّتت {n}.'),
    'pk_noman': ('Paket listesi alınamadı (internet?): {e}', 'Could not get the pack list (internet?): {e}', 'تعذر جلب قائمة الحزم (الإنترنت؟): {e}'),
    'pk_use': ('Çevrimdışı çeviride kullanılacak model', 'Model used for offline translation', 'النموذج المستخدم للترجمة غير المتصلة'),
    'chk_title': ('Denetim ayrıntısı', 'Check details', 'تفاصيل التدقيق'),
    'iss_term': ('terim: “{a}” → “{b}” bekleniyordu', 'term: “{a}” → expected “{b}”', 'مصطلح: “{a}” → كان المتوقع “{b}”'),
    'iss_num': ('sayı eksik: {a}', 'number missing: {a}', 'رقم ناقص: {a}'),
    'iss_id': ('ad/kod değişmiş: {a}', 'name/code changed: {a}', 'اسم/رمز تغيّر: {a}'),
    'iss_empty': ('çeviri boş', 'empty translation', 'ترجمة فارغة'),
}


def tx(k, **a):
    v = TX[k][L3.get(lang(), 0)]
    return v.format(**a) if a else v


class _Bridge(QObject):
    prog = Signal(object)


def _combo():
    c = QComboBox(); c.setSizeAdjustPolicy(QComboBox.AdjustToContents)
    return c


def _lang_combo(auto=False, cur=None):
    c = _combo()
    if auto: c.addItem(tx('auto'), 'auto')
    for l in CV.LANGS: c.addItem(tx('l_' + l), l)
    if cur:
        i = c.findData(cur)
        if i >= 0: c.setCurrentIndex(i)
    return c


def _mb(n):
    return f'{n / 1048576:,.1f} MB'.replace(',', ' ')


class TranslatePage(Page):
    def __init__(self, win):
        super().__init__(win)
        self.s = win.settings
        self.br = _Bridge(); self.br.prog.connect(self._on_prog)
        self._cancel = False; self._busy = False; self._queue = []
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        intro = label(tx('intro'), 'muted', wrap=True); v.addWidget(intro)
        # seçenekler
        o = QHBoxLayout()
        o.addWidget(QLabel(tx('mode')))
        self.c_mode = _combo()
        for k, d in (('m_auto', 'auto'), ('m_off', 'offline'), ('m_on', 'online')): self.c_mode.addItem(tx(k), d)
        self.c_mode.setCurrentIndex(max(0, self.c_mode.findData('offline' if self.s.get('tx_private') else (self.s.get('tx_mode') or 'auto'))))
        o.addWidget(self.c_mode)
        o.addWidget(QLabel(tx('quality')))
        self.c_q = _combo(); self.c_q.addItem(tx('q_max'), 'max'); self.c_q.addItem(tx('q_std'), 'std')
        self.c_q.setCurrentIndex(0 if (self.s.get('tx_quality') or 'max') == 'max' else 1); o.addWidget(self.c_q)
        o.addStretch(1); v.addLayout(o)
        o2 = QHBoxLayout()
        self.k_google = QCheckBox(tx('google')); self.k_google.setChecked(bool(self.s.get('tx_google', True))); o2.addWidget(self.k_google)
        self.st = label('', 'muted', wrap=True); o2.addWidget(self.st, 1)
        v.addLayout(o2)
        for w in (self.c_mode, self.c_q): w.currentIndexChanged.connect(self._save_opts)
        self.k_google.toggled.connect(self._save_opts)
        self.tabs = QTabWidget(); v.addWidget(self.tabs, 1)
        self.tabs.addTab(self._tab_text(), tx('tab_text'))
        self.tabs.addTab(self._tab_doc(), tx('tab_doc'))
        self.tabs.addTab(self._tab_ocr(), tx('tab_ocr'))
        self.tabs.addTab(self._tab_gl(), tx('tab_gl'))
        self.tabs.addTab(self._tab_pk(), tx('tab_pk'))
        self.setAcceptDrops(True)
        QTimer.singleShot(0, self._status)

    # ------------------------------------------------------------ ortak
    def _save_opts(self, *_):
        m = self.c_mode.currentData()
        self.s['tx_mode'] = m; self.s['tx_private'] = m == 'offline'
        self.s['tx_quality'] = self.c_q.currentData(); self.s['tx_google'] = self.k_google.isChecked()
        try: self.s.save()
        except Exception: pass
        self._status()

    def on_show(self):
        self._status()

    def _status(self):
        from ..core import ai
        s = self.s; parts = []
        m = CV.mode(s)
        if m != 'offline':
            keys = ai._keys(s)
            on = [ai.PROVIDERS[p]['name'] for p in ('gemini', 'anthropic') if keys.get(p)]
            x = tx('st_key', p=' + '.join(on)) if on else tx('st_free')
            if not s.get('online', True): x = tx('st_noweb')
            parts.append(tx('st_online', x=x))
        if m != 'online':
            d = PK.nllb_dir(s.get('tx_nllb'))
            ocr_ok = PK.installed('ocr')
            x = (PK.PACKS[PK.nllb_id(d)]['name'] if d else tx('st_none'))
            if ocr_ok: x += ' · OCR ✔'
            parts.append(tx('st_offline', x=x))
        self.st.setText('   ·   '.join(parts))

    def _on_prog(self, x):
        kind = x[0]
        if kind == 'tx':
            _, d, n, e = x
            self._bar.setRange(0, max(1, n)); self._bar.setValue(d); self._bar.setVisible(True)
            self.win.set_status(tx('working', d=d, n=n, e=e))
        elif kind == 'pk':
            _, done, total = x
            self.pbox.set(self._trk.update(done, finished=False) if total else {'done': done, 'total': 0, 'pct': 0, 'remaining': 0, 'speed': 0})

    def _run(self, fn, ok, fail=None):
        from .common import run_bg
        self._cancel = False; self._busy = True

        def done(r):
            self._busy = False; self._bar.setVisible(False); ok(r)

        def bad(e):
            self._busy = False; self._bar.setVisible(False)
            if 'no engine' in str(e) or 'all engines failed' in str(e): e = tx('no_engine')
            (fail or (lambda m: error(self, m)))(str(e))
        return run_bg(fn, on_done=done, on_fail=bad)

    def _prog_cb(self):
        return lambda d, n, e: self.br.prog.emit(('tx', d, n, e))

    def _usage(self):
        return getattr(self.win, 'usage', None)

    def _report(self, rep, box):
        txt = CV.report_text(rep, lang())
        iss = rep.get('issues') or []
        if iss:
            lines = []
            for x in iss[:12]:
                _, k, a, b = x
                lines.append({'term': tx('iss_term', a=a, b=b), 'num': tx('iss_num', a=a), 'id': tx('iss_id', a=a), 'empty': tx('iss_empty')}[k])
            box.setToolTip(tx('chk_title') + ':\n' + '\n'.join(lines))
        box.setText(txt + (' ⓘ' if iss else ''))

    # ------------------------------------------------------------ Metin
    def _tab_text(self):
        w = QWidget(); v = QVBoxLayout(w)
        h = QHBoxLayout()
        self.t_src = _lang_combo(True, self.s.get('tx_src') or 'auto')
        self.t_tgt = _lang_combo(False, self.s.get('tx_tgt') or ('ar' if lang() != 'ar' else 'tr'))
        h.addWidget(self.t_src); h.addWidget(button(tx('swap'), self._swap)); h.addWidget(self.t_tgt)
        self.b_go = button(tx('go'), self.translate_now, primary=True); h.addWidget(self.b_go)
        h.addStretch(1)
        h.addWidget(button(tx('copy'), lambda: QGuiApplication.clipboard().setText(self.t_out.toPlainText())))
        self.b_fix = button(tx('save_fix'), self._save_fix); h.addWidget(self.b_fix)
        v.addLayout(h)
        sp = QSplitter(Qt.Horizontal)
        self.t_in = QPlainTextEdit(); self.t_in.setPlaceholderText(tx('src_ph'))
        self.t_out = QPlainTextEdit()
        for e in (self.t_in, self.t_out):
            f = e.font(); f.setPointSize(f.pointSize() + 2); e.setFont(f)
        sp.addWidget(self.t_in); sp.addWidget(self.t_out); v.addWidget(sp, 1)
        self.t_bar = QProgressBar(); self.t_bar.setVisible(False); v.addWidget(self.t_bar); self._bar = self.t_bar
        self.t_rep = label('', 'muted', wrap=True); v.addWidget(self.t_rep)
        self.t_in.textChanged.connect(self._dir_in)
        self.t_tgt.currentIndexChanged.connect(self._dir_out)
        self._dir_out(); self._last = None
        return w

    def _dir_in(self):
        l = CV.detect(self.t_in.toPlainText()[:400])
        self.t_in.setLayoutDirection(Qt.RightToLeft if l == 'ar' else Qt.LeftToRight)
        o = self.t_in.document().defaultTextOption(); o.setTextDirection(Qt.RightToLeft if l == 'ar' else Qt.LeftToRight)
        self.t_in.document().setDefaultTextOption(o)

    def _dir_out(self, *_):
        rtl = self.t_tgt.currentData() == 'ar'
        self.t_out.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        o = self.t_out.document().defaultTextOption(); o.setTextDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        o.setAlignment(Qt.AlignRight if rtl else Qt.AlignLeft)
        self.t_out.document().setDefaultTextOption(o)

    def _swap(self):
        s, t = self.t_src.currentData(), self.t_tgt.currentData()
        if s == 'auto': s = CV.detect(self.t_in.toPlainText())
        self.t_src.setCurrentIndex(self.t_src.findData(t)); self.t_tgt.setCurrentIndex(self.t_tgt.findData(s))
        if self.t_out.toPlainText().strip():
            self.t_in.setPlainText(self.t_out.toPlainText()); self.t_out.clear()

    def translate_now(self):
        text = self.t_in.toPlainText()
        if not text.strip() or self._busy: return
        src, tgt = self.t_src.currentData(), self.t_tgt.currentData()
        self.s['tx_src'] = src; self.s['tx_tgt'] = tgt
        if src == 'auto': src = CV.detect(text)
        if src == tgt:
            tgt = 'en' if src != 'en' else ('ar' if lang() == 'ar' else 'tr')
            self.t_tgt.setCurrentIndex(self.t_tgt.findData(tgt))
        self.b_go.setEnabled(False); self.t_rep.setText('…'); self._bar = self.t_bar
        s, u, cb = self.s, self._usage(), self._prog_cb()

        def ok(r):
            out, rep = r
            self.b_go.setEnabled(True); self.t_out.setPlainText(out); self._report(rep, self.t_rep)
            self._last = (text, src, tgt, out); self.win.set_status(tx('done'))

        def bad(m):
            self.b_go.setEnabled(True); self.t_rep.setText(''); error(self, m)
        self._run(lambda: CV.translate_text(text, src, tgt, s, u, cb, lambda: self._cancel), ok, bad)

    def _save_fix(self):
        if not self._last: return
        text, src, tgt, out = self._last
        mine = self.t_out.toPlainText()
        if not mine.strip(): return
        a, b = text.split('\n'), mine.split('\n')
        if len(a) == len(b):
            for x, y in zip(a, b):
                if x.strip() and y.strip(): CV.save_correction(x, src, tgt, y)
        else:
            CV.save_correction(text, src, tgt, mine)
        self.win.set_status(tx('fix_saved')); self._fill_tm()

    # ------------------------------------------------------------ Belge
    def _tab_doc(self):
        w = QWidget(); v = QVBoxLayout(w)
        h = QHBoxLayout()
        h.addWidget(button(tx('doc_pick'), self._pick_doc, primary=True))
        self.d_src = _lang_combo(True, 'auto'); self.d_tgt = _lang_combo(False, self.s.get('tx_tgt') or 'ar')
        h.addWidget(self.d_src); h.addWidget(QLabel('→')); h.addWidget(self.d_tgt); h.addStretch(1)
        v.addLayout(h)
        self.d_file = label(tx('doc_drop'), 'muted', wrap=True); v.addWidget(self.d_file)
        self.d_hdr = QCheckBox(tx('doc_hdr')); self.d_hdr.setChecked(bool(self.s.get('tx_headers', True))); v.addWidget(self.d_hdr)
        v.addWidget(label(tx('doc_rules'), 'muted', wrap=True))
        h2 = QHBoxLayout()
        self.b_doc = button(tx('doc_go'), self.translate_doc, primary=True); self.b_doc.setEnabled(False); h2.addWidget(self.b_doc)
        self.b_dopen = button(tx('open'), lambda: open_path(self._doc_out)); self.b_dopen.setEnabled(False); h2.addWidget(self.b_dopen)
        self.b_dfold = button(tx('folder'), lambda: open_path(os.path.dirname(self._doc_out))); self.b_dfold.setEnabled(False); h2.addWidget(self.b_dfold)
        self.b_dstop = button(tx('pk_cancel'), lambda: setattr(self, '_cancel', True)); h2.addWidget(self.b_dstop)
        h2.addStretch(1); v.addLayout(h2)
        self.d_bar = QProgressBar(); self.d_bar.setVisible(False); v.addWidget(self.d_bar)
        self.d_rep = label('', 'muted', wrap=True); v.addWidget(self.d_rep)
        v.addStretch(1)
        self._doc = None; self._doc_out = ''
        return w

    def _pick_doc(self):
        p, _ = QFileDialog.getOpenFileName(self, tx('doc_pick'), '', 'Documents (*.docx *.pdf *.txt *.md *.csv *.param *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)')
        if p: self.set_doc(p)

    def set_doc(self, p):
        from ..core import belge
        if not belge.kind(p): return
        self._doc = p; self.b_doc.setEnabled(True)
        self.tabs.setCurrentIndex(1)
        self._doc_out = belge.out_name(p, self.d_tgt.currentData())
        self.d_file.setText(os.path.basename(p) + '\n' + tx('doc_out', p=self._doc_out))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            from ..core import belge
            k = belge.kind(p)
            if k == 'img': self._load_img(p); return
            if k: self.set_doc(p); return

    def translate_doc(self):
        if not self._doc or self._busy: return
        from ..core import belge
        src, tgt = self.d_src.currentData(), self.d_tgt.currentData()
        self._doc_out = belge.out_name(self._doc, tgt)
        self.s['tx_headers'] = self.d_hdr.isChecked()
        s, u, doc, out, hdr = self.s, self._usage(), self._doc, self._doc_out, self.d_hdr.isChecked()
        self.b_doc.setEnabled(False); self.d_rep.setText('…')
        self._bar = self.d_bar
        cb = self._prog_cb()

        def job():
            if belge.kind(doc) == 'docx':
                return belge.translate_docx(doc, out, src, tgt, s, u, cb, lambda: self._cancel, headers=hdr)
            return belge.translate_file(doc, out, src, tgt, s, u, cb, lambda: self._cancel)

        def ok(rep):
            self.b_doc.setEnabled(True); self.b_dopen.setEnabled(True); self.b_dfold.setEnabled(True)
            self._report(rep, self.d_rep); self.d_rep.setText(tx('doc_ok', p=out) + '\n' + self.d_rep.text())
            self.win.set_status(tx('doc_ok', p=os.path.basename(out)))

        def bad(m):
            self.b_doc.setEnabled(True); self.d_rep.setText(''); error(self, m)
        self._run(job, ok, bad)

    # ------------------------------------------------------------ OCR
    def _tab_ocr(self):
        w = QWidget(); v = QVBoxLayout(w)
        h = QHBoxLayout()
        h.addWidget(button(tx('ocr_open'), self._pick_img)); h.addWidget(button(tx('ocr_paste'), self._paste_img))
        h.addWidget(QLabel(tx('ocr_lang'))); self.o_lang = _lang_combo(True, 'auto'); h.addWidget(self.o_lang)
        self.b_ocr = button(tx('ocr_read'), self.read_ocr, primary=True); self.b_ocr.setEnabled(False); h.addWidget(self.b_ocr)
        self.b_otx = button(tx('ocr_tx'), self._ocr_to_text); h.addWidget(self.b_otx)
        self.b_odoc = button(tx('ocr_doc'), self._ocr_doc); self.b_odoc.setEnabled(False); h.addWidget(self.b_odoc)
        h.addStretch(1); v.addLayout(h)
        sp = QSplitter(Qt.Horizontal)
        self.o_img = ImageView(); sp.addWidget(self.o_img)
        self.o_txt = QPlainTextEdit(); self.o_txt.setPlaceholderText(tx('ocr_ph')); sp.addWidget(self.o_txt)
        v.addWidget(sp, 1)
        self.o_rep = label('', 'muted'); v.addWidget(self.o_rep)
        self._img = None
        return w

    def _pick_img(self):
        p, _ = QFileDialog.getOpenFileName(self, tx('ocr_open'), '', 'Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif)')
        if p: self._load_img(p)

    def _load_img(self, p):
        self._img = p
        with open(p, 'rb') as f: self.o_img.set_png(f.read())
        self.b_ocr.setEnabled(True); self.b_odoc.setEnabled(True); self.tabs.setCurrentIndex(2)

    def _paste_img(self):
        im = QGuiApplication.clipboard().image()
        if im is None or im.isNull(): return info(self, tx('ocr_none'))
        from ..core.paths import data_dir
        p = os.path.join(data_dir(), 'ocr_clipboard.png'); im.save(p, 'PNG')
        self._load_img(p)

    def read_ocr(self):
        if not self._img or self._busy: return
        from ..core import ocr as O
        s, u, img, lg = self.s, self._usage(), self._img, self.o_lang.currentData()
        self.b_ocr.setEnabled(False); self.o_rep.setText('…')

        def ok(r):
            t, eng = r
            self.b_ocr.setEnabled(True); self.o_txt.setPlainText(t); self.o_rep.setText(tx('ocr_eng', e=eng))
            rtl = CV.detect(t[:400]) == 'ar'
            o = self.o_txt.document().defaultTextOption(); o.setTextDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
            o.setAlignment(Qt.AlignRight if rtl else Qt.AlignLeft); self.o_txt.document().setDefaultTextOption(o)

        def bad(m):
            self.b_ocr.setEnabled(True); self.o_rep.setText('')
            error(self, tx('ocr_off') if 'no OCR' in m or 'not installed' in m else m)
        self._run(lambda: O.ocr(img, lg, s, u), ok, bad)

    def _ocr_to_text(self):
        t = self.o_txt.toPlainText()
        if not t.strip(): return
        self.t_in.setPlainText(t)
        lg = self.o_lang.currentData()
        self.t_src.setCurrentIndex(self.t_src.findData(lg if lg in CV.LANGS else 'auto'))
        self.tabs.setCurrentIndex(0); self.translate_now()

    def _ocr_doc(self):
        if not self._img or self._busy: return
        from ..core import belge
        tgt = self.t_tgt.currentData(); out = belge.out_name(self._img, tgt)
        p, _ = QFileDialog.getSaveFileName(self, tx('ocr_doc'), out, 'Word (*.docx)')
        if not p: return
        s, u, img, lg = self.s, self._usage(), self._img, self.o_lang.currentData()
        known = self.o_txt.toPlainText().strip() or None
        self._bar = self.t_bar

        def ok(rep):
            self.o_rep.setText(tx('doc_ok', p=p)); open_path(p)
        self._run(lambda: belge.translate_image(img, p, lg, tgt, s, u, self._prog_cb(), ocr_text=known), ok)

    # ------------------------------------------------------------ Sözlük + hafıza
    def _tab_gl(self):
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(label(tx('gl_note'), 'muted', wrap=True))
        h = QHBoxLayout()
        self.g_q = QLineEdit(); self.g_q.setPlaceholderText(tx('gl_search')); self.g_q.textChanged.connect(self._fill_gl); h.addWidget(self.g_q, 1)
        v.addLayout(h)
        self.g_tbl = QTableWidget(0, 4); self.g_tbl.setHorizontalHeaderLabels(list(tx('gl_cols')))
        self.g_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.g_tbl.setSelectionBehavior(QAbstractItemView.SelectRows); self.g_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        v.addWidget(self.g_tbl, 2)
        h2 = QHBoxLayout()
        self.g_en, self.g_tr, self.g_ar = QLineEdit(), QLineEdit(), QLineEdit()
        self.g_en.setPlaceholderText('English'); self.g_tr.setPlaceholderText('Türkçe'); self.g_ar.setPlaceholderText('العربية')
        self.g_ar.setLayoutDirection(Qt.RightToLeft)
        for e in (self.g_en, self.g_tr, self.g_ar): h2.addWidget(e, 1)
        h2.addWidget(button(tx('gl_add'), self._add_term, primary=True)); h2.addWidget(button(tx('gl_del'), self._del_term))
        v.addLayout(h2)
        v.addWidget(label(tx('tm_title'), 'h2'))
        self.tm_tbl = QTableWidget(0, 3); self.tm_tbl.setHorizontalHeaderLabels(list(tx('tm_cols')))
        self.tm_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tm_tbl.setSelectionBehavior(QAbstractItemView.SelectRows); self.tm_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        v.addWidget(self.tm_tbl, 1)
        h3 = QHBoxLayout(); h3.addWidget(button(tx('tm_del'), self._del_tm)); h3.addWidget(button(tx('tm_clear'), self._clear_cache)); h3.addStretch(1)
        v.addLayout(h3)
        self._fill_gl(); self._fill_tm()
        return w

    def _fill_gl(self, *_):
        q = (self.g_q.text() if hasattr(self, 'g_q') else '').strip().lower()
        rows = [(e, e.user) for e in CV.entries(self.s)]
        if q: rows = [r for r in rows if q in (r[0].en + ' ' + r[0].tr + ' ' + r[0].ar).lower()]
        self.g_tbl.setRowCount(len(rows))
        for i, (e, u) in enumerate(rows):
            for j, val in enumerate((e.en, e.tr, e.ar, tx('gl_user') if u else tx('gl_builtin'))):
                it = QTableWidgetItem(val)
                if j == 2: it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.g_tbl.setItem(i, j, it)
        self._gl_rows = rows

    def _add_term(self):
        en, tr, ar = self.g_en.text().strip(), self.g_tr.text().strip(), self.g_ar.text().strip()
        if not (en and tr and ar): return error(self, tx('gl_need3'))
        L = [x for x in (self.s.get('tx_terms') or []) if x.get('en', '').lower() != en.lower()]
        L.insert(0, {'en': en, 'tr': tr, 'ar': ar}); self.s['tx_terms'] = L
        try: self.s.save()
        except Exception: pass
        for e in (self.g_en, self.g_tr, self.g_ar): e.clear()
        self._fill_gl()

    def _del_term(self):
        r = self.g_tbl.currentRow()
        if r < 0 or r >= len(self._gl_rows) or not self._gl_rows[r][1]: return
        en = self._gl_rows[r][0].en
        self.s['tx_terms'] = [x for x in (self.s.get('tx_terms') or []) if x.get('en') != en]
        try: self.s.save()
        except Exception: pass
        self._fill_gl()

    def _fill_tm(self):
        try: rows = CV._tm().user_entries()
        except Exception: rows = []
        self._tm_rows = rows
        self.tm_tbl.setRowCount(len(rows))
        for i, (src, tgt, text, out, ts) in enumerate(rows):
            for j, val in enumerate((f'{src.upper()} → {tgt.upper()}', text, out)):
                self.tm_tbl.setItem(i, j, QTableWidgetItem(val))

    def _del_tm(self):
        r = self.tm_tbl.currentRow()
        if r < 0 or r >= len(self._tm_rows): return
        src, tgt, text, _, _ = self._tm_rows[r]
        CV._tm().delete_user(text, src, tgt); self._fill_tm()

    def _clear_cache(self):
        CV._tm().clear_cache(); self.win.set_status(tx('done'))

    # ------------------------------------------------------------ Paketler
    def _tab_pk(self):
        from fccore.widgets import ProgressBox
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(label(tx('pk_intro'), 'muted', wrap=True))
        self.p_tbl = QTableWidget(0, 3); self.p_tbl.setHorizontalHeaderLabels(list(tx('pk_cols')))
        self.p_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.p_tbl.setSelectionBehavior(QAbstractItemView.SelectRows); self.p_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.p_tbl.setMaximumHeight(150)
        v.addWidget(self.p_tbl)
        h = QHBoxLayout()
        self.b_pdl = button(tx('pk_dl'), self.download_pack, primary=True); h.addWidget(self.b_pdl)
        self.b_pall = button(tx('pk_all'), lambda: self.download_pack([p for p in PK.PACKS if PK.PACKS[p].get('best') and not PK.installed(p)]))
        h.addWidget(self.b_pall)
        self.b_prm = button(tx('pk_rm'), self._remove_pack); h.addWidget(self.b_prm)
        self.b_pstop = button(tx('pk_cancel'), lambda: setattr(self, '_cancel', True)); self.b_pstop.setVisible(False); h.addWidget(self.b_pstop)
        h.addStretch(1)
        h.addWidget(QLabel(tx('pk_use'))); self.c_nllb = _combo()
        for pid in PK.MT_ORDER: self.c_nllb.addItem(PK.PACKS[pid]['name'], pid)
        self.c_nllb.setCurrentIndex(max(0, self.c_nllb.findData(self.s.get('tx_nllb') or 'nllb-3.3b')))
        self.c_nllb.currentIndexChanged.connect(self._set_nllb)
        h.addWidget(self.c_nllb)
        v.addLayout(h)
        self.pbox = ProgressBox(); self.pbox.setVisible(False); v.addWidget(self.pbox)
        v.addStretch(1)
        self._fill_pk()
        return w

    def _set_nllb(self, *_):
        self.s['tx_nllb'] = self.c_nllb.currentData()
        try: self.s.save()
        except Exception: pass
        self._status()

    def _fill_pk(self):
        ids = list(PK.PACKS)
        self.p_tbl.setRowCount(len(ids))
        for i, pid in enumerate(ids):
            p = PK.PACKS[pid]
            inst = PK.installed(pid)
            size = _mb(PK.size_on_disk(pid)) if inst else f"~{p['approx_mb']:,} MB".replace(',', ' ')
            for j, val in enumerate((p['name'] + (tx('pk_best') if p.get('best') else ''), tx('pk_inst') if inst else tx('pk_not'), size)):
                self.p_tbl.setItem(i, j, QTableWidgetItem(val))
        if self.p_tbl.currentRow() < 0: self.p_tbl.selectRow(0)

    def _sel_pack(self):
        r = self.p_tbl.currentRow()
        ids = list(PK.PACKS)
        return ids[r] if 0 <= r < len(ids) else None

    def download_pack(self, pid=None):
        if isinstance(pid, list):
            q = list(pid)
            if not q: return
            self._queue = q[1:]; pid = q[0]
        else:
            self._queue = []
            pid = pid if isinstance(pid, str) else self._sel_pack()
        if not pid or self._busy: return
        from fccore.progress import tracker
        self._trk = tracker(0)
        self.pbox.setVisible(True); self.pbox.set_title(tx('pk_dling', n=PK.PACKS[pid]['name'])); self.pbox.busy(tx('pk_dling', n=PK.PACKS[pid]['name']))
        self.b_pdl.setEnabled(False); self.b_pstop.setVisible(True)

        def job():
            man = PK.manifest(force=True)
            tot = PK.total_size(man['packs'][pid])
            self._trk.set_total(tot)
            return PK.download(pid, lambda d, n: self.br.prog.emit(('pk', d, n)), lambda: self._cancel, man=man)

        def ok(_):
            self.b_pdl.setEnabled(True); self.b_pstop.setVisible(False)
            self.pbox.set(self._trk.update(PK.size_on_disk(pid), finished=True)); self.pbox.set_title(tx('pk_ok', n=PK.PACKS[pid]['name']))
            self._fill_pk(); self._status()
            if self._queue and not self._cancel:
                QTimer.singleShot(300, lambda: self.download_pack(list(self._queue)))

        def bad(m):
            self._queue = []
            self.b_pdl.setEnabled(True); self.b_pstop.setVisible(False); self.pbox.setVisible(False)
            if not self._cancel: error(self, tx('pk_noman', e=m) if 'HTTP' in m or 'urlopen' in m.lower() else m)
        self._run(job, ok, bad)

    def _remove_pack(self):
        pid = self._sel_pack()
        if not pid or self._busy: return
        PK.remove(pid); self._fill_pk(); self._status()
