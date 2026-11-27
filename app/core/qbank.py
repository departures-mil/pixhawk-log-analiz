"""Soru bankası: el yazımı öğretici sorular (qbank_d1..d4) + kütüphanelerden üretilen sorular (log mesajları, alanlar,
kritik parametreler) + kullanıcının eklediği / düzenlediği sorular.

Kullanıcı değişiklikleri arşivde 'qbank' kaydı olarak tutulur (GitHub/LAN eşitlemesiyle taşınır):
- tam soru sözlüğü  → yeni soru ya da hazır sorunun düzenlenmiş hâli (aynı kimlik)
- {'id', 'hidden': True} → hazır sorunun bankadan kaldırılması (geri yüklenebilir)

Soru sözlüğü: {id, topic, level 1-3, src, q{tr,en,ar}, opts[{tr,en,ar}…], ans, exp{tr,en,ar}, wexp[{…}]|None, origin, lib, key}
v1.1.11: type 'mc' (çoktan seçmeli, varsayılan) | 'open' (açık uçlu yorum: model{…} örnek cevap, kw{lg:[grup…]} anahtar kavramlar,
opts boş, ans -1); img = 'visq/…png' (hazır havuz, app/data) ya da 'data:image/…;base64,…' (kullanıcı görseli);
case = {label crash|normal|incident, cause, kind real|synth|open, veh} (görselli vaka sorularında).
"""
from __future__ import annotations
import json, random, time, uuid
from .paths import res

LANGS = ('tr', 'en', 'ar')
TOPICS = {
    'basics': ('Temel kavramlar ve log yapısı', 'Basics and log structure', 'المفاهيم الأساسية وبنية السجل'),
    'modes': ('Uçuş modları', 'Flight modes', 'أوضاع الطيران'),
    'gps': ('GPS ve konum', 'GPS and position', 'GPS والموقع'),
    'ekf': ('EKF (konum/açı kestirimi)', 'EKF (state estimation)', 'EKF (تقدير الحالة)'),
    'compass': ('Pusula', 'Compass', 'البوصلة'),
    'vibration': ('Titreşim ve IMU', 'Vibration and IMU', 'الاهتزاز وIMU'),
    'power': ('Güç ve batarya', 'Power and battery', 'الطاقة والبطارية'),
    'rc': ('Kumanda (RC)', 'Radio control (RC)', 'جهاز التحكم (RC)'),
    'motors': ('Servo ve motor çıkışları', 'Servo and motor outputs', 'مخرجات السيرفو والمحركات'),
    'control': ('Kontrol ve ayar (PID)', 'Control and tuning (PID)', 'التحكم والضبط (PID)'),
    'plane': ('Sabit kanat (Plane)', 'Fixed wing (Plane)', 'الجناح الثابت (Plane)'),
    'copter': ('Multikopter (Copter)', 'Multicopter (Copter)', 'المروحية متعددة المحركات (Copter)'),
    'vtol': ('VTOL (QuadPlane)', 'VTOL (QuadPlane)', 'VTOL (QuadPlane)'),
    'failsafe': ('Failsafe ve güvenlik', 'Failsafe and safety', 'الأمان والسلامة'),
    'method': ('Kırım analizi yöntemi', 'Crash analysis method', 'منهجية تحليل الحوادث'),
    'mp': ('Mission Planner', 'Mission Planner', 'Mission Planner'),
    'charts': ('Grafik yorumlama (görselli)', 'Chart interpretation (with images)', 'تفسير الرسوم البيانية (مع صور)'),
    'library': ('Log mesajları ve alanlar', 'Log messages and fields', 'رسائل السجل وحقولها'),
    'params': ('Kritik parametreler', 'Critical parameters', 'المعاملات الحرجة'),
    'experts': ('Uzman tecrübeleri (gerçek kırımlar)', 'Expert experience (real crashes)', 'خبرة الخبراء (حوادث حقيقية)'),
}
LEVELS = {1: ('Temel', 'Basic', 'أساسي'), 2: ('Orta', 'Intermediate', 'متوسط'), 3: ('İleri', 'Advanced', 'متقدم')}
ORIGINS = {'builtin': ('Hazır (öğretici)', 'Built-in (tutorial)', 'جاهز (تعليمي)'), 'auto': ('Kütüphaneden', 'From library', 'من المكتبة'),
           'user': ('Benim sorum', 'My question', 'سؤالي')}

