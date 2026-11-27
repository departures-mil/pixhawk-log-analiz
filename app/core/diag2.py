"""Derin teşhis (v1.0.8): sağlık alanlarına eklenen ek bulgular ve log yeterliliği.

- Ters kumanda yüzeyi (uçak): kontrolcünün istediği irtifa/yatış yönü ile aracın gerçek dönüş hızı ters ilintili.
- Ağırlık merkezi / trim (uçak): düz uçuşta irtifa dümeni sürekli bir yöne basılı.
- Hava hızı kalibrasyonu (uçak): uzun uçuşta ortalama hava hızı / yer hızı oranı.
- Batarya iç direnci: gerilim–akım eğiminden (hücre başına mΩ).
- Titreşim frekansı: IMU yeterince hızlı kaydedilmişse baskın titreşim frekansı ve çentik filtresi uyumu.
- Log yeterliliği: teşhis için eksik kayıtlar (RCOU, VIBE, akım, ESC, PID, düşük ATT hızı).

Bulgular {'k','a'} biçimindedir (texts.S anahtarları) ve uygun sağlık alanına eklenir.
"""
from __future__ import annotations
import numpy as np

FW_MODES = {1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15}


def _F(k, **a):
    return {'k': k, 'a': a}


def _rate(s):
    t = s['t']
    if len(t) < 10: return 0.0
    d = np.diff(t); d = d[(d > 0) & (d < 1)]
    return float(1.0 / np.median(d)) if len(d) else 0.0


def _fw_mask(A, t):
    """Uçuşta ve sabit kanat modlarında olan örnekler."""
    L = A.L
    m = A.in_flight(t) if A.flights else np.zeros(len(t), bool)
    if not L.modes: return m
    mm = np.zeros(len(t), bool)
    ms = L.modes
    for i, (t0, num, _, _) in enumerate(ms):
        if int(num) not in FW_MODES: continue
        t1 = ms[i + 1][0] if i + 1 < len(ms) else 1e12
        mm |= (t >= t0) & (t < t1)
    return m & mm


def _add(A, dom, f, pen=0):
    h = A.health.get(dom)
    if h is None:
        A._dom(dom, 100 - pen, {}, [f]); return
    h.setdefault('findings', []).append(f)
    if pen:
        sc = int(max(0, min(100, h['score'] - pen)))
        h['score'] = sc; h['status'] = 'good' if sc >= 80 else ('warn' if sc >= 55 else 'bad')


# ------------------------------------------------------------------ uçak
def surfaces(A):
    """Ters yüzey ve trim. A.surf_rev = (t, yüzey) ayarlanır."""
    L = A.L; ae = L.s('AETR'); at = L.s('ATT')
    if A.vehicle != 'Plane' or not ae.has('Elev') or not at.has('Pitch'): return []
    m = _fw_mask(A, ae['t'])
    if m.sum() < 60: m = A.in_flight(ae['t']) if A.flights else m     # mod kaydı yoksa/kısa uçuş
    if m.sum() < 60: return []
    t = ae['t'][m]; out = []
    for f, ax, name in (('Elev', 'Pitch', 'elev'), ('Ail', 'Roll', 'ail')):
        if not ae.has(f): continue
        dem = ae[f][m]
        if np.nanstd(dem) < 150: continue
        ang = np.interp(t, at['t'], at[ax]); rate = np.gradient(ang, t)
        best = 0.0
        sat = float(np.mean(np.abs(dem) > 4000))        # yüzey sonuna kadar basılı (yetki yetersiz olabilir)
        for lag in (0.1, 0.2, 0.3, 0.5):
            r2 = np.interp(t + lag, t, rate)
            ok = np.isfinite(dem) & np.isfinite(r2) & (np.abs(r2) < 200)
            if ok.sum() < 60: continue
            c = float(np.corrcoef(dem[ok], r2[ok])[0, 1])
            if abs(c) > abs(best): best = c
        if sat > 0.25 and best > -0.4:
            out.append(('control', _F('surf_weak', s=name, p=round(sat * 100)), 15))
        if best <= -0.4:
            out.append(('control', _F('surf_rev', s=name, c=round(best, 2)), 50))
            if getattr(A, 'surf_rev', None) is None: A.surf_rev = (float(t[0]), name)
    # trim / ağırlık merkezi: düz, yatışsız, irtifa sabit uçuşta ortalama irtifa dümeni
    if ae.has('Elev'):
        rl = np.interp(t, at['t'], at['Roll']); pt = np.interp(t, at['t'], at['Pitch'])
        pr = np.gradient(pt, t)
        lv = (np.abs(rl) < 10) & (np.abs(pr) < 3)
        if lv.sum() > 200 and (t[lv][-1] - t[lv][0]) > 20:
            e = float(np.nanmedian(ae['Elev'][m][lv])); pct = abs(e) / 45.0
            if pct >= 30 and not any(o[1]['k'] == 'surf_rev' and o[1]['a']['s'] == 'elev' for o in out):
                out.append(('control', _F('cg_nose' if e > 0 else 'cg_tail', p=round(pct)), 10))
    return out


