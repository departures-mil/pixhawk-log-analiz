"""Öğrenen ikinci görüş: uzman etiketli gerçek loglarla eğitilmiş lojistik regresyon (yalnız numpy).

Kurallar asıl kararı verir; model yalnız (1) kararın yanında 'model görüşü' olasılığı gösterir,
(2) çapraz doğrulamada yararı ölçülmüşse sınırdaki kararları düzeltir:
    kural 'normal' + model ≥ hi  → 'incident' (kaçan kaza)
    kural 'incident' (kırım puanı 0) + model ≤ lo → 'normal' (yanlış alarm)
Ağırlıklar app/data/ml_model.json (tools_data/train_model.py üretir). Dosya yoksa model devre dışıdır.
"""
from __future__ import annotations
import json, os
import numpy as np

EVID = ['cr_stat', 'cr_err', 'cr_msg', 'cr_sink', 'cr_log_end', 'cr_log_cut', 'cr_attitude', 'cr_impact', 'cr_flip', 'cr_landed', 'cr_yaw']
DOMS = ['gps', 'vibration', 'power', 'ekf', 'control', 'servo', 'rc', 'cpu', 'motors', 'airspeed']
_M = {'v': None}


def _path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'ml_model.json')


def features(d, finds=None):
    """d: {'verdict': {...}, 'health': {...}, 'vehicle': str} (Analysis ya da to_json biçimi)."""
    v = d.get('verdict') or {}; h = d.get('health') or {}
    ek = {e.get('k') for e in v.get('evidence', [])}
    x = [1.0 if k in ek else 0.0 for k in EVID]
    x.append(min(float(v.get('score') or 0), 150) / 100.0)
    for k in DOMS:
        x.append((100.0 - float((h.get(k) or {}).get('score', 100))) / 100.0)
    st = [(h[k] or {}).get('status') for k in h]
    x += [st.count('bad') / 3.0, st.count('warn') / 3.0]
    m = (h.get('vibration') or {}).get('metrics') or {}
    x.append(min(float(m.get('max') or m.get('max_vibe') or 0), 120) / 60.0)
    g = (h.get('gps') or {}).get('metrics') or {}
    x.append(min(float(g.get('glitches') or 0), 10) / 5.0)
    veh = d.get('vehicle')
    x += [1.0 if veh == 'Copter' else 0.0, 1.0 if veh == 'Plane' else 0.0]
    fk = {f.get('k') for dom in h.values() for f in ((dom or {}).get('findings') or [])}
    for k in (finds or []):
        x.append(1.0 if k in fk else 0.0)
    return np.array(x, float)


def load():
    if _M['v'] is None:
        try: _M['v'] = json.load(open(_path(), encoding='utf-8'))
        except Exception: _M['v'] = {}
    return _M['v']


def prob(d):
    M = load()
    if not M: return None
    x = features(d, M.get('finds'))
    if len(x) != len(M['mu']): return None
    z = (x - np.array(M['mu'])) / np.array(M['sd'])
    s = float(np.dot(z, M['w']) + M['b'])
    return float(1.0 / (1.0 + np.exp(-s)))


def adjust(kind, score, p):
    """Ölçülmüş eşiklerle sınırdaki kararı düzelt (model dosyası 'use' içermiyorsa dokunma)."""
    M = load()
    if not M or p is None or not M.get('use'): return kind
    if kind == 'normal' and p >= M.get('hi', 0.9): return 'incident'
    if kind == 'incident' and (score or 0) == 0 and p <= M.get('lo', 0.1): return 'normal'
    return kind
