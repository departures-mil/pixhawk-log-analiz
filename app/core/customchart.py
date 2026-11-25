"""Kendi grafiğini çiz: logdaki herhangi bir MESAJ.ALAN'ı ya da formülü (ör. RCOU.C3 - RCOU.C1, BAT.Volt * BAT.Curr) ve
Full Parameter List parametrelerini (eşik çizgisi olarak) seçip mod bantlı, saatli grafik üretir; görünen aralık için
istatistik (en düşük / en yüksek / ortalama, eşik üstünde geçen süre) verir. Grafik tanımları kaydedilip yeniden kullanılır.

Formül dili (güvenli, yalnız izinli işlemler):
  MESAJ.ALAN · MESAJ[1].ALAN · PARAMETRE_ADI (bu logdaki değeri) · sayılar · + - * / ** · ( )
  abs sqrt deg rad sin cos tan atan2 hypot min max clip(x,lo,hi) smooth(x,n) rate(x) (saniye başına değişim) pct(x,lo,hi) (0–100)
"""
from __future__ import annotations
import ast, re
import numpy as np

FIELD_RE = re.compile(r'\b([A-Z][A-Z0-9_]*(?:\[\d+\])?)\.([A-Za-z_][A-Za-z0-9_]*)\b')
MAXPTS = 9000

PRESETS = [
    {'name': ('Güç (W) = gerilim × akım', 'Power (W) = voltage × current', 'القدرة (واط) = الجهد × التيار'),
     'series': [{'expr': 'BAT.Volt * BAT.Curr', 'panel': 1}, {'expr': 'CTUN.ThO', 'panel': 2}], 'params': []},
    {'name': ('Yatış hatası (istenen − gerçek)', 'Roll error (desired − actual)', 'خطأ الدوران (المطلوب − الفعلي)'),
     'series': [{'expr': 'ATT.DesRoll - ATT.Roll', 'panel': 1}, {'expr': 'ATT.DesPitch - ATT.Pitch', 'panel': 2}], 'params': []},
    {'name': ('Hava hızı ve sınırları', 'Airspeed and its limits', 'السرعة الجوية وحدودها'),
     'series': [{'expr': 'ARSP.Airspeed', 'panel': 1}, {'expr': 'GPS.Spd', 'panel': 1}],
     'params': [{'name': 'AIRSPEED_MIN', 'panel': 1}, {'name': 'ARSPD_FBW_MIN', 'panel': 1}, {'name': 'AIRSPEED_MAX', 'panel': 1}, {'name': 'ARSPD_FBW_MAX', 'panel': 1}]},
    {'name': ('Titreşim ve kırpılma', 'Vibration and clipping', 'الاهتزاز والقص'),
     'series': [{'expr': 'VIBE.VibeX', 'panel': 1}, {'expr': 'VIBE.VibeY', 'panel': 1}, {'expr': 'VIBE.VibeZ', 'panel': 1}, {'expr': 'VIBE.Clip', 'panel': 2}], 'params': []},
    {'name': ('Gaz kanalı ve sınırları', 'Throttle channel and limits', 'قناة الخانق وحدودها'),
     'series': [{'expr': 'RCOU.C3', 'panel': 1}, {'expr': 'RCIN.C3', 'panel': 1}],
     'params': [{'name': 'SERVO3_MIN', 'panel': 1}, {'name': 'SERVO3_MAX', 'panel': 1}, {'name': 'THR_FS_VALUE', 'panel': 1}]},
    {'name': ('İrtifa: barometre ve GPS', 'Altitude: barometer vs GPS', 'الارتفاع: البارومتر و GPS'),
     'series': [{'expr': 'BARO.Alt', 'panel': 1}, {'expr': 'POS.RelHomeAlt', 'panel': 1}, {'expr': 'BARO.Alt - POS.RelHomeAlt', 'panel': 2}], 'params': []},
]


class ExprError(ValueError):
    pass


def catalog(L):
    """[(MESAJ.ALAN, mesaj, alan, örnek sayısı)] — logdaki tüm sayısal alanlar."""
    out = []
    for m in sorted(L.msgs):
        s = L.msgs[m]
        n = len(s.get('t', []))
        if not n: continue
        for f in s:
            if f == 't': continue
            try:
                a = s[f]
                if not hasattr(a, 'dtype') or a.dtype.kind not in 'fiub' or len(a) != n: continue
            except Exception:
                continue
            out.append((f'{m}.{f}', m, f, n))
    return out


