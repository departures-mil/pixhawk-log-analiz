"""Güven yüzdesi kalibrasyonu: "%80 eminim" denen kök neden kararlarının gerçekten ~%80'i doğru çıkmalı.

Girdi: uzman etiketli kırımlarda programın ham güveni (why.build conf) ve kök nedeni (JSON listesi:
[{id, cause, conf}], ör. hızlı yineleme çıktısı). Çıktı: app/data/calib.json
  p = σ(a·logit(ham) + c·logit(neden_öncülü) + b);  neden öncülü = (isabet + 2·genel) / (n + 2)
Ölçüm leave-one-out ile yapılır; ECE (beklenen kalibrasyon hatası) ham ve kalibre için yazılır.
    python tools_data/calibrate.py sonuclar.json
"""
from __future__ import annotations
import json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lg = lambda p: np.log(np.clip(p, 1e-3, 1 - 1e-3) / (1 - np.clip(p, 1e-3, 1 - 1e-3)))
sg = lambda z: 1 / (1 + np.exp(-z))


def priors(causes, ys, excl=None):
    g = float(np.mean(ys)); out = {}
    for c in set(causes):
        idx = [i for i, x in enumerate(causes) if x == c and i != excl]
        out[c] = (sum(ys[i] for i in idx) + 2 * g) / (len(idx) + 2)
    return out, g


def fit(X, y, it=4000, lr=0.2, lam=0.01):
    w = np.zeros(X.shape[1]); b = 0.0
    for _ in range(it):
        p = sg(X @ w + b); g = p - y
        w -= lr * (X.T @ g / len(y) + lam * w); b -= lr * g.mean()
    return w, b


def ece(p, y, bins=6):
    e = 0.0; edges = np.linspace(0, 1, bins + 1)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (p >= a) & (p < b if b < 1 else p <= b)
        if m.any(): e += m.mean() * abs(p[m].mean() - y[m].mean())
    return e


def main(src):
    R = json.load(open(src))
    lab = json.load(open(os.path.join(ROOT, 'tools_data', 'crashbench', 'labels.json'), encoding='utf-8'))['labels']
    rows = []
    for r in R:
        l = lab.get(r['id'])
        if not l or l.get('label') != 'crash' or not l.get('cause') or r.get('conf') is None or l.get('exclude'): continue
        rows.append((r.get('cause') or 'unknown', float(r['conf']), float(r.get('cause') in {l['cause'], *(l.get('alt') or [])})))
    causes = [c for c, _, _ in rows]; raw = np.array([x for _, x, _ in rows]); y = np.array([v for _, _, v in rows])
    P = np.zeros(len(y))
    for i in range(len(y)):                                      # leave-one-out
        pr, g = priors(causes, y, excl=i)
        X = np.column_stack([lg(raw), lg(np.array([pr.get(c, g) for c in causes]))])
        mk = np.arange(len(y)) != i
        w, b = fit(X[mk], y[mk]); P[i] = sg(X[i] @ w + b)
    pr, g = priors(causes, y)
    X = np.column_stack([lg(raw), lg(np.array([pr[c] for c in causes]))])
    w, b = fit(X, y)
    out = {'a': float(w[0]), 'c': float(w[1]), 'b': float(b), 'prior': {k: round(v, 3) for k, v in pr.items()}, 'global': round(g, 3),
           'n': int(len(y)), 'ece_raw': round(ece(raw, y), 3), 'ece_cal': round(ece(P, y), 3),
           'brier_raw': round(float(np.mean((raw - y) ** 2)), 3), 'brier_cal': round(float(np.mean((P - y) ** 2)), 3)}
    json.dump(out, open(os.path.join(ROOT, 'app', 'data', 'calib.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'prior'}))


if __name__ == '__main__':
    main(sys.argv[1])
