"""ArduPilot'un resmî parametre tanımlarını (apm.pdef.json) bütün araç sınıfları için indirip
programın offline kullandığı tek dosyada (app/data/params_full.json.gz) birleştirir.

GitHub Actions'ta çalışır (tools_data/request_params.txt değişince). Kaynak: autotest.ardupilot.org/Parameters.
Varsayılan değerler ArduPilot kaynak kodundaki AP_GROUPINFO / GSCALAR tanımlarından okunur (defaults.py).
Elle yazılmış TR/AR çeviriler (app/data/params.json içindeki 'tr'/'ar') korunur.
"""
from __future__ import annotations
import gzip, json, os, sys, time, urllib.request, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://autotest.ardupilot.org/Parameters'
# program içi ad -> autotest klasör adları (ilk bulunan)
VEHICLES = [('Plane', ['ArduPlane']), ('Copter', ['ArduCopter']), ('Heli', ['Heli', 'ArduCopter-heli']),
            ('Rover', ['Rover', 'APMrover2']), ('Sub', ['ArduSub']), ('Blimp', ['Blimp']),
            ('Tracker', ['AntennaTracker']), ('Periph', ['AP_Periph'])]


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'pixhawk-log-analiz-ci'})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:
            print('  retry', url, e); time.sleep(3 * (i + 1))
    return None


def fnum(x):
    try:
        v = float(str(x).strip())
        return int(v) if v.is_integer() and abs(v) < 1e15 else v
    except Exception:
        return None


def norm(p):
    """apm.pdef.json girdisini sade biçime çevir."""
    o = {}
    dn = p.get('DisplayName') or p.get('displayName') or ''
    d = p.get('Description') or p.get('description') or ''
    if dn: o['dn'] = ' '.join(str(dn).split())
    if d: o['d'] = ' '.join(str(d).split())
    u = p.get('Units')
    if u: o['u'] = u
    r = p.get('Range')
    if isinstance(r, dict) and ('low' in r or 'high' in r):
        o['r'] = [fnum(r.get('low')), fnum(r.get('high'))]
    inc = p.get('Increment')
    if inc not in (None, ''): o['inc'] = fnum(inc) if fnum(inc) is not None else inc
    usr = p.get('User') or p.get('user')
    if usr: o['usr'] = usr
    for src, dst in (('Values', 'vals'), ('Bitmask', 'bits')):
        x = p.get(src)
        if isinstance(x, dict) and x:
            o[dst] = {str(k).strip(): ' '.join(str(v).split()) for k, v in x.items()}
    if str(p.get('RebootRequired', '')).lower() in ('true', '1'): o['rb'] = 1
    if str(p.get('ReadOnly', '')).lower() in ('true', '1'): o['ro'] = 1
    if str(p.get('Volatile', '')).lower() in ('true', '1'): o['vol'] = 1
    if str(p.get('Calibration', '')).lower() in ('true', '1'): o['cal'] = 1
    return o


def main():
    raw_dir = os.environ.get('RAW_DIR', os.path.join(ROOT, 'build_raw'))
    os.makedirs(raw_dir, exist_ok=True)
    per = {}; meta = {}
    for name, folders in VEHICLES:
        data = None
        for f in folders:
            b = get(f'{BASE}/{f}/apm.pdef.json')
            if b:
                try:
                    data = json.loads(b.decode('utf-8')); meta[name] = {'src': f'{BASE}/{f}/apm.pdef.json'}
                    open(os.path.join(raw_dir, name + '.json'), 'wb').write(b); break
                except Exception as e:
                    print('bad json', f, e)
        if not data:
            print('!! missing', name); continue
        fw = (data.get('json') or {}).get('firmware') or {}
        meta[name].update({k: fw.get(k) for k in ('git_sha', 'git_tag') if fw.get(k)})
        ps = {}
        for grp, items in data.items():
            if grp == 'json' or not isinstance(items, dict): continue
            for k, p in items.items():
                if not isinstance(p, dict): continue
                nm = k.split(':')[-1]
                ps[nm] = norm(p)
        per[name] = ps
        print(f'{name}: {len(ps)} params')
    if not per:
        sys.exit('no data')

    # Varsayılanlar (kaynak koddan)
    defs = {}
    src = os.environ.get('ARDUPILOT_SRC')
    if src and os.path.isdir(src):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import defaults
        defs = defaults.extract(src, per)
        print('defaults resolved:', sum(len(v) for v in defs.values()))

    # Birleştir: ortak alanlar tek kez, farklı olanlar araç bazında 'var' içinde
    allnames = sorted(set().union(*[set(v) for v in per.values()]))
    order = [n for n, _ in VEHICLES if n in per]
    out = {}
    for k in allnames:
        vs = [v for v in order if k in per[v]]
        base = dict(per[vs[0]][k])
        var = {}
        for v in vs[1:]:
            diff = {f: x for f, x in per[v][k].items() if base.get(f) != x}
            miss = [f for f in base if f not in per[v][k]]
            for f in miss: diff[f] = None
            if diff: var[v] = diff
        e = base; e['v'] = vs
        if var: e['var'] = var
        dv = {v: defs[v][k] for v in vs if k in defs.get(v, {})}
        if dv:
            vals = set(json.dumps(x) for x in dv.values())
            e['def'] = next(iter(dv.values())) if len(vals) == 1 and len(dv) == len(vs) else dv
        out[k] = e

    # Gruplar ve elle yazılmış çeviriler (eski kütüphaneden)
    old = json.load(open(os.path.join(ROOT, 'app', 'data', 'params.json'), encoding='utf-8'))
    groups = dict(old.get('groups', {}))
    for k, e in out.items():
        g = k.split('_')[0] if '_' in k else k
        e['g'] = g
        groups.setdefault(g, {'en': g})
        o = old['params'].get(k)
        if o:
            for lg in ('tr', 'ar'):
                if o.get(lg): e[lg] = o[lg]   # [görünen ad, açıklama]
    res = {'built': datetime.datetime.utcnow().strftime('%Y-%m-%d'), 'source': meta, 'vehicles': order,
           'groups': groups, 'params': out}
    dst = os.path.join(ROOT, 'app', 'data', 'params_full.json.gz')
    with gzip.open(dst, 'wt', encoding='utf-8', compresslevel=9) as f:
        json.dump(res, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    print('written', dst, os.path.getsize(dst) // 1024, 'KB', len(out), 'params')


if __name__ == '__main__':
    main()
