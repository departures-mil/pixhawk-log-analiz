"""CI öz-testi: 7 sentetik senaryo doğru teşhis edilmeli, raporlar üretilebilmeli."""
import os, sys, tempfile, time
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

# ---- v1.0.3: Parametre Merkezi, ders kitabı, video, gerçek kaza kütüphanesi
try:
    from app.core import pcenter as PCm, pcritical, textbook, video, crashlib
    db = PCm.PDB.get()
    print('params:', 'full' if db.full else 'fallback', {v: db.count(v) for v in db.vehicles}, 'tx:', {k: len(v) for k, v in db.tx.items()})
    if db.full:
        for v in ('Plane', 'Copter', 'Rover', 'Sub'):
            assert db.count(v) > 1500, (v, db.count(v))
    top = [k for k, _ in PCm.search('batarya azalınca eve dönsün', 'Copter', 4)]
    assert 'BATT_FS_LOW_ACT' in top, top
    assert any(k.startswith('FS_THR') for k, _ in PCm.search('kumanda kaybında iniş yapsın', 'Copter', 6))
    P_ = PCm.parse_text('# c\nARMING_CHECK,0\n1 1 RTL_ALT 1500 9\nFS_THR_ENABLE\t0\nBATT_MONITOR 4\nBATT_FS_LOW_ACT,0')
    assert P_ == {'ARMING_CHECK': 0, 'RTL_ALT': 1500, 'FS_THR_ENABLE': 0, 'BATT_MONITOR': 4, 'BATT_FS_LOW_ACT': 0}, P_
    for fm in ('mp', 'qgc', 'csv'):
        fp = os.path.join(d, 'p.' + fm); PCm.write_file(P_, fp, fm); assert PCm.read_file(fp) == P_, fm
    rk = PCm.risks(P_, 'Copter', 'ar'); assert {r['param'] for r in rk} >= {'ARMING_CHECK', 'FS_THR_ENABLE', 'BATT_FS_LOW_ACT'}, rk
    assert PCm.detect_vehicle({'WPNAV_SPEED': 1, 'MOT_THST_HOVER': .3}) == 'Copter'
    assert [b for b, _, on in PCm.decode_bits(5, {'0': 'a', '1': 'b', '2': 'c'}) if on] == [0, 2]
    assert 'BATT_FS_LOW_ACT' in PCm.offline_answer('batarya azalınca eve dönsün', 'Copter', 'tr')
    arc2 = Archive(os.path.join(d, 'arch2.db'))
    PCm.set_mark(arc2, 'RTL_ALT', star=True, note='n'); assert PCm.marks(arc2)['RTL_ALT']['star']
    rid = PCm.save_pset(arc2, P_, 'set1', 'Copter', 'not'); assert PCm.psets(arc2)[0]['params']['RTL_ALT'] == 1500
    assert len(pcritical.critical('Plane')) > 40
    for lg in ('tr', 'ar'):
        textbook.param_report(P_, 'Copter', 'ci.param', lg, os.path.join(d, f'prep_{lg}.pdf'), LHM.PRESET)
    t0 = time.time(); bp = os.path.join(d, 'book_ar.pdf'); textbook.build_book(bp, 'ar', LHM.PRESET)
    assert os.path.getsize(bp) > 300_000; print('textbook ar', os.path.getsize(bp) // 1024, 'KB', round(time.time() - t0, 1), 's')
    textbook.build_book(os.path.join(d, 'book_tr.pdf'), 'tr', None, ['intro', 'causes', 'params'])
    Av = analysis.Analysis(loader.load(os.path.join(d, 'gps_loss.BIN')))
    vp = os.path.join(d, 'v.mp4'); r = video.export(Av, vp, 'ar', target_s=25, voice='none', size=(640, 360), fps=8)
    assert os.path.getsize(vp) > 50_000 and os.path.exists(r['srt']), r
    print('video OK', r)
    cl = crashlib.load(); print('crashlib cases:', len(cl.get('cases') or []))
    print('v1.0.3 param center / textbook / video OK')
except Exception:
    import traceback; traceback.print_exc(); bad += 1

# ---- v1.0.4: uçuş bilgileri formu, 'Neden düştü?', problem çözücü, havacılık sözlüğü
try:
    from app.core import flightinfo as FI, why as WHY, solver as SV, glossary as GL
    from app.core.analysis import fmt_t as _ft
    Ls = loader.load(os.path.join(d, 'stall.BIN'))
    det, src = FI.detect(Ls); print('detect:', det)
    info = {**det, 'crashed': 'yes', 'power': 'ice', 'gas_cc': '55', 'stroke': '2', 'airframe': 'vtail', 'autopilot': 'Cube Orange'}
    As = analysis.Analysis(Ls, info=info)
    assert As.verdict.get('kind') == 'crash', As.verdict
    assert As.why and As.why.get('conf', 0) > 0.5, As.why
    for lg in ('tr', 'en', 'ar'):
        Rw = WHY.render(As, lg, _ft); assert Rw['sentence'] and Rw['chain'], Rw
        R = SV.solve(As, ['stall'], {'tr': 'havada hız kaybedip düştü', 'en': 'lost speed and fell', 'ar': 'فقد السرعة وسقط'}[lg], lg)
        md = SV.to_markdown(R, lg); assert len(md) > 400
        rows_ = FI.rows(info, lg); assert len(rows_) >= 5
        rd = report.ReportData(As, lg, None, online_map=False); report.build_pdf(rd, os.path.join(d, f'why_{lg}.pdf'))
    print('why:', WHY.render(As, 'tr', _ft)['sentence'][:120])
    # kullanıcı "kırım yok" der, log da normal: normal kalmalı
    An = analysis.Analysis(loader.load(os.path.join(d, 'normal.BIN')), info={'crashed': 'no'})
    assert An.verdict.get('kind') == 'normal', An.verdict
    # sözlük: arm / prearm doğru terimle
    assert 'arm' in GL.fix('ön kol kontrolü başarısız', 'tr').lower(), GL.fix('ön kol kontrolü başarısız', 'tr')
    x, tk = GL.protect('Disable prearm display'); assert tk, x
    c = FI.conf({}); assert c['ask'] is True
    print('v1.0.4 flight info / why / solver / glossary OK')
except Exception:
    import traceback; traceback.print_exc(); bad += 1
# ---- v1.0.6: uçuş öncesi .param kontrol listesi, PID/TECS ayar önerileri
try:
    from app.core import preflight as PF, tuning as TU
    Ln = loader.load(os.path.join(d, 'normal.BIN')); An = analysis.Analysis(Ln)
    for lg in ('tr', 'en', 'ar'):
        r = PF.checklist(Ln.params, 'Plane', lg); assert r['items'] and r['status'] in ('go', 'caution', 'nogo'), r
        assert PF.to_text(r).count('\n') > 5
        tr_ = TU.analyze(An, lg); assert 'axes' in tr_ and tr_['disclaimer']
    bad_p = dict(Ln.params); bad_p.update({'ARMING_CHECK': 0, 'THR_FAILSAFE': 0, 'BATT_MONITOR': 0})
    r = PF.checklist(bad_p, 'Plane', 'tr'); assert r['status'] == 'nogo', r['counts']
    fixed = PF.apply_fixes(bad_p, r); assert fixed['ARMING_CHECK'] == 1 and fixed['THR_FAILSAFE'] == 1
    r2 = PF.checklist({'FS_THR_ENABLE': 1, 'FS_THR_VALUE': 975, 'RC3_MIN': 1100, 'FS_EKF_ACTION': 1, 'ARMING_CHECK': 1,
                       'BATT_MONITOR': 4, 'BATT_LOW_VOLT': 14.0, 'BATT_CRT_VOLT': 13.2, 'BATT_FS_LOW_ACT': 2, 'BATT_FS_CRT_ACT': 1,
                       'BATT_CAPACITY': 5000, 'RTL_ALT': 3000, 'LOG_BITMASK': 180222, 'FENCE_ENABLE': 1, 'FENCE_ACTION': 1}, 'Copter', 'en')
    assert r2['status'] == 'go', [(i['id'], i['st'], i['text']) for i in r2['items'] if i['st'] != 'pass']
    print('v1.0.6 preflight / tuning OK', r['counts_t'])
except Exception:
    import traceback; traceback.print_exc(); bad += 1
# ---- v1.0.8: derin teşhis, geri bildirim, öğrenen model
try:
    from app.core import diag2, feedback, mlmodel
    import json as _json
    _f = feedback._fs_fields({'a': 1, 'b': 1.5, 'c': 'x', 'd': [1, 'y'], 'e': {'k': None}, 'f': True})
    assert _f['a'] == {'integerValue': '1'} and _f['f'] == {'booleanValue': True} and 'arrayValue' in _f['d']
    assert feedback._url().endswith(feedback.COLLECTION + '?key=' + feedback.contact._FS.split('?key=')[1])
    assert mlmodel.adjust('normal', 0, None) == 'normal'
    print('v1.1.1 diag2 / feedback / mlmodel OK')
except Exception as _e:
    print('v1.0.8 FAIL', _e); raise

# ---- v1.1.4: dört seviyeli karar, kalibrasyon, geçmişle karşılaştırma, kanıta dayalı YZ, olay raporu
try:
    from app.core import baseline as BL, why as WY, texts as TX
    assert TX.vkey({'kind': 'incident', 'severity': 'minor'}) == 'incident_minor'
    assert TX.vkey({'kind': 'incident', 'severity': 'serious'}) == 'incident' and TX.vkey(None) == 'normal'
    c = WY.calibrate(0.9, 'motor'); assert 0.1 <= c <= 0.95, c
    assert '⚠' in WY._check_grounding('12:34 anında', {'t': '10:00'}) and '⚠' not in WY._check_grounding('10:00', {'t': '10:00'})
    An = analysis.Analysis(loader.load(os.path.join(d, 'normal.BIN')))
    assert any(k.startswith('bl_') for k in An.facts), 'baseline facts'
    assert An.verdict.get('kind') != 'crash' and An.fall is None, An.verdict
    BL.compare(An, None)
    print('v1.1.4 vkey / calibrate / grounding / baseline OK')
except Exception:
    import traceback; traceback.print_exc(); bad += 1

# ---- v1.1.5: modlar, kanal görevleri, motor isimleri, grafik seti, Mission Planner
try:
    from app.core import viz, charts as CH
    class _L: params = {'FRAME_CLASS': 1, 'FRAME_TYPE': 1}; modes = []; duration = 10; t0_us = 0
    class _A: vehicle = 'Copter'; L = _L()
    assert viz.motor_name(_A, 1, 'tr') == 'M1 · Ön sağ' and viz.motor_name(_A, 2, 'en') == 'M2 · Rear left', viz.motor_name(_A, 1, 'tr')
    assert viz.motor_name(_A, 3, 'tr').endswith('Ön sol') and viz.motor_name(_A, 4, 'tr').endswith('Arka sağ')
    _L.params = {'FRAME_CLASS': 2, 'FRAME_TYPE': 1}; assert viz.motor_name(_A, 1, 'tr').startswith('M1 · Sağ'), viz.motor_name(_A, 1, 'tr')
    assert viz.reason_text(26, 'tr').startswith('Açılış') and viz.reason_text(39, 'en').startswith('RTL complete')
    An = analysis.Analysis(loader.load(os.path.join(d, 'normal.BIN')))
    sg = viz.segments(An, 'tr'); assert sg and all(x['t1'] >= x['t0'] for x in sg)
    assert any(r['kind'] == 'ctrl' for r in viz.channel_roles(An, 'tr'))
    assert not [m for m in viz.motors(An) if m['kind'] == 'lift'], 'sabit kanatta kanatçık motor sanılmamalı'
    for lg in ('tr', 'ar'):
        for k, fn in list(CH.ALL) + [('c_timeline', CH.chart_timeline)]:
            fn(An, lg)
    xm = viz.mavgraphs_xml(An); assert '<graphs>' in xm and 'ATT.Roll' in xm
    print('v1.1.5 viz / charts OK', len(CH.ALL), 'grafik')
    # v1.1.7: her grafik/tablonun kaynağı (log alanı + parametre + Mission Planner yolu)
    from app.core import sources as SRC
    for lg in ('tr', 'en', 'ar'):
        for k in [k for k, _ in CH.ALL] + ['sec_modes', 'sec_phases', 'dom_gps', 'dom_power', 'c_map', 'c_health']:
            SRC.html(An, k, lg); SRC.footer(An, k, lg)
    r = SRC.rows(An, 'c_att', 'tr'); assert any(x['name'] == 'ATT.Roll' and x['meaning'] for x in r['fields'])
    assert 'Review a Log' in SRC.html(An, 'c_att', 'en') and 'ATT.Roll' in SRC.footer(An, 'c_att', 'tr')
    CH.want_fig(True)
    try:
        fg = dict(CH.ALL)['c_att'](An, 'tr'); assert any('ATT.Roll' in t.get_text() for t in fg.texts), 'grafik altı kaynak şeridi yok'
    finally:
        CH.want_fig(False)
    print('v1.1.7 sources OK')
    # v1.1.8: kendi grafiğim (formül/parametre eşiği) + video eşleme / OSD / birleştirme
    from app.core import customchart as CC, vidsync as VS
    import subprocess, tempfile as _tf
    assert len(CC.catalog(An.L)) > 20
    t_, y_ = CC.evaluate(An.L, 'ATT.Roll - ATT.DesRoll'); assert len(t_) == len(y_) > 10
    t_, y_ = CC.evaluate(An.L, 'smooth(abs(ATT.Pitch), 5) * 2'); assert (y_ >= 0).all()
    for bad_, code_ in (('', 'empty'), ('XXX.Y + 1', 'missing'), ('ATT.Roll +', 'syntax'), ('__import__("os")', '')):
        try: CC.evaluate(An.L, bad_); raise AssertionError('hata bekleniyordu: ' + bad_)
        except CC.ExprError as e_: assert str(e_).startswith(code_), (bad_, str(e_))
    pn_ = next(iter(An.L.params))
    png_, out_ = CC.build(An, {'series': [{'expr': 'GPS.Spd', 'panel': 1}], 'params': [{'name': pn_, 'panel': 1}]}, 'ar')
    assert png_[:4] == b'\x89PNG' and out_[0]['t'] is not None
    st_ = CC.stats(out_[0]['t'], out_[0]['y'], None, None, 1.0); assert st_['above'] + st_['below'] > 0
    vd_ = _tf.mkdtemp(); vf_ = os.path.join(vd_, 'cam.mp4')
    subprocess.run([VS.ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=10:duration=3',
                    '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast', vf_], check=True)
    vi_ = VS.probe(vf_); assert abs(vi_['dur'] - 3) < 0.3 and vi_['w'] == 320
    D_ = VS.OSDData(An, 'tr')
    for lg in ('tr', 'ar'):
        im_ = VS.osd_frame(VS.grab(vi_, 1.0, 320), VS.OSDData(An, lg).sample(60.0), VS.OSD_KEYS, lg, analysis.fmt_t)
        assert im_.size[0] == 320
    ov_ = os.path.join(vd_, 'out.mp4')
    VS.export(An, ov_, vi_, 50.0, second=vi_, off_second=50.0, layout='pip', panel=True, width=320)
    assert VS.probe(ov_)['dur'] > 2
    print('v1.1.8 custom chart / video OK')
except Exception:
    import traceback; traceback.print_exc(); bad += 1

sys.exit(1 if bad else 0)

