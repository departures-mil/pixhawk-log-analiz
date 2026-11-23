"""Parametre Merkezi (Full Parameter List): ArduPilot'un bütün araç sınıfları için resmî parametre listesi.

Veri: app/data/params_full.json.gz (autotest.ardupilot.org apm.pdef.json, araç başına) + params_tx_tr/ar.json.gz
(offline makine çevirisi). Elle yazılmış çeviriler (parametredeki 'tr'/'ar') ve kullanıcının yapay zekâ ile
yaptırdığı çeviriler makine çevirisinden önce gelir. Tamamen offline çalışır.

İçerik: araç bazında gezinme, açıklama/birim/aralık/varsayılan/seçenek/bitmask çözümü, .param dosyası okuma-yazma
(Mission Planner, QGroundControl, CSV), varsayılandan farklı ve riskli değer denetimi, iki dosya karşılaştırma,
anahtar/yıldız işaretleri ve notlar, offline "nasıl yaparım" arama motoru, yapay zekâ için bağlam üretimi.
"""
from __future__ import annotations
import gzip, json, math, os, re, threading, time
from .paths import res

VEHICLES = ['Plane', 'Copter', 'Heli', 'Rover', 'Sub', 'Blimp', 'Tracker', 'Periph']
VNAME = {'Plane': ('ArduPlane (sabit kanat / QuadPlane)', 'ArduPlane (fixed wing / QuadPlane)', 'ArduPlane (جناح ثابت / QuadPlane)'),
         'Copter': ('ArduCopter (çok rotorlu drone)', 'ArduCopter (multirotor drone)', 'ArduCopter (طائرة متعددة المراوح)'),
         'Heli': ('Helikopter (ArduCopter-Heli)', 'Helicopter (ArduCopter-Heli)', 'مروحية (ArduCopter-Heli)'),
         'Rover': ('Rover (kara aracı / tekne)', 'Rover (ground vehicle / boat)', 'Rover (مركبة أرضية / قارب)'),
         'Sub': ('ArduSub (sualtı aracı)', 'ArduSub (underwater ROV)', 'ArduSub (مركبة تحت الماء)'),
         'Blimp': ('Blimp (zeplin)', 'Blimp', 'Blimp (منطاد)'),
         'Tracker': ('AntennaTracker (anten izleyici)', 'AntennaTracker', 'AntennaTracker (متتبع الهوائي)'),
         'Periph': ('AP_Periph (CAN çevre birimi)', 'AP_Periph (CAN peripheral)', 'AP_Periph (ملحق CAN)')}
LI = {'tr': 0, 'en': 1, 'ar': 2}
SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9(])')


def vname(v, lang):
    return VNAME.get(v, (v, v, v))[LI.get(lang, 0)]


def _num(x):
    try:
        f = float(x)
        return f if math.isfinite(f) else None
    except Exception:
        return None


def fmt(v):
    if v is None: return ''
    if isinstance(v, str): return v
    f = float(v)
    if f.is_integer() and abs(f) < 1e12: return str(int(f))
    return f'{f:.6g}'


