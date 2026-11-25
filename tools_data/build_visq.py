"""Hazır görselli soru havuzunu üretir: app/data/visq.json + app/data/visq/*.png

Kaynaklar:
- crashbench gerçek logları (uzman etiketli kırım / normal; BENCH klasörleri), kök nedene göre kotalı seçim
- synth eğitim senaryoları (normal, GPS kaybı, batarya, titreşim, RC kaybı, stall, pusula)

Kullanım: python tools_data/build_visq.py [BENCH_DIR ...]
"""
import json, os, sys, tempfile, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import warnings
warnings.filterwarnings('ignore')
from app.core import loader, analysis, synth, visq  # noqa: E402

QUOTA = {'motor': 8, 'control': 7, 'vibration': 5, 'power': 5, 'gps': 3, 'ekf': 3, 'compass': 4, 'radio': 3, 'stall': 3, 'normal': 10}
MAX_MB = 45


def pick(benches):
    res = {r['id']: r for r in json.load(open(os.path.join(ROOT, 'tools_data', 'crashbench', 'results.json')))['results']}
    lab = json.load(open(os.path.join(ROOT, 'tools_data', 'crashbench', 'labels.json')))['labels']

    def path(tid):
        for b in benches:
            p = os.path.join(b, tid + '.bin')
            if os.path.exists(p): return p
    cand = {}
    for tid, l in lab.items():
        r = res.get(tid)
        if not r or l.get('exclude') or not l.get('label') or r.get('got') in (None, 'error'): continue
        p = path(tid)
        if not p or os.path.getsize(p) > MAX_MB * 1e6: continue
        if l['label'] == 'normal':
            if r['got'] != 'normal': continue
            k = 'normal'; pri = 0 if r['vehicle'] == 'Plane' else 1
        else:
            c = {'battery': 'power'}.get(l.get('cause'), l.get('cause'))
            if c not in QUOTA or r['got'] != 'crash': continue
            if c == 'stall' and r['vehicle'] != 'Plane': continue
            k = c; pri = 0 if r.get('got_cause') in (l.get('cause'), c) else 1
        cand.setdefault(k, []).append((pri, os.path.getsize(p), tid, p, l['label'], None if k == 'normal' else k, r['vehicle']))
    out = []
    for k, q in QUOTA.items():
        xs = sorted(cand.get(k, []))
        if k == 'control':   # uçak ve kopter karışık
            pl = [x for x in xs if x[6] == 'Plane'][:3]; xs = pl + [x for x in xs if x not in pl]
        if k == 'normal':
            pl = [x for x in xs if x[6] == 'Plane'][:3]; xs = pl + [x for x in xs if x not in pl]
        out += xs[:q]
        print(k, len(cand.get(k, [])), '→', min(q, len(xs)))
    return out


def main():
    benches = sys.argv[1:] or ['/tmp/claude-0/bench2', '/tmp/claude-0/bench']
    dst = os.path.join(ROOT, 'app', 'data', 'visq'); os.makedirs(dst, exist_ok=True)
    for f in os.listdir(dst): os.remove(os.path.join(dst, f))
    allq = []; images = {}; n = 0
    for _, _, tid, p, label, cause, veh in pick(benches):
        n += 1
        try:
            A = analysis.Analysis(loader.load(p))
            qs = visq.make(A, f'V{n:02d}', label, cause, 'real', images=images)
        except Exception as e:
            print('!', tid, e); continue
        allq += qs; print(tid, label, cause, veh, len(qs))
    tmp = tempfile.mkdtemp()
    smap = {'normal': ('normal', None), 'gps_loss': (None, 'gps'), 'battery': (None, 'power'), 'vibration': (None, 'vibration'),
            'radio_loss': (None, 'radio'), 'stall': (None, 'stall'), 'compass': (None, 'compass')}
    for i, sc in enumerate(synth.SCENARIOS):
        p = os.path.join(tmp, sc + '.BIN'); synth.generate(p, sc)
        A = analysis.Analysis(loader.load(p, use_cache=False))
        label, cause = smap[sc]
        if label is None: label = 'crash' if A.verdict.get('kind') == 'crash' else 'incident'
        qs = visq.make(A, f'S{i + 1:02d}', label, cause, 'synth', images=images)
        allq += qs; print('synth', sc, label, cause, len(qs))
    used = set()
    for q in allq:
        k = q['img'][1:]; q['img'] = f'visq/{k}.png'; used.add(k)
    tot = 0
    for k, raw in images.items():
        if k not in used: continue
        with open(os.path.join(dst, k + '.png'), 'wb') as f: f.write(raw)
        tot += len(raw)
    with open(os.path.join(ROOT, 'app', 'data', 'visq.json'), 'w', encoding='utf-8') as f:
        json.dump({'v': 1, 'questions': allq}, f, ensure_ascii=False, indent=0)
    print(len(allq), 'soru', len(used), 'görsel', round(tot / 1e6, 2), 'MB')


if __name__ == '__main__':
    main()
