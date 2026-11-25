"""Soru Bankası sayfası: bankanın tamamını görme, arama/süzme, ekleme, düzenleme, silme, geri yükleme, içe/dışa aktarma."""
from __future__ import annotations
import html
from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QSplitter, QTextBrowser, QDialog, QFormLayout, QTabWidget, QPlainTextEdit,
                               QRadioButton, QButtonGroup, QGridLayout, QFileDialog, QMessageBox)
from .i18n import lang
from .common import label, button, error, info
from .pages_a import Page

E = html.escape
TX = {
    'title': ('Soru Bankası', 'Question Bank', 'بنك الأسئلة'),
    'intro': ('Alıştırma Modu ve Sınav bu bankadan soru seçer. Hazır öğretici sorular, kütüphanelerden üretilen sorular ve sizin sorularınız burada; '
              'her soruyu görebilir, düzenleyebilir, silebilir ya da yenisini ekleyebilirsiniz. Değişiklikler eşitlemeyle diğer bilgisayarlarınıza da gider.',
              'Practice Mode and Exams pick questions from this bank. Built-in tutorial questions, questions generated from the libraries and your own '
              'questions are here; you can view, edit, delete any question or add new ones. Changes travel to your other computers with sync.',
              'يختار وضع التدريب والاختبار الأسئلة من هذا البنك. هنا الأسئلة التعليمية الجاهزة والأسئلة المولَّدة من المكتبات وأسئلتك؛ '
              'يمكنك عرض أي سؤال وتعديله وحذفه أو إضافة أسئلة جديدة. وتنتقل التغييرات إلى أجهزتك الأخرى عبر المزامنة.'),
    'search': ('Ara: soru, şık, açıklama, kaynak (üç dilde)…', 'Search question, option, explanation, source (all languages)…', 'ابحث في السؤال أو الخيار أو الشرح أو المصدر (كل اللغات)…'),
    'all_t': ('Tüm konular', 'All topics', 'كل المواضيع'), 'all_l': ('Tüm seviyeler', 'All levels', 'كل المستويات'),
    'all_o': ('Tüm sorular', 'All questions', 'كل الأسئلة'), 'o_mod': ('Düzenlediklerim', 'Edited by me', 'ما عدّلته'),
    'o_hidden': ('Kaldırılanlar (geri yüklenebilir)', 'Removed (restorable)', 'المحذوفة (قابلة للاستعادة)'),
    'count': ('{n} soru', '{n} questions', '{n} سؤال'),
    'new': ('➕ Yeni soru', '➕ New question', '➕ سؤال جديد'), 'edit': ('✏ Düzenle', '✏ Edit', '✏ تعديل'), 'dup': ('⧉ Çoğalt', '⧉ Duplicate', '⧉ نسخ'),
    'del': ('🗑 Sil', '🗑 Delete', '🗑 حذف'), 'restore': ('↺ Özgün hâline döndür', '↺ Restore original', '↺ استعادة الأصل'),
    'export': ('📤 Dışa aktar', '📤 Export', '📤 تصدير'), 'import': ('📥 İçe aktar', '📥 Import', '📥 استيراد'),
    'practice': ('🎓 Bu sorularla alıştırma', '🎓 Practise these', '🎓 تدرّب على هذه'),
    'cols': (('Kimlik', 'Konu', 'Seviye', 'Soru', 'Doğru cevap', 'Kaynak', 'Tür'), ('ID', 'Topic', 'Level', 'Question', 'Correct answer', 'Source', 'Type'),
             ('المعرّف', 'الموضوع', 'المستوى', 'السؤال', 'الإجابة الصحيحة', 'المصدر', 'النوع')),
    'mod': ('düzenlendi', 'edited', 'معدَّل'), 'hidden': ('kaldırıldı', 'removed', 'محذوف'),
    'correct': ('Doğru cevap', 'Correct answer', 'الإجابة الصحيحة'), 'exp': ('Açıklama', 'Explanation', 'الشرح'),
    'wexp': ('Bu şık neden yanlış', 'Why this option is wrong', 'لماذا هذا الخيار خاطئ'), 'src': ('Kaynak', 'Source', 'المصدر'),
    'del_q': ('Seçili {n} soru silinsin mi? Hazır sorular "Kaldırılanlar" listesinden geri yüklenebilir; kendi sorularınız kalıcı silinir.',
              'Delete the {n} selected questions? Built-in questions can be restored from the "Removed" list; your own questions are deleted permanently.',
              'حذف {n} من الأسئلة المحددة؟ يمكن استعادة الأسئلة الجاهزة من قائمة "المحذوفة"، أما أسئلتك فتُحذف نهائياً.'),
    'exp_done': ('{n} soru dışa aktarıldı:\n{p}', '{n} questions exported:\n{p}', 'تم تصدير {n} سؤال:\n{p}'),
    'imp_done': ('{a} soru eklendi, {s} atlandı.', '{a} questions added, {s} skipped.', 'أضيف {a} سؤال وتُخطّي {s}.'),
    # düzenleyici
    'ed_new': ('Yeni soru', 'New question', 'سؤال جديد'), 'ed_edit': ('Soruyu düzenle', 'Edit question', 'تعديل السؤال'),
    'ed_topic': ('Konu', 'Topic', 'الموضوع'), 'ed_level': ('Seviye', 'Level', 'المستوى'),
    'ed_src': ('Kaynak (log alanı / parametre)', 'Source (log field / parameter)', 'المصدر (حقل السجل / المعامل)'),
    'ed_q': ('Soru', 'Question', 'السؤال'), 'ed_opt': ('Şık {n}', 'Option {n}', 'الخيار {n}'),
    'ed_ans': ('Doğru şık', 'Correct option', 'الخيار الصحيح'),
    'ed_help': ('Dilleri ayrı sekmelerde yazın; boş bırakılan dilde İngilizce (o da yoksa Türkçe) gösterilir. En az 2 şık gerekir; 4. şık isteğe bağlıdır.',
                'Write each language in its own tab; an empty language shows English (or Turkish). At least 2 options are needed; the 4th is optional.',
                'اكتب كل لغة في تبويبها؛ اللغة الفارغة تعرض الإنجليزية (أو التركية). يلزم خياران على الأقل والرابع اختياري.'),
    'ed_type': ('Soru türü', 'Question type', 'نوع السؤال'),
    'ty_mc': ('Çoktan seçmeli', 'Multiple choice', 'اختيار من متعدد'),
    'ty_open': ('Yorum (yazılı cevap; eğitimci puanlar)', 'Interpretation (written; the instructor grades)', 'تفسير (إجابة كتابية؛ يصححها المدرّب)'),
    'ed_img': ('Görsel', 'Image', 'صورة'), 'ed_img_add': ('🖼 Görsel ekle…', '🖼 Add image…', '🖼 إضافة صورة…'),
    'ed_img_rm': ('Görseli kaldır', 'Remove image', 'إزالة الصورة'), 'ed_img_none': ('(görsel yok)', '(no image)', '(لا صورة)'),
    'ed_img_has': ('Görsel var — önizleme altta', 'Has image — preview below', 'توجد صورة — المعاينة أدناه'),
    'ed_model': ('Örnek cevap', 'Model answer', 'إجابة نموذجية'),
    'ed_kw': ('Aranan kavramlar', 'Key concepts', 'المفاهيم المطلوبة'),
    'ed_kw_ph': ('virgülle ayırın; eş anlamlıları | ile: titreşim|vibe, pervane', 'comma separated; synonyms with |: vibration|vibe, propeller',
                 'افصل بفواصل؛ المرادفات بـ |: اهتزاز|vibe، مروحة'),
    'ed_err_model': ('Yorum sorusu için örnek cevap yazın.', 'Write a model answer for the interpretation question.', 'اكتب إجابة نموذجية لسؤال التفسير.'),
    'ed_err_q': ('Soru metni boş.', 'The question text is empty.', 'نص السؤال فارغ.'),
    'ed_err_opts': ('En az iki şık yazın.', 'Write at least two options.', 'اكتب خيارين على الأقل.'),
    'ed_err_ans': ('Doğru şık boş olamaz.', 'The correct option cannot be empty.', 'لا يمكن أن يكون الخيار الصحيح فارغاً.'),
    'pr_mix': ('Karışık: bu log + soru bankası', 'Mixed: this log + question bank', 'مختلط: هذا السجل + بنك الأسئلة'),
    'pr_bank': ('Soru bankası', 'Question bank', 'بنك الأسئلة'), 'pr_log': ('Yalnız bu log', 'This log only', 'هذا السجل فقط'),
    'pr_wrong': ('Yanlışlarımı tekrar et', 'Review my mistakes', 'راجع أخطائي'), 'pr_q': ('soru', 'questions', 'سؤال'),
    'pr_src_mix': ('Sorular açık logdan ve soru bankasından (öğretici sorular + kütüphaneler + sizin sorularınız) seçilir.',
                   'Questions come from the open log and the question bank (tutorial questions + libraries + your own).',
                   'تُختار الأسئلة من السجل المفتوح ومن بنك الأسئلة (الأسئلة التعليمية + المكتبات + أسئلتك).'),
    'pr_src_bank': ('Sorular soru bankasından seçilir; konu ve seviye süzgeçleri uygulanır.', 'Questions come from the question bank; topic and level filters apply.',
                    'تُختار الأسئلة من بنك الأسئلة مع تطبيق مرشحي الموضوع والمستوى.'),
    'pr_src_log': ('Sorular açık logdan üretilir (kalkış, irtifa, karar, kök neden…).', 'Questions are generated from the open log (takeoff, altitude, verdict, root cause…).',
                   'تُولَّد الأسئلة من السجل المفتوح (الإقلاع، الارتفاع، الحكم، السبب الجذري…).'),
    'pr_src_wrong': ('Daha önce yanlış yaptığınız bankadaki sorular, en çok yanlış yapılan önce gelir.', 'Bank questions you got wrong before, most-missed first.',
                     'أسئلة البنك التي أخطأت فيها سابقاً، الأكثر خطأً أولاً.'),
    'pr_no_wrong': ('Henüz yanlış yapılmış soru yok. Önce bankadan alıştırma yapın.', 'No missed questions yet. Practise from the bank first.',
                    'لا توجد أسئلة أخطأت فيها بعد. تدرّب من البنك أولاً.'),
    'ex_bank': ('Soru bankası', 'Question bank', 'بنك الأسئلة'),
    'ex_bank_log': ('Soru bankası + açık log', 'Question bank + open log', 'بنك الأسئلة + السجل المفتوح'),
    'save': ('Kaydet', 'Save', 'حفظ'), 'cancel': ('Vazgeç', 'Cancel', 'إلغاء'),
}


