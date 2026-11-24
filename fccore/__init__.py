"""fccore — Ortak Çekirdek'in Python/PySide6 sürümü (web/Electron çekirdeğiyle aynı görünüm, metin ve kurallar).

    import fccore
    from fccore.window import FcWindow, Shell
    app = QApplication(sys.argv)
    core = fccore.init(app, app_id='organizer', repo='organizer', version='2.2.0', announcements=True)
    win = FcWindow('Organizer'); shell = Shell(win, name='Organizer', tag='…', version='2.2.0')
    ...
    shell.topbar.mount(sync={...}, lan={...}, update=core.updates, before=[core.ann.button()])
    win.start(); core.after_show()
"""
import os
import sys

__version__ = '1.0.0'
WEB_CORE = '87f42f8+ebec004'   # eşlenen web çekirdeği (metinler/tokenlar tools/gen_from_web.js ile üretildi)

from . import storage, i18n  # noqa: E402


class Core:
    updates = None
    ann = None
    agent = None


def init(app, app_id, repo=None, version='0.0.0', owner=None, data_dir=None, channel='win-app', setup_channel='win-setup',
         update=True, crash=True, announcements=False, whatsnew=True, onboarding=None, interval_hours=6, updater_kwargs=None,
         agent=True):
    """Tek çağrıda: depo, dil + görünüm (yazı tipleri, QSS, RTL), iletişim kuyruğu, çökme raporu, güncelleme denetimi
    (açılış + 6 saat), "neler yeni", isteğe bağlı duyurular ve ilk açılış sihirbazı (after_show() ile)."""
    from . import style, contact, crash as _crash, whatsnew as _wn
    storage.use(data_dir, app=app_id) if data_dir else storage.use(app=app_id)
    core = Core()
    core.app_id, core.version = app_id, version
    style.install(app)
    contact.init(app=app_id, version=version)
    if crash:
        _crash.init(app=app_id, version=version)
    if update and repo:
        from .updater import Updater, confirm_started
        from .update_ui import UpdateController
        u = Updater(repo=repo, app=app_id, version=version, owner=owner, channel=channel, setup_channel=setup_channel, **(updater_kwargs or {}))
        confirm_started(u.staging, version)
        core.updates = UpdateController(u).start(interval_hours=interval_hours)
    core.whatsnew_shown = _wn.start(version) if whatsnew else False
    if announcements:
        from . import announcements as _ann
        core.ann = _ann.start(app=app_id, version=version, on_update=(core.updates.run if core.updates else None))
    core.onboarding = onboarding
    if agent:   # Asistan Agent: True ya da {'ai': f, 'sync': bool}; üst çubuğa core.agent.button(), ayarlara kart kendiliğinden
        try:
            from . import agent as _ag
            a = agent if isinstance(agent, dict) else {}
            core.agent = _ag.start(app, app_id, version, ai=a.get('ai'), sync=a.get('sync', True))
        except Exception:
            core.agent = None

    failed = [a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--fc-update-failed=')]

    def after_show():
        if failed:
            from PySide6.QtCore import QTimer
            from .widgets import toast
            QTimer.singleShot(1200, lambda: toast(i18n.t('fc.update.failed', {'e': 'v' + failed[0]}), 'error', 9000))
        if onboarding is not None and onboarding is not False and not core.whatsnew_shown:
            from PySide6.QtCore import QTimer
            from . import onboarding as ob
            QTimer.singleShot(600, lambda: ob.maybe_start(**(onboarding or {})))
    core.after_show = after_show
    return core
