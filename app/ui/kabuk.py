"""Ortak çekirdek (fccore) yapıştırıcısı: depo, dil köprüsü, 'klasik' şema (v1.0.x renkleri), uygulama QSS'i,
açık temada HTML renk eşlemesi, güncelleme (win-app + win-setup), çökme raporu, neler yeni, ilk açılış rehberi."""
from __future__ import annotations
import os, re, subprocess, sys, weakref


from fccore import i18n as fi18n, storage, style, usage as fusage

from ..version import VERSION
from ..core.paths import data_dir

REPO = 'pixhawk-log-analiz'
CORE_APP = 'pixhawk-log-analiz'
SETUP_ARGS = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/CLOSEAPPLICATIONS']
INNO_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8C3F7B2E-5A1D-4E7B-9C2F-6D1A0B4E3F21}_is1'

from ..news import NEWS, notes_for  # noqa: E402,F401


# ---------------------------------------------------------------- klasik şema (v1.0.x renkleri)
KLASIK_DARK = {
    'bg': '#0F172A', 'bg-grid': '#00000000', 'panel': '#111C33', 'panel-solid': '#111C33', 'panel-hover': '#1E293B',
    'border': '#1E293B', 'border-strong': '#334155', 'text': '#E2E8F0', 'muted': '#94A3B8', 'label': '#CBD5E1',
    'nav-text': '#CBD5E1', 'nav-title': '#64748B', 'accent': '#3B82F6', 'accent-2': '#1D4ED8', 'on-accent': '#FFFFFF',
    'primary-1': '#2563EB', 'primary-2': '#1D4ED8', 'active-1': '#2563EB59', 'active-2': '#2563EB26', 'active-line': '#3B82F680',
    'accent-soft': '#2563EB1F', 'accent-line': '#3B82F659', 'focus': '#3B82F6', 'focus-ring': '#3B82F633',
    'sidebar-bg': '#0B1222', 'topbar-bg': '#0B1222', 'modal-bg': '#0F172A', 'modal-border': '#334155',
    'bar-track': '#1E293B', 'scroll-thumb': '#334155', 'glow-1': '#00000000', 'glow-2': '#00000000',
}
KLASIK_LIGHT = {
    'bg': '#F1F5F9', 'bg-grid': '#00000000', 'panel': '#FFFFFF', 'panel-solid': '#FFFFFF', 'panel-hover': '#E2E8F0',
    'border': '#CBD5E1', 'border-strong': '#94A3B8', 'text': '#0F172A', 'muted': '#475569', 'label': '#1E3A8A',
    'nav-text': '#334155', 'nav-title': '#64748B', 'accent': '#2563EB', 'accent-2': '#1D4ED8', 'on-accent': '#FFFFFF',
    'primary-1': '#2563EB', 'primary-2': '#1D4ED8', 'active-1': '#2563EB26', 'active-2': '#2563EB0D', 'active-line': '#2563EB59',
    'accent-soft': '#2563EB14', 'accent-line': '#2563EB40', 'focus': '#2563EB', 'focus-ring': '#2563EB26',
    'sidebar-bg': '#E2E8F0', 'topbar-bg': '#F8FAFC', 'modal-bg': '#FFFFFF', 'modal-border': '#CBD5E1',
    'bar-track': '#E2E8F0', 'scroll-thumb': '#94A3B8', 'glow-1': '#00000000', 'glow-2': '#00000000',
}
KLASIK_LABEL = {'tr': 'Klasik (eski görünüm)', 'en': 'Classic (previous look)', 'ar': 'الكلاسيكي (المظهر السابق)'}