def refs(expr):
    return [(m.group(1), m.group(2)) for m in FIELD_RE.finditer(expr or '')]


def _smooth(x, n=5):
    n = max(1, int(n))
    if n <= 1 or len(x) < n: return x
    k = np.ones(n) / n
    xx = np.nan_to_num(x, nan=np.nanmean(x) if np.isfinite(x).any() else 0.0)
    return np.convolve(xx, k, mode='same')


def evaluate(L, expr):
    """(t, y) — formülü hesaplar. Zaman tabanı ilk alanın zamanıdır; diğerleri ona doğrusal aradeğerlenir."""
    expr = (expr or '').strip().replace('×', '*').replace('−', '-').replace('÷', '/')
    if not expr: raise ExprError('empty')
    rs = refs(expr)
    if not rs: raise ExprError('no_field')
    env = {}; t0 = None; code = expr
    for i, (m, f) in enumerate(dict.fromkeys(rs)):
        s = L.s(m)
        if not s.has(f): raise ExprError(f'missing:{m}.{f}')
        v = f'_v{i}'
        if t0 is None:
            t0 = np.asarray(s['t'], float); env[v] = np.asarray(s[f], float)
        else:
            tt = np.asarray(s['t'], float); y = np.asarray(s[f], float)
            ok = np.isfinite(y)
            env[v] = np.interp(t0, tt[ok], y[ok], left=np.nan, right=np.nan) if ok.sum() >= 2 else np.full(len(t0), np.nan)
        code = re.sub(r'\b' + re.escape(m) + r'\.' + re.escape(f) + r'\b', v, code)
    dt = np.gradient(t0) if len(t0) > 1 else np.ones(len(t0))
    dt[dt == 0] = np.nan
    F = {'abs': np.abs, 'sqrt': lambda x: np.sqrt(np.clip(x, 0, None)), 'deg': np.degrees, 'rad': np.radians,
         'sin': np.sin, 'cos': np.cos, 'tan': np.tan, 'atan2': np.arctan2, 'hypot': np.hypot,
         'min': np.minimum, 'max': np.maximum, 'clip': np.clip, 'smooth': _smooth,
         'rate': lambda x: np.gradient(x) / dt, 'pct': lambda x, lo, hi: (x - lo) / (hi - lo) * 100.0}
    try:
        tree = ast.parse(code, mode='eval')
    except SyntaxError:
        raise ExprError('syntax')

    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return float(n.value)
        if isinstance(n, ast.Name):
            if n.id in env: return env[n.id]
            if n.id in L.params: return float(L.params[n.id])
            raise ExprError(f'unknown:{n.id}')
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            x = ev(n.operand); return -x if isinstance(n.op, ast.USub) else x
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            with np.errstate(all='ignore'):
                if isinstance(n.op, ast.Add): return a + b
                if isinstance(n.op, ast.Sub): return a - b
                if isinstance(n.op, ast.Mult): return a * b
                if isinstance(n.op, ast.Div): return a / b
                if isinstance(n.op, ast.Pow): return a ** b
            raise ExprError('op')
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in F and not n.keywords:
            with np.errstate(all='ignore'):
                return F[n.func.id](*[ev(a) for a in n.args])
        raise ExprError('syntax')

    y = ev(tree)
    y = np.broadcast_to(np.asarray(y, float), t0.shape).astype(float)
    return t0, y


def stats(t, y, t0=None, t1=None, thr=None):
    """Görünen aralıkta: n, en düşük, en yüksek, ortalama, son; thr verilirse üstünde geçen süre (s)."""
    t = np.asarray(t); y = np.asarray(y, float)
    m = np.isfinite(y)
    if t0 is not None: m &= t >= t0
    if t1 is not None: m &= t <= t1
    if m.sum() == 0: return None
    yy = y[m]; tt = t[m]
    r = {'n': int(m.sum()), 'min': float(np.min(yy)), 'max': float(np.max(yy)), 'mean': float(np.mean(yy)),
         'tmin': float(tt[int(np.argmin(yy))]), 'tmax': float(tt[int(np.argmax(yy))])}
    if thr is not None and len(tt) > 1:
        d = np.diff(tt, append=tt[-1]); d = np.clip(d, 0, 1.0)
        r['above'] = float(np.sum(d[yy > thr])); r['below'] = float(np.sum(d[yy < thr]))
    return r


def _dec(t, y):
    from .charts import _dec as d
    try: return d(t, y)
    except Exception: return t, y