class PDB:
    """Parametre veritabanı (tek örnek, tembel yükleme)."""
    _inst = None
    _lock = threading.Lock()

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._inst is None: cls._inst = PDB()
            return cls._inst

    def __init__(self):
        self.full = True
        p = res('data', 'params_full.json.gz')
        if os.path.exists(p):
            with gzip.open(p, 'rt', encoding='utf-8') as f: D = json.load(f)
        else:   # eski kütüphane (yalnız Plane/Copter) — veri hattı çalışmadıysa
            self.full = False
            O = json.load(open(res('data', 'params.json'), encoding='utf-8'))
            P = {}
            for k, o in O['params'].items():
                e = {'v': o.get('v', []), 'g': o.get('g')}
                en = o.get('en') or ['', '']
                e['dn'], e['d'] = en[0], en[1]
                for a, b in (('u', 'u'), ('usr', 'usr'), ('inc', 'inc')):
                    if o.get(a) is not None: e[b] = o[a]
                if o.get('r'):
                    lo, hi = (str(o['r']).split() + [None, None])[:2]; e['r'] = [_num(lo), _num(hi)]
                for a, b in (('vals', 'vals'), ('bm', 'bits')):
                    x = o.get(a)
                    if isinstance(x, str) and x:
                        e[b] = {kv.split(':', 1)[0].strip(): kv.split(':', 1)[1].strip() for kv in x.split(',') if ':' in kv}
                    elif isinstance(x, dict): e[b] = x
                for lg in ('tr', 'ar'):
                    if o.get(lg): e[lg] = o[lg]
                P[k] = e
            D = {'vehicles': ['Plane', 'Copter'], 'groups': O.get('groups', {}), 'params': P, 'built': '', 'source': {}}
        self.D = D; self.P = D['params']; self.G = D.get('groups', {})
        have = D.get('vehicles', [])
        # autotest'te ayrı Heli listesi yok: Copter listesi helikopter parametrelerini (H_…) de içerir
        self.alias = {'Heli': 'Copter'} if 'Heli' not in have and 'Copter' in have and self.full else {}
        self.vehicles = [v for v in VEHICLES if v in have or v in self.alias] or ['Plane', 'Copter']
        self.built = D.get('built', ''); self.source = D.get('source', {})
        self.tx = {}
        for lg in ('tr', 'ar'):
            q = res('data', f'params_tx_{lg}.json.gz')
            try:
                with gzip.open(q, 'rt', encoding='utf-8') as f: self.tx[lg] = json.load(f)
            except Exception:
                self.tx[lg] = {}
        self.user_tx = {}     # yapay zekâ çevirileri: {lang: {name: [dn, d]}}
        self._by_v = {}
        self._blob = {}

    # ------------------------------------------------------------ erişim
    def names(self, vehicle):
        if vehicle not in self._by_v:
            if vehicle in self.alias:
                self._by_v[vehicle] = [k for k in self.names(self.alias[vehicle]) if not k.startswith(('MOT_', 'ATC_RAT_YAW'))]
            else:
                self._by_v[vehicle] = sorted(k for k, p in self.P.items() if vehicle in p.get('v', []))
        return self._by_v[vehicle]

    def count(self, vehicle):
        return len(self.names(vehicle))

    def meta(self, name, vehicle=None):
        p = self.P.get(name)
        if not p: return None
        vehicle = self.alias.get(vehicle, vehicle)
        e = {k: v for k, v in p.items() if k != 'var'}
        if vehicle in e.get('v', []) and 'Copter' in e['v'] and self.alias: e['v'] = e['v'] + ['Heli']
        if vehicle and p.get('var', {}).get(vehicle):
            for k, v in p['var'][vehicle].items():
                if v is None: e.pop(k, None)
                else: e[k] = v
        d = p.get('def')
        e['default'] = d.get(vehicle) if isinstance(d, dict) else d
        return e

    def groups(self, vehicle):
        gs = {}
        for k in self.names(vehicle):
            g = self.P[k].get('g') or k.split('_')[0]; gs[g] = gs.get(g, 0) + 1
        return sorted(gs.items())

    def group_text(self, g, lang):
        x = self.G.get(g) or {}
        en = x.get('en') or g
        if lang == 'en': return en
        return x.get(lang) or self.tx.get(lang, {}).get(en) or en

    def lbl(self, text, lang):
        """Seçenek / bit adlarının çevirisi."""
        if lang == 'en' or not text: return text
        return self.tx.get(lang, {}).get(text) or text

    def text(self, name, vehicle, lang):
        """(görünen ad, açıklama, kaynak) — kaynak: 'curated' | 'ai' | 'mt' | 'en'"""
        m = self.meta(name, vehicle) or {}
        dn, d = m.get('dn', ''), m.get('d', '')
        if lang == 'en': return dn, d, 'en'
        if self.user_tx.get(lang, {}).get(name): u = self.user_tx[lang][name]; return u[0], u[1], 'ai'
        if m.get(lang): return m[lang][0], m[lang][1], 'curated'
        T = self.tx.get(lang, {})
        tdn = T.get(dn); td = T.get(d)
        if tdn or td: return tdn or dn, td or d, 'mt'
        return dn, d, 'en'

    def default(self, name, vehicle):
        m = self.meta(name, vehicle)
        return m.get('default') if m else None

    def blob(self, name, vehicle):
        """Arama için tüm dillerde birleşik metin (küçük harf)."""
        key = (name, vehicle)
        b = self._blob.get(key)
        if b is None:
            m = self.meta(name, vehicle) or {}
            parts = [name, name.replace('_', ' '), m.get('dn', ''), m.get('d', '')]
            for lg in ('tr', 'ar'):
                a, bb, _ = self.text(name, vehicle, lg); parts += [a, bb]
            for f in ('vals', 'bits'):
                for x in (m.get(f) or {}).values():
                    parts += [x, self.lbl(x, 'tr'), self.lbl(x, 'ar')]
            b = ' '.join(parts).lower()
            self._blob[key] = b
        return b


