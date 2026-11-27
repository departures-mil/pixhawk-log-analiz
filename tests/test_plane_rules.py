"""v1.1.16 Plane teşhis kuralları: hava hızı kaynağı seçimi, crash_dump mesajı, uzun/sakin uçuş derecesi, VTOL motor doygunluğu."""
import numpy as np
import pytest


@pytest.fixture(scope='module')
def plane(tmp_path_factory):
    from app.core import synth, loader, analysis
    p = str(tmp_path_factory.mktemp('pr') / 'normal.BIN'); synth.generate(p, 'normal', duration=600.0)
    return analysis, loader.load(p, use_cache=False)


def test_airspeed_source_skips_dead_sensor(plane):
    analysis, L = plane
    A = analysis.Analysis(L)
    s, f = A.airspeed_src()
    assert f == 'Airspeed'                      # gerçek sensör verisi varsa o kullanılır
    ar = L.s('ARSP')
    saved = ar['Airspeed'].copy()
    try:
        ar['Airspeed'][:] = 0.0               # sensör takılı değil / kullanılmıyor: hep 0 okur
        B = analysis.Analysis(L)
        s2, f2 = B.airspeed_src()
        assert f2 != 'Airspeed'                 # kontrolcünün tahmini (CTUN/TECS) ya da hiç
        if f2 is None:
            assert B.health.get('airspeed') is None or 'as_low' not in {x['k'] for x in B.health['airspeed'].get('findings', [])}
    finally:
        ar['Airspeed'][:] = saved


def test_crash_dump_is_not_a_crash(plane):
    analysis, L = plane
    L.texts.insert(0, (1.0, 'Logging @SYS/crash_dump.bin'))
    try:
        A = analysis.Analysis(L)
        assert 'cr_msg' not in {e['k'] for e in A.verdict.get('evidence', [])}
    finally:
        L.texts.pop(0)


def test_normal_plane_flight_not_serious(plane):
    analysis, L = plane
    A = analysis.Analysis(L)
    v = A.verdict
    assert not (v.get('kind') == 'incident' and v.get('severity') == 'serious' and not
                ({e['k'] for e in v.get('evidence', [])} - {'cr_landed'}))
