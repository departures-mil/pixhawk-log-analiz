import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
_home = tempfile.mkdtemp(prefix='px-test-')
os.environ['APPDATA'] = _home          # app.core.paths.data_dir() → geçici klasör
os.environ['XDG_CONFIG_HOME'] = _home

import pytest  # noqa: E402


@pytest.fixture(scope='session')
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope='session')
def win(qapp):
    """Gerçek ana pencere (offscreen): kabuk.init + MainWindow, ilk açılış rehberi kapalı."""
    from app.core import crash
    from app.core.settings import Settings
    from app.ui import kabuk
    crash.install()
    s = Settings(); s['watch_enabled'] = False
    core = kabuk.init(qapp, s, auto_update=False)
    from fccore import storage
    storage.set('onboarding.done', True)
    from app.ui.main_window import MainWindow
    w = MainWindow(s, core)
    w.resize(1500, 950)
    w.show_start()
    qapp.processEvents()
    yield w
    w.close()