# ------------------------------------------------------------------ değer yorumlama
def decode_bits(value, bits):
    """[(bit, ad, açık mı)]"""
    out = []
    try: iv = int(float(value)) if value is not None else 0
    except Exception: iv = 0
    for k, lab in sorted((bits or {}).items(), key=lambda kv: int(kv[0]) if str(kv[0]).lstrip('-').isdigit() else 0):
        try: b = int(k)
        except Exception: continue
        out.append((b, lab, bool(iv >> b & 1) if b >= 0 else False))
    return out


def value_label(value, vals):
    if value is None or not vals: return None
    for k, lab in vals.items():
        kv = _num(k)
        if kv is not None and abs(kv - float(value)) < 1e-6: return lab
    return None


def check_value(value, meta):
    """Değer tanıma uygun mu? (sorun_kodu | None)"""
    if value is None or not meta: return None
    r = meta.get('r')
    if r and r[0] is not None and r[1] is not None:
        lo, hi = float(r[0]), float(r[1])
        if lo <= hi and (value < lo - 1e-9 or value > hi + 1e-9): return 'range'
    vals = meta.get('vals')
    if vals and not meta.get('bits') and value_label(value, vals) is None and len(vals) >= 2: return 'enum'
    bits = meta.get('bits')
    if bits:
        try:
            iv = int(float(value)); known = 0
            for k in bits:
                if str(k).isdigit(): known |= 1 << int(k)
            if iv >= 0 and iv & ~known and known: return 'bits'
        except Exception:
            pass
    return None


# ------------------------------------------------------------------ dosya okuma / yazma
def parse_text(txt):
    """Mission Planner (.param: AD,DEĞER), QGroundControl (.params: 1 1 AD DEĞER TÜR), boşluklu ve CSV biçimlerini okur."""
    out = {}
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s[0] in '#;/': continue
        if '#' in s: s = s.split('#', 1)[0].strip()
        parts = [x for x in re.split(r'[,\t ;]+', s) if x]
        if len(parts) >= 5 and parts[0].isdigit() and parts[1].isdigit():    # QGC
            nm, val = parts[2], parts[3]
        elif len(parts) >= 2:
            nm, val = parts[0], parts[1]
        else:
            continue
        v = _num(val)
        if v is None or not re.match(r'^[A-Z][A-Z0-9_]{1,31}$', nm): continue
        out[nm] = v
    return out


def read_file(path):
    with open(path, 'rb') as f: b = f.read()
    for enc in ('utf-8-sig', 'utf-16', 'cp1254', 'latin-1'):
        try:
            txt = b.decode(enc)
            if '\x00' in txt and enc != 'utf-16': continue
            return parse_text(txt)
        except Exception:
            continue
    return {}


