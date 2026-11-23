"""Ortak arayüz parçaları: iş parçacığı, başlık çubuğu, tema, görsel görüntüleyici."""
from __future__ import annotations
import os, subprocess, sys, traceback
from PySide6.QtCore import Qt, QObject, QThread, Signal, QPoint, QSize
from PySide6.QtGui import QPixmap, QFont, QIcon, QPainter, QColor
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QScrollArea, QVBoxLayout,
                               QFrame, QMessageBox, QApplication)
from .i18n import t, lang

STYLE = """
* { font-family: 'Segoe UI', 'Noto Sans', 'DejaVu Sans'; font-size: 10pt; }
QMainWindow, QWidget#root, QDialog { background: #0F172A; }
QWidget { color: #E2E8F0; }
#titlebar { background: #0B1222; border-bottom: 1px solid #1E293B; }
#apptitle { font-size: 11pt; font-weight: 600; color: #F8FAFC; }
#tbtn { background: transparent; border: none; color: #CBD5E1; padding: 4px 12px; font-size: 10pt; border-radius: 4px; }
#tbtn:hover { background: #1E293B; color: white; }
#tbtnClose { background: transparent; border: none; color: #CBD5E1; padding: 4px 14px; font-size: 11pt; border-radius: 4px; }
#tbtnClose:hover { background: #DC2626; color: white; }
#tbtnAccent { background: #1D4ED8; border: none; color: white; padding: 4px 12px; border-radius: 4px; }
#tbtnAccent:hover { background: #2563EB; }
QListWidget#nav { background: #0B1222; border: none; border-right: 1px solid #1E293B; padding-top: 6px; }
QListWidget#nav::item { padding: 9px 12px; border-radius: 6px; margin: 2px 6px; color: #CBD5E1; }
QListWidget#nav::item:selected { background: #1E3A8A; color: white; }
QListWidget#nav::item:hover:!selected { background: #172033; }
QPushButton { background: #1E293B; border: 1px solid #334155; border-radius: 6px; padding: 6px 14px; color: #E2E8F0; }
QPushButton:hover { background: #273449; border-color: #475569; }
QPushButton:disabled { color: #64748B; }
QPushButton#primary { background: #2563EB; border: none; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #3B82F6; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QTextBrowser {
  background: #111C33; border: 1px solid #334155; border-radius: 6px; padding: 5px; color: #E2E8F0; selection-background-color: #2563EB; }
QComboBox QAbstractItemView { background: #111C33; color: #E2E8F0; selection-background-color: #1E3A8A; }
QTableWidget, QTreeWidget, QListWidget { background: #0F1A30; alternate-background-color: #111F38; border: 1px solid #1E293B;
  gridline-color: #1E293B; color: #E2E8F0; selection-background-color: #1E3A8A; }
QHeaderView::section { background: #162238; color: #CBD5E1; border: none; border-right: 1px solid #1E293B; padding: 5px; font-weight: 600; }
QProgressBar { background: #111C33; border: 1px solid #334155; border-radius: 6px; text-align: center; color: white; height: 18px; }
QProgressBar::chunk { background: #2563EB; border-radius: 6px; }
QGroupBox { border: 1px solid #1E293B; border-radius: 8px; margin-top: 14px; padding: 10px; background: #0F1A30; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #93C5FD; font-weight: 600; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #0F172A; width: 10px; } QScrollBar::handle:vertical { background: #334155; border-radius: 5px; min-height: 30px; }
QScrollBar:horizontal { background: #0F172A; height: 10px; } QScrollBar::handle:horizontal { background: #334155; border-radius: 5px; }
QCheckBox, QRadioButton { spacing: 6px; }
QListView::indicator { width: 14px; height: 14px; border: 1px solid #64748B; border-radius: 3px; background: #0B1222; }
QListView::indicator:checked { background: #2563EB; border: 1px solid #93C5FD; }
QSlider::groove:horizontal { height: 6px; background: #1E293B; border-radius: 3px; }
QSlider::handle:horizontal { background: #3B82F6; width: 14px; margin: -5px 0; border-radius: 7px; }
QTabWidget::pane { border: 1px solid #1E293B; border-radius: 8px; background: #0F172A; top: -1px; }
QTabBar::tab { background: #111C33; color: #CBD5E1; padding: 7px 16px; border: 1px solid #1E293B; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background: #1E3A8A; color: white; }
QWidget#page { background: #0F172A; }
QToolTip { background: #1E293B; color: white; border: 1px solid #334155; }
#card { background: #111C33; border: 1px solid #1E293B; border-radius: 10px; }
#h1 { font-size: 15pt; font-weight: 700; color: #F8FAFC; }
#h2 { font-size: 11.5pt; font-weight: 600; color: #93C5FD; }
#muted { color: #94A3B8; }
#statusbar { background: #0B1222; border-top: 1px solid #1E293B; color: #94A3B8; padding: 3px 10px; }
"""

