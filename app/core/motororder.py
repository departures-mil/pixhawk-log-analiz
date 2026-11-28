"""Motor Yönleri Bankası: ArduPilot çerçevelerinin motor numarası, konumu, dönüş yönü ve test sırası.

Veri `app/data/motororder.json` (tools_data/build_motororder.py ArduPilot'un AP_MotorsMatrix.cpp dosyasından üretir),
resimler `app/data/motororder/<id>.png`. Renkler ArduPilot belgeleriyle aynı: mavi = saat yönünün tersi (CCW),
yeşil = saat yönü (CW). Resimde dilden bağımsız yalnız motor numarası (büyük) ve test harfi (A, B, C…) bulunur.
"""
from __future__ import annotations
import json, math, os

CCW_COL = '#5BC8EC'; CW_COL = '#4CAF50'; NONE_COL = '#B0B8C4'; FRAME_COL = '#5BB8E0'; ARM_COL = '#8A96A8'
_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

CLS_TX = {
    'QUAD': ('Quad (4 motor)', 'Quad (4 motors)', 'رباعي (4 محركات)'),
    'HEXA': ('Hexa (6 motor)', 'Hexa (6 motors)', 'سداسي (6 محركات)'),
    'OCTA': ('Octa (8 motor)', 'Octa (8 motors)', 'ثماني (8 محركات)'),
    'OCTAQUAD': ('X8 / OctaQuad (4 kolda 8 motor, üst-alt)', 'X8 / OctaQuad (8 motors on 4 arms, top-bottom)', 'X8 / OctaQuad (8 محركات على 4 أذرع، علوي-سفلي)'),
    'Y6': ('Y6 (3 kolda 6 motor, üst-alt)', 'Y6 (6 motors on 3 arms, top-bottom)', 'Y6 (6 محركات على 3 أذرع، علوي-سفلي)'),
    'DECA': ('Deca (10 motor)', 'Deca (10 motors)', 'عشاري (10 محركات)'),
    'DODECAHEXA': ('DodecaHexa (6 kolda 12 motor, üst-alt)', 'DodecaHexa (12 motors on 6 arms, top-bottom)', 'DodecaHexa (12 محركاً على 6 أذرع، علوي-سفلي)'),
    'TRI': ('Tri (3 motor + kuyruk servosu)', 'Tri (3 motors + tail servo)', 'ثلاثي (3 محركات + مؤازر ذيل)'),
    'TAILSITTER': ('Tailsitter (sol/sağ motor)', 'Tailsitter (left/right motor)', 'Tailsitter (محرك أيسر/أيمن)'),
}
TYPE_TX = {
    'PLUS': ('+ (artı)', '+ (plus)', '+ (زائد)'), 'X': ('X', 'X', 'X'), 'V': ('V', 'V', 'V'), 'H': ('H', 'H', 'H'),
    'VTAIL': ('V kuyruk', 'V-tail', 'ذيل V'), 'ATAIL': ('A kuyruk', 'A-tail', 'ذيل A'),
    'PLUSREV': ('+ (motor yönleri ters)', '+ (reversed motors)', '+ (اتجاهات معكوسة)'),
    'Y6B': ('Y6B (üstler CW)', 'Y6B (top motors CW)', 'Y6B (العلوية CW)'), 'Y6F': ('Y6F (FireFly Y6)', 'Y6F (FireFly Y6)', 'Y6F (FireFly Y6)'),
    'Y6A (default)': ('Y6A (varsayılan)', 'Y6A (default)', 'Y6A (الافتراضي)'),
    'BF_X': ('X – Betaflight sırası', 'X – Betaflight order', 'X – ترتيب Betaflight'),
    'BF_X_REV': ('X – Betaflight sırası, yönler ters', 'X – Betaflight order, reversed', 'X – ترتيب Betaflight، معكوس'),
    'DJI_X': ('X – DJI sırası', 'X – DJI order', 'X – ترتيب DJI'), 'CW_X': ('X – saat yönü sırası', 'X – clockwise order', 'X – ترتيب باتجاه عقارب الساعة'),
    'I': ('I (yan yatık H)', 'I (sideways H)', 'I (H جانبي)'),
    'NYT_PLUS': ('+ – yaw torku yok (yalnız QuadPlane)', '+ – no yaw torque (QuadPlane only)', '+ – بلا عزم انعراج (QuadPlane فقط)'),
    'NYT_X': ('X – yaw torku yok (yalnız QuadPlane)', 'X – no yaw torque (QuadPlane only)', 'X – بلا عزم انعراج (QuadPlane فقط)'),
    'Y4': ('Y4 (arkada üst-alt)', 'Y4 (coaxial rear)', 'Y4 (خلفي محوري)'),
    'X_COR': ('X8 – aynı yönde dönen (eski sıra)', 'X8 – co-rotating (old order)', 'X8 – دوران بنفس الاتجاه (ترتيب قديم)'),
    'CW_X_COR': ('X8 – aynı yönde dönen, saat yönü sırası', 'X8 – co-rotating, clockwise order', 'X8 – دوران بنفس الاتجاه، ترتيب عقارب الساعة'),
    'DUAL': ('İki motor (sol/sağ)', 'Two motors (left/right)', 'محركان (أيسر/أيمن)'),
    'STD': ('Standart', 'Standard', 'قياسي'),
}
GROUPS = [('qp', ('QuadPlane / VTOL (ArduPlane)', 'QuadPlane / VTOL (ArduPlane)', 'QuadPlane / VTOL (ArduPlane)')),
          ('mc', ('Multikopter (ArduCopter)', 'Multicopter (ArduCopter)', 'متعدد المراوح (ArduCopter)')),
          ('other', ('Uçak ve diğer araçlar', 'Plane and other vehicles', 'الطائرة والمركبات الأخرى'))]