def write_file(params, path, fmt_='mp', vehicle='', note=''):
    names = sorted(params)
    with open(path, 'w', encoding='utf-8', newline='\r\n' if os.name == 'nt' else '\n') as f:
        if fmt_ == 'qgc':
            f.write(f'# Onboard parameters for Vehicle 1\n# Pixhawk Log Analiz {time.strftime("%Y-%m-%d %H:%M")} {vehicle} {note}\n#\n# Vehicle-Id Component-Id Name Value Type\n')
            for k in names:
                v = params[k]; ty = 9 if not float(v).is_integer() else 6
                f.write(f'1\t1\t{k}\t{fmt(v)}\t{ty}\n')
        elif fmt_ == 'csv':
            f.write('name,value\n')
            for k in names: f.write(f'{k},{fmt(params[k])}\n')
        else:
            f.write(f'# Pixhawk Log Analiz · {time.strftime("%Y-%m-%d %H:%M")} · {vehicle} · {note}\n')
            for k in names: f.write(f'{k},{fmt(params[k])}\n')
    return path


SIGNS = [('Heli', ('H_SW_TYPE', 'H_RSC_MODE', 'H_COL_MAX')), ('Sub', ('SURFACE_DEPTH', 'JS_GAIN_DEFAULT', 'SURFACE_MAX_THR')),
         ('Blimp', ('FINS_FREQ_HZ', 'BLIMP_')), ('Tracker', ('YAW_RANGE', 'PITCH_RANGE', 'TRACK_')),
         ('Rover', ('CRUISE_SPEED', 'CRUISE_THROTTLE', 'PIVOT_TURN_ANGLE', 'WP_OVERSHOOT')),
         ('Plane', ('TRIM_ARSPD_CM', 'AIRSPEED_CRUISE', 'Q_ENABLE', 'LIM_ROLL_CD', 'ROLL_LIMIT_DEG', 'PTCH_LIM_MAX_DEG', 'TECS_')),
         ('Copter', ('WPNAV_', 'MOT_THST_HOVER', 'PILOT_SPEED_UP', 'LOIT_SPEED', 'ATC_RAT_RLL_P', 'ANGLE_MAX'))]


def detect_vehicle(params, hint=None):
    if hint in VEHICLES: return hint
    if not params: return 'Plane'
    keys = set(params)
    for v, sig in SIGNS:
        for s in sig:
            if s.endswith('_') and any(k.startswith(s) for k in keys): return v
            if s in keys: return v
    db = PDB.get()
    best = max(db.vehicles, key=lambda v: len(keys & set(db.names(v))))
    return best


def vehicle_from_log(veh):
    return {'Plane': 'Plane', 'Copter': 'Copter', 'Rover': 'Rover', 'Sub': 'Sub', 'Heli': 'Heli'}.get(veh or '', 'Plane')


# ------------------------------------------------------------------ inceleme / karşılaştırma
def inspect(params, vehicle):
    """Her parametre için satır: (ad, değer, varsayılan, durum listesi)"""
    db = PDB.get(); rows = []
    for k in sorted(params):
        v = params[k]; m = db.meta(k, vehicle)
        st = []
        if m is None:
            st.append('unknown')
        else:
            d = m.get('default')
            if isinstance(d, (int, float)) and abs(float(d) - v) > 1e-6 * max(1, abs(float(d))): st.append('changed')
            c = check_value(v, m)
            if c: st.append(c)
            if m.get('ro'): st.append('ro')
        rows.append({'name': k, 'value': v, 'default': (m or {}).get('default'), 'st': st})
    return rows


def compare(a, b):
    out = []
    for k in sorted(set(a) | set(b)):
        va, vb = a.get(k), b.get(k)
        if va is None: s = 'only_b'
        elif vb is None: s = 'only_a'
        elif abs(va - vb) > 1e-6 * max(1, abs(va)): s = 'diff'
        else: s = 'same'
        out.append({'name': k, 'a': va, 'b': vb, 'st': s})
    return out


