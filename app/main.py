"""Pixhawk Log Analiz — giriş noktası."""
import os, sys

if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = 'app'


def main():
    # Pencereli exe'de konsol yok: print/traceback çökmesin
    for n in ('stdout', 'stderr'):
        if getattr(sys, n) is None: setattr(sys, n, open(os.devnull, 'w', encoding='utf-8'))
    if '--analyze' in sys.argv:
        return cli(sys.argv)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from app.ui.common import app_icon
    from app.version import APP_NAME
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME); app.setWindowIcon(app_icon())
    files = [a for a in sys.argv[1:] if os.path.isfile(a) and a.lower().endswith(('.bin', '.tlog', '.pxloc'))]
    # Tek örnek: program açıksa dosyayı mevcut pencereye gönder
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    sname = 'PixhawkLogAnaliz-' + (os.environ.get('USERNAME') or os.environ.get('USER') or 'u')
    sock = QLocalSocket(); sock.connectToServer(sname)
    if sock.waitForConnected(300):
        sock.write(((files[0] if files else '') + '\n').encode('utf-8')); sock.flush(); sock.waitForBytesWritten(1000); sock.disconnectFromServer()
        return
    QLocalServer.removeServer(sname)
    server = QLocalServer(); server.listen(sname)
    from app.core import crash
    from app.core.settings import Settings
    crash.install()                       # yerel kayıt; fccore.crash bunu sarar (kabuk.init)
    settings = Settings()
    from app.ui import kabuk
    core = kabuk.init(app, settings, auto_update=bool(settings.get('auto_update_check', True)))
    from app.ui.main_window import MainWindow
    from app.ui import ajan
    ajan.kur()
    w = MainWindow(settings, core)
    crash.set_callback(lambda p: w.crashed.emit(p))

    def incoming():
        c = server.nextPendingConnection()
        if not c: return
        c.waitForReadyRead(1000)
        p = bytes(c.readAll()).decode('utf-8', 'replace').strip()
        w.open_req.emit(p)
    server.newConnection.connect(incoming)
    if not w.login():
        crash.shutdown(); return
    w.apply_role(); w.show_start()
    kabuk.after_show(core, w)
    ajan.baslat(app, w)
    for a in files:
        w.open_log(a); break
    rc = app.exec()
    crash.shutdown()
    sys.exit(rc)


def cli(argv):
    """Arayüzsüz analiz: PixhawkLogAnaliz.exe --analyze log.BIN [--json out.json] [--pdf rapor.pdf] [--lang tr]"""
    import json, time
    from app.core import loader, analysis, report
    def arg(k, d=None):
        return argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d
    src = arg('--analyze'); out = arg('--json', os.path.splitext(src)[0] + '_analiz.json'); lg = arg('--lang', 'tr')
    t0 = time.time()
    L = loader.load(src); t1 = time.time()
    A = analysis.Analysis(L); t2 = time.time()
    d = A.to_json() if hasattr(A, 'to_json') else {}
    if isinstance(d, str): d = json.loads(d)
    d['_timing'] = {'load_s': round(t1 - t0, 2), 'analyze_s': round(t2 - t1, 2), 'size_mb': round(L.size / 1e6, 1)}
    if arg('--pdf'):
        report.build_pdf(report.ReportData(A, lg, None, online_map=False), arg('--pdf'))
    with open(out, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=1, default=str)
    return 0


if __name__ == '__main__':
    main()
