"""fccore.onboarding — ilk açılış sihirbazı: dil → görünüm → kendi Firebase'iniz → kendi AI anahtarınız (isteğe bağlı) → bitti.
    onboarding.maybe_start(on_firebase=lambda cfg, code: ..., on_ai=lambda v: ...)   # yalnız ilk açılışta
    onboarding.open(firebase=False, ai=False)                                       # Ayarlar'dan; adım çıkarılabilir
Varsayılan olarak yapılandırma 'firebase.config', anahtar 'ai' altında storage'a yazılır; store=False ise yalnız geri çağrılar."""
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from . import storage, i18n, usage
from .i18n import t

GUIDE = 'https://github.com/departures-mil/duyurular/blob/main/firebase-kurulum.md'
AI = {
    'gemini': {'name': 'Google Gemini', 'key': 'https://aistudio.google.com/app/apikey'},
    'openai': {'name': 'OpenAI', 'key': 'https://platform.openai.com/api-keys'},
    'anthropic': {'name': 'Anthropic Claude', 'key': 'https://console.anthropic.com/settings/keys'},
    'groq': {'name': 'Groq', 'key': 'https://console.groq.com/keys'},
}
KEYS = ['apiKey', 'authDomain', 'projectId', 'storageBucket', 'messagingSenderId', 'appId', 'measurementId', 'databaseURL']


def parse_firebase(text):
    """firebaseConfig metni (JSON ya da `const firebaseConfig = {...}` kodu) → dict; geçersizse None."""
    s = str(text or '')
    a, b = s.find('{'), s.rfind('}')
    if a < 0 or b <= a:
        return None
    s = s[a:b + 1]
    try:
        o = json.loads(s)
    except ValueError:
        try:
            j = re.sub(r'//[^\n]*', '', s)
            j = re.sub(r'/\*[\s\S]*?\*/', '', j)
            j = re.sub(r'([{,]\s*)([A-Za-z_$][\w$]*)\s*:', r'\1"\2":', j)
            j = re.sub(r"'((?:[^'\\]|\\.)*)'", lambda m: json.dumps(m.group(1).replace("\\'", "'")), j)
            j = re.sub(r',\s*([}\]])', r'\1', j)
            o = json.loads(j)
        except ValueError:
            return None
    if not isinstance(o, dict):
        return None
    if not re.fullmatch(r'AIza[0-9A-Za-z_-]{30,}', str(o.get('apiKey') or '')) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{3,38}[a-z0-9]', str(o.get('projectId') or '')):
        return None
    return {k: str(o[k]) for k in KEYS if o.get(k)}