def airspeed(A):
    L = A.L
    if A.vehicle != 'Plane': return []
    s, f = A.airspeed_src()
    g = L.s('GPS')
    if f is None or not g.has('Spd'): return []
    m = _fw_mask(A, s['t'])
    if m.sum() < 100 or s['t'][m][-1] - s['t'][m][0] < 180: return []
    a = s[f][m]; gs = np.interp(s['t'][m], g['t'], g['Spd'])
    ok = (a > 3) & (gs > 3)
    if ok.sum() < 100: return []
    r = float(np.nanmean(a[ok]) / np.nanmean(gs[ok]))
    if r < 0.75 or r > 1.35:
        return [('airspeed', _F('aspd_ratio', r=round(r, 2)), 15)]
    return []


# ------------------------------------------------------------------ güç
def battery_ir(A):
    L = A.L; b = L.s('BAT')
    cf = 'Curr' if b.has('Curr') else None
    if not b.has('Volt') or cf is None or not A.flights: return []
    m = A.in_flight(b['t'])
    v = b['Volt'][m]; i = b[cf][m]
    ok = np.isfinite(v) & np.isfinite(i) & (i > 0.5)
    if ok.sum() < 60 or np.std(i[ok]) < 2: return []
    v = v[ok]; i = i[ok]; t = b['t'][m][ok]
    # yavaş boşalmayı ayır: gerilimdeki doğrusal zaman eğilimini çıkar
    k = np.polyfit(t - t[0], v, 1); vr = v - np.polyval(k, t - t[0])
    slope = np.polyfit(i, vr, 1)[0]
    R = -float(slope)
    cells = (A.health.get('power') or {}).get('metrics', {}).get('cells') or 0
    if R <= 0 or not cells: return []
    per = R / cells * 1000.0
    A.bat_ir = {'R_mohm': round(R * 1000, 1), 'per_cell': round(per, 1)}
    h = A.health.get('power')
    if h: h.setdefault('metrics', {})['ir_mohm'] = round(R * 1000, 1)
    if per > 12 and np.nanmax(i) > 10:
        return [('power', _F('bat_ir', r=round(R * 1000), c=round(per, 1), n=int(cells)), 10)]
    return []


# ------------------------------------------------------------------ fizik modeli (güç bütçesi)
def power_budget(A):
    """Çok rotorlu: düz asılı kalmadaki gazdan itki/ağırlık oranı (MOT_THST_EXPO eğrisiyle), asılı kalma gücü ve
    kalan süre kestirimi. Sabit kanat: düz seyirdeki gaz. Sonuçlar A.physics ve 'motors'/'power' alanına yazılır."""
    L = A.L; P = L.params; ct = L.s('CTUN'); out = []
    if not A.flights or not ct.has('ThO'): return out
    t = ct['t']; th = ct['ThO'].astype(float)
    if np.nanmax(th) > 1.5: th = th / 100.0
    fl = A.in_flight(t)
    phys = {}
    if A.vehicle in ('Copter', 'Heli') and A.vehicle != 'Heli':
        crt = ct['CRt'] if ct.has('CRt') else None
        m = fl & (th > 0.05)
        if crt is not None: m &= np.abs(crt) < 0.4
        tb = t[m]
        if len(tb) < 30: return out
        # kalkış/iniş geçişlerini dışla: uçuş başı ve sonundan 5 s
        ok = np.ones(len(tb), bool)
        for a, b in A.flights: ok &= ~((tb >= a) & (tb < a + 5)) & ~((tb > b - 5) & (tb <= b))
        h = float(np.nanmedian(th[m][ok])) if ok.sum() >= 20 else float(np.nanmedian(th[m]))
        if not (0.05 < h < 0.98): return out
        # CTUN.ThO itki cinsindendir (MOT_THST_EXPO doğrusallaştırması PWM'e çevirirken uygulanır): itki/ağırlık ≈ 1/ThO
        tw = 1.0 / h
        phys.update(hover_thr=round(h, 3), tw=round(tw, 2))
        b = L.s('BAT')
        if b.has('Volt') and b.has('Curr') and np.nanmax(b['Curr']) > 0.5:
            mb = A.in_flight(b['t'])
            if mb.sum() > 20:
                W = float(np.nanmedian(b['Volt'][mb] * b['Curr'][mb])); I = float(np.nanmedian(b['Curr'][mb]))
                phys.update(hover_w=round(W), hover_a=round(I, 1))
                cap = float(P.get('BATT_CAPACITY', 0) or 0)
                if cap > 0 and I > 0.5:
                    phys['endurance_min'] = round(cap / 1000.0 * 0.8 / I * 60, 1)   # %80 kullanılabilir kapasite
        if tw < 1.45:
            out.append(('motors', _F('tw_low', tw=round(tw, 2), h=round(h * 100)), 25))
        elif tw < 1.8:
            out.append(('motors', _F('tw_marginal', tw=round(tw, 2), h=round(h * 100)), 8))
    elif A.vehicle == 'Plane':
        m = _fw_mask(A, t) & (th > 0.05)
        if ct.has('CRt'): m &= np.abs(ct['CRt']) < 1.0
        if m.sum() >= 60:
            h = float(np.nanmedian(th[m])); phys['cruise_thr'] = round(h, 3)
            if h > 0.8: out.append(('motors', _F('fw_thr_high', v=round(h * 100)), 10))
    if phys:
        A.physics = phys
        A.facts.update({('phys_' + k): v for k, v in phys.items()})
    return out


