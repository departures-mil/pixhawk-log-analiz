"""Sınav ve sertifika modu.

Eğitimci bir sınıf açar, bir log (senaryo, arşivdeki uçuş veya dosya) üzerinden sabit sorulu sınav oluşturur.
Öğrenciler aynı soruları çözer (süre sınırı, geçme notu); puanlar kaydedilir ve geçenlere antetli, QR doğrulamalı
sertifika PDF'i üretilir. Sınav paketi (.pxexam) ve sonuç dosyası (.pxres) bilgisayarlar arasında taşınabilir;
GitHub/LAN eşitlemesiyle de otomatik paylaşılır. Paketler isteğe bağlı parolayla şifrelenir.
"""
from __future__ import annotations
import json, os, time, uuid, hashlib


def new_id(n=10):
    return uuid.uuid4().hex[:n].upper()


def new_code(archive=None):
    """Kâğıt / telefon sınavı için 4 haneli sınav kodu (mevcut sınavlarla çakışmaz)."""
    import random
    used = {e.get('code') for e in archive.rec_list('exam')} if archive is not None else set()
    while True:
        c = f'{random.SystemRandom().randrange(10000):04d}'
        if c not in used: return c


def ensure_code(archive, exam):
    if not exam.get('code'):
        exam = dict(exam, code=new_code(archive)); archive.rec_put('exam', exam['id'], exam)
    return exam


def create_class(archive, name, instructor, students=()):
    cid = new_id(8)
    archive.rec_put('class', cid, {'id': cid, 'name': name, 'instructor': instructor, 'students': list(students), 'created': time.strftime('%Y-%m-%d')})
    return cid


def create_exam(archive, class_id, title, A, lang='tr', n=10, time_limit_min=20, pass_mark=70, source=None, questions=None):
    from .practice import generate
    seed = int(time.time())
    qs = list(questions) if questions is not None else generate(A, lang, n, seed)
    for q in qs:  # grafik/kütüphane bağlantılarını koru, numpy değerlerini temizle
        if q.get('t') is not None: q['t'] = float(q['t'])
    eid = new_id(10)
    archive.rec_put('exam', eid, {'id': eid, 'class_id': class_id, 'title': title, 'lang': lang, 'questions': qs, 'n': len(qs), 'code': new_code(archive),
                                  'time_limit_min': int(time_limit_min), 'pass_mark': int(pass_mark), 'source': source or {},
                                  'log_name': os.path.basename(A.L.path) if A is not None else '', 'created': time.strftime('%Y-%m-%d %H:%M')})
    return eid


def bank_questions(archive, lang='tr', n=10, topics=None, levels=None, A=None, mix_log=False, seed=None):
    """Soru bankasından sınav soruları (konu/seviye süzgeçli); mix_log ise açık logdan da en fazla üçte biri eklenir."""
    import random
    from . import qbank as QB
    from .practice import generate
    seed = int(time.time()) if seed is None else seed
    nl = n // 3 if (mix_log and A is not None) else 0
    rnd = random.Random(seed)
    qs = [QB.to_item(q, lang, rnd) for q in QB.pick(QB.load(archive), topics, levels, n - nl, seed)]
    if nl:
        qs += [x for x in generate(A, lang, n, seed) if not x.get('lib')][:nl]
        rnd.shuffle(qs)
    return qs


def is_open(q):
    return (q or {}).get('type') == 'open'


def auto_scores(exam, answers):
    """Açık uçlu cevaplar için anahtar kavram puanı önerisi: {indeks: {'score': 0..1, 'pts': 0|0.5|1, 'hit': [...]}}"""
    from . import visq
    out = {}
    for i, (q, a) in enumerate(zip(exam['questions'], answers)):
        if not is_open(q): continue
        sc, hit = visq.score_open(a if isinstance(a, str) else '', q.get('kw'))
        out[str(i)] = {'score': sc, 'pts': visq.suggest_points(sc), 'hit': hit}
    return out


