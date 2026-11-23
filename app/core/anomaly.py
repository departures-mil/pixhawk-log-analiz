"""Anomali tespiti (çevrimdışı, hafif makine öğrenmesi).

Uçuş 10 saniyelik pencerelere bölünür; her pencere için titreşim, GPS, tutum hatası, gaz, batarya, EKF, pusula,
irtifa/rota hatası gibi 14 özellik hesaplanır. Model, kullanıcının NORMAL sonuçlanan uçuşlarından profil başına
(sabit kanat / VTOL / multikopter …) özellik dağılımını öğrenir (Welford ortalama/varyans). Yeni bir uçuşta
her pencere bu dağılıma göre z-puanıyla değerlendirilir; ayrıca uçuşun kendi içindeki ani sapmalar (medyan/MAD)
da ölçülür. Kural setinin yakalamadığı "alışılmadık" bölümler zaman, puan ve sorumlu özelliklerle raporlanır.
Henüz yeterli normal uçuş yoksa yerleşik başlangıç modeli kullanılır.
"""
from __future__ import annotations
import json, math, os, threading
import numpy as np

WIN = 10.0
# ad, yön (+1 yüksek kötü, -1 düşük kötü, 0 iki yön), önsel ortalama, önsel sapma
FEATS = [
    ('vibe', 1, 12.0, 6.0), ('clip', 1, 0.0, 0.5), ('sats', -1, 14.0, 3.0), ('hdop', 1, 0.8, 0.35),
    ('att_err', 1, 2.0, 1.5), ('thr', 0, 55.0, 25.0), ('v_drop', 1, 0.01, 0.02), ('curr', 0, 15.0, 12.0),
    ('ekf', 1, 0.2, 0.15), ('mag_dev', 1, 2.0, 2.5), ('alt_err', 1, 3.0, 4.5), ('xtrack', 1, 5.0, 6.0),
    ('as_gs', 0, 0.0, 4.0), ('cpu', 1, 40.0, 15.0),
]
NAMES = {
    'vibe': ('Titreşim', 'Vibration', 'الاهتزاز'), 'clip': ('İvmeölçer doyması (clip)', 'Accelerometer clipping', 'تشبع مقياس التسارع'),
    'sats': ('Uydu sayısı', 'Satellite count', 'عدد الأقمار'), 'hdop': ('HDOP (GPS hassasiyeti)', 'HDOP (GPS precision)', 'HDOP (دقة GPS)'),
    'att_err': ('Tutum takip hatası', 'Attitude tracking error', 'خطأ تتبع الوضعية'), 'thr': ('Gaz', 'Throttle', 'الخانق'),
    'v_drop': ('Hücre gerilimi düşüş hızı', 'Cell voltage drop rate', 'معدل هبوط جهد الخلية'), 'curr': ('Akım', 'Current', 'التيار'),
    'ekf': ('EKF varyansı', 'EKF variance', 'تباين EKF'), 'mag_dev': ('Manyetik alan sapması', 'Magnetic field deviation', 'انحراف المجال المغناطيسي'),
    'alt_err': ('İrtifa takip hatası', 'Altitude tracking error', 'خطأ تتبع الارتفاع'), 'xtrack': ('Rota sapması', 'Cross-track error', 'الانحراف عن المسار'),
    'as_gs': ('Hava hızı − yer hızı', 'Airspeed − ground speed', 'السرعة الجوية − الأرضية'), 'cpu': ('İşlemci yükü', 'CPU load', 'حمل المعالج'),
}
_lock = threading.Lock()


