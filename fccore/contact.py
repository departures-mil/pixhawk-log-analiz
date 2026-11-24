"""fccore.contact — "Admin ile iletişim" (SPEC "Admin gelen kutusu"; web FC.contact ile aynı alanlar ve adres).
    contact.init(app='organizer', version='2.2.0')
    contact.send(tur='oneri'|'hata', mesaj='…', iletisim='')  → 'sent' | 'queued'
    contact.card()  → Ayarlar kartı (settings.build bunu EN SONA koyar)
Firestore REST (comm-calc-103111111 / mesajlar, yalnız ekleme). Gönderilemeyen yerel kuyruğa alınır (en çok 30),
sonra tekrar denenir. Kullanıcı mesajında yedek FormSubmit kullanılır; çökme raporları yalnız gelen kutusuna gider."""
import base64
import json
import os
import platform as _pf
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request

from . import storage, i18n

INBOX = 'https://firestore.googleapis.com/v1/projects/comm-calc-103111111/databases/(default)/documents/mesajlar?key=AIzaSyB12RFS6ENPpmnnPsETfjedNH-3hmNWQvA'
QKEY, MAXQ = 'contact.queue', 30
cfg = {'app': '', 'version': '', 'post': None}
_lock = threading.Lock()
_subs = []


def _to():
    return base64.b64decode('').decode()[::-1]


def device_id():
    d = storage.get('device')
    if not d:
        d = secrets.token_hex(9)
        storage.set('device', d)
    return d


def platform():
    s = sys.platform
    os_ = 'windows' if s.startswith('win') else 'mac' if s == 'darwin' else 'linux' if s.startswith('linux') else s
    return 'qt/' + os_


def version():
    v = cfg.get('version')
    try:
        return str(v() if callable(v) else v or '')
    except Exception:
        return ''


def fields(o):
    f = {'tur': o.get('tur') or 'oneri', 'uygulama': cfg.get('app') or '', 'surum': version(), 'platform': platform(),
         'dil': i18n.lang(), 'mesaj': str(o.get('mesaj') or '')[:5000],
         'zaman': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()) + '.%03dZ' % (int(time.time() * 1000) % 1000), 'cihaz': device_id()}
    if o.get('iletisim'):
        f['iletisim'] = str(o['iletisim'])[:160]
    return f


def payload(f):
    """Firestore belge gövdesi: her alan stringValue."""
    return {'fields': {k: {'stringValue': str(v)} for k, v in f.items()}}


def _http_post(url, body, headers):
    req = urllib.request.Request(url, data=body, headers=dict(headers, **{'User-Agent': 'FalconCekirdek-Qt/1.0'}), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception:
        return 0, b''


def _post(url, obj, headers):
    fn = cfg.get('post') or _http_post
    return fn(url, json.dumps(obj, ensure_ascii=False).encode('utf-8'), dict({'Content-Type': 'application/json'}, **headers))


def inbox(f):
    st, _ = _post(INBOX, payload(f), {})
    return 200 <= st < 300


def mail(f):
    body = {'_subject': (f.get('uygulama') or 'Uygulama') + ': ' + f['tur'], '_template': 'table', '_captcha': 'false', 'Tur': f['tur'],
            'Mesaj': f['mesaj'], 'Uygulama': f['uygulama'], 'Surum': f['surum'], 'Platform': f['platform'], 'Dil': f['dil'], 'Cihaz': f['cihaz']}
    if f.get('iletisim'):
        body['Iletisim'] = f['iletisim']
        if '@' in f['iletisim']:
            body['_replyto'] = f['iletisim']
    st, raw = _post('https://formsubmit.co/ajax/' + _to(), body, {'Accept': 'application/json'})
    try:
        return str(json.loads(raw.decode('utf-8') or '{}').get('success')).lower() == 'true'
    except Exception:
        return False


def deliver(item):
    if inbox(item['f']):
        return True
    return mail(item['f']) if item.get('mail') else False


def queue():
    q = storage.get(QKEY, [])
    return q if isinstance(q, list) else []


def _set_queue(q):
    storage.set(QKEY, q[-MAXQ:])
    for f in list(_subs):
        try:
            f(len(q))
        except Exception:
            pass


def on_queue(f):
    _subs.append(f)


def post(o, use_mail=False):
    """Ham gönderim (çökme raporu da bunu kullanır). Engelleyici — arka planda çağırın."""
    item = {'f': fields(o), 'mail': bool(use_mail)}
    if deliver(item):
        flush()
        return 'sent'
    with _lock:
        q = queue()
        q.append(item)
        _set_queue(q)
    return 'queued'


def send(tur='oneri', mesaj='', iletisim=''):
    return post({'tur': 'hata' if tur == 'hata' else 'oneri', 'mesaj': mesaj, 'iletisim': iletisim}, use_mail=True)


def post_async(o, use_mail=False, done=None):
    def w():
        r = post(o, use_mail)
        if done:
            done(r)
    threading.Thread(target=w, name='fc-contact', daemon=True).start()


def flush():
    if not _lock.acquire(blocking=False):
        return
    try:
        while True:
            q = queue()
            if not q:
                return
            if not deliver(q[0]):
                return
            rest = queue()
            rest.pop(0)
            _set_queue(rest)
    finally:
        _lock.release()


def init(app=None, version=None, post_fn=None, flush_delay=5.0):
    if app is not None:
        cfg['app'] = app
    if version is not None:
        cfg['version'] = version
    if post_fn is not None:
        cfg['post'] = post_fn
    if flush_delay is not None and not getattr(init, 'done', False):
        init.done = True

        def loop():
            time.sleep(flush_delay)
            while True:
                try:
                    flush()
                except Exception:
                    pass
                time.sleep(300)
        threading.Thread(target=loop, name='fc-contact-flush', daemon=True).start()


def card():
    from .cards import contact_card
    return contact_card()
