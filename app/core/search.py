"""Arşivde gelişmiş arama.

Doğal dil sorguları (TR/EN/AR) filtrelere çevrilir, örn.:
  "son 3 ayda GPS kaybı yaşayan uçuşlar", "kırım olan multikopter uçuşları", "puanı 60'ın altında",
  "last 2 weeks vibration", "آخر 3 أشهر فقدان GPS".
Ayrıca yapılandırılmış filtrelerle (dönem, sonuç, bulgu, uçak, pilot, puan) birleştirilebilir.
"""
from __future__ import annotations
import json, re, time

TOPICS = {
    'gps': (['gps', 'uydu', 'konum kayb', 'satellite', 'hdop', 'أقمار', 'الموقع'], ['gps_', 'cause_gps']),
    'vibration': (['titreşim', 'titresim', 'vibration', 'vibe', 'clip', 'اهتزاز'], ['vibe_', 'cause_vibration']),
    'battery': (['batarya', 'pil', 'voltaj', 'gerilim', 'battery', 'voltage', 'بطارية'], ['bat_', 'cause_battery', 'pa_batt', 'vcc_']),
    'radio': (['radyo', 'rc kayb', 'kumanda', 'radio', 'rc loss', 'failsafe', 'راديو', 'وصلة'], ['rc_', 'cause_radio', 'pa_thr_fs']),
    'compass': (['pusula', 'manyetik', 'compass', 'magnetic', 'بوصلة', 'مغناطيس'], ['mag_', 'cause_compass']),
    'ekf': (['ekf', 'varyans', 'variance'], ['ekf_', 'cause_ekf']),
    'stall': (['stall', 'hız kayb', 'hava hızı', 'airspeed', 'انهيار', 'السرعة الجوية'], ['as_', 'cause_stall']),
    'anomaly': (['anomali', 'alışılmadık', 'anomaly', 'unusual', 'شذوذ'], ['anomaly']),
    'motor': (['motor', 'esc', 'محرك'], ['mot_', 'pa_hover']),
    'wind': (['rüzgar', 'rüzgâr', 'wind', 'رياح'], ['wind_']),
    'control': (['tutum', 'kontrol kayb', 'attitude', 'control', 'الوضعية'], ['att_', 'cause_control']),
}
VERDICTS = {
    'crash': ['kırım', 'kirim', 'kaza', 'düştü', 'crash', 'accident', 'تحطم', 'حادث'],
    'incident': ['sorunlu', 'olaylı', 'incident', 'issue', 'problem', 'مشاكل', 'مشكلة'],
    'normal': ['normal uçuş', 'sorunsuz', 'normal flight', 'normal', 'طبيعي'],
}
PROFILES = {'copter': ['multikopter', 'kopter', 'drone', 'copter', 'quad', 'متعدد'], 'vtol': ['vtol', 'quadplane', 'dikey'],
            'plane': ['sabit kanat', 'uçak', 'plane', 'fixed wing', 'طائرة', 'جناح ثابت'], 'heli': ['helikopter', 'heli', 'مروحية']}
UNITS = {'gün': 1, 'gun': 1, 'day': 1, 'يوم': 1, 'أيام': 1, 'hafta': 7, 'week': 7, 'أسبوع': 7, 'أسابيع': 7,
         'ay': 30, 'month': 30, 'شهر': 30, 'أشهر': 30, 'yıl': 365, 'yil': 365, 'year': 365, 'سنة': 365}
WORDN = {'bir': 1, 'iki': 2, 'üç': 3, 'dört': 4, 'beş': 5, 'altı': 6, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'six': 6,
         'واحد': 1, 'اثنين': 2, 'ثلاثة': 3, 'ستة': 6}
STOP = set('son ayda günde haftada yılda içinde olan olanlar yaşayan yaşanan uçuş uçuşlar uçuşları uçuşu ile ve veya ki de da '
           'kaybı kaybi kayıp kayip sorunu sorun sorunlar olanlar yaşanan problem problems loss lost issues issue '
        'the last in with flights flight that had having of and or من في آخر خلال الرحلات رحلات التي فقدان مشكلة'.split())


