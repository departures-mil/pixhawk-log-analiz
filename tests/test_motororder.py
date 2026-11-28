"""v1.1.19 Motor Yönleri Bankası: ArduPilot motor tanımlarından üretilen veri ve resimler."""
import os


def test_bank_complete_and_images_exist():
    from app.core import motororder as MO
    B = MO.bank()['frames']
    assert len(B) >= 55
    for f in B:
        assert os.path.exists(MO.image(f['id'])), f['id']
        for lg in ('tr', 'en', 'ar'):
            assert MO.title(f, lg)
            assert MO.rows(f, lg)
    ids = {f['id'] for f in B}
    for need in ('qp_quad_x', 'qp_quad_plus', 'qp_octaquad_x', 'qp_y6_y6b', 'qp_tri', 'qp_tailsitter', 'mc_quad_x', 'mc_hexa_x',
                 'mc_octa_x', 'mc_y6_y6b', 'mc_deca_x', 'mc_dodecahexa_x', 'mc_tri', 'pl_single', 'pl_twin', 'rv_skid'):
        assert need in ids, need


def test_quad_x_matches_ardupilot():
    """ArduPilot belgeleri: Quad X → 1 ön sağ CCW, 2 arka sol CCW, 3 ön sol CW, 4 arka sağ CW; test sırası 1=A, 4=B, 2=C, 3=D."""
    from app.core import motororder as MO
    f = next(x for x in MO.bank()['frames'] if x['id'] == 'mc_quad_x')
    m = {z['n']: z for z in f['motors']}
    assert m[1]['x'] > 0 and m[1]['y'] > 0 and m[1]['yaw'] == 1 and MO.letter(m[1]['order']) == 'A'
    assert m[2]['x'] < 0 and m[2]['y'] < 0 and m[2]['yaw'] == 1 and MO.letter(m[2]['order']) == 'C'
    assert m[3]['x'] < 0 and m[3]['y'] > 0 and m[3]['yaw'] == -1 and MO.letter(m[3]['order']) == 'D'
    assert m[4]['x'] > 0 and m[4]['y'] < 0 and m[4]['yaw'] == -1 and MO.letter(m[4]['order']) == 'B'
    x8 = next(x for x in MO.bank()['frames'] if x['id'] == 'mc_octaquad_x')
    lv = {z['n']: z.get('level') for z in x8['motors']}
    assert all(lv[i] == 'top' for i in (1, 2, 3, 4)) and all(lv[i] == 'bottom' for i in (5, 6, 7, 8))


def test_find_for_params():
    from app.core import motororder as MO
    assert MO.find_for_params({'Q_ENABLE': 1, 'Q_FRAME_CLASS': 1, 'Q_FRAME_TYPE': 1}, 'Plane')['id'] == 'qp_quad_x'
    assert MO.find_for_params({'Q_ENABLE': 1, 'Q_FRAME_CLASS': 10}, 'Plane')['id'] == 'qp_tailsitter'
    assert MO.find_for_params({'FRAME_CLASS': 2, 'FRAME_TYPE': 1}, 'Copter')['id'] == 'mc_hexa_x'
    assert MO.find_for_params({'SERVO3_FUNCTION': 70}, 'Plane')['id'] == 'pl_single'


def test_page_lists_frames(win, qapp):
    pg = win.pages['motors']
    pg.grp.setCurrentIndex(0); qapp.processEvents()
    from app.core import motororder as MO
    assert pg.gal.count() == len(MO.bank()['frames'])
    pg.q.setText('tailsitter'); qapp.processEvents()
    assert pg.gal.count() >= 1 and 'Tailsitter' in pg.d_title.text()
    pg.q.clear(); pg.grp.setCurrentIndex(1)
