"""Uçuş anındaki hava durumu (çevrimiçi, ücretsiz Open-Meteo — anahtar gerekmez).

Uçuşun GPS saatine ve kalkış konumuna göre saatlik geçmiş veri alınır: sıcaklık, rüzgâr (10 m), esinti,
yön, nem, basınç, bulut ve yağış. İnternet yoksa yalnızca logdan kestirilen rüzgâr kullanılır.
Sonuçlar önbelleğe alınır; aynı uçuş için tekrar internet gerekmez.
"""
from __future__ import annotations
import json, os, time, urllib.request, urllib.parse
from .paths import data_dir

VARS = 'temperature_2m,relative_humidity_2m,surface_pressure,cloud_cover,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m'
DIRS = {'tr': ['K', 'KD', 'D', 'GD', 'G', 'GB', 'B', 'KB'], 'en': ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
        'ar': ['ش', 'ش.ق', 'ق', 'ج.ق', 'ج', 'ج.غ', 'غ', 'ش.غ']}


def compass(deg, lang='tr'):
    if deg is None: return '-'
    return DIRS.get(lang, DIRS['en'])[int(((deg % 360) + 22.5) // 45) % 8]


def _cache_path():
    return os.path.join(data_dir(), 'weather_cache.json')


def _cache():
    try:
        with open(_cache_path(), encoding='utf-8') as f: return json.load(f)
    except Exception: return {}


def fetch(lat, lon, unix, timeout=8):
    """unix anındaki saatlik hava. Hata olursa None."""
    if lat is None or lon is None or not unix: return None
    day = time.strftime('%Y-%m-%d', time.gmtime(unix)); hour = time.gmtime(unix).tm_hour
    key = f'{lat:.2f},{lon:.2f},{day},{hour}'
    c = _cache()
    if key in c: return c[key]
    age_days = (time.time() - unix) / 86400
    q = {'latitude': f'{lat:.4f}', 'longitude': f'{lon:.4f}', 'hourly': VARS, 'wind_speed_unit': 'ms', 'timezone': 'UTC'}
    if age_days > 6:
        url = 'https://archive-api.open-meteo.com/v1/archive?' + urllib.parse.urlencode({**q, 'start_date': day, 'end_date': day})
    else:
        url = 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode({**q, 'past_days': 7, 'forecast_days': 1})
    req = urllib.request.Request(url, headers={'User-Agent': 'PixhawkLogAnaliz'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    h = d.get('hourly') or {}
    times = h.get('time') or []
    want = f'{day}T{hour:02d}:00'
    if want not in times: return None
    i = times.index(want)
    g = lambda k: (h.get(k) or [None] * len(times))[i]
    w = {'source': 'Open-Meteo', 'time_utc': want.replace('T', ' '), 'lat': lat, 'lon': lon, 'temp': g('temperature_2m'),
         'rh': g('relative_humidity_2m'), 'press': g('surface_pressure'), 'cloud': g('cloud_cover'), 'precip': g('precipitation'),
         'wind': g('wind_speed_10m'), 'dir': g('wind_direction_10m'), 'gust': g('wind_gusts_10m')}
    c[key] = w
    try:
        with open(_cache_path(), 'w', encoding='utf-8') as f: json.dump(c, f)
    except Exception: pass
    return w


def for_analysis(A):
    """Analiz için hava durumunu getirir (A.weather'a yazar)."""
    try:
        home = A.facts.get('home'); u = A.L.unix_at(A.flights[0][0] if A.flights else 0)
        if not home or not u: return None
        A.weather = fetch(home[0], home[1], u)
    except Exception:
        A.weather = None
    return A.weather


def rows(A, lang='tr'):
    """Rapor/arayüz için (etiket, değer) satırları."""
    i = ('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0
    Lb = {'src': ('Kaynak', 'Source', 'المصدر'), 'time': ('Saat (UTC)', 'Time (UTC)', 'الوقت (UTC)'), 'temp': ('Sıcaklık', 'Temperature', 'درجة الحرارة'),
          'wind': ('Rüzgâr (10 m)', 'Wind (10 m)', 'الرياح (10 م)'), 'gust': ('Esinti', 'Gusts', 'الهبات'), 'rh': ('Nem', 'Humidity', 'الرطوبة'),
          'press': ('Basınç', 'Pressure', 'الضغط'), 'cloud': ('Bulut', 'Cloud cover', 'الغيوم'), 'precip': ('Yağış', 'Precipitation', 'الهطول'),
          'logw': ('Logdan kestirilen rüzgâr (EKF)', 'Wind estimated from log (EKF)', 'الرياح المقدرة من السجل (EKF)'),
          'none': ('Çevrimiçi hava verisi alınamadı (internet yok veya GPS saati yok).', 'Online weather not available (no internet or no GPS time).', 'بيانات الطقس غير متاحة (لا إنترنت أو لا توقيت GPS).')}
    out = []
    w = getattr(A, 'weather', None)
    if w:
        f = lambda v, u='', d=1: '-' if v is None else f'{v:.{d}f}{u}'
        out += [(Lb['src'][i], w.get('source', '')), (Lb['time'][i], w.get('time_utc', '')), (Lb['temp'][i], f(w.get('temp'), ' °C')),
                (Lb['wind'][i], f"{f(w.get('wind'), ' m/s')} · {compass(w.get('dir'), lang)} ({f(w.get('dir'), '°', 0)})"),
                (Lb['gust'][i], f(w.get('gust'), ' m/s')), (Lb['rh'][i], f(w.get('rh'), ' %', 0)), (Lb['press'][i], f(w.get('press'), ' hPa', 0)),
                (Lb['cloud'][i], f(w.get('cloud'), ' %', 0)), (Lb['precip'][i], f(w.get('precip'), ' mm'))]
    if getattr(A, 'wind', None):
        wd = A.wind
        out.append((Lb['logw'][i], f"{wd['mean']:.1f} m/s (max {wd['max']:.1f}) · {compass(wd['from_deg'], lang)} ({wd['from_deg']:.0f}°)"))
    if not out: out.append(('', Lb['none'][i]))
    return out