def parse(q: str):
    """Sorgu → filtre sözlüğü."""
    s = (q or '').lower().strip()
    f = {}
    # dönem: "son 3 ay", "last 2 weeks", "آخر 3 أشهر", "son ay"
    m = re.search(r'(son|last|past|آخر|خلال)\s*(\d+|' + '|'.join(WORDN) + r')?\s*(' + '|'.join(sorted(UNITS, key=len, reverse=True)) + r')', s)
    if m:
        n = m.group(2); n = int(n) if (n and n.isdigit()) else WORDN.get(n or '', 1)
        f['days'] = n * UNITS[m.group(3)]
        s = s.replace(m.group(0), ' ')
    for k, ws in VERDICTS.items():
        if any(w in s for w in ws):
            f['verdict'] = k
            for w in ws: s = s.replace(w, ' ')
            break
    tops = []
    for k, (ws, _) in TOPICS.items():
        if any(w in s for w in ws):
            tops.append(k)
            for w in ws: s = s.replace(w, ' ')
    if tops: f['topics'] = tops
    for k, ws in PROFILES.items():
        if any(w in s for w in ws):
            f['profile'] = k
            for w in ws: s = s.replace(w, ' ')
            break
    m = re.search(r"(puan\w*|skor\w*|score)\D{0,12}?(\d{1,3})\W*(?:'?[ıi]n|'?un)?\s*(altında|altı|below|under|<|üstünde|üzeri|above|over|>)", s) or \
        re.search(r"(puan\w*|score)\s*(<|>)\s*(\d{1,3})", s)
    if m:
        g = m.groups()
        if g[1] in ('<', '>'): op, val = g[1], int(g[2])
        else: val = int(g[1]); op = '<' if g[2] in ('altında', 'altı', 'below', 'under', '<') else '>'
        f['score_max' if op == '<' else 'score_min'] = val
        s = s.replace(m.group(0), ' ')
    m = re.search(r'(\d+)\s*(dakika|dk|min)\w*\s*(dan|den)?\s*(uzun|fazla|longer|more)', s)
    if m:
        f['min_flight_min'] = int(m.group(1)); s = s.replace(m.group(0), ' ')
    words = [w for w in re.split(r'[\s,;]+', s) if w and w not in STOP and len(w) > 1 and not w.isdigit()]
    if words: f['text'] = ' '.join(words)
    return f


def _ts(r):
    if r.get('flight_ts'): return float(r['flight_ts'])
    for k in ('flight_date', 'analyzed_at'):
        v = r.get(k)
        if v:
            try: return time.mktime(time.strptime(v[:16], '%Y-%m-%d %H:%M'))
            except Exception:
                try: return time.mktime(time.strptime(v[:10], '%Y-%m-%d'))
                except Exception: pass
    return 0


def apply(rows, f, aircraft_names=None, pilot_names=None):
    out = []
    now = time.time()
    for r in rows:
        if f.get('days') and _ts(r) < now - f['days'] * 86400: continue
        if f.get('verdict') and r.get('verdict') != f['verdict']: continue
        if f.get('profile') and (r.get('profile') or '') != f['profile']: continue
        if f.get('aircraft') and (r.get('aircraft') or '') != f['aircraft']: continue
        if f.get('pilot') and (r.get('pilot') or '') != f['pilot']: continue
        if f.get('score_max') is not None and (r.get('overall') or 0) >= f['score_max']: continue
        if f.get('score_min') is not None and (r.get('overall') or 0) <= f['score_min']: continue
        if f.get('min_flight_min') and (r.get('flight_time') or 0) < f['min_flight_min'] * 60: continue
        if f.get('topics'):
            try: fk = json.loads(r.get('findings') or '[]')
            except Exception: fk = []
            fk = fk + (['cause_' + r['cause']] if r.get('cause') else [])
            if not all(any(k.startswith(p) for k in fk for p in TOPICS[t][1]) for t in f['topics']): continue
        if f.get('text'):
            hay = ' '.join(str(r.get(k) or '') for k in ('name', 'notes', 'tags', 'vehicle', 'version', 'device', 'aircraft')).lower()
            hay += ' ' + (aircraft_names or {}).get(r.get('aircraft') or '', '').lower() + ' ' + (pilot_names or {}).get(r.get('pilot') or '', '').lower()
            if not all(w in hay for w in f['text'].split()): continue
        out.append(r)
    return out


DESC = {
    'days': ('son {v} gün', 'last {v} days', 'آخر {v} يوم'), 'verdict': ('sonuç: {v}', 'verdict: {v}', 'النتيجة: {v}'),
    'topics': ('bulgu: {v}', 'finding: {v}', 'نتيجة: {v}'), 'profile': ('profil: {v}', 'profile: {v}', 'الملف: {v}'),
    'score_max': ('puan < {v}', 'score < {v}', 'الدرجة < {v}'), 'score_min': ('puan > {v}', 'score > {v}', 'الدرجة > {v}'),
    'min_flight_min': ('uçuş > {v} dk', 'flight > {v} min', 'الطيران > {v} د'), 'text': ('metin: "{v}"', 'text: "{v}"', 'نص: "{v}"'),
}


def describe(f, lang='tr'):
    i = ('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0
    parts = []
    for k, v in f.items():
        if k in DESC:
            parts.append(DESC[k][i].format(v=', '.join(v) if isinstance(v, list) else v))
    return ' · '.join(parts)