# QuadPlane'de sık kullanılan çerçeveler (Q_FRAME_CLASS / Q_FRAME_TYPE), bu sırayla
QP_PICK = [('QUAD', 'X'), ('QUAD', 'PLUS'), ('QUAD', 'H'), ('QUAD', 'NYT_X'), ('QUAD', 'NYT_PLUS'), ('QUAD', 'V'),
           ('HEXA', 'X'), ('HEXA', 'PLUS'), ('OCTA', 'X'), ('OCTA', 'PLUS'), ('OCTAQUAD', 'X'), ('OCTAQUAD', 'PLUS'),
           ('Y6', 'Y6B'), ('Y6', 'Y6F')]
L3 = {'tr': 0, 'en': 1, 'ar': 2}


def _tx(d, k, lg):
    v = d.get(k)
    return v[L3.get(lg, 0)] if v else k


def _id(prefix, cls, typ):
    return f"{prefix}_{cls}_{typ}".lower().replace(' ', '').replace('(', '').replace(')', '').replace('/', '_')


def build_bank(frames):
    """Ayrıştırılmış matris çerçevelerinden kartlar: QuadPlane seçkisi + bütün multikopterler + tri/tailsitter/diğer."""
    out = []
    by = {(f['cls_name'], f['type_name']): f for f in frames}
    for c, ty in QP_PICK:
        f = by.get((c, ty))
        if not f: continue
        out.append({**f, 'id': _id('qp', c, ty), 'group': 'qp', 'kind': 'matrix', 'body': 'plane', **_note(f),
                    'params': f"Q_ENABLE=1 · Q_FRAME_CLASS={f['cls']} · Q_FRAME_TYPE={f['type']}"})
    out.append(_tri('qp')); out.append(_tailsitter())
    order = ['QUAD', 'HEXA', 'OCTA', 'OCTAQUAD', 'Y6', 'DECA', 'DODECAHEXA']
    for c in order:
        for f in [f for f in frames if f['cls_name'] == c]:
            if f['type_name'] in ('NYT_X', 'NYT_PLUS'): continue      # yalnız ArduPlane derlemesinde var
            out.append({**f, 'id': _id('mc', c, f['type_name']), 'group': 'mc', 'kind': 'matrix', 'body': 'copter', **_note(f),
                        'params': f"FRAME_CLASS={f['cls']} · FRAME_TYPE={f['type']}" if f['type'] >= 0 else f"FRAME_CLASS={f['cls']} · FRAME_TYPE (Y6 dışı değer)"})
        if c == 'QUAD': pass
    out.append(_tri('mc'))
    out += _others()
    return {'source': 'ArduPilot libraries/AP_Motors/AP_MotorsMatrix.cpp (master)', 'frames': out}


