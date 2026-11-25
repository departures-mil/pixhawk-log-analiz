"""v1.1.5 grafik seti: özet panosu, stick hareketleri, görevli kanallar, isimli motorlar, hız/rüzgâr, TECS, PID, navigasyon,
GPS doğruluğu, titreşim spektrumu, IMU/baro karşılaştırması, güç, ESC, EKF yenilikleri, pusula örnekleri, mod çizelgesi.
Hepsi charts.py'deki ortak süslemeyi kullanır: mod bantları, mod adları ve gerçek saat, aşama şeridi, kırım çizgisi."""
from __future__ import annotations
import math, warnings
import numpy as np
warnings.filterwarnings('ignore', message='All-NaN slice')
warnings.filterwarnings('ignore', message='Mean of empty slice')
from matplotlib.ticker import FuncFormatter
from . import charts as B
from . import viz
from .analysis import fmt_t
from .rtexts import RT

C = B.C
_g = B._g


def rt(k, lg):
    return B.rt(k, lg)


def _t(tup, lg):
    return B.mshape(viz.tx(tup, lg), lg)


def _base(ax, A, lg, top=True):
    B._style(ax, lg); B._phases(ax, A)


def _end(ax, A, lg, top=True):
    B._modes(ax, A, lg, label=top); B._crash(ax, A)
    ax.set_xlim(0, max(1.0, float(A.L.duration or 1)))


def _leg(ax, hs=None, ls=None, ncol=6, loc='upper left'):
    if hs is None: hs, ls = ax.get_legend_handles_labels()
    if hs: ax.legend(hs, ls, fontsize=5.8, loc=loc, ncol=min(ncol, len(hs)), framealpha=0.85, borderaxespad=0.3, handlelength=1.4)


def _both(ax, ax2, **kw):
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); _leg(ax, h1 + h2, l1 + l2, **kw)


def _title(ax, key, lg, extra=''):
    ax.set_title(rt(key, lg) + (('  ·  ' + B.mshape(extra, lg)) if extra else ''), fontsize=9, loc='left')


def _first(L, *names):
    for n in names:
        s = L.s(n)
        if s and len(s.get('t', [])): return s
    return L.s(names[0])