VERDICT_COL = {'normal': '#16A34A', 'incident': '#D97706', 'crash': '#DC2626', 'noflight': '#64748B'}
STATUS_COL = {'good': '#16A34A', 'warn': '#D97706', 'bad': '#DC2626'}


class Worker(QObject):
    """Bir fonksiyonu arka planda çalıştırır. fn(progress_cb, cancel_cb) imzası isteğe bağlı."""
    progress = Signal(object)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *a, **kw):
        super().__init__()
        self.fn, self.a, self.kw = fn, a, kw
        self.cancelled = False

    def run(self):
        try:
            r = self.fn(*self.a, **self.kw)
            self.done.emit(r)
        except Exception as e:
            traceback.print_exc()
            self.failed.emit(str(e) or e.__class__.__name__)


_workers = set()


def run_bg(fn, *a, on_done=None, on_fail=None, on_progress=None, **kw):
    """fn arka planda (Python iş parçacığı); Worker ana iş parçacığında yaşadığı için sinyaller ana iş parçacığında işlenir."""
    import threading
    w = Worker(fn, *a, **kw)
    if on_done: w.done.connect(on_done)
    if on_fail: w.failed.connect(on_fail)
    if on_progress: w.progress.connect(on_progress)
    _workers.add(w)
    w.done.connect(lambda *_: _workers.discard(w)); w.failed.connect(lambda *_: _workers.discard(w))
    threading.Thread(target=w.run, daemon=True).start()
    return w


def open_path(p):
    try:
        if sys.platform.startswith('win'): os.startfile(p)
        elif sys.platform == 'darwin': subprocess.Popen(['open', p])
        else: subprocess.Popen(['xdg-open', p])
    except Exception:
        pass


def label(text='', obj=None, wrap=False, sel=False):
    l = QLabel(text)
    if obj: l.setObjectName(obj)
    if wrap: l.setWordWrap(True)
    if sel: l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return l


def button(text, slot=None, primary=False, tip=None):
    b = QPushButton(text)
    if primary: b.setObjectName('primary')
    if slot: b.clicked.connect(slot)
    if tip: b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    return b


def card():
    f = QFrame(); f.setObjectName('card'); return f


def info(parent, text, title=None):
    QMessageBox.information(parent, title or t('app'), text)


def error(parent, text):
    QMessageBox.warning(parent, t('err'), text)


def app_icon():
    pm = QPixmap(64, 64); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor('#2563EB')); p.setPen(Qt.NoPen); p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    p.setPen(QColor('white')); f = QFont('Segoe UI', 22, QFont.Bold); p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, 'PX'); p.end()
    return QIcon(pm)


class ImageView(QScrollArea):
    """PNG baytlarını genişliğe sığdırarak gösterir."""
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.lbl = QLabel(); self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setStyleSheet('background: white; border-radius: 8px;')
        self.setWidget(self.lbl)
        self.pm = None

    def set_png(self, b):
        self.pm = QPixmap(); self.pm.loadFromData(b or b''); self._fit()

    def _fit(self):
        if self.pm and not self.pm.isNull():
            w = max(200, self.viewport().width() - 8)
            self.lbl.setPixmap(self.pm.scaledToWidth(min(w, self.pm.width() * 2), Qt.SmoothTransformation))
        else:
            self.lbl.clear()

    def resizeEvent(self, e):
        super().resizeEvent(e); self._fit()


