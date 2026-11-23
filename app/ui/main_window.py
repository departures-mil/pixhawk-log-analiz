"""Ana pencere: çerçevesiz, açılışta tam ekran; sağ üstte Güncelle, Eşitle, Küçült, Yarım, Kapat."""
from __future__ import annotations
import os, sys, time
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QStackedWidget,
                               QFileDialog, QDialog, QFormLayout, QComboBox, QCheckBox, QProgressBar, QLabel, QApplication, QSizeGrip)
from .i18n import t, lang, set_lang
from .common import TitleBar, label, button, run_bg, error, info, open_path, app_icon
from . import pages_a as PA, pages_b as PB, pages_c as PC, pages_p as PP
from .settings_page import SettingsPage
from ..core.settings import Settings
from ..core.archive import Archive, file_uid
from ..core.advisor import Usage
from ..core.paths import data_dir

NAV = [('analysis', '🔎', 'nav_analysis', PA.AnalysisPage), ('charts', '📈', 'nav_charts', PA.ChartsPage),
       ('map', '🗺', 'nav_map', PA.MapPage), ('timeline', '🕒', 'nav_timeline', PA.TimelinePage),
       ('advisor', '🤖', 'nav_advisor', PA.AdvisorPage), ('practice', '🎓', 'nav_practice', PA.PracticePage),
       ('exam', '📝', 'nav_exam', PC.ExamPage),
       ('scen', '🧪', 'nav_scen', PB.ScenarioPage), ('crashlib', '💥', 'nav_crashlib', PP.CrashLibPage), ('batch', '🗂', 'nav_batch', PB.BatchPage),
       ('archive', '🗄', 'nav_archive', PB.ArchivePage), ('fleet', '🛩', 'nav_fleet', PC.FleetPage),
       ('pilots', '👨‍✈️', 'nav_pilots', PC.PilotsPage), ('msgs', '📘', 'nav_msgs', PB.MsgLibPage),
       ('params', '🧩', 'nav_params', PP.ParamCenterPage), ('verify', '✅', 'nav_verify', PB.VerifyPage),
       ('settings', '🛠', 'nav_settings', SettingsPage)]