# ------------------------------------------------------------------ özet panosu
def chart_overview(A, lg):
    L = A.L
    fig = B._fig(5.6, 8.2)
    gs = fig.add_gridspec(4, 2, height_ratios=[0.9, 1, 1, 1], hspace=0.55, wspace=0.18)
    axk = fig.add_subplot(gs[0, :]); axk.axis('off')
    f = A.facts or {}; v = A.verdict or {}
    from .texts import vkey
    vk = vkey(v)
    vcol = {'crash': C['red'], 'incident': C['amber'], 'incident_minor': '#CA8A04', 'normal': C['green']}.get(vk, C['gray'])
    from .texts import T as _T
    vt = _T('v_' + vk, lg)
    segs = viz.segments(A, lg)
    dur = sum(b - a for a, b in (A.flights or []))
    cards = [(_t(('Karar', 'Verdict', 'القرار'), lg), B.mshape(vt.split(' (')[0], lg), vcol),
             (_t(('Uçuş süresi', 'Flight time', 'زمن الطيران'), lg), fmt_t(dur)[:-2] if dur else '-', C['blue']),
             (_t(('Azami irtifa', 'Max altitude', 'أقصى ارتفاع'), lg), f"{np.nanmax(A.track['rel']):.0f} m" if A.track is not None and len(A.track['rel']) else '-', C['teal']),
             (_t(('Mod değişimi', 'Mode changes', 'تغييرات الوضع'), lg), f"{max(0, len(segs) - 1)}", C['purple']),
             (_t(('Sağlık', 'Health', 'الصحة'), lg), f"{A.overall}/100", C['green'] if A.overall >= 80 else (C['amber'] if A.overall >= 55 else C['red']))]
    c0 = viz.clock(A, A.flights[0][0]) if A.flights else None
    if c0: cards.append((_t(('Kalkış saati', 'Takeoff time', 'وقت الإقلاع'), lg), f'{viz.date_of(A) or ""} {c0}'.strip(), C['ink']))
    n = len(cards)
    for i, (k, val, col) in enumerate(cards):
        x = i / n
        axk.add_patch(B.matplotlib.patches.FancyBboxPatch((x + 0.006, 0.08), 1 / n - 0.012, 0.84, boxstyle='round,pad=0.01,rounding_size=0.04',
                                                           transform=axk.transAxes, fc=col, alpha=0.12, ec=col, lw=1))
        axk.text(x + 0.5 / n, 0.66, k, transform=axk.transAxes, ha='center', va='center', fontsize=6.5, color='#374151')
        axk.text(x + 0.5 / n, 0.32, val, transform=axk.transAxes, ha='center', va='center', fontsize=8.5 if len(val) < 14 else 6.5, color=col, fontweight='bold')
    panels = []
    if A.track is not None: panels.append(('l_alt', A.track['t'], A.track['rel'], C['blue'], 'm'))
    g = L.s('GPS')
    if g.has('Spd'): panels.append(('l_gs', g['t'], g['Spd'], C['orange'], 'm/s'))
    b = L.s('BAT')
    if b.has('Volt'): panels.append(('l_volt', b['t'], np.where(b['Volt'] > 1, b['Volt'], np.nan), C['green'], 'V'))
    if b.has('Curr') and np.nanmax(np.abs(b['Curr'])) > 0.5: panels.append(('l_curr', b['t'], b['Curr'], C['red'], 'A'))
    vb = L.s('VIBE')
    if vb.has('VibeZ'): panels.append(('c_vibe', vb['t'], vb['VibeZ'], C['amber'], 'Z m/s²'))
    if g.has('NSats'): panels.append(('ax_sats', g['t'], g['NSats'], C['purple'], ''))
    for i, (k, t, y, col, u) in enumerate(panels[:6]):
        ax = fig.add_subplot(gs[1 + i // 2, i % 2]); B._style(ax, lg); B._phases(ax, A)
        ax.plot(*_g(t, y), color=col, lw=0.8)
        ax.set_title(rt(k, lg).split(' ')[0] + (f' ({u})' if u else '') if k == 'c_vibe' else rt(k, lg) + (f' ({u})' if u else ''), fontsize=7, loc='left', pad=2)
        ax.tick_params(labelsize=5.5); B._modes(ax, A, lg, label=False); B._crash(ax, A)
        ax.set_xlim(0, max(1.0, float(L.duration or 1)))
    fig.suptitle(rt('c_overview', lg), fontsize=10, x=0.02, ha='left')
    return B._png(fig)


# ------------------------------------------------------------------ stick hareketleri
def chart_sticks(A, lg):
    L = A.L; r = L.s('RCIN'); m = viz.rc_map(A)
    if not r.has(f"C{m['roll']}"): return None
    fig = B._fig(4.6)
    ax1 = fig.add_subplot(311); ax2 = fig.add_subplot(312, sharex=ax1); ax3 = fig.add_subplot(313, sharex=ax1)
    for ax in (ax1, ax2, ax3): _base(ax, A, lg)
    for k, col, lab in (('roll', C['blue'], ('Roll (sağ stick ↔)', 'Roll (right stick ↔)', 'الدوران (العصا اليمنى ↔)')),
                        ('pitch', C['orange'], ('Pitch (sağ stick ↕)', 'Pitch (right stick ↕)', 'الميلان (العصا اليمنى ↕)'))):
        ch = f"C{m[k]}"
        if r.has(ch): ax1.plot(*_g(r['t'], viz.stick_norm(A, m[k], r[ch])), color=col, lw=0.7, label=_t(lab, lg) + f' · RCIN.{ch}')
    for k, col, lab, cen in (('thr', C['red'], ('Gaz (sol stick ↕)', 'Throttle (left stick ↕)', 'الخانق (العصا اليسرى ↕)'), False),
                             ('yaw', C['purple'], ('Yaw (sol stick ↔)', 'Yaw (left stick ↔)', 'الانعراج (العصا اليسرى ↔)'), True)):
        ch = f"C{m[k]}"
        if r.has(ch): ax2.plot(*_g(r['t'], viz.stick_norm(A, m[k], r[ch], centred=cen)), color=col, lw=0.7, label=_t(lab, lg) + f' · RCIN.{ch}')
    if not viz.rc_active(A):
        ax1.text(0.5, 0.45, _t(('Logda kumanda sinyali yok (RCIN = 0): araç kumandasız, yer istasyonu / otomatik görevle uçmuş ya da alıcı bağlı değil.',
                               'No RC signal in the log (RCIN = 0): flown without a transmitter (ground station / auto mission) or receiver not connected.',
                               'لا توجد إشارة تحكم في السجل (RCIN = 0): طارت دون جهاز تحكم (محطة أرضية / مهمة آلية) أو المستقبل غير موصول.'), lg),
                 transform=ax1.transAxes, ha='center', va='center', fontsize=7, color=C['red'], bbox=dict(fc='white', alpha=0.9, lw=0.5, ec=C['red']))
    for ax in (ax1, ax2):
        ax.axhline(0, color='#9CA3AF', lw=0.5); ax.set_ylim(-110, 110); ax.set_ylabel('%', fontsize=7); _leg(ax, ncol=2)
    ax2.set_ylim(-110, 110)
    P = L.params
    fs = P.get('THR_FS_VALUE', P.get('FS_THR_VALUE'))
    if m.get('mode') and r.has(f"C{m['mode']}"):
        ch = f"C{m['mode']}"
        ax3.plot(*_g(r['t'], np.where(r[ch] < 800, np.nan, r[ch])), color=C['teal'], lw=0.8, label=_t(('Mod anahtarı', 'Mode switch', 'مفتاح الوضع'), lg) + f' · RCIN.{ch}')
        # 6 konumlu mod anahtarı sınırları ve konum adları
        edges = [1230, 1360, 1490, 1620, 1750]
        for e in edges: ax3.axhline(e, color='#D1D5DB', lw=0.5, ls=':')
        pre = 'FLTMODE' if A.vehicle in ('Plane', 'Copter') else 'MODE'
        for j, (lo, hi) in enumerate(zip([900] + edges, edges + [2100])):
            num = P.get(f'{pre}{j + 1}')
            if num is None: continue
            from . import knowledge as K
            ax3.text(1.002, (lo + hi) / 2, f'{j + 1}: {K.mode_name(A.vehicle, num)}', transform=ax3.get_yaxis_transform(), fontsize=5.2, va='center', color='#374151', clip_on=False)
        ax3.set_ylim(900, 2100)
    if fs and r.has(f"C{m['thr']}"):
        ch = f"C{m['thr']}"
        ax3.plot(*_g(r['t'], np.where(r[ch] < 800, np.nan, r[ch])), color=C['red'], lw=0.6, alpha=0.7, label=_t(('Gaz PWM', 'Throttle PWM', 'PWM الخانق'), lg))
        ax3.axhline(float(fs), color=C['red'], lw=0.8, ls='--')
        ax3.text(0.001, float(fs), ' failsafe ' + f'{fs:.0f}', transform=ax3.get_yaxis_transform(), fontsize=5.5, color=C['red'], va='bottom')
    ax3.set_ylabel('PWM', fontsize=7); _leg(ax3, ncol=3, loc='lower left')
    _end(ax1, A, lg, True); _end(ax2, A, lg, False); _end(ax3, A, lg, False)
    _title(ax1, 'c_sticks', lg)
    return B._png(fig)


# ------------------------------------------------------------------ görevli kanallar (servo)
def chart_rcou(A, lg):
    L = A.L; o = L.s('RCOU')
    if not o.has('C1'): return None
    roles = [r for r in viz.channel_roles(A, lg) if r['kind'] in ('ctrl', 'thr')]
    if not roles: roles = [{'ch': c, 'name': c, 'axes': '', 'kind': 'ctrl'} for c in ('C1', 'C2', 'C3', 'C4') if o.has(c)]
    groups = [('R', ('Roll', 'Roll', 'الدوران')), ('P', ('Pitch', 'Pitch', 'الميلان')), ('Y', ('Yaw', 'Yaw', 'الانعراج')), ('T', ('Gaz', 'Throttle', 'الخانق'))]
    used = [(g, n) for g, n in groups if any(g in r['axes'] for r in roles)]
    rest = [r for r in roles if not r['axes']]
    if rest: used.append(('', ('Diğer', 'Other', 'أخرى')))
    if not used: used = [('', ('Çıkışlar', 'Outputs', 'المخارج'))]
    fig = B._fig(1.35 * len(used) + 0.9)
    axs = []; pal = [C['blue'], C['orange'], C['green'], C['purple'], C['teal'], C['red'], C['amber'], C['gray']]
    ae = L.s('AETR')
    aef = {'R': 'Ail', 'P': 'Elev', 'Y': 'Rudd', 'T': 'Thr'}
    for i, (g, nm) in enumerate(used):
        ax = fig.add_subplot(len(used), 1, i + 1, sharex=axs[0] if axs else None); axs.append(ax); _base(ax, A, lg)
        rs = [r for r in roles if (g and g in r['axes']) or (not g and not r['axes'])]
        for j, r in enumerate(rs):
            if o.has(r['ch']): ax.plot(*_g(o['t'], o[r['ch']]), lw=0.6, color=pal[j % len(pal)], label=B.mshape(viz.role_label(r, lg, A), lg))
        if g and ae.has(aef[g]):    # otopilotun istediği (normalleştirilmiş) çıkış: sağ eksen
            a2 = ax.twinx(); a2.tick_params(labelsize=6)
            a2.plot(*_g(ae['t'], ae[aef[g]]), color='#111827', lw=0.5, alpha=0.45, label=f'AETR.{aef[g]}')
            a2.set_ylabel('AETR', fontsize=6); _both(ax, a2, ncol=3)
        else:
            _leg(ax, ncol=3)
        ax.set_ylabel(_t(nm, lg) + '\nPWM', fontsize=7)
    for i, ax in enumerate(axs): _end(ax, A, lg, i == 0)
    _title(axs[0], 'c_rcou', lg)
    return B._png(fig)


# ------------------------------------------------------------------ motorlar
def _layout_inset(fig, A, lg, ev, rect):
    ax = fig.add_axes(rect); ax.set_aspect('equal'); ax.axis('off')
    M = viz.motors(A, lg); bad = {e['m'] for e in ev.get('events', []) if e.get('root') or e['kind'] in ('stop', 'sat')}
    opp = (ev.get('opp') or {}).get('m')
    lift = [m for m in M if m['kind'] == 'lift' and m['angle'] is not None]
    # gövde
    ax.add_patch(B.matplotlib.patches.FancyBboxPatch((-0.18, -0.5), 0.36, 1.0, boxstyle='round,pad=0.02', fc='#E5E7EB', ec='#6B7280', lw=0.8))
    ax.annotate('', xy=(0, 0.78), xytext=(0, 0.45), arrowprops=dict(arrowstyle='->', color='#111827', lw=1.2))
    ax.text(0, 0.84, _t(('ÖN', 'FRONT', 'الأمام'), lg), ha='center', fontsize=6, fontweight='bold')
    if A.vehicle == 'Plane':
        ax.add_patch(B.matplotlib.patches.Rectangle((-1.05, -0.06), 2.1, 0.16, fc='#D1D5DB', ec='#6B7280', lw=0.6))
    seen = {}
    for m in lift:
        a = math.radians(m['angle']); k = round(m['angle'] % 360)
        r_ = 0.78 + 0.18 * seen.get(k, 0); seen[k] = seen.get(k, 0) + 1
        x, y = r_ * math.sin(a), r_ * math.cos(a)
        ax.plot([0, x * 0.8], [0, y * 0.8], color='#9CA3AF', lw=1.2, zorder=1)
        fc = C['red'] if m['m'] in bad else (C['amber'] if m['m'] == opp else '#DBEAFE')
        ax.add_patch(B.matplotlib.patches.Circle((x, y), 0.17, fc=fc, ec='#1F2937', lw=0.8, zorder=3))
        ax.text(x, y, str(m['m']), ha='center', va='center', fontsize=7, fontweight='bold', color='white' if m['m'] in bad else '#111827', zorder=4)
    for m in M:
        if m['kind'] == 'push':
            ax.add_patch(B.matplotlib.patches.FancyBboxPatch((-0.14, -0.86), 0.28, 0.2, boxstyle='round,pad=0.01', fc='#FEF3C7', ec='#92400E', lw=0.8))
            ax.text(0, -0.76, _t(('İtiş', 'Push', 'دفع'), lg), ha='center', va='center', fontsize=5.5)
    ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.05, 1.05)
    ax.text(0, -1.02, B.mshape(viz.frame_text(A, lg), lg), ha='center', va='top', fontsize=6, color='#374151')


def chart_motors(A, lg):
    L = A.L; o = L.s('RCOU')
    M = [m for m in viz.motors(A, lg) if o.has(m['ch'])]
    if not M: return None
    ev = viz.motor_events(A, lg)
    n = len(M)
    root = next((e for e in ev['events'] if e.get('root')), None) or next((e for e in ev['events'] if e['kind'] == 'stop'), None) \
        or (ev['events'][0] if ev['events'] else None)
    zoom = root is not None
    fig = B._fig(min(0.95 * n + 1.5 + (1.9 if zoom else 0), 11.5), 8.4)
    try: hi, lo = A._mot_limits()
    except Exception: hi, lo = None, None
    esc = [L.s(f'ESC[{i}]') for i in range(12)]
    axs = []
    left, right = 0.13, 0.80
    units = n + (2.7 if zoom else 0)
    fh = fig.get_figheight(); top, bot = 1 - 0.85 / fh, 0.35 / fh
    hh = (top - bot) / units
    for i, m in enumerate(M):
        y0 = top - (i + 1) * hh
        ax = fig.add_axes([left, y0 + hh * 0.08, right - left, hh * 0.82], sharex=axs[0] if axs else None); axs.append(ax)
        _base(ax, A, lg)
        mine = [e for e in ev['events'] if e['ch'] == m['ch']]
        col = C['red'] if any(e.get('root') or e['kind'] == 'stop' for e in mine) else (C['amber'] if mine else (C['orange'] if m['kind'] == 'push' else C['blue']))
        ax.plot(*_g(o['t'], o[m['ch']]), color=col, lw=0.7)
        if m['kind'] == 'lift' and hi:
            ax.axhline(hi, color=C['red'], lw=0.5, ls=':'); ax.axhline(lo, color=C['gray'], lw=0.5, ls=':')
        if m['kind'] == 'lift' and m['m'] and m['m'] - 1 < len(esc) and esc[m['m'] - 1].has('RPM'):
            e = esc[m['m'] - 1]; a2 = ax.twinx(); a2.tick_params(labelsize=5)
            a2.plot(*_g(e['t'], e['RPM']), color=C['green'], lw=0.5, alpha=0.6); a2.set_ylabel('RPM', fontsize=5)
        for e in mine:
            ax.axvspan(e['t'] - 0.3, max(e['t1'], e['t']) + 0.3, color=C['red'] if e['kind'] == 'stop' or e.get('root') else C['amber'], alpha=0.35, zorder=3)
            ax.annotate(B.mshape(viz.tx(viz.EV_TXT[e['kind']], lg), lg), (e['t'], 0.9), xycoords=('data', 'axes fraction'), fontsize=5.5,
                        color=C['red'], ha='right', va='top', fontweight='bold')
        rev = L.params.get(f"SERVO{m['ch'][1:]}_REVERSED") in (1, 1.0)
        ax.set_ylabel(B.mshape(m['name'].replace(' · ', '\n'), lg) + f"\n({m['ch']})" +
                      ('\n' + B.mshape(viz.tx(('[ters: düşük PWM = çok gaz]', '[reversed: low PWM = more]', '[معكوس]'), lg), lg) if rev else ''),
                      fontsize=6, rotation=0, ha='right', va='center', labelpad=6)
        ax.tick_params(labelsize=5.5)
        if i < n - 1: ax.tick_params(labelbottom=False)
    for i, ax in enumerate(axs): _end(ax, A, lg, i == 0)
    head = ('⚠ ' + viz.event_text(A, root, lg)) if root else ''
    axs[0].set_title(rt('c_motors', lg) + (('\n' + B.mshape(head, lg)) if head else ''), fontsize=8.5, loc='left', color=C['red'] if head else C['ink'], pad=18)
    if zoom:
        z0 = max(0.0, root['t'] - 15); z1 = min(float(L.duration or root['t'] + 10), max(root['t1'], root['t']) + 8)
        az = fig.add_axes([left, bot + hh * 0.2, right - left, hh * 1.75])
        B._style(az, lg); B._phases(az, A)
        k = (o['t'] >= z0) & (o['t'] <= z1)
        pal = [C['blue'], C['green'], C['purple'], C['teal'], C['gray'], '#0EA5E9', '#A16207', '#4D7C0F']
        bad = {e['ch'] for e in ev['events'] if e.get('root') or e['kind'] == 'stop'}
        opp = (ev.get('opp') or {}).get('ch')
        j = 0
        for m in M:
            if m['kind'] != 'lift': continue
            if m['ch'] in bad: c, lw = C['red'], 1.6
            elif m['ch'] == opp: c, lw = C['amber'], 1.3
            else: c, lw = pal[j % len(pal)], 0.8; j += 1
            az.plot(o['t'][k], o[m['ch']][k], color=c, lw=lw, label=B.mshape(m['name'], lg) + f" ({m['ch']})")
        if hi: az.axhline(hi, color=C['red'], lw=0.5, ls=':')
        az.axvline(root['t'], color=C['red'], lw=1, ls='--')
        B._modes(az, A, lg, label=False); B._crash(az, A); az.set_xlim(z0, z1)
        az.set_title(B.mshape(viz.tx(('Olay anı yakından (tüm kaldırma motorları)', 'Close-up of the event (all lift motors)', 'لقطة مقرّبة للحدث (كل محركات الرفع)'), lg), lg),
                     fontsize=7.5, loc='left', color=C['red'])
        az.set_ylabel('PWM', fontsize=7); az.tick_params(labelsize=6)
        _leg(az, ncol=4, loc='lower left')
    _layout_inset(fig, A, lg, ev, [0.81, 0.45, 0.18, 0.36])
    if getattr(B._TL, 'fig', False): return fig
    import io
    b = io.BytesIO(); fig.savefig(b, format='png', dpi=150); return b.getvalue()


# ------------------------------------------------------------------ hız ve rüzgâr
def chart_speed(A, lg):
    L = A.L; g = L.s('GPS')
    a = _first(L, 'ARSP', 'ARSP[0]')
    if not g.has('Spd') and not a.has('Airspeed'): return None
    x2 = _first(L, 'XKF2', 'XKF2[0]', 'NKF2')
    wind = x2.has('VWN') and x2.has('VWE')
    fig = B._fig(4.0 if wind else 2.9)
    ax = fig.add_subplot(211 if wind else 111); _base(ax, A, lg)
    if a.has('Airspeed'): ax.plot(*_g(a['t'], a['Airspeed']), color=C['green'], lw=0.8, label=rt('l_as', lg) + ' · ARSP.Airspeed')
    if g.has('Spd'): ax.plot(*_g(g['t'], g['Spd']), color=C['orange'], lw=0.8, label=rt('l_gs', lg) + ' · GPS.Spd')
    te = L.s('TECS')
    if te.has('spdem'): ax.plot(*_g(te['t'], te['spdem']), color='#111827', lw=0.6, ls='--', alpha=0.7, label=_t(('Hedef hız', 'Target speed', 'السرعة المستهدفة'), lg) + ' · TECS.spdem')
    P = L.params
    for k, col in (('AIRSPEED_MIN', C['red']), ('ARSPD_FBW_MIN', C['red']), ('AIRSPEED_MAX', C['amber']), ('ARSPD_FBW_MAX', C['amber']), ('AIRSPEED_CRUISE', C['blue'])):
        if P.get(k) and A.vehicle == 'Plane':
            ax.axhline(float(P[k]) / (100 if k.endswith('CRUISE') and P[k] > 200 else 1), color=col, lw=0.6, ls=':')
    ax.set_ylabel(rt('ax_spd', lg), fontsize=8); _leg(ax, ncol=3, loc='lower left')
    _end(ax, A, lg, True)
    if wind:
        a2 = fig.add_subplot(212, sharex=ax); _base(a2, A, lg)
        ws = np.hypot(x2['VWN'], x2['VWE']); wd = (np.degrees(np.arctan2(-x2['VWE'], -x2['VWN'])) + 360) % 360
        a2.plot(*_g(x2['t'], ws), color=C['teal'], lw=0.9, label=_t(('Rüzgâr hızı', 'Wind speed', 'سرعة الرياح'), lg))
        a2.set_ylabel('m/s', fontsize=7)
        a3 = a2.twinx(); a3.tick_params(labelsize=6); a3.scatter(x2['t'][::3], wd[::3], s=0.6, color=C['purple'], label=_t(('Geldiği yön (°)', 'From direction (°)', 'الاتجاه القادم منه (°)'), lg))
        a3.set_ylim(0, 360); a3.set_yticks([0, 90, 180, 270, 360]); a3.set_ylabel('°', fontsize=7)
        _both(a2, a3, ncol=2); _end(a2, A, lg, False)
    _title(ax, 'c_speed', lg)
    return B._png(fig)


# ------------------------------------------------------------------ irtifa/hız kontrolü (TECS / Copter CTUN)
def chart_tecs(A, lg):
    L = A.L; te = L.s('TECS'); ct = L.s('CTUN'); qt = L.s('QTUN')
    fig = B._fig(4.2)
    if te.has('hdem'):
        ax1 = fig.add_subplot(311); ax2 = fig.add_subplot(312, sharex=ax1); ax3 = fig.add_subplot(313, sharex=ax1)
        for ax in (ax1, ax2, ax3): _base(ax, A, lg)
        ax1.plot(*_g(te['t'], te['hdem']), color='#111827', lw=0.6, ls='--', label=_t(('İstenen irtifa', 'Demanded height', 'الارتفاع المطلوب'), lg) + ' · TECS.hdem')
        ax1.plot(*_g(te['t'], te['h']), color=C['blue'], lw=0.8, label=_t(('Gerçek irtifa', 'Height', 'الارتفاع'), lg) + ' · TECS.h')
        ax1.set_ylabel('m', fontsize=7); _leg(ax1, ncol=2, loc='lower left')
        if te.has('spdem'):
            ax2.plot(*_g(te['t'], te['spdem']), color='#111827', lw=0.6, ls='--', label=_t(('İstenen hız', 'Demanded speed', 'السرعة المطلوبة'), lg) + ' · TECS.spdem')
            ax2.plot(*_g(te['t'], te['sp']), color=C['green'], lw=0.8, label=_t(('Hız', 'Speed', 'السرعة'), lg) + ' · TECS.sp')
        ax2.set_ylabel('m/s', fontsize=7); _leg(ax2, ncol=2, loc='lower left')
        if te.has('th'): ax3.plot(*_g(te['t'], te['th'] * (100 if np.nanmax(np.abs(te['th'])) <= 1.5 else 1)), color=C['red'], lw=0.7, label=_t(('Gaz isteği %', 'Throttle demand %', 'طلب الخانق %'), lg) + ' · TECS.th')
        if te.has('ph'):
            a4 = ax3.twinx(); a4.tick_params(labelsize=6)
            a4.plot(*_g(te['t'], np.degrees(te['ph']) if np.nanmax(np.abs(te['ph'])) < 2 else te['ph']), color=C['purple'], lw=0.6, label=_t(('Yunuslama isteği °', 'Pitch demand °', 'طلب الميلان °'), lg) + ' · TECS.ph')
            _both(ax3, a4, ncol=2, loc='lower left')
        else: _leg(ax3)
        axs = (ax1, ax2, ax3)
    else:
        src = qt if qt.has('DAlt') else ct
        if not src.has('Alt'): return None
        ax1 = fig.add_subplot(211); ax2 = fig.add_subplot(212, sharex=ax1)
        for ax in (ax1, ax2): _base(ax, A, lg)
        nm = 'QTUN' if src is qt else 'CTUN'
        if src.has('DAlt'): ax1.plot(*_g(src['t'], src['DAlt']), color='#111827', lw=0.6, ls='--', label=f'{nm}.DAlt')
        ax1.plot(*_g(src['t'], src['Alt']), color=C['blue'], lw=0.8, label=f'{nm}.Alt')
        if src.has('BAlt'): ax1.plot(*_g(src['t'], src['BAlt']), color=C['teal'], lw=0.5, alpha=0.7, label=f'{nm}.BAlt')
        ax1.set_ylabel('m', fontsize=7); _leg(ax1, ncol=3, loc='lower left')
        if src.has('DCRt'): ax2.plot(*_g(src['t'], src['DCRt'] / (100 if np.nanmax(np.abs(src['DCRt'])) > 60 else 1)), color='#111827', lw=0.6, ls='--', label=f'{nm}.DCRt')
        if src.has('CRt'): ax2.plot(*_g(src['t'], src['CRt'] / (100 if np.nanmax(np.abs(src['CRt'])) > 60 else 1)), color=C['green'], lw=0.7, label=f'{nm}.CRt')
        ax2.set_ylabel('m/s', fontsize=7); _leg(ax2, ncol=2, loc='lower left')
        axs = (ax1, ax2)
    for i, ax in enumerate(axs): _end(ax, A, lg, i == 0)
    _title(axs[0], 'c_tecs', lg)
    return B._png(fig)


# ------------------------------------------------------------------ PID
def chart_pid(A, lg):
    L = A.L
    rows = [(k, L.s(k)) for k in ('PIDR', 'PIDP', 'PIDY') if L.s(k).has('Tar')]
    q = [(k, L.s(k)) for k in ('PIQR', 'PIQP', 'PIQY') if L.s(k).has('Tar')]
    rows += q
    if not rows: return None
    fig = B._fig(1.3 * len(rows) + 0.9)
    axs = []
    nm = {'PIDR': 'Roll', 'PIDP': 'Pitch', 'PIDY': 'Yaw', 'PIQR': 'VTOL Roll', 'PIQP': 'VTOL Pitch', 'PIQY': 'VTOL Yaw'}
    for i, (k, s) in enumerate(rows):
        ax = fig.add_subplot(len(rows), 1, i + 1, sharex=axs[0] if axs else None); axs.append(ax); _base(ax, A, lg)
        ax.plot(*_g(s['t'], s['Tar']), color='#111827', lw=0.55, ls='--', label=f'{k}.Tar')
        ax.plot(*_g(s['t'], s['Act']), color=C['blue'], lw=0.7, label=f'{k}.Act')
        a2 = ax.twinx(); a2.tick_params(labelsize=5)
        for f, c in (('P', C['green']), ('I', C['orange']), ('D', C['purple']), ('FF', C['teal'])):
            if s.has(f): a2.plot(*_g(s['t'], s[f]), color=c, lw=0.45, alpha=0.75, label=f'{k}.{f}')
        ax.set_ylabel(nm[k] + '\n°/s', fontsize=7); a2.set_ylabel('P/I/D/FF', fontsize=5.5)
        _both(ax, a2, ncol=6)
    for i, ax in enumerate(axs): _end(ax, A, lg, i == 0)
    _title(axs[0], 'c_pid', lg)
    return B._png(fig)


# ------------------------------------------------------------------ navigasyon
def chart_nav(A, lg):
    L = A.L; nt = L.s('NTUN')
    dist = next((f for f in ('Dist', 'WpDist', 'WPDst') if nt.has(f)), None)
    if not dist: return None
    fig = B._fig(3.4)
    ax1 = fig.add_subplot(211); ax2 = fig.add_subplot(212, sharex=ax1)
    for ax in (ax1, ax2): _base(ax, A, lg)
    ax1.plot(*_g(nt['t'], nt[dist]), color=C['blue'], lw=0.8, label=_t(('Hedefe uzaklık', 'Distance to target', 'المسافة إلى الهدف'), lg) + f' · NTUN.{dist}')
    ax1.set_ylabel('m', fontsize=7); _leg(ax1, ncol=2)
    for f, c, lab in (('XT', C['orange'], ('Rota sapması', 'Cross-track error', 'خطأ المسار العرضي')), ('AltE', C['purple'], ('İrtifa hatası', 'Altitude error', 'خطأ الارتفاع')),
                      ('AsE', C['green'], ('Hız hatası', 'Airspeed error', 'خطأ السرعة'))):
        if nt.has(f): ax2.plot(*_g(nt['t'], nt[f]), color=c, lw=0.7, label=_t(lab, lg) + f' · NTUN.{f}')
    ax2.axhline(0, color='#9CA3AF', lw=0.5); ax2.set_ylabel('m · m/s', fontsize=7); _leg(ax2, ncol=3, loc='lower left')
    cm = L.s('CMD')
    if cm.has('CNum'):
        from matplotlib.transforms import blended_transform_factory as btf
        for ax in (ax1, ax2):
            tr = btf(ax.transData, ax.transAxes)
            for t, n in zip(cm['t'], cm['CNum']):
                ax.axvline(t, color='#0F172A', lw=0.4, ls=':', alpha=0.6)
                if ax is ax2: ax.text(t, 0.04, f'WP{int(n)}', transform=tr, fontsize=5, rotation=90, va='bottom', ha='right', color='#0F172A')
    _end(ax1, A, lg, True); _end(ax2, A, lg, False)
    _title(ax1, 'c_nav', lg)
    return B._png(fig)


# ------------------------------------------------------------------ GPS (uydu + doğruluk)
def chart_gps(A, lg):
    L = A.L; g = L.s('GPS')
    if not g.has('NSats'): return None
    ga = _first(L, 'GPA', 'GPA[0]')
    acc = ga.has('HAcc')
    fig = B._fig(3.9 if acc else 2.8)
    ax = fig.add_subplot(211 if acc else 111); _base(ax, A, lg)
    ax.plot(*_g(g['t'], g['NSats']), color=C['blue'], lw=1, label=rt('ax_sats', lg) + ' · GPS.NSats')
    ax.axhline(6, color=C['red'], lw=0.6, ls=':'); ax.axhline(10, color=C['green'], lw=0.6, ls=':')
    ax.set_ylabel(rt('ax_sats', lg), fontsize=8); ax.set_ylim(0, max(20, np.nanmax(g['NSats']) + 2))
    if g.has('HDop'):
        a2 = ax.twinx(); a2.tick_params(labelsize=7)
        a2.plot(*_g(g['t'], np.clip(g['HDop'], 0, 10)), color=C['orange'], lw=0.8, label='HDOP · GPS.HDop'); a2.axhline(2, color=C['orange'], lw=0.6, ls=':')
        a2.set_ylabel('HDOP', fontsize=8); _both(ax, a2, ncol=2, loc='lower left')
    else: _leg(ax)
    gl = [t for t, s, c in L.errors if s == 11 and c == 2]
    for t in gl: ax.axvline(t, color=C['red'], lw=1.2, alpha=0.8)
    _end(ax, A, lg, True)
    if acc:
        b = fig.add_subplot(212, sharex=ax); _base(b, A, lg)
        for f, c in (('HAcc', C['blue']), ('VAcc', C['purple']), ('SAcc', C['green'])):
            if ga.has(f): b.plot(*_g(ga['t'], np.clip(ga[f], 0, 30)), color=c, lw=0.7, label=f'GPA.{f}')
        b.set_ylabel(_t(('Doğruluk (m, m/s)', 'Accuracy (m, m/s)', 'الدقة (م، م/ث)'), lg), fontsize=7); _leg(b, ncol=3); _end(b, A, lg, False)
    _title(ax, 'c_gps', lg)
    return B._png(fig)


# ------------------------------------------------------------------ titreşim (zaman) — charts.chart_vibe'e mod etiketi
def chart_vibe(A, lg):
    v = A.L.s('VIBE')
    if not v.has('VibeZ'): return None
    fig = B._fig(2.9); ax = fig.add_subplot(111); _base(ax, A, lg)
    for f, c in (('VibeX', C['blue']), ('VibeY', C['green']), ('VibeZ', C['orange'])):
        if v.has(f): ax.plot(*_g(v['t'], v[f]), color=c, lw=0.7, label=f'VIBE.{f}')
    ax.axhline(30, color=C['amber'], lw=0.8, ls='--'); ax.axhline(60, color=C['red'], lw=0.8, ls='--')
    ax.set_ylabel(rt('ax_vibe', lg), fontsize=8)
    ck = next((k for k in ('Clip', 'Clip0') if v.has(k)), None)
    if ck:
        a2 = ax.twinx(); a2.tick_params(labelsize=7); a2.plot(*_g(v['t'], v[ck]), color=C['red'], lw=0.8, alpha=0.6, label=rt('l_clip', lg) + f' · VIBE.{ck}')
        a2.set_ylabel(rt('l_clip', lg), fontsize=8); _both(ax, a2, ncol=4)
    else: _leg(ax, ncol=3)
    _end(ax, A, lg, True); _title(ax, 'c_vibe', lg)
    return B._png(fig)


# ------------------------------------------------------------------ titreşim spektrumu (FFT)
def _rate(s):
    t = s['t']
    if len(t) < 20: return 0.0
    d = np.diff(t); d = d[d > 0]
    return float(1.0 / np.median(d)) if len(d) else 0.0


def chart_fft(A, lg):
    L = A.L
    im = _first(L, 'IMU', 'IMU[0]')
    if not im.has('AccZ'): return None
    hz = _rate(im)
    m = A.in_flight(im['t']) if A.flights else np.ones(len(im['t']), bool)
    fig = B._fig(3.0); ax = fig.add_subplot(111)
    ax.grid(True, color=C['grid'], lw=0.6); ax.tick_params(labelsize=7)
    for s_ in ('top', 'right'): ax.spines[s_].set_visible(False)
    P = L.params
    note = None
    if hz < 40 or m.sum() < 64:
        note = _t((f'IMU kayıt hızı {hz:.0f} Hz: spektrum için yetersiz. Ayrıntılı analiz için INS_LOG_BAT_MASK=1 (toplu örnekleme) ya da INS_FAST_SAMPLE + LOG_BITMASK ile IMU_RAW açın.',
                   f'IMU log rate {hz:.0f} Hz: too low for a spectrum. Enable batch sampling (INS_LOG_BAT_MASK=1) or raw IMU logging for detailed analysis.',
                   f'معدل تسجيل IMU {hz:.0f} هرتز: غير كافٍ للطيف. فعّل أخذ العينات الدفعي (INS_LOG_BAT_MASK=1) أو تسجيل IMU الخام.'), lg)
    if hz >= 10 and m.sum() >= 64:
        n = int(min(m.sum(), hz * 4)); n = 1 << int(np.log2(max(n, 64)))
        w = np.hanning(n); fr = np.fft.rfftfreq(n, 1.0 / hz)
        for f, c in (('AccX', C['blue']), ('AccY', C['green']), ('AccZ', C['orange'])):
            if not im.has(f): continue
            x = im[f][m] - np.nanmean(im[f][m]); x = np.nan_to_num(x)
            segs = [x[j:j + n] for j in range(0, len(x) - n + 1, max(1, n // 2))][:300]
            if not segs: continue
            ps = np.mean([np.abs(np.fft.rfft(s * w)) ** 2 for s in segs], axis=0)
            ax.semilogy(fr[1:], ps[1:] + 1e-12, color=c, lw=0.8, label=f'IMU.{f}')
        if P.get('INS_HNTCH_ENABLE') and P.get('INS_HNTCH_FREQ'):
            nf = float(P['INS_HNTCH_FREQ']); bw = float(P.get('INS_HNTCH_BW', nf / 2) or nf / 2)
            ax.axvspan(nf - bw / 2, nf + bw / 2, color=C['purple'], alpha=0.12)
            ax.axvline(nf, color=C['purple'], lw=1, ls='--', label=_t(('Çentik filtresi', 'Notch filter', 'مرشح الشق'), lg) + f' {nf:.0f} Hz')
        vp = getattr(A, 'vib_peak', None)
        if vp: ax.axvline(vp['f'], color=C['red'], lw=0.8, ls=':', label=_t(('Tepe', 'Peak', 'الذروة'), lg) + f" {vp['f']} Hz")
        ax.set_xlim(0, hz / 2)
        _leg(ax, ncol=3, loc='upper right')
    ax.set_xlabel('Hz', fontsize=8); ax.set_ylabel(_t(('Güç (log)', 'Power (log)', 'القدرة (لوغاريتمي)'), lg), fontsize=8)
    if note: ax.text(0.02, 0.5 if hz < 10 else 0.08, note, transform=ax.transAxes, fontsize=6.5, color=C['red'], wrap=True, va='center' if hz < 10 else 'bottom')
    ax.set_title(rt('c_fft', lg), fontsize=9, loc='left')
    return B._png(fig)


# ------------------------------------------------------------------ IMU'lar ve irtifa kaynakları
def chart_imu(A, lg):
    L = A.L
    ims = [(i, L.s(f'IMU[{i}]')) for i in range(3) if L.s(f'IMU[{i}]').has('AccZ')]
    if not ims and L.s('IMU').has('AccZ'): ims = [(0, L.s('IMU'))]
    br = _first(L, 'BARO', 'BARO[0]'); g = L.s('GPS')
    if not ims and not br.has('Alt'): return None
    fig = B._fig(4.0)
    ax1 = fig.add_subplot(311); ax2 = fig.add_subplot(312, sharex=ax1); ax3 = fig.add_subplot(313, sharex=ax1)
    for ax in (ax1, ax2, ax3): _base(ax, A, lg)
    pal = [C['blue'], C['orange'], C['green']]
    for j, (i, s) in enumerate(ims):
        ax1.plot(*_g(s['t'], s['AccZ']), color=pal[j], lw=0.5, alpha=0.8, label=f'IMU[{i}].AccZ')
        if s.has('GyrX'): ax2.plot(*_g(s['t'], np.degrees(s['GyrX'])), color=pal[j], lw=0.5, alpha=0.8, label=f'IMU[{i}].GyrX')
    ax1.set_ylabel('m/s²', fontsize=7); ax2.set_ylabel('°/s', fontsize=7); _leg(ax1, ncol=3); _leg(ax2, ncol=3)
    if br.has('Alt'):
        ax3.plot(*_g(br['t'], br['Alt']), color=C['teal'], lw=0.8, label=_t(('Barometre', 'Barometer', 'البارومتر'), lg) + ' · BARO.Alt')
    if g.has('Alt') and br.has('Alt') and A.flights:
        t0 = A.flights[0][0]
        gb = np.interp(t0, g['t'], g['Alt']) - np.interp(t0, br['t'], br['Alt'])
        ax3.plot(*_g(g['t'], g['Alt'] - gb), color=C['orange'], lw=0.7, label=_t(('GPS (kalkışa göre)', 'GPS (rel. takeoff)', 'GPS (نسبةً للإقلاع)'), lg) + ' · GPS.Alt')
    ax3.set_ylabel('m', fontsize=7); _leg(ax3, ncol=2)
    for i, ax in enumerate((ax1, ax2, ax3)): _end(ax, A, lg, i == 0)
    _title(ax1, 'c_imu', lg)
    return B._png(fig)


# ------------------------------------------------------------------ güç
def chart_bat(A, lg):
    L = A.L; b = L.s('BAT')
    if not b.has('Volt'): return None
    cells = (A.health.get('power') or {}).get('metrics', {}).get('cells') or 0
    fig = B._fig(4.0)
    ax = fig.add_subplot(211); _base(ax, A, lg)
    vv = np.where(b['Volt'] > 1, b['Volt'], np.nan)
    ax.plot(*_g(b['t'], vv), color=C['blue'], lw=1, label=rt('l_volt', lg) + ' · BAT.Volt'); ax.set_ylabel(rt('ax_volt', lg), fontsize=8)
    P = L.params
    for k, c in (('BATT_LOW_VOLT', C['amber']), ('BATT_CRT_VOLT', C['red'])):
        if P.get(k): ax.axhline(P[k], color=c, lw=0.7, ls='--')
    if cells and cells > 1:
        sec = ax.secondary_yaxis('right', functions=(lambda x: x / cells, lambda x: x * cells))
        sec.set_ylabel(_t((f'Hücre başına V ({cells}S)', f'V per cell ({cells}S)', f'فولت لكل خلية ({cells}S)'), lg), fontsize=7); sec.tick_params(labelsize=6)
    _leg(ax, ncol=2, loc='lower left'); _end(ax, A, lg, True)
    a2 = fig.add_subplot(212, sharex=ax); _base(a2, A, lg)
    has_c = b.has('Curr') and np.nanmax(np.abs(b['Curr'])) > 0.5
    if has_c: a2.plot(*_g(b['t'], b['Curr']), color=C['orange'], lw=0.6, label=rt('l_curr', lg) + ' · BAT.Curr')
    a2.set_ylabel(rt('ax_curr', lg), fontsize=7)
    a3 = a2.twinx(); a3.tick_params(labelsize=6)
    cap = float(P.get('BATT_CAPACITY', 0) or 0)
    if b.has('CurrTot') and np.nanmax(b['CurrTot']) > 1:
        a3.plot(*_g(b['t'], b['CurrTot']), color=C['red'], lw=0.9, label=_t(('Harcanan mAh', 'Used mAh', 'المستهلك mAh'), lg) + ' · BAT.CurrTot')
        if cap: a3.axhline(cap, color=C['red'], lw=0.6, ls=':'); a3.axhline(cap * 0.8, color=C['amber'], lw=0.6, ls=':')
        a3.set_ylabel('mAh', fontsize=7)
        if has_c and cap and A.flights:
            tl = A.flights[-1][1]; used = float(np.interp(tl, b['t'], b['CurrTot']))
            win = (b['t'] > tl - 60) & (b['t'] <= tl); cur = float(np.nanmean(b['Curr'][win])) if win.any() else 0
            if cur > 0.5:
                rem = max(0.0, (cap * 0.8 - used)) / (cur * 1000 / 60)
                a3.text(0.99, 0.92, _t((f'Kalan (%%80 kural): ~{rem:.0f} dk', f'Remaining (80%% rule): ~{rem:.0f} min', f'المتبقي (قاعدة 80%%): ~{rem:.0f} دقيقة'), lg).replace('%%', '%'),
                        transform=a3.transAxes, ha='right', va='top', fontsize=6, color=C['red'], bbox=dict(fc='white', alpha=0.8, lw=0))
    pw = L.s('POWR')
    if pw.has('Vcc'):
        a3.plot([], []); a2.plot([], [])
    _both(a2, a3, ncol=3, loc='upper left'); _end(a2, A, lg, False)
    _title(ax, 'c_bat', lg)
    return B._png(fig)


# ------------------------------------------------------------------ ESC
def chart_esc(A, lg):
    L = A.L
    E = [(i, L.s(f'ESC[{i}]')) for i in range(12) if L.s(f'ESC[{i}]').has('RPM')]
    if not E and L.s('ESC').has('RPM'): E = [(0, L.s('ESC'))]
    if not E: return None
    M = {m['m']: m['name'] for m in viz.motors(A, lg) if m['m']}
    fig = B._fig(4.0)
    ax1 = fig.add_subplot(311); ax2 = fig.add_subplot(312, sharex=ax1); ax3 = fig.add_subplot(313, sharex=ax1)
    for ax in (ax1, ax2, ax3): _base(ax, A, lg)
    pal = [C['blue'], C['orange'], C['green'], C['purple'], C['teal'], C['red'], C['amber'], C['gray']]
    for j, (i, e) in enumerate(E):
        nm = M.get(i + 1, f'ESC{i + 1}').split(' · ')[-1]
        ax1.plot(*_g(e['t'], e['RPM']), color=pal[j % 8], lw=0.5, label=f'{i + 1} {nm}')
        if e.has('Temp'): ax2.plot(*_g(e['t'], e['Temp']), color=pal[j % 8], lw=0.6)
        if e.has('Curr'): ax3.plot(*_g(e['t'], e['Curr']), color=pal[j % 8], lw=0.5)
    ax1.set_ylabel('RPM', fontsize=7); ax2.set_ylabel('°C', fontsize=7); ax3.set_ylabel('A', fontsize=7)
    B.mshape('', lg); _leg(ax1, ncol=4)
    for i, ax in enumerate((ax1, ax2, ax3)): _end(ax, A, lg, i == 0)
    _title(ax1, 'c_esc', lg)
    return B._png(fig)


# ------------------------------------------------------------------ EKF
def chart_ekf(A, lg):
    L = A.L
    x = _first(L, 'XKF4', 'XKF4[0]', 'NKF4')
    if not x.has('SV'): return None
    x3 = _first(L, 'XKF3', 'XKF3[0]', 'NKF3')
    inn = x3.has('IVN')
    fig = B._fig(4.0 if inn else 2.8)
    ax = fig.add_subplot(211 if inn else 111); _base(ax, A, lg)
    for f, c in (('SV', C['blue']), ('SP', C['green']), ('SH', C['orange']), ('SM', C['purple'])):
        if x.has(f): ax.plot(*_g(x['t'], x[f]), lw=0.8, color=c, label=f'XKF4.{f}')
    ax.axhline(0.8, color=C['amber'], lw=0.7, ls='--'); ax.axhline(1.0, color=C['red'], lw=0.7, ls='--')
    ax.set_ylabel(rt('ax_ratio', lg), fontsize=8); _leg(ax, ncol=4)
    from matplotlib.transforms import blended_transform_factory as btf
    tr = btf(ax.transData, ax.transAxes)
    for t, m in L.texts:
        ml = m.lower()
        if ('lane switch' in ml) or ('primary changed' in ml) or ('ekf' in ml and 'switch' in ml):
            ax.axvline(t, color=C['red'], lw=1, ls='-.'); ax.text(t, 0.5, ' ' + m[:28], transform=tr, rotation=90, fontsize=5, color=C['red'], va='center')
    _end(ax, A, lg, True)
    if inn:
        b = fig.add_subplot(212, sharex=ax); _base(b, A, lg)
        for f, c in (('IVN', C['blue']), ('IVE', C['teal']), ('IPN', C['green']), ('IPE', C['amber']), ('IPD', C['orange']), ('IMX', C['purple'])):
            if x3.has(f): b.plot(*_g(x3['t'], x3[f]), lw=0.55, color=c, label=f'XKF3.{f}')
        b.set_ylabel(_t(('Yenilik (ölçüm−tahmin)', 'Innovation (meas−pred)', 'الابتكار (القياس−التنبؤ)'), lg), fontsize=6.5)
        b.axhline(0, color='#9CA3AF', lw=0.5); _leg(b, ncol=6); _end(b, A, lg, False)
    _title(ax, 'c_ekf', lg)
    return B._png(fig)


# ------------------------------------------------------------------ pusula
def chart_mag(A, lg):
    L = A.L
    ms = [(i, L.s(f'MAG[{i}]')) for i in range(3) if L.s(f'MAG[{i}]').has('MagX')]
    if not ms and L.s('MAG').has('MagX'): ms = [(0, L.s('MAG'))]
    if not ms: return None
    fig = B._fig(3.0); ax = fig.add_subplot(111); _base(ax, A, lg)
    pal = [C['teal'], C['purple'], C['gray']]
    for j, (i, m) in enumerate(ms):
        fm = np.sqrt(m['MagX'] ** 2 + m['MagY'] ** 2 + m['MagZ'] ** 2)
        ax.plot(*_g(m['t'], fm), color=pal[j], lw=0.8, label=f'|MAG[{i}]|')
    ax.set_ylabel(rt('ax_mag', lg), fontsize=8)
    b = L.s('BAT'); c = L.s('CTUN')
    a2 = ax.twinx(); a2.tick_params(labelsize=7)
    if b.has('Curr') and np.nanmax(np.abs(b['Curr'])) > 0.5:
        a2.plot(*_g(b['t'], b['Curr']), color=C['red'], lw=0.5, alpha=0.55, label=rt('l_curr', lg) + ' · BAT.Curr'); a2.set_ylabel(rt('ax_curr', lg), fontsize=7)
    elif c.has('ThO'):
        a2.plot(*_g(c['t'], c['ThO']), color=C['red'], lw=0.5, alpha=0.55, label=rt('l_thr', lg) + ' · CTUN.ThO'); a2.set_ylabel(rt('ax_thr', lg), fontsize=7)
    _both(ax, a2, ncol=4); _end(ax, A, lg, True)
    _title(ax, 'c_mag', lg)
    return B._png(fig)


# ------------------------------------------------------------------ olaylar ve modlar (mod şeridi + olaylar)
def chart_timeline(A, lg):
    from .texts import render
    segs = viz.segments(A, lg)
    E = [e for e in A.events if e['cat'] in ('err', 'flight', 'ev', 'msg') and (e['cat'] != 'msg' or e['sev'] > 0)]
    fig = B._fig(3.6)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.1, 2.0], hspace=0.08)
    a1 = fig.add_subplot(gs[0]); a2 = fig.add_subplot(gs[1], sharex=a1)
    dur = max(1.0, float(A.L.duration or 1))
    # mod şeridi: her bölüm kendi renginde, adı ve başlangıç saati
    for s in segs:
        a1.barh(0, s['t1'] - s['t0'], left=s['t0'], height=0.8, color=s['col'], edgecolor='white', lw=0.6)
        if (s['t1'] - s['t0']) / dur > 0.03:
            c = viz.clock(A, s['t0'], sec=False)
            a1.text(s['t0'] + dur * 0.003, 0.12, s['name'], fontsize=6, color='white', fontweight='bold', va='center', clip_on=True)
            a1.text(s['t0'] + dur * 0.003, -0.2, fmt_t(s['t0'])[:-2] + (f' · {c}' if c else ''), fontsize=5, color='white', va='center', clip_on=True)
        if s['fs']:
            a1.plot([s['t0']], [0.55], marker='v', color=C['red'], ms=6, mec='white')
    a1.set_yticks([0]); a1.set_yticklabels([rt('cat_mode', lg)], fontsize=7); a1.set_ylim(-0.6, 0.75)
    for sp in ('top', 'right'): a1.spines[sp].set_visible(False)
    a1.tick_params(labelbottom=False, labelsize=6)
    B._clock_axis(a1, A)
    B._style(a2, lg); B._phases(a2, A)
    rows = {'flight': 3, 'ev': 2, 'err': 1, 'msg': 0}
    cols = {0: C['blue'], 1: C['amber'], 2: C['red']}
    for e in E:
        a2.plot(e['t'], rows.get(e['cat'], 0), 'o', color=cols[e['sev']], ms=4.5, mec='white', mew=0.4)
    for s in segs[1:]:
        a2.axvline(s['t0'], color=C['red'] if s['fs'] else s['col'], lw=0.7, ls='--', alpha=0.7)
    a2.set_yticks(list(rows.values())); a2.set_yticklabels([rt('cat_' + k, lg) for k in rows], fontsize=7)
    a2.set_ylim(-0.7, 3.7); a2.set_xlim(0, dur); B._crash(a2, A)
    a1.set_title(rt('c_timeline', lg), fontsize=9, loc='left')
    return B._png(fig)


# ------------------------------------------------------------------ irtifa (mod etiketli)
def chart_alt(A, lg):
    return B.chart_alt(A, lg)


def chart_att(A, lg):
    a = A.L.s('ATT')
    if not a.has('Roll'): return None
    fig = B._fig(4.0)
    rows = [('Roll', 'l_roll', C['blue']), ('Pitch', 'l_pitch', C['orange'])] + ([('Yaw', None, C['purple'])] if a.has('Yaw') else [])
    axs = []
    for i, (f, lab, col) in enumerate(rows):
        ax = fig.add_subplot(len(rows), 1, i + 1, sharex=axs[0] if axs else None); axs.append(ax); _base(ax, A, lg)
        nm = rt(lab, lg) if lab else 'Yaw'
        if a.has('Des' + f): ax.plot(*_g(a['t'], a['Des' + f]), color='#111827', lw=0.55, ls='--', label=f"{nm} ({rt('l_des', lg)}) · ATT.Des{f}")
        ax.plot(*_g(a['t'], a[f]), color=col, lw=0.75, label=f'{nm} · ATT.{f}')
        ax.set_ylabel(rt('ax_deg', lg), fontsize=7); _leg(ax, ncol=2)
    for i, ax in enumerate(axs): _end(ax, A, lg, i == 0)
    _title(axs[0], 'c_att', lg)
    return B._png(fig)


ALL = [('c_overview', chart_overview), ('c_alt', chart_alt), ('c_att', chart_att), ('c_sticks', chart_sticks), ('c_rcou', chart_rcou),
       ('c_motors', chart_motors), ('c_speed', chart_speed), ('c_tecs', chart_tecs), ('c_pid', chart_pid), ('c_nav', chart_nav),
       ('c_gps', chart_gps), ('c_vibe', chart_vibe), ('c_fft', chart_fft), ('c_imu', chart_imu), ('c_bat', chart_bat), ('c_esc', chart_esc),
       ('c_ekf', chart_ekf), ('c_mag', chart_mag)]