_AQ = {  # kütüphane soruları kalıpları
    'msg': ('"{d}" bilgisi hangi log mesajında bulunur?', 'Which log message contains: "{d}"?', 'أي رسالة سجل تحتوي على: "{d}"؟'),
    'fld': ('{m} mesajında hangi alan şunu tutar: "{d}"?', 'Which field of the {m} message holds: "{d}"?', 'أي حقل في رسالة {m} يحمل: "{d}"؟'),
    'par': ('Şu açıklama hangi parametreye aittir: "{d}"', 'Which parameter matches this description: "{d}"', 'أي معامل يطابق هذا الوصف: "{d}"'),
    'holds': ('{x} şunu tutar: {d}', '{x} holds: {d}', '{x} يحمل: {d}'),
}
_MSG_TOPIC = {'GPS': 'gps', 'GPA': 'gps', 'POS': 'gps', 'ORGN': 'ekf', 'MAG': 'compass', 'VIBE': 'vibration', 'IMU': 'vibration',
              'BAT': 'power', 'POWR': 'power', 'RCIN': 'rc', 'RCI2': 'rc', 'RSSI': 'rc', 'RCOU': 'motors', 'RCO2': 'motors', 'RPM': 'motors',
              'ATT': 'control', 'AHR2': 'control', 'ARSP': 'plane', 'TECS': 'plane', 'TEC2': 'plane', 'AETR': 'plane', 'AOA': 'plane',
              'NTUN': 'plane', 'CTUN': 'plane', 'MODE': 'modes', 'BARO': 'copter', 'PM': 'basics'}
_CRIT_TOPIC = {'safety': 'failsafe', 'rtl': 'failsafe', 'arming': 'failsafe', 'battery': 'power', 'rc': 'rc', 'nav': 'gps',
               'tuning': 'control', 'limits': 'control', 'log': 'basics'}
_SKIP_FIELDS = {'TimeUS', 'Instance', 'Id', 'Inst'}


def tri(x):
    """str ya da (tr,en,ar) → {'tr','en','ar'}"""
    if isinstance(x, dict): return {k: x.get(k, '') or '' for k in LANGS}
    if isinstance(x, (tuple, list)): return {k: (x[i] if i < len(x) else '') or '' for i, k in enumerate(LANGS)}
    return {k: str(x) for k in LANGS}


def tx(d, lg):
    """Çok dilli metinden istenen dil (yoksa İngilizce, o da yoksa Türkçe)."""
    if not d: return ''
    if isinstance(d, str): return d
    return d.get(lg) or d.get('en') or d.get('tr') or d.get('ar') or ''


def topic_name(k, lg):
    return tx(tri(TOPICS.get(k, (k, k, k))), lg)


def level_name(n, lg):
    return tx(tri(LEVELS.get(int(n or 1), LEVELS[1])), lg)


# ------------------------------------------------------------------ hazır sorular
_CACHE = {}


def _handwritten():
    from . import qbank_d1, qbank_d2, qbank_d3, qbank_d4
    out = []
    for qid, top, lvl, src, q, opts, exp in qbank_d1.Q + qbank_d2.Q + qbank_d3.Q + qbank_d4.Q:
        out.append({'id': qid, 'topic': top, 'level': lvl, 'src': src, 'q': tri(q), 'opts': [tri(o) for o in opts], 'ans': 0,
                    'exp': tri(exp), 'wexp': None, 'origin': 'builtin'})
    return out


