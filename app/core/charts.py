"""Rapor ve arayüz grafikleri (matplotlib). Her grafik PNG bayt dizisi olarak üretilir."""
from __future__ import annotations
import io, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from .analysis import Analysis, fmt_t, hav
from .rtexts import RT
from . import knowledge as K

C = {'blue': '#2563EB', 'orange': '#EA580C', 'green': '#16A34A', 'red': '#DC2626', 'gray': '#6B7280', 'purple': '#7C3AED',
     'teal': '#0D9488', 'amber': '#D97706', 'ink': '#111827', 'grid': '#E5E7EB'}
PH_COL = {'ground': '#F3F4F6', 'takeoff': '#DBEAFE', 'climb': '#E0F2FE', 'cruise': '#ECFDF5', 'descent': '#FEF3C7', 'landing': '#FCE7F3'}


def shape(s, lang):
    if lang != 'ar' or not s:
        return s
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(s))
    except Exception:
        return s


def rt(key, lang):
    i = ('tr', 'en', 'ar').index(lang)
    return shape(RT[key][i], lang)


def _fig(h=3.2, w=8.0):
    fig = Figure(figsize=(w, h), dpi=150)
    fig.patch.set_facecolor('white')
    return fig


def _style(ax, lang):
    ax.grid(True, color=C['grid'], lw=0.6)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=7)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: fmt_t(x)[:-2]))


MARK = {'t': None, 'span': None}


def _png(fig):
    if MARK['t'] is not None or MARK['span']:
        for ax in fig.axes:
            if getattr(ax, 'name', '') != 'rectilinear' or not isinstance(ax.xaxis.get_major_formatter(), FuncFormatter): continue
            if MARK['span']: ax.axvspan(MARK['span'][0], MARK['span'][1], color='#F59E0B', alpha=0.22, zorder=5)
            if MARK['t'] is not None: ax.axvline(MARK['t'], color='#F59E0B', lw=2.4, zorder=6)
    b = io.BytesIO(); fig.tight_layout(); fig.savefig(b, format='png', dpi=150); return b.getvalue()


def _phases(ax, A):
    for p in A.phases:
        ax.axvspan(p['t0'], p['t1'], color=PH_COL.get(p['name'], '#fff'), lw=0, zorder=0)


def _modes(ax, A, lang, label=True):
    ylim = ax.get_ylim()
    for t, n, _, r in A.L.modes:
        col = C['red'] if r in K.FAILSAFE_REASONS else C['purple']
        ax.axvline(t, color=col, lw=0.8, ls='--', alpha=0.7, zorder=1)
        if label:
            ax.text(t, ylim[1], ' ' + K.mode_name(A.vehicle, n), rotation=90, va='top', ha='left', fontsize=6, color=col)


def _crash(ax, A):
    if A.verdict.get('kind') == 'crash' and A.flights:
        ax.axvline(A.flights[-1][1], color=C['red'], lw=2, alpha=0.6)