# ------------------------------------------------------------------ risk denetimi
def risks(params, vehicle, lang='tr'):
    """Analizdeki parametre denetimi kuralları + kritik parametre kuralları. [{'sev','text','param'}]"""
    from .pcritical import RULES
    out = []
    if not params: return out
    # analizdeki kurallar (aynı metinler)
    try:
        from . import analysis as AN

        class _L: pass
        X = AN.Analysis.__new__(AN.Analysis)
        X.L = _L(); X.L.params = params; X.vehicle = 'Copter' if vehicle in ('Copter', 'Heli') else 'Plane' if vehicle == 'Plane' else vehicle
        if vehicle in ('Plane', 'Copter', 'Heli'):
            from . import texts as TX
            X._params()
            for f in X.param_findings:
                if f.get('param') and f['text'].get('k') not in ('pa_ok', 'pa_none'):
                    out.append({'sev': f['sev'], 'text': TX.render(f['text'], lang), 'param': f['param']})
    except Exception:
        pass
    seen = {f.get('param') for f in out}
    for r in RULES:
        if r['v'] and vehicle not in r['v']: continue
        p = r['p']
        if p in seen or p not in params: continue
        try: hit = r['test'](params[p], params)
        except Exception: hit = False
        if hit:
            out.append({'sev': r['sev'], 'text': r['msg'][LI.get(lang, 0)].format(v=fmt(params[p])), 'param': p})
    # tanım dışı değerler
    db = PDB.get()
    for k, v in params.items():
        m = db.meta(k, vehicle)
        c = check_value(v, m) if m else None
        if c == 'range':
            r = m['r']
            out.append({'sev': 1, 'param': k, 'text': {'tr': f'{k} = {fmt(v)} önerilen aralığın dışında ({fmt(r[0])} … {fmt(r[1])}).',
                                                       'en': f'{k} = {fmt(v)} is outside the recommended range ({fmt(r[0])} … {fmt(r[1])}).',
                                                       'ar': f'{k} = {fmt(v)} خارج النطاق الموصى به ({fmt(r[0])} … {fmt(r[1])}).'}[lang]})
        elif c == 'enum':
            out.append({'sev': 1, 'param': k, 'text': {'tr': f'{k} = {fmt(v)} tanımlı seçeneklerden biri değil.',
                                                       'en': f'{k} = {fmt(v)} is not one of the defined options.',
                                                       'ar': f'{k} = {fmt(v)} ليس من الخيارات المعرّفة.'}[lang]})
    out.sort(key=lambda f: -f['sev'])
    return out


