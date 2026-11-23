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
sys.exit(1 if bad else 0)