# ---------------------------------------------------------------- uygulamaya özgü QSS (eski objectName'ler)
def app_qss(sid=None, mode=None):
    T = style.scheme_tokens(sid, mode)
    q = style.q
    s = style.scale()

    def px(n):
        return '%dpx' % round(n * s)
    grad = 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 %s, stop:1 %s)' % (q(T['primary-1']), q(T['primary-2']))
    return '''
QPushButton#primary {{ color: {onacc}; background: {grad}; border-color: transparent; font-weight: 600; }}
QPushButton#primary:hover {{ border-color: {focus}; }}
QLabel#h1 {{ font-size: {h1}; font-weight: 700; }}
QLabel#h2 {{ font-size: {h2}; font-weight: 600; color: {label}; }}
QLabel#muted {{ color: {muted}; }}
QWidget#page, QWidget#root {{ background: transparent; }}
QWidget#statusbar {{ background: {topbar}; border-top: 1px solid {border}; }}
QWidget#statusbar QLabel {{ color: {muted}; }}
QProgressBar#appbar {{ min-height: {pbh}; max-height: {pbh}; border-radius: 6px; color: {text}; font-size: {fs12}; }}
QProgressBar#appbar::chunk {{ border-radius: 6px; }}
QScrollArea#fcNavScroll {{ background: transparent; border: 0; }}
QWidget#fcNav {{ background: transparent; }}
QLabel#pxLogInfo {{ color: {muted}; }}
QPushButton[fc~="nav-item"] {{ padding-top: {navp}; padding-bottom: {navp}; }}
QLabel#fcBrandName {{ font-size: {brand}; }}
'''.format(onacc=q(T['on-accent']), grad=grad, focus=q(T['focus']), h1=px(20), h2=px(15), label=q(T['label']), muted=q(T['muted']),
           topbar=q(T['topbar-bg']), navp=px(7), brand=px(15), border=q(T['border']), text=q(T['text']), pbh=px(18), fs12=px(12))


_orig_qss = style.qss


def _qss(sid=None, mode=None, sc=None, rtl=None):
    return _orig_qss(sid, mode, sc, rtl) + app_qss(sid, mode)


# ---------------------------------------------------------------- açık temada eski (koyu) HTML renkleri
LIGHT_MAP = {
    '#F8FAFC': '#0F172A', '#E2E8F0': '#1E293B', '#CBD5E1': '#334155', '#94A3B8': '#475569', '#93C5FD': '#1D4ED8',
    '#60A5FA': '#2563EB', '#A5B4FC': '#4338CA', '#FBBF24': '#B45309', '#86EFAC': '#15803D', '#4ADE80': '#15803D',
    '#F87171': '#B91C1C', '#111C33': '#F1F5F9', '#0F1A30': '#FFFFFF', '#1E1B2E': '#FFF1F2', '#0F172A': '#FFFFFF',
    '#162238': '#E2E8F0', '#1E293B': '#E2E8F0',
}
_HEX = re.compile(r'#[0-9A-Fa-f]{6}\b')
_html_widgets = weakref.WeakSet()


def themed_html(h):
    if not isinstance(h, str) or style.effective() != 'light':
        return h
    return _HEX.sub(lambda m: LIGHT_MAP.get(m.group(0).upper(), m.group(0)), h)


def _patch_html():
    from PySide6.QtWidgets import QTextEdit, QTextBrowser
    if getattr(QTextEdit, '_px_patched', False):
        return
    orig = {c: c.setHtml for c in (QTextEdit, QTextBrowser)}

    def make(cls_):
        o = orig[cls_]

        def setHtml(self, h):
            try:
                self._px_src = h
                _html_widgets.add(self)
            except Exception:
                pass
            return o(self, themed_html(h))
        return setHtml

    def forget(name, cls_):
        o = getattr(cls_, name)

        def f(self, *a, **k):
            try:
                self._px_src = None
            except Exception:
                pass
            return o(self, *a, **k)
        return f
    for c in (QTextEdit, QTextBrowser):
        c.setHtml = make(c)
        for n in ('setPlainText', 'setMarkdown', 'clear', 'append', 'insertHtml', 'insertPlainText'):
            setattr(c, n, forget(n, c))
    QTextEdit._px_patched = True

    def reapply(_st):
        for w in list(_html_widgets):
            try:
                src = getattr(w, '_px_src', None)
                if src:
                    orig[QTextBrowser if isinstance(w, QTextBrowser) else QTextEdit](w, themed_html(src))
            except RuntimeError:
                pass
    style.on_change(reapply)


