"""Gerçek forum konularındaki uzman yanıtlarını tarayıp her konuya ders kodları atar → app/data/expert_cases.json.
Kullanım: python tools_data/expert_tags.py   (tools_data/crashbench/*threads.json.gz + labels.json)"""
import gzip, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from expert_rx import RX
from app.core import expert as E

CB = os.path.join(ROOT, 'tools_data', 'crashbench')


def experts(th):
    ps = th.get('posts') or []
    op = ps[0]['u'] if ps else None
    return [p for p in ps[1:] if p.get('u') != op and (p.get('staff') or p.get('tl', 0) >= 2 or p.get('likes', 0) > 0)]


def main():
    assert set(RX) == set(E.L), set(RX) ^ set(E.L)
    T = {}
    for f in ('threads.json.gz', 'holdout_threads.json.gz', 'more_threads.json.gz', 'plane_threads.json.gz'):
        p = os.path.join(CB, f)
        if os.path.exists(p): T.update(json.load(gzip.open(p)))
    lab = json.load(open(os.path.join(CB, 'labels.json'), encoding='utf-8'))['labels']
    out, st = {}, {}
    for tid, th in T.items():
        l = lab.get(tid) or {}
        if l.get('exclude'): continue
        ex = experts(th)
        text = '\n'.join(p.get('x') or '' for p in ex)
        hit = [k for k, r in RX.items() if re.search(r, text, re.I)]
        cause = l.get('cause'); alt = l.get('alt') or []
        rel = set(E.for_cause(cause)) | {k for a in alt for k in E.for_cause(a)}
        if cause == 'pilot' and 'pilot_stab' not in hit: hit.append('pilot_stab')
        # nedene en ilgili dersler önce, sonra uzmanların en sık değindiği
        hit.sort(key=lambda k: (k not in rel, -len(re.findall(RX[k], text, re.I))))
        if not hit and not cause: continue
        out[tid] = {'lessons': hit[:6], 'experts': len({p['u'] for p in ex}), 'cause': cause, 'alt': alt, 'label': l.get('label')}
        for k in hit: st[k] = st.get(k, 0) + 1
    json.dump({'n': len(out), 'stats': dict(sorted(st.items(), key=lambda kv: -kv[1])), 'cases': out},
              open(os.path.join(ROOT, 'app', 'data', 'expert_cases.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(len(out), st)


if __name__ == '__main__':
    main()