def _note(f):
    t = f['type_name']
    if t in ('NYT_X', 'NYT_PLUS'):
        return {'note': ('Yaw torku yok: motorların yaw katsayısı 0, yön kontrolü uçağın yüzeyleri/eğimiyle yapılır; pervane yönleri yazılımda sabit değildir.',
                         'No yaw torque: the motors have zero yaw factor, yaw comes from the aircraft surfaces/tilt; prop directions are not fixed by the firmware.',
                         'بلا عزم انعراج: معامل الانعراج للمحركات صفر، ويأتي الانعراج من أسطح الطائرة/الإمالة؛ اتجاهات المراوح غير محددة في البرنامج.')}
    if t in ('VTAIL', 'ATAIL'):
        return {'note': ('Ön motorlar (gri) yaw üretmez, yalnız roll/pitch; yaw yalnız arka motorlardan gelir. Gri diskin dönüş yönü yazılımda sabit değildir.',
                         'Front motors (grey) produce no yaw, only roll/pitch; yaw comes only from the rear motors. Grey discs have no firmware-defined direction.',
                         'المحركات الأمامية (الرمادية) لا تنتج انعراجاً، فقط دحرجة/ميل؛ الانعراج من الخلفية فقط. لا اتجاه محدداً للأقراص الرمادية.')}
    if any(m.get('level') for m in f['motors']):
        return {'note': ('Aynı koldaki iki motor üst üstedir: düz çizgili disk ÜST, kesik çizgili disk ALT motordur.',
                         'Two motors share each arm: the solid disc is the TOP motor, the dashed disc is the BOTTOM motor.',
                         'محركان على كل ذراع: القرص المتصل هو العلوي، والقرص المتقطع هو السفلي.')}
    return {}


def _tri(group):
    # AP_MotorsTri: motor 1 sağ ön, 2 sol ön, 4 arka; kuyruk servosu MOT7 (SERVOx_FUNCTION=39). Yön yazılımda tanımlı değil.
    mots = [{'n': 1, 'x': 0.87, 'y': 0.5, 'yaw': 0, 'order': 1}, {'n': 2, 'x': -0.87, 'y': 0.5, 'yaw': 0, 'order': 3},
            {'n': 4, 'x': 0.0, 'y': -1.0, 'yaw': 0, 'order': 2}]
    p = 'Q_FRAME_CLASS=7 · Q_TILT_MASK' if group == 'qp' else 'FRAME_CLASS=7 · SERVOx_FUNCTION=39 (Motor7 = kuyruk servosu)'
    return {'id': f'{group}_tri', 'group': group, 'kind': 'tri', 'body': 'plane' if group == 'qp' else 'copter', 'cls': 7, 'cls_name': 'TRI',
            'type': -1, 'type_name': 'STD', 'ap_string': 'TRI', 'motors': mots, 'servo': {'x': 0.0, 'y': -1.0}, 'params': p,
            'note': ('Yaw kuyruk motorunu yatıran servoyla (Motor7) yapılır; dönüş yönleri ArduPilot\'ta sabit değildir, '
                     'çerçeve/pervane üreticisinin şemasına uyun.',
                     'Yaw comes from the servo that tilts the tail motor (Motor7); rotation directions are not fixed by ArduPilot, '
                     'follow the frame/prop maker\'s diagram.',
                     'الانعراج عبر المؤازر الذي يميل المحرك الخلفي (Motor7)؛ اتجاهات الدوران غير محددة في ArduPilot، '
                     'اتبع مخطط مصنع الهيكل/المراوح.')}