def _auto():
    """Kütüphanelerden üretilen sorular (kararlı kimlik ve şıklar: aynı soru her açılışta aynıdır)."""
    from . import glossary as GL
    out = []
    try:
        M = json.load(open(res('data', 'logmsgs.json'), encoding='utf-8'))
    except Exception:
        M = {}
    core = sorted(k for k, v in M.items() if v.get('core') and (v.get('desc') or {}).get('en'))
    dsc = {k: {lg: GL.lt(M[k]['desc'], lg) for lg in LANGS} for k in core}
    for k in core:
        r = random.Random('msg' + k)
        others = r.sample([x for x in core if x != k], 3)
        opts = [k] + others
        d = dsc[k]
        out.append({'id': 'L-msg-' + k, 'topic': _MSG_TOPIC.get(k, 'library' if not k.startswith(('XK', 'NK')) else 'ekf'), 'level': 1,
                    'src': k, 'origin': 'auto', 'lib': 'msgs', 'key': k,
                    'q': {lg: _AQ['msg'][i].format(d=_cut(d[lg], 170)) for i, lg in enumerate(LANGS)},
                    'opts': [tri(o) for o in opts], 'ans': 0,
                    'exp': {lg: f'{k}: {d[lg]}' for lg in LANGS},
                    'wexp': [None] + [{lg: _AQ['holds'][i].format(x=o, d=_cut(dsc[o][lg], 200)) for i, lg in enumerate(LANGS)} for o in others]})
        flds = [(f, x) for f, x in (M[k].get('fields') or {}).items() if f not in _SKIP_FIELDS and len(f) >= 2 and (x or {}).get('en') and len(x.get('en', '')) > 12]
        if len(flds) < 4: continue
        names = [f for f, _ in flds]
        fd = {f: {lg: GL.lt(x, lg) for lg in LANGS} for f, x in flds}
        lim = 4 if k.startswith(('XK', 'NK')) else 8
        for f, _ in [(f, x) for f, x in flds if not (len(f) > 2 and f.lower() in fd[f]['en'].lower())][:lim]:
            r = random.Random('fld' + k + f)
            oth = r.sample([x for x in names if x != f], 3)
            out.append({'id': f'L-fld-{k}-{f}', 'topic': _MSG_TOPIC.get(k, 'library' if not k.startswith(('XK', 'NK')) else 'ekf'), 'level': 2,
                        'src': f'{k}.{f}', 'origin': 'auto', 'lib': 'msgs', 'key': k,
                        'q': {lg: _AQ['fld'][i].format(m=k, d=_cut(fd[f][lg], 170)) for i, lg in enumerate(LANGS)},
                        'opts': [tri(f)] + [tri(o) for o in oth], 'ans': 0,
                        'exp': {lg: f'{k}.{f}: {fd[f][lg]}' + (f' — {dsc[k][lg][:160]}' if dsc[k][lg] else '') for lg in LANGS},
                        'wexp': [None] + [{lg: _AQ['holds'][i].format(x=f'{k}.{o}', d=_cut(fd[o][lg], 200)) for i, lg in enumerate(LANGS)} for o in oth]})
    try:
        from . import pcritical as PC
        crit = list(PC.CRIT)
    except Exception:
        crit = []
    bycat = {}
    for c in crit: bycat.setdefault(c[0], []).append(c)
    allp = [c[1] for c in crit]
    for cat, p, _veh, d in crit:
        r = random.Random('par' + p)
        same = [c[1] for c in bycat[cat] if c[1] != p]
        pool = same if len(same) >= 3 else same + [x for x in allp if x != p and x not in same]
        oth = r.sample(pool, 3)
        dd = tri(d); dmap = {c[1]: tri(c[3]) for c in crit}
        out.append({'id': 'L-par-' + p, 'topic': _CRIT_TOPIC.get(cat, 'params'), 'level': 2, 'src': p, 'origin': 'auto', 'lib': 'params', 'key': p,
                    'q': {lg: _AQ['par'][i].format(d=_cut(dd[lg], 220)) for i, lg in enumerate(LANGS)},
                    'opts': [tri(p)] + [tri(o) for o in oth], 'ans': 0,
                    'exp': {lg: f'{p}: {dd[lg]}' for lg in LANGS},
                    'wexp': [None] + [{lg: _AQ['holds'][i].format(x=o, d=_cut(dmap[o][lg], 200)) for i, lg in enumerate(LANGS)} for o in oth]})
    return out


