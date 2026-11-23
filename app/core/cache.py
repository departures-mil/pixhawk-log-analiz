"""Okunmuş log önbelleği: aynı dosya ikinci kez açıldığında ayrıştırma atlanır (saniyenin altında açılır).

Anahtar: dosya içerik kimliği (boyut + ilk/son 4 MB SHA-256) + okuyucu sürümü. Önbellek boyutu sınırlıdır;
en eski kullanılanlar silinir. Yalnızca türetilmiş veri saklanır, orijinal log asla değiştirilmez.
"""
from __future__ import annotations
import json, os, time
import numpy as np
from .paths import data_dir

MAX_MB = 3000


def _dir():
    d = os.path.join(data_dir(), 'cache'); os.makedirs(d, exist_ok=True); return d


def _key(path):
    from .archive import file_uid
    from .loader import LOADER_VER
    return f'{file_uid(path)[:32]}_v{LOADER_VER}'


def get(path):
    from .loader import LogData, Series
    k = _key(path); base = os.path.join(_dir(), k)
    if not (os.path.exists(base + '.npz') and os.path.exists(base + '.json')):
        return None
    with open(base + '.json', encoding='utf-8') as f:
        meta = json.load(f)
    z = np.load(base + '.npz', allow_pickle=False)
    L = LogData()
    for a in ('kind', 'version', 'vehicle', 'board', 'duration', 't0_us', 'truncated', 'types_seen'):
        setattr(L, a, meta.get(a, getattr(L, a)))
    L.path = path; L.size = os.path.getsize(path)
    L.params = meta['params']; L.texts = [tuple(x) for x in meta['texts']]
    L.modes = [tuple(x) for x in meta['modes']]; L.errors = [tuple(x) for x in meta['errors']]
    L.events = [tuple(x) for x in meta['events']]; L.arm = [tuple(x) for x in meta['arm']]
    L.gps_time0 = tuple(meta['gps_time0']) if meta.get('gps_time0') else None
    msgs = {}
    for key in z.files:
        name, fld = key.split('|', 1)
        msgs.setdefault(name, Series())[fld] = z[key]
    for alias, target in meta.get('alias', {}).items():
        if target in msgs: msgs[alias] = msgs[target]
    L.msgs = msgs
    L.from_cache = True
    try: os.utime(base + '.npz', None)
    except Exception: pass
    return L


def put(path, L):
    k = _key(path); base = os.path.join(_dir(), k)
    arrays = {}; alias = {}; seen = {}
    for name, s in L.msgs.items():
        sid = id(s)
        if sid in seen: alias[name] = seen[sid]; continue
        seen[sid] = name
        for f, v in s.items():
            v = np.asarray(v)
            if v.dtype.kind in 'fiub': arrays[f'{name}|{f}'] = v
    meta = {a: getattr(L, a) for a in ('kind', 'version', 'vehicle', 'board', 'duration', 't0_us', 'truncated', 'types_seen')}
    meta.update(params=L.params, texts=L.texts, modes=L.modes, errors=L.errors, events=L.events, arm=L.arm,
                gps_time0=L.gps_time0, alias=alias, src=os.path.basename(path), saved=time.strftime('%Y-%m-%d %H:%M:%S'))
    tmp = base + '.tmp.npz'
    np.savez(tmp, **arrays)
    os.replace(tmp, base + '.npz')
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, default=float)
    prune()


def size_mb():
    d = _dir()
    return sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d)) / 1e6


def prune(max_mb=None):
    max_mb = max_mb or MAX_MB
    d = _dir()
    files = [os.path.join(d, f) for f in os.listdir(d) if f.endswith('.npz')]
    files.sort(key=os.path.getmtime)
    tot = sum(os.path.getsize(f) for f in files)
    while files and tot > max_mb * 1e6:
        f = files.pop(0); tot -= os.path.getsize(f)
        for p in (f, f[:-4] + '.json'):
            try: os.remove(p)
            except Exception: pass


def clear():
    prune(0.000001)
