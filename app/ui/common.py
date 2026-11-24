"""Ortak arayüz parçaları: iş parçacığı, yardımcı widget'lar, görsel görüntüleyici."""
from __future__ import annotations
import os, subprocess, sys, traceback
from PySide6.QtCore import Qt, QObject, QThread, Signal, QPoint, QSize
from PySide6.QtGui import QPixmap, QFont, QIcon, QPainter, QColor
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QScrollArea, QVBoxLayout,
                               QFrame, QMessageBox, QApplication)
from .i18n import t, lang

# Görünüm v1.1.0'dan beri ortak çekirdekte (fccore.style + app/ui/kabuk.py: 'klasik' şema = eski renkler).

VERDICT_COL = {'normal': '#16A34A', 'incident': '#D97706', 'incident_minor': '#CA8A04', 'crash': '#DC2626', 'noflight': '#64748B'}
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