class TitleBar(QWidget):
    """Çerçevesiz pencere başlığı: sağ üstte Güncelle, Eşitle, Küçült, Yarım, Kapat."""
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setObjectName('titlebar'); self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(40)
        h = QHBoxLayout(self); h.setContentsMargins(10, 0, 4, 0); h.setSpacing(4)
        ic = QLabel(); ic.setPixmap(app_icon().pixmap(24, 24)); h.addWidget(ic)
        self.title = QLabel(); self.title.setObjectName('apptitle'); h.addWidget(self.title)
        self.sub = QLabel(); self.sub.setObjectName('muted'); h.addWidget(self.sub)
        h.addSpacing(14)
        # işlemler (programın her yerinden tek tık)
        self.b_open = self._b('📂', 'tbtn', lambda: win.pick_log())
        self.b_info = self._b('✈', 'tbtn', lambda: win.edit_flight_info())
        self.b_solve = self._b('🩺', 'tbtn', lambda: win.goto('solver'))
        self.b_rep = self._b('📄', 'tbtn', lambda: win.export_report())
        for b in (self.b_open, self.b_info, self.b_solve, self.b_rep): h.addWidget(b)
        h.addSpacing(10)
        # o anki log bilgisi (dosya · karar · kırım işareti)
        self.loginfo = QLabel(''); self.loginfo.setObjectName('muted'); self.loginfo.setMinimumWidth(40)
        from PySide6.QtWidgets import QSizePolicy, QComboBox
        self.loginfo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        h.addWidget(self.loginfo, 1)
        # dil seçimi
        self.lang = QComboBox(); self.lang.setObjectName('tlang'); self.lang.setFocusPolicy(Qt.NoFocus); self.lang.setMinimumWidth(130)
        self.lang.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        for c, n in (('tr', '🌐 Türkçe'), ('en', '🌐 English'), ('ar', '🌐 العربية')): self.lang.addItem(n, c)
        self.lang.setCurrentIndex(max(0, self.lang.findData(win.settings['lang'])))
        self.lang.currentIndexChanged.connect(self._lang)
        h.addWidget(self.lang); h.addSpacing(6)
        self.b_upd = self._b('⬇', 'tbtnAccent', win.do_update)
        self.b_sync = self._b('⇅', 'tbtn', win.do_sync)
        self.b_min = self._b('—', 'tbtn', win.showMinimized)
        self.b_half = self._b('◧', 'tbtn', win.toggle_half)
        self.b_close = self._b('✕', 'tbtnClose', win.close)
        for b in (self.b_upd, self.b_sync, self.b_min, self.b_half, self.b_close): h.addWidget(b)
        self._drag = None
        self.retranslate()

    def _lang(self):
        c = self.lang.currentData()
        if c and c != self.win.settings['lang']:
            self.win.settings['lang'] = c; self.win.settings.save(); self.win.apply_lang()

    def set_log(self, A=None, crash_mark=''):
        if A is None: self.loginfo.setText(''); return
        import os
        from ..core import texts
        v = A.verdict.get('kind', 'normal')
        icon = {'crash': '💥', 'incident': '⚠', 'normal': '✅', 'noflight': '⏸'}.get(v, '')
        mark = '  ·  💥 ' + t('fi_crash_mark') if crash_mark == 'yes' and v != 'crash' else ''
        self.loginfo.setText(f"  {os.path.basename(A.L.path)}  ·  {A.vehicle}  ·  {icon} {texts.T('v_' + v, lang())}  ·  {A.overall}/100{mark}")

    def _b(self, txt, obj, slot):
        b = QPushButton(txt); b.setObjectName(obj); b.clicked.connect(slot); b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.NoFocus); return b

    def retranslate(self):
        from ..version import VERSION
        self.title.setText(t('app')); self.sub.setText(f'  v{VERSION}')
        self.b_upd.setText('⬇ ' + t('t_update')); self.b_upd.setToolTip(t('t_update'))
        self.b_sync.setText('⇅ ' + t('t_sync')); self.b_sync.setToolTip(t('t_sync'))
        self.b_open.setToolTip(t('open_log')); self.b_info.setToolTip(t('fi_title')); self.b_solve.setToolTip(t('nav_solver'))
        self.b_rep.setToolTip(t('export'))
        self.b_min.setToolTip(t('t_min')); self.b_half.setToolTip(t('t_half')); self.b_close.setToolTip(t('t_close'))
        # Pencere butonları her dilde sağ üstte kalsın
        self.setLayoutDirection(Qt.LeftToRight)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            if self.win.isMaximized():
                return
            self.win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.win.toggle_half()