def fname(k, lang='tr'):
    return NAMES.get(k, (k, k, k))[('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0]


def _wmean(t, v, edges):
    """Pencerelere göre ortalama (NaN güvenli)."""
    out = np.full(len(edges) - 1, np.nan)
    if t is None or len(t) == 0: return out
    ok = np.isfinite(v)
    t, v = t[ok], v[ok]
    if not len(t): return out
    idx = np.searchsorted(edges, t, side='right') - 1
    m = (idx >= 0) & (idx < len(out))
    s = np.bincount(idx[m], v[m], minlength=len(out)); n = np.bincount(idx[m], minlength=len(out))
    with np.errstate(invalid='ignore', divide='ignore'):
        r = s / n
    r[n == 0] = np.nan
    return r


def features(A):
    """(pencere başlangıçları, X [pencere × özellik])"""
    L = A.L
    if not A.flights: return np.array([]), np.zeros((0, len(FEATS)))
    edges = []
    for a, b in A.flights:
        # Kalkış ve inişin ilk/son 25 sn'si doğası gereği farklıdır (kural motoru ayrıca inceler)
        e = np.arange(a + 25, b - 25 - WIN, WIN)
        for ph in A.phases:
            if ph['name'] in ('takeoff', 'landing'):
                e = e[(e + WIN < ph['t0'] - 30) | (e > ph['t1'] + 5)]
        if len(e) >= 2: edges.append(e)
    if not edges: return np.array([]), np.zeros((0, len(FEATS)))
    # Uçuşlar arası boşluklar ayrı pencere üretmesin: her uçuşu ayrı hesaplayıp birleştir
    T0 = []; rows = []
    for e in edges:
        e2 = np.r_[e, e[-1] + WIN]
        cols = []
        v = L.s('VIBE')
        if v.has('VibeZ'):
            vm = np.nanmax(np.vstack([_wmean(v['t'], v[k], e2) for k in ('VibeX', 'VibeY', 'VibeZ') if v.has(k)]), axis=0)
        else: vm = np.full(len(e), np.nan)
        cols.append(vm)
        ck = next((k for k in ('Clip', 'Clip0') if v.has(k)), None)
        if ck:
            c = v[ck]; dc = np.r_[0, np.maximum(0, np.diff(c))]
            cols.append(_wmean(v['t'], dc, e2) * 10)
        else: cols.append(np.full(len(e), np.nan))
        g = L.s('GPS')
        cols.append(_wmean(g['t'], g['NSats'], e2) if g.has('NSats') else np.full(len(e), np.nan))
        cols.append(_wmean(g['t'], g['HDop'], e2) if g.has('HDop') else np.full(len(e), np.nan))
        at = L.s('ATT')
        if at.has('DesRoll'):
            er = np.abs(at['DesRoll'] - at['Roll']) + np.abs(at['DesPitch'] - at['Pitch'])
            cols.append(_wmean(at['t'], er / 2, e2))
        else: cols.append(np.full(len(e), np.nan))
        ct = L.s('CTUN')
        if ct.has('ThO'):
            th = ct['ThO'] * (100 if np.nanmax(ct['ThO']) <= 1.05 else 1)
            cols.append(_wmean(ct['t'], th, e2))
        else: cols.append(np.full(len(e), np.nan))
        b = L.s('BAT')
        if b.has('Volt') and len(b['t']) > 5:
            vmax = np.nanmax(b['Volt']); cells = max(1, round(vmax / 4.2)) if vmax > 5 else 1
            vw = _wmean(b['t'], b['Volt'] / cells, e2)
            drop = np.r_[np.nan, -(np.diff(vw)) / (WIN / 60.0)]  # V/dk
            cols.append(drop)
            cols.append(_wmean(b['t'], b['Curr'], e2) if b.has('Curr') and np.nanmax(np.abs(b['Curr'])) > 0.5 else np.full(len(e), np.nan))
        else:
            cols += [np.full(len(e), np.nan)] * 2
        x = L.s('XKF4') if L.s('XKF4').has('SV') else L.s('NKF4')
        if x.has('SV'):
            ek = np.nanmax(np.vstack([_wmean(x['t'], x[k], e2) for k in ('SV', 'SP', 'SH') if x.has(k)]), axis=0)
            cols.append(ek)
        else: cols.append(np.full(len(e), np.nan))
        mg = L.s('MAG')
        if mg.has('MagX'):
            fm = np.sqrt(mg['MagX'] ** 2 + mg['MagY'] ** 2 + mg['MagZ'] ** 2)
            med = np.nanmedian(fm) or 1
            cols.append(_wmean(mg['t'], np.abs(fm - med) / med * 100, e2))
        else: cols.append(np.full(len(e), np.nan))
        nt = L.s('NTUN')
        ae = next((k for k in ('AltE', 'AltErr') if nt.has(k)), None)
        cols.append(_wmean(nt['t'], np.abs(nt[ae]), e2) if ae else np.full(len(e), np.nan))
        cols.append(_wmean(nt['t'], np.abs(nt['XT']), e2) if nt.has('XT') else np.full(len(e), np.nan))
        asrc = L.s('ARSP') if L.s('ARSP').has('Airspeed') else ct
        af = 'Airspeed' if asrc.has('Airspeed') else ('As' if asrc.has('As') else None)
        if af and g.has('Spd') and A.vehicle == 'Plane':
            gs = np.interp(asrc['t'], g['t'], g['Spd'])
            cols.append(_wmean(asrc['t'], asrc[af] - gs, e2))
        else: cols.append(np.full(len(e), np.nan))
        pm = L.s('PM')
        cols.append(_wmean(pm['t'], pm['Load'] / 10.0, e2) if pm.has('Load') else np.full(len(e), np.nan))
        rows.append(np.vstack(cols).T); T0.append(e)
    return np.concatenate(T0), np.vstack(rows)


# ----------------------------------------------------------------- model
def _path():
    from .paths import data_dir
    return os.path.join(data_dir(), 'anomaly_model.json')


def load_model():
    try:
        with open(_path(), encoding='utf-8') as f: return json.load(f)
    except Exception:
        return {'profiles': {}, 'learned': []}


def save_model(m):
    tmp = _path() + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(m, f)
    os.replace(tmp, _path())


def stats_for(model, profile):
    """Her özellik için (ortalama, sapma, n) — öğrenilmiş + önsel karışım."""
    pr = model.get('profiles', {}).get(profile, {})
    out = []
    for i, (k, d, mu0, sd0) in enumerate(FEATS):
        st = pr.get(k)
        if st and st['n'] >= 30:
            n = st['n']; mu = st['mean']; var = st['m2'] / max(1, n - 1)
            sd = max(math.sqrt(var), sd0 * 0.25)
            w = min(1.0, n / 300.0)
            out.append((mu * w + mu0 * (1 - w), sd * w + sd0 * (1 - w), n))
        else:
            out.append((mu0, sd0, st['n'] if st else 0))
    return out


def learn(A, uid=None):
    """Normal uçuştan öğren (aynı log iki kez öğrenilmez)."""
    if A.verdict.get('kind') != 'normal': return False
    t0, X = features(A)
    if not len(X): return False
    with _lock:
        m = load_model()
        if uid and uid in m.get('learned', []): return False
        pr = m.setdefault('profiles', {}).setdefault(A.profile, {})
        for j, (k, *_r) in enumerate(FEATS):
            col = X[:, j]; col = col[np.isfinite(col)]
            st = pr.setdefault(k, {'n': 0, 'mean': 0.0, 'm2': 0.0})
            for x in col:
                st['n'] += 1; dlt = x - st['mean']; st['mean'] += dlt / st['n']; st['m2'] += dlt * (x - st['mean'])
        if uid: m.setdefault('learned', []).append(uid); m['learned'] = m['learned'][-5000:]
        m['flights'] = m.get('flights', 0) + 1
        save_model(m)
    return True


def model_info():
    m = load_model()
    return {'flights': m.get('flights', 0), 'profiles': {p: max((v['n'] for v in d.values()), default=0) for p, d in m.get('profiles', {}).items()}}


def detect(A, model=None):
    t0, X = features(A)
    if not len(X): return {'windows': 0, 'items': [], 'index': 0, 'learned_flights': 0}
    model = model or load_model()
    st = stats_for(model, A.profile)
    mu = np.array([s[0] for s in st]); sd = np.array([s[1] for s in st])
    dirs = np.array([f[1] for f in FEATS])
    z = (X - mu) / sd
    zd = np.where(dirs > 0, z, np.where(dirs < 0, -z, np.abs(z)))
    # Uçuşun kendi içindeki ani sapma (medyan / MAD)
    med = np.nanmedian(X, axis=0); mad = np.nanmedian(np.abs(X - med), axis=0) * 1.4826
    mad = np.maximum(mad, sd * 0.3)
    zs = (X - med) / mad
    zsd = np.where(dirs > 0, zs, np.where(dirs < 0, -zs, np.abs(zs)))
    zd = np.nan_to_num(zd, nan=0.0); zsd = np.nan_to_num(zsd, nan=0.0)
    score = np.maximum(zd, np.minimum(zsd, zd + 3) * 0.8)
    wscore = score.max(axis=1)
    flag = (zd.max(axis=1) > 4.0) | ((zsd.max(axis=1) > 6.0) & (zd.max(axis=1) > 2.0))
    items = []
    i = 0; n = len(flag)
    while i < n:
        if not flag[i]: i += 1; continue
        j = i
        while j + 1 < n and flag[j + 1] and t0[j + 1] - t0[j] <= WIN * 1.5: j += 1
        seg = score[i:j + 1]
        best = seg.max(axis=0)
        top = [int(k) for k in np.argsort(-best)[:3] if best[k] > 2.5]
        k_row = int(i + np.argmax(seg.max(axis=1)))
        items.append({'t0': float(t0[i]), 't1': float(t0[j] + WIN), 'score': float(round(seg.max(), 1)),
                      'feats': [{'k': FEATS[k][0], 'v': (None if not np.isfinite(X[k_row, k]) else float(round(X[k_row, k], 3))),
                                 'exp': float(round(mu[k], 3)), 'z': float(round(best[k], 1))} for k in top]})
        i = j + 1
    items.sort(key=lambda x: -x['score'])
    idx = 0 if not flag.any() else int(round(min(100, 100 * flag.mean() * 3 + max(0, float(np.nanmax(wscore[flag])) - 4) * 3)))
    return {'windows': int(n), 'items': items[:10], 'index': idx, 'learned_flights': int(model.get('flights', 0))}
