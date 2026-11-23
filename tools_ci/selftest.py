"""CI öz-testi: 7 sentetik senaryo doğru teşhis edilmeli, raporlar üretilebilmeli."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core import synth, loader, analysis, report, advisor

EXPECT = {'normal': ('normal', None), 'gps_loss': ('crash', 'gps'), 'battery': ('crash', 'battery'), 'vibration': ('incident', 'vibration'),
          'radio_loss': ('incident', 'radio'), 'stall': ('crash', 'stall'), 'compass': ('crash', 'compass')}
d = tempfile.mkdtemp(); bad = 0
for sc, (kind, cause) in EXPECT.items():
    p = os.path.join(d, sc + '.BIN'); synth.generate(p, sc)
    A = analysis.Analysis(loader.load(p))
    got = (A.verdict.get('kind'), (A.root or {}).get('cause'))
    ok = got[0] == kind and (cause is None or got[1] == cause)
    bad += not ok
    print(f'{sc:11s} -> {got} {"OK" if ok else "FAIL"}')
    if sc == 'gps_loss':
        for lg in ('tr', 'en', 'ar'):
            rd = report.ReportData(A, lg, None, online_map=False)
            report.build_pdf(rd, os.path.join(d, f'r_{lg}.pdf')); report.build_docx(rd, os.path.join(d, f'r_{lg}.docx'))
            print(lg, advisor.offline_answer(A, {'tr': 'Hangi saniyede kalkış yapıldı?', 'en': 'When did it take off?', 'ar': 'متى حدث الإقلاع؟'}[lg], lg)[:80])

# ---- Antet: hazır antet, besmele yalnızca ilk sayfada, Word şablonu içe aktarma
from app.core import letterhead as LHM
try:
    top, bottom = LHM.bands(LHM.resolve(LHM.PRESET['bg']))
    assert 3.0 < top < 5.5, top
    A = analysis.Analysis(loader.load(os.path.join(d, 'normal.BIN')))
    for lg in ('tr', 'ar'):
        rd = report.ReportData(A, lg, None, online_map=False)
        pp = os.path.join(d, f'lh_{lg}.pdf'); dp = os.path.join(d, f'lh_{lg}.docx')
        report.build_pdf(rd, pp, LHM.PRESET); report.build_docx(rd, dp, LHM.PRESET)
        from docx import Document
        doc = Document(dp)
        body_imgs = [p for p in doc.paragraphs[:2] if p._p.xpath('.//pic:pic')]
        assert body_imgs, 'besmele missing on first page'
        assert len(doc.sections) == 1 and doc.sections[0].top_margin.cm >= top - 0.01
        print('letterhead', lg, 'OK', os.path.getsize(pp) // 1024, 'KB pdf', os.path.getsize(dp) // 1024, 'KB docx')
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    td = Document(); h = td.sections[0].header
    p = h.paragraphs[0]; p.add_run('Test Org / Birim'); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    td.add_paragraph('\uFDFD'); tp = os.path.join(d, 'tpl.docx'); td.save(tp)
    r = LHM.import_docx(tp)
    assert os.path.exists(r['bg']) and r['besmele'] and 'Test Org / Birim' in r['texts'], r
    assert len(LHM.preview_images({**LHM.PRESET})) == 2
    print('letterhead import/preview OK')
except Exception as e:
    import traceback; traceback.print_exc(); bad += 1

# ---- v1.0.2: hızlı okuyucu, profiller, anomali, arama, sınav/sertifika, pilot kartı, güvenlik, kısa/uzun/şifreli rapor
try:
    import numpy as np, tempfile as _tf
    os.environ.setdefault('APPDATA', _tf.mkdtemp())
    from app.core import fleet, exam as X, security, search, anomaly, profiles, lessons, practice
    from app.core.archive import Archive, file_uid
    p = os.path.join(d, 'gps_loss.BIN')
    Lf = loader.load(p, use_cache=False); Ls = loader._load_bin(p)
    for m in ('ATT', 'GPS', 'BAT', 'VIBE'):
        a, b = Lf.s(m), Ls.s(m)
        assert abs(len(a['t']) - len(b['t'])) <= max(3, 0.02 * len(b['t'])), (m, len(a['t']), len(b['t']))
    print('fastbin == pymavlink OK')
    A = analysis.Analysis(loader.load(p))
    assert A.profile in profiles.PROFILES and A.th
    for lg in ('tr', 'en', 'ar'):
        rd = report.ReportData(A, lg, None, online_map=False, mode='short')
        report.build_pdf(rd, os.path.join(d, f's_{lg}.pdf')); report.build_docx(rd, os.path.join(d, f's_{lg}.docx'))
    rd = report.ReportData(A, 'tr', None, online_map=False, sections=[['summary', True], ['params', False], ['facts', True]])
    assert 'params' not in rd.sections
    ep = os.path.join(d, 'enc.pdf'); report.build_pdf(rd, ep, encrypt='1234')
    assert b'/Encrypt' in open(ep, 'rb').read()
    print('report short/sections/encrypted OK')
    An = analysis.Analysis(loader.load(os.path.join(d, 'normal.BIN')))
    assert anomaly.learn(An, 'x1') in (True, False); assert An.anomaly_index <= 30, An.anomaly_index
    arc = Archive(os.path.join(d, 'arch.db'))
    uid = file_uid(p); arc.add_analysis(uid, A, p, 'ci', False)
    fleet.ensure_aircraft(arc, A)
    pid = fleet.add_pilot(arc, 'Test Pilot', 'L1'); arc.set_field(uid, pilot=pid)
    fleet.pilot_pdf(arc, pid, os.path.join(d, 'pilot.pdf'), 'ar', None)
    f = search.parse('son 3 ayda GPS kaybı yaşayan uçuşlar'); assert f.get('days') == 90 and f.get('topics') == ['gps'], f
    assert search.parse('kırım olan multikopter uçuşları').get('verdict') == 'crash'
    cid = X.create_class(arc, 'C', 'I', ['S1'])
    eid = X.create_exam(arc, cid, 'E', A, 'tr', 6, 10, 50, {'type': 'ci'})
    ex = arc.rec_get('exam', eid if isinstance(eid, str) else eid['id'])
    r = X.save_result(arc, ex, 'S1', [q['ans'] for q in ex['questions']], 0, 60)
    assert r['passed'] and r.get('cert_id') and X.find_certificate(arc, r['cert_id'])
    X.certificate_pdf(arc, r, os.path.join(d, 'cert.pdf'), 'ar', None)
    assert lessons.build(A, 'ar') and all(q.get('wexp') for q in practice.generate(A, 'tr', 8, 1) if 'lib' not in q)
    blob = security.encrypt(b'hello', 'pw'); assert security.decrypt(blob, 'pw') == b'hello'
    try: security.decrypt(blob, 'x'); raise AssertionError('wrong pw accepted')
    except ValueError: pass
    assert security.unprotect(security.protect('secret-key')) == 'secret-key'
    print('fleet/pilot/search/exam/certificate/security OK')
except Exception:
    import traceback; traceback.print_exc(); bad += 1
sys.exit(1 if bad else 0)