def _tailsitter():
    mots = [{'n': 'L', 'x': -0.7, 'y': 0.15, 'yaw': 0, 'order': 2, 'fn': 73}, {'n': 'R', 'x': 0.7, 'y': 0.15, 'yaw': 0, 'order': 1, 'fn': 74}]
    return {'id': 'qp_tailsitter', 'group': 'qp', 'kind': 'tailsitter', 'body': 'wing', 'cls': 10, 'cls_name': 'TAILSITTER', 'type': -1,
            'type_name': 'DUAL', 'ap_string': 'TAILSITTER', 'motors': mots,
            'params': 'Q_ENABLE=1 · Q_FRAME_CLASS=10 · Q_TAILSIT_ENABLE=1 · SERVOx_FUNCTION=73 (ThrottleLeft) / 74 (ThrottleRight)',
            'note': ('Sol motor ThrottleLeft (73), sağ motor ThrottleRight (74). Pervaneler çoğunlukla zıt yönde döner; '
                     'yaw/roll kontrolü elevon ve motor farkıyla yapılır.',
                     'Left motor ThrottleLeft (73), right motor ThrottleRight (74). Props usually counter-rotate; '
                     'yaw/roll control comes from elevons and differential thrust.',
                     'المحرك الأيسر ThrottleLeft (73) والأيمن ThrottleRight (74). المراوح عادة تدور بعكس بعضها؛ '
                     'التحكم بالانعراج/الدحرجة عبر الإيلفونات وفرق الدفع.')}


def _others():
    return [
        {'id': 'pl_single', 'group': 'other', 'kind': 'plane1', 'body': 'plane', 'cls': -1, 'cls_name': 'PLANE', 'type': -1, 'type_name': 'STD',
         'ap_string': 'Plane', 'motors': [{'n': 'T', 'x': 0.0, 'y': 1.25, 'yaw': 0, 'order': 1, 'fn': 70}],
         'params': 'SERVO3_FUNCTION=70 (Throttle)',
         'title': ('Uçak – tek motor', 'Plane – single motor', 'طائرة – محرك واحد'),
         'note': ('İtki motoru Throttle (70). Dönüş yönü motor/pervaneye göre seçilir; QuadPlane\'de bu motor kaldırma motorlarından ayrıdır.',
                  'The thrust motor is Throttle (70). Direction follows the motor/prop; on a QuadPlane it is separate from the lift motors.',
                  'محرك الدفع Throttle (70). الاتجاه حسب المحرك/المروحة؛ وفي QuadPlane منفصل عن محركات الرفع.')},
        {'id': 'pl_twin', 'group': 'other', 'kind': 'plane2', 'body': 'plane', 'cls': -1, 'cls_name': 'PLANE', 'type': -1, 'type_name': 'DUAL',
         'ap_string': 'Plane', 'motors': [{'n': 'L', 'x': -0.55, 'y': 0.35, 'yaw': 0, 'order': 2, 'fn': 73},
                                          {'n': 'R', 'x': 0.55, 'y': 0.35, 'yaw': 0, 'order': 1, 'fn': 74}],
         'params': 'SERVOx_FUNCTION=73 (ThrottleLeft) / 74 (ThrottleRight) · RUDD_DT_GAIN',
         'title': ('Uçak – çift motor (diferansiyel itki)', 'Plane – twin motor (differential thrust)', 'طائرة – محركان (دفع تفاضلي)'),
         'note': ('Sol ThrottleLeft (73), sağ ThrottleRight (74); RUDD_DT_GAIN ile dümen motor farkına karışır. Pervaneler çoğunlukla zıt yönde döner.',
                  'Left ThrottleLeft (73), right ThrottleRight (74); RUDD_DT_GAIN mixes rudder into the motor difference. Props usually counter-rotate.',
                  'الأيسر ThrottleLeft (73) والأيمن ThrottleRight (74)؛ RUDD_DT_GAIN يمزج الدفة في فرق المحركين. المراوح عادة متعاكسة.')},
        {'id': 'rv_skid', 'group': 'other', 'kind': 'rover', 'body': 'rover', 'cls': -1, 'cls_name': 'ROVER', 'type': -1, 'type_name': 'DUAL',
         'ap_string': 'Rover', 'motors': [{'n': 'L', 'x': -0.6, 'y': 0.0, 'yaw': 0, 'order': 2, 'fn': 73},
                                          {'n': 'R', 'x': 0.6, 'y': 0.0, 'yaw': 0, 'order': 1, 'fn': 74}],
         'params': 'SERVO1_FUNCTION=73 (ThrottleLeft) · SERVO3_FUNCTION=74 (ThrottleRight)',
         'title': ('Kara aracı / tekne – paletli (skid steering)', 'Rover / boat – skid steering', 'مركبة أرضية / قارب – توجيه انزلاقي'),
         'note': ('Sol taraf ThrottleLeft (73), sağ taraf ThrottleRight (74). İleri komutta iki taraf da ileri dönmeli; ters dönen tarafı SERVOx_REVERSED ile düzeltin.',
                  'Left side ThrottleLeft (73), right side ThrottleRight (74). Both sides must drive forward on a forward command; fix a reversed side with SERVOx_REVERSED.',
                  'الجانب الأيسر ThrottleLeft (73) والأيمن ThrottleRight (74). يجب أن يدفع الجانبان للأمام عند أمر الأمام؛ صحّح الجانب المعكوس بـ SERVOx_REVERSED.')},
    ]


