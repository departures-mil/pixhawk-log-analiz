"""Admin ile iletişim: öneri / hata bildirimi (Firestore mesaj kutusu + e-posta kopyası)."""
from __future__ import annotations
import base64, json, platform, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from ..version import VERSION, APP_NAME

_FS = ('https://firestore.googleapis.com/v1/projects/comm-calc-103111111/databases/(default)/documents/mesajlar'
       '?key=AIzaSyB12RFS6ENPpmnnPsETfjedNH-3hmNWQvA')
_TO = base64.b64decode('').decode()[::-1]


def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **headers}, method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode('utf-8', 'replace')


def send(message, name='', mail='', lang='tr'):
    """İki kanaldan biri kabul ederse True."""
    plat = f'{APP_NAME} · {platform.system()} {platform.release()}'
    def F(v): return {'stringValue': v[:4000]}
    fields = {'mesaj': F(message), 'konu': F(f'{APP_NAME} · Mesaj'), 'dil': F(lang), 'surum': F(VERSION),
              'platform': F(plat), 'zaman': {'timestampValue': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}}
    if name: fields['ad'] = F(name)
    if mail: fields['iletisim'] = F(mail)
    body = {'_subject': f'{APP_NAME}: yeni mesaj', '_template': 'table', '_captcha': 'false', 'Ad': name or '-',
            'Mesaj': message, 'Surum': VERSION, 'Cihaz': plat, 'Dil': lang}
    if mail: body['email'] = mail; body['_replyto'] = mail

    def inbox():
        try: return _post(_FS, {'fields': fields}, {})[0] < 300
        except Exception: return False

    def email():
        try:
            st, txt = _post('https://formsubmit.co/ajax/' + _TO, body,
                            {'Accept': 'application/json', 'Referer': 'https://formsubmit.co/', 'Origin': 'https://formsubmit.co',
                             'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) PixhawkLogAnaliz/{VERSION}'})
            return str(json.loads(txt or '{}').get('success')).lower() == 'true'
        except Exception:
            return False

    with ThreadPoolExecutor(2) as ex:
        a, b = ex.submit(inbox), ex.submit(email)
        return a.result() or b.result()