def grade(exam, answers, manual=None, auto=None):
    """→ (puan, soru sayısı, yüzde, geçti mi). Çoktan seçmeli: doğruysa 1. Açık uçlu: eğitimcinin verdiği puan (0/0,5/1),
    verilmemişse anahtar kavram önerisi."""
    qs = exam['questions']; manual = manual or {}
    if auto is None: auto = auto_scores(exam, answers)
    ok = 0.0
    for i, (q, a) in enumerate(zip(qs, answers)):
        if is_open(q):
            k = str(i)
            ok += float(manual[k]) if k in manual else float((auto.get(k) or {}).get('pts', 0))
        elif a == q['ans']:
            ok += 1
    ok = round(ok, 2)
    pct = 100.0 * ok / max(1, len(qs))
    return (int(ok) if ok == int(ok) else ok), len(qs), pct, pct >= exam.get('pass_mark', 70)


def pending(exam, result):
    """Eğitimcinin henüz puanlamadığı açık uçlu soru sayısı."""
    man = result.get('manual') or {}
    return sum(1 for i, q in enumerate(exam.get('questions', [])) if is_open(q) and str(i) not in man)


def _cert(rid, student, exam):
    return time.strftime('%Y%m%d') + '-' + hashlib.sha256(f'{rid}{student}{exam["id"]}'.encode()).hexdigest()[:8].upper()


def save_result(archive, exam, student, answers, started, finished):
    auto = auto_scores(exam, answers)
    ok, tot, pct, passed = grade(exam, answers, None, auto)
    rid = new_id(12)
    cert = _cert(rid, student, exam) if passed else ''
    r = {'id': rid, 'exam_id': exam['id'], 'class_id': exam.get('class_id'), 'student': student, 'answers': answers, 'score': ok, 'total': tot,
         'pct': round(pct, 1), 'passed': passed, 'started': started, 'finished': finished, 'duration_s': int(max(0, finished - started)),
         'date': time.strftime('%Y-%m-%d %H:%M'), 'cert_id': cert, 'auto': auto, 'manual': {}}
    archive.rec_put('result', rid, r)
    return r


def regrade(archive, result, manual):
    """Eğitimci açık uçlu cevapları puanladı: {indeks: 0|0.5|1} → puan, yüzde, geçme ve sertifika yeniden hesaplanır."""
    exam = archive.rec_get('exam', result['exam_id']) or {}
    r = dict(result); r['manual'] = {str(k): float(v) for k, v in manual.items()}
    ok, tot, pct, passed = grade(exam, r.get('answers', []), r['manual'], r.get('auto'))
    r.update({'score': ok, 'total': tot, 'pct': round(pct, 1), 'passed': passed, 'graded': time.strftime('%Y-%m-%d %H:%M')})
    if passed and not r.get('cert_id'): r['cert_id'] = _cert(r['id'], r['student'], exam)
    if not passed: r['cert_id'] = ''
    archive.rec_put('result', r['id'], r)
    return r


def results_of(archive, exam_id=None, class_id=None):
    rs = archive.rec_list('result')
    if exam_id: rs = [r for r in rs if r.get('exam_id') == exam_id]
    if class_id: rs = [r for r in rs if r.get('class_id') == class_id]
    return sorted(rs, key=lambda r: (-r.get('pct', 0), r.get('duration_s', 0)))


# ------------------------------------------------------------ paket taşıma
def export_package(archive, exam_id, path, password=''):
    ex = archive.rec_get('exam', exam_id); cl = archive.rec_get('class', ex.get('class_id')) if ex else None
    data = json.dumps({'type': 'pxexam', 'v': 1, 'exam': ex, 'class': cl}, ensure_ascii=False).encode()
    _write(path, data, password)
    return path


def export_results(archive, exam_id, path, password=''):
    data = json.dumps({'type': 'pxres', 'v': 1, 'results': results_of(archive, exam_id)}, ensure_ascii=False).encode()
    _write(path, data, password)
    return path


def import_file(archive, path, password=''):
    from . import security
    raw = open(path, 'rb').read()
    if security.is_encrypted(raw):
        raw = security.decrypt(raw, password)
    d = json.loads(raw.decode('utf-8'))
    n = 0
    if d.get('type') == 'pxexam':
        if d.get('class'): archive.rec_put('class', d['class']['id'], d['class']); n += 1
        if d.get('exam'): archive.rec_put('exam', d['exam']['id'], d['exam']); n += 1
    elif d.get('type') == 'pxres':
        for r in d.get('results', []):
            if archive.rec_get('result', r['id']) is None: archive.rec_put('result', r['id'], r); n += 1
    return d.get('type'), n


def _write(path, data, password):
    from . import security
    if password: data = security.encrypt(data, password)
    with open(path, 'wb') as f: f.write(data)


