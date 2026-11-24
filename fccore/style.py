"""fccore.style — görünüm: renk şeması (falcon varsayılan …), mod (dark | light | auto), yazı boyutu (0.85–1.4),
gömülü Inter + Noto Sans Arabic ve tokenlardan üretilen tam QSS (web css/core.css karşılığı).

    from fccore import style
    style.apply(app)                       # yazı tipleri + QSS + yön; seçimler kalıcı (storage: scheme/theme/fontScale)
    style.set_scheme('zumrut'); style.set_theme('light'); style.bump(+1)
    style.register_scheme('klasik', dark={'bg': '#1d2433', ...}, light={...}, label={'tr': 'Klasik (eski görünüm)', ...})
    style.tok('accent') → '#22d3ee'        style.qcolor('#22d3ee29') → QColor
Bileşenler sınıfı dinamik özellikle alır: w.setProperty('fc', 'btn primary small') (bkz. widgets.cls()).
"""
import os

from . import storage, i18n
from .tokens import TOKENS, SCHEMES, BUILTIN as _BUILTIN

MIN, MAX, STEP = 0.85, 1.4, 0.05
BUILTIN = list(_BUILTIN)
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
_custom = {}     # id → {'dark', 'light', 'label'}
_subs = []
_fonts_loaded = False
_app = None


# ---------------------------------------------------------------- şema / mod / ölçek
def schemes():
    l = list(BUILTIN)
    for k in _custom:
        if k not in l:
            l.insert(1 if k == 'klasik' else len(l), k)
    return l


def scheme():
    s = storage.get('scheme')
    return s if s in schemes() else 'falcon'


def scheme_label(sid, l=None):
    if sid in _custom:
        return i18n.pick(_custom[sid]['label'], l) or sid
    return i18n.t('fc.scheme.' + sid, None, l)


def _clean(t):
    out = {}
    for k, v in (t or {}).items():
        k = k[2:] if k.startswith('--') else k
        if k in TOKENS and isinstance(v, str):
            out[k] = v.strip()
    return out


def register_scheme(sid, dark=None, light=None, label=None):
    """Uygulamanın eski görünümü ('klasik'): eksik tokenlar falcon'dan tamamlanır; light verilmezse dark kullanılır."""
    import re
    sid = re.sub(r'[^a-z0-9-]', '', str(sid or '').lower())
    if not sid or sid == 'falcon' or not (dark or light):
        return
    d, li = _clean(dark or light), _clean(light or dark)
    _custom[sid] = {'dark': dict(SCHEMES['falcon']['dark'], **d), 'light': dict(SCHEMES['falcon']['light' if light else 'dark'], **li),
                    'label': label or sid}
    apply()


def scheme_tokens(sid=None, mode=None):
    sid = sid or scheme()
    mode = mode or effective()
    if sid in _custom:
        return _custom[sid][mode]
    return SCHEMES.get(sid, SCHEMES['falcon'])[mode]


def set_scheme(sid):
    if sid in schemes():
        storage.set('scheme', sid)
        apply()


def theme():
    t = storage.get('theme')
    return t if t in ('light', 'auto') else 'dark'


def effective():
    t = theme()
    if t != 'auto':
        return t
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        return 'light' if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Light else 'dark'
    except Exception:
        return 'dark'


def set_theme(t):
    if t in ('dark', 'light', 'auto'):
        storage.set('theme', t)
        apply()


def toggle():
    set_theme('dark' if effective() == 'light' else 'light')


def clamp(x):
    try:
        x = round(float(x or 1) * 100) / 100
    except (TypeError, ValueError):
        x = 1
    return min(MAX, max(MIN, x))


def scale():
    return clamp(storage.get('fontScale', 1))


def set_scale(x):
    storage.set('fontScale', clamp(x))
    apply()


def bump(d):
    set_scale(scale() + d * STEP)


def on_change(f):
    _subs.append(f)
    return lambda: _subs.remove(f) if f in _subs else None