# ------------------------------------------------------------------ offline arama ("nasıl yaparım?")
SYN = [
    (r'batarya|pil|akü|بطارية|البطارية', 'battery batt voltage capacity'), (r'voltaj|gerilim|جهد', 'voltage volt'),
    (r'eve dön|geri dön|rtl|عودة|العودة', 'rtl return home'), (r'kalkış|havalan|إقلاع|الإقلاع', 'takeoff tkoff launch'),
    (r'iniş|indir|هبوط|الهبوط', 'land landing flare'), (r'hız|سرعة|السرعة', 'speed'), (r'hava hız|سرعة جوية', 'airspeed arspd'),
    (r'irtifa|yükseklik|ارتفاع|الارتفاع', 'altitude alt height'), (r'kumanda|radyo|alıcı|rc|راديو|جهاز التحكم|المستقبل', 'rc radio receiver throttle failsafe'),
    (r'failsafe|güvenlik|kayıp|kaybol|طوارئ|فقدان', 'failsafe fs action'), (r'pusula|manyetometre|بوصلة|البوصلة', 'compass mag'),
    (r'titreşim|filtre|çentik|اهتزاز|مرشح', 'vibration filter notch hntch ins'), (r'gaz|throttle|خانق|الخانق', 'throttle thr'),
    (r'motor|محرك|المحرك', 'motor mot spin'), (r'servo|سيرفو', 'servo function trim reversed'), (r'kamera|كاميرا', 'camera cam trigger'),
    (r'gimbal|mount|حامل', 'mount gimbal'), (r'çit|sınır|geofence|سياج', 'fence'), (r'görev|misyon|مهمة|المهمة', 'mission auto wp waypoint'),
    (r'log|kayıt|سجل', 'log logging bitmask'), (r'arm|silah|تسليح|التسليح', 'arming arm check'), (r'mod|uçuş modu|وضع', 'mode fltmode flight mode'),
    (r'yatış|bank|دوران|الميل الجانبي', 'roll bank'), (r'yunuslama|burun|ميلان', 'pitch'), (r'sapma|yön|dümen|انعراج|الاتجاه', 'yaw rudder heading'),
    (r'rüzgar|رياح', 'wind'), (r'stall|tutunma|انهيار', 'stall airspeed min'), (r'paraşüt|مظلة', 'parachute chute'),
    (r'lidar|mesafe sensör|sonar|مستشعر المسافة', 'rangefinder rngfnd'), (r'optik akış|تدفق بصري', 'flow optical'),
    (r'telemetri|seri port|mavlink|قياس عن بعد|منفذ', 'serial telem mavlink protocol baud'), (r'\bgps\b|uydu|أقمار', 'gps gnss satellite'),
    (r'ekf|konum tahmini|مرشح كالمان', 'ek3 ekf ahrs'), (r'otomatik ayar|autotune|ضبط آلي', 'autotune tune'),
    (r'uyarı|ses|buzzer|تنبيه|صوت', 'notify buzzer'), (r'led|ışık|ضوء', 'ntf led'), (r'osd', 'osd'), (r'can\b|dronecan|uavcan', 'can dronecan'),
    (r'dikey|vtol|quadplane|عمودي', 'q_ vtol quadplane'), (r'pid|kazanç|ayar|ضبط|كسب', 'p i d gain rate atc'), (r'tekne|bot|قارب', 'boat frame'),
    (r'kalkan|engel|kaçın|تجنب|عائق', 'avoid proximity oa'), (r'güç|power|كهرباء', 'power brd'), (r'yer kontrol|ykİ|gcs|المحطة الأرضية', 'gcs fs_gcs'),
    (r'süre|zaman|timeout|مهلة', 'timeout time'), (r'açı|زاوية', 'angle'), (r'derinlik|عمق', 'depth surface'), (r'dalış|غوص', 'dive depth'),
]
STOP = set('ve ile için bir bu şu o ne nasıl nedir yapar yaparım olur mu mi mı hangi parametre parametreler seçenek seçeneği değer değeri '
           'the a an of to and or for how do i what which is are does with parameter option value set make can should '
           'في من على إلى كيف ما هو هي أي هل معامل خيار قيمة'.split())


def _terms(q):
    ql = q.lower()
    extra = []; groups = []
    for rx, en in SYN:
        if re.search(rx, ql): extra += en.split(); groups.append(en.split())
    words = [w for w in re.findall(r'[\w]+', ql) if len(w) > 1 and w not in STOP]
    return words, extra, groups


def _prefixes(db, vehicle):
    k = ('_pfx', vehicle)
    if k not in db._blob:
        db._blob[k] = {n.split('_')[0] for n in db.names(vehicle)}
    return db._blob[k]


_TOK_ALIAS = {'fs': 'failsafe', 'thr': 'throttle', 'batt': 'battery', 'rtl': 'return', 'alt': 'altitude', 'spd': 'speed',
              'gcs': 'gcs', 'ekf': 'ekf', 'mag': 'compass', 'compass': 'compass', 'gps': 'gps', 'arming': 'arm', 'rc': 'rc'}


