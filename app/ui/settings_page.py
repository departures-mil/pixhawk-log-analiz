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

        # Yapay zekâ
        g = QGroupBox(t('s_ai')); f = QFormLayout(g)
        f.addRow(label(t('s_key_help'), 'muted', wrap=True))
        kh = QHBoxLayout()
        self.key = QLineEdit(s.get('api_key', '')); self.key.setEchoMode(QLineEdit.Password); self.key.setPlaceholderText('sk-ant-…')
        self.key.editingFinished.connect(lambda: self._set('api_key', self.key.text().strip()))
        kh.addWidget(self.key, 1)
        kh.addWidget(button('👁', lambda: self.key.setEchoMode(QLineEdit.Normal if self.key.echoMode() == QLineEdit.Password else QLineEdit.Password)))
        kh.addWidget(button(t('s_get_key'), lambda: QDesktopServices.openUrl(QUrl('https://console.anthropic.com/settings/keys'))))
        kh.addWidget(button(t('s_test'), self.test_key))
        f.addRow(t('s_key'), kh)
        from ..core.advisor import MODELS
        self.model = QComboBox(); self.model.addItems(MODELS); self.model.setEditable(True)
        self.model.setCurrentText(s.get('model')); self.model.currentTextChanged.connect(lambda x: self._set('model', x.strip()))
        f.addRow(t('s_model'), self.model)
        self.effort = QComboBox(); self.effort.addItems(['low', 'medium', 'high', 'max']); self.effort.setCurrentText(s.get('effort', 'medium'))
        self.effort.currentTextChanged.connect(lambda x: self._set('effort', x)); f.addRow(t('s_effort'), self.effort)
        f.addRow(label(t('s_usage'), 'h2'))
        self.usage = label('', wrap=True, sel=True); f.addRow(self.usage)
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
        self._usage(); self._cache(); self._sync_info()

    def _set(self, k, val):
        self.win.settings[k] = val; self.win.settings.save()

    def _lang(self):
        self._set('lang', self.lang.currentData()); self.win.apply_lang()

    # ---- AI
    def _usage(self):
        d = self.win.usage.data; day = time.strftime('%Y-%m-%d'); bd = d['by_day'].get(day, {'calls': 0, 'in': 0, 'out': 0})
        txt = t('s_usage_txt', c=d['calls'], i=d['input_tokens'], o=d['output_tokens'], dc=bd['calls'], dt=bd['in'] + bd['out'])
        lim = d.get('limits') or {}
        if lim:
            parts = []
            for k in ('requests', 'input-tokens', 'output-tokens', 'tokens'):
                if k + '-limit' in lim:
                    parts.append(f"{k}: {lim.get(k + '-remaining', '?')}/{lim[k + '-limit']} (reset {lim.get(k + '-reset', '')[11:19]})")
            txt += '\n' + t('s_limits') + '\n' + '\n'.join(parts)
        else:
            txt += '\n' + t('s_no_limits')
        self.usage.setText(txt)

    def test_key(self):
        self._set('api_key', self.key.text().strip())
        key = self.key.text().strip()
        if not key: return
        model = self.model.currentText().strip(); usage = self.win.usage

        def job():
            import anthropic
            c = anthropic.Anthropic(api_key=key, timeout=60)
            raw = c.messages.with_raw_response.create(model=model, max_tokens=16, messages=[{'role': 'user', 'content': 'ping'}])
            usage.add(raw.parse().usage, raw.headers); return True
        run_bg(job, on_done=lambda _: (self._usage(), info(self, '✔ OK')), on_fail=lambda e: error(self, e[:300]))

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
