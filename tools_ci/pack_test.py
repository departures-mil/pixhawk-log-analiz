"""Çevrimdışı paket doğrulaması (packs.yml): gerçek NLLB-200 modeliyle havacılık cümlelerini çevirir ya da gerçek Tesseract ile
TR/EN/AR metni okur. Programın kendi kodu (app.core.ceviri / app.core.ocr) kullanılır; sonuç bozuksa çıkış kodu 1.

  python tools_ci/pack_test.py nllb <model klasörü>
  python tools_ci/pack_test.py ocr               (PX_PACKS_DIR altında 'ocr' paketi kurulu olmalı)
"""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core import ceviri as CV

SENT = {
    'en': ['Pre-arm checks failed: compass not calibrated.',
           'Set Q_ASSIST_SPEED to 16 m/s before the next VTOL flight.',
           'The aircraft lost airspeed during the approach and stalled before landing.',
           'Replace the damaged propeller and check the motor mount.'],
    'tr': ['Uçuş öncesi kontrolde batarya gerilimi 22,1 V ölçüldü.', 'Pervane değiştirildi ve motor bağlantısı kontrol edildi.'],
    'ar': ['تم استبدال المروحة بعد الهبوط الاضطراري.', 'يجب فحص البوصلة قبل الطيران.'],
}


def nllb(d):
    e = CV.NLLBEngine(d, 'NLLB')
    bad = 0
    for src, tgts in (('en', ('tr', 'ar')), ('tr', ('en', 'ar')), ('ar', ('en', 'tr'))):
        for tgt in tgts:
            t0 = time.time()
            out = e.batch(SENT[src], src, tgt, CV.entries({}), [])
            print(f'--- {src} -> {tgt}  ({time.time() - t0:.1f} s)')
            for s, o in zip(SENT[src], out):
                print('  ', s, '\n   =>', o)
                ok = bool(o.strip()) and (bool(re.search('[؀-ۿ]', o)) == (tgt == 'ar'))
                for i in re.findall(r'\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b', s): ok &= i in o
                if not ok: bad += 1; print('   !! FAIL')
    return bad


def ocr():
    import pymupdf
    from app.core import ocr as O, paketler as PK
    assert PK.tesseract_exe(), 'pack not installed'
    font = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fccore', 'fonts')
    css = '@font-face {font-family: ara; src: url(NotoSansArabic-400.ttf);} @font-face {font-family: lat; src: url(Inter-400.ttf);} * {margin:0}'
    cases = [('tr', 'lat', 'ltr', 'BAKIM FORMU: Pervane değişimi yapıldı. Batarya 25,2 V.', ['Pervane', '25,2']),
             ('en', 'lat', 'ltr', 'Set BATT_MONITOR to 4 and calibrate the airspeed sensor.', ['BATT_MONITOR', 'airspeed']),
             ('ar', 'ara', 'rtl', 'تم استبدال المروحة بعد الهبوط الاضطراري.', ['المروحة', 'الهبوط'])]
    bad = 0
    for lg, fam, d, text, must in cases:
        doc = pymupdf.open(); p = doc.new_page(width=700, height=160)
        p.insert_htmlbox(pymupdf.Rect(20, 30, 680, 140), f'<p dir="{d}" style="font-family:{fam};font-size:16pt">{text}</p>',
                         css=css, archive=pymupdf.Archive(font))
        im = O.pdf_page_image(p, 200)
        for hint in (lg, 'auto'):
            out = O.ocr_offline(im, hint)
            ok = all(m in out for m in must)
            print(lg, hint, '=>', out.replace('\n', ' | '), '' if ok else '!! FAIL')
            bad += 0 if ok else 1
    return bad


if __name__ == '__main__':
    n = nllb(sys.argv[2]) if sys.argv[1] == 'nllb' else ocr()
    print('FAILURES:', n)
    sys.exit(1 if n else 0)