def chart_alt(A: Analysis, lang):
    L = A.L; fig = _fig(3.4); ax = fig.add_subplot(111); _style(ax, lang)
    _phases(ax, A)
    if A.track is not None:
        ax.plot(A.track['t'], A.track['rel'], color=C['blue'], lw=1.3, label=rt('l_alt', lang))
    ax.set_ylabel(rt('ax_alt', lang), fontsize=8)
    ax2 = ax.twinx(); ax2.tick_params(labelsize=7)
    g = L.s('GPS')
    if g.has('Spd'): ax2.plot(g['t'], g['Spd'], color=C['orange'], lw=0.8, alpha=0.9, label=rt('l_gs', lang))
    a = L.s('ARSP') if L.s('ARSP').has('Airspeed') else L.s('CTUN')
    f = 'Airspeed' if a.has('Airspeed') else ('As' if a.has('As') else None)
    if f and A.vehicle == 'Plane': ax2.plot(a['t'], a[f], color=C['green'], lw=0.8, alpha=0.9, label=rt('l_as', lang))
    amin = L.params.get('AIRSPEED_MIN', L.params.get('ARSPD_FBW_MIN'))
    if amin and A.vehicle == 'Plane': ax2.axhline(amin, color=C['green'], lw=0.6, ls=':')
    ax2.set_ylabel(rt('ax_spd', lang), fontsize=8)
    _modes(ax, A, lang); _crash(ax, A)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6, loc='upper right', framealpha=0.8)
    ax.set_title(rt('c_alt', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_att(A, lang):
    a = A.L.s('ATT')
    if not a.has('Roll'): return None
    fig = _fig(3.6); ax1 = fig.add_subplot(211); ax2 = fig.add_subplot(212, sharex=ax1)
    for ax, f, lab in ((ax1, 'Roll', 'l_roll'), (ax2, 'Pitch', 'l_pitch')):
        _style(ax, lang); _phases(ax, A)
        if a.has('Des' + f): ax.plot(a['t'], a['Des' + f], color=C['gray'], lw=0.7, label=f"{rt(lab, lang)} ({rt('l_des', lang)})")
        ax.plot(a['t'], a[f], color=C['blue'] if f == 'Roll' else C['orange'], lw=0.8, label=rt(lab, lang))
        ax.set_ylabel(rt('ax_deg', lang), fontsize=7); ax.legend(fontsize=6, loc='upper right'); _crash(ax, A)
    ax1.set_title(rt('c_att', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_gps(A, lang):
    g = A.L.s('GPS')
    if not g.has('NSats'): return None
    fig = _fig(2.8); ax = fig.add_subplot(111); _style(ax, lang); _phases(ax, A)
    ax.plot(g['t'], g['NSats'], color=C['blue'], lw=1, label=rt('ax_sats', lang))
    ax.axhline(6, color=C['red'], lw=0.6, ls=':'); ax.axhline(10, color=C['green'], lw=0.6, ls=':')
    ax.set_ylabel(rt('ax_sats', lang), fontsize=8); ax.set_ylim(0, max(20, np.nanmax(g['NSats']) + 2))
    if g.has('HDop'):
        ax2 = ax.twinx(); ax2.tick_params(labelsize=7)
        ax2.plot(g['t'], np.clip(g['HDop'], 0, 10), color=C['orange'], lw=0.8, label='HDOP'); ax2.axhline(2, color=C['orange'], lw=0.6, ls=':')
        ax2.set_ylabel('HDOP', fontsize=8)
        h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=6, loc='lower right')
    _modes(ax, A, lang, False); _crash(ax, A)
    ax.set_title(rt('c_gps', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_vibe(A, lang):
    v = A.L.s('VIBE')
    if not v.has('VibeZ'): return None
    fig = _fig(2.9); ax = fig.add_subplot(111); _style(ax, lang); _phases(ax, A)
    for f, c in (('VibeX', C['blue']), ('VibeY', C['green']), ('VibeZ', C['orange'])):
        if v.has(f): ax.plot(v['t'], v[f], color=c, lw=0.7, label=f[-1])
    ax.axhline(30, color=C['amber'], lw=0.8, ls='--'); ax.axhline(60, color=C['red'], lw=0.8, ls='--')
    ax.set_ylabel(rt('ax_vibe', lang), fontsize=8)
    ck = next((k for k in ('Clip', 'Clip0') if v.has(k)), None)
    if ck:
        ax2 = ax.twinx(); ax2.tick_params(labelsize=7); ax2.plot(v['t'], v[ck], color=C['red'], lw=0.8, alpha=0.6, label=rt('l_clip', lang))
        ax2.set_ylabel(rt('l_clip', lang), fontsize=8)
    ax.legend(fontsize=6, loc='upper left'); _crash(ax, A)
    ax.set_title(rt('c_vibe', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_bat(A, lang):
    b = A.L.s('BAT')
    if not b.has('Volt'): return None
    fig = _fig(2.9); ax = fig.add_subplot(111); _style(ax, lang); _phases(ax, A)
    vv = np.where(b['Volt'] > 1, b['Volt'], np.nan)
    ax.plot(b['t'], vv, color=C['blue'], lw=1, label=rt('l_volt', lang)); ax.set_ylabel(rt('ax_volt', lang), fontsize=8)
    P = A.L.params
    for k, c in (('BATT_LOW_VOLT', C['amber']), ('BATT_CRT_VOLT', C['red'])):
        if P.get(k): ax.axhline(P[k], color=c, lw=0.7, ls='--')
    if b.has('Curr') and np.nanmax(np.abs(b['Curr'])) > 0.5:
        ax2 = ax.twinx(); ax2.tick_params(labelsize=7); ax2.plot(b['t'], b['Curr'], color=C['orange'], lw=0.6, alpha=0.8, label=rt('l_curr', lang))
        ax2.set_ylabel(rt('ax_curr', lang), fontsize=8)
        h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=6, loc='lower left')
    _crash(ax, A)
    ax.set_title(rt('c_bat', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_rcou(A, lang):
    o = A.L.s('RCOU'); c = A.L.s('CTUN')
    if not o.has('C1'): return None
    fig = _fig(3.0); ax = fig.add_subplot(111); _style(ax, lang); _phases(ax, A)
    cols = [C['blue'], C['green'], C['orange'], C['purple']]
    for i, ch in enumerate(('C1', 'C2', 'C3', 'C4')):
        if o.has(ch): ax.plot(o['t'], o[ch], lw=0.6, color=cols[i], label=ch)
    ax.set_ylabel(rt('ax_pwm', lang), fontsize=8); ax.legend(fontsize=6, loc='upper left', ncol=4)
    if c.has('ThO'):
        ax2 = ax.twinx(); ax2.tick_params(labelsize=7); ax2.plot(c['t'], c['ThO'], color=C['red'], lw=0.6, alpha=0.6); ax2.set_ylabel(rt('ax_thr', lang), fontsize=8)
    _crash(ax, A)
    ax.set_title(rt('c_rcou', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_ekf(A, lang):
    x = A.L.s('XKF4') if A.L.s('XKF4').has('SV') else A.L.s('NKF4')
    if not x.has('SV'): return None
    fig = _fig(2.8); ax = fig.add_subplot(111); _style(ax, lang); _phases(ax, A)
    for f, c in (('SV', C['blue']), ('SP', C['green']), ('SH', C['orange']), ('SM', C['purple'])):
        if x.has(f): ax.plot(x['t'], x[f], lw=0.8, color=c, label=f)
    ax.axhline(0.8, color=C['amber'], lw=0.7, ls='--'); ax.axhline(1.0, color=C['red'], lw=0.7, ls='--')
    ax.set_ylabel(rt('ax_ratio', lang), fontsize=8); ax.legend(fontsize=6, loc='upper left', ncol=4); _modes(ax, A, lang, False); _crash(ax, A)
    ax.set_title(rt('c_ekf', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_mag(A, lang):
    m = A.L.s('MAG'); c = A.L.s('CTUN')
    if not m.has('MagX'): return None
    fig = _fig(2.8); ax = fig.add_subplot(111); _style(ax, lang); _phases(ax, A)
    fm = np.sqrt(m['MagX'] ** 2 + m['MagY'] ** 2 + m['MagZ'] ** 2)
    ax.plot(m['t'], fm, color=C['teal'], lw=0.8, label='|MAG|'); ax.set_ylabel(rt('ax_mag', lang), fontsize=8)
    if c.has('ThO'):
        ax2 = ax.twinx(); ax2.tick_params(labelsize=7); ax2.plot(c['t'], c['ThO'], color=C['red'], lw=0.6, alpha=0.6, label=rt('l_thr', lang)); ax2.set_ylabel(rt('ax_thr', lang), fontsize=8)
    ax.set_title(rt('c_mag', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_map(A, lang, online=True, src='osm'):
    tr = A.track
    if tr is None: return None
    lat, lon = tr['lat'], tr['lon']
    la0, la1 = float(np.nanmin(lat)), float(np.nanmax(lat)); lo0, lo1 = float(np.nanmin(lon)), float(np.nanmax(lon))
    pad = max(la1 - la0, lo1 - lo0) * 0.12 + 0.0008
    la0 -= pad; la1 += pad; lo0 -= pad; lo1 += pad
    fig = _fig(5.2, 7.2); ax = fig.add_subplot(111)
    try:
        from .tiles import mosaic
        mz = mosaic(la0, la1, lo0, lo1, src=src, online=online)
    except Exception:
        mz = None
    if mz:
        img, ext, z = mz
        ax.imshow(img, extent=ext, aspect='auto', zorder=0)
        attribution = '© OpenStreetMap' if src == 'osm' else ('© Esri' if src == 'sat' else '© OpenTopoMap')
        ax.text(0.99, 0.01, attribution, transform=ax.transAxes, fontsize=5, ha='right', va='bottom', color='#333', bbox=dict(fc='white', alpha=0.6, lw=0))
    sc = ax.scatter(lon, lat, c=tr['rel'], s=2, cmap='viridis', zorder=3)
    cb = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.01); cb.ax.tick_params(labelsize=6); cb.set_label(rt('ax_alt', lang), fontsize=7)
    ax.plot(lon[0], lat[0], marker='*', color=C['amber'], ms=12, mec='k', zorder=5, label=rt('l_home', lang))
    for t, n, _, r in A.L.modes:
        if t < tr['t'][0] or t > tr['t'][-1]: continue
        i = int(np.searchsorted(tr['t'], t)); i = min(i, len(lat) - 1)
        col = C['red'] if r in K.FAILSAFE_REASONS else C['purple']
        ax.plot(lon[i], lat[i], 'o', color=col, ms=4, zorder=4); ax.text(lon[i], lat[i], ' ' + K.mode_name(A.vehicle, n), fontsize=6, color=col, zorder=6)
    if A.verdict.get('kind') == 'crash':
        ax.plot(lon[-1], lat[-1], 'X', color=C['red'], ms=12, mec='k', zorder=6, label=rt('l_crash', lang))
    ax.set_xlim(lo0, lo1); ax.set_ylim(la0, la1)
    ax.set_aspect(1 / math.cos(math.radians((la0 + la1) / 2)))
    ax.tick_params(labelsize=6); ax.legend(fontsize=6, loc='upper left')
    ax.set_title(rt('c_map', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_health(A, lang):
    from .texts import T
    if not A.health: return None
    items = list(A.health.items())
    fig = _fig(0.42 * len(items) + 0.8, 7.2); ax = fig.add_subplot(111)
    names = [shape(T('dom_' + k, lang), lang) for k, _ in items]; vals = [v['score'] for _, v in items]
    cols = [C['green'] if v['status'] == 'good' else (C['amber'] if v['status'] == 'warn' else C['red']) for _, v in items]
    y = np.arange(len(items))[::-1]
    ax.barh(y, vals, color=cols, height=0.6)
    for yy, v in zip(y, vals): ax.text(v + 1, yy, str(v), va='center', fontsize=7)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=7); ax.set_xlim(0, 108)
    ax.axvline(80, color=C['green'], lw=0.6, ls=':'); ax.axvline(55, color=C['amber'], lw=0.6, ls=':')
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=7)
    ax.set_title(rt('c_health', lang), fontsize=9, loc='left')
    return _png(fig)


def chart_timeline(A, lang):
    from .texts import render
    E = [e for e in A.events if e['cat'] in ('mode', 'err', 'flight') or e['sev'] > 0]
    if not E: return None
    fig = _fig(2.6); ax = fig.add_subplot(111); _style(ax, lang); _phases(ax, A)
    rows = {'flight': 4, 'mode': 3, 'ev': 2, 'err': 1, 'msg': 0}
    cols = {0: C['blue'], 1: C['amber'], 2: C['red']}
    for e in E:
        ax.plot(e['t'], rows.get(e['cat'], 0), 'o', color=cols[e['sev']], ms=5)
    ax.set_yticks(list(rows.values())); ax.set_yticklabels([rt('cat_' + k, lang) for k in rows], fontsize=7)
    ax.set_ylim(-0.7, 4.7); ax.set_xlim(0, max(1, A.L.duration))
    ax.set_title(rt('c_timeline', lang), fontsize=9, loc='left')
    return _png(fig)


ALL = [('c_alt', chart_alt), ('c_att', chart_att), ('c_gps', chart_gps), ('c_vibe', chart_vibe), ('c_bat', chart_bat),
       ('c_rcou', chart_rcou), ('c_ekf', chart_ekf), ('c_mag', chart_mag)]


def render_marked(key, A, lang, t=None, span=None):
    """Belirtilen grafiği, ilgili an/aralık turuncu işaretli olarak üretir (alıştırma ve ders rehberi)."""
    fn = dict(ALL + [('c_health', chart_health), ('c_timeline', chart_timeline)]).get(key)
    if not fn: return None
    MARK['t'] = t; MARK['span'] = span
    try:
        return fn(A, lang)
    finally:
        MARK['t'] = None; MARK['span'] = None
