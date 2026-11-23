"""Ana pencere: çerçevesiz, açılışta tam ekran; sağ üstte Güncelle, Eşitle, Küçült, Yarım, Kapat."""
from __future__ import annotations
import os, sys, time
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QStackedWidget,
                               QFileDialog, QDialog, QFormLayout, QComboBox, QCheckBox, QProgressBar, QLabel, QApplication, QSizeGrip)
from .i18n import t, lang, set_lang
from .common import TitleBar, label, button, run_bg, error, info, open_path, app_icon
from . import pages_a as PA, pages_b as PB
from .settings_page import SettingsPage
from ..core.settings import Settings
from ..core.archive import Archive, file_uid
from ..core.advisor import Usage
from ..core.paths import data_dir

NAV = [('analysis', '🔎', 'nav_analysis', PA.AnalysisPage), ('charts', '📈', 'nav_charts', PA.ChartsPage),
       ('map', '🗺', 'nav_map', PA.MapPage), ('timeline', '🕒', 'nav_timeline', PA.TimelinePage),
       ('advisor', '🤖', 'nav_advisor', PA.AdvisorPage), ('practice', '🎓', 'nav_practice', PA.PracticePage),
       ('scen', '🧪', 'nav_scen', PB.ScenarioPage), ('batch', '🗂', 'nav_batch', PB.BatchPage),
       ('archive', '🗄', 'nav_archive', PB.ArchivePage), ('msgs', '📘', 'nav_msgs', PB.MsgLibPage),
       ('params', '⚙', 'nav_params', PB.ParamLibPage), ('verify', '✅', 'nav_verify', PB.VerifyPage),
       ('settings', '🛠', 'nav_settings', SettingsPage)]


class MainWindow(QMainWindow):
    lan_merged = Signal(object, str)

    def __init__(self):
        super().__init__()
        self.settings = Settings(); set_lang(self.settings['lang'])
        self.archive = Archive()
        self.usage = Usage(os.path.join(data_dir(), 'ai_usage.json'))
        self.A = None; self.uid = None; self._cancel = False; self._half = False
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
        self.upd_bar = QProgressBar(); self.upd_bar.setVisible(False); self.upd_bar.setFixedWidth(560); sb.addWidget(self.upd_bar)
        sb.addWidget(QSizeGrip(sbw))
        v.addWidget(sbw)
        self.nav.setCurrentRow(0)
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
            from ..core import loader, analysis
            L = loader.load(path, progress=lambda f: w.progress.emit(('l', f)), cancel=lambda: self._cancel)
            w.progress.emit(('a', 0.0))
            A = analysis.Analysis(L)
            uid = file_uid(path)
            if archive:
                arc.add_analysis(uid, A, path, s['device_name'], s.get('archive_copy_logs', True), s.get('archive_copy_max_mb', 200))
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
        ai = QCheckBox(t('rep_ai')); ai.setChecked(bool(s.get('report_ai', True) and s.get('api_key') and s.get('online', True))); f.addRow(ai)
        mp = QCheckBox(t('rep_map')); mp.setChecked(bool(s.get('online', True))); f.addRow(mp)
        h = QHBoxLayout(); h.addWidget(button(t('cancel'), dl.reject)); h.addWidget(button(t('export'), dl.accept, primary=True)); f.addRow(h)
        if dl.exec() != QDialog.Accepted: return
        rl, fmt, tpl = lc.currentData(), fc.currentData(), tc.currentText()
        s['report_lang'] = rl; s['report_fmt'] = fmt; s['template'] = tpl; s['report_ai'] = ai.isChecked(); s.save()
        base = os.path.splitext(os.path.basename(self.A.L.path))[0] + f'_rapor_{rl}'
        ext = 'docx' if fmt == 'docx' else 'pdf'
        out, _ = QFileDialog.getSaveFileName(self, t('rep_title'), os.path.join(os.path.dirname(self.A.L.path), base + '.' + ext),
                                             'PDF (*.pdf)' if ext == 'pdf' else 'Word (*.docx)')
        if not out: return
        out = os.path.splitext(out)[0]
        A = self.A; uid = self.uid; lh = s['templates'].get(tpl) or s.letterhead(); use_ai = ai.isChecked(); online_map = mp.isChecked()
        arc = self.archive; dev = s['device_name']; key = s.get('api_key'); model = s.get('model'); effort = s.get('effort', 'medium'); usage = self.usage
        self.set_status(t('rep_creating'))
        pg = self.pages['analysis']; pg.set_busy(True, t('rep_creating')); pg.prog.setRange(0, 0)

        def job():
            from ..core import report
            from ..core.advisor import OnlineAdvisor
            ai_text = None
            if use_ai and key:
                try:
                    adv = OnlineAdvisor(A, key, model, rl, usage, effort)
                    ai_text = adv.ask('Write the expert commentary section of the official flight-log report: 1) overall assessment, '
                                      '2) what happened and when (key times), 3) root cause with evidence, 4) concrete recommendations '
                                      '(parameters, maintenance, training). Use short headings (#) and bullet points. Max ~450 words.')
                except Exception:
                    ai_text = None
            rd = report.ReportData(A, rl, ai_text, online_map, s.get('map_src', 'osm'))
            outs = []
            if fmt in ('pdf', 'both'):
                p = out + '.pdf'; report.build_pdf(rd, p, lh); outs.append((p, 'pdf'))
            if fmt in ('docx', 'both'):
                p = out + '.docx'; report.build_docx(rd, p, lh); outs.append((p, 'docx'))
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
            self.set_status(t('u_apply'))
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
        super().closeEvent(e)
