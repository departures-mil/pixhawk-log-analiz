"""fccore.cards — Ayarlar kartları: Görünüm, Kullanım Limitleri, Otomatik hata raporu, Hakkında, Admin ile iletişim.
Her kart dil/şema değişince kendini yeniden çizer."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget)

from . import i18n, style, icons, storage
from .i18n import t
from .widgets import Card, Segmented, button, cls, field, hbox, label, notice, toast, link, open_url


def live(card, draw, look=False):
    """draw() hemen ve dil (isteğe bağlı görünüm) değişince çağrılır; kart silinince abonelik kalkar."""
    def safe(*_):
        try:
            draw()
        except RuntimeError:   # silinmiş Qt nesnesi
            for u in uns:
                u()
    uns = [i18n.on_change(safe)]
    if look:
        uns.append(style.on_change(safe))
    card.destroyed.connect(lambda *_: [u() for u in uns])
    draw()
    return card


# ---------------------------------------------------------------- Görünüm
def lang_options():
    box = QWidget()
    g = QGridLayout(box)
    g.setContentsMargins(0, 0, 0, 0)
    g.setSpacing(10)
    btns = {}
    for i, l in enumerate(i18n.LANGS):
        b = QPushButton()
        b.setProperty('fc', 'lang-option')
        b.setCheckable(True)
        b.setCursor(Qt.PointingHandCursor)
        b.setMinimumHeight(46)
        h = QHBoxLayout(b)
        h.setContentsMargins(16, 0, 14, 0)
        b.name = label(i18n.NAMES[l])
        b.name.setFont(style.font(15, 400, l))
        b.check = QLabel()
        h.addWidget(b.name)
        h.addStretch(1)
        h.addWidget(b.check)
        b.clicked.connect(lambda _=False, l=l: i18n.set(l))
        g.addWidget(b, 0, i)
        btns[l] = b

    def draw():
        for l, b in btns.items():
            on = l == i18n.lang()
            b.setChecked(on)
            b.name.setStyleSheet('color:%s' % style.q(style.tok('accent' if on else 'text')))
            if on:
                b.check.setPixmap(icons.pixmap('check', style.tok('accent'), 14))
            else:
                b.check.clear()
    return live(box, draw, look=True), btns


def look_controls():
    from .scheme_picker import SchemePicker
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    picker = SchemePicker()
    f1 = field(t('fc.scheme'), picker)
    seg = Segmented([('dark', t('fc.theme.dark'), 'moon'), ('light', t('fc.theme.light'), 'sun'), ('auto', t('fc.theme.auto'), 'sync')], style.theme())
    seg.changed.connect(style.set_theme)
    f2 = field(t('fc.mode'), seg)
    minus = button('A−\u200e', 'btn small', slot=lambda: style.bump(-1))
    plus = button('A+\u200e', 'btn small', slot=lambda: style.bump(1))
    pct = label('100%')
    pct.setMinimumWidth(48)
    pct.setAlignment(Qt.AlignCenter)
    reset = button(t('fc.font.reset'), 'btn small ghost', slot=lambda: style.set_scale(1))
    for b in (minus, plus):
        b.setLayoutDirection(Qt.LeftToRight)
    f3 = field(t('fc.font'), hbox(minus, pct, plus, reset, None, spacing=10))
    for f in (f1, f2, f3):
        v.addWidget(f)

    def draw():
        f1.label.setText(t('fc.scheme'))
        f2.label.setText(t('fc.mode'))
        f3.label.setText(t('fc.font'))
        for val, b in seg.btns.items():
            b.setText(t('fc.theme.' + val))
        seg.set(style.theme())
        s = style.scale()
        pct.setText('%d%%' % round(s * 100))
        pct.setStyleSheet('font-weight:700')
        minus.setEnabled(s > style.MIN)
        plus.setEnabled(s < style.MAX)
        minus.setToolTip(t('fc.font.smaller'))
        plus.setToolTip(t('fc.font.larger'))
        reset.setText(t('fc.font.reset'))
    return live(w, draw, look=True)


def look_card():
    c = Card('look', t('fc.look'), 'type', t('fc.look.desc'))
    c.add(look_controls())
    lo, _ = lang_options()
    lf = field(t('fc.lang'), lo)
    c.add(lf)

    def draw():
        c.set_title(t('fc.look'))
        c.set_desc(t('fc.look.desc'))
        lf.label.setText(t('fc.lang'))
    return live(c, draw)


# ---------------------------------------------------------------- Kullanım Limitleri
def _meter(lbl, used, mx):
    from . import usage
    pct = min(100.0, used / mx * 100)
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 12, 0, 0)
    v.setSpacing(5)
    head = QHBoxLayout()
    head.setContentsMargins(0, 0, 0, 0)
    a = label(lbl, 'meter-head')
    b = label(i18n.num(used) + ' / ' + i18n.num(mx), 'meter-head')
    b.setStyleSheet('font-weight:600')
    b.setLayoutDirection(Qt.LeftToRight)
    head.addWidget(a)
    head.addStretch(1)
    head.addWidget(b)
    v.addLayout(head)
    bar = QProgressBar()
    bar.setRange(0, 1000)
    bar.setValue(int(round(pct * 10)))
    bar.setTextVisible(False)
    bar.setProperty('fc', 'meter' + (' full' if pct >= 100 else ' warn' if pct >= 80 else ''))
    bar.setAccessibleName(lbl)
    v.addWidget(bar)
    return w


def usage_card(firebase=True, ai=True, project=None, providers=None):
    from . import usage
    c = Card('usage', t('fc.usage.title'), 'gauge')

    def dur(ms):
        h, m = ms // 3600000, ms % 3600000 // 60000
        return ('%d %s ' % (h, t('fc.h')) if h else '') + '%d %s' % (m, t('fc.min'))

    def draw():
        c.clear()
        v = usage.data()
        try:
            proj = (project() if callable(project) else project) or v.get('project') or ''
        except Exception:
            proj = ''
        c.set_title(t('fc.usage.title'))
        c.set_desc(t('fc.usage.none' if firebase is False and ai is False else 'fc.usage.desc'))
        if firebase is not False:
            c.add(label(t('fc.usage.firebase').upper() if i18n.lang() != 'ar' else t('fc.usage.firebase'), 'fc-sub', wrap=True), 16)
            c.add(label(t('fc.usage.project', {'p': proj}) if proj else t('fc.usage.noFirebase'), 'field-hint'), 4)
            c.add(_meter(t('fc.usage.read'), v['c'].get('firebase.read', 0), usage.LIMIT['read']))
            c.add(_meter(t('fc.usage.write'), v['c'].get('firebase.write', 0), usage.LIMIT['write']))
            c.add(_meter(t('fc.usage.delete'), v['c'].get('firebase.delete', 0), usage.LIMIT['delete']))
            if v['c'].get('firebase.full'):
                c.add(notice(t('fc.usage.full'), 'error'), 14)
            c.add(label(t('fc.usage.reset', {'t': dur(usage.ms_to_reset())}) + ' ' + t('fc.usage.device'), 'field-hint', wrap=True), 10)
        if ai is not False:
            c.add(label(t('fc.usage.ai').upper() if i18n.lang() != 'ar' else t('fc.usage.ai'), 'fc-sub', wrap=True), 16)
            lst = QWidget()
            lv = QVBoxLayout(lst)
            lv.setContentsMargins(0, 8, 0, 0)
            lv.setSpacing(6)
            for k in [p for p in (providers or list(usage.PROVIDERS)) if p in usage.PROVIDERS]:
                P = usage.PROVIDERS[k]
                li = QFrame()
                li.setProperty('fc', 'fc-li')
                h = QHBoxLayout(li)
                h.setContentsMargins(10, 8, 10, 8)
                h.setSpacing(10)
                left = QVBoxLayout()
                left.setSpacing(1)
                nm = label(P['name'])
                nm.setStyleSheet('font-weight:700;font-size:%dpx' % round(13 * style.scale()))
                left.addWidget(nm)
                left.addWidget(label(t('fc.ai.' + k + '.note'), 'field-hint', wrap=True))
                right = QVBoxLayout()
                right.setSpacing(1)
                n = label(t('fc.usage.calls', {'n': i18n.num(v['c'].get('ai.' + k, 0))}))
                n.setStyleSheet('font-weight:700;font-size:%dpx' % round(13 * style.scale()))
                n.setAlignment(Qt.AlignRight if i18n.lang() != 'ar' else Qt.AlignLeft)
                right.addWidget(n)
                lk = link(t('fc.usage.limits'), P['limits'])
                lk.setStyleSheet('font-size:%dpx' % round(12 * style.scale()))
                lk.setAlignment(n.alignment())
                right.addWidget(lk)
                h.addLayout(left, 1)
                h.addLayout(right)
                lv.addWidget(li)
            c.add(lst)
    usage.on_change(lambda v: QTimer.singleShot(0, lambda: _safe(draw)))
    tm = QTimer(c)
    tm.timeout.connect(lambda: _safe(draw))
    tm.start(60000)
    return live(c, draw)


def _safe(f):
    try:
        f()
    except RuntimeError:
        pass


# ---------------------------------------------------------------- Çökme
def crash_card():
    from . import crash
    c = Card('crash', t('fc.crash.title'), 'bug', t('fc.crash.desc'))
    cb = QCheckBox()
    cb.setChecked(storage.get('crash.enabled', True) is not False)
    cb.toggled.connect(lambda on: storage.set('crash.enabled', on))
    c.add(cb, 10)
    hint = c.add(label('', 'field-hint'), 10)

    def draw():
        c.set_title(t('fc.crash.title'))
        c.set_desc(t('fc.crash.desc'))
        cb.setText(t('fc.crash.on'))
        hint.setText(t('fc.crash.sent', {'n': crash.sent_today()}))
    return live(c, draw)


# ---------------------------------------------------------------- Hakkında
def about_card(version='', on_check=None, whatsnew=True, onboarding=None):
    c = Card('about', t('fc.settings.about'), 'info')
    vrow = QWidget()
    vh = QHBoxLayout(vrow)
    vh.setContentsMargins(0, 0, 0, 0)
    vh.setSpacing(6)
    vl = label('', 'card-desc')
    vb = label('v' + version, 'version-badge')
    vh.addWidget(vl)
    vh.addWidget(vb)
    vh.addStretch(1)
    c.add(vrow)
    col = QWidget()
    cv = QVBoxLayout(col)
    cv.setContentsMargins(0, 6, 0, 0)
    cv.setSpacing(10)
    b1 = button('', 'btn small', icon='download', slot=on_check) if on_check else None
    b2 = button('', 'btn small', icon='sparkles', slot=lambda: __import__('fccore.whatsnew', fromlist=['x']).show()) if whatsnew else None
    b3 = None
    if onboarding is not False:
        from . import onboarding as ob
        b3 = button('', 'btn small', icon='sparkles', slot=lambda: ob.open(**(onboarding or {})))
    row = QWidget()
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 0, 0, 0)
    rl.setSpacing(10)
    bs = [b for b in (b1, b2, b3) if b]
    for b in bs:
        rl.addWidget(b, 0, Qt.AlignLeading)
    rl.addStretch(1)
    c.add(row, 6)
    # web'de dar kartta düğmeler alt alta sarılır; Qt'de satır taşarsa ikiye böl
    from .widgets import Columns  # noqa: F401

    def draw():
        c.set_title(t('fc.settings.about'))
        vl.setText(t('fc.settings.version'))
        if b1:
            b1.setText(t('fc.update.check'))
        if b2:
            b2.setText(t('fc.wn.show'))
        if b3:
            b3.setText(t('fc.ob.reopen'))
        # sarma: genişlik yetmezse dikey
        rl.setDirection(QHBoxLayout.LeftToRight if sum(b.sizeHint().width() for b in bs) + 20 < 300 else QHBoxLayout.TopToBottom)
    return live(c, draw)


# ---------------------------------------------------------------- İletişim
def contact_card():
    from . import contact
    c = Card('contact', t('fc.contact.title'), 'mail', t('fc.contact.desc'))
    typ = QComboBox()
    msg = QPlainTextEdit()
    msg.setFixedHeight(120)
    reach = QLineEdit()
    reach.setMaxLength(160)
    f1 = c.add(field('', typ))
    f2 = c.add(field('', msg))
    f3 = c.add(field('', reach))
    st = label('', 'field-hint', wrap=True)
    send = button('', 'btn primary', icon='mail')
    c.add(hbox(send, st, spacing=10, margins=(0, 12, 0, 0)))
    priv = c.add(label('', 'field-hint', wrap=True), 12)

    def draw():
        cur = typ.currentData() or 'oneri'
        typ.clear()
        typ.addItem(t('fc.contact.oneri'), 'oneri')
        typ.addItem(t('fc.contact.hata'), 'hata')
        typ.setCurrentIndex(max(0, typ.findData(cur)))
        c.set_title(t('fc.contact.title'))
        c.set_desc(t('fc.contact.desc'))
        f1.label.setText(t('fc.contact.type'))
        f2.label.setText(t('fc.contact.msg'))
        f3.label.setText(t('fc.contact.reach'))
        msg.setPlaceholderText(t('fc.contact.msg'))
        reach.setPlaceholderText(t('fc.contact.reach'))
        send.setText(t('fc.contact.send'))
        priv.setText(t('fc.contact.privacy'))
        n = len(contact.queue())
        st.setText(t('fc.contact.waiting', {'n': n}) if n else '')

    def go():
        m = msg.toPlainText().strip()
        if not m:
            st.setText(t('fc.contact.empty'))
            cls(msg, 'invalid')
            msg.setFocus()
            return
        cls(msg, '')
        send.setEnabled(False)
        st.setText(t('fc.contact.sending'))

        def done(r):
            QTimer.singleShot(0, lambda: _sent(r))
        contact.post_async({'tur': typ.currentData(), 'mesaj': m, 'iletisim': reach.text().strip()}, use_mail=True, done=_relay(done))

    def _sent(r):
        msg.setPlainText('')
        st.setText(t('fc.contact.ok' if r == 'sent' else 'fc.contact.queued'))
        toast(st.text(), '' if r == 'sent' else 'info')
        send.setEnabled(True)
    send.clicked.connect(go)
    return live(c, draw)


def _relay(f):
    """İş parçacığından ana iş parçacığına güvenli çağrı."""
    from PySide6.QtCore import QObject, Signal

    class R(QObject):
        sig = Signal(object)
    r = R()
    r.sig.connect(f)
    _relay.keep = getattr(_relay, 'keep', [])
    _relay.keep.append(r)
    return lambda v: r.sig.emit(v)