# ------------------------------------------------------------ sertifika
CT = {
    'title': ('BAŞARI SERTİFİKASI', 'CERTIFICATE OF ACHIEVEMENT', 'شهادة إنجاز'),
    'body': ('{n}', '{n}', '{n}'),
    'txt': ('"{e}" uçuş logu analiz sınavını %{p:.0f} başarı ile tamamlamıştır.', 'has successfully completed the flight-log analysis exam "{e}" with a score of {p:.0f}%.', 'أتمّ بنجاح اختبار تحليل سجل الطيران "{e}" بنسبة {p:.0f}%.'),
    'class': ('Sınıf', 'Class', 'الصف'), 'instr': ('Eğitimci', 'Instructor', 'المدرّب'), 'date': ('Tarih', 'Date', 'التاريخ'),
    'score': ('Puan', 'Score', 'الدرجة'), 'cert': ('Sertifika no', 'Certificate no', 'رقم الشهادة'),
    'verify': ('Doğrulama: QR kodu bu programın Rapor Doğrulama sayfasında okutun veya sertifika numarasını yazın.', 'Verification: scan the QR code or type the certificate number in the Verify page of this program.', 'التحقق: امسح رمز QR أو اكتب رقم الشهادة في صفحة التحقق في هذا البرنامج.'),
    'sign': ('İmza', 'Signature', 'التوقيع'),
}


def certificate_pdf(archive, result, path, lang='tr', lh=None):
    import io
    from reportlab.platypus import Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from . import report as RP
    import qrcode
    i = ('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0
    ex = archive.rec_get('exam', result['exam_id']) or {}; cl = archive.rec_get('class', result.get('class_id')) or {}
    K_ = RP.pdf_kit(lang, lh, footer_extra=f"{CT['cert'][i]}: {result.get('cert_id')}")
    P, tbl, W, cm, colors = K_['P'], K_['tbl'], K_['W'], K_['cm'], K_['colors']
    big = ParagraphStyle('cb', parent=K_['TT'], fontSize=26, leading=32)
    name = ParagraphStyle('cn', parent=K_['TT'], fontSize=22, leading=28, textColor=colors.HexColor('#111827'))
    mid = ParagraphStyle('cm', parent=K_['base'], fontSize=12, leading=17, alignment=TA_CENTER)
    story = K_['besmele']() + [Spacer(1, 1.2 * cm), P(CT['title'][i], big), Spacer(1, 0.9 * cm), P(result['student'], name), Spacer(1, 0.5 * cm),
                               P(CT['txt'][i].format(e=ex.get('title', ''), p=result.get('pct', 0)), mid), Spacer(1, 1.0 * cm)]
    rows = [[CT['class'][i], cl.get('name', '-')], [CT['instr'][i], cl.get('instructor', '-')], [CT['date'][i], result.get('date', '')],
            [CT['score'][i], f"{result.get('score')}/{result.get('total')} (%{result.get('pct', 0):.0f})"], [CT['cert'][i], result.get('cert_id', '')]]
    story.append(tbl(rows, None, [5 * cm, W - 5 * cm], fs=10))
    q = qrcode.QRCode(box_size=6, border=1); q.add_data(f"PLACERT|{result.get('cert_id')}|{result['student'][:40]}|{result.get('pct', 0):.0f}"); q.make(fit=True)
    b = io.BytesIO(); q.make_image(fill_color='black', back_color='white').save(b, format='PNG')
    qr = Image(io.BytesIO(b.getvalue()), width=3.2 * cm, height=3.2 * cm)
    sig = [P('______________________', mid), P(f"{CT['sign'][i]} · {cl.get('instructor', '')}", mid)]
    row = [qr, sig] if lang != 'ar' else [sig, qr]
    t = Table([row], colWidths=[4 * cm, W - 4 * cm] if lang != 'ar' else [W - 4 * cm, 4 * cm]); t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story += [Spacer(1, 1.2 * cm), t, Spacer(1, 0.4 * cm), P(CT['verify'][i], K_['small'])]
    K_['build'](path, story, CT['title'][i])
    return path


def find_certificate(archive, cert_id):
    cid = (cert_id or '').strip().upper()
    for r in archive.rec_list('result'):
        if r.get('cert_id') and r['cert_id'].upper() == cid: return r
    return None