def _cut(s, n):
    s = (s or '').strip()
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'


def _visual():
    """Hazır görselli grafik soruları (gerçek kırım / normal uçuşlar ve eğitim senaryoları; tools_data/build_visq.py)."""
    try:
        d = json.load(open(res('data', 'visq.json'), encoding='utf-8'))
    except Exception:
        return []
    out = []
    for q in d.get('questions', []):
        q = dict(q); q['origin'] = 'builtin'
        q['q'] = tri(q['q']); q['exp'] = tri(q.get('exp') or ''); q['opts'] = [tri(o) for o in q.get('opts') or []]
        if q.get('model'): q['model'] = tri(q['model'])
        out.append(q)
    return out


_EQ = {
    'look': ('{t}: uzmanlara göre logda önce nereye bakılır?', '{t}: according to the experts, where do you look in the log first?',
             '{t}: حسب الخبراء، أين تنظر في السجل أولاً؟'),
    'fix': ('{t}: uzmanlara göre ne yapılmalı?', '{t}: according to the experts, what should be done?', '{t}: حسب الخبراء، ماذا يجب أن تفعل؟'),
    'rule': ('Gerçek kırım konularında uzmanların verdiği şu öğüt hangi konuya aittir? "{d}"',
             'Which topic does this advice from experts in real crash threads belong to? "{d}"',
             'إلى أي موضوع تنتمي هذه النصيحة من الخبراء في مواضيع الحوادث الحقيقية؟ "{d}"'),
}


def _expert():
    """Uzman tecrübelerinden (core/expert.py) üretilen sorular: logda nereye bakılır, ne yapılır, öğüt hangi konuya ait."""
    from . import expert as EX
    keys = sorted(EX.L); out = []
    for k in keys:
        L_ = EX.L[k]
        for kind, lvl in (('look', 2), ('fix', 2), ('rule', 3)):
            r = random.Random('ex' + kind + k)
            oth = r.sample([x for x in keys if x != k and EX.L[x]['cause'] != L_['cause']], 3)
            fld = 'title' if kind == 'rule' else kind
            q = {lg: _EQ[kind][i].format(t=L_['title'][i], d=_cut(L_['fix'][i], 200)) for i, lg in enumerate(LANGS)}
            out.append({'id': f'X-{kind}-{k}', 'topic': 'experts', 'level': lvl, 'src': 'discuss.ardupilot.org', 'origin': 'builtin',
                        'q': q, 'opts': [tri(EX.L[x][fld]) for x in [k] + oth], 'ans': 0,
                        'exp': tri(tuple(f'{L_["title"][i]}: {L_["rule"][i]}' for i in range(3))),
                        'wexp': [None] + [tri(tuple(f'{EX.L[x]["title"][i]}: {_cut(EX.L[x]["rule"][i], 220)}' for i in range(3))) for x in oth]})
    return out


def builtin():
    if 'b' not in _CACHE:
        _CACHE['b'] = _handwritten() + _visual() + _expert() + _auto()
    return _CACHE['b']


def is_open(q):
    return (q or {}).get('type') == 'open'


def img_bytes(ref):
    """Soru görselinin baytları: 'visq/x.png' (program verisi) ya da data URI. Yoksa None."""
    if not ref: return None
    try:
        if ref.startswith('data:'):
            import base64
            return base64.b64decode(ref.split(',', 1)[1])
        with open(res('data', *ref.split('/')), 'rb') as f: return f.read()
    except Exception:
        return None


def img_from_file(path, max_w=1400):
    """Kullanıcının seçtiği resmi küçültüp data URI yapar (eşitlemede taşınabilsin diye boyut sınırlı)."""
    from PIL import Image
    import base64, io
    im = Image.open(path); im = im.convert('RGB')
    if im.width > max_w: im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, format='JPEG', quality=82, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


