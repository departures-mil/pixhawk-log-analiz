"""Pixhawk Log Analiz — giriş noktası."""
import os, sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = 'app'


def main():
    # Pencereli exe'de konsol yok: print/traceback çökmesin
    for n in ('stdout', 'stderr'):
        if getattr(sys, n) is None: setattr(sys, n, open(os.devnull, 'w', encoding='utf-8'))
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from app.ui.common import STYLE, app_icon
    from app.version import APP_NAME
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME); app.setWindowIcon(app_icon())
    app.setStyleSheet(STYLE)
    from app.ui.main_window import MainWindow
    w = MainWindow(); w.show_start()
    for a in sys.argv[1:]:
        if os.path.isfile(a) and a.lower().endswith(('.bin', '.tlog')):
            w.open_log(a); break
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