def search(q, vehicle, limit=40):
    """Sorguya en uygun parametreler [(ad, skor)]. Kavram grupları (ör. batarya + eve dönüş) birlikte geçerse ödüllendirilir."""
    db = PDB.get(); q = (q or '').strip()
    if not q: return []
    Q = q.upper().replace(' ', '_')
    words, extra, groups = _terms(q)
    pfx = _prefixes(db, vehicle)
    try:
        from . import pcritical as PCR
        crit = {c[1] for c in PCR.CRIT}
    except Exception:
        crit = set()
    out = []
    for k in db.names(vehicle):
        sc = 0.0
        if k == Q: sc += 100
        elif k.startswith(Q) and len(Q) >= 3: sc += 40
        elif Q in k and len(Q) >= 3: sc += 20
        b = db.blob(k, vehicle); kl = k.lower()
        for w in words:
            if w in b: sc += 4 + (8 if w in kl else 0)
        ng = 0
        toks = set(kl.split('_')); toks |= {_TOK_ALIAS[x] for x in toks if x in _TOK_ALIAS}
        for g in groups:
            best = 0
            for w in g:
                if w in toks: best = max(best, 12)
                elif re.search(r'\b' + re.escape(w), b): best = max(best, 5)
            if best: ng += 1; sc += best
        if ng > 1: sc *= 1 + 0.7 * (ng - 1)
        if sc > 0:
            m = db.meta(k, vehicle) or {}
            if m.get('usr') == 'Standard': sc *= 1.25
            if k in crit: sc *= 1.3
            if vehicle != 'Plane' and ('quadplan' in b or ' q failsafe' in b): sc *= 0.3   # QuadPlane'e özgü
            if len(b) > 3000: sc *= 0.6    # uzun seçenek listeleri (RC/BTN fonksiyonları) her kelimeyi içerir
            tok = k.split('_')[0]
            if len(tok) > 3 and (tok[-1].isdigit() or tok[:-1] in pfx) and tok[:-1] in pfx | {tok.rstrip('0123456789')}:
                sc *= 0.45    # BATT2_, BATTA_, SERVO9_ … tekrar örnekleri geri plana
            out.append((k, sc))
    out.sort(key=lambda x: -x[1])
    return out[:limit]


def option_hits(q, meta, lang):
    """Sorudaki kelimelerle eşleşen seçenek/bitler."""
    words, extra, _g = _terms(q); hits = []
    db = PDB.get()
    for f in ('vals', 'bits'):
        for k, lab in (meta.get(f) or {}).items():
            b = (lab + ' ' + db.lbl(lab, lang)).lower()
            if any(w in b for w in words + extra): hits.append((f, k, lab))
    return hits[:6]


def offline_answer(q, vehicle, lang='tr', names=None):
    """Yapay zekâ olmadan: soruya en uygun parametreleri, ilgili seçenekleriyle açıklayan metin (Markdown)."""
    db = PDB.get()
    found = [(n, 0) for n in names] if names else search(q, vehicle, 6)
    if not found:
        return {'tr': 'Bu soruyla eşleşen parametre bulunamadı. Parametre adının bir kısmını (ör. BATT_, RTL_, FS_) ya da başka bir kelime deneyin.',
                'en': 'No matching parameter was found. Try part of a parameter name (e.g. BATT_, RTL_, FS_) or other words.',
                'ar': 'لم يُعثر على معامل مطابق. جرّب جزءاً من اسم المعامل (مثل BATT_ أو RTL_ أو FS_) أو كلمات أخرى.'}[lang]
    H = {'tr': ('Sorunuzla ilgili parametreler ({v}):', 'Bu davranışı sağlayan seçenek', 'Seçenekler', 'Birim', 'Aralık', 'Varsayılan', 'Bitler (toplanarak seçilir)',
                'Değişiklikten sonra kartı yeniden başlatın.', 'Not: çevrimdışı cevap; parametre kütüphanesinden derlendi. Ayrıntı için yapay zekâ anahtarı ekleyebilirsiniz.'),
         'en': ('Parameters related to your question ({v}):', 'Option that gives this behaviour', 'Options', 'Unit', 'Range', 'Default', 'Bits (add values together)',
                'Reboot the board after changing.', 'Note: offline answer compiled from the parameter library. Add an AI key for deeper explanations.'),
         'ar': ('المعاملات المتعلقة بسؤالك ({v}):', 'الخيار الذي يحقق هذا السلوك', 'الخيارات', 'الوحدة', 'النطاق', 'الافتراضي', 'البتات (تُجمع القيم)',
                'أعد تشغيل اللوحة بعد التغيير.', 'ملاحظة: إجابة دون اتصال من مكتبة المعاملات. أضف مفتاح ذكاء اصطناعي لشرح أعمق.')}[lang]
    L = [f'**{H[0].format(v=vname(vehicle, lang))}**', '']
    for k, _ in found:
        m = db.meta(k, vehicle) or {}
        dn, d, _src = db.text(k, vehicle, lang)
        L.append(f'### {k} — {dn}')
        L.append(d)
        info = []
        if m.get('u'): info.append(f"{H[3]}: {m['u']}")
        if m.get('r'): info.append(f"{H[4]}: {fmt(m['r'][0])} … {fmt(m['r'][1])}")
        if m.get('default') is not None: info.append(f"{H[5]}: {fmt(m['default'])}")
        if info: L.append(' · '.join(info))
        hits = option_hits(q, m, lang)
        for f, kk, lab in hits:
            val = kk if f == 'vals' else f'bit {kk} (= {1 << int(kk) if str(kk).isdigit() else kk})'
            L.append(f'- ✅ {H[1]}: **{k} = {val}** → {db.lbl(lab, lang)}')
        if m.get('vals') and not hits:
            L.append(f"- {H[2]}: " + ', '.join(f'{kk} = {db.lbl(v, lang)}' for kk, v in list(m['vals'].items())[:12]))
        if m.get('bits') and not hits:
            L.append(f"- {H[6]}: " + ', '.join(f'{kk}: {db.lbl(v, lang)}' for kk, v in list(m['bits'].items())[:12]))
        if m.get('rb'): L.append(f'- ⚠ {H[7]}')
        L.append('')
    L.append(f'_{H[8]}_')
    return '\n'.join(L)


