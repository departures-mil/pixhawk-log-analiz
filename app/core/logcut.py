"""Log kesme (v1.1.18): logun yalnız çalışılacak aralığını incele, kalanını sakla ve istenince geri getir.

`crop(L, t0, t1)` yeni bir LogData döndürür: yalnız [t0, t1] aralığındaki örnekler, zaman bu aralığın başından sayılır
(t = 0 → kesimin başı), böylece bütün grafikler yalnız çalışılan kısmı gösterir ve ekranı kaplar. Gerçek zaman bilgisi
korunur: `t0_us` (log TimeUS'u, Mission Planner eşlemesi) ve `gps_time0` (saat) kaydırılır. Asıl log `cut['full']`'da
saklanır; `restore(L)` onu geri verir. Parametreler (PARM) her zaman tam kalır.

`records(L)` logdaki ayrı kayıtları (motor kurulu dönemler; yoksa veri boşlukları) bulur: "yalnız 2. kayıt" gibi hızlı seçim.
"""
from __future__ import annotations
import numpy as np

PAD = 5.0          # kayda göre kesimde başa/sona eklenen pay (s)
MERGE_GAP = 20.0   # aradaki boşluk bundan kısaysa iki kurulu dönem tek kayıt sayılır (s)


def _alt_series(L):
    for name, f in (('POS', 'RelHomeAlt'), ('BARO', 'Alt'), ('CTUN', 'BAlt'), ('GPS', 'Alt')):
        s = L.s(name)
        if s.has(f) and len(s['t']) > 2:
            a = np.asarray(s[f], float)
            if name == 'GPS':
                ok = np.isfinite(a)
                if not ok.any(): continue
                a = a - np.nanmin(a[ok])
            return s['t'], a, f'{name}.{f}'
    return None, None, ''


def _armed_periods(L):
    ev = [(t, True) for t, i in L.events if i == 10] + [(t, False) for t, i in L.events if i == 11]
    ev += [(t, bool(a)) for t, a in L.arm]
    ev.sort()
    cur = None; out = []
    for t, a in ev:
        if a and cur is None: cur = t
        elif not a and cur is not None:
            if t > cur: out.append((cur, t))
            cur = None
        elif not a and cur is None and not out and t > 1: out.append((0.0, t))
    if cur is not None: out.append((cur, L.duration))
    return out


def _gap_periods(L):
    """Kurulu dönem bilgisi yoksa: hızlı akan bir mesajdaki ≥MERGE_GAP s boşluklarla ayrılmış veri blokları."""
    for name in ('ATT', 'IMU', 'GPS', 'BARO', 'CTUN'):
        t = L.s(name).t
        if len(t) > 20:
            d = np.diff(t); cut = np.where(d >= MERGE_GAP)[0]
            if not len(cut): return [(float(t[0]), float(t[-1]))]
            st = [0] + list(cut + 1); en = list(cut) + [len(t) - 1]
            return [(float(t[a]), float(t[b])) for a, b in zip(st, en)]
    return []


def records(L):
    """Logdaki ayrı kayıtlar: [{'i', 't0', 't1', 'dur', 'alt_max', 'flew'}] (zaman sırasıyla)."""
    per = _armed_periods(L)
    if not per: per = _gap_periods(L)
    merged = []
    for a, b in sorted(per):
        if merged and a - merged[-1][1] < MERGE_GAP: merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else: merged.append((a, b))
    t, alt, _ = _alt_series(L)
    g = L.s('GPS')
    out = []
    for i, (a, b) in enumerate(merged, 1):
        am = None; sp = None
        if t is not None:
            m = (t >= a) & (t <= b)
            if m.any():
                v = alt[m]; v = v[np.isfinite(v)]
                if len(v): am = float(np.max(v) - (np.percentile(v, 5) if len(v) > 10 else np.min(v)))
        if g.has('Spd'):
            m = (g.t >= a) & (g.t <= b)
            if m.any(): sp = float(np.nanmax(g['Spd'][m]))
        flew = bool((am or 0) > 5 or (sp or 0) > 5)
        out.append({'i': i, 't0': float(a), 't1': float(b), 'dur': float(b - a), 'alt_max': am, 'spd_max': sp, 'flew': flew})
    return out


def record_range(L, rec, pad=PAD):
    return max(0.0, rec['t0'] - pad), min(float(L.duration), rec['t1'] + pad)


def _sl(s, t0, t1):
    from .loader import Series
    t = s.get('t')
    if t is None or not len(t):
        return s
    m = (t >= t0) & (t <= t1)
    o = Series()
    for f, v in s.items():
        try:
            o[f] = (v[m] - t0) if f == 't' else v[m]
        except Exception:
            o[f] = v
    return o


def crop(L, t0, t1):
    """[t0, t1] aralığını yeni LogData olarak döndürür (zaman t0'dan sayılır). Asıl log L.cut['full']'da saklanır."""
    full = getattr(L, 'cut', None) and L.cut.get('full') or L
    base = (L.cut or {}).get('t0', 0.0) if getattr(L, 'cut', None) else 0.0
    t0 = float(t0) + base; t1 = float(t1) + base          # zaten kesilmiş logda aralık yeniden seçilirse asıl loga göre
    t0 = max(0.0, min(t0, full.duration)); t1 = max(t0 + 1.0, min(t1, full.duration))
    from .loader import LogData
    C = LogData()
    for a in ('path', 'kind', 'size', 'version', 'vehicle', 'board', 'truncated', 'types_seen'):
        setattr(C, a, getattr(full, a))
    C.params = full.params
    for a in ('units', 'fmt_cols', 'from_cache'):
        if hasattr(full, a): setattr(C, a, getattr(full, a))
    seen = {}; msgs = {}
    for name, s in full.msgs.items():
        k = id(s)
        if k not in seen: seen[k] = _sl(s, t0, t1)
        msgs[name] = seen[k]
    C.msgs = msgs
    inr = lambda t: t0 <= t <= t1
    C.texts = [(t - t0, x) for t, x in full.texts if inr(t)]
    prev = [m for m in full.modes if m[0] < t0]
    C.modes = ([(0.0,) + tuple(prev[-1][1:])] if prev else []) + [(m[0] - t0,) + tuple(m[1:]) for m in full.modes if inr(m[0])]
    C.errors = [(t - t0, s, c) for t, s, c in full.errors if inr(t)]
    C.events = [(t - t0, i) for t, i in full.events if inr(t)]
    C.arm = [(t - t0, a) for t, a in full.arm if inr(t)]
    # kesim başında motorlar kuruluysa (ARM olayı kesilen kısımda kaldı) kurulu başlat
    per = _armed_periods(full)
    if any(a < t0 < b for a, b in per):
        C.arm = [(0.0, True)] + C.arm
    C.duration = t1 - t0
    C.t0_us = int((full.t0_us or 0) + t0 * 1e6)
    C.gps_time0 = (full.gps_time0[0] - t0, full.gps_time0[1]) if full.gps_time0 else None
    C.cut = {'t0': t0, 't1': t1, 'full_dur': float(full.duration), 'full': full}
    if getattr(full, '_browse_done', False): C._browse_done = True
    return C


def restore(L):
    """Kesilmiş logun asıl (tam) hâli; kesilmemişse kendisi."""
    c = getattr(L, 'cut', None)
    return c['full'] if c and c.get('full') is not None else L


def is_cut(L):
    return bool(getattr(L, 'cut', None))


def fmt(t):
    t = max(0, int(round(t)))
    return f'{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}' if t >= 3600 else f'{t // 60:02d}:{t % 60:02d}'
