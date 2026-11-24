"""fccore.update_ui — Updater'ın Qt köprüsü: arka plan iş parçacığı, ana iş parçacığına durum sinyali, uygulamayı kapatma.
    ctl = UpdateController(Updater(repo='organizer', app='organizer', version=__version__))
    ctl.state_changed.connect(...); ctl.check(); ctl.run()
TopBar'daki Güncelle düğmesi ve açılan Falcon tarzı ilerleme penceresi bunu kullanır."""
import threading

from PySide6.QtCore import QObject, QTimer, Signal, Slot, Qt
from PySide6.QtWidgets import QApplication

from .updater import Updater, error_text


class UpdateController(QObject):
    state_changed = Signal(dict)
    _relay = Signal(dict)
    _quit_sig = Signal()

    def __init__(self, updater=None, **kw):
        super().__init__()
        self.u = updater or Updater(**kw)
        if self.u.on_quit is None:
            self.u.on_quit = self._quit_sig.emit
        self._relay.connect(self._on_state, Qt.QueuedConnection)
        self._quit_sig.connect(self._do_quit, Qt.QueuedConnection)
        self.state = self.u.snapshot()
        self.u.subscribe(lambda s: self._relay.emit(s))

    @Slot(dict)
    def _on_state(self, s):
        self.state = s
        self.state_changed.emit(s)

    def _bg(self, fn):
        threading.Thread(target=fn, name='fc-update', daemon=True).start()

    def check(self, silent=False):
        self._bg(lambda: self.u.check(silent=silent))

    def run(self):
        def w():
            try:
                self.u.run()
            except Exception:
                pass
        self._bg(w)

    def start(self, interval_hours=6, first_delay_ms=6000):
        QTimer.singleShot(first_delay_ms, lambda: self.check(silent=True))
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self.check(silent=True))
        self._timer.start(int(max(1, interval_hours) * 3600 * 1000))
        return self

    def error_text(self, code):
        return error_text(code)

    def _do_quit(self):
        QTimer.singleShot(900, QApplication.quit)
