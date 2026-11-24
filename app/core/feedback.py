"""'Teşhis doğru muydu?' geri bildirimi.

Kullanıcının izniyle yalnız teşhis ÖZETİ gönderilir (log dosyası, konum, kişisel bilgi gönderilmez):
program sürümü, araç tipi/profili, yazılım sürümü, programın kararı ve kök nedeni, güven, kanıt anahtarları,
sağlık puanları, kullanıcının verdiği gerçek sonuç ve neden, isteğe bağlı not.
Admin iletişimiyle aynı Firestore projesinde 'teshis_geri_bildirim' koleksiyonuna yazılır; internet yoksa sıraya
alınır ve sonraki açılışta gönderilir. Geri bildirimler gerçek kaza test setini (crashbench) büyütmek için kullanılır.
"""
from __future__ import annotations
import hashlib, json, os, time, urllib.request
from ..version import VERSION
from .paths import data_dir
from . import contact

COLLECTION = 'teshis_geri_bildirim'
CAUSES = ['gps', 'ekf', 'battery', 'radio', 'stall', 'vibration', 'compass', 'power', 'control', 'motor', 'unknown']
OUTCOMES = ['crash', 'incident', 'normal']


def _url():
    # admin iletişim kutusunun adresi; yalnız koleksiyon adı farklı
    return contact._FS.replace('/documents/mesajlar', '/documents/' + COLLECTION)


def _queue_path():
    return os.path.join(data_dir(), 'feedback_queue.json')


def summary(A):
    """Gönderilecek, kişisel veri içermeyen teşhis özeti."""
    L = A.L
    root = A.root or {}
    fid = hashlib.sha256(f'{os.path.basename(L.path)}|{L.size}|{L.duration:.1f}'.encode()).hexdigest()[:16]
    return {
        'log_id': fid, 'app': VERSION, 'vehicle': A.vehicle, 'profile': A.profile, 'fw': (L.version or '')[:60],
        'size_mb': round(L.size / 1e6, 1), 'dur_s': round(float(L.duration)),
        'verdict': A.verdict.get('kind'), 'score': A.verdict.get('score'), 'cause': root.get('cause'),
        'others': root.get('others') or [], 'conf': (getattr(A, 'why', {}) or {}).get('conf'),
        'evidence': [e.get('k') for e in A.verdict.get('evidence', [])],
        'health': {k: v.get('score') for k, v in A.health.items()},
        'findings': sorted({f.get('k') for v in A.health.values() for f in v.get('findings', [])}),
        'motor': root.get('motor'), 'gaps': list(getattr(A, 'gaps', []) or []),
    }


def build(A, verdict_ok, real_outcome, real_cause, note='', lang='tr'):
    d = summary(A)
    d.update({'user_ok': verdict_ok, 'user_outcome': real_outcome, 'user_cause': real_cause, 'note': (note or '')[:1500], 'lang': lang,
              'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
    return d


def _fs_fields(d):
    def val(v):
        if v is None: return {'nullValue': None}
        if isinstance(v, bool): return {'booleanValue': v}
        if isinstance(v, int): return {'integerValue': str(v)}
        if isinstance(v, float): return {'doubleValue': v}
        if isinstance(v, (list, tuple)): return {'arrayValue': {'values': [val(x) for x in v]}}
        if isinstance(v, dict): return {'mapValue': {'fields': {str(k): val(x) for k, x in v.items()}}}
        return {'stringValue': str(v)[:4000]}
    return {k: val(v) for k, v in d.items()}


def _post(d):
    body = json.dumps({'fields': _fs_fields(d)}).encode()
    req = urllib.request.Request(_url(), data=body, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status < 300


def _load_q():
    try: return json.load(open(_queue_path(), encoding='utf-8'))
    except Exception: return []


def _save_q(q):
    try:
        os.makedirs(os.path.dirname(_queue_path()), exist_ok=True)
        json.dump(q[-200:], open(_queue_path(), 'w', encoding='utf-8'), ensure_ascii=False)
    except Exception:
        pass


def send(d):
    """True: gönderildi; False: sıraya alındı (internet yok)."""
    try:
        if _post(d): return True
    except Exception:
        pass
    q = _load_q(); q.append(d); _save_q(q)
    return False


def flush():
    """Sıradaki geri bildirimleri göndermeyi dener (açılışta arka planda). Gönderilen sayısını döndürür."""
    q = _load_q()
    if not q: return 0
    left = []; n = 0
    for d in q:
        try:
            if _post(d): n += 1; continue
        except Exception:
            pass
        left.append(d)
    _save_q(left)
    return n
