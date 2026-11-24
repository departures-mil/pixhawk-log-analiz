"""Öğrenen ikinci görüşü eğitir: tools_data/crashbench/results.json (uzman etiketli) → app/data/ml_model.json.

Bire-bir-dışarıda (leave-one-out) çapraz doğrulama ile kural kararı ve 'kural+model' kararı karşılaştırılır;
model yalnız doğrulukta ölçülmüş belirgin bir kazanç sağlıyorsa (kaza yakalamada ≤2 puan kayıpla) 'use': true yazılır.
    python tools_data/train_model.py
"""
from __future__ import annotations
import json, os, sys
from collections import Counter
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.core import mlmodel as MM  # noqa: E402


def fit(X, y, lam=1.0, it=3000, lr=0.1):
    mu = X.mean(0); sd = X.std(0); sd[sd < 1e-6] = 1.0
    Z = (X - mu) / sd
    w = np.zeros(Z.shape[1]); b = 0.0
    pos = max(1, y.sum()); neg = max(1, len(y) - y.sum())
    cw = np.where(y == 1, len(y) / (2 * pos), len(y) / (2 * neg))      # sınıf dengesi
    for _ in range(it):
        p = 1 / (1 + np.exp(-(Z @ w + b)))
        g = (p - y) * cw
        w -= lr * (Z.T @ g / len(y) + lam * w / len(y)); b -= lr * g.mean()
    return mu, sd, w, b


def pred(m, X):
    mu, sd, w, b = m
    return 1 / (1 + np.exp(-(((X - mu) / sd) @ w + b)))


def main():
    R = json.load(open(os.path.join(ROOT, 'tools_data', 'crashbench', 'results.json'), encoding='utf-8'))['results']
    R = [r for r in R if r.get('got') not in (None, 'error') and not r.get('exclude') and r.get('label') in ('crash', 'normal')]
    fc = Counter(f.get('k') for r in R for dom in (r.get('health') or {}).values() for f in ((dom or {}).get('findings') or []))
    finds = [k for k, n in fc.most_common() if n >= 4][:25]
    X = np.array([MM.features(r, finds) for r in R]); y = np.array([1.0 if r['label'] == 'crash' else 0.0 for r in R])
    rule = np.array([r['got'] in ('crash', 'incident') for r in R])
    sc = np.array([r['verdict'].get('score') or 0 for r in R]); kind = [r['got'] for r in R]
    best = None
    for lam in (0.3, 1.0, 3.0, 10.0):
        P = np.zeros(len(y))
        for i in range(len(y)):
            mk = np.arange(len(y)) != i
            P[i] = pred(fit(X[mk], y[mk], lam), X[i:i + 1])[0]
        for hi in (0.8, 0.85, 0.9, 0.95):
            for lo in (0.05, 0.1, 0.15, 0.2):
                dec = []
                for k, p, s in zip(kind, P, sc):
                    if k == 'normal' and p >= hi: k = 'incident'
                    elif k == 'incident' and s == 0 and p <= lo: k = 'normal'
                    dec.append(k in ('crash', 'incident'))
                dec = np.array(dec)
                acc = float((dec == (y == 1)).mean())
                rec = float(dec[y == 1].mean()); spe = float((~dec[y == 0]).mean())
                cand = (acc, rec, lam, hi, lo, spe, float(((P >= 0.5) == (y == 1)).mean()))
                if best is None or cand[:2] > best[:2]: best = cand
    acc0 = float((rule == (y == 1)).mean()); rec0 = float(rule[y == 1].mean()); spe0 = float((~rule[y == 0]).mean())
    acc, rec, lam, hi, lo, spe, macc = best
    # kural kararına göre doğrulukta belirgin kazanç; kaza yakalamada en çok 2 puan kayıp kabul edilir
    use = acc > acc0 + 0.01 and rec >= rec0 - (0.02 if acc > acc0 + 0.03 else 0.005)
    m = fit(X, y, lam)
    out = {'mu': m[0].tolist(), 'sd': m[1].tolist(), 'w': m[2].tolist(), 'b': float(m[3]), 'finds': finds, 'n': int(len(y)),
           'use': bool(use), 'hi': hi, 'lo': lo, 'lam': lam,
           'cv': {'rule_acc': round(acc0, 3), 'rule_recall': round(rec0, 3), 'rule_spec': round(spe0, 3),
                  'combined_acc': round(acc, 3), 'combined_recall': round(rec, 3), 'combined_spec': round(spe, 3), 'model_only_acc': round(macc, 3)}}
    json.dump(out, open(os.path.join(ROOT, 'app', 'data', 'ml_model.json'), 'w'), indent=0)
    print(json.dumps(out['cv'], indent=1), 'use=', use, 'lam', lam, 'hi', hi, 'lo', lo, 'n', len(y))


if __name__ == '__main__':
    main()
