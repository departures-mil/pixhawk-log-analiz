"""fccore.usage — "Kullanım Limitleri": kullanıcının KENDİ Firebase'indeki bugünkü okuma/yazma/silme sayısı
(Spark: 50k / 20k / 20k) ve sağlayıcı başına yapay zeka çağrıları. Gün Pasifik saatiyle döner. Web FC.usage ile aynı anahtarlar.
    usage.count('firebase.read', 3); usage.count('ai.gemini'); usage.count('firebase.full')
    usage.count_http(method, url, body, status, json)   # Firestore REST / AI isteğinden sonra (isteğe bağlı otomatik sayım)
    usage.card(firebase=False, ai=False)  → bulut/AI yoksa "sınırlı hizmet yok" kipi"""
import json
import re
import time
from datetime import datetime, timedelta, timezone

from . import storage

LIMIT = {'read': 50000, 'write': 20000, 'delete': 20000}
KEY = 'usage'
PROVIDERS = {
    'gemini': {'name': 'Google Gemini', 'limits': 'https://ai.google.dev/gemini-api/docs/rate-limits', 'host': re.compile(r'generativelanguage\.googleapis\.com')},
    'openai': {'name': 'OpenAI', 'limits': 'https://platform.openai.com/settings/organization/limits', 'host': re.compile(r'api\.openai\.com')},
    'anthropic': {'name': 'Anthropic Claude', 'limits': 'https://console.anthropic.com/settings/limits', 'host': re.compile(r'api\.anthropic\.com')},
    'groq': {'name': 'Groq', 'limits': 'https://console.groq.com/settings/limits', 'host': re.compile(r'api\.groq\.com')},
}
cfg = {'now': None}
_subs = []


def _now():
    return cfg['now']() if cfg.get('now') else datetime.now(timezone.utc)


def pacific(d):
    try:
        from zoneinfo import ZoneInfo
        return d.astimezone(ZoneInfo('America/Los_Angeles'))
    except Exception:
        return d.astimezone(timezone(timedelta(hours=-8)))


def today():
    return pacific(_now()).strftime('%Y-%m-%d')


def ms_to_reset():
    p = pacific(_now())
    return max(0, 86400000 - ((p.hour * 3600 + p.minute * 60 + p.second) * 1000))


def data():
    v, d = storage.get(KEY), today()
    if not isinstance(v, dict) or v.get('day') != d:
        v = {'day': d, 'c': {}, 'project': (v or {}).get('project', '') if isinstance(v, dict) else ''}
        storage.set(KEY, v)
    return v


def count(key, n=1):
    n = 1 if n is None else (n or 0)
    if n <= 0:
        return
    v = data()
    v['c'][key] = v['c'].get(key, 0) + n
    storage.set(KEY, v)
    for f in list(_subs):
        try:
            f(v)
        except Exception:
            pass


def get(key):
    return data()['c'].get(key, 0)


def set_project(p):
    v = data()
    if p and v.get('project') != p:
        v['project'] = p
        storage.set(KEY, v)


def on_change(f):
    _subs.append(f)
    return lambda: _subs.remove(f) if f in _subs else None


def provider(url):
    for k, p in PROVIDERS.items():
        if p['host'].search(url):
            return k
    return ''


def count_http(method, url, body=None, status=200, resp_json=None):
    """Bir HTTP isteğinden sonra çağrılır; web wrapFetch() ile aynı sınıflandırma."""
    url = str(url)
    ai = provider(url)
    if ai:
        count('ai.' + ai)
        if status == 429:
            count('ai.' + ai + '.full')
        return
    if not re.search(r'firestore\.googleapis\.com/v1/', url) or re.search(r'comm-calc-103111111/databases/\(default\)/documents/mesajlar', url):
        return
    m = re.search(r'/projects/([^/]+)/', url)
    if m and 200 <= status < 300:
        set_project(m.group(1))
    if status == 429:
        count('firebase.full')
        return
    if not 200 <= status < 300:
        return
    path = url.split('?')[0]
    if re.search(r':(listen|write)\b|/Listen/|/Write/', path) or re.search(r':beginTransaction$|:rollback$', path):
        return
    if re.search(r':commit$|:batchWrite$', path):
        try:
            b = json.loads(body) if isinstance(body, (str, bytes)) else body
        except Exception:
            b = None
        for w in (b or {}).get('writes', []) if isinstance(b, dict) else []:
            count('firebase.delete' if isinstance(w, dict) and w.get('delete') else 'firebase.write')
        return
    method = str(method or 'GET').upper()
    if re.search(r':runQuery$|:runAggregationQuery$|:batchGet$', path) or (method == 'GET' and len([x for x in (path.split('/documents')[1:] or [''])[0].split('/') if x]) % 2 == 1):
        j = resp_json
        n = len([x for x in j if isinstance(x, dict) and (x.get('document') or x.get('found'))]) if isinstance(j, list) else len((j or {}).get('documents') or []) if isinstance(j, dict) else 0
        count('firebase.read', max(1, n))
        return
    if method == 'GET':
        return count('firebase.read')
    if method == 'DELETE':
        return count('firebase.delete')
    count('firebase.write')


def card(**o):
    from .cards import usage_card
    return usage_card(**o)
