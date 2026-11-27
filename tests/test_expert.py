"""v1.1.12 uzman tecrübeleri: dersler (TR/EN/AR), gerçek konuların dersleri, pilot hatası nedeni, soru bankası, sayfa."""
import re
from app.core import expert as EX, texts, qbank as QB


def test_lessons_complete():
    assert len(EX.L) >= 30
    for k, v in EX.L.items():
        for f in ('title', 'rule', 'look', 'fix'):
            assert len(v[f]) == 3 and all(s.strip() for s in v[f]), (k, f)
            assert re.search('[؀-ۿ]', v[f][2]), (k, f)          # Arapça gerçekten Arapça
        assert v['cause'] in EX.CAUSE_ORDER
        assert v['chart'].startswith('c_')
    assert len(EX.golden('ar')) == len(EX.GOLDEN) >= 8


def test_case_tags():
    C = EX.cases(); assert C['n'] >= 300
    assert all(k in EX.L for k in C['stats'])
    for cid, x in C['cases'].items():
        assert all(k in EX.L for k in x['lessons']), cid
    assert 'pilot_stab' in EX.case_lessons('126622')['lessons']
    for c in EX.CAUSE_ORDER[:-1]:
        assert EX.for_cause(c), c
    h = EX.html_for('vibration', 'ar'); assert 'dir' not in h and 'VIBE' in h


def test_pilot_cause_texts():
    for lg in ('tr', 'en', 'ar'):
        for k in ('cause_pilot', 'why_pilot', 'prevent_pilot'):
            assert texts.T(k, lg)
    from app.core import why, lessons, practice, solver
    assert why.CAUSE_DOM['pilot'] and lessons.CAUSE_CHART['pilot'] and practice.CAUSE_CHART['pilot'] and solver.ROOT2CHECK['pilot']


def test_expert_questions():
    x = [q for q in QB.builtin() if q['topic'] == 'experts']
    assert len(x) == 3 * len(EX.L)
    assert all(QB.validate(q) is None for q in x)
    assert len({q['id'] for q in x}) == len(x)


def test_crashlib_page(win):
    win.goto('crashlib'); pg = win.pages['crashlib']
    assert pg.tabs.count() == 2 and pg.rows
    pg.tb.setCurrentCell(0, 0); assert pg.det.toPlainText().strip()
    pg.tabs.setCurrentIndex(1); assert pg.ls.count() == len(EX.L)
    pg.ls.setCurrentRow(0); assert pg.ld.toPlainText().strip()
    pg.show_examples(); assert pg.tabs.currentIndex() == 0 and pg.f_les.currentData() and pg.rows
    i = pg.f_cause.findData('pilot'); pg.f_cause.setCurrentIndex(i); assert pg.ls.count() >= 1
