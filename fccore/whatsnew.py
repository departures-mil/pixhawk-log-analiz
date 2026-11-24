"""fccore.whatsnew — güncellemeden sonraki ilk açılışta "Bu sürümde neler yeni".
Notlar updater tarafından kurulumdan ÖNCE storage 'whatsnew.pending'e yazılır ({version, notes:{tr,en,ar}})."""
import re
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel

from . import storage, i18n
from .i18n import t

cfg = {}


def notes_for(v):
    n = cfg.get('notes')
    if n:
        n = n(v) if callable(n) else n
        if n:
            return n
    p = storage.get('whatsnew.pending')
    return p.get('notes') if isinstance(p, dict) and str(p.get('version')) == str(v) else None


def show(v=None, parent=None):
    from .widgets import Modal, label, notice
    from . import icons
    v = v or cfg.get('version')
    notes = i18n.pick(notes_for(v))
    body = QWidget()
    lay = QVBoxLayout(body)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    lay.addWidget(label(t('fc.wn.ver', {'v': v}), 'muted'))
    lines = [re.sub(r'^\s*[-*•]\s*', '', x).strip() for x in re.split(r'\r?\n', str(notes or ''))]
    lines = [x for x in lines if x]
    if len(lines) > 1:
        lay.addWidget(label('<ul style="margin:0;-qt-list-indent:1">' + ''.join('<li>%s</li>' % _esc(x) for x in lines) + '</ul>', wrap=True, rich=True))
    else:
        lay.addWidget(label(lines[0] if lines else t('fc.wn.none'), wrap=True))
    lay.addWidget(notice('✓  ' + t('fc.wn.safe'), 'ok'))
    return Modal(parent=parent, title=t('fc.wn.title'), icon='sparkles', size='small', body=body)


def start(version, notes=None, delay_ms=900):
    """Döner: gösterilecekse True (ilk kurulumda ya da aynı sürümde False)."""
    cfg['version'] = str(version or '')
    if notes is not None:
        cfg['notes'] = notes
    v = cfg['version']
    if not v:
        return False
    seen = storage.get('whatsnew.seen')
    storage.set('whatsnew.seen', v)
    if not seen or seen == v:
        return False
    try:
        from .updater import cmp
        if cmp(v, seen) <= 0:
            return False
    except Exception:
        pass
    QTimer.singleShot(delay_ms, lambda: show(v))
    return True


def _esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
