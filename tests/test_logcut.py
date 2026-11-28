"""v1.1.18: log kesme (yalnız çalışılacak aralık) ve uçuş bilgileri formunun liste görünümü."""
import numpy as np
import pytest


@pytest.fixture(scope='module')
def two(tmp_path_factory):
    """İki ayrı kurulu dönemi olan log: sentetik uçuşu ikinci bir ARM/DISARM çifti ile çoğalt."""
    from app.core import synth, loader
    p = str(tmp_path_factory.mktemp('lc') / 'n.BIN'); synth.generate(p, 'normal', duration=300.0)
    L = loader.load(p, use_cache=False)
    return L


def test_crop_shifts_time_and_keeps_params(two):
    from app.core import logcut, analysis
    L = two
    C = logcut.crop(L, 100.0, 200.0)
    assert abs(C.duration - 100.0) < 1e-6
    for name, s in C.msgs.items():
        if len(s.get('t', [])):
            assert s['t'].min() >= -1e-9 and s['t'].max() <= 100.0 + 1e-9, name
    assert C.params is L.params
    assert C.t0_us == int(L.t0_us + 100e6)                   # Mission Planner TimeUS eşlemesi korunur
    if L.gps_time0:
        assert abs(C.unix_at(0.0) - L.unix_at(100.0)) < 1e-6   # saat korunur
    assert logcut.is_cut(C) and logcut.restore(C) is L and not logcut.is_cut(L)
    A = analysis.Analysis(C)
    assert A.verdict.get('kind')
    # kesilmiş logda aralık yeniden seçilirse asıl loga göre hesaplanır
    C2 = logcut.crop(C, 10.0, 50.0)
    assert abs(C2.cut['t0'] - 110.0) < 1e-6 and logcut.restore(C2) is L


def test_crop_mode_and_arm_at_start(two):
    from app.core import logcut
    L = two
    C = logcut.crop(L, 150.0, 250.0)
    if L.modes: assert C.modes and C.modes[0][0] == 0.0     # kesim başındaki aktif mod taşınır
    per = logcut._armed_periods(L)
    if any(a < 150 < b for a, b in per): assert C.arm and C.arm[0] == (0.0, True)


def test_records_and_range(two):
    from app.core import logcut
    rs = logcut.records(two)
    assert rs and all(r['t1'] > r['t0'] for r in rs)
    a, b = logcut.record_range(two, rs[0])
    assert 0 <= a < b <= two.duration


def test_flight_form_lists_all_options(win):
    from app.ui.flightform import FlightInfoDialog, OptionList
    d = FlightInfoDialog(win, {'gps': 'Here 3', 'autopilot': 'Benim kartım', 'crashed': 'no'}, {})
    kinds = {q: k for q, (k, w) in d.w.items()}
    assert kinds['gps'] == 'list' and kinds['autopilot'] == 'list' and kinds['airframe'] == 'list'
    v = d.values()
    assert v['gps'] == 'Here 3' and v['autopilot'] == 'Benim kartım' and v['crashed'] == 'no'
    ol = d.w['gps'][1]
    assert isinstance(ol, OptionList) and len(ol.grp.buttons()) >= 10      # bütün seçenekler aynı anda görünür
    b = ol.grp.buttons()[0]; b.click()
    assert d.values()['gps'] == b.property('val')
    b.click()                                                            # seçili seçeneğe yeniden tıklamak seçimi kaldırır
    assert 'gps' not in d.values()
    d.reject(); d.deleteLater()


def test_window_cut_and_restore(win, two, monkeypatch, qapp):
    import time
    from app.core import analysis, logcut
    from app.ui import logcut_dlg
    win.A = analysis.Analysis(two); win.uid = 'test-uid'
    for p in win.pages.values():
        try: p.on_analysis(win.A)
        except Exception: pass

    class Fake:
        def __init__(self, *a, **k):
            class R:
                def isChecked(self): return True
            self.rem = R(); self.result_range = Fake.rng
        def exec(self): return True
    monkeypatch.setattr(logcut_dlg, 'LogCutDialog', Fake)

    def wait(cond):
        t0 = time.time()
        while not cond() and time.time() - t0 < 60: qapp.processEvents(); time.sleep(0.05)
        assert cond()
    Fake.rng = (60.0, 160.0); win.cut_log()
    wait(lambda: logcut.is_cut(win.A.L))
    assert abs(win.A.L.duration - 100) < 1e-6 and win.settings['log_cuts']['test-uid'] == [60.0, 160.0]
    assert win.pages['analysis'].cutbar.isVisibleTo(win.pages['analysis'])
    win.restore_log()
    wait(lambda: not logcut.is_cut(win.A.L))
    assert 'test-uid' not in win.settings['log_cuts'] and not win.pages['analysis'].cutbar.isVisibleTo(win.pages['analysis'])
