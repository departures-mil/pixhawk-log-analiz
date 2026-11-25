"""Kâğıt sınav: soru kitapçığı (görselli), cevap anahtarı (telefon kamerasıyla okunan QR'lı) ve optik form.

Kitapçık ve optik formdaki soru numaraları aynıdır; yorum (açık uçlu) soruları kitapçıkta yazılı cevaplanır, optik formda
o satır boş bırakılır. Cevap anahtarı QR'ı düz metindir ("Sınav 4821 · 1-A 2-C 3-✎ …"): herhangi bir telefon kamerası
internetsiz okur.
"""
from __future__ import annotations
import io

T = {
    'code': ('Sınav kodu', 'Exam code', 'رمز الاختبار'),
    'booklet': ('SORU KİTAPÇIĞI', 'QUESTION BOOKLET', 'كراسة الأسئلة'),
    'key': ('CEVAP ANAHTARI', 'ANSWER KEY', 'مفتاح الإجابة'),
    'info': ('{n} soru · {m} dakika · geçme notu %{p}', '{n} questions · {m} minutes · pass mark {p}%', '{n} سؤالاً · {m} دقيقة · درجة النجاح {p}%'),
    'name': ('Adı Soyadı: ______________________   No: __________', 'Name: ______________________   No: __________', 'الاسم: ______________________   الرقم: __________'),
    'rules': ('Çoktan seçmeli soruları optik forma işaretleyin. ✎ işaretli yorum sorularını bu kitapçıkta, sorunun altındaki satırlara yazın; optik formda o satırı boş bırakın.',
              'Mark the multiple-choice answers on the answer sheet. Write the ✎ interpretation answers in this booklet on the lines below the question; leave that row blank on the answer sheet.',
              'ظلّل إجابات الاختيار من متعدد في ورقة الإجابة. اكتب إجابات أسئلة التفسير ✎ في هذه الكراسة على الأسطر أسفل السؤال، واترك ذلك السطر فارغًا في ورقة الإجابة.'),
    'open': ('✎ Yorum sorusu — cevabınızı aşağıya yazın', '✎ Interpretation question — write your answer below', '✎ سؤال تفسير — اكتب إجابتك أدناه'),
    'model': ('Örnek cevap', 'Model answer', 'إجابة نموذجية'),
    'kw': ('Aranan kavramlar', 'Key concepts', 'المفاهيم المطلوبة'),
    'qr': ('Telefon kamerasıyla okutun: anahtar internetsiz görünür.', 'Scan with a phone camera: the key appears without internet.', 'امسحه بكاميرا الهاتف: يظهر المفتاح دون إنترنت.'),
    'pts': ('Puanlama: çoktan seçmeli doğru = 1, yorum 0 / 0,5 / 1 (eğitimci verir).', 'Scoring: correct multiple choice = 1, interpretation 0 / 0.5 / 1 (given by the instructor).',
            'التصحيح: الاختيار الصحيح = 1، والتفسير 0 / 0.5 / 1 (يحدده المدرّب).'),
    'no': ('No', 'No', 'رقم'), 'ans': ('Cevap', 'Answer', 'الإجابة'), 'topic': ('Konu', 'Topic', 'الموضوع'),
}
LETTERS = {'tr': ['A', 'B', 'C', 'D', 'E'], 'en': ['A', 'B', 'C', 'D', 'E'], 'ar': ['أ', 'ب', 'ج', 'د', 'هـ']}


def _i(lg):
    return ('tr', 'en', 'ar').index(lg) if lg in ('tr', 'en', 'ar') else 0


def letter(k, lg='tr'):
    return LETTERS.get(lg, LETTERS['tr'])[k] if 0 <= k < 5 else '-'


def key_text(exam):
    """Telefon kamerasının okuyacağı düz metin anahtar."""
    lg = exam.get('lang', 'tr'); i = _i(lg)
    parts = []
    for n, q in enumerate(exam['questions'], 1):
        parts.append(f"{n}-{'✎' if q.get('type') == 'open' else letter(q['ans'], 'tr')}")
    return f"{T['code'][i]} {exam.get('code', '')} · {exam.get('title', '')}\n" + ' '.join(parts)


def _qr(text, size_cm):
    import qrcode
    from reportlab.platypus import Image
    from reportlab.lib.units import cm
    q = qrcode.QRCode(box_size=6, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M); q.add_data(text); q.make(fit=True)
    b = io.BytesIO(); q.make_image(fill_color='black', back_color='white').save(b, format='PNG')
    return Image(io.BytesIO(b.getvalue()), width=size_cm * cm, height=size_cm * cm)