# ------------------------------------------------------------------ birleşik banka
def _recs(archive):
    try: return {r['id']: r for r in archive.rec_list('qbank') if r.get('id')}
    except Exception: return {}


def load(archive=None, include_hidden=False):
    """Hazır + kullanıcı soruları; düzenlenmiş hazır sorular 'mod'=True, kaldırılanlar (include_hidden ise) 'hidden'=True."""
    R = _recs(archive) if archive is not None else {}
    out = []; seen = set()
    for q in builtin():
        r = R.get(q['id']); seen.add(q['id'])
        if r and r.get('hidden'):
            if include_hidden: out.append(dict(q, hidden=True))
            continue
        if r and r.get('q'):
            x = dict(q); x.update(r); x['origin'] = q['origin']; x['mod'] = True; out.append(x)
        else:
            out.append(q)
    for rid, r in R.items():
        if rid in seen or r.get('hidden') or not r.get('q'): continue
        x = dict(r); x['origin'] = 'user'; out.append(x)
    return out


def new_id():
    return 'U-' + uuid.uuid4().hex[:8].upper()


def validate(q):
    """Hata kodu ya da None: 'q' soru metni yok, 'opts' en az 2 şık, 'ans' doğru şık boş, 'model' açık uçluda örnek cevap yok."""
    if not any((q.get('q') or {}).get(lg, '').strip() for lg in LANGS): return 'q'
    if is_open(q):
        return None if any(tri(q.get('model') or '').get(lg, '').strip() for lg in LANGS) else 'model'
    opts = [o for o in q.get('opts') or [] if any((o or {}).get(lg, '').strip() for lg in LANGS)]
    if len(opts) < 2: return 'opts'
    a = int(q.get('ans', 0))
    if a < 0 or a >= len(q.get('opts') or []) or not any((q['opts'][a] or {}).get(lg, '').strip() for lg in LANGS): return 'ans'
    return None


def clean(q):
    """Boş şıkları atar, doğru şık indeksini korur, eksik dilleri boş bırakır (gösterimde yedek dil kullanılır)."""
    opts = q.get('opts') or []; a = int(q.get('ans', 0)); keep = []; na = 0; wex = q.get('wexp') or []; nw = []
    for i, o in enumerate(opts):
        o = tri(o)
        if not any(o[lg].strip() for lg in LANGS): continue
        if i == a: na = len(keep)
        keep.append(o); nw.append(wex[i] if i < len(wex) else None)
    out = {'id': q.get('id') or new_id(), 'topic': q.get('topic') or 'basics', 'level': int(q.get('level') or 1), 'src': (q.get('src') or '').strip(),
           'q': tri(q.get('q')), 'opts': keep, 'ans': na, 'exp': tri(q.get('exp') or ''), 'wexp': nw if any(nw) else None,
           'edited': time.strftime('%Y-%m-%d %H:%M')}
    for k in ('lib', 'key', 'img', 'case'):
        if q.get(k): out[k] = q[k]
    if is_open(q):
        m = tri(q.get('model') or '')
        out.update({'type': 'open', 'opts': [], 'ans': -1, 'wexp': None, 'model': m,
                    'exp': out['exp'] if any(out['exp'].values()) else m,
                    'kw': {lg: [g.strip() for g in (q.get('kw') or {}).get(lg, []) if g and g.strip()] for lg in LANGS}})
    return out


def save(archive, q):
    q = clean(q)
    err = validate(q)
    if err: raise ValueError(err)
    archive.rec_put('qbank', q['id'], q)
    return q


def delete(archive, qid):
    """Kullanıcı sorusu silinir; hazır soru bankadan kaldırılır (geri yüklenebilir)."""
    if any(q['id'] == qid for q in builtin()):
        archive.rec_put('qbank', qid, {'id': qid, 'hidden': True})
    else:
        archive.rec_del('qbank', qid)


def restore(archive, qid):
    """Hazır soruyu özgün hâline döndürür (düzenleme ya da kaldırma geri alınır)."""
    archive.rec_del('qbank', qid)


def copy_of(q):
    x = {k: v for k, v in q.items() if k not in ('origin', 'mod', 'hidden', 'edited')}
    x['id'] = new_id()
    return x