def tok(name, sid=None, mode=None):
    return scheme_tokens(sid, mode)[name]


# ---------------------------------------------------------------- renk
def rgba(c):
    """CSS #rgb/#rgba/#rrggbb/#rrggbbaa → (r, g, b, a 0-255)."""
    c = c.strip().lstrip('#')
    if len(c) in (3, 4):
        c = ''.join(ch * 2 for ch in c)
    if len(c) == 6:
        c += 'ff'
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16)


def q(c):
    """QSS rengi (Qt #aarrggbb kullanır; CSS #rrggbbaa'yı rgba()'ya çeviririz)."""
    r, g, b, a = rgba(c)
    return 'rgba(%d,%d,%d,%d)' % (r, g, b, a) if a != 255 else '#%02x%02x%02x' % (r, g, b)


def style_rgb(c):
    return rgba(c)[:3]


def qcolor(c):
    from PySide6.QtGui import QColor
    r, g, b, a = rgba(c)
    return QColor(r, g, b, a)


def mix(c, pct, over='#00000000'):
    """color-mix(in srgb, c pct%, transparent) yaklaşığı."""
    r, g, b, a = rgba(c)
    return '#%02x%02x%02x%02x' % (r, g, b, round(a * pct / 100))


# ---------------------------------------------------------------- yazı tipleri
def load_fonts():
    global _fonts_loaded
    if _fonts_loaded:
        return
    from PySide6.QtGui import QFontDatabase
    for f in sorted(os.listdir(FONT_DIR)):
        if f.endswith('.ttf'):
            QFontDatabase.addApplicationFont(os.path.join(FONT_DIR, f))
    _fonts_loaded = True


def families(l=None):
    return ['Noto Sans Arabic', 'Inter', 'Segoe UI'] if i18n.is_rtl(l) else ['Inter', 'Noto Sans Arabic', 'Segoe UI']


def base_px():
    return 14 * scale()


def font(px=None, weight=400, l=None):
    from PySide6.QtGui import QFont
    f = QFont()
    f.setFamilies(families(l))
    f.setPixelSize(round(px or base_px()))
    f.setWeight(QFont.Weight(weight))
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