# ------------------------------------------------------------------ veri
_BANK = None


def bank():
    global _BANK
    if _BANK is None:
        try:
            with open(os.path.join(_DIR, 'motororder.json'), encoding='utf-8') as f: _BANK = json.load(f)
        except Exception:
            _BANK = {'frames': []}
    return _BANK


def image(fid):
    return os.path.join(_DIR, 'motororder', fid + '.png')


def title(fr, lg):
    if fr.get('title'): return fr['title'][L3.get(lg, 0)]
    return f"{_tx(CLS_TX, fr['cls_name'], lg)} · {_tx(TYPE_TX, fr['type_name'], lg)}"


def note(fr, lg):
    n = fr.get('note')
    return n[L3.get(lg, 0)] if n else ''


def letter(order):
    return chr(ord('A') + int(order) - 1) if isinstance(order, int) and order > 0 else ''


def rows(fr, lg):
    """Tablo satırları: (çıkış/motor, konum, yön, test harfi, SERVOx_FUNCTION)."""
    D = {'tr': ('Saat yönünün tersi (CCW)', 'Saat yönü (CW)', '—'), 'en': ('Counter-clockwise (CCW)', 'Clockwise (CW)', '—'),
         'ar': ('عكس عقارب الساعة (CCW)', 'مع عقارب الساعة (CW)', '—')}[lg if lg in L3 else 'tr']
    out = []
    for m in sorted(fr['motors'], key=lambda z: (isinstance(z['n'], str), z['n'] if isinstance(z['n'], int) else 0, str(z['n']))):
        d = D[0] if m['yaw'] > 0 else D[1] if m['yaw'] < 0 else D[2]
        fn = m.get('fn') or (32 + m['n'] if isinstance(m['n'], int) else '')
        nm = f"Motor {m['n']}" if isinstance(m['n'], int) else {'L': 'Sol / Left / أيسر', 'R': 'Sağ / Right / أيمن', 'T': 'Throttle'}.get(m['n'], m['n'])
        out.append((nm, pos_text(m, lg), d, letter(m.get('order')), str(fn)))
    return out