def ai_context(q, vehicle, lang, current=None, names=None):
    """Yapay zekâya verilecek parametre bağlamı (ilgili parametrelerin resmî tanımları)."""
    db = PDB.get()
    found = names or [k for k, _ in search(q, vehicle, 14)]
    ctx = []
    for k in found[:14]:
        m = db.meta(k, vehicle) or {}
        e = {'name': k, 'display': m.get('dn'), 'description': m.get('d'), 'units': m.get('u'), 'range': m.get('r'),
             'default': m.get('default'), 'values': m.get('vals'), 'bitmask': m.get('bits'), 'reboot_required': bool(m.get('rb'))}
        if current and k in current: e['current_value'] = current[k]
        ctx.append({x: y for x, y in e.items() if y not in (None, '', {}, [])})
    return ctx


def ai_question(settings, usage, q, vehicle, lang, current=None, names=None):
    from . import ai
    from .advisor import LANG_NAME
    ctx = ai_context(q, vehicle, lang, current, names)
    system = ('You are an expert ArduPilot instructor. Answer in {L}. Explain which parameters and which option values achieve the behaviour '
              'the user asks about, with exact parameter names and values, step by step, with safety warnings where relevant. '
              'Use the official metadata provided (vehicle: {V}); if it is not enough, say what else to check. Be concise and practical; use Markdown.'
              ).format(L=LANG_NAME.get(lang, 'Turkish'), V=vehicle)
    prompt = f'Question: {q}\n\nOfficial parameter metadata (JSON):\n' + json.dumps(ctx, ensure_ascii=False)[:24000]
    return ai.chat(settings, usage, system, prompt)


# ------------------------------------------------------------------ işaretler ve arşiv (eşitlenen kayıtlar)
def marks(archive):
    return {r['id']: r for r in archive.rec_list('pmark')}


def set_mark(archive, name, **kw):
    cur = archive.rec_get('pmark', name) or {}
    cur.update(kw)
    if not (cur.get('star') or cur.get('key') or cur.get('note') or cur.get('cat')):
        archive.rec_del('pmark', name); return None
    archive.rec_put('pmark', name, cur); return cur


def psets(archive):
    return sorted(archive.rec_list('pset'), key=lambda r: r.get('date', ''), reverse=True)


def save_pset(archive, params, name, vehicle, note='', aircraft='', source=''):
    import uuid
    rid = uuid.uuid4().hex[:12]
    archive.rec_put('pset', rid, {'name': name, 'vehicle': vehicle, 'note': note, 'aircraft': aircraft, 'source': source,
                                  'date': time.strftime('%Y-%m-%d %H:%M'), 'n': len(params), 'params': params})
    return rid