# ------------------------------------------------------------------ seçme ve sunma
def pick(qs, topics=None, levels=None, n=10, seed=None, ids=None, weights=None):
    """Konu/seviye süzgeciyle n soru; konular arasında dengeli dağıtır. weights: {id: ağırlık} (ör. yanlış yapılanlar)."""
    rnd = random.Random(seed)
    pool = [q for q in qs if (not topics or q.get('topic') in topics) and (not levels or int(q.get('level', 1)) in levels)
            and (ids is None or q['id'] in ids)]
    if not pool: return []
    if weights:
        pool.sort(key=lambda q: -weights.get(q['id'], 0) + rnd.random() * 0.5)
        return pool[:n]
    by = {}
    for q in pool: by.setdefault(q.get('topic'), []).append(q)
    for v in by.values(): rnd.shuffle(v)
    keys = list(by); rnd.shuffle(keys); out = []
    while len(out) < n and any(by.values()):
        for k in keys:
            if by[k] and len(out) < n: out.append(by[k].pop())
    rnd.shuffle(out)
    return out


def to_item(q, lg, rnd=None):
    """Alıştırma/sınav biçimi: {'q','opts','ans','exp','wexp','bank_id','topic','level','src','lib','key'} (şıklar karışık)."""
    rnd = rnd or random.Random()
    if is_open(q):
        item = {'type': 'open', 'q': tx(q['q'], lg), 'opts': [], 'ans': -1, 'exp': tx(q.get('exp') or q.get('model'), lg),
                'model': tx(q.get('model'), lg), 'kw': q.get('kw') or {}, 'wexp': [],
                'bank_id': q['id'], 'topic': q.get('topic'), 'level': int(q.get('level', 1)), 'src': q.get('src', '')}
        if q.get('img'): item['img'] = q['img']
        return item
    idx = list(range(len(q['opts']))); rnd.shuffle(idx)
    opts = [tx(q['opts'][i], lg) for i in idx]
    we = q.get('wexp') or []
    wexp = [tx(we[i], lg) if i < len(we) and we[i] else '' for i in idx]
    item = {'q': tx(q['q'], lg), 'opts': opts, 'ans': idx.index(int(q.get('ans', 0))), 'exp': tx(q.get('exp'), lg), 'wexp': wexp,
            'bank_id': q['id'], 'topic': q.get('topic'), 'level': int(q.get('level', 1)), 'src': q.get('src', '')}
    if q.get('lib') and q.get('key'): item['lib'] = q['lib']; item['key'] = q['key']
    if q.get('img'): item['img'] = q['img']
    return item


def counts(qs):
    c = {}
    for q in qs: c[q.get('topic')] = c.get(q.get('topic'), 0) + 1
    return c


# ------------------------------------------------------------------ dışa / içe aktarma
def export_file(path, qs):
    data = {'type': 'pxbank', 'v': 1, 'created': time.strftime('%Y-%m-%d %H:%M'),
            'questions': [{k: v for k, v in q.items() if k not in ('origin', 'mod', 'hidden')} for q in qs]}
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=1)
    return len(qs)


def import_file(archive, path):
    """.pxbank (ya da soru listesi içeren JSON) içe alır. Hazır soruyla aynı kimlik → düzenleme olarak, diğerleri kullanıcı sorusu.
    Mevcut kullanıcı sorusunun üzerine YAZMAZ (aynı kimlik varsa yeni kimlik verilir). → (eklenen, atlanan)"""
    with open(path, encoding='utf-8') as f: d = json.load(f)
    qs = d.get('questions') if isinstance(d, dict) else d
    if not isinstance(qs, list): raise ValueError('format')
    bids = {q['id'] for q in builtin()}; R = _recs(archive); added = skipped = 0
    for q in qs:
        try:
            q = dict(q)
            if q.get('id') in R and q.get('id') not in bids: q['id'] = new_id()
            save(archive, q); added += 1
        except Exception:
            skipped += 1
    return added, skipped
