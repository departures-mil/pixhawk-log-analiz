"""Gerçek pencere (offscreen): üst çubuk sırası, tam ekran, ayarlar sırası (iletişim EN SONDA), klasik şema, dil/RTL."""
from PySide6.QtCore import Qt


def test_starts_fullscreen(win):
    assert win.isFullScreen()
    win.toggle_half(); assert win.half and not win.isFullScreen()
    win.toggle_half(); assert win.isFullScreen()


def test_topbar_order(win):
    tb = win.topbar
    al = tb.al
    ws = [al.itemAt(i).widget() for i in range(al.count()) if al.itemAt(i).widget() is not None]
    quick = [win.q_open, win.q_info, win.q_solve, win.q_rep]
    assert ws[:4] == quick
    rest = ws[4:]
    assert rest[0] is tb.sync_btn and rest[1] is tb.lan_btn and rest[2] is tb.upd_btn and rest[3] is tb.theme_btn
    assert rest[4].property('fc') == 'lang-switch'
    wc = rest[-1]
    names = [b.property('fcWin') for b in wc.findChildren(type(tb.b_min))]
    assert names == ['minimize', 'half', 'fullscreen', 'close']


def test_settings_contact_last_and_core_cards(win):
    from PySide6.QtWidgets import QScrollArea, QFrame
    sa = win.pages['settings'].findChild(QScrollArea)
    lay = sa.widget().layout()
    ws = [lay.itemAt(i).widget() for i in range(lay.count()) if lay.itemAt(i).widget() is not None]
    keys = [w.property('fcCard') for w in ws if isinstance(w, QFrame) and w.property('fcCard')]
    assert keys[0] == 'look'
    for k in ('usage', 'crash', 'about'):
        assert k in keys, keys
    assert keys[-1] == 'contact' and ws[-1].property('fcCard') == 'contact'      # Admin ile iletişim EN SONDA


def test_klasik_scheme_is_old_look(win):
    from fccore import style
    assert 'klasik' in style.schemes() and style.schemes()[0] == 'falcon'
    assert style.scheme() == 'falcon'                       # varsayılan
    style.set_scheme('klasik')
    assert style.tok('bg').lower() == '#0f172a' and style.tok('sidebar-bg').lower() == '#0b1222'
    style.set_scheme('falcon')


def test_language_switch_rtl_and_rebuild(win, qapp):
    from fccore import i18n
    i18n.set('ar'); qapp.processEvents()
    assert qapp.layoutDirection() == Qt.RightToLeft
    assert win.settings['lang'] == 'ar' and 'التحليل' in win.nav_btns[0].text()
    i18n.set('en'); qapp.processEvents()
    assert qapp.layoutDirection() == Qt.LeftToRight and 'Analysis' in win.nav_btns[0].text()
    i18n.set('tr'); qapp.processEvents()
    assert 'Analiz' in win.nav_btns[0].text()


def test_light_theme_recolors_old_html(win, qapp):
    from fccore import style
    from app.ui import kabuk
    style.set_theme('light')
    assert '#0F172A' in kabuk.themed_html('<span style="color:#F8FAFC">x</span>')
    style.set_theme('dark')
    assert kabuk.themed_html('<span style="color:#F8FAFC">x</span>').count('#F8FAFC') == 1


def test_usage_counts_ai_calls(win):
    from fccore import usage
    before = usage.data()['c'].get('ai.gemini', 0)
    win.usage.add_generic('gemini', 10, 5, {})
    win.usage.add_generic('free', 1, 1, {})
    assert usage.data()['c']['ai.gemini'] == before + 1 and usage.data()['c'].get('ai.pollinations', 0) >= 1


def test_crash_report_has_trail(win, monkeypatch):
    from app.core import crash
    sent = []
    import fccore.contact as C
    monkeypatch.setattr(C, 'post_async', lambda o, use_mail=False, done=None: sent.append(o))
    crash.note('open uçuş_42.BIN')
    crash.send_core('[ui] ValueError: x  key AIzaSyABCDEFGHIJKLMNOP')
    assert sent and sent[0]['tur'] == 'cokme' and 'Son işlemler' in sent[0]['mesaj'] and 'AIza***' in sent[0]['mesaj']


def test_onboarding_offers_only_supported_ai(win):
    from fccore import onboarding
    assert set(onboarding.AI) == {'gemini', 'anthropic'}
    from app.ui import kabuk
    kabuk._on_ai(win.settings, {'provider': 'gemini', 'key': 'AIzaTEST123456789'})
    assert win.settings['gemini_key'] == 'AIzaTEST123456789' and win.settings['ai_provider'] == 'gemini'