# ---------------------------------------------------------------- uygulama metinleri (fccore sözlüğüne)
TEXTS = {
    'tr': {'px.tag': 'ArduPilot uçuş logu analizi', 'px.grp.analysis': 'Analiz', 'px.grp.learn': 'Eğitim', 'px.grp.records': 'Kayıtlar',
           'px.grp.library': 'Kütüphane', 'px.grp.system': 'Sistem', 'fc.ai.pollinations.note': 'Anahtarsız ücretsiz model (Pollinations)',
           'px.crash.toast': 'Beklenmeyen bir hata oldu; ayarlarda izin verdiyseniz yöneticiye bildirildi.',
           'px.sync.backup': 'Eşitleme yedeği: {n} kayıt (çakışmada kaybeden ya da uzaktan silinip arşivlenen)',
           'px.sync.export': 'Yedeği dışa aktar (JSON)', 'px.sync.saved': 'Yedek kaydedildi: {p}',
           'px.auto_upd': 'Program açılırken güncellemeleri denetle'},
    'en': {'px.tag': 'ArduPilot flight log analysis', 'px.grp.analysis': 'Analysis', 'px.grp.learn': 'Training', 'px.grp.records': 'Records',
           'px.grp.library': 'Library', 'px.grp.system': 'System', 'fc.ai.pollinations.note': 'Free model without a key (Pollinations)',
           'px.crash.toast': 'An unexpected error occurred; it was reported to the administrator if you allowed it in settings.',
           'px.sync.backup': 'Sync backup: {n} records (conflict losers or remotely deleted and archived)',
           'px.sync.export': 'Export backup (JSON)', 'px.sync.saved': 'Backup saved: {p}',
           'px.auto_upd': 'Check for updates when the program starts'},
    'ar': {'px.tag': 'تحليل سجلات طيران ArduPilot', 'px.grp.analysis': 'التحليل', 'px.grp.learn': 'التدريب', 'px.grp.records': 'السجلات',
           'px.grp.library': 'المكتبة', 'px.grp.system': 'النظام', 'fc.ai.pollinations.note': 'نموذج مجاني بلا مفتاح (Pollinations)',
           'px.crash.toast': 'حدث خطأ غير متوقع؛ أُبلغ المسؤول إن سمحت بذلك في الإعدادات.',
           'px.sync.backup': 'نسخة المزامنة الاحتياطية: {n} سجل (الخاسر عند التعارض أو المحذوف عن بُعد والمؤرشف)',
           'px.sync.export': 'تصدير النسخة الاحتياطية (JSON)', 'px.sync.saved': 'حُفظت النسخة الاحتياطية: {p}',
           'px.auto_upd': 'التحقق من التحديثات عند بدء البرنامج'},
}


# ---------------------------------------------------------------- güncelleme: kurulum exe'si sessiz + yeniden aç
def _spawn(staging):
    def spawn(args):
        from fccore.updater import _spawn_detached
        exe = args[0] if args else ''
        if len(args) == 1 and exe.lower().endswith('.exe') and sys.platform.startswith('win'):
            # Inno Setup: program kapanınca sessiz kurulum, sonra kurulu programı aç (eski güncelleyiciyle aynı akış)
            target = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'), 'Programs', 'Pixhawk Log Analiz', 'PixhawkLogAnaliz.exe')
            if getattr(sys, 'frozen', False) and os.path.isfile(os.path.join(os.path.dirname(sys.executable), 'PixhawkLogAnaliz.exe')):
                target = sys.executable
            pid = os.getpid()
            log = os.path.join(staging, 'setup.log')
            body = ('@echo off\r\n:bekle\r\ntasklist /FI "PID eq %d" 2>NUL | find "%d" >NUL && (ping -n 2 127.0.0.1 >NUL & goto bekle)\r\n'
                    'start "" /wait "%s" %s /LOG="%s"\r\nstart "" "%s" --fc-updated\r\n(goto) 2>NUL & del "%%~f0"\r\n') % (
                pid, pid, exe, ' '.join(SETUP_ARGS), log, target)
            script = os.path.join(staging, 'kurulum.cmd')
            with open(script, 'w', encoding='mbcs' if os.name == 'nt' else 'utf-8') as f:
                f.write(body)
            return subprocess.Popen(['cmd.exe', '/c', script], cwd=staging, close_fds=True, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000 | 0x00000200)
        # takas betiği: çalışma klasörü kurulum klasörü olmasın (klasör taşınabilsin). DETACHED_PROCESS KULLANMA: konsolsuz cmd'de
        # tasklist/find/ping her biri ayrı pencere açıyor, Windows Terminal varsayılanken `find` takılıp güncelleme bitmiyordu
        # (v1.1.4 → v1.1.5). fccore'un gizli konsollu başlatıcısı kullanılır.
        return _spawn_detached(args, cwd=staging)
    return spawn