def tx(k, **a):
    from ..core import qbank as B
    v = TX[k]
    s = B.tx(B.tri(v), lang()) if not isinstance(v[0], tuple) else v[{'tr': 0, 'en': 1, 'ar': 2}.get(lang(), 0)]
    return s.format(**a) if a and isinstance(s, str) else s


class QuestionEditor(QDialog):
    def __init__(self, parent, q=None):
        super().__init__(parent)
        from ..core import qbank as B
        self.B = B; self.q = q or {}
        self.setWindowTitle(tx('ed_edit') if q else tx('ed_new')); self.setMinimumSize(820, 860)
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.topic = QComboBox()
        for k in B.TOPICS: self.topic.addItem(B.topic_name(k, lang()), k)
        self.topic.setCurrentIndex(max(0, self.topic.findData(self.q.get('topic', 'basics'))))
        f.addRow(tx('ed_topic'), self.topic)
        self.level = QComboBox()
        for n in (1, 2, 3): self.level.addItem(B.level_name(n, lang()), n)
        self.level.setCurrentIndex(max(0, self.level.findData(int(self.q.get('level', 1)))))
        f.addRow(tx('ed_level'), self.level)
        self.src = QLineEdit(self.q.get('src', '')); f.addRow(tx('ed_src'), self.src)
        self.typ = QComboBox(); self.typ.addItem(tx('ty_mc'), 'mc'); self.typ.addItem(tx('ty_open'), 'open')
        self.typ.setCurrentIndex(1 if B.is_open(self.q) else 0); f.addRow(tx('ed_type'), self.typ)
        self.img_ref = self.q.get('img')
        ih = QHBoxLayout(); self.img_l = QLabel(); ih.addWidget(self.img_l, 1)
        ih.addWidget(button(tx('ed_img_add'), self._img_add)); ih.addWidget(button(tx('ed_img_rm'), self._img_rm)); f.addRow(tx('ed_img'), ih)
        v.addLayout(f)
        v.addWidget(label(tx('ed_help'), 'muted', wrap=True))
        self.tabs = QTabWidget(); self.w = {}
        n_opt = max(4, len(self.q.get('opts') or []))
        for lg, nm in (('tr', 'Türkçe'), ('en', 'English'), ('ar', 'العربية')):
            w = QWidget(); g = QGridLayout(w)
            qe = QPlainTextEdit(B.tx({lg: (self.q.get('q') or {}).get(lg, '')}, lg)); qe.setFixedHeight(70)
            g.addWidget(QLabel(tx('ed_q')), 0, 0); g.addWidget(qe, 0, 1)
            opts = []
            for i in range(n_opt):
                o = (self.q.get('opts') or [])[i] if i < len(self.q.get('opts') or []) else {}
                le = QLineEdit((o or {}).get(lg, '')); g.addWidget(QLabel(tx('ed_opt', n=i + 1)), i + 1, 0); g.addWidget(le, i + 1, 1); opts.append(le)
            ex = QPlainTextEdit((self.q.get('exp') or {}).get(lg, '')); ex.setFixedHeight(110)
            g.addWidget(QLabel(tx('exp')), n_opt + 1, 0); g.addWidget(ex, n_opt + 1, 1)
            mo = QPlainTextEdit(B.tri(self.q.get('model') or '').get(lg, '')); mo.setFixedHeight(110)
            ml = QLabel(tx('ed_model')); g.addWidget(ml, n_opt + 2, 0); g.addWidget(mo, n_opt + 2, 1)
            kw = QLineEdit(', '.join((self.q.get('kw') or {}).get(lg, []))); kw.setPlaceholderText(tx('ed_kw_ph'))
            kl = QLabel(tx('ed_kw')); g.addWidget(kl, n_opt + 3, 0); g.addWidget(kw, n_opt + 3, 1)
            if lg == 'ar':
                for x in [qe, ex, mo, kw] + opts: x.setLayoutDirection(Qt.RightToLeft)
            self.w[lg] = (qe, opts, ex, mo, kw, g, ml, kl); self.tabs.addTab(w, nm)
        v.addWidget(self.tabs, 1)
        from .pages_x import ImgLabel
        self.img_v = ImgLabel(150); v.addWidget(self.img_v)
        r = QHBoxLayout(); self.ans_l = QLabel(tx('ed_ans') + ':'); r.addWidget(self.ans_l)
        self.ans = QButtonGroup(self)
        for i in range(n_opt):
            rb = QRadioButton(str(i + 1)); self.ans.addButton(rb, i); r.addWidget(rb)
        b = self.ans.button(max(0, int(self.q.get('ans', 0))))
        if b: b.setChecked(True)
        r.addStretch(1); r.addWidget(button(tx('cancel'), self.reject)); r.addWidget(button(tx('save'), self.accept, primary=True)); v.addLayout(r)
        self.tabs.setCurrentIndex({'tr': 0, 'en': 1, 'ar': 2}.get(lang(), 0))
        self.typ.currentIndexChanged.connect(self._mode); self._mode(); self._img_show()

    def _mode(self, *_):
        op = self.typ.currentData() == 'open'
        for qe, opts, ex, mo, kw, g, ml, kl in self.w.values():
            for i, le in enumerate(opts):
                le.setVisible(not op); g.itemAtPosition(i + 1, 0).widget().setVisible(not op)
            for x in (mo, kw, ml, kl): x.setVisible(op)
        self.ans_l.setVisible(not op)
        for b in self.ans.buttons(): b.setVisible(not op)

    def _img_show(self):
        self.img_l.setText(tx('ed_img_has') if self.img_ref else tx('ed_img_none'))
        self.img_v.set_ref(self.img_ref)

    def _img_add(self):
        p, _ = QFileDialog.getOpenFileName(self, tx('ed_img_add'), '', 'Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if not p: return
        try: self.img_ref = self.B.img_from_file(p)
        except Exception as e: return error(self, str(e))
        self._img_show()

    def _img_rm(self):
        self.img_ref = None; self._img_show()

    def value(self):
        n_opt = len(self.w['tr'][1])
        q = {k: v for k, v in self.q.items() if k not in ('origin', 'mod', 'hidden')}
        q['topic'] = self.topic.currentData(); q['level'] = self.level.currentData(); q['src'] = self.src.text().strip()
        q['q'] = {lg: self.w[lg][0].toPlainText().strip() for lg in self.w}
        q['opts'] = [{lg: self.w[lg][1][i].text().strip() for lg in self.w} for i in range(n_opt)]
        q['exp'] = {lg: self.w[lg][2].toPlainText().strip() for lg in self.w}
        q['ans'] = max(0, self.ans.checkedId())
        q['img'] = self.img_ref
        if self.typ.currentData() == 'open':
            q['type'] = 'open'; q['opts'] = []; q['ans'] = -1
            q['model'] = {lg: self.w[lg][3].toPlainText().strip() for lg in self.w}
            q['kw'] = {lg: [g.strip() for g in self.w[lg][4].text().replace('،', ',').split(',') if g.strip()] for lg in self.w}
            return q
        q.pop('type', None); q.pop('model', None); q.pop('kw', None)
        we = self.q.get('wexp') or []
        q['wexp'] = [we[i] if i < len(we) else None for i in range(n_opt)] if we else None
        return q

    def accept(self):
        err = self.B.validate(self.value())
        if err: return error(self, tx('ed_err_' + err))
        super().accept()


class QBankPage(Page):
    def __init__(self, win):
        super().__init__(win)
        from ..core import qbank as B
        self.B = B
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        v.addWidget(label(tx('intro'), 'muted', wrap=True))
        r = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText(tx('search')); self.q.textChanged.connect(self.fill); r.addWidget(self.q, 2)
        self.top = QComboBox(); self.top.addItem(tx('all_t'), None)
        for k in B.TOPICS: self.top.addItem(B.topic_name(k, lang()), k)
        self.lvl = QComboBox(); self.lvl.addItem(tx('all_l'), None)
        for n in (1, 2, 3): self.lvl.addItem(B.level_name(n, lang()), n)
        self.org = QComboBox(); self.org.addItem(tx('all_o'), None)
        for k in B.ORIGINS: self.org.addItem(B.tx(B.tri(B.ORIGINS[k]), lang()), k)
        self.org.addItem(tx('o_mod'), 'mod'); self.org.addItem(tx('o_hidden'), 'hidden')
        for c in (self.top, self.lvl, self.org): c.currentIndexChanged.connect(self.fill); r.addWidget(c, 1)
        self.cnt = label('', 'muted'); r.addWidget(self.cnt)
        v.addLayout(r)
        r = QHBoxLayout()
        self.b_new = button(tx('new'), self.new, primary=True); r.addWidget(self.b_new)
        self.b_edit = button(tx('edit'), self.edit); r.addWidget(self.b_edit)
        r.addWidget(button(tx('dup'), self.dup))
        self.b_del = button(tx('del'), self.delete); r.addWidget(self.b_del)
        self.b_res = button(tx('restore'), self.restore); r.addWidget(self.b_res)
        r.addStretch(1)
        r.addWidget(button(tx('practice'), self.practice))
        r.addWidget(button(tx('export'), self.export)); r.addWidget(button(tx('import'), self.import_))
        v.addLayout(r)
        sp = QSplitter(Qt.Vertical)
        self.tbl = QTableWidget(0, 7); self.tbl.setHorizontalHeaderLabels(list(tx('cols')))
        hh = self.tbl.horizontalHeader(); hh.setSectionResizeMode(QHeaderView.Interactive); hh.setSectionResizeMode(3, QHeaderView.Stretch)
        for c, w_ in ((0, 96), (1, 170), (2, 70), (4, 300), (5, 170), (6, 150)): self.tbl.setColumnWidth(c, w_)
        self.tbl.verticalHeader().setVisible(False); self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows); self.tbl.setWordWrap(False)
        self.tbl.itemSelectionChanged.connect(self._show); self.tbl.cellDoubleClicked.connect(lambda *_: self.edit())
        sp.addWidget(self.tbl)
        from .pages_x import ImgLabel, scroll
        pw = QWidget(); pv = QVBoxLayout(pw); pv.setContentsMargins(0, 0, 0, 0)
        self.img = ImgLabel(340); self.view = QTextBrowser(); self.view.setOpenExternalLinks(False); self.view.setMinimumHeight(160)
        pv.addWidget(self.img); pv.addWidget(self.view, 1); sp.addWidget(scroll(pw))
        sp.setSizes([480, 380]); v.addWidget(sp, 1)
        self.rows = []
        self.fill()

    def on_analysis(self, A):
        pass

    def showEvent(self, e):
        super().showEvent(e); self.fill()

    # ------------------------------------------------------------ liste
    def _all(self):
        return self.B.load(self.win.archive, include_hidden=self.org.currentData() == 'hidden')

    def fill(self, *_):
        from ..core import msgsearch as MS
        B = self.B; lg = lang()
        sel = self._sel_ids()
        qs = self._all()
        t_, l_, o_ = self.top.currentData(), self.lvl.currentData(), self.org.currentData()
        ws = MS.words(self.q.text())
        out = []
        for q in qs:
            if t_ and q.get('topic') != t_: continue
            if l_ and int(q.get('level', 1)) != l_: continue
            if o_ == 'hidden':
                if not q.get('hidden'): continue
            elif o_ == 'mod':
                if not q.get('mod'): continue
            elif o_ and q.get('origin') != o_: continue
            if ws:
                blob = MS.norm(' '.join([q['id'], q.get('src', '')] + [B.tx(q['q'], x) for x in B.LANGS] + [B.tx(q.get('exp'), x) for x in B.LANGS] +
                                        [B.tx(o, x) for o in q['opts'] for x in B.LANGS] + [B.tx(q.get('model'), x) for x in B.LANGS if q.get('model')]))
                if not all(w in blob for w in ws): continue
            out.append(q)
        self.rows = out
        self.tbl.setUpdatesEnabled(False); self.tbl.setRowCount(len(out))
        oc = {'builtin': '#60A5FA', 'auto': '#94A3B8', 'user': '#4ADE80'}
        for i, q in enumerate(out):
            typ = B.tx(B.tri(B.ORIGINS.get(q.get('origin'), ('', '', ''))), lg)
            if q.get('mod'): typ += ' · ' + tx('mod')
            if q.get('hidden'): typ += ' · ' + tx('hidden')
            vals = [q['id'], B.topic_name(q.get('topic'), lg), B.level_name(q.get('level'), lg), B.tx(q['q'], lg),
                    ('✎ ' + B.tx(q.get('model'), lg)) if B.is_open(q) else B.tx(q['opts'][int(q.get('ans', 0))], lg) if q['opts'] else '', q.get('src', ''), typ]
            if q.get('img'): vals[0] = '🖼 ' + vals[0]
            for j, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if j == 6: it.setForeground(QColor('#FBBF24' if q.get('mod') else '#F87171' if q.get('hidden') else oc.get(q.get('origin'), '#94A3B8')))
                if j == 0: it.setData(Qt.UserRole, q['id'])
                if j in (3, 4): it.setToolTip(val)
                self.tbl.setItem(i, j, it)
        self.tbl.setUpdatesEnabled(True)
        self.cnt.setText(tx('count', n=len(out)))
        hit = next((i for i, q in enumerate(out) if q['id'] in sel), None) if sel else None
        if out:
            r_ = hit if hit is not None else 0
            self.tbl.setCurrentCell(r_, 0, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        else: self.view.clear()
        self._show()

    def _sel_rows(self):
        rs = sorted({ix.row() for ix in self.tbl.selectedIndexes()})
        if not rs and self.tbl.currentRow() >= 0: rs = [self.tbl.currentRow()]
        return rs

    def _sel_ids(self):
        return [self.rows[r]['id'] for r in self._sel_rows() if r < len(self.rows)]

    def _cur(self):
        r = self._sel_rows()
        return self.rows[r[0]] if r and r[0] < len(self.rows) else None

    def _show(self):
        q = self._cur(); B = self.B; lg = lang()
        if not q: self.view.clear(); self.img.set_raw(None); return
        self.img.set_ref(q.get('img'))
        if B.is_open(q):
            from .pages_x import q_html
            self.view.setHtml(f'<p style="color:#94A3B8">{E(q["id"])}</p>' + q_html(q, lg)); self.b_res.setEnabled(bool(q.get('mod') or q.get('hidden'))); return
        d = 'rtl' if lg == 'ar' else 'ltr'
        h = [f'<div dir="{d}"><p style="color:#94A3B8">{E(q["id"])} · {E(B.topic_name(q.get("topic"), lg))} · {E(B.level_name(q.get("level"), lg))}'
             + (f' · {E(tx("src"))}: <b>{E(q.get("src", ""))}</b>' if q.get('src') else '') + '</p>',
             f'<h3>{E(B.tx(q["q"], lg))}</h3><ol>']
        we = q.get('wexp') or []
        for i, o in enumerate(q['opts']):
            ok = i == int(q.get('ans', 0))
            st = 'color:#4ADE80;font-weight:700' if ok else ''
            extra = f'<br><span style="color:#94A3B8">↳ {E(B.tx(we[i], lg))}</span>' if not ok and i < len(we) and we[i] else ''
            h.append(f'<li style="{st}">{"✔ " if ok else ""}{E(B.tx(o, lg))}{extra}</li>')
        h.append(f'</ol><p><b>{E(tx("exp"))}:</b> {E(B.tx(q.get("exp"), lg))}</p></div>')
        self.view.setHtml(''.join(h))
        self.b_res.setEnabled(bool(q.get('mod') or q.get('hidden')))

    # ------------------------------------------------------------ düzenleme
    def _save(self, q):
        try:
            self.B.save(self.win.archive, q)
        except ValueError as e:
            return error(self, tx('ed_err_' + str(e)) if ('ed_err_' + str(e)) in TX else str(e))
        self.fill(); self._select(q.get('id'))

    def _select(self, qid):
        for i, r in enumerate(self.rows):
            if r['id'] == qid: self.tbl.setCurrentCell(i, 0, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows); self.tbl.scrollToItem(self.tbl.item(i, 0)); return

    def new(self):
        t_ = self.top.currentData()
        dl = QuestionEditor(self, None)
        if t_: dl.topic.setCurrentIndex(max(0, dl.topic.findData(t_)))
        if dl.exec() != QDialog.Accepted: return
        q = dl.value(); q['id'] = self.B.new_id(); self._save(q)

    def edit(self):
        q = self._cur()
        if not q or q.get('hidden'): return
        dl = QuestionEditor(self, q)
        if dl.exec() != QDialog.Accepted: return
        self._save(dl.value())

    def dup(self):
        q = self._cur()
        if not q: return
        c = self.B.copy_of(q)
        dl = QuestionEditor(self, c)
        if dl.exec() != QDialog.Accepted: return
        self._save(dl.value())

    def delete(self):
        ids = self._sel_ids()
        if not ids: return
        if QMessageBox.question(self, tx('title'), tx('del_q', n=len(ids))) != QMessageBox.Yes: return
        for i in ids: self.B.delete(self.win.archive, i)
        self.fill()

    def restore(self):
        for i in self._sel_ids(): self.B.restore(self.win.archive, i)
        self.fill()

    def export(self):
        qs = [r for r in self.rows if not r.get('hidden')]
        ids = set(self._sel_ids())
        if len(ids) > 1: qs = [r for r in qs if r['id'] in ids]
        p, _ = QFileDialog.getSaveFileName(self, tx('export'), 'soru_bankasi.pxbank', 'Soru bankası (*.pxbank *.json)')
        if not p: return
        n = self.B.export_file(p, qs); info(self, tx('exp_done', n=n, p=p))

    def import_(self):
        p, _ = QFileDialog.getOpenFileName(self, tx('import'), '', 'Soru bankası (*.pxbank *.json)')
        if not p: return
        try: a, s = self.B.import_file(self.win.archive, p)
        except Exception as e: return error(self, str(e))
        self.fill(); info(self, tx('imp_done', a=a, s=s))

    def practice(self):
        """Görünen (süzülmüş) sorularla ya da seçili sorularla alıştırma başlatır."""
        ids = self._sel_ids()
        pool = [r['id'] for r in self.rows if not r.get('hidden')] if len(ids) < 2 else ids
        pg = self.win.pages['practice']; self.win.goto('practice')
        pg.start_bank(ids=set(pool))
