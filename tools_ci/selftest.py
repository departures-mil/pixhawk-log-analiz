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
sys.exit(1 if bad else 0)
