"""ArduPilot kaynak kodundan parametre varsayılanlarını çıkarır (kod ÇALIŞTIRILMAZ, yalnızca metin okunur).

// @Param: NAME + // @DisplayName: ... yorum bloğundan sonra gelen AP_GROUPINFO / GSCALAR / ASCALAR
makrosunun varsayılan argümanı okunur, basit #define sabitleri çözülür. Eşleştirme görünen ad + kısa adla yapılır.
Çözülemeyen (koşullu, kart başına değişen) varsayılanlar boş bırakılır.
"""
from __future__ import annotations
import ast, operator, os, re

VDIR = {'Plane': 'ArduPlane', 'Copter': 'ArduCopter', 'Heli': 'ArduCopter', 'Rover': 'Rover', 'Sub': 'ArduSub',
        'Blimp': 'Blimp', 'Tracker': 'AntennaTracker', 'Periph': os.path.join('Tools', 'AP_Periph')}
RE_PARAM = re.compile(r'//\s*@Param(?:\{[^}]*\})?\s*:\s*([A-Za-z0-9_]+)')
RE_DN = re.compile(r'//\s*@DisplayName(?:\{[^}]*\})?\s*:\s*(.+)')
RE_DEF = re.compile(r'^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*(?://.*)?$')
RE_CONST = re.compile(r'^\s*(?:static\s+)?(?:inline\s+)?(?:const|constexpr)\s+(?:[A-Za-z_0-9:<>]+\s+)+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);')
RE_ENUM = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^,/]+?)\s*,?\s*(?://.*)?$')
MACROS = ('AP_GROUPINFO_FLAGS_FRAME', 'AP_GROUPINFO_FLAGS_DEFAULT_POINTER', 'AP_GROUPINFO_FLAGS', 'AP_GROUPINFO_FRAME', 'AP_GROUPINFO',
          'GSCALAR', 'ASCALAR', 'GGLOBAL')


def _args(s, i):
    """s[i] == '(' ; üst düzey virgüllere göre argümanlar ve bitiş indeksi."""
    depth = 0; cur = ''; out = []; j = i
    while j < len(s):
        c = s[j]
        if c in '([{':
            depth += 1
            if depth > 1: cur += c
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                out.append(cur.strip()); return out, j
            cur += c
        elif c == ',' and depth == 1:
            out.append(cur.strip()); cur = ''
        elif c == '"':
            k = s.index('"', j + 1); cur += s[j:k + 1]; j = k
        else:
            if depth >= 1: cur += c
        j += 1
    return out, j


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.LShift: operator.lshift,
        ast.RShift: operator.rshift, ast.BitOr: operator.or_, ast.BitAnd: operator.and_, ast.USub: operator.neg, ast.UAdd: operator.pos,
        ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.Invert: operator.invert}


def _ev(n):
    if isinstance(n, ast.Expression): return _ev(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool): return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS: return _OPS[type(n.op)](_ev(n.left), _ev(n.right))
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS: return _OPS[type(n.op)](_ev(n.operand))
    raise ValueError('expr')


def evaluate(expr, defs, depth=0):
    e = expr.strip()
    if depth > 8 or not e: return None
    e = re.sub(r'static_cast<[^>]*>', '', e)
    e = re.sub(r'\((?:u?int(?:8|16|32|64)_t|float|double|int|unsigned|uint)\)', '', e)
    e = re.sub(r'(?<=\d)(?:\.?)[fF]\b', '', e)
    e = re.sub(r'(?<=[0-9a-fA-Fx])(?:ULL|UL|LL|U|L)\b', '', e)
    e = re.sub(r'\b(true)\b', '1', e); e = re.sub(r'\b(false)\b', '0', e)
    e = re.sub(r'\b(?:M_PI)\b', '3.141592653589793', e)
    e = re.sub(r'\b(?:float|int|uint8_t|int8_t|int16_t|uint16_t|int32_t|uint32_t)\s*\(', '(', e)
    e = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*::', '', e)
    if '?' in e or '"' in e or '{' in e: return None

    def rep(m):
        w = m.group(0)
        if w in defs:
            vals = {evaluate(x, defs, depth + 1) for x in defs[w]}
            if len(vals) != 1: raise KeyError(w)
            v = vals.pop()
            if v is None: raise KeyError(w)
            return repr(v)
        raise KeyError(w)
    try:
        e2 = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b', rep, e)
        v = _ev(ast.parse(e2, mode='eval'))
        if isinstance(v, float):
            v = round(v, 6)
            if v.is_integer(): v = int(v)
        return v
    except Exception:
        return None