# ---------------------------------------------------------------- QSS
def qss(sid=None, mode=None, sc=None, rtl=None):
    T = {k: q(v) for k, v in scheme_tokens(sid, mode).items() if k not in ('border-w', 'focus-w', 'shadow-pop', 'shadow-modal', 'shadow-toast')}
    raw = scheme_tokens(sid, mode)
    bw = raw['border-w']
    fw = raw['focus-w']
    s = clamp(sc if sc is not None else scale())
    rtl = i18n.is_rtl() if rtl is None else rtl
    ar = i18n.is_rtl()

    def px(n):
        return '%dpx' % round(n * s)

    def rem(n):
        return '%dpx' % round(14 * n * s)
    start, end = ('right', 'left') if rtl else ('left', 'right')
    grad = 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 %s, stop:1 %s)' % (T['primary-1'], T['primary-2'])
    gact = 'qlineargradient(x1:%d, y1:0, x2:%d, y2:0, stop:0 %s, stop:1 %s)' % (1 if rtl else 0, 0 if rtl else 1, T['active-1'], T['active-2'])
    seg_on = q(mix(raw['accent'], 16))
    from .icons import svg_file
    chev = svg_file('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#%02x%02x%02x" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>' % style_rgb(raw['text']))
    tick = svg_file('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#%02x%02x%02x" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>' % style_rgb(raw['on-accent']))
    V = dict(T, chev=chev, tick=tick, bw=bw, fw=fw, grad=grad, gact=gact, start=start, end=end, seg_on=seg_on, base=rem(1),
             fs13=px(13), fs12=px(12), fs125=px(12.5), fs115=px(11.5), fs11=px(11), fs105=px(10.5), fs135=px(13.5),
             title=rem(1.57), ctitle=rem(1.07), desc=rem(0.93), brand=rem(1.21), tag=rem(0.82), h2=rem(1.21),
             upper='12px' if ar else '11px')
    css = '''
* {{ color: {text}; outline: 0; }}
QWidget {{ font-size: {base}; }}
QMainWindow, QDialog#fcDialog {{ background: transparent; }}
QWidget#fcRoot {{ background: {bg}; }}
QToolTip {{ color: {text}; background: {panel-solid}; border: {bw} solid {border-strong}; border-radius: 6px; padding: 5px 8px; }}
QLabel {{ background: transparent; }}
QLabel[fc~="muted"] {{ color: {muted}; }}
QLabel[fc~="accent"] {{ color: {accent}; }}
a {{ color: {accent}; }}

/* ---- kabuk ---- */
QFrame#fcSidebar {{ background: {sidebar-bg}; border: 0; border-{end}: {bw} solid {border}; }}
QFrame#fcBrand {{ background: transparent; border: 0; border-bottom: {bw} solid {border}; }}
QLabel#fcBrandLogo {{ background: {grad}; border-radius: 11px; }}
QLabel#fcBrandName {{ font-size: {brand}; font-weight: 700; }}
QLabel#fcBrandTag {{ color: {muted}; font-size: {tag}; }}
QLabel[fc~="version-badge"] {{ color: {accent}; background: {accent-soft}; border: 1px solid {accent-line}; border-radius: 9px; padding: 1px 7px; font-size: {fs11}; font-weight: 600; }}
QLabel[fc~="nav-title"] {{ color: {nav-title}; font-size: {upper}; padding: 10px 12px 6px 12px; letter-spacing: 1.2px; }}
QPushButton[fc~="nav-item"] {{ color: {nav-text}; background: transparent; border: 1px solid transparent; border-radius: 10px; padding: 10px 12px; text-align: {start}; font-weight: 400; }}
QPushButton[fc~="nav-item"]:hover {{ background: {panel-hover}; color: {text}; }}
QPushButton[fc~="nav-item"]:checked {{ color: {text}; background: {gact}; border: 1px solid {active-line}; border-{start}: 3px solid {accent}; padding-{start}: 10px; }}
QFrame#fcTopbar {{ background: {topbar-bg}; border: 0; border-bottom: {bw} solid {border}; }}
QLabel#fcPageTitle {{ font-size: {title}; font-weight: 700; }}
QLabel#fcPageSub {{ color: {muted}; font-size: {desc}; }}
QFrame[fc~="topbar-sep"] {{ background: {border}; border: 0; min-width: 1px; max-width: 1px; min-height: 22px; max-height: 22px; }}
QScrollArea, QScrollArea > QWidget > QWidget#fcContent, QWidget#fcContent, QStackedWidget#fcPages {{ background: transparent; border: 0; }}

/* ---- düğmeler ---- */
QPushButton, QToolButton {{ color: {text}; background: {panel-solid}; border: {bw} solid {border}; border-radius: 10px; padding: 8px 16px; font-weight: 500; }}
QPushButton:hover, QToolButton:hover {{ background: {panel-hover}; border-color: {border-strong}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {muted}; }}
QPushButton:focus {{ border-color: {focus}; }}
QPushButton[fc~="small"] {{ padding: 5px 11px; font-size: {fs125}; border-radius: 8px; }}
QPushButton[fc~="primary"] {{ color: {on-accent}; background: {grad}; border-color: transparent; }}
QPushButton[fc~="primary"]:hover {{ background: {grad}; border-color: {focus}; }}
QPushButton[fc~="ghost"] {{ background: transparent; }}
QPushButton[fc~="success"] {{ color: {ok-text}; background: {ok-soft}; border-color: {ok-line}; }}
QPushButton[fc~="danger-soft"] {{ color: {danger-text}; background: {danger-soft}; border-color: {danger-line}; }}
QPushButton[fc~="danger"] {{ color: {on-accent}; background: {danger}; border-color: {danger}; }}
QPushButton[fc~="icon-btn"], QToolButton[fc~="icon-btn"] {{ color: {muted}; background: transparent; border: {bw} solid {border}; border-radius: 9px; padding: 0; min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px; }}
QPushButton[fc~="icon-btn"]:hover {{ background: {panel-hover}; color: {text}; border-color: {border}; }}
QPushButton[fc~="icon-btn"][fc~="danger"]:hover {{ color: {danger-text}; background: {danger-soft}; border-color: {danger-line}; }}
QPushButton[fc~="top-act"] {{ padding: 6px 12px; font-size: {fs13}; min-height: 21px; }}
QPushButton[fc~="top-act"][fc~="avail"] {{ color: {accent}; border-color: {border-strong}; }}
QPushButton[fc~="top-act"][fc~="error"] {{ color: {danger-text}; border-color: {danger-line}; }}
QPushButton[fc~="top-act"][fc~="off"], QPushButton[fc~="top-act"][fc~="offline"] {{ color: {muted}; }}
QFrame[fc~="lang-switch"] {{ background: transparent; border: {bw} solid {border}; border-radius: 10px; }}
QPushButton[fc~="lang-btn"] {{ color: {muted}; background: transparent; border: 0; border-radius: 7px; padding: 4px 8px; font-size: {fs12}; font-weight: 600; min-height: 18px; }}
QPushButton[fc~="lang-btn"]:hover {{ color: {text}; background: transparent; }}
QPushButton[fc~="lang-btn"]:checked {{ color: {accent}; background: {active-1}; }}
QPushButton[fc~="lang-option"] {{ background: {panel-solid}; border: {bw} solid {border}; border-radius: 10px; padding: 12px 16px; text-align: {start}; }}
QPushButton[fc~="lang-option"]:checked {{ border-color: {border-strong}; color: {accent}; }}
QFrame[fc~="segmented"] {{ background: {panel-solid}; border: {bw} solid {border}; border-radius: 10px; }}
QFrame[fc~="segmented"] QPushButton {{ color: {muted}; background: transparent; border: 0; border-radius: 7px; padding: 8px 10px; font-weight: 600; }}
QFrame[fc~="segmented"] QPushButton:checked {{ color: {accent}; background: {seg_on}; }}
QFrame[fc~="segmented"] QPushButton:hover:!checked {{ color: {text}; }}
QLabel[fc~="sync-badge"] {{ background: {accent}; color: {on-badge}; border-radius: 9px; font-size: {fs105}; font-weight: 700; padding: 0 5px; }}
QLabel[fc~="update-dot"] {{ background: {accent}; border: 2px solid {bg}; border-radius: 6px; }}
QFrame#fcUpdateFloat {{ background: {panel-solid}; border: {bw} solid {border-strong}; border-radius: 12px; }}
QLabel[fc~="update-detail"] {{ color: {muted}; font-size: {fs12}; }}
QLabel[fc~="update-mode"] {{ color: {accent}; font-size: {fs115}; font-weight: 600; }}

/* ---- girişler ---- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
  color: {text}; background: {panel-solid}; border: {bw} solid {border}; border-radius: 9px; padding: 8px 12px;
  selection-background-color: {accent}; selection-color: {on-accent}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{ border-color: {border-strong}; }}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {{ color: {muted}; }}
QLineEdit[fc~="invalid"], QTextEdit[fc~="invalid"], QPlainTextEdit[fc~="invalid"] {{ border-color: {danger}; }}
QComboBox::drop-down {{ border: 0; width: 28px; subcontrol-position: center {end}; }}
QComboBox::down-arrow {{ image: url({chev}); width: 14px; height: 14px; margin-{end}: 10px; }}
QComboBox QAbstractItemView {{ background: {panel-solid}; color: {text}; border: {bw} solid {border-strong}; border-radius: 8px; padding: 4px; selection-background-color: {active-1}; selection-color: {text}; outline: 0; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ border: 0; width: 16px; background: transparent; }}
QLabel[fc~="field-label"] {{ color: {label}; font-size: {fs125}; font-weight: 500; }}
QLabel[fc~="field-hint"] {{ color: {muted}; font-size: {fs115}; }}
QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; border: {bw} solid {border-strong}; background: {panel-solid}; }}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; image: url({tick}); }}
QRadioButton::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QSlider::groove:horizontal {{ height: 6px; background: {bar-track}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {accent}; width: 14px; margin: -5px 0; border-radius: 7px; }}

/* ---- kartlar ---- */
QFrame#card, QFrame[fc~="card"] {{ background: {panel}; border: {bw} solid {border}; border-radius: 14px; }}
QLabel[fc~="card-title"] {{ font-size: {ctitle}; font-weight: 600; }}
QLabel[fc~="card-desc"] {{ color: {muted}; font-size: {desc}; }}
QLabel[fc~="fc-sub"] {{ color: {label}; font-size: {fs12}; font-weight: 600; letter-spacing: 0.8px; }}
QLabel[fc~="section-title"] {{ color: {label}; font-size: {fs13}; font-weight: 600; letter-spacing: 1px; }}
QLabel[fc~="badge"] {{ color: {badge-text}; background: {badge-bg}; border: 1px solid {badge-line}; border-radius: 10px; padding: 3px 10px; font-size: {fs12}; }}
QLabel[fc~="notice"] {{ color: {warn-text}; background: {warn-soft}; border: {bw} solid {warn-line}; border-radius: 10px; padding: 11px 15px; font-size: {fs13}; }}
QLabel[fc~="notice"][fc~="info"] {{ color: {accent}; background: {accent-soft}; border-color: {accent-line}; }}
QLabel[fc~="notice"][fc~="error"] {{ color: {danger-text}; background: {danger-soft}; border-color: {danger-line}; }}
QLabel[fc~="notice"][fc~="ok"] {{ color: {ok-text}; background: {ok-soft}; border-color: {ok-line}; }}
QFrame[fc~="fc-li"] {{ background: {panel-solid}; border: {bw} solid {border}; border-radius: 9px; }}
QLabel[fc~="meter-head"] {{ font-size: {fs125}; }}
QLabel[fc~="link"] {{ color: {accent}; font-size: {fs12}; }}
QPushButton[fc~="fc-scheme"] {{ background: {panel-solid}; border: {bw} solid {border}; border-radius: 10px; padding: 0; text-align: {start}; }}
QPushButton[fc~="fc-scheme"]:hover {{ border-color: {border-strong}; }}
QPushButton[fc~="fc-scheme"]:checked {{ border: 2px solid {accent}; }}

/* ---- ilerleme ---- */
QProgressBar {{ background: {bar-track}; border: 0; border-radius: 4px; max-height: 8px; min-height: 8px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
QProgressBar[fc~="meter"] {{ max-height: 6px; min-height: 6px; border-radius: 3px; }}
QProgressBar[fc~="meter"]::chunk {{ border-radius: 3px; }}
QProgressBar[fc~="warn"]::chunk {{ background: {warn}; }}
QProgressBar[fc~="full"]::chunk {{ background: {danger}; }}
QFrame[fc~="fc-steps"] QFrame {{ background: {bar-track}; border-radius: 2px; min-height: 4px; max-height: 4px; }}
QFrame[fc~="fc-steps"] QFrame[fc~="on"] {{ background: {accent}; }}

/* ---- tablolar / listeler ---- */
QTableView, QTreeView, QListView, QTableWidget, QTreeWidget, QListWidget {{ background: {panel}; alternate-background-color: {panel-hover};
  border: {bw} solid {border}; border-radius: 10px; gridline-color: {border}; selection-background-color: {active-1}; selection-color: {text}; }}
QTableView::item:hover, QTreeView::item:hover, QListView::item:hover {{ background: {panel-hover}; }}
QHeaderView {{ background: transparent; border: 0; }}
QHeaderView::section {{ background: {panel-solid}; color: {label}; border: 0; border-bottom: {bw} solid {border}; border-{end}: 1px solid {border}; padding: 7px 10px; font-weight: 600; font-size: {fs125}; }}
QTableCornerButton::section {{ background: {panel-solid}; border: 0; }}
QTabWidget::pane {{ border: {bw} solid {border}; border-radius: 10px; background: {panel}; top: -1px; }}
QTabBar::tab {{ color: {muted}; background: transparent; border: 0; border-bottom: 2px solid transparent; padding: 8px 16px; font-weight: 600; }}
QTabBar::tab:selected {{ color: {accent}; border-bottom-color: {accent}; }}
QTabBar::tab:hover:!selected {{ color: {text}; }}
QGroupBox {{ border: {bw} solid {border}; border-radius: 10px; margin-top: 14px; padding: 12px; background: {panel}; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top {start}; padding: 0 6px; color: {label}; font-weight: 600; }}

/* ---- kaydırma çubuğu ---- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: {scroll-thumb}; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:vertical {{ min-height: 30px; }}
QScrollBar::handle:horizontal {{ min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: 0; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ---- menü / pencere / bildirim ---- */
QMenu {{ background: {panel-solid}; border: {bw} solid {border-strong}; border-radius: 10px; padding: 5px; }}
QMenu::item {{ padding: 7px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {active-1}; color: {text}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 8px; }}
QMenuBar {{ background: transparent; }}
QMenuBar::item:selected {{ background: {panel-hover}; border-radius: 6px; }}
QFrame#fcModal {{ background: {modal-bg}; border: {bw} solid {modal-border}; border-radius: 18px; }}
QFrame#fcModalHeader {{ background: transparent; border: 0; border-bottom: {bw} solid {border}; }}
QFrame#fcModalFooter {{ background: transparent; border: 0; border-top: {bw} solid {border}; }}
QLabel#fcModalTitle {{ font-size: {h2}; font-weight: 700; }}
QWidget#fcBackdrop {{ background: {backdrop}; }}
QMessageBox, QInputDialog, QFileDialog, QColorDialog, QDialog {{ background: {modal-bg}; }}
QLabel[fc~="toast"] {{ color: {toast-text}; background: {toast-bg}; border: 1px solid {toast-line}; border-radius: 11px; padding: 12px 18px; font-size: {fs135}; }}
QLabel[fc~="toast"][fc~="error"] {{ color: {toast-err-text}; background: {toast-err-bg}; border-color: {toast-err-line}; }}
QLabel[fc~="toast"][fc~="info"] {{ color: {text}; background: {panel-solid}; border-color: {border-strong}; }}
QLabel[fc~="fc-tag"] {{ color: {on-accent}; background: {danger}; border-radius: 6px; padding: 1px 8px; font-size: {fs11}; }}
QStatusBar {{ background: {topbar-bg}; color: {muted}; border-top: {bw} solid {border}; }}
'''.format(**V)
    return css


def apply(app=None):
    """Yazı tipi, yön ve QSS'i uygular; abonelere {theme, effective, scale, scheme} bildirir."""
    global _app
    try:
        from PySide6.QtWidgets import QApplication
        app = app or _app or QApplication.instance()
    except Exception:
        app = None
    if app is not None:
        _app = app
        load_fonts()
        i18n.apply(app)
        app.setFont(font())
        app.setStyleSheet(qss())
    st = {'theme': theme(), 'effective': effective(), 'scale': scale(), 'scheme': scheme()}
    for f in list(_subs):
        try:
            f(st)
        except Exception:
            import traceback
            traceback.print_exc()


def install(app):
    """apply() + dil değişince yeniden uygula + sistem koyu/açık değişimini izle (otomatik mod)."""
    apply(app)
    i18n.on_change(lambda l: apply(app))
    try:
        app.styleHints().colorSchemeChanged.connect(lambda *_: theme() == 'auto' and apply(app))
    except Exception:
        pass


def _reset():
    _custom.clear()
    del _subs[:]
