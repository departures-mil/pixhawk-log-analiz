"""Ayarlar sayfası: dil, yapay zekâ + limitler, antet şablonları, harita, eşitleme, güncelleme, arşiv, admin iletişim (en sonda)."""
from __future__ import annotations
import os, time
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QComboBox, QLineEdit, QCheckBox,
                               QScrollArea, QSpinBox, QFileDialog, QPlainTextEdit, QInputDialog, QColorDialog)
from .i18n import t, lang
from .common import label, button, run_bg, error, info, open_path
from .pages_a import Page
from ..core.paths import data_dir
from ..version import VERSION


class SettingsPage(Page):
    def __init__(self, win):
        super().__init__(win)
        s = win.settings
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); outer.addWidget(sc)
        body = QWidget(); body.setObjectName('page'); body.setAttribute(Qt.WA_StyledBackground, True); sc.setWidget(body)
        v = QVBoxLayout(body); v.setContentsMargins(24, 16, 24, 24); v.setSpacing(10)

        # Genel
        g = QGroupBox(t('s_general')); f = QFormLayout(g)
        self.lang = QComboBox()
        for code, name in (('tr', 'Türkçe'), ('en', 'English'), ('ar', 'العربية')): self.lang.addItem(name, code)
        self.lang.setCurrentIndex(self.lang.findData(s['lang'])); self.lang.currentIndexChanged.connect(self._lang)
        f.addRow(t('s_lang'), self.lang)
        self.online = QCheckBox(t('s_online')); self.online.setChecked(s.get('online', True))
        self.online.toggled.connect(lambda x: self._set('online', x)); f.addRow(self.online)
        v.addWidget(g)

        # Yapay zekâ (Gemini ücretsiz / Claude) — kolay kurulum
        g = QGroupBox(t('s_ai')); f = QFormLayout(g)
        f.addRow(label(t('ai_intro'), 'muted', wrap=True))
        self.prov = QComboBox(); self.prov.addItem(t('ai_gemini'), 'gemini'); self.prov.addItem(t('ai_claude'), 'anthropic')
        self.prov.setCurrentIndex(max(0, self.prov.findData(s.get('ai_provider') or 'gemini')))
        self.prov.currentIndexChanged.connect(self._prov_changed); f.addRow(t('s_provider'), self.prov)
        kh = QHBoxLayout()
        self.key = QLineEdit(); self.key.setEchoMode(QLineEdit.Password)
        self.key.editingFinished.connect(self._key_edited); kh.addWidget(self.key, 1)
        kh.addWidget(button('👁', lambda: self.key.setEchoMode(QLineEdit.Normal if self.key.echoMode() == QLineEdit.Password else QLineEdit.Password)))
        kh.addWidget(button(t('ai_paste'), self._paste))
        kh.addWidget(button(t('ai_wizard'), self.key_wizard, primary=True))
        kh.addWidget(button(t('s_test'), self.test_key))
        f.addRow(t('s_key'), kh)
        self.ai_st = label('', 'muted', wrap=True); f.addRow(self.ai_st)
        mh = QHBoxLayout()
        self.model = QComboBox(); self.model.setEditable(True); self.model.setMinimumWidth(280)
        self.model.currentTextChanged.connect(self._model_changed); mh.addWidget(self.model, 1)
        mh.addWidget(button(t('ai_refresh'), self.test_key)); f.addRow(t('s_model'), mh)
        self.effort = QComboBox(); self.effort.addItems(['low', 'medium', 'high', 'max']); self.effort.setCurrentText(s.get('effort', 'medium'))
        self.effort.currentTextChanged.connect(lambda x: self._set('effort', x)); f.addRow(t('s_effort'), self.effort)
        f.addRow(label(t('s_usage'), 'h2'))
        self.usage = label('', wrap=True, sel=True); f.addRow(self.usage)
        v.addWidget(g)
        self._prov_changed(init=True)

        # Analiz: profil, önbellek, hava durumu, anomali modeli
        g = QGroupBox(t('s_analysis')); f = QFormLayout(g)
        from ..core import profiles as PRF
        self.prof = QComboBox(); self.prof.addItem(t('s_profile_auto'), 'auto')
        for p in ('plane', 'vtol', 'copter', 'heli', 'rover'): self.prof.addItem(PRF.name(p, lang()), p)
        self.prof.setCurrentIndex(max(0, self.prof.findData(s.get('profile', 'auto'))))
        self.prof.currentIndexChanged.connect(lambda _: (self._set('profile', self.prof.currentData()), self.win._apply_core_settings()))
        f.addRow(t('s_profile'), self.prof); f.addRow(label(t('s_profile_help'), 'muted', wrap=True))
        ch2 = QHBoxLayout(); self.cmb = QSpinBox(); self.cmb.setRange(100, 50000); self.cmb.setSingleStep(500); self.cmb.setValue(int(s.get('cache_max_mb', 3000)))
        self.cmb.valueChanged.connect(lambda x: (self._set('cache_max_mb', x), self.win._apply_core_settings())); ch2.addWidget(self.cmb)
        self.cache_now = label('', 'muted'); ch2.addWidget(self.cache_now, 1); ch2.addWidget(button(t('s_cache_clear'), self._clear_cache))
        f.addRow(t('s_cache_mb'), ch2)
        self.wx = QCheckBox(t('s_weather')); self.wx.setChecked(s.get('weather_online', True)); self.wx.toggled.connect(lambda x: self._set('weather_online', x)); f.addRow(self.wx)
        ah2 = QHBoxLayout(); self.anom_l = label('', 'muted'); ah2.addWidget(self.anom_l, 1); ah2.addWidget(button(t('s_anom_reset'), self._anom_reset)); f.addRow(ah2)
        v.addWidget(g)

        # Rapor & antet
        g = QGroupBox(t('s_report')); f = QFormLayout(g)
        th = QHBoxLayout()
        self.tpl = QComboBox(); self.tpl.currentIndexChanged.connect(self._load_tpl); th.addWidget(self.tpl, 1)
        th.addWidget(button(t('s_new_tpl'), self.new_tpl)); th.addWidget(button(t('s_del_tpl'), self.del_tpl))
        f.addRow(t('s_tpl_name'), th)
        self.fields = {}
        for k, lab in (('org', 's_org'), ('sub', 's_sub'), ('prepared_by', 's_prep'), ('watermark', 's_wm'), ('footer', 's_footer')):
            e = QLineEdit(); e.editingFinished.connect(self._save_tpl); self.fields[k] = e; f.addRow(t(lab), e)
        hh = QHBoxLayout(); e = QLineEdit(); e.editingFinished.connect(self._save_tpl); self.fields['logo'] = e; hh.addWidget(e, 1)
        hh.addWidget(button(t('s_browse'), lambda _=False, e=e: self._browse(e))); f.addRow(t('s_logo'), hh)
        ch = QHBoxLayout(); self.color = QLineEdit(); self.color.editingFinished.connect(self._save_tpl); self.fields['color'] = self.color
        ch.addWidget(self.color, 1); ch.addWidget(button('🎨', self._pick_color)); f.addRow(t('s_color'), ch)
        v.addWidget(g)

        # Antet ekle (DOCX/PDF arka planı)
        g = QGroupBox(t('s_lh')); f = QFormLayout(g)
        f.addRow(label(t('s_lh_help'), 'muted', wrap=True))
        bh = QHBoxLayout(); self.bg = QLineEdit(); self.bg.setReadOnly(True); self.fields['bg'] = self.bg; bh.addWidget(self.bg, 1)
        bh.addWidget(button(t('s_lh_load'), self.load_lh, primary=True)); bh.addWidget(button(t('s_lh_clear'), self.clear_lh))
        f.addRow(t('s_bg'), bh)
        f.addRow(button('⭐ ' + t('s_lh_preset'), self.use_preset))
        self.besmele = QCheckBox(t('s_besmele')); self.besmele.toggled.connect(lambda x: self._set_tpl('besmele', bool(x))); f.addRow(self.besmele)
        from PySide6.QtWidgets import QDoubleSpinBox
        self.top = QDoubleSpinBox(); self.top.setRange(0, 12); self.top.setSingleStep(0.1); self.top.setDecimals(1)
        self.top.valueChanged.connect(lambda x: self._set_tpl('top_cm', round(float(x), 1))); f.addRow(t('s_top'), self.top)
        self.lh_info = label('', 'muted', wrap=True); f.addRow(self.lh_info)
        ph = QHBoxLayout(); ph.addWidget(button(t('s_lh_preview'), self.preview_lh, primary=True)); ph.addWidget(button(t('s_lh_pdf'), self.sample_pdf)); ph.addStretch(1)
        f.addRow(ph)
        v.addWidget(g)

        # Harita
        g = QGroupBox(t('s_maps')); f = QFormLayout(g)
        self.cache_l = label(''); f.addRow(self.cache_l)
        v.addWidget(g)

        # Eşitleme
        g = QGroupBox(t('s_sync')); f = QFormLayout(g)
        f.addRow(label(t('s_gh'), 'h2'))
        f.addRow(label(t('s_gh_help'), 'muted', wrap=True))
        gh = QHBoxLayout()
        self.tok = QLineEdit(s.get('gh_token', '')); self.tok.setEchoMode(QLineEdit.Password); self.tok.setPlaceholderText('ghp_… / github_pat_…')
        self.tok.editingFinished.connect(lambda: self._set('gh_token', self.tok.text().strip())); gh.addWidget(self.tok, 1)
        from ..core.sync import TOKEN_URL
        gh.addWidget(button(t('s_get_token'), lambda: QDesktopServices.openUrl(QUrl(TOKEN_URL))))
        self.b_gh = button('⇅ ' + t('s_sync_now'), self.gh_sync, primary=True); gh.addWidget(self.b_gh)
        f.addRow(t('s_token'), gh)
        self.sync_l = label('', 'muted', wrap=True); f.addRow(self.sync_l)
        f.addRow(label(t('s_lan'), 'h2'))
        f.addRow(label(t('s_lan_help'), 'muted', wrap=True))
        lh = QHBoxLayout()
        self.code = QLineEdit(s.get('lan_code', '')); self.code.editingFinished.connect(lambda: self._set('lan_code', self.code.text().strip()))
        lh.addWidget(self.code, 1)
        self.b_lan = button('📶 ' + t('s_lan_find'), self.lan_sync); lh.addWidget(self.b_lan)
        f.addRow(t('s_lan_code'), lh)
        self.lan_l = label('', 'muted', wrap=True); f.addRow(self.lan_l)
        v.addWidget(g)

        # Arşiv
        g = QGroupBox(t('s_archive')); f = QFormLayout(g)
        ah = QHBoxLayout()
        self.copy = QCheckBox(); self.copy.setChecked(s.get('archive_copy_logs', True)); self.copy.toggled.connect(lambda x: self._set('archive_copy_logs', x))
        self.mb = QSpinBox(); self.mb.setRange(10, 5000); self.mb.setValue(int(s.get('archive_copy_max_mb', 200)))
        self.mb.valueChanged.connect(lambda x: self._set('archive_copy_max_mb', x))
        ah.addWidget(self.copy); ah.addWidget(self.mb); ah.addStretch(1)
        f.addRow(t('s_copy_logs'), ah)
        f.addRow(button('📂 ' + t('s_open_data'), lambda: open_path(data_dir())))
        v.addWidget(g)

        # Güncelleme
        g = QGroupBox(t('s_update')); f = QFormLayout(g)
        f.addRow(label(t('s_version', v=VERSION), 'h2'))
        self.auto = QCheckBox(t('s_auto_upd')); self.auto.setChecked(s.get('auto_update_check', True))
        self.auto.toggled.connect(lambda x: self._set('auto_update_check', x)); f.addRow(self.auto)
        f.addRow(button('⬇ ' + t('s_check_upd'), win.do_update, primary=True))
        v.addWidget(g)

        # Rapor şablon düzenleyici (bölümler, kısa/uzun)
        g = QGroupBox(t('s_rep_tpl')); f = QFormLayout(g)
        f.addRow(label(t('s_rep_tpl_help'), 'muted', wrap=True))
        self.rmode = QComboBox(); self.rmode.addItem(t('rep_long'), 'long'); self.rmode.addItem(t('rep_short'), 'short')
        self.rmode.setCurrentIndex(max(0, self.rmode.findData(s.get('report_mode', 'long'))))
        self.rmode.currentIndexChanged.connect(lambda _: self._set('report_mode', self.rmode.currentData())); f.addRow(t('s_rep_mode'), self.rmode)
        from PySide6.QtWidgets import QListWidget, QAbstractItemView
        self.secs = QListWidget(); self.secs.setDragDropMode(QAbstractItemView.InternalMove); self.secs.setMinimumHeight(250)
        self.secs.itemChanged.connect(lambda *_: self._save_secs()); self.secs.model().rowsMoved.connect(lambda *_: self._save_secs())
        f.addRow(self.secs); f.addRow(button(t('s_rep_reset'), self._reset_secs))
        v.addWidget(g)
        self._fill_secs()

        # Mission Planner entegrasyonu
        g = QGroupBox(t('s_mp')); f = QFormLayout(g)
        f.addRow(label(t('s_mp_help'), 'muted', wrap=True))
        self.watch = QCheckBox(t('s_watch')); self.watch.setChecked(bool(s.get('watch_enabled'))); self.watch.toggled.connect(lambda x: (self._set('watch_enabled', x), self.win.setup_watch(), self._dirs()))
        f.addRow(self.watch)
        self.autoan = QCheckBox(t('s_auto_an')); self.autoan.setChecked(bool(s.get('auto_analyze'))); self.autoan.toggled.connect(lambda x: self._set('auto_analyze', x)); f.addRow(self.autoan)
        from PySide6.QtWidgets import QListWidget as _LW
        self.dirs = _LW(); self.dirs.setMaximumHeight(110); f.addRow(t('s_dirs'), self.dirs)
        dh = QHBoxLayout(); dh.addWidget(button(t('s_add_dir'), self._add_dir)); dh.addWidget(button(t('s_rm_dir'), self._rm_dir)); dh.addStretch(1); f.addRow(dh)
        ash = QHBoxLayout(); ash.addWidget(button('🔗 ' + t('s_assoc'), self._assoc, primary=True)); self.assoc_l = label('', 'muted'); ash.addWidget(self.assoc_l, 1); f.addRow(ash)
        v.addWidget(g)
        self._dirs()

        # Güvenlik ve kullanıcılar
        g = QGroupBox(t('s_sec')); f = QFormLayout(g)
        f.addRow(label(t('s_sec_help'), 'muted', wrap=True))
        self.ulist = _LW(); self.ulist.setMaximumHeight(120); f.addRow(t('s_users'), self.ulist)
        uh = QHBoxLayout(); uh.addWidget(button('➕ ' + t('s_add_user'), self._add_user)); uh.addWidget(button('🗑 ' + t('s_del_user'), self._del_user)); uh.addStretch(1); f.addRow(uh)
        self.reql = QCheckBox(t('s_req_login')); self.reql.setChecked(bool(s.get('require_login'))); self.reql.toggled.connect(self._req_login); f.addRow(self.reql)
        self.encl = QCheckBox(t('s_enc_local')); self.encl.setChecked(bool(s.get('encrypt_local'))); self.encl.toggled.connect(lambda x: self._set('encrypt_local', x)); f.addRow(self.encl)
        eh = QHBoxLayout(); eh.addWidget(button('🔒 ' + t('s_enc_file'), self._enc_file)); eh.addWidget(button('🔓 ' + t('s_dec_file'), self._dec_file)); eh.addStretch(1); f.addRow(eh)
        v.addWidget(g)
        self._users()

        # Hata raporları
        g = QGroupBox(t('s_crash')); f = QFormLayout(g)
        crh = QHBoxLayout(); self.crash_l = label('', 'muted'); crh.addWidget(self.crash_l, 1)
        self.b_crash = button('✉ ' + t('cr_send'), self._send_crash); crh.addWidget(self.b_crash); f.addRow(crh)
        v.addWidget(g)

        # Admin ile iletişim (en sonda)
        g = QGroupBox(t('s_contact')); f = QFormLayout(g)
        f.addRow(label(t('s_contact_desc'), 'muted', wrap=True))
        self.c_name = QLineEdit(); f.addRow(t('c_name'), self.c_name)
        self.c_mail = QLineEdit(); f.addRow(t('c_mail'), self.c_mail)
        self.c_msg = QPlainTextEdit(); self.c_msg.setMinimumHeight(110); f.addRow(t('c_msg'), self.c_msg)
        ch = QHBoxLayout(); self.b_send = button(t('c_send'), self.contact, primary=True); ch.addWidget(self.b_send)
        self.c_st = label('', 'muted'); ch.addWidget(self.c_st, 1); f.addRow(ch)
        v.addWidget(g)
        v.addStretch(1)
        self._fill_tpls()

    def on_show(self):
        self._usage(); self._cache(); self._sync_info(); self._an_info(); self._crash_info(); self._dirs(); self._users()
        if not self.key.text().strip(): self._paste(silent=True)

    def _set(self, k, val):
        self.win.settings[k] = val; self.win.settings.save()

    def _lang(self):
        self._set('lang', self.lang.currentData()); self.win.apply_lang()

    # ---- AI
    def _pkey(self, prov=None):
        prov = prov or self.prov.currentData()
        return 'gemini_key' if prov == 'gemini' else 'api_key'

    def _mkey(self, prov=None):
        prov = prov or self.prov.currentData()
        return 'gemini_model' if prov == 'gemini' else 'model'

    def _prov_changed(self, *_, init=False):
        from ..core import ai as AI
        s = self.win.settings; prov = self.prov.currentData()
        if not init: self._set('ai_provider', prov)
        self.key.blockSignals(True); self.key.setText(s.get(self._pkey(), '') or '')
        self.key.setPlaceholderText('AIza… / AQ.…' if prov == 'gemini' else 'sk-ant-…'); self.key.blockSignals(False)
        self._fill_models()
        self.ai_st.setText(t('ai_none') if not self.key.text().strip() else '')
        self._usage()

    def _fill_models(self, models=None):
        from ..core import ai as AI
        s = self.win.settings; prov = self.prov.currentData()
        lk = 'gemini_models' if prov == 'gemini' else 'claude_models'
        if models is not None: s[lk] = models; s.save()
        ms = s.get(lk) or []
        ms = AI.candidates(prov, ms) if ms else list(AI.PROVIDERS[prov]['fallback'])
        cur = s.get(self._mkey()) or AI.PROVIDERS[prov]['default']
        self.model.blockSignals(True); self.model.clear(); self.model.addItems(ms)
        self.model.setCurrentText(cur); self.model.blockSignals(False)

    def _model_changed(self, x):
        if x.strip(): self._set(self._mkey(), x.strip())

    def _key_edited(self):
        from ..core import ai as AI
        k = self.key.text().strip()
        p = AI.detect_provider(k)
        if p and p != self.prov.currentData():
            self.prov.setCurrentIndex(self.prov.findData(p))   # anahtara göre sağlayıcıyı otomatik seç
        if k != (self.win.settings.get(self._pkey()) or ''):
            self._set(self._pkey(), k)
            if k: self.test_key()

    def _paste(self, *_, silent=False):
        from PySide6.QtWidgets import QApplication
        from ..core import ai as AI
        try: txt = QApplication.clipboard().text()
        except Exception: txt = ''
        p, k = AI.find_key(txt)
        if not k:
            if not silent and txt.strip(): self.key.setText(txt.strip()); self._key_edited()
            return False
        if k == (self.win.settings.get(self._pkey(p)) or ''): return False
        self.prov.setCurrentIndex(self.prov.findData(p))
        self.key.setText(k); self._set(self._pkey(p), k)
        self.ai_st.setText(t('ai_clip_found', p=AI.PROVIDERS[p]['name']))
        self.test_key()
        return True

    def key_wizard(self):
        from PySide6.QtWidgets import QDialog, QApplication
        from PySide6.QtCore import QTimer
        from ..core import ai as AI
        prov = self.prov.currentData(); url = AI.PROVIDERS[prov]['key_url']
        dl = QDialog(self); dl.setWindowTitle(t('ai_wiz_title')); dl.setMinimumWidth(520); lay = QVBoxLayout(dl)
        lay.addWidget(label(t('ai_wiz_steps') if prov == 'gemini' else t('ai_wiz_steps_c'), wrap=True))
        st = label('⏳ ' + t('ai_wiz_wait'), 'h2'); lay.addWidget(st)
        bh = QHBoxLayout(); bh.addWidget(button(t('ai_open_page'), lambda: QDesktopServices.openUrl(QUrl(url)))); bh.addStretch(1)
        bh.addWidget(button(t('cancel'), dl.reject)); lay.addLayout(bh)
        try: start = QApplication.clipboard().text()
        except Exception: start = ''
        tm = QTimer(dl); tm.setInterval(700)

        def poll():
            try: txt = QApplication.clipboard().text()
            except Exception: return
            if txt == start: return
            p, k = AI.find_key(txt)
            if k:
                tm.stop(); st.setText('✔ ' + t('ai_wiz_got')); QTimer.singleShot(500, dl.accept)
                self.prov.setCurrentIndex(self.prov.findData(p)); self.key.setText(k); self._set(self._pkey(p), k)
        tm.timeout.connect(poll); tm.start()
        QDesktopServices.openUrl(QUrl(url))
        if dl.exec() == QDialog.Accepted: self.test_key()
        tm.stop()

    def test_key(self):
        from ..core import ai as AI
        prov = self.prov.currentData(); key = self.key.text().strip()
        self._set(self._pkey(), key)
        if not key: self.ai_st.setText(t('ai_none')); return
        model = self.model.currentText().strip(); usage = self.win.usage
        self.ai_st.setText('⏳ ' + t('ai_testing'))

        def ok(r):
            models, m = r
            self._set(self._mkey(), m); self._fill_models(models)
            self.ai_st.setText(t('ai_ok', n=len(models), m=m)); self._usage()

        def fail(e):
            self.ai_st.setText(t('ai_bad', e=str(e)[:260])); self._usage()
        run_bg(AI.test, prov, key, model, usage, on_done=ok, on_fail=fail)

    def _usage(self):
        d = self.win.usage.data; day = time.strftime('%Y-%m-%d')
        lines = []
        names = {'gemini': 'Gemini', 'anthropic': 'Claude'}
        bp = d.get('by_provider') or {}
        for p in ('gemini', 'anthropic'):
            x = bp.get(p)
            if not x: continue
            td = x.get('today') or {}
            dc, dt = (td.get('calls', 0), td.get('tokens', 0)) if td.get('day') == day else (0, 0)
            lines.append(t('ai_prov_usage', p=names[p], c=x['calls'], tk=f"{x['in'] + x['out']:,}", dc=dc, dt=f'{dt:,}'))
        if not lines and d.get('calls'):
            bd = d['by_day'].get(day, {'calls': 0, 'in': 0, 'out': 0})
            lines.append(t('s_usage_txt', c=d['calls'], i=d['input_tokens'], o=d['output_tokens'], dc=bd['calls'], dt=bd['in'] + bd['out']))
        if not lines: lines.append(t('ai_no_usage'))
        tk, c = self.win.usage.month_tokens(30)
        lines.append(t('ai_30d', c=c, tk=f'{tk:,}'))
        pl = d.get('plimits') or {}
        prov = self.prov.currentData()
        if prov == 'gemini':
            lines.append(''); lines.append(t('ai_gem_lim'))
            q = pl.get('gemini') or {}
            if q.get('quota_hit'): lines.append(t('ai_quota_hit', t=q['quota_hit'], d='; '.join(q.get('details') or [])[:300]))
        else:
            lim = pl.get('anthropic') or d.get('limits') or {}
            parts = []
            for k in ('requests', 'input-tokens', 'output-tokens', 'tokens'):
                if k + '-limit' in lim:
                    parts.append(f"{k}: {lim.get(k + '-remaining', '?')}/{lim[k + '-limit']} (reset {str(lim.get(k + '-reset', ''))[11:19]})")
            lines.append(''); lines.append(t('s_limits') + '\n' + '\n'.join(parts) if parts else t('s_no_limits'))
        self.usage.setText('\n'.join(lines))

    # ---- Analiz
    def _an_info(self):
        try:
            from ..core import cache, anomaly
            self.cache_now.setText(t('s_cache_now', mb=cache.size_mb()))
            self.anom_l.setText(t('s_anom', n=anomaly.model_info()['flights']))
        except Exception as e:
            self.anom_l.setText(str(e)[:120])

    def _clear_cache(self):
        from ..core import cache
        cache.clear(); self._an_info()

    def _anom_reset(self):
        from ..core import anomaly
        anomaly.save_model({'profiles': {}, 'learned': []}); self._an_info()

    # ---- Rapor bölümleri
    def _fill_secs(self):
        from PySide6.QtWidgets import QListWidgetItem
        from ..core import report
        cfg = self.win.settings.get('report_sections')
        order = [k for k, _ in cfg] if cfg else list(report.SECTIONS)
        order += [k for k in report.SECTIONS if k not in order]
        on = dict(cfg) if cfg else {}
        self.secs.blockSignals(True); self.secs.clear()
        for k in order:
            if k not in report.SECTIONS: continue
            it = QListWidgetItem(('★ ' if k in report.SHORT else '   ') + report.R('sec_' + k, lang()))
            it.setData(Qt.UserRole, k); it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            it.setCheckState(Qt.Checked if on.get(k, True) else Qt.Unchecked); self.secs.addItem(it)
        self.secs.blockSignals(False)

    def _save_secs(self):
        cfg = [[self.secs.item(i).data(Qt.UserRole), self.secs.item(i).checkState() == Qt.Checked] for i in range(self.secs.count())]
        self._set('report_sections', cfg)

    def _reset_secs(self):
        self._set('report_sections', None); self._fill_secs()

    # ---- Mission Planner
    def _dirs(self):
        from ..core import mpwatch
        s = self.win.settings
        self.dirs.clear()
        for d in s.get('watch_dirs') or []: self.dirs.addItem(d)
        for d in mpwatch.default_dirs():
            if d not in (s.get('watch_dirs') or []): self.dirs.addItem(d + '  (Mission Planner)')
        self.assoc_l.setText(t('s_assoc_on') if mpwatch.is_associated() else ('' if mpwatch.exe_path() else t('s_assoc_dev')))

    def _add_dir(self):
        d = QFileDialog.getExistingDirectory(self, t('s_add_dir'))
        if d:
            s = self.win.settings; ds = list(s.get('watch_dirs') or [])
            if d not in ds: ds.append(d)
            self._set('watch_dirs', ds); self.win.setup_watch(); self._dirs()

    def _rm_dir(self):
        it = self.dirs.currentItem()
        if not it: return
        s = self.win.settings; ds = [x for x in (s.get('watch_dirs') or []) if x != it.text()]
        self._set('watch_dirs', ds); self.win.setup_watch(); self._dirs()

    def _assoc(self):
        from ..core import mpwatch
        try:
            if mpwatch.associate(): info(self, t('s_assoc_ok'))
            else: info(self, t('s_assoc_dev'))
        except Exception as e:
            error(self, str(e)[:300])
        self._dirs()

    # ---- Güvenlik
    def _users(self):
        from ..core import security
        self.ulist.clear()
        for u in security.users(self.win.archive):
            from PySide6.QtWidgets import QListWidgetItem
            it = QListWidgetItem(f"{u['name']} · {security.role_name(u.get('role'), lang())}"); it.setData(Qt.UserRole, u['id']); self.ulist.addItem(it)

    def _add_user(self):
        from PySide6.QtWidgets import QDialog
        from ..core import security
        dl = QDialog(self); dl.setWindowTitle(t('s_add_user')); f = QFormLayout(dl)
        nm = QLineEdit(); f.addRow(t('u_name'), nm)
        pw = QLineEdit(); pw.setEchoMode(QLineEdit.Password); f.addRow(t('u_pw'), pw)
        rl = QComboBox()
        for r in security.ROLES: rl.addItem(security.role_name(r, lang()), r)
        if not security.users(self.win.archive): rl.setCurrentIndex(0)
        else: rl.setCurrentIndex(2)
        f.addRow(t('u_role'), rl)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('save'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() == QDialog.Accepted and nm.text().strip() and pw.text():
            security.add_user(self.win.archive, nm.text(), rl.currentData(), pw.text()); self._users()

    def _del_user(self):
        it = self.ulist.currentItem()
        if it: self.win.archive.rec_del('user', it.data(Qt.UserRole)); self._users()

    def _req_login(self, x):
        from ..core import security
        if x and not any(u.get('role') == 'admin' for u in security.users(self.win.archive)):
            self.reql.blockSignals(True); self.reql.setChecked(False); self.reql.blockSignals(False)
            info(self, t('s_need_admin')); return
        self._set('require_login', x)

    def _enc_file(self):
        from ..core import security
        p, _ = QFileDialog.getOpenFileName(self, t('s_enc_file'))
        if not p: return
        pw, ok = QInputDialog.getText(self, t('s_enc_file'), t('u_pw'), QLineEdit.Password)
        if not ok or not pw: return
        out = security.encrypt_file(p, p + '.pxenc', pw); info(self, t('enc_done', p=out))

    def _dec_file(self):
        from ..core import security
        p, _ = QFileDialog.getOpenFileName(self, t('s_dec_file'), '', 'Encrypted (*.pxenc);;All (*.*)')
        if not p: return
        pw, ok = QInputDialog.getText(self, t('s_dec_file'), t('u_pw'), QLineEdit.Password)
        if not ok: return
        out = p[:-6] if p.endswith('.pxenc') else p + '.dec'
        try:
            security.decrypt_file(p, out, pw); info(self, t('dec_done', p=out)); open_path(os.path.dirname(out))
        except Exception:
            error(self, t('ex_bad_pw'))

    # ---- Hata raporları
    def _crash_info(self):
        from ..core import crash
        try: n = len(crash.pending())
        except Exception: n = 0
        self.crash_l.setText(t('s_crash_n', n=n) if n else t('s_crash_none')); self.b_crash.setEnabled(bool(n))

    def _send_crash(self):
        from ..core import crash
        ps = crash.pending()
        if ps: self.win.crash_dialog(ps)
        self._crash_info()

    # ---- Antet şablonları
    def _fill_tpls(self):
        s = self.win.settings
        self.tpl.blockSignals(True); self.tpl.clear()
        for n in s['templates']: self.tpl.addItem(n)
        self.tpl.setCurrentText(s.get('template', 'default')); self.tpl.blockSignals(False)
        self._load_tpl()

    def _load_tpl(self):
        n = self.tpl.currentText(); s = self.win.settings
        if not n: return
        s['template'] = n; s.save()
        lh = s['templates'].get(n, {})
        for k, e in self.fields.items(): e.setText(str(lh.get(k, '')))
        for w, val in ((self.besmele, bool(lh.get('besmele'))), (self.top, float(lh.get('top_cm') or 0))):
            w.blockSignals(True); (w.setChecked if w is self.besmele else w.setValue)(val); w.blockSignals(False)
        self._lh_info()

    def _set_tpl(self, k, val):
        n = self.tpl.currentText(); s = self.win.settings
        if not n: return
        s['templates'].setdefault(n, {})[k] = val; s.save(); self._lh_info()

    def _cur_lh(self):
        from ..core.report import DEFAULT_LH
        s = self.win.settings
        return {**DEFAULT_LH, **s['templates'].get(self.tpl.currentText(), {})}

    def _lh_info(self):
        from ..core import letterhead as LHM
        lh = self._cur_lh()
        if not LHM.resolve(lh.get('bg') or ''):
            self.lh_info.setText(t('s_lh_none')); return
        try:
            top, _ = LHM.bands(LHM.resolve(lh['bg']))
            self.lh_info.setText(t('s_lh_auto', t=top))
        except Exception as e:
            self.lh_info.setText(str(e)[:200])

    def load_lh(self):
        p, _ = QFileDialog.getOpenFileName(self, t('s_lh_load'), '', 'Letterhead (*.png *.jpg *.jpeg *.docx)')
        if not p: return
        from ..core import letterhead as LHM
        if p.lower().endswith('.docx'):
            def done(r):
                self.bg.setText(r['bg']); self._save_tpl()
                if r.get('besmele'): self.besmele.setChecked(True)
                info(self, t('s_lh_imported') + ('\n' + ' · '.join(r.get('texts') or [])[:300] if r.get('texts') else ''))
                self.preview_lh()
            run_bg(LHM.import_docx, p, on_done=done, on_fail=lambda e: error(self, e[:300]))
            return
        self._browse(self.bg, p); self._lh_info()

    def clear_lh(self):
        self.bg.setText(''); self._save_tpl(); self._lh_info()

    def use_preset(self):
        from ..core.letterhead import PRESET_NAME, PRESET
        s = self.win.settings
        s['templates'][PRESET_NAME] = {**PRESET, **{k: v for k, v in s['templates'].get(PRESET_NAME, {}).items() if k not in ('bg',)}}
        s['templates'][PRESET_NAME]['bg'] = PRESET['bg']
        s['template'] = PRESET_NAME; s.save(); self._fill_tpls()

    def preview_lh(self):
        from PySide6.QtWidgets import QDialog, QLabel
        from PySide6.QtGui import QPixmap, QImage
        from ..core import letterhead as LHM
        lh = self._cur_lh()
        try:
            pages = LHM.preview_images(lh, self.win.settings.get('report_lang', 'tr'), width=430)
        except Exception as e:
            error(self, str(e)[:300]); return
        dl = QDialog(self); dl.setWindowTitle(t('s_lh_preview')); lay = QVBoxLayout(dl); row = QHBoxLayout(); lay.addLayout(row)
        for im, cap in zip(pages, (t('s_lh_p1'), t('s_lh_p2'))):
            col = QVBoxLayout(); b = im.convert('RGB').tobytes('raw', 'RGB')
            qi = QImage(b, im.width, im.height, im.width * 3, QImage.Format_RGB888).copy()
            lb = QLabel(); lb.setPixmap(QPixmap.fromImage(qi)); lb.setStyleSheet('border:1px solid #9CA3AF;')
            col.addWidget(lb); col.addWidget(label(cap, 'muted')); row.addLayout(col)
        bh = QHBoxLayout(); bh.addStretch(1); bh.addWidget(button(t('s_lh_pdf'), self.sample_pdf)); bh.addWidget(button(t('close'), dl.accept, primary=True))
        lay.addLayout(bh); dl.exec()

    def sample_pdf(self):
        from ..core import report
        lh = self._cur_lh(); lg = self.win.settings.get('report_lang', 'tr')
        out = os.path.join(data_dir(), 'antet_onizleme.pdf')
        run_bg(report.sample_pdf, out, lh, lg, on_done=lambda p: open_path(p), on_fail=lambda e: error(self, e[:300]))

    def _save_tpl(self):
        n = self.tpl.currentText(); s = self.win.settings
        if not n: return
        lh = s['templates'].setdefault(n, {})
        for k, e in self.fields.items(): lh[k] = e.text().strip()
        s.save()

    def new_tpl(self):
        n, ok = QInputDialog.getText(self, t('s_new_tpl'), t('s_tpl_name'))
        if ok and n.strip():
            s = self.win.settings; s['templates'][n.strip()] = dict(s.letterhead()); s['template'] = n.strip(); s.save(); self._fill_tpls()

    def del_tpl(self):
        n = self.tpl.currentText()
        if n and n != 'default':
            s = self.win.settings; s['templates'].pop(n, None); s['template'] = 'default'; s.save(); self._fill_tpls()

    def _browse(self, e, p=None):
        if not p:
            p, _ = QFileDialog.getOpenFileName(self, t('s_browse'), '', 'Image (*.png *.jpg *.jpeg)')
        if p:
            # Görseli veri klasörüne kopyala (eşitlenen şablon yolları kopmasın)
            import shutil
            d = os.path.join(data_dir(), 'letterheads'); os.makedirs(d, exist_ok=True)
            dst = os.path.join(d, os.path.basename(p))
            try: shutil.copy2(p, dst); p = dst
            except Exception: pass
            e.setText(p); self._save_tpl()

    def _pick_color(self):
        from PySide6.QtGui import QColor
        c = QColorDialog.getColor(QColor(self.color.text() or '#1E3A8A'), self)
        if c.isValid(): self.color.setText(c.name().upper()); self._save_tpl()

    # ---- Harita
    def _cache(self):
        from ..core.tiles import cache_dir
        tot = 0
        for r, _, fs in os.walk(cache_dir()):
            for f in fs:
                try: tot += os.path.getsize(os.path.join(r, f))
                except Exception: pass
        self.cache_l.setText(t('s_cache', mb=tot / 1e6))

    # ---- Eşitleme
    def _sync_info(self):
        s = self.win.settings; parts = []
        if s.get('last_sync'): parts.append(t('s_last_sync', t=s['last_sync']))
        rl = s.get('gh_rate') or {}
        if rl.get('limit'): parts.append(t('s_rate', r=rl.get('remaining'), l=rl.get('limit')))
        self.sync_l.setText('  ·  '.join(parts))

    def gh_sync(self):
        self._set('gh_token', self.tok.text().strip())
        self.win.do_sync(after=self._sync_info)

    def lan_sync(self):
        self._set('lan_code', self.code.text().strip())
        from ..core import sync
        s = self.win.settings; a = self.win.archive
        self.b_lan.setEnabled(False); self.lan_l.setText('…')

        def job():
            peers = sync.discover(s)
            res = []
            for p in peers:
                try: res.append((p['name'], sync.lan_sync_with(s, a, p)))
                except Exception as e: res.append((p['name'], str(e)))
            return res

        def ok(res):
            self.b_lan.setEnabled(True)
            if not res: self.lan_l.setText(t('s_lan_none')); return
            lines = []
            for n, r in res:
                lines.append(f'{n}: ' + (t('s_synced', a=r[0], u=r[1]) if isinstance(r, tuple) else r))
            self.lan_l.setText('\n'.join(lines)); self.win.pages['archive'].refresh(); self._fill_tpls()
        run_bg(job, on_done=ok, on_fail=lambda e: (self.b_lan.setEnabled(True), self.lan_l.setText(e)))

    # ---- İletişim
    def contact(self):
        import re
        msg = self.c_msg.toPlainText().strip(); mail = self.c_mail.text().strip()
        if not msg: self.c_st.setText(t('c_empty')); return
        if mail and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', mail): self.c_st.setText(t('c_fail')); return
        from ..core import contact
        self.b_send.setEnabled(False); self.c_st.setText('…')

        def ok(r):
            self.b_send.setEnabled(True)
            if r: self.c_msg.clear(); self.c_st.setText(t('c_ok'))
            else: self.c_st.setText(t('c_fail'))
        run_bg(contact.send, msg, self.c_name.text().strip(), mail, lang(), on_done=ok,
               on_fail=lambda e: (self.b_send.setEnabled(True), self.c_st.setText(t('c_fail'))))