# ------------------------------------------------------------------ titreşim frekansı
def vib_freq(A):
    L = A.L; P = L.params; im = L.s('IMU')
    if not im.has('AccZ') or not A.flights: return []
    hz = _rate(im)
    if hz < 200: return []
    m = A.in_flight(im['t'])
    if m.sum() < hz * 10: return []
    x = np.concatenate([im[k][m] - np.nanmean(im[k][m]) for k in ('AccX', 'AccY', 'AccZ') if im.has(k)])
    n = int(min(len(x), hz * 4)); n = 1 << int(np.log2(max(n, 64)))
    segs = [x[j:j + n] for j in range(0, len(x) - n, n // 2)][:200]
    if not segs: return []
    w = np.hanning(n)
    ps = np.mean([np.abs(np.fft.rfft(s_ * w)) ** 2 for s_ in segs], axis=0)
    fr = np.fft.rfftfreq(n, 1.0 / hz)
    band = (fr > 15) & (fr < hz / 2 * 0.9)
    if band.sum() < 5: return []
    j = int(np.argmax(np.where(band, ps, 0))); fpk = float(fr[j])
    prom = float(ps[j] / (np.median(ps[band]) + 1e-12))
    A.vib_peak = {'f': round(fpk), 'prom': round(prom, 1), 'hz': round(hz)}
    if prom < 8: return []
    out = []
    vst = (A.health.get('vibration') or {}).get('status')
    en = P.get('INS_HNTCH_ENABLE', None)
    if en == 0 and A.vehicle == 'Copter' and vst in ('warn', 'bad'):
        out.append(('vibration', _F('vib_peak_nonotch', f=round(fpk)), 0))
    elif en and P.get('INS_HNTCH_FREQ'):
        nf = float(P.get('INS_HNTCH_FREQ')); hm = int(P.get('INS_HNTCH_HMNCS', 1) or 1)
        hs = [nf * (k + 1) for k in range(8) if hm & (1 << k)] or [nf]
        if fpk < nf * 0.7 and min(abs(fpk - h) for h in hs) > nf * 0.3:
            out.append(('vibration', _F('vib_peak_notch', f=round(fpk), n=round(nf)), 0))
    return out


# ------------------------------------------------------------------ log yeterliliği
def data_gaps(A):
    """Teşhisi sınırlayan eksik kayıtlar (anahtar listesi)."""
    L = A.L; g = []
    if not L.s('RCOU').has('C1'): g.append('gap_rcou')
    if not L.s('VIBE').has('VibeZ'): g.append('gap_vibe')
    at = L.s('ATT')
    if not at.has('Roll'): g.append('gap_att')
    elif _rate(at) < 9: g.append('gap_att_rate')
    b = L.s('BAT')
    cur_ok = b.has('Curr') and len(b['Curr']) > 0 and float(np.nanmax(np.abs(b['Curr']))) > 0.2
    if not cur_ok and (A.info or {}).get('power') not in ('gas', 'glow', 'turbine'): g.append('gap_curr')
    if A.vehicle == 'Copter':
        if not L.s('PIDR').has('P') and not L.s('PIDR').has('Tar'): g.append('gap_pid')
        if not any(L.s(f'ESC[{i}]').has('RPM') for i in range(4)) and not L.s('ESC').has('RPM'): g.append('gap_esc')
    if not L.s('GPS').has('Lat'): g.append('gap_gps')
    return g


def run(A):
    A.surf_rev = None; A.bat_ir = None; A.vib_peak = None; A.physics = {}
    for fn in (surfaces, airspeed, battery_ir, power_budget, vib_freq):
        try:
            for dom, f, pen in fn(A):
                _add(A, dom, f, pen)
        except Exception:
            import traceback; traceback.print_exc()
    try:
        A.gaps = data_gaps(A)
    except Exception:
        A.gaps = []
