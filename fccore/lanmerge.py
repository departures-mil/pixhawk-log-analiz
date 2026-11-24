"""fccore.lanmerge — Wi-Fi/LAN eşitlemesinin saf birleştirme kuralı; web/js/lan-sync-merge.js ile BİREBİR aynı anlam
(ortak test vektörleri: tests/fixtures/merge_vectors.json → web çıktısı merge_expected.json).

    r = merge(yerel, uzak, idKey='id', updatedKey='updatedAt')
    r['records']   yazılacak canlı kayıtlar (arşivlenenler archived:True ile)
    r['conflicts'] [{'id', 'kept', 'lost', 'keptFrom': 'local'|'remote'}]  → eski hal çakışma yedeğine
    r['archived']  [{'id', 'record', 'deletedAt', 'from'}]                  → uzak silme yerelde SİLMEZ, arşivler
Hiçbir kayıt silinmez, hiçbir kayıt sessizce ezilmez. Girdiler değiştirilmez.
"""
import json
import math
from datetime import datetime, timezone


def _jsnum(x):
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, int):
        return str(x)
    if math.isnan(x) or math.isinf(x):
        return 'null'
    if x == int(x) and abs(x) < 1e21:
        return str(int(x))
    r = repr(x)
    if 'e' in r:  # JS: 1e+21, 1e-7
        m, e = r.split('e')
        e = int(e)
        return m + ('e+' if e > 0 else 'e-') + str(abs(e))
    return r


def _jstr(s):
    return json.dumps(s, ensure_ascii=False)


def canon(x, skip=None):
    """JSON.stringify benzeri, anahtarlar sıralı (karşılaştırma için)."""
    if x is None or isinstance(x, (bool, int, float, str)):
        if isinstance(x, str):
            return _jstr(x)
        if x is None:
            return 'null'
        return _jsnum(x)
    if isinstance(x, (list, tuple)):
        return '[' + ','.join(canon(v) for v in x) + ']'
    if isinstance(x, dict):
        ks = sorted((str(k) for k in x.keys()), key=_u16)
        return '{' + ','.join(_jstr(k) + ':' + canon(x[k]) for k in ks if not skip or k not in skip) + '}'
    return _jstr(str(x))


def _u16(s):
    return s.encode('utf-16-be', 'surrogatepass')


def _parse_date(v):
    s = v.strip()
    try:
        if s.endswith('Z') or s.endswith('z'):
            s = s[:-1] + '+00:00'
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    if d.tzinfo is None:
        if 'T' not in v and ' ' not in v.strip():   # yalnız tarih → JS UTC sayar
            d = d.replace(tzinfo=timezone.utc)
        # tarih+saat, bölgesiz → JS yerel saat sayar (Python naive da yerel)
    return d.timestamp() * 1000


def ts(v):
    if v is None or v == '':
        return 0
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return v
    s = str(v)
    n = _parse_date(s)
    if n is not None:
        return round(n)
    try:
        f = float(s.strip())
        return 0 if math.isnan(f) else (int(f) if f == int(f) else f)
    except ValueError:
        return 0


def _iso(ms):
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return d.strftime('%Y-%m-%dT%H:%M:%S.') + '%03dZ' % (int(round(ms)) % 1000)


def _key(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float):
        return _jsnum(v)
    return str(v)


def merge(local, remote, opt=None, **kw):
    o = dict(opt or {})
    o.update(kw)
    ID = o.get('idKey') or 'id'
    UP = o.get('updatedKey') or 'updatedAt'
    DEL = o.get('deletedKey') or 'deleted'
    DELAT = o.get('deletedAtKey') or 'deletedAt'
    ARC = o.get('archivedKey') or 'archived'
    ARCAT = o.get('archivedAtKey') or 'archivedAt'
    skip = [UP]

    def index(lst):
        m, order = {}, []
        for r in lst or []:
            if not isinstance(r, dict) or r.get(ID) is None:
                continue
            k = _key(r[ID])
            if k not in m:
                order.append(k)
            m[k] = r
        return m, order

    Lm, Lo = index(local)
    Rm, Ro = index(remote)
    ids = Lo + [k for k in Ro if k not in Lm]
    records, conflicts, archived = [], [], []

    def dead(r):
        return bool(r and r.get(DEL))

    def del_time(r):
        return ts(r.get(DELAT)) or ts(r.get(UP))

    def archive(live, tomb, frm):
        t = del_time(tomb)
        rec = dict(live)
        rec[ARC] = True
        rec[ARCAT] = _iso(t) if isinstance(tomb.get(DELAT), str) or isinstance(tomb.get(UP), str) else t
        if ts(rec.get(UP)) < t:
            rec[UP] = _iso(t) if isinstance(live.get(UP), str) else t
        rec.pop(DEL, None)
        rec.pop(DELAT, None)
        records.append(rec)
        archived.append({'id': _key(live[ID]), 'record': rec, 'deletedAt': t, 'from': frm})

    for i in ids:
        x, y = Lm.get(i), Rm.get(i)
        if x is not None and y is None:
            if not dead(x):
                records.append(x)
            continue
        if y is not None and x is None:
            if not dead(y):
                records.append(y)
            continue
        if dead(x) and dead(y):
            continue
        if dead(y):
            if del_time(y) >= ts(x.get(UP)):
                archive(x, y, 'remote')
            else:
                records.append(x)
            continue
        if dead(x):
            if del_time(x) >= ts(y.get(UP)):
                archive(y, x, 'local')
            else:
                records.append(y)
            continue
        cx, cy = canon(x, skip), canon(y, skip)
        sx, sy = ts(x.get(UP)), ts(y.get(UP))
        if cx == cy:
            records.append(y if sy > sx else x)
            continue
        local_wins = sx > sy or (sx == sy and _u16(cx) > _u16(cy))
        records.append(x if local_wins else y)
        conflicts.append({'id': i, 'kept': x if local_wins else y, 'lost': y if local_wins else x,
                          'keptFrom': 'local' if local_wins else 'remote'})
    return {'records': records, 'conflicts': conflicts, 'archived': archived}
