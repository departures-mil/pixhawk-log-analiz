"""v1.1.14 Log Gezgini: mesaj ağacı (örnekler, kanal görevleri, birimler), eşik çizgileri, sorunlu bölgeler, hazır görünümler,
uzman adımları, alıştırma ve sayfa (sol/sağ eksen, kırım anına git, veri tablosu)."""
import time
import numpy as np
import pytest
from PySide6.QtCore import Qt


@pytest.fixture(scope='module')
def stall(tmp_path_factory):
    from app.core import synth, loader, analysis
    p = str(tmp_path_factory.mktemp('lb') / 'stall.BIN'); synth.generate(p, 'stall', duration=300.0)
    return analysis.Analysis(loader.load(p, use_cache=False))


def test_tree_roles_units_instances(stall):
    from app.core import logbrowse as LB
    from app.core.loader import Series
    A = stall
    tr = {n['base']: n for n in LB.tree(A, 'tr')}
    assert {'ATT', 'RCOU', 'RCIN', 'VIBE', 'ARSP'} <= set(tr)
    rc = tr['RCOU']['insts'][0]['fields']
    assert rc[0]['key'] == 'RCOU.C1' and 'Kanatçık' in rc[0]['label'] and rc[0]['unit'] in ('µs', 'us')
    assert any('Gaz stick' in f['label'] for f in tr['RCIN']['insts'][0]['fields'])
    assert next(f for f in tr['ATT']['insts'][0]['fields'] if f['name'] == 'Roll')['unit'] == 'deg'
    # çok örnekli mesaj: IMU[0] / IMU[1] alt dalları
    L = A.L
    for k in (0, 1):
        s = Series(); s['t'] = np.arange(10.0); s['AccZ'] = np.full(10, -9.8); s['GyrX'] = np.zeros(10); L.msgs[f'IMU[{k}]'] = s
    L.msgs['IMU'] = L.msgs['IMU[0]']
    try:
        imu = next(n for n in LB.tree(A, 'en') if n['base'] == 'IMU')
        assert [i['key'] for i in imu['insts']] == ['IMU[0]', 'IMU[1]'] and 'sensor 2' in imu['insts'][1]['label']
        assert imu['insts'][1]['fields'][0]['key'].startswith('IMU[1].')
    finally:
        for k in ('IMU', 'IMU[0]', 'IMU[1]'): L.msgs.pop(k, None)


def test_info_limits_problems(stall):
    from app.core import logbrowse as LB
    A = stall
    P = A.L.params
    ll = LB.limit_lines(A, 'ARSP.Airspeed')
    if 'AIRSPEED_MIN' in P or 'ARSPD_FBW_MIN' in P:
        assert any(x[0].startswith(('AIRSPEED_MIN', 'ARSPD_FBW_MIN')) for x in ll)
    assert any(x[3] == 'ref' and x[1] == 30.0 for x in LB.limit_lines(A, 'VIBE.VibeZ'))
    assert len(LB.limit_lines(A, 'RCOU.C1')) >= 1 or 'SERVO1_MIN' not in P
    for lg in ('tr', 'en', 'ar'):
        d = LB.field_info(A, 'VIBE.VibeZ', lg)
        assert d['meaning'] and d['normal'] and d['unit']
        assert 'VIBE.VibeZ' in LB.tooltip(A, 'VIBE.VibeZ', lg)
    pr = LB.problems(A, 'tr')
    assert pr and any(p['kind'] == 'crash' for p in pr) and all(p['t0'] < p['t1'] for p in pr)
    ct = LB.crash_t(A); assert ct is not None and 0 < ct <= A.L.duration + 1
    assert LB.problem_at({'problems': pr}, (pr[-1]['t0'] + pr[-1]['t1']) / 2) is not None


def test_presets_steps_practice_build(stall):
    from app.core import logbrowse as LB, charts
    A = stall
    ids = [p['id'] for p in LB.presets(A)]
    assert {'stall', 'tecs', 'servo', 'vibe', 'overview'} <= set(ids) and 'transition' not in ids   # VTOL değil
    sel = LB.preset_sel(A, next(p for p in LB.PRESETS if p['id'] == 'servo'))
    assert any(s['side'] == 'R' and s['key'].startswith('RCOU.C') for s in sel)
    for p in LB.PRESETS:
        for lg in range(3): assert p['name'][lg] and p['look'][lg]
    st = LB.expert_steps(A, 'en')
    assert st[0]['zoom'] == 'all' and any(s['zoom'] == 'crash' for s in st) and any(s['preset'] == 'stall' for s in st)
    r = LB.check_guess(A, LB.truth(A), 'tr'); assert r['ok'] and '✅' in r['html']
    r = LB.check_guess(A, 'gps', 'ar'); assert not r['ok'] and r['html']
    charts.want_fig(True)
    try:
        fig, info = LB.build(A, sel, {'quiz': True}, 'tr'); assert fig is not None and info['problems'] == []
        fig, info = LB.build(A, sel, {}, 'ar'); assert info['problems'] and len(info['lines']) == len(sel)
    finally:
        charts.want_fig(False)
    hd, rows = LB.table(A, [s['key'] for s in sel], 10, 20)
    assert hd[:3] == ['t', 'clock', 'mode'] and rows and len(rows[0]) == len(hd)


def test_logbrowser_page(win, qapp, stall):
    A = stall
    pg = win.pages['logbrowser']; win.A = A; win.goto('logbrowser'); pg.on_analysis(A)

    def wait(c, n=300):
        for _ in range(n):
            qapp.processEvents(); time.sleep(0.02)
            if c(): return True
        return False
    assert wait(lambda: pg.view.canvas is not None and not pg._busy and not pg._reading)
    assert pg.tree.topLevelItemCount() >= 10 and pg.sel
    it = pg.items['ATT.Pitch']; pg.tree.setCurrentItem(it); pg._side_cur('R'); qapp.processEvents()
    assert {'key': 'ATT.Pitch', 'side': 'R'} in pg.sel and it.checkState(0) == Qt.Checked
    assert 'ATT.Pitch' in pg.info.toPlainText()
    pg.q.setText('kanatçık'); qapp.processEvents()
    rc = pg.items['RCOU.C1']; assert not rc.isHidden() and pg.items['ATT.Roll'].isHidden()
    pg.q.setText('')
    pg.goto_crash(); x0, x1 = pg.view.taxes[0].get_xlim(); assert x1 - x0 < 90
    pg.tabs.setCurrentIndex(1); assert wait(lambda: pg.table.rowCount() > 0, 50)
    pg.start_expert(); assert pg.xsteps.count() >= 3
    assert wait(lambda: not pg._busy and pg.view.canvas is not None)
    pg.c_prac.setChecked(True); assert pg._opts()['quiz']
    pg.check_guess(); assert pg._revealed and pg.gres.toPlainText()
    pg.c_prac.setChecked(False)
    pg.clear_graph(); assert pg.sel == []
    assert wait(lambda: not pg._busy)