def build(A, spec, lg='tr'):
    """spec = {'title', 'series': [{'expr', 'panel', 'label'?}], 'params': [{'name', 'panel'}], 'lines': [{'y','panel','label'}]}
    → (Figure, [{'label','expr','t','y','panel','err'}])"""
    from . import charts as B, charts2 as C2
    L = A.L
    ser = [dict(s) for s in spec.get('series', []) if (s.get('expr') or '').strip()]
    pars = [dict(p) for p in spec.get('params', []) if p.get('name')]
    panels = sorted({int(s.get('panel', 1) or 1) for s in ser} | {int(p.get('panel', 1) or 1) for p in pars}) or [1]
    np_ = len(panels)
    fig = B._fig(min(1.7 + 1.8 * np_, 10.0), 10.5)
    axs = {}
    for i, pn in enumerate(panels):
        ax = fig.add_subplot(np_, 1, i + 1, sharex=axs[panels[0]] if axs else None); C2._base(ax, A, lg); axs[pn] = ax
    pal = ['#2563EB', '#EA580C', '#16A34A', '#9333EA', '#0D9488', '#DC2626', '#CA8A04', '#475569', '#DB2777', '#0EA5E9']
    out = []
    for j, s in enumerate(ser):
        pn = int(s.get('panel', 1) or 1); ax = axs[pn]
        lab = s.get('label') or s['expr']
        try:
            t, y = evaluate(L, s['expr'])
            ax.plot(*_dec(t, y), color=pal[j % len(pal)], lw=0.8, label=lab)
            out.append({'label': lab, 'expr': s['expr'], 't': t, 'y': y, 'panel': pn, 'err': None, 'color': pal[j % len(pal)]})
        except ExprError as e:
            out.append({'label': lab, 'expr': s['expr'], 't': None, 'y': None, 'panel': pn, 'err': str(e), 'color': pal[j % len(pal)]})
    for p in pars:
        n = p['name']; pn = int(p.get('panel', 1) or 1)
        if n not in L.params: continue
        v = float(L.params[n])
        C2._plim(axs[pn], v, f'{n}={v:g}', '#B91C1C', ls='--', lw=0.8, x=0.6)
        out.append({'label': n, 'param': n, 'value': v, 'panel': pn, 'err': None})
    for ln in spec.get('lines', []) or []:
        try:
            C2._plim(axs[int(ln.get('panel', 1))], float(ln['y']), ln.get('label') or f"{float(ln['y']):g}", '#7C3AED', ls='-.', lw=0.7)
        except Exception: pass
    for i, pn in enumerate(panels):
        ax = axs[pn]; C2._leg(ax, ncol=3); C2._end(ax, A, lg, i == 0)
        if i < np_ - 1: ax.tick_params(labelbottom=False)
    title = spec.get('title') or ''
    if title and not getattr(B._TL, 'fig', False): axs[panels[0]].set_title(B.mshape(title, lg), fontsize=9, loc='left', pad=30)
    # kaynak şeridi: seçilen alanlar ve parametreler
    flds = list(dict.fromkeys(f'{m}.{f}' for s in ser for m, f in refs(s['expr'])))
    ps = [f"{p['name']}={float(L.params[p['name']]):g}" for p in pars if p['name'] in L.params]
    txt = 'log: ' + '  '.join(flds[:14]) + (('\nparam: ' + '  '.join(ps[:10])) if ps else '')
    import io, warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try: fig.tight_layout()
        except Exception: pass
    _footer_text(fig, txt, lg)
    if getattr(B._TL, 'fig', False): return fig, out
    b = io.BytesIO(); fig.savefig(b, format='png', dpi=150)
    return b.getvalue(), out


def _footer_text(fig, txt, lg):
    n = txt.count('\n') + 1
    H = fig.get_figheight(); dh = 0.105 * n + 0.2; Hn = H + dh; fig.set_figheight(Hn)
    k = H / Hn; off = dh / Hn
    for ax in fig.axes:
        p = ax.get_position(); ax.set_position([p.x0, p.y0 * k + off, p.width, p.height * k])
    fig.text(0.01, 0.012, txt, fontsize=5.6, color='#475569', family='DejaVu Sans Mono', ha='left', va='bottom', linespacing=1.35,
             bbox=dict(boxstyle='round,pad=0.25', fc='#F1F5F9', ec='#CBD5E1', lw=0.5))
    fig._src_done = True