def booklet_pdf(exam, path, lh=None):
    from reportlab.platypus import Spacer, KeepTogether, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from . import report as RP, qbank as QB
    lg = exam.get('lang', 'tr'); i = _i(lg)
    K = RP.pdf_kit(lg, lh, footer_extra=f"{T['code'][i]}: {exam.get('code', '')}")
    P, W, cm, colors = K['P'], K['W'], K['cm'], K['colors']
    qst = ParagraphStyle('q', parent=K['base'], fontName='DJB', fontSize=10, leading=14)
    ost = ParagraphStyle('o', parent=K['base'], fontSize=9.5, leading=13)
    head = [P(exam.get('title', ''), K['TT']), P(T['booklet'][i], ParagraphStyle('bk', parent=K['H2'], alignment=1)),
            P(f"{T['code'][i]}: {exam.get('code', '')}  ·  " + T['info'][i].format(n=len(exam['questions']), m=exam.get('time_limit_min', ''), p=exam.get('pass_mark', '')), K['small']),
            Spacer(1, 4), P(T['name'][i], K['base']), Spacer(1, 3), P(T['rules'][i], K['small']), Spacer(1, 8)]
    story = K['besmele']() + head
    for n, q in enumerate(exam['questions'], 1):
        blk = [P(f"{n}. {q['q']}", qst)]
        raw = QB.img_bytes(q.get('img'))
        if raw:
            try:
                im = K['img'](raw, W * 0.92)
                if im.drawHeight > 10.5 * cm:
                    r = 10.5 * cm / im.drawHeight; im.drawHeight *= r; im.drawWidth *= r
                im.hAlign = 'CENTER'; blk += [Spacer(1, 3), im, Spacer(1, 3)]
            except Exception:
                pass
        if q.get('type') == 'open':
            blk.append(P(T['open'][i], K['small']))
            ln = Table([['']] * 6, colWidths=[W], rowHeights=[0.75 * cm] * 6)
            ln.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#94A3B8'))]))
            blk.append(ln)
        else:
            for k, o in enumerate(q['opts']):
                blk.append(P(f"{letter(k, lg)})  {o}", ost))
        blk.append(Spacer(1, 10))
        story.append(KeepTogether(blk))
    K['build'](path, story, exam.get('title', ''))
    return path


def key_pdf(exam, path, lh=None):
    from reportlab.platypus import Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from . import report as RP, qbank as QB
    lg = exam.get('lang', 'tr'); i = _i(lg)
    K = RP.pdf_kit(lg, lh, footer_extra=f"{T['code'][i]}: {exam.get('code', '')}")
    P, W, cm, colors = K['P'], K['W'], K['cm'], K['colors']
    story = [P(exam.get('title', ''), K['TT']), P(T['key'][i], ParagraphStyle('bk', parent=K['H2'], alignment=1)),
             P(f"{T['code'][i]}: {exam.get('code', '')}", K['small']), Spacer(1, 6)]
    qs = exam['questions']
    cells = [f"{n}  {'✎' if q.get('type') == 'open' else letter(q['ans'], lg)}" for n, q in enumerate(qs, 1)]
    cols = 8; rows = [cells[r:r + cols] + [''] * (cols - len(cells[r:r + cols])) for r in range(0, len(cells), cols)]
    t = Table([[P(c, ParagraphStyle('k', parent=K['base'], fontName='DJB', fontSize=11, leading=14)) for c in r] for r in rows], colWidths=[W / cols] * cols)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    qr = _qr(key_text(exam), 4.2)
    side = [qr, P(T['qr'][i], K['small'])]
    lay = Table([[t, side]] if not K['rtl'] else [[side, t]], colWidths=[W - 5 * cm, 5 * cm] if not K['rtl'] else [5 * cm, W - 5 * cm])
    lay.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    # anahtar tablosu dar sütuna sığsın
    t._argW = [(W - 5.2 * cm) / cols] * cols
    story += [lay, Spacer(1, 6), P(T['pts'][i], K['small']), Spacer(1, 8)]
    for n, q in enumerate(qs, 1):
        if q.get('type') != 'open': continue
        story += [P(f"{n}. {q['q']}", K['H2']), P(f"{T['model'][i]}: {q.get('model') or q.get('exp', '')}", K['base'])]
        kw = (q.get('kw') or {}).get(lg) or (q.get('kw') or {}).get('en') or []
        if kw: story.append(P(f"{T['kw'][i]}: " + ' · '.join(g.replace('|', ' / ') for g in kw), K['small']))
        story.append(Spacer(1, 6))
    K['build'](path, story, exam.get('title', '') + ' — ' + T['key'][i])
    return path


def sheet_pdf(exam, path, school='', copies=1):
    from . import omr
    lg = exam.get('lang', 'tr')
    n_opts = max([len(q['opts']) for q in exam['questions'] if q.get('type') != 'open'] or [4])
    return omr.sheet_pdf(path, exam.get('title', ''), exam.get('code', ''), len(exam['questions']), n_opts, lg, school, copies, LETTERS.get(lg))


def grade_sheet(archive, exam, read_res, students=None):
    """Optik okuma sonucunu sınav sonucu olarak kaydeder. Öğrenci adı: sınıf listesinde numarayla başlayan satır
    ("1023 Ali Veli") varsa o ad, yoksa "No 1023". → kayıt"""
    import time
    from . import exam as X
    ans = []
    for q, a in zip(exam['questions'], read_res['answers'] + [-1] * len(exam['questions'])):
        ans.append('' if q.get('type') == 'open' else (a if a >= 0 else -1))
    no = (read_res.get('no') or '').replace('*', '').strip()
    name = None
    for s in students or []:
        s = str(s).strip(); head = s.split(' ', 1)
        if no and head[0].lstrip('0') == no.lstrip('0') and len(head) > 1: name = head[1].strip(); break
    st = name or (f"No {no.lstrip('0') or '0'}" if no else '?')
    now = time.time()
    r = X.save_result(archive, exam, st, ans, now, now)
    r = dict(r, via='omr', no=no, multi=[k + 1 for k, a in enumerate(read_res['answers']) if a == -2])
    archive.rec_put('result', r['id'], r)
    return r
