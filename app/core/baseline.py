"""Aynı aracın geçmişiyle karşılaştırma (v1.1.2).

Her analizde temel ölçümler facts içine 'bl_*' olarak yazılır (arşive de girer). Yeni bir log açıldığında aynı
kartın (seri numarası) önceki normal/sorunlu uçuşlarının ortancası ve yayılımı ile karşılaştırılır; yalnız
kötü yöndeki belirgin sapmalar bildirilir ("bu araç için alışılmadık"). Kişisel veri kullanılmaz; her şey yereldir.
"""
from __future__ import annotations
import json
import numpy as np

# (anahtar, sağlık alanı, ölçüm, kötü yön: +1 = yüksek kötü, -1 = düşük kötü, en küçük anlamlı fark)
METRICS = [
    ('vib_p95', 'vibration', 'p95', +1, 3.0),
    ('vib_z', 'vibration', 'z_mean', +1, 2.0),
    ('cell_min', 'power', 'per_cell_min', -1, 0.08),
    ('vcc_min', 'power', 'vcc_min', -1, 0.1),
    ('bat_ir', 'power', 'ir_mohm', +1, 5.0),
    ('mag_var', 'ekf', 'SM', +1, 0.1),
    ('roll_rms', 'control', 'roll_rms', +1, 1.5),
    ('pitch_rms', 'control', 'pitch_rms', +1, 1.5),
    ('sats', 'gps', 'mean_sats', -1, 1.5),
    ('hdop', 'gps', 'max_hdop', +1, 0.3),
    ('mot_imb', 'motors', 'motor_imbalance_us', +1, 20.0),
    ('hover_thr', 'motors', 'hover_thr', +1, 0.04),
    ('cpu', 'cpu', 'load_max', +1, 10.0),
]


def collect(A):
    """Analizden karşılaştırma ölçümlerini çıkar ve facts'a yaz."""
    out = {}
    for key, dom, m, _, _ in METRICS:
        v = ((A.health.get(dom) or {}).get('metrics') or {}).get(m)
        if isinstance(v, (int, float)) and np.isfinite(v): out[key] = float(v)
    ph = getattr(A, 'physics', None) or {}
    if 'hover_thr' in ph: out['hover_thr'] = float(ph['hover_thr'])
    if 'cruise_thr' in ph: out['cruise_thr'] = float(ph['cruise_thr'])
    for k, v in out.items(): A.facts['bl_' + k] = round(v, 4)
    return out


def compare(A, arc, uid=None, max_n=20):
    """[{key, v, med, n, dir}] — bu araç için alışılmadık (kötü yönde) ölçümler."""
    serial = getattr(A, 'serial', '') or ''
    if not serial or arc is None: return []
    cur = {k[3:]: v for k, v in (A.facts or {}).items() if k.startswith('bl_') and isinstance(v, (int, float))}
    if not cur: return []
    try:
        rows = arc.db.execute("SELECT uid, facts, verdict, flight_ts FROM analyses WHERE aircraft=? ORDER BY flight_ts DESC",
                              (serial,)).fetchall()
    except Exception:
        return []
    hist = []
    for r in rows:
        if uid and r['uid'] == uid: continue
        if (r['verdict'] or '') not in ('normal', 'incident'): continue
        try: f = json.loads(r['facts'] or '{}')
        except Exception: continue
        hist.append({k[3:]: v for k, v in f.items() if k.startswith('bl_') and isinstance(v, (int, float))})
        if len(hist) >= max_n: break
    out = []
    spec = {k: (d, mn) for k, _, _, d, mn in METRICS}; spec['cruise_thr'] = (+1, 0.05)
    for k, v in cur.items():
        xs = np.array([h[k] for h in hist if k in h], float)
        if len(xs) < 3 or k not in spec: continue
        d, mn = spec[k]
        med = float(np.median(xs)); mad = float(np.median(np.abs(xs - med))) * 1.4826
        lim = max(3 * mad, mn, 0.25 * abs(med))
        if (v - med) * d > lim:
            out.append({'key': k, 'v': round(v, 3), 'med': round(med, 3), 'n': int(len(xs)), 'dir': d})
    A.baseline = out
    return out


NAMES = {
    'vib_p95': ('Titreşim (p95)', 'Vibration (p95)', 'الاهتزاز (p95)'),
    'vib_z': ('Z titreşimi ortalaması', 'Mean Z vibration', 'متوسط اهتزاز Z'),
    'cell_min': ('En düşük hücre gerilimi (V)', 'Lowest cell voltage (V)', 'أدنى جهد للخلية (فولت)'),
    'vcc_min': ('En düşük kart beslemesi Vcc (V)', 'Lowest board supply Vcc (V)', 'أدنى جهد تغذية اللوحة Vcc (فولت)'),
    'bat_ir': ('Batarya iç direnci (mΩ)', 'Battery internal resistance (mΩ)', 'المقاومة الداخلية للبطارية (مللي أوم)'),
    'mag_var': ('Pusula tutarsızlığı (EKF SM)', 'Compass inconsistency (EKF SM)', 'عدم اتساق البوصلة (EKF SM)'),
    'roll_rms': ('Yatış takip hatası (RMS °)', 'Roll tracking error (RMS °)', 'خطأ تتبع الدحرجة (RMS °)'),
    'pitch_rms': ('Yunuslama takip hatası (RMS °)', 'Pitch tracking error (RMS °)', 'خطأ تتبع الانحدار (RMS °)'),
    'sats': ('Ortalama uydu sayısı', 'Mean satellite count', 'متوسط عدد الأقمار'),
    'hdop': ('En yüksek HDOP', 'Highest HDOP', 'أعلى HDOP'),
    'mot_imb': ('Motor dengesizliği (µs)', 'Motor imbalance (µs)', 'عدم توازن المحركات (ميكروثانية)'),
    'hover_thr': ('Asılı kalma gazı', 'Hover throttle', 'خانق التحليق'),
    'cruise_thr': ('Seyir gazı', 'Cruise throttle', 'خانق الطيران المستوي'),
    'cpu': ('İşlemci yükü (en yüksek)', 'CPU load (max)', 'حمل المعالج (الأقصى)'),
}
HEAD = ('Bu aracın önceki uçuşlarına göre alışılmadık', 'Unusual compared with this aircraft\'s previous flights',
        'غير معتاد مقارنةً برحلات هذه الطائرة السابقة')
LINE = ('{name}: {v} (bu araçta olağan değer {med}, {n} uçuş)', '{name}: {v} (usual for this aircraft {med}, {n} flights)',
        '{name}: {v} (المعتاد لهذه الطائرة {med}، {n} رحلات)')


def render(A, lg):
    i = {'tr': 0, 'en': 1, 'ar': 2}.get(lg, 1)
    items = getattr(A, 'baseline', None) or []
    if not items: return None, []
    f = lambda x: (f'{x:.2f}' if abs(x) < 10 else f'{x:.0f}')
    return HEAD[i], [LINE[i].format(name=NAMES.get(b['key'], (b['key'],) * 3)[i], v=f(b['v']), med=f(b['med']), n=b['n']) for b in items]
