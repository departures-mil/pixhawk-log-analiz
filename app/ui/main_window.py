"""Ana pencere (ortak çekirdek fccore): çerçevesiz, her açılışta tam ekran; Falcon kenar çubuğu + üst çubuk
(Eşitle · Wi-Fi · Güncelle · tema · dil | Küçült · Orta · Tam ekran · Kapat)."""
from __future__ import annotations
import json, os, sys, time
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QFrame, QScrollArea,
                               QFileDialog, QDialog, QFormLayout, QComboBox, QCheckBox, QProgressBar, QLabel, QApplication)
from fccore import i18n as fi18n, icons as ficons
from fccore.window import FcWindow, TopBar
from fccore.widgets import button as fbutton, label as flabel, toast
from .i18n import t, lang, set_lang
from .common import label, button, run_bg, error, info, open_path, app_icon
from . import pages_a as PA, pages_b as PB, pages_c as PC, pages_p as PP, pages_s as PS, pages_v as PV, pages_q as PQ, pages_g as PG
from .settings_page import SettingsPage
from ..core.settings import Settings
from ..core.archive import Archive, file_uid
from ..core.advisor import Usage
from ..core.paths import data_dir

NAV = [('analysis', '🔎', 'nav_analysis', PA.AnalysisPage), ('solver', '🩺', 'nav_solver', PS.SolverPage), ('charts', '📈', 'nav_charts', PA.ChartsPage),
       ('map', '🗺', 'nav_map', PA.MapPage), ('logbrowser', '🧭', 'nav_logbrowser', PG.LogBrowserPage), ('custom', '📐', 'nav_custom', PV.CustomChartPage),
       ('video', '🎞', 'nav_video', PV.VideoPage), ('timeline', '🕒', 'nav_timeline', PA.TimelinePage),
       ('advisor', '🤖', 'nav_advisor', PA.AdvisorPage), ('practice', '🎓', 'nav_practice', PA.PracticePage),
       ('exam', '📝', 'nav_exam', PC.ExamPage), ('qbank', '🗃', 'nav_qbank', PQ.QBankPage),
       ('scen', '🧪', 'nav_scen', PB.ScenarioPage), ('crashlib', '💥', 'nav_crashlib', PP.CrashLibPage), ('batch', '🗂', 'nav_batch', PB.BatchPage),
       ('archive', '🗄', 'nav_archive', PB.ArchivePage), ('fleet', '🛩', 'nav_fleet', PC.FleetPage),
       ('pilots', '👨‍✈️', 'nav_pilots', PC.PilotsPage), ('msgs', '📘', 'nav_msgs', PB.MsgLibPage),
       ('params', '🧩', 'nav_params', PP.ParamCenterPage), ('verify', '✅', 'nav_verify', PB.VerifyPage),
       ('settings', '🛠', 'nav_settings', SettingsPage)]
# kenar çubuğu grupları (ilk anahtar → grup başlığı)
GROUPS = {'analysis': 'px.grp.analysis', 'practice': 'px.grp.learn', 'batch': 'px.grp.records', 'msgs': 'px.grp.library', 'verify': 'px.grp.system'}


def _upper(s):
    l = lang()
    if l == 'ar': return s
    if l == 'tr': s = s.replace('i', 'İ').replace('ı', 'I')
    return s.upper()


