"""Motor Yönleri Bankası verisi: ArduPilot'un kendi motor tanımlarından (libraries/AP_Motors/AP_MotorsMatrix.cpp) üretilir.

Kullanım: python tools_data/build_motororder.py [AP_MotorsMatrix.cpp]
  (dosya verilmezse ArduPilot master'dan indirilir) → app/data/motororder.json + app/data/motororder/*.png

Her motor: n (MOTn çıkışı = SERVOx_FUNCTION 33+n-1), sağ/ön konum, yön (+1 CCW, -1 CW, 0 yaw torku yok), test sırası (A, B, C…),
aynı konumda iki motor varsa üst/alt (ilk tanımlanan üstte; ArduPilot yorumlarıyla uyumlu: dodecahexa 'forward-top').
"""
from __future__ import annotations
import json, math, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_URL = 'https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_Motors/AP_MotorsMatrix.cpp'
CLASS = {'quad': (1, 'QUAD'), 'hexa': (2, 'HEXA'), 'octa': (3, 'OCTA'), 'octaquad': (4, 'OCTAQUAD'), 'y6': (5, 'Y6'),
         'dodecahexa': (12, 'DODECAHEXA'), 'deca': (14, 'DECA')}
TYPE = {'PLUS': 0, 'X': 1, 'V': 2, 'H': 3, 'VTAIL': 4, 'ATAIL': 5, 'PLUSREV': 6, 'Y6B': 10, 'Y6F': 11, 'BF_X': 12, 'DJI_X': 13,
        'CW_X': 14, 'I': 15, 'NYT_PLUS': 16, 'NYT_X': 17, 'BF_X_REV': 18, 'Y4': 19, 'X_COR': 20, 'CW_X_COR': 21}
YAW = {'AP_MOTORS_MATRIX_YAW_FACTOR_CW': -1, 'AP_MOTORS_MATRIX_YAW_FACTOR_CCW': 1, '0': 0}
NUM = r'(-?\d+(?:\.\d+)?)f?'


def parse(src):
    frames = []
    for m in re.finditer(r'bool AP_MotorsMatrix::setup_(\w+)_matrix\(motor_frame_type frame_type\)\s*\{(.*?)\n\}', src, re.S):
        cls = m.group(1); body = m.group(2)
        if cls not in CLASS: continue
        # 'case X:' ve 'default:' etiketlerine böl
        parts = re.split(r'\n\s*(case MOTOR_FRAME_TYPE_\w+:|default:)', body)
        labels = []
        for p in parts[1:]:
            if p.startswith('case ') or p == 'default:':
                labels.append(p[len('case MOTOR_FRAME_TYPE_'):-1] if p.startswith('case ') else 'default'); continue
            mots = []
            raw = 'MotorDefRaw' in p
            for e in re.finditer(r'\{\s*' + NUM + r'\s*,\s*' + (NUM + r'\s*,\s*' if raw else '') + r'([A-Z_]+|0)\s*,\s*(\d+)\s*\}', p):
                g = e.groups()
                if raw: r, pf, y, o = float(g[0]), float(g[1]), g[2], int(g[3]); x, f = -r, pf
                else:
                    a = math.radians(float(g[0])); y, o = g[1], int(g[2]); x, f = math.sin(a), math.cos(a)
                mots.append({'x': x, 'y': f, 'yaw': YAW.get(y, 0), 'order': o})
            for e in re.finditer(r'add_motor\(AP_MOTORS_MOT_(\d+),\s*' + NUM + r',\s*' + NUM + r',\s*([A-Z_]+|0),\s*(\d+)\)', p):
                n, rd, pd, y, o = e.groups()
                x = -math.cos(math.radians(float(rd) + 90)); f = math.cos(math.radians(float(pd)))
                mots.append({'n': int(n), 'x': x, 'y': f, 'yaw': YAW.get(y, 0), 'order': int(o)})
            if not mots:
                continue
            ts = re.search(r'_frame_type_string = "([^"]+)"', p)
            for i, mo in enumerate(mots):
                mo.setdefault('n', i + 1)
            if labels and labels[0] in ('VTAIL', 'ATAIL'):
                # arka motorların roll katsayısı 0 (yalnız yaw verirler); konumları V/A kuyruğun iki kolu:
                # test sırası saat yönünde (ön sağ → arka sağ → arka sol → ön sol): M4 arka sağ, M2 arka sol
                for mo in mots:
                    if mo['n'] == 2: mo['x'], mo['y'] = -0.45, -0.94
                    if mo['n'] == 4: mo['x'], mo['y'] = 0.45, -0.94
            # aynı konumda iki motor: ilk tanımlanan üstte
            seen = {}
            for mo in sorted(mots, key=lambda z: mots.index(z)):
                k = (round(mo['x'], 3), round(mo['y'], 3))
                if k in seen: mo['level'] = 'bottom'; seen[k]['level'] = 'top'
                else: seen[k] = mo
            for lab in labels:
                if lab == 'default' and cls != 'y6': continue
                cid, cname = CLASS[cls]
                frames.append({'cls': cid, 'cls_name': cname, 'type': TYPE.get(lab, -1) if lab != 'default' else -1,
                               'type_name': lab if lab != 'default' else 'Y6A (default)', 'ap_string': ts.group(1) if ts else lab,
                               'motors': [dict(z) for z in mots]})
            labels = []
    return frames


def main():
    p = sys.argv[1] if len(sys.argv) > 1 else None
    if p: src = open(p, encoding='utf-8').read()
    else: src = urllib.request.urlopen(SRC_URL, timeout=60).read().decode('utf-8')
    frames = parse(src)
    sys.path.insert(0, ROOT)
    from app.core import motororder as MO
    data = MO.build_bank(frames)
    out = os.path.join(ROOT, 'app', 'data', 'motororder.json')
    json.dump(data, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    imgdir = os.path.join(ROOT, 'app', 'data', 'motororder'); os.makedirs(imgdir, exist_ok=True)
    for f in os.listdir(imgdir):
        if f.endswith('.png'): os.remove(os.path.join(imgdir, f))
    for fr in data['frames']:
        MO.render(fr, os.path.join(imgdir, fr['id'] + '.png'))
    print(len(frames), 'matrix frames;', len(data['frames']), 'cards ->', out)


if __name__ == '__main__':
    main()
