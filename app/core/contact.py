"""Admin ile iletişim: öneri / hata bildirimi (yalnız Firestore mesaj kutusu; programda kişisel e-posta adresi yoktur)."""
from __future__ import annotations
import json, platform, time, urllib.request
from ..version import VERSION, APP_NAME

_FS = ('https://firestore.googleapis.com/v1/projects/comm-calc-103111111/databases/(default)/documents/mesajlar'
       '?key=AIzaSyB12RFS6ENPpmnnPsETfjedNH-3hmNWQvA')


def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **headers}, method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode('utf-8', 'replace')


def send(message, name='', mail='', lang='tr'):
    """Mesaj kutusu kabul ederse True."""
    plat = f'{APP_NAME} · {platform.system()} {platform.release()}'
    def F(v): return {'stringValue': v[:4000]}
    fields = {'mesaj': F(message), 'konu': F(f'{APP_NAME} · Mesaj'), 'dil': F(lang), 'surum': F(VERSION),
              'platform': F(plat), 'zaman': {'timestampValue': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}}
    if name: fields['ad'] = F(name)
    if mail: fields['iletisim'] = F(mail)
    try:
        return _post(_FS, {'fields': fields}, {})[0] < 300
    except Exception:
        return False