def pos_text(m, lg):
    x, y = m['x'], m['y']
    W = {'tr': ('ön', 'arka', 'sağ', 'sol', 'merkez', 'üst', 'alt'), 'en': ('front', 'rear', 'right', 'left', 'centre', 'top', 'bottom'),
         'ar': ('أمامي', 'خلفي', 'أيمن', 'أيسر', 'مركز', 'علوي', 'سفلي')}[lg if lg in L3 else 'tr']
    parts = []
    if y > 0.2: parts.append(W[0])
    elif y < -0.2: parts.append(W[1])
    if x > 0.2: parts.append(W[2])
    elif x < -0.2: parts.append(W[3])
    s = ' '.join(parts) or W[4]
    if m.get('level') == 'top': s += f' ({W[5]})'
    if m.get('level') == 'bottom': s += f' ({W[6]})'
    a = (math.degrees(math.atan2(x, y)) + 360) % 360
    return f'{s} · {a:.0f}°' if parts else s


def find_for_params(P, vehicle='Plane'):
    """Logdaki parametrelerden bu aracın kartı (QuadPlane: Q_FRAME_*, kopter: FRAME_*)."""
    B = bank()['frames']
    if vehicle == 'Plane' and P.get('Q_ENABLE', 0) >= 1:
        c, t = int(P.get('Q_FRAME_CLASS', 1)), int(P.get('Q_FRAME_TYPE', 1))
        if c == 10 or P.get('Q_TAILSIT_ENABLE', 0) >= 1: return next((f for f in B if f['id'] == 'qp_tailsitter'), None)
        if c == 7: return next((f for f in B if f['id'] == 'qp_tri'), None)
        return next((f for f in B if f['group'] == 'qp' and f['cls'] == c and f['type'] == t), None) or \
            next((f for f in B if f['group'] == 'mc' and f['cls'] == c and f['type'] == t), None)
    if vehicle == 'Copter' and 'FRAME_CLASS' in P:
        c, t = int(P.get('FRAME_CLASS', 1)), int(P.get('FRAME_TYPE', 1))
        if c == 7: return next((f for f in B if f['id'] == 'mc_tri'), None)
        return next((f for f in B if f['group'] == 'mc' and f['cls'] == c and f['type'] == t), None) or \
            (next((f for f in B if f['group'] == 'mc' and f['cls'] == 5 and f['type'] == -1), None) if c == 5 else None)
    if vehicle == 'Plane':
        return next((f for f in B if f['id'] == ('pl_twin' if any(P.get(f'SERVO{i}_FUNCTION') == 73 for i in range(1, 17)) else 'pl_single')), None)
    if vehicle == 'Rover':
        return next((f for f in B if f['id'] == 'rv_skid'), None)
    return None