def _get(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=dict(headers or {}, **{'User-Agent': 'FalconCekirdek-Qt/1.0'}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read()
        except Exception:
            return e.code, b''


def test_firebase(c, get=None):
    """Var olmayan bir belgeyi okur → 'ok'|'rules'|'nodb'|'badkey'|'net' (web ile aynı yorum)."""
    url = 'https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents/_fc_baglanti/deneme?key=%s' % (
        urllib.parse.quote(c['projectId']), urllib.parse.quote(c['apiKey']))
    try:
        st, raw = (get or _get)(url)
    except Exception:
        return 'net'
    try:
        j = json.loads(raw.decode('utf-8') or '{}')
    except Exception:
        j = {}
    usage.count('firebase.read')
    msg = str(((j or {}).get('error') or {}).get('message') or '')
    if 200 <= st < 300:
        return 'ok'
    if st == 404 and not re.search(r'database|does not exist', msg, re.I):
        return 'ok'
    if st == 404 or re.search(r'has not been used|is disabled|does not exist', msg, re.I):
        return 'nodb'
    if st == 400 or re.search(r'API key', msg, re.I):
        return 'badkey'
    if st == 403:
        return 'rules'
    return 'net'


def test_ai(p, key, get=None):
    h = {}
    if p == 'gemini':
        u = 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1&key=' + urllib.parse.quote(key)
    elif p == 'openai':
        u, h = 'https://api.openai.com/v1/models', {'Authorization': 'Bearer ' + key}
    elif p == 'groq':
        u, h = 'https://api.groq.com/openai/v1/models', {'Authorization': 'Bearer ' + key}
    elif p == 'anthropic':
        u, h = 'https://api.anthropic.com/v1/models?limit=1', {'x-api-key': key, 'anthropic-version': '2023-06-01'}
    else:
        return 'unknown'
    try:
        st, _ = (get or _get)(u, h)
    except Exception:
        return 'unknown'
    return 'ok' if 200 <= st < 300 else 'bad' if st in (400, 401, 403) else 'unknown'


class _Bg(QObject):
    done = Signal(object)


def _bg(fn, cb):
    r = _Bg()
    r.done.connect(cb)
    _bg.keep = getattr(_bg, 'keep', [])
    _bg.keep.append(r)
    threading.Thread(target=lambda: r.done.emit(fn()), daemon=True).start()


def open(firebase=True, ai=True, store=True, on_firebase=None, on_ai=None, on_close=None, guide_url=None, parent=None, start_step=0):  # noqa: A001
    from .widgets import Modal, label, button, field, notice, cls, link, hbox
    from .cards import look_controls, lang_options
    steps = ['lang', 'look'] + (['firebase'] if firebase is not False else []) + (['ai'] if ai is not False else []) + ['done']
    st = {'i': start_step, 'fb_text': '', 'fb_conf': storage.get('firebase.config'), 'fb_res': None,
          'ai': storage.get('ai') or {'provider': 'gemini', 'key': ''}}

    def closed():
        storage.set('onboarding.done', True)
        if on_close:
            on_close()
    m = Modal(parent=parent, title=t('fc.ob.welcome'), icon='sparkles', buttons=[], on_close=closed)

    def save_ai():
        if not st['ai'].get('key'):
            return
        v = {'provider': st['ai']['provider'], 'key': st['ai']['key']}
        if store:
            storage.set('ai', v)
        if on_ai:
            on_ai(v)

    def render():
        s = steps[st['i']]
        titles = {'lang': 'fc.ob.welcome', 'look': 'fc.ob.lookTitle', 'firebase': 'fc.ob.fbTitle', 'ai': 'fc.ob.aiTitle', 'done': 'fc.ob.doneTitle'}
        ics = {'lang': 'globe', 'look': 'type', 'firebase': 'cloud', 'ai': 'key', 'done': 'check'}
        m.set_title(t(titles[s]), ics[s])
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)
        dots = QFrame()
        dots.setProperty('fc', 'fc-steps')
        dl = QHBoxLayout(dots)
        dl.setContentsMargins(0, 0, 0, 6)
        dl.setSpacing(6)
        for k in range(len(steps)):
            d = QFrame()
            if k <= st['i']:
                d.setProperty('fc', 'on')
            dl.addWidget(d, 1)
        dots.setAccessibleName(t('fc.ob.step', {'i': st['i'] + 1, 'n': len(steps)}))
        v.addWidget(dots)
        if s == 'lang':
            v.addWidget(label(t('fc.ob.langDesc'), 'muted', wrap=True))
            v.addWidget(lang_options()[0])
        if s == 'look':
            v.addWidget(label(t('fc.ob.lookDesc'), 'muted', wrap=True))
            v.addWidget(look_controls())
        if s == 'firebase':
            v.addWidget(label(t('fc.ob.fbDesc'), wrap=True))
            v.addWidget(hbox(link(t('fc.ob.fbGuide'), guide_url or GUIDE), link(t('fc.ob.fbConsole'), 'https://console.firebase.google.com/'), None, spacing=16))
            ta = QPlainTextEdit()
            ta.setFixedHeight(150)
            ta.setLayoutDirection(Qt.LeftToRight)
            ta.setPlaceholderText('{ "apiKey": "AIza…", "authDomain": "…", "projectId": "…", "appId": "…" }')
            ta.setPlainText(st['fb_text'] or (json.dumps(st['fb_conf'], indent=2) if st['fb_conf'] else ''))
            ta.setStyleSheet('font-family: Consolas, "DejaVu Sans Mono", monospace;')
            res = QWidget()
            rl = QVBoxLayout(res)
            rl.setContentsMargins(0, 0, 0, 0)

            def show_res(kind, text):
                while rl.count():
                    rl.takeAt(0).widget().deleteLater()
                st['fb_res'] = (kind, text)
                rl.addWidget(notice(text, kind))
            if st['fb_res']:
                show_res(*st['fb_res'])
            test = button(t('fc.ob.test'), 'btn', icon='cloud')

            def on_text():
                st['fb_text'] = ta.toPlainText()
                cls(ta, '')
            ta.textChanged.connect(on_text)

            def do_test():
                c = parse_firebase(ta.toPlainText())
                if not c:
                    cls(ta, 'invalid')
                    show_res('error', t('fc.ob.fbBad'))
                    return
                test.setEnabled(False)
                test.setText(t('fc.ob.testing'))

                def done(code):
                    try:
                        test.setEnabled(True)
                        test.setText(t('fc.ob.test'))
                    except RuntimeError:
                        pass
                    mp = {'ok': ('ok', 'fc.ob.fbOk'), 'rules': ('', 'fc.ob.fbRules'), 'nodb': ('error', 'fc.ob.fbNoDb'),
                          'badkey': ('error', 'fc.ob.fbBadKey'), 'net': ('error', 'fc.ob.fbNet')}[code]
                    try:
                        show_res(mp[0], t(mp[1], {'p': c['projectId']}))
                    except RuntimeError:
                        st['fb_res'] = (mp[0], t(mp[1], {'p': c['projectId']}))
                    if code in ('ok', 'rules'):
                        st['fb_conf'] = c
                        if store:
                            storage.set('firebase.config', c)
                        usage.set_project(c['projectId'])
                        if on_firebase:
                            on_firebase(c, code)
                _bg(lambda: test_firebase(c), done)
            test.clicked.connect(do_test)
            v.addWidget(field(t('fc.ob.fbPaste'), ta))
            v.addWidget(hbox(test, None))
            v.addWidget(res)
            v.addWidget(label(t('fc.ob.fbLater'), 'field-hint', wrap=True))
        if s == 'ai':
            v.addWidget(label(t('fc.ob.aiDesc'), wrap=True))
            sel = QComboBox()
            for k, a in AI.items():
                sel.addItem(a['name'], k)
            sel.setCurrentIndex(max(0, sel.findData(st['ai'].get('provider') or 'gemini')))
            key = QLineEdit()
            key.setEchoMode(QLineEdit.Password)
            key.setLayoutDirection(Qt.LeftToRight)
            key.setPlaceholderText('sk-… / AIza… / gsk_…')
            key.setText(st['ai'].get('key') or '')
            hint = QWidget()
            hl = QVBoxLayout(hint)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(2)

            def draw_link():
                while hl.count():
                    hl.takeAt(0).widget().deleteLater()
                p = sel.currentData()
                hl.addWidget(link(t('fc.ob.aiGet') + ' — ' + AI[p]['name'], AI[p]['key']))
                hl.addWidget(label(t('fc.ai.' + p + '.note'), 'field-hint', wrap=True))
            draw_link()
            sel.currentIndexChanged.connect(lambda *_: (st['ai'].__setitem__('provider', sel.currentData()), draw_link()))
            key.textChanged.connect(lambda x: st['ai'].__setitem__('key', x.strip()))
            res2 = QWidget()
            r2 = QVBoxLayout(res2)
            r2.setContentsMargins(0, 0, 0, 0)
            test2 = button(t('fc.ob.test'), 'btn', icon='key')

            def do_test2():
                if not st['ai'].get('key'):
                    cls(key, 'invalid')
                    return
                cls(key, '')
                test2.setEnabled(False)

                def done(r):
                    try:
                        test2.setEnabled(True)
                        save_ai()
                        while r2.count():
                            r2.takeAt(0).widget().deleteLater()
                        r2.addWidget(notice(t('fc.ob.aiOk' if r == 'ok' else 'fc.ob.aiBad' if r == 'bad' else 'fc.ob.aiUnk'), 'ok' if r == 'ok' else 'error' if r == 'bad' else ''))
                    except RuntimeError:
                        pass
                p, k = st['ai']['provider'], st['ai']['key']
                _bg(lambda: test_ai(p, k), done)
            test2.clicked.connect(do_test2)
            v.addWidget(field(t('fc.ob.aiProvider'), sel))
            v.addWidget(field(t('fc.ob.aiKey'), key, hint))
            v.addWidget(hbox(test2, None))
            v.addWidget(res2)
        if s == 'done':
            v.addWidget(label(t('fc.ob.doneDesc'), wrap=True))
        m.set_body(body)
        last = st['i'] == len(steps) - 1
        btns = []
        if not last and st['i'] > 0:
            btns.append({'label': t('fc.skip'), 'cls': 'ghost', 'on_click': lambda _m: go(1)})
        btns.append('spacer')
        if st['i'] > 0:
            btns.append({'label': t('fc.back'), 'on_click': lambda _m: go(-1)})

        def nxt(_m):
            if s == 'ai':
                save_ai()
            if last:
                return True
            return go(1)
        btns.append({'label': t('fc.ob.start') if last else t('fc.next'), 'cls': 'primary', 'on_click': nxt})
        m.set_buttons(btns)

    def go(d):
        st['i'] = max(0, min(len(steps) - 1, st['i'] + d))
        render()
        return False

    def relang(l):
        try:
            if m.isVisible():
                render()
        except RuntimeError:
            un()
    un = i18n.on_change(relang)
    m.closed.connect(lambda: un())
    render()
    return m


def maybe_start(**opts):
    if not storage.get('onboarding.done', False):
        return open(**opts)
    return None