def test_interactive_charts_modes_mp(win, qapp, tmp_path):
    """v1.1.5: grafikler etkileşimli tuvalde (Figure), mod tablosu dolu, Mission Planner sekmesi alanları gösteriyor."""
    import time
    from app.core import synth, loader, analysis
    p = str(tmp_path / 'n.BIN'); synth.generate(p, 'normal', duration=300.0)
    A = analysis.Analysis(loader.load(p)); win.A = A
    pg = win.pages['charts']; pg.on_analysis(A)
    pg.show_key('c_motors')
    for _ in range(200):
        qapp.processEvents(); time.sleep(0.02)
        if pg.view.canvas is not None or pg.view.msg.isVisible() and 'yok' in pg.view.msg.text(): break
    pg.show_key('c_alt')
    for _ in range(200):
        qapp.processEvents(); time.sleep(0.02)
        if pg.view.canvas is not None and pg.view.fig is not None: break
    assert pg.view.canvas is not None and pg.view.taxes
    assert pg.mt.rowCount() >= 1
    assert 'GPS.Alt' in pg.mp.toPlainText() or 'ATT' in pg.mp.toPlainText()
    pg.view.set_cursor(50.0); pg._mode_dbl(0, 0)
    assert win.pages['map'].mcol.count() == 2
    # v1.1.7: kaynak sekmesi log alanını ve Mission Planner yolunu gösterir; grafiğin altında kaynak şeridi var
    src = pg.src.toPlainText()
    assert 'GPS.Alt' in src and 'Review a Log' in src
    assert any('GPS.Alt' in t_.get_text() for t_ in pg.view.fig.texts)
    assert 'MODE.Mode' in pg.mt_src.text()


def _lavfi(path, dur=4, created=None):
    import subprocess
    from app.core.vidsync import ffmpeg_exe
    args = [ffmpeg_exe(), '-y', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', f'testsrc=size=320x240:rate=10:duration={dur}',
            '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast']
    if created: args += ['-metadata', f'creation_time={created}']
    subprocess.run(args + [path], check=True)


def test_custom_chart_and_video_pages(win, qapp, tmp_path):
    """v1.1.8: Kendi Grafiğim (alan + formül + parametre eşiği, kayıt) ve Video ve OSD (eşleme, grafikten videoya gitme)."""
    import time
    from app.core import synth, loader, analysis, vidsync as V
    p = str(tmp_path / 'n.BIN'); synth.generate(p, 'normal', duration=300.0)
    A = analysis.Analysis(loader.load(p)); win.A = A
    cc = win.pages['custom']; cc.on_analysis(A)
    assert cc.fl.count() > 20 and cc.pl.count() > 0
    cc.set_spec({'series': [{'expr': 'ATT.Roll - ATT.DesRoll', 'panel': 1}, {'expr': 'GPS.Spd', 'panel': 2}],
                 'params': [{'name': cc.pl.item(0).data(256), 'panel': 2}]})
    cc.draw()
    for _ in range(300):
        qapp.processEvents(); time.sleep(0.02)
        if cc.view.canvas is not None and cc.st.rowCount(): break
    assert cc.view.taxes and cc.st.rowCount() == 2
    cc.name.setText('pytest'); cc._save()
    assert any(x['title'] == 'pytest' for x in win.settings['custom_charts'])
    vp = win.pages['video']; vp.on_analysis(A)
    vp.goto_log_time(10.0)  # video yokken sessiz geçer
    f = str(tmp_path / 'v.mp4'); _lavfi(f)
    vp.vids[0] = V.probe(f); vp.which.setCurrentIndex(0); vp._which(); vp._labels()
    vp.offsp.setValue(100.0)
    win.pages['charts']._clicked(102.0)
    for _ in range(100):
        qapp.processEvents(); time.sleep(0.02)
        if vp.frame is not None: break
    assert vp.frame is not None and abs(vp.vt - 2.0) < 0.3, vp.vt
    assert abs(vp.log_t() - 102.0) < 0.3
    vp.stop()


def test_msglib_search_descriptions_all_languages(win, qapp):
    """v1.1.9: log mesajları aramasında açıklamalar ve üç dildeki çeviriler de aranır (aksan duyarsız, eş anlamlılarla)."""
    import json
    from app.core import msgsearch as MS
    from app.core.paths import res
    I = MS.Index(json.load(open(res('data', 'logmsgs.json'), encoding='utf-8')))
    for q in ('titreşim', 'titresim', 'vibration', 'اهتزاز', 'VIBE.VibeX'):
        assert I.search(q) and I.search(q)[0][0] == 'VIBE', q
    r = dict(I.search('batarya gerilim'))
    assert 'BAT' in r and 'Volt' in r['BAT']['fields']
    assert I.search('gps hdop')[0][1]['fields'][0].lower() == 'hdop'
    assert not I.search('xyzzq')
    assert '<span' in MS.highlight('Titreşim seviyesi', 'titresim', str)
    pg = win.pages['msgs']; pg.q.setText('titreşim'); qapp.processEvents()
    ks = [pg.list.item(i).data(256) for i in range(pg.list.count())]
    assert ks[0] == 'VIBE' and 'VibeX' in pg.list.item(0).text()
    assert '<span' in pg.view.toHtml() or 'FDE047' in pg.view.toHtml()
    pg.q.setText('')