# ------------------------------------------------------------------ çizim
def render(fr, path=None, size=4.2, dpi=110):
    """Örnekteki gibi üstten görünüm: gövde, kollar, renkli diskler, dönüş oku, numara ve test harfi. Dilden bağımsız."""
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle, FancyArrowPatch, Polygon, FancyBboxPatch, Rectangle, Arc
    fig = Figure(figsize=(size, size), dpi=dpi); fig.patch.set_facecolor('white')
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_aspect('equal'); ax.axis('off')
    ax.set_xlim(-1.75, 1.75); ax.set_ylim(-1.75, 1.75)
    mots = fr['motors']
    n = len(mots)
    R = 0.36 if n <= 4 else 0.30 if n <= 6 else 0.24 if n <= 8 else 0.20
    sc = 1.05 if fr['body'] != 'copter' else 1.1
    for m in mots:
        m['_x'], m['_y'] = m['x'] * sc, m['y'] * sc
    # koaksiyel: üst/alt diskleri hafifçe kaydır
    for m in mots:
        if m.get('level') == 'top': m['_x'] -= R * 0.30; m['_y'] += R * 0.30
        if m.get('level') == 'bottom': m['_x'] += R * 0.30; m['_y'] -= R * 0.30
    body = fr['body']
    z = 1
    if body == 'plane':
        ax.add_patch(FancyBboxPatch((-0.12, -1.45), 0.24, 2.9, boxstyle='round,pad=0,rounding_size=0.12', fc=FRAME_COL, ec='#2B6F8E', lw=1.2, zorder=z + 1))
        ax.add_patch(Polygon([(-1.6, 0.25), (1.6, 0.25), (1.5, -0.05), (-1.5, -0.05)], closed=True, fc=FRAME_COL, ec='#2B6F8E', lw=1.2, zorder=z + 1))
        ax.add_patch(Polygon([(-0.55, -1.25), (0.55, -1.25), (0.5, -1.42), (-0.5, -1.42)], closed=True, fc=FRAME_COL, ec='#2B6F8E', lw=1.0, zorder=z + 1))
        ax.add_patch(Rectangle((-1.45, 0.05), 0.35, 0.12, fc='#16A34A', ec='none', zorder=z + 2))
        ax.add_patch(Rectangle((1.10, 0.05), 0.35, 0.12, fc='#16A34A', ec='none', zorder=z + 2))
        ax.add_patch(Rectangle((-0.3, -1.40), 0.6, 0.08, fc='#16A34A', ec='none', zorder=z + 2))
        if fr['kind'] == 'matrix':
            # kaldırma motorları kanattan uzanan kirişlerde (boom): her yan için x ortalamasında dikey kiriş
            for side in (-1, 1):
                xs = [m['_x'] for m in mots if m['x'] * side > 0.2]
                if xs:
                    bx = sum(xs) / len(xs)
                    ys = [m['_y'] for m in mots if m['x'] * side > 0.2]
                    ax.plot([bx, bx], [min(ys + [0.1]), max(ys + [0.1])], color=ARM_COL, lw=5, solid_capstyle='round', zorder=z)
            for m in mots:
                if abs(m['x']) <= 0.2:
                    ax.plot([0, m['_x']], [0.1 if m['_y'] > 0 else -0.2, m['_y']], color=ARM_COL, lw=5, solid_capstyle='round', zorder=z)
                else:
                    bx = sum(mm['_x'] for mm in mots if mm['x'] * m['x'] > 0.04) / max(1, sum(1 for mm in mots if mm['x'] * m['x'] > 0.04))
                    if abs(bx - m['_x']) > 0.05: ax.plot([bx, m['_x']], [m['_y'], m['_y']], color=ARM_COL, lw=4, zorder=z)
        elif fr['kind'] == 'tri':
            for m in mots: ax.plot([0, m['_x']], [0.1, m['_y']], color=ARM_COL, lw=5, solid_capstyle='round', zorder=z)
    elif body == 'wing':
        ax.add_patch(Polygon([(-1.6, 0.35), (1.6, 0.35), (1.35, -0.35), (-1.35, -0.35)], closed=True, fc=FRAME_COL, ec='#2B6F8E', lw=1.2, zorder=z + 1))
        ax.add_patch(Rectangle((-1.3, -0.35), 0.9, 0.12, fc='#16A34A', ec='none', zorder=z + 2))
        ax.add_patch(Rectangle((0.4, -0.35), 0.9, 0.12, fc='#16A34A', ec='none', zorder=z + 2))
        ax.plot([-0.25, 0.25], [-0.35, -0.35], color='#2B6F8E', lw=1)
    elif body == 'rover':
        ax.add_patch(FancyBboxPatch((-0.55, -1.0), 1.1, 2.0, boxstyle='round,pad=0,rounding_size=0.15', fc=FRAME_COL, ec='#2B6F8E', lw=1.2, zorder=z + 1))
        for sx in (-0.75, 0.75):
            ax.add_patch(FancyBboxPatch((sx - 0.15, -1.05), 0.3, 2.1, boxstyle='round,pad=0,rounding_size=0.12', fc='#475569', ec='#1E293B', lw=1, zorder=z + 1))
    else:  # copter
        for m in mots:
            ax.plot([0, m['x'] * sc], [0, m['y'] * sc], color=ARM_COL, lw=6, solid_capstyle='round', zorder=z)
        ax.add_patch(FancyBboxPatch((-0.26, -0.3), 0.52, 0.6, boxstyle='round,pad=0,rounding_size=0.1', fc=FRAME_COL, ec='#2B6F8E', lw=1.2, zorder=z + 2))
    # ön oku
    ax.add_patch(FancyArrowPatch((0, 1.46), (0, 1.72), arrowstyle='-|>', mutation_scale=18, color='#DC2626', lw=2.2, zorder=9))
    if fr['kind'] == 'tri' and fr.get('servo'):
        sx, sy = fr['servo']['x'] * sc, fr['servo']['y'] * sc
        ax.add_patch(Rectangle((sx - 0.12, sy + R + 0.02), 0.24, 0.14, fc='#F59E0B', ec='#92400E', lw=1, zorder=8))
        ax.text(sx + 0.17, sy + R + 0.09, '7', fontsize=9, fontweight='bold', color='#92400E', va='center', zorder=9)
    # diskler: alt motorlar önce (üst motor üstte görünsün)
    for m in sorted(mots, key=lambda z: 0 if m_level(z) == 'bottom' else 1):
        x, y = m['_x'], m['_y']
        col = CCW_COL if m['yaw'] > 0 else CW_COL if m['yaw'] < 0 else NONE_COL
        bottom = m.get('level') == 'bottom'
        ax.add_patch(Circle((x, y), R, fc=col, ec='#1F2937' if not bottom else '#334155', lw=1.0, ls='-' if not bottom else (0, (3, 2)),
                            alpha=1.0 if not bottom else 0.92, zorder=4 if bottom else 6))
        if m['yaw'] != 0:
            # dönüş oku: diskin içinde 250°'lik yay + yay ucunda belirgin ok başı (CCW: saat tersine, CW: saat yönüne)
            rr = R * 0.80; zz = 7 if not bottom else 5
            if m['yaw'] > 0: t1, t2, end = -125, 125, 125          # CCW: yay -125°→125°, uç 125°'de
            else: t1, t2, end = 55, 305, 55                         # CW: yay 305°→55° saat yönünde, uç 55°'de
            ax.add_patch(Arc((x, y), 2 * rr, 2 * rr, theta1=t1, theta2=t2, color='white', lw=2.2 if R >= 0.24 else 1.6, zorder=zz))
            e = math.radians(end); px, py = x + rr * math.cos(e), y + rr * math.sin(e)
            tx, ty = (-math.sin(e), math.cos(e)) if m['yaw'] > 0 else (math.sin(e), -math.cos(e))   # hareket yönü
            nx, ny = math.cos(e), math.sin(e); h = R * 0.42; w = R * 0.24
            ax.add_patch(Polygon([(px + tx * h * 0.6, py + ty * h * 0.6), (px - tx * h * 0.4 + nx * w, py - ty * h * 0.4 + ny * w),
                                  (px - tx * h * 0.4 - nx * w, py - ty * h * 0.4 - ny * w)], closed=True, fc='white', ec='none', zorder=zz))
        lt = letter(m.get('order'))
        if bottom:
            # alt motor üst diskin altında kalır: numarası ve test harfi sağ alttaki rozette
            bx, by = x + R * 0.62, y - R * 0.62
            ax.add_patch(Circle((bx, by), R * 0.42, fc=col, ec='#0F172A', lw=1.2, zorder=10))
            ax.text(bx, by + R * 0.07, str(m['n']), ha='center', va='center', fontsize=10 if R >= 0.24 else 8, fontweight='bold', color='white', zorder=11)
            if lt: ax.text(bx, by - R * 0.24, lt, ha='center', va='center', fontsize=6, color='#0F172A', fontweight='bold', zorder=11)
            continue
        ax.text(x, y + R * 0.12, str(m['n']), ha='center', va='center', fontsize=17 if R >= 0.3 else 13 if R >= 0.24 else 11,
                fontweight='bold', color='white', zorder=9)
        if lt:
            ax.text(x, y - R * 0.52, lt, ha='center', va='center', fontsize=8 if R >= 0.24 else 7, color='#0F172A', fontweight='bold', zorder=9)
    if path:
        fig.savefig(path, dpi=dpi, facecolor='white')
    return fig


def m_level(m):
    return m.get('level') or ''