class MainWindow(FcWindow):
    lan_merged = Signal(object, str)
    crashed = Signal(str)
    open_req = Signal(str)

    def __init__(self, settings=None, core=None):
        super().__init__('Pixhawk Log Analiz')
        self.settings = settings or Settings(); set_lang(self.settings['lang'])
        self.core = core
        self.archive = Archive()
        self.usage = Usage(os.path.join(data_dir(), 'ai_usage.json'))
        self.A = None; self.uid = None; self._cancel = False
        self.role = 'admin'; self.user_name = ''
        self._apply_core_settings()
        self.crashed.connect(self._on_crash); self.open_req.connect(self._open_req)
        self.setWindowIcon(app_icon())
        self.lan_merged.connect(self._lan_merged)
        self._shell()
        self.build()
        fi18n.on_change(self._core_lang)
        # LAN eşitleme sunucusu (aynı modemdeki cihazlar için)
        try:
            from ..core.sync import LanServer
            self.lan = LanServer(self.settings, self.archive, on_merged=lambda r, n: self.lan_merged.emit(r, n)); self.lan.start()
        except Exception:
            self.lan = None
        self._draw_sync_state()
        # Mission Planner log klasörü izleme
        self.watcher = None; self.wtimer = QTimer(self); self.wtimer.setInterval(5000); self.wtimer.timeout.connect(self._watch_tick)
        self.setup_watch()
        QTimer.singleShot(9000, self._flush_feedback)

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
            self.nav_btns[i].setHidden(k in hid)
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
        if self.isMinimized(): self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_(); self.activateWindow()
        if p and os.path.isfile(p): self.open_log(p)

    def _flush_feedback(self):
        """İnternetsizken sıraya alınmış teşhis geri bildirimlerini arka planda gönder."""
        try:
            from ..core import feedback
            from .common import run_bg
            run_bg(feedback.flush)
        except Exception:
            pass

    # ------------------------------------------------------------ çökme raporu (fccore.crash gönderir)
    def _on_crash(self, path):
        try: toast(fi18n.t('px.crash.toast'), 'error', 7000)
        except Exception: pass
        self.set_status(fi18n.t('px.crash.toast'))

    # ------------------------------------------------------------ kabuk (bir kez)
    def _shell(self):
        lay = QHBoxLayout(self.root); lay.setSizeConstraint(QHBoxLayout.SetNoConstraint)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        # kenar çubuğu
        self.sidebar = QFrame(); self.sidebar.setObjectName('fcSidebar'); self.sidebar.setFixedWidth(264)
        sv = QVBoxLayout(self.sidebar); sv.setContentsMargins(0, 0, 0, 0); sv.setSpacing(0)
        brand = QFrame(); brand.setObjectName('fcBrand')
        bl = QHBoxLayout(brand); bl.setContentsMargins(20, 22, 20, 18); bl.setSpacing(12)
        logo = QLabel(); logo.setObjectName('fcBrandLogo'); logo.setFixedSize(38, 38); logo.setAlignment(Qt.AlignCenter)
        logo.setText('PX'); logo.setStyleSheet('color:white;font-weight:800;font-size:14px')
        names = QVBoxLayout(); names.setSpacing(2)
        self.brand_name = flabel('', obj='fcBrandName', wrap=True); self.brand_tag = flabel('', obj='fcBrandTag', wrap=True)
        names.addWidget(self.brand_name); names.addWidget(self.brand_tag)
        from ..version import VERSION
        bl.addWidget(logo, 0, Qt.AlignTop); bl.addLayout(names, 1)
        bl.addWidget(flabel('v' + VERSION, 'version-badge'), 0, Qt.AlignTop)
        sv.addWidget(brand)
        self.nav_scroll = QScrollArea(); self.nav_scroll.setObjectName('fcNavScroll'); self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setFrameShape(QFrame.NoFrame); self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sv.addWidget(self.nav_scroll, 1)
        lay.addWidget(self.sidebar)
        # ana sütun: üst çubuk + sayfalar + durum çubuğu
        main = QWidget(); mv = QVBoxLayout(main); mv.setContentsMargins(0, 0, 0, 0); mv.setSpacing(0)
        self.topbar = TopBar(self)
        self.topbar.h.setContentsMargins(24, 12, 16, 12)
        self.q_open = fbutton('📂', 'icon-btn', slot=lambda: self.pick_log())
        self.q_info = fbutton('✈', 'icon-btn', slot=lambda: self.edit_flight_info())
        self.q_solve = fbutton('🩺', 'icon-btn', slot=lambda: self.goto('solver'))
        self.q_rep = fbutton('📄', 'icon-btn', slot=lambda: self.export_report())
        self.q_cut = fbutton('✂', 'icon-btn', slot=lambda: self.cut_log())
        try: self.q_cut.setToolTip(t('cut_tip'))
        except Exception: pass
        quick = [self.q_open, self.q_info, self.q_cut, self.q_solve, self.q_rep]
        upd = self.core.updates if self.core is not None else None
        self.topbar.mount(sync={'on_click': lambda st: self.do_sync()}, lan={'on_click': lambda st: self.do_lan()},
                          update=upd, before=quick)
        mv.addWidget(self.topbar)
        self.stack_host = QWidget(); self.stack_l = QVBoxLayout(self.stack_host); self.stack_l.setContentsMargins(0, 0, 0, 0)
        mv.addWidget(self.stack_host, 1)
        sbw = QWidget(); sbw.setObjectName('statusbar'); sbw.setAttribute(Qt.WA_StyledBackground, True)
        sb = QHBoxLayout(sbw); sb.setContentsMargins(14, 3, 14, 3)
        self.status = QLabel(''); sb.addWidget(self.status, 1)
        self.mp_btn = button('', self._mp_open, primary=True); self.mp_btn.setVisible(False); sb.addWidget(self.mp_btn)
        self.upd_bar = QProgressBar(); self.upd_bar.setObjectName('appbar'); self.upd_bar.setVisible(False); self.upd_bar.setFixedWidth(560)
        sb.addWidget(self.upd_bar)
        mv.addWidget(sbw)
        lay.addWidget(main, 1)
        self.titlebar = self   # eski kod uyumu: self.titlebar.set_log(...)

    # ------------------------------------------------------------ sayfalar (dil değişince yeniden)
    def build(self):
        self.setWindowTitle(t('app'))
        self.brand_name.setText(t('app')); self.brand_tag.setText(fi18n.t('px.tag'))
        old_nav = self.nav_scroll.takeWidget()
        nav = QWidget(); nav.setObjectName('fcNav'); nl = QVBoxLayout(nav); nl.setContentsMargins(12, 12, 12, 20); nl.setSpacing(2)
        old_stack = getattr(self, 'stack', None)
        self.stack = QStackedWidget(); self.stack.setObjectName('fcPages')
        self.pages = {}; self.keys = []; self.nav_btns = []; self._grp_lbl = {}
        for key, ic, tk, cls in NAV:
            if key in GROUPS:
                if self.keys: nl.addSpacing(10)
                g = flabel(_upper(fi18n.t(GROUPS[key])), 'nav-title')
                nl.addWidget(g); self._grp_lbl[key] = g
            b = fbutton(f'{ic}   ' + t(tk).replace('&', '&&'), 'nav-item'); b.setCheckable(True); b.setFocusPolicy(Qt.NoFocus)
            idx = len(self.keys); b.clicked.connect(lambda _=False, i=idx: self.setCurrentRow(i))
            nl.addWidget(b); self.nav_btns.append(b)
            p = cls(self); self.pages[key] = p; self.keys.append(key); self.stack.addWidget(p)
        nl.addStretch(1)
        self.nav_scroll.setWidget(nav)
        if old_nav is not None: old_nav.deleteLater()
        self.stack_l.addWidget(self.stack)
        if old_stack is not None:
            self.stack_l.removeWidget(old_stack); old_stack.deleteLater()
        self.q_open.setToolTip(t('open_log')); self.q_info.setToolTip(t('fi_title')); self.q_solve.setToolTip(t('nav_solver'))
        self.q_rep.setToolTip(t('export'))
        self._row = -1
        self.setCurrentRow(0)
        self.apply_role()
        if self.A:
            for p in self.pages.values():
                try: p.on_analysis(self.A)
                except Exception: pass
            self.set_log(self.A, (self.A.info or {}).get('crashed', ''))

    def _core_lang(self, l):
        """Üst çubuktaki / Ayarlar'daki dil düğmesi (fccore) → uygulama dili."""
        if l != self.settings.get('lang'):
            self.settings['lang'] = l; self.settings.save()
        if l != lang():
            self.apply_lang()

    def apply_lang(self):
        set_lang(self.settings['lang'])
        if fi18n.lang() != self.settings['lang']:
            fi18n.set(self.settings['lang'])      # _core_lang tekrar çağrılır; lang() artık eşit
            return
        cur = max(0, self._row)
        self.build()
        self.setCurrentRow(cur)
        self.set_status(t('restart_lang'))

    # eski QListWidget arayüzü (nav.currentRow / setCurrentRow / item(i).setHidden)
    def setCurrentRow(self, i):
        if i < 0 or i >= len(self.keys): return
        self._row = i
        for k, b in enumerate(self.nav_btns): b.setChecked(k == i)
        self.stack.setCurrentIndex(i)
        key = self.keys[i]
        self.topbar.set_title(t(NAV[i][2]), self._loginfo if getattr(self, '_loginfo', '') else '')
        try: self.stack.currentWidget().on_show()
        except Exception: pass

    def currentRow(self):
        return self._row

    def _nav(self, i):
        self.setCurrentRow(i)

    def goto(self, key):
        self.setCurrentRow(self.keys.index(key))

    def set_status(self, s):
        self.status.setText(s)

    def set_log(self, A=None, crash_mark=''):
        """Üst çubuk alt başlığı: dosya · araç · karar · puan (eski başlık çubuğundaki log bilgisi)."""
        if A is None:
            self._loginfo = ''
        else:
            from ..core import texts
            v = texts.vkey(A.verdict)
            icon = {'crash': '💥', 'incident': '⚠', 'incident_minor': 'ℹ', 'normal': '✅', 'noflight': '⏸'}.get(v, '')
            mark = '  ·  💥 ' + t('fi_crash_mark') if crash_mark == 'yes' and v != 'crash' else ''
            self._loginfo = f"{os.path.basename(A.L.path)}  ·  {A.vehicle}  ·  {icon} {texts.T('v_' + v, lang())}  ·  {A.overall}/100{mark}"
            c = getattr(A.L, 'cut', None)
            if c:
                from ..core import logcut
                self._loginfo += f"  ·  ✂ {logcut.fmt(c['t0'])}–{logcut.fmt(c['t1'])}"
        if self._row >= 0: self.topbar.set_title(t(NAV[self._row][2]), self._loginfo)

    # ----------------------------------------------------- pencere düğmeleri
    def show_start(self):
        self.start()

    # ------------------------------------------------------------ log açma
    def pick_log(self):
        p, _ = QFileDialog.getOpenFileName(self, t('open_log'), '', 'Pixhawk log (*.bin *.BIN *.tlog *.log);;All (*.*)')
        if p: self.open_log(p)

    def cancel_load(self):
        self._cancel = True

    def open_log(self, path, archive=True, info=None):
        """1) logu oku + offline tahmin  2) uçuş bilgileri formu (cevaplar)  3) analiz (derin inceleme) ve arşiv."""
        self.goto('analysis')
        pg = self.pages['analysis']; pg.set_busy(True, t('loading')); self._cancel = False
        s = self.settings
        w = None

        def job():
            from ..core import loader, crash, security, flightinfo as FI
            crash.note('open ' + os.path.basename(path))
            real = path
            if path.lower().endswith('.pxloc'): real = security.open_local_file(path)
            L = loader.load(real, progress=lambda f: w.progress.emit(('l', f)), cancel=lambda: self._cancel)
            det, src = FI.detect(L)
            return L, real, det, src

        def prog(x):
            k, f = x
            if k == 'l': pg.set_progress(f, t('loading'))
            else: pg.set_progress(1.0, t('analyzing'))

        def loaded(r):
            L, real, det, src = r
            from ..core import flightinfo as FI
            uid = file_uid(real)
            old = self.archive.get(uid) or {}
            prev = {}
            try: prev = json.loads(old.get('info') or '{}')
            except Exception: pass
            last = {k: v for k, v in (s.get('fi_last') or {}).items() if k in FI.STICKY}
            ans = {**last, **det, **prev, **(info or {})}
            srcs = {**{k: 'prev' for k in last}, **src, **{k: 'prev' for k in prev}}
            if info is None and FI.conf(s)['ask']:
                from .flightform import FlightInfoDialog
                dl = FlightInfoDialog(self, ans, srcs, L=L)
                if dl.exec() and not dl.skipped: ans = dl.values()
            s['fi_last'] = {k: v for k, v in ans.items() if k in FI.STICKY}; s.save()
            cut = (s.get('log_cuts') or {}).get(uid)
            if cut:                                   # bu log daha önce kesildi: aynı aralıkla aç (✂ Geri getir ile tamamı)
                try:
                    from ..core import logcut
                    L = logcut.crop(L, float(cut[0]), float(cut[1]))
                except Exception as e:
                    print('cut', e)
            self._analyze(L, real, uid, ans, path, archive)

        def fail(e):
            pg.set_busy(False); error(self, e)
        w = run_bg(job, on_done=loaded, on_fail=fail, on_progress=prog)

    def _analyze(self, L, real, uid, info, path, archive=True):
        pg = self.pages['analysis']; pg.set_busy(True, t('analyzing')); pg.set_progress(1.0, t('analyzing'))
        s = self.settings; arc = self.archive

        def job():
            from ..core import analysis, crash
            A = analysis.Analysis(L, info=info)
            if archive:
                arc.add_analysis(uid, A, real, s['device_name'], s.get('archive_copy_logs', True), s.get('archive_copy_max_mb', 200),
                                 encrypt=bool(s.get('encrypt_local')))
                try:
                    from ..core import fleet, anomaly
                    fleet.ensure_aircraft(arc, A)
                    anomaly.learn(A, uid)
                    from ..core import baseline
                    baseline.compare(A, arc, uid)
                except Exception as e:
                    crash.note(f'fleet/anomaly: {e}')
            if s.get('online', True) and s.get('weather_online', True):
                try:
                    from ..core import weather
                    weather.for_analysis(A)
                except Exception:
                    pass
            return A, uid

        def ok(r):
            pg.set_busy(False)
            self.A, self.uid = r
            for p in self.pages.values():
                try: p.on_analysis(self.A)
                except Exception as e: print('page', p, e)
            self.titlebar.set_log(self.A, (self.A.info or {}).get('crashed', ''))
            self.set_status(f'{os.path.basename(path)} · {t("saved_archive") if archive else ""}')

        def fail(e):
            pg.set_busy(False); error(self, e)
        run_bg(job, on_done=ok, on_fail=fail)

    def edit_flight_info(self):
        """Açık logun uçuş bilgilerini düzenle ve yeniden incele."""
        if not self.A: return error(self, t('no_log'))
        from .flightform import FlightInfoDialog
        dl = FlightInfoDialog(self, dict(self.A.info or {}), {}, L=self.A.L)
        if not dl.exec() or dl.skipped: return
        self._analyze(self.A.L, self.A.L.path, self.uid, dl.values(), self.A.L.path, archive=True)

    # ------------------------------------------------------------- ✂ kes
    def cut_log(self):
        """Logun yalnız çalışılacak aralığını incele; kesilen kısım saklanır, analizden ve grafiklerden çıkar."""
        if not self.A: return error(self, t('no_log'))
        from ..core import logcut
        from .logcut_dlg import LogCutDialog
        L = self.A.L; full = logcut.restore(L)
        cur = (L.cut['t0'], L.cut['t1']) if logcut.is_cut(L) else None
        dl = LogCutDialog(self, full, cur=cur)
        if not dl.exec() or dl.result_range is None: return
        s = self.settings; cuts = dict(s.get('log_cuts') or {})
        if dl.result_range == 'restore':
            cuts.pop(self.uid, None); newL = full
        else:
            a, b = dl.result_range; newL = logcut.crop(full, a, b)
            if dl.rem.isChecked() and self.uid: cuts[self.uid] = [round(a, 2), round(b, 2)]
            else: cuts.pop(self.uid, None)
        s['log_cuts'] = cuts; s.save()
        self._analyze(newL, full.path, self.uid, dict(self.A.info or {}), full.path, archive=True)

    def restore_log(self):
        if not self.A: return
        from ..core import logcut
        if not logcut.is_cut(self.A.L): return
        s = self.settings; cuts = dict(s.get('log_cuts') or {}); cuts.pop(self.uid, None); s['log_cuts'] = cuts; s.save()
        full = logcut.restore(self.A.L)
        self._analyze(full, full.path, self.uid, dict(self.A.info or {}), full.path, archive=True)

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

    # --------------------------------------------------------- güncelleme (fccore: latest.json + yama + SHA-256)
    def do_update(self, silent=False):
        """Ayarlar'daki "Güncellemeleri denetle": üst çubuktaki Güncelle düğmesiyle aynı akış."""
        ctl = self.core.updates if self.core is not None else None
        if ctl is None: return
        if ctl.state.get('status') == 'available' and not silent:
            ctl.run()
        else:
            self.topbar.show_result = not silent
            ctl.check(silent=silent)

    # ----------------------------------------------------------- eşitleme
    def _draw_sync_state(self, st=None):
        s = self.settings
        if st is None:
            st = 'idle' if (s.get('gh_token') or '').strip() else 'off'
        self.topbar.set_sync(st)
        self.topbar.set_lan('on' if self.lan is not None else 'off')

    def do_sync(self, after=None):
        from ..core import sync
        s = self.settings
        if not (s.get('gh_token') or '').strip():
            info(self, t('sync_need')); self.goto('settings'); return
        self.set_status('⇅ …'); self.topbar.set_sync('syncing')

        def ok(r):
            a, u, rl = r
            self.set_status(t('s_synced', a=a, u=u) + (('  ·  ' + t('s_rate', r=rl.get('remaining'), l=rl.get('limit'))) if rl.get('limit') else ''))
            self._draw_sync_state('idle')
            self.pages['archive'].refresh()
            if after: after()

        def fail(e):
            self.set_status(''); self._draw_sync_state('error'); error(self, e)
        run_bg(sync.github_sync, s, self.archive, on_done=ok, on_fail=fail)

    def do_lan(self, on_done=None):
        """Wi-Fi düğmesi: aynı ağdaki cihazları bul ve hepsiyle eşitle (kayıtlar silinmeden birleştirilir)."""
        from ..core import sync
        s = self.settings; a = self.archive
        self.topbar.set_lan('busy'); self.set_status(fi18n.t('fc.lan.busy'))

        def job():
            peers = sync.discover(s)
            res = []
            for p in peers:
                try: res.append((p['name'], sync.lan_sync_with(s, a, p)))
                except Exception as e: res.append((p['name'], str(e)))
            return res

        def ok(res):
            self._draw_sync_state()
            if not res:
                msg = t('s_lan_none')
            else:
                msg = '\n'.join(f'{n}: ' + (t('s_synced', a=r[0], u=r[1]) if isinstance(r, tuple) else r) for n, r in res)
                try: self.pages['archive'].refresh()
                except Exception: pass
            self.set_status(msg.replace('\n', '  ·  '))
            if on_done: on_done(msg)

        def fail(e):
            self._draw_sync_state(); self.set_status(e)
            if on_done: on_done(e)
        run_bg(job, on_done=ok, on_fail=fail)

    def _lan_merged(self, r, name):
        self.set_status(t('lan_merged', n=name, a=r[0], u=r[1]))
        try: self.pages['archive'].refresh()
        except Exception: pass

    def closeEvent(self, e):
        if self.lan: self.lan.stop = True
        self.wtimer.stop()
        super().closeEvent(e)