def _scan_file(path, defs_out, entries_out):
    try:
        s = open(path, encoding='utf-8', errors='replace').read()
    except Exception:
        return
    in_enum = 0
    for line in s.splitlines():
        m = RE_DEF.match(line) or RE_CONST.match(line)
        if not m and in_enum: m = RE_ENUM.match(line)
        if m:
            defs_out.setdefault(m.group(1), set()).add(m.group(2).strip())
        if re.search(r'\benum\b', line): in_enum = 1
        if in_enum and '}' in line: in_enum = 0
    if '@Param' not in s: return
    lines = s.splitlines(); i = 0
    while i < len(lines):
        m = RE_PARAM.search(lines[i])
        if not m: i += 1; continue
        short = m.group(1); dn = ''; j = i + 1
        while j < len(lines) and lines[j].strip().startswith('//'):
            md = RE_DN.search(lines[j])
            if md: dn = md.group(1).strip()
            if RE_PARAM.search(lines[j]): break
            j += 1
        if j < len(lines) and RE_PARAM.search(lines[j]):
            i = j; continue
        chunk = '\n'.join(lines[j:j + 12])
        mm = re.search(r'\b(' + '|'.join(MACROS) + r')\s*\(', chunk)
        if mm and chunk[:mm.start()].strip() == '':
            args, _ = _args(chunk, mm.end() - 1)
            name = de = None
            if mm.group(1) in ('GSCALAR', 'ASCALAR', 'GGLOBAL') and len(args) >= 3:
                name, de = args[1].strip('"'), args[2]
            elif mm.group(1).startswith('AP_GROUPINFO') and len(args) >= 5:
                name, de = args[0].strip('"'), args[4]
            if name is not None:
                entries_out.append((short.lstrip('_'), name.lstrip('_'), ' '.join(dn.split()), de))
        i = j + 1


def extract(src, per):
    """per: {araç: {param: {'dn':..}}} -> {araç: {param: varsayılan}}"""
    lib_defs = {}; lib_entries = []
    for root, _, files in os.walk(os.path.join(src, 'libraries')):
        if '/tests' in root or 'examples' in root or 'SITL' in root: continue
        for f in files:
            if f.endswith(('.cpp', '.h')): _scan_file(os.path.join(root, f), lib_defs, lib_entries)
    out = {}
    cache = {}
    for v, params in per.items():
        d = VDIR.get(v)
        if d not in cache:
            vdefs = {}; vent = []
            p = os.path.join(src, d)
            for root, _, files in os.walk(p):
                for f in files:
                    if f.endswith(('.cpp', '.h')): _scan_file(os.path.join(root, f), vdefs, vent)
            cache[d] = (vdefs, vent)
        vdefs, vent = cache[d]
        defs = dict(lib_defs); defs.update(vdefs)
        if v == 'Heli': defs['FRAME_CONFIG'] = {'HELI_FRAME'}
        idx_v = {}; idx_l = {}
        for short, nm, dn, de in vent: idx_v.setdefault(dn, []).append((short, nm, de))
        for short, nm, dn, de in lib_entries: idx_l.setdefault(dn, []).append((short, nm, de))
        res = {}
        for k, p in params.items():
            dn = p.get('dn', '')
            for idx in (idx_v, idx_l):
                cands = [c for c in idx.get(dn, []) if k == c[1] or k.endswith('_' + c[1]) or k.endswith(c[1])]
                if not cands: continue
                vals = {evaluate(c[2], defs) for c in cands}
                vals.discard(None)
                if len(vals) == 1: res[k] = vals.pop()
                break
        out[v] = res
        print(f'  defaults {v}: {len(res)}/{len(params)}')
    return out