class MainWindow(QMainWindow):
    lan_merged = Signal(object, str)
    crashed = Signal(str)
    open_req = Signal(str)

    def __init__(self):
        super().__init__()
        self.settings = Settings(); set_lang(self.settings['lang'])
        self.archive = Archive()
        self.usage = Usage(os.path.join(data_dir(), 'ai_usage.json'))
        self.A = None; self.uid = None; self._cancel = False; self._half = False
        self.role = 'admin'; self.user_name = ''
        self._apply_core_settings()
        self.crashed.connect(self._on_crash); self.open_req.connect(self._open_req)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setWindowIcon(app_icon())
        self.lan_merged.connect(self._lan_merged)
        self.build()
        # LAN eşitleme sunucusu (aynı modemdeki cihazlar için)
        try:
            from ..core.sync import LanServer
            self.lan = LanServer(self.settings, self.archive, on_merged=lambda r, n: self.lan_merged.emit(r, n)); self.lan.start()
        except Exception:
            self.lan = None
        if self.settings.get('auto_update_check', True):
            QTimer.singleShot(2500, lambda: self.do_update(silent=True))
        # Mission Planner log klasörü izleme
        self.watcher = None; self.wtimer = QTimer(self); self.wtimer.setInterval(5000); self.wtimer.timeout.connect(self._watch_tick)
        self.setup_watch()
        QTimer.singleShot(4000, self._pending_crashes)

    # ------------------------------------------------------------ v1.0.2 yardımcıları
    def _apply_core_settings(self):
        s = self.settings
        try:
            from ..core import analysis, cache
            analysis.PROFILE_OVERRIDE['v'] = s.get('profile', 'auto') or 'auto'
            cache.MAX_MB = int(s.get('cache_max_mb', 3000) or 3000)
        except Exception:
            pass

    def login(self):
        """Giriş gerekiyorsa sor. False: kullanıcı vazgeçti."""
        from ..core import security
        us = security.users(self.archive)
        if not (self.settings.get('require_login') and us): return True
        from PySide6.QtWidgets import QLineEdit
        while True:
            dl = QDialog(); dl.setWindowTitle(t('login_title')); dl.setWindowIcon(app_icon()); dl.setMinimumWidth(380); f = QFormLayout(dl)
            nm = QComboBox(); nm.setEditable(True); nm.addItems([u['name'] for u in us]); f.addRow(t('u_name'), nm)
            pw = QLineEdit(); pw.setEchoMode(QLineEdit.Password); f.addRow(t('u_pw'), pw); pw.setFocus()
            h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('login_title'), dl.accept, primary=True)); f.addRow(h)
            if dl.exec() != QDialog.Accepted: return False
            u = security.login(self.archive, nm.currentText(), pw.text())
            if u:
                self.role = u.get('role', 'student'); self.user_name = u['name']; return True
            error(dl, t('login_bad'))

    def apply_role(self):
        from ..core import security
        hid = security.HIDDEN.get(self.role, set())
        for i, k in enumerate(self.keys):
            self.nav.item(i).setHidden(k in hid)
        if self.user_name:
            self.set_status(t('login_as', n=self.user_name, r=security.role_name(self.role, lang())))

    def setup_watch(self):
        from ..core import mpwatch
        s = self.settings
        if s.get('watch_enabled'):
            dirs = list(dict.fromkeys((s.get('watch_dirs') or []) + mpwatch.default_dirs()))
            self.watcher = mpwatch.Watcher(dirs); self.wtimer.start()
        else:
            self.watcher = None; self.wtimer.stop()

    def _watch_tick(self):
        if not self.watcher: return
        try: new = self.watcher.scan()
        except Exception: return
        for p in new:
            if self.settings.get('auto_analyze'):
                self.open_log(p)
            else:
                self.set_status(t('mp_new', n=os.path.basename(p)))
                self.mp_btn.setText('▶ ' + t('mp_analyze') + ': ' + os.path.basename(p)); self.mp_btn.setVisible(True)
                self.mp_btn.path = p
            break

    def _mp_open(self):
        p = getattr(self.mp_btn, 'path', None); self.mp_btn.setVisible(False)
        if p: self.open_log(p)

    def _open_req(self, p):
        self.showMaximized(); self.raise_(); self.activateWindow()
        if p and os.path.isfile(p): self.open_log(p)

    # ------------------------------------------------------------ çökme raporu
    def _on_crash(self, path):
        self.crash_dialog([path])

    def _pending_crashes(self):
        from ..core import crash
        try: ps = crash.pending()
        except Exception: ps = []
        if ps: self.crash_dialog(ps, prev=True)

    def crash_dialog(self, paths, prev=False):
        if getattr(self, '_crash_open', False): return
        self._crash_open = True
        try:
            from PySide6.QtWidgets import QPlainTextEdit
            from ..core import crash
            dl = QDialog(self); dl.setWindowTitle(t('cr_title')); dl.setMinimumWidth(560); v = QVBoxLayout(dl)
            v.addWidget(label((t('cr_prev') + '\n\n' if prev else '') + t('cr_text'), wrap=True))
            note = QPlainTextEdit(); note.setPlaceholderText(t('cr_note')); note.setMaximumHeight(80); v.addWidget(note)
            det = QPlainTextEdit(); det.setReadOnly(True); det.setVisible(False); det.setMinimumHeight(220)
            try: det.setPlainText('\n\n'.join(open(p, encoding='utf-8').read()[-5000:] for p in paths))
            except Exception: pass
            v.addWidget(det)
            h = QHBoxLayout(); h.addWidget(button(t('cr_details'), lambda: det.setVisible(not det.isVisible()))); h.addStretch(1)
            h.addWidget(button(t('cr_later'), dl.reject)); h.addWidget(button(t('cr_send'), dl.accept, primary=True)); v.addLayout(h)
            if dl.exec() == QDialog.Accepted:
                run_bg(crash.send, paths, lang(), note.toPlainText(), on_done=lambda ok: self.set_status(t('cr_sent') if ok else t('c_fail')),
                       on_fail=lambda e: self.set_status(t('c_fail')))
        finally:
            self._crash_open = False

    # ------------------------------------------------------------ kurulum
    def build(self):
        rtl = lang() == 'ar'
        QApplication.instance().setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        self.setWindowTitle(t('app'))
        root = QWidget(); root.setObjectName('root'); self.setCentralWidget(root)
        v = QVBoxLayout(root); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        self.titlebar = TitleBar(self); v.addWidget(self.titlebar)
        body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)
        self.nav = QListWidget(); self.nav.setObjectName('nav'); self.nav.setFixedWidth(250)
        self.stack = QStackedWidget(); self.pages = {}; self.keys = []
        for key, ic, tk, cls in NAV:
            it = QListWidgetItem(f'{ic}  {t(tk)}'); self.nav.addItem(it)
            p = cls(self); self.pages[key] = p; self.keys.append(key); self.stack.addWidget(p)
        self.nav.currentRowChanged.connect(self._nav)
        body.addWidget(self.nav); body.addWidget(self.stack, 1)
        v.addLayout(body, 1)
        sb = QHBoxLayout(); sbw = QWidget(); sbw.setObjectName('statusbar'); sbw.setAttribute(Qt.WA_StyledBackground, True); sbw.setLayout(sb)
        sb.setContentsMargins(10, 2, 2, 2)
        self.status = QLabel(''); sb.addWidget(self.status, 1)
        self.mp_btn = button('', self._mp_open, primary=True); self.mp_btn.setVisible(False); sb.addWidget(self.mp_btn)
        self.upd_bar = QProgressBar(); self.upd_bar.setVisible(False); self.upd_bar.setFixedWidth(560); sb.addWidget(self.upd_bar)
        sb.addWidget(QSizeGrip(sbw))
        v.addWidget(sbw)
        self.nav.setCurrentRow(0)
        self.apply_role()
        if self.A:
            for p in self.pages.values():
                try: p.on_analysis(self.A)
                except Exception: pass

    def apply_lang(self):
        set_lang(self.settings['lang'])
        cur = self.nav.currentRow()
        old = self.centralWidget(); self.build(); old.deleteLater()
        self.nav.setCurrentRow(cur)
        self.set_status(t('restart_lang'))

    def _nav(self, i):
        self.stack.setCurrentIndex(i)
        try: self.stack.currentWidget().on_show()
        except Exception: pass

    def goto(self, key):
        self.nav.setCurrentRow(self.keys.index(key))

    def set_status(self, s):
        self.status.setText(s)

    # ----------------------------------------------------- pencere düğmeleri
    def show_start(self):
        self.showMaximized()

    def toggle_half(self):
        scr = self.screen().availableGeometry()
        if self.isMaximized() or not self._half:
            self.showNormal()
            w = scr.width() // 2; self.setGeometry(scr.x() + (scr.width() - w) // 2, scr.y() + scr.height() // 10, w, int(scr.height() * 0.8))
            self._half = True
        else:
            self._half = False; self.showMaximized()

    # ------------------------------------------------------------ log açma
    def pick_log(self):
        p, _ = QFileDialog.getOpenFileName(self, t('open_log'), '', 'Pixhawk log (*.bin *.BIN *.tlog *.log);;All (*.*)')
        if p: self.open_log(p)

    def cancel_load(self):
        self._cancel = True

    def open_log(self, path, archive=True):
        self.goto('analysis')
        pg = self.pages['analysis']; pg.set_busy(True, t('loading')); self._cancel = False
        s = self.settings; arc = self.archive
        w = None

        def job():
            from ..core import loader, analysis, crash, security
            crash.note('open ' + os.path.basename(path))
            real = path
            if path.lower().endswith('.pxloc'): real = security.open_local_file(path)
            L = loader.load(real, progress=lambda f: w.progress.emit(('l', f)), cancel=lambda: self._cancel)
            w.progress.emit(('a', 0.0))
            A = analysis.Analysis(L)
            uid = file_uid(real)
            if archive:
                arc.add_analysis(uid, A, real, s['device_name'], s.get('archive_copy_logs', True), s.get('archive_copy_max_mb', 200),
                                 encrypt=bool(s.get('encrypt_local')))
                try:
                    from ..core import fleet, anomaly
                    fleet.ensure_aircraft(arc, A)
                    anomaly.learn(A, uid)
                except Exception as e:
                    crash.note(f'fleet/anomaly: {e}')
            if s.get('online', True) and s.get('weather_online', True):
                try:
                    from ..core import weather
                    weather.for_analysis(A)
                except Exception:
                    pass
            return A, uid

        def prog(x):
            k, f = x
            if k == 'l': pg.set_progress(f, t('loading'))
            else: pg.set_progress(1.0, t('analyzing'))

        def ok(r):
            pg.set_busy(False)
            self.A, self.uid = r
            for p in self.pages.values():
                try: p.on_analysis(self.A)
                except Exception as e: print('page', p, e)
            self.set_status(f'{os.path.basename(path)} · {t("saved_archive") if archive else ""}')

        def fail(e):
            pg.set_busy(False); error(self, e)
        w = run_bg(job, on_done=ok, on_fail=fail, on_progress=prog)

    # ------------------------------------------------------------- rapor
    def export_report(self):
        if not self.A: return error(self, t('no_log'))
        s = self.settings
        dl = QDialog(self); dl.setWindowTitle(t('rep_title')); dl.setMinimumWidth(480)
        f = QFormLayout(dl)
        lc = QComboBox()
        for c, n in (('tr', 'Türkçe'), ('en', 'English'), ('ar', 'العربية')): lc.addItem(n, c)
        lc.setCurrentIndex(lc.findData(s.get('report_lang', lang()))); f.addRow(t('rep_lang'), lc)
        fc = QComboBox(); fc.addItem('PDF', 'pdf'); fc.addItem('DOCX', 'docx'); fc.addItem(t('rep_both'), 'both')
        fc.setCurrentIndex(max(0, fc.findData(s.get('report_fmt', 'pdf')))); f.addRow(t('rep_fmt'), fc)
        tc = QComboBox(); tc.addItems(list(s['templates'])); tc.setCurrentText(s.get('template', 'default')); f.addRow(t('rep_tpl'), tc)
        from ..core import ai as AI
        md = QComboBox(); md.addItem(t('rep_long'), 'long'); md.addItem(t('rep_short'), 'short')
        md.setCurrentIndex(max(0, md.findData(s.get('report_mode', 'long')))); f.addRow(t('s_rep_mode'), md)
        acs = QComboBox(); acs.addItem(t('fl_none'), '')
        for a_ in self.archive.rec_list('aircraft'): acs.addItem(f"{a_.get('name', '')} · {a_.get('serial', '')}", a_['id'])
        cur_rec = self.archive.get(self.uid) if self.uid else None
        acs.setCurrentIndex(max(0, acs.findData((cur_rec or {}).get('aircraft') or getattr(self.A, 'serial', '')))); f.addRow(t('rep_aircraft'), acs)
        pls = QComboBox(); pls.addItem(t('fl_none'), '')
        for p_ in self.archive.rec_list('pilot'): pls.addItem(p_['name'], p_['id'])
        pls.setCurrentIndex(max(0, pls.findData((cur_rec or {}).get('pilot') or ''))); f.addRow(t('rep_pilot'), pls)
        ai = QCheckBox(t('rep_ai')); ai.setChecked(bool(s.get('report_ai', True) and AI.available(s))); ai.setEnabled(AI.available(s)); f.addRow(ai)
        mp = QCheckBox(t('rep_map')); mp.setChecked(bool(s.get('online', True))); f.addRow(mp)
        from PySide6.QtWidgets import QLineEdit
        enc = QCheckBox(t('rep_encrypt')); pw = QLineEdit(); pw.setEchoMode(QLineEdit.Password); pw.setPlaceholderText(t('rep_pw')); pw.setEnabled(False)
        enc.toggled.connect(pw.setEnabled); eh = QHBoxLayout(); eh.addWidget(enc); eh.addWidget(pw, 1); f.addRow(eh)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('export'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted: return
        rl, fmt, tpl = lc.currentData(), fc.currentData(), tc.currentText()
        mode = md.currentData(); s['report_mode'] = mode
        s['report_lang'] = rl; s['report_fmt'] = fmt; s['template'] = tpl; s['report_ai'] = ai.isChecked(); s.save()
        password = pw.text() if enc.isChecked() and pw.text() else None
        if self.uid:
            if acs.currentData() != ((cur_rec or {}).get('aircraft') or ''): self.archive.set_field(self.uid, aircraft=acs.currentData())
            if pls.currentData() != ((cur_rec or {}).get('pilot') or ''): self.archive.set_field(self.uid, pilot=pls.currentData())
        ac_name = acs.currentText() if acs.currentData() else ''; pi_name = pls.currentText() if pls.currentData() else ''
        sections = s.get('report_sections')
        base = os.path.splitext(os.path.basename(self.A.L.path))[0] + f'_rapor_{rl}'
        ext = 'docx' if fmt == 'docx' else 'pdf'
        out, _ = QFileDialog.getSaveFileName(self, t('rep_title'), os.path.join(os.path.dirname(self.A.L.path), base + '.' + ext),
                                             'PDF (*.pdf)' if ext == 'pdf' else 'Word (*.docx)')
        if not out: return
        out = os.path.splitext(out)[0]
        A = self.A; uid = self.uid; lh = s['templates'].get(tpl) or s.letterhead(); use_ai = ai.isChecked(); online_map = mp.isChecked()
        arc = self.archive; dev = s['device_name']; usage = self.usage
        self.set_status(t('rep_creating'))
        pg = self.pages['analysis']; pg.set_busy(True, t('rep_creating')); pg.prog.setRange(0, 0)

        def job():
            from ..core import report
            from ..core import ai as AI, security
            ai_text = None
            if use_ai and AI.available(s):
                try:
                    adv = AI.make_advisor(A, s, rl, usage)
                    ai_text = adv.ask('Write the expert commentary section of the official flight-log report: 1) overall assessment, '
                                      '2) what happened and when (key times), 3) root cause with evidence, 4) concrete recommendations '
                                      '(parameters, maintenance, training). Use short headings (#) and bullet points. Max ~450 words.')
                except Exception:
                    ai_text = None
            rd = report.ReportData(A, rl, ai_text, online_map, s.get('map_src', 'osm'), sections=sections, mode=mode)
            rd.aircraft_name = ac_name; rd.pilot_name = pi_name
            outs = []
            if fmt in ('pdf', 'both'):
                p = out + '.pdf'; report.build_pdf(rd, p, lh, encrypt=password); outs.append((p, 'pdf'))
            if fmt in ('docx', 'both'):
                p = out + '.docx'; report.build_docx(rd, p, lh)
                if password:
                    security.encrypt_file(p, p + '.pxenc', password); os.remove(p); p = p + '.pxenc'
                outs.append((p, 'docx'))
            for p, fm in outs:
                if uid: arc.add_report(rd.id, uid, report.file_sha256(p), A.verdict.get('kind'), A.overall, rl, fm, p, dev, os.path.basename(A.L.path))
            return outs

        def ok(outs):
            pg.set_busy(False); self.set_status('')
            from PySide6.QtWidgets import QMessageBox
            m = QMessageBox(self); m.setWindowTitle(t('done')); m.setText(t('rep_done', p='\n'.join(p for p, _ in outs)))
            bo = m.addButton(t('open_file'), QMessageBox.AcceptRole); bf = m.addButton(t('open_folder'), QMessageBox.ActionRole)
            m.addButton(t('close'), QMessageBox.RejectRole); m.exec()
            if m.clickedButton() == bo: open_path(outs[0][0])
            elif m.clickedButton() == bf: open_path(os.path.dirname(outs[0][0]))
        run_bg(job, on_done=ok, on_fail=lambda e: (pg.set_busy(False), error(self, e)))

    # --------------------------------------------------------- güncelleme
    def do_update(self, silent=False):
        from ..core import updater
        from ..version import VERSION
        if getattr(self, '_updating', False): return
        self._updating = True
        w = None

        def job():
            info_ = updater.check()
            if not info_: return None
            if silent: return ('avail', info_)
            w.progress.emit(('start', info_))
            p = updater.download(info_, progress=lambda d, n, sp, eta: w.progress.emit(('p', (d, n, sp, eta))))
            return ('done', p)

        def prog(x):
            k, v = x
            if k == 'start':
                self.upd_bar.setVisible(True); self.upd_bar.setRange(0, 1000); self.set_status(t('u_found', v=v['version']))
            else:
                d, n, sp, eta = v
                self.upd_bar.setValue(int(1000 * d / max(n, 1)))
                e = f'{int(eta // 60)}:{int(eta % 60):02d}'
                self.upd_bar.setFormat(t('u_prog', p=100 * d / max(n, 1), d=d / 1e6, t=n / 1e6, r=(n - d) / 1e6, s=sp / 1e6, eta=e))

        def ok(r):
            self._updating = False
            if r is None:
                if not silent: self.set_status(t('u_none', v=VERSION)); info(self, t('u_none', v=VERSION))
                return
            if r[0] == 'avail':
                self.set_status(t('u_avail', v=r[1]['version'])); self.titlebar.b_upd.setStyleSheet('background:#16A34A'); return
            self.set_status(t('u_install') if 'setup' in os.path.basename(r[1]).lower() else t('u_apply'))
            if updater.apply_and_restart(r[1]):
                QTimer.singleShot(600, QApplication.instance().quit)
            else:
                self.upd_bar.setVisible(False); info(self, t('u_dev'))

        def fail(e):
            self._updating = False; self.upd_bar.setVisible(False)
            if not silent: error(self, t('u_fail', e=e))
        w = run_bg(job, on_done=ok, on_fail=fail, on_progress=prog)

    # ----------------------------------------------------------- eşitleme
    def do_sync(self, after=None):
        from ..core import sync
        s = self.settings
        if not (s.get('gh_token') or '').strip():
            info(self, t('sync_need')); self.goto('settings'); return
        self.set_status('⇅ …')

        def ok(r):
            a, u, rl = r
            self.set_status(t('s_synced', a=a, u=u) + (('  ·  ' + t('s_rate', r=rl.get('remaining'), l=rl.get('limit'))) if rl.get('limit') else ''))
            self.pages['archive'].refresh()
            if after: after()
        run_bg(sync.github_sync, s, self.archive, on_done=ok, on_fail=lambda e: (self.set_status(''), error(self, e)))

    def _lan_merged(self, r, name):
        self.set_status(t('lan_merged', n=name, a=r[0], u=r[1]))
        try: self.pages['archive'].refresh()
        except Exception: pass

    def closeEvent(self, e):
        if self.lan: self.lan.stop = True
        self.wtimer.stop()
        super().closeEvent(e)