def _mark_installed_version():
    """win-app güncellemesinden sonra Denetim Masası'ndaki sürümü düzelt (Inno kaydı varsa)."""
    if not (sys.platform.startswith('win') and getattr(sys, 'frozen', False)):
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, INNO_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
            cur = winreg.QueryValueEx(k, 'DisplayVersion')[0]
            if cur != VERSION:
                winreg.SetValueEx(k, 'DisplayVersion', 0, winreg.REG_SZ, VERSION)
    except OSError:
        pass


# ---------------------------------------------------------------- kurulum
class Core:
    updates = None


def init(app, settings, auto_update=True):
    """storage → dil → şemalar/QSS → iletişim → çökme → güncelleme → neler yeni. Döner: Core."""
    from fccore import contact, crash as fcrash, whatsnew, onboarding
    old_user = os.path.isfile(settings.path)
    storage.use(data_dir())
    fi18n.add(TEXTS)
    # dil: uygulamanın ayarı esas (eski kullanıcı), çekirdek deposuna da yaz
    fi18n.set(settings.get('lang') or fi18n.detect())
    style.qss = _qss
    style.register_scheme('klasik', dark=KLASIK_DARK, light=KLASIK_LIGHT, label=KLASIK_LABEL)
    style.install(app)
    _patch_html()
    # kullanım limitleri: ücretsiz (anahtarsız) sağlayıcı da listelensin
    fusage.PROVIDERS.setdefault('pollinations', {'name': 'Pollinations (ücretsiz)', 'limits': 'https://pollinations.ai',
                                                 'host': re.compile(r'pollinations\.ai')})
    # ilk açılış rehberi yalnız uygulamanın desteklediği sağlayıcıları sunsun
    for k in ('openai', 'groq'):
        onboarding.AI.pop(k, None)
    contact.init(app=CORE_APP, version=VERSION)
    from ..core import crash as appcrash
    fcrash.init(app=CORE_APP, version=VERSION, send=appcrash.send_core)
    core = Core()
    core.version = VERSION
    from fccore.updater import Updater, confirm_started
    from fccore.update_ui import UpdateController
    staging = os.path.join(data_dir(), 'guncelleme')
    os.makedirs(staging, exist_ok=True)
    u = Updater(repo=REPO, app=CORE_APP, version=VERSION, channel='win-app', setup_channel='win-setup', staging=staging,
                spawn=_spawn(staging), setup_args=None)   # Inno kurulumu: sessiz kurulum + yeniden açma _spawn'da (SETUP_ARGS)
    if getattr(sys, 'frozen', False) and not _installed_dir(os.path.dirname(sys.executable)):
        u.cfg['channel'] = 'win-exe'          # taşınabilir tek exe
    confirm_started(staging, VERSION)
    core.updates = UpdateController(u)
    if auto_update:
        core.updates.start(interval_hours=6, first_delay_ms=4000)
    _mark_installed_version()
    if old_user and not storage.get('whatsnew.seen'):
        # v1.0.x'ten gelen kullanıcı: "neler yeni" gösterilsin, ilk açılış rehberi kendiliğinden açılmasın
        # (Ayarlar → Hakkında → "Rehberi yeniden aç" ile her zaman açılabilir)
        storage.set('whatsnew.seen', '1.0.0')
        storage.set('onboarding.done', True)
    core.whatsnew_shown = whatsnew.start(VERSION, notes=notes_for)
    core.onboarding = {'firebase': False, 'ai': True, 'on_ai': lambda v: _on_ai(settings, v)}
    return core


def _installed_dir(d):
    """PyInstaller one-dir kurulumu mu? (_internal klasörü exe'nin yanında)"""
    return os.path.isdir(os.path.join(d, '_internal'))


def _on_ai(settings, v):
    p, k = (v or {}).get('provider'), ((v or {}).get('key') or '').strip()
    if not k:
        return
    if p == 'gemini':
        settings['gemini_key'] = k; settings['ai_provider'] = 'gemini'
    elif p == 'anthropic':
        settings['api_key'] = k; settings['ai_provider'] = 'anthropic'
    settings.save()


def after_show(core, parent=None):
    from PySide6.QtCore import QTimer
    failed = [a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--fc-update-failed=')]
    if failed:
        from fccore.widgets import toast
        QTimer.singleShot(1200, lambda: toast(fi18n.t('fc.update.failed', {'e': 'v' + failed[0]}), 'error', 9000))
    if not core.whatsnew_shown:
        from fccore import onboarding as ob
        QTimer.singleShot(700, lambda: ob.maybe_start(**core.onboarding))
