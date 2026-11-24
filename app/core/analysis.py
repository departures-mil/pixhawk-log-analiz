"""Analiz motoru: uçuş tespiti, aşamalar, sağlık puanları, olay çizelgesi, kırım tespiti,
kök neden zinciri ve parametre denetimi. Tamamen offline çalışır.

Bulgular dil bağımsızdır: her bulgu bir metin anahtarı ve argümanlardan oluşur, gösterim anında
core.texts ile seçilen dile çevrilir.
"""
from __future__ import annotations
import math
import numpy as np
from .loader import LogData, Series
from . import knowledge as K
from . import profiles as PR
from .analysis_ext import ExtMixin

PROFILE_OVERRIDE = {'v': 'auto'}   # Ayarlar'dan: auto / plane / vtol / copter / heli / rover


def F(key, **kw):
    return {'k': key, 'a': kw}


def _fin(a):
    a = np.asarray(a, dtype=float)
    return a[np.isfinite(a)]


def _interp(s: Series, f, t):
    if not s.has(f) or len(s['t']) < 2:
        return np.full(len(t), np.nan)
    return np.interp(t, s['t'], s[f], left=np.nan, right=np.nan)


def fmt_t(t):
    t = max(0.0, float(t))
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f'{h}:{m:02d}:{s:04.1f}' if h else f'{m:02d}:{s:04.1f}'


def hav(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1; dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


class Analysis(ExtMixin):
    def __init__(self, L: LogData, profile=None, extras=True, info=None):
        from . import flightinfo as FI
        self.L = L
        self.vehicle = L.vehicle
        self.info = dict(info or {})     # kullanıcının uçuş bilgileri formu
        p = profile or PROFILE_OVERRIDE.get('v') or 'auto'
        if p == 'auto' and FI.profile_for(self.info): p = FI.profile_for(self.info)
        self.profile = PR.detect(L) if p == 'auto' else p
        self.th = FI.adjust_thresholds(PR.get(self.profile), self.info)
        self.why = {}
        self.extras = extras
        self.anomalies = []      # ML anomali pencereleri
        self.pilot = {}          # pilot performans ölçütleri
        self.wind = {}           # logdan kestirilen rüzgâr
        self.weather = None      # çevrimiçi hava durumu (sonradan eklenir)
        self.serial = ''         # kart seri numarası (filo takibi)
        self.summary = {}
        self.flights = []        # [(takeoff_t, land_t)]
        self.armed = []          # [(arm_t, disarm_t)]
        self.phases = []         # [{name,t0,t1,stats}]
        self.health = {}         # domain -> {score,status,metrics,findings}
        self.overall = 100
        self.events = []         # [{t,cat,sev,text}]
        self.verdict = {}        # {kind, confidence, evidence}
        self.root = {}           # {cause, chain, prevent}
        self.param_findings = []
        self.facts = {}
        self.track = None        # dict t,lat,lon,alt,relalt
        self.run()

    # ------------------------------------------------------------------ temel
    def run(self):
        L = self.L
        self._track()
        self._armed()
        self._flying()
        self._phases()
        self._events()
        self._health()
        self._profile_checks()
        from . import diag2
        diag2.run(self)
        self._overall()
        self._crash()
        self._root_cause()
        self._params()
        self._facts()
        try:
            from . import why
            self.why = why.build(self)
        except Exception:
            import traceback; traceback.print_exc(); self.why = {}
        self._serial()
        self._wind()
        if self.extras:
            for fn in (self._pilot_metrics, self._anomaly):
                try: fn()
                except Exception:
                    import traceback; traceback.print_exc()

    def _track(self):
        L = self.L
        pos = L.s('POS')
        if pos.has('Lat') and len(pos['t']) > 2:
            lat, lon = pos['Lat'], pos['Lng']
            alt = pos['Alt'] if pos.has('Alt') else np.zeros(len(lat))
            rel = pos['RelHomeAlt'] if pos.has('RelHomeAlt') else alt - np.nanmin(alt)
            t = pos['t']
        else:
            g = L.s('GPS')
            if not g.has('Lat'):
                self.track = None; return
            ok = (g['Status'] >= 3) if g.has('Status') else np.ones(len(g['t']), bool)
            t = g['t'][ok]; lat = g['Lat'][ok]; lon = g['Lng'][ok]; alt = g['Alt'][ok]
            rel = alt - (alt[0] if len(alt) else 0)
        good = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) > 0.0001)
        if good.sum() < 2:
            self.track = None; return
        t, lat, lon, alt, rel = t[good], lat[good], lon[good], alt[good], rel[good]
        self.track = {'t': t, 'lat': lat, 'lon': lon, 'alt': alt, 'rel': rel}

    def _armed(self):
        L = self.L
        ev = [(t, True) for t, i in L.events if i == 10] + [(t, False) for t, i in L.events if i == 11]
        ev += L.arm
        ev.sort()
        cur = None; out = []
        for t, a in ev:
            if a and cur is None: cur = t
            elif not a and cur is not None: out.append((cur, t)); cur = None
            elif not a and cur is None and not out: out.append((0.0, t))   # log kurulu hâlde başlamış (LOG_DISARMED=0)
        if cur is not None: out.append((cur, L.duration))
        if not out:
            st = L.s('STAT')
            if st.has('Armed'):
                a = st['Armed'] > 0.5
                out = self._runs(st['t'], a)
        if not out and any(i in (15, 28) for _, i in L.events):
            # ARMED kaydı yok ama otopilot 'kendiliğinden kuruldu' / 'yerden kalktı' demiş: log kurulu başlamış
            out = [(0.0, L.duration)]
        self.armed = out

    @staticmethod
    def _runs(t, mask, min_len=0.0):
        out = []; start = None
        for i in range(len(t)):
            if mask[i] and start is None: start = t[i]
            if not mask[i] and start is not None:
                if t[i] - start >= min_len: out.append((start, t[i]))
                start = None
        if start is not None and t[-1] - start >= min_len: out.append((start, t[-1]))
        return out

    def _flying(self):
        L = self.L
        st = L.s('STAT')
        flights = []
        if st.has('isFlying') and len(st['t']) > 5:
            flights = self._runs(st['t'], st['isFlying'] > 0.5, 3.0)
        if not flights and self.track is not None:
            tr = self.track
            spd = np.zeros(len(tr['t']))
            dt = np.diff(tr['t']); d = hav(tr['lat'][:-1], tr['lon'][:-1], tr['lat'][1:], tr['lon'][1:])
            spd[1:] = np.where(dt > 0, d / np.maximum(dt, 1e-3), 0)
            m = (tr['rel'] > 3) | (spd > self.th['fly_speed'])
            flights = self._runs(tr['t'], m, 5.0)
        self.flip = None; self.esc_stop = None; self.yaw_loss = None; self.motor_fault = None
        if not flights:
            flights = self._flying_fallback()
        # Birleştir (kısa kesintiler)
        merged = []
        for f in flights:
            if merged and f[0] - merged[-1][1] < 10:
                merged[-1] = (merged[-1][0], f[1])
            else:
                merged.append(f)
        self.flights = merged
        if self.flip is None and merged and self.vehicle == 'Copter':
            self._late_flip()

    def _late_flip(self):
        """Çok rotorlu: son kurulum döneminin sonunda (≤3 s) araç devrildiyse (öncesinde düz uçuyordu) kırım say.
        Uçuş algılaması (isFlying) alçak irtifada devrilmeyi kaçırabiliyor."""
        L = self.L; att = L.s('ATT')
        if not att.has('Roll') or not self.armed: return
        a0, a1 = self.armed[-1]
        if a1 - a0 < 5 or a1 < self.flights[-1][0]: return
        m = (att['t'] >= a0) & (att['t'] <= a1 + 1)
        if m.sum() < 20: return
        at = att['t'][m]; ang = np.maximum(np.abs(att['Roll'][m]), np.abs(att['Pitch'][m]))
        lim = max(self.th['roll_crash'], 60)
        late = at >= a1 - 3.0; before = (at >= a1 - 15) & (at < a1 - 3.0)
        if late.any() and before.sum() > 5 and np.nanmax(ang[late]) > lim and np.nanpercentile(ang[before], 90) < 35:
            k = int(np.argmax(late & (ang > lim))); tf = float(at[k])
            self.flip = (tf, float(np.nanmax(ang[late])))
            if tf > self.flights[-1][1] + 10:      # ayrı (algılanmamış) bir uçuş: ayrı uçuş olarak ekle
                self.flights.append((max(a0, self.flights[-1][1], tf - 6), tf))
            elif tf > self.flights[-1][1]:
                self.flights[-1] = (self.flights[-1][0], tf)

    def _fall(self, f):
        """Uçuş içinde kontrolsüz düşüş: barometre irtifası ≥8 m'den yere (≤3 m) hızla iner (çok rotorlu/VTOL Q modu
        ≥5 m/s, uçak ≥10 m/s ortalama) ve ya öncesinde ≥45° tutum sapması ya da düşüşten sonra araç yerde kalır.
        Normal iniş (QLAND/LAND ~1–3 m/s) bu hıza ulaşmaz."""
        L = self.L; b = L.s('BARO')
        if not b.has('Alt'): return None
        m = (b['t'] >= f[0] - 2) & (b['t'] <= f[1] + 3)
        if m.sum() < 20: return None
        t = b['t'][m]; al = b['Alt'][m].astype(float)
        ref = float(np.nanmedian(b['Alt'][(b['t'] >= f[0] - 5) & (b['t'] <= f[0] + 1)])) if ((b['t'] >= f[0] - 5) & (b['t'] <= f[0] + 1)).sum() else al[0]
        h = al - ref
        dt = float(np.median(np.diff(t))) if len(t) > 2 else 0.1
        k = max(1, int(round(1.0 / max(dt, 1e-3))))
        hs = np.convolve(h, np.ones(k) / k, mode='same')
        ground = np.flatnonzero(hs <= 3.0)
        q = self.vehicle in ('Copter', 'Heli') or self.profile == 'vtol'
        vmin = 5.0 if q else 10.0
        best = None
        for gi in ground:
            if gi == 0 or hs[gi - 1] <= 3.0: continue        # yalnız yere varış anları
            tg = t[gi]
            w = (t >= tg - 6) & (t <= tg)
            if w.sum() < 5: continue
            top = float(np.nanmax(hs[w])); itop = int(np.flatnonzero(w)[np.nanargmax(hs[w])])
            drop = top - float(hs[gi]); dur = max(tg - t[itop], 0.2)
            if drop < 8 or drop / dur < vmin: continue
            best = dict(t=float(tg), h=drop, v=drop / dur, t0=float(t[itop])); break
        if best is None: return None
        att = L.s('ATT'); ang = roll = pitch = 0.0
        if att.has('Roll'):
            wa = (att['t'] >= best['t0'] - 5) & (att['t'] <= best['t'])
            if wa.any():
                roll = float(np.nanmax(np.abs(att['Roll'][wa]))); pitch = float(np.nanmax(np.abs(att['Pitch'][wa])))
                ang = max(roll, pitch)
        stay = (t > best['t'] + 1) & (t <= best['t'] + 6)
        stays = stay.sum() > 3 and float(np.nanmax(hs[stay])) < 4
        if not (ang > 45 or stays): return None
        # iniş moduna geçip yavaş alçalan normal inişleri ayır: Q/LAND modunda tutum düzgünse düşüş sayma
        if ang <= 45 and best['v'] < vmin * 1.6: return None
        best.update(ang=ang, roll=roll, pitch=pitch)
        return best

    def crash_time(self):
        """Otopilotun kendi kırım tespiti (STAT.Crash, ERR 12, 'Crash' mesajı) zamanı."""
        L = self.L; ts = []
        st = L.s('STAT')
        if st.has('Crash') and len(st['t']) and np.nanmax(st['Crash']) > 0:
            ts.append(float(st['t'][np.argmax(st['Crash'] > 0)]))
        ts += [t for t, s, c in L.errors if s == 12 and c != 0][:1]
        ts += [t for t, x in L.texts if 'crash' in x.lower()][:1]
        return min(ts) if ts else None

    def _flying_fallback(self):
        """isFlying/konum izi uçuş göstermezse: barometre yükselişi, yer hızı,
        otopilotun kırım tespiti veya devrilme ile kısa (kalkışta düşen) uçuşları yakala."""
        L = self.L; out = []
        b = L.s('BARO'); g = L.s('GPS'); att = L.s('ATT')
        tc = self.crash_time()
        for a0, a1 in self.armed:
            if a1 - a0 < 1.0: continue
            got = []
            if b.has('Alt'):
                m = (b['t'] >= a0) & (b['t'] <= a1)
                if m.sum() > 10:
                    bt = b['t'][m]; al = b['Alt'][m]
                    ref = np.nanmedian(al[bt <= a0 + 2.0]) if (bt <= a0 + 2.0).sum() else al[0]
                    got += self._runs(bt, (al - ref) > 1.5, 1.5)
            if g.has('Spd'):
                m = (g['t'] >= a0) & (g['t'] <= a1)
                if g.has('Status'): m &= g['Status'] >= 3
                if m.sum() > 3:
                    got += self._runs(g['t'][m], g['Spd'][m] > max(2.5, self.th['fly_speed']), 2.0)
            if tc is not None and a0 <= tc <= a1 + 1:
                got.append((a0 + min(2.0, (tc - a0) / 2), min(tc, a1)))
            # devrilme: kurulumda düz, kurulum sonunda büyük yatış/yunuslama
            if att.has('Roll') and a1 - a0 > 3:
                m = (att['t'] >= a0) & (att['t'] <= a1)
                if m.sum() > 10:
                    at = att['t'][m]; ang = np.maximum(np.abs(att['Roll'][m]), np.abs(att['Pitch'][m]))
                    lim = max(self.th['roll_crash'], 50)
                    early = ang[at <= a0 + 2.0]
                    late = at >= a1 - 3.0
                    if len(early) and np.nanmax(early) < 25 and late.any() and np.nanmax(ang[late]) > lim:
                        k = int(np.argmax(ang > lim)); tf = float(at[k])
                        self.flip = (tf, float(np.nanmax(ang[late])))
                        got.append((a0 + min(2.0, (tf - a0) / 2), a1))
            # otopilotun kendi kalkış algısı (Copter: NOT_LANDED=28 → LAND_COMPLETE=18 / disarm)
            if self.vehicle in ('Copter', 'Heli'):
                es = sorted((t, i) for t, i in L.events if a0 - 0.5 <= t <= a1 + 0.5 and i in (28, 18))
                st0 = None
                for t, i in es:
                    if i == 28 and st0 is None: st0 = t
                    elif i == 18 and st0 is not None:
                        if t - st0 >= 2.0: got.append((st0, t))
                        st0 = None
                if st0 is not None and a1 - st0 >= 2.0: got.append((st0, a1))
            if got:
                out.append((min(x[0] for x in got), max(x[1] for x in got)))
        return out

    def cruise_mask(self, t):
        t = np.asarray(t); m = np.zeros(len(t), bool)
        for p in self.phases:
            if p['name'] in ('cruise', 'climb', 'descent'):
                m |= (t >= p['t0']) & (t <= p['t1'])
        return m

    def in_flight(self, t):
        t = np.asarray(t)
        m = np.zeros(len(t), bool)
        for a, b in self.flights:
            m |= (t >= a) & (t <= b)
        return m

    # -------------------------------------------------------------- aşamalar
    def _phases(self):
        tr = self.track
        if tr is None or not self.flights:
            return
        t = tr['t']; rel = tr['rel']
        if len(t) < 3: return
        # dikey hız (düzgünleştirilmiş)
        k = min(len(t), max(1, int(len(t) / max(1, (t[-1] - t[0])) * 3)))
        rs = np.convolve(rel, np.ones(k) / k, mode='same')
        vz = np.gradient(rs, t)
        ctun = self.L.s('CTUN')
        thr = _interp(ctun, 'ThO', t) if ctun.has('ThO') else np.full(len(t), np.nan)
        spd = _interp(ctun, 'As', t) if ctun.has('As') else np.full(len(t), np.nan)
        g = self.L.s('GPS'); gs = _interp(g, 'Spd', t)
        labels = np.array(['ground'] * len(t), dtype=object)
        for a, b in self.flights:
            m = (t >= a) & (t <= b)
            if not m.any() or not np.isfinite(rel[m]).any(): continue   # konum verisi bu uçuşu kapsamıyor
            labels[m] = 'cruise'
            labels[m & (vz > 1.0)] = 'climb'
            labels[m & (vz < -1.0)] = 'descent'
            to = m & (t <= a + 25) & (vz > -0.5)
            labels[to] = 'takeoff'
            ld = m & (t >= b - 40) & (rel < np.nanmax(rel[m]) * 0.5 + 5)
            labels[ld & (vz < 0.5)] = 'landing'
        segs = []
        cur = None
        for i in range(len(t)):
            if cur is None or labels[i] != cur['name']:
                if cur: cur['t1'] = t[i]; segs.append(cur)
                cur = {'name': labels[i], 't0': t[i], 'i0': i}
            cur['i1'] = i
        if cur: cur['t1'] = t[-1]; segs.append(cur)
        # kısa parçaları komşuya kat
        out = []
        for s in segs:
            if out and (s['t1'] - s['t0'] < 8) and s['name'] not in ('takeoff', 'landing'):
                out[-1]['t1'] = s['t1']; out[-1]['i1'] = s['i1']; continue
            if out and out[-1]['name'] == s['name']:
                out[-1]['t1'] = s['t1']; out[-1]['i1'] = s['i1']; continue
            out.append(s)
        for s in out:
            sl = slice(s['i0'], s['i1'] + 1)
            def mx(a):
                a = _fin(a[sl]); return float(a.max()) if len(a) else None
            def mn(a):
                a = _fin(a[sl]); return float(a.mean()) if len(a) else None
            att = self.L.s('ATT')
            roll = _interp(att, 'Roll', t); pitch = _interp(att, 'Pitch', t)
            s['stats'] = {'dur': float(s['t1'] - s['t0']), 'alt_max': mx(rel), 'alt_mean': mn(rel),
                          'vz_mean': mn(vz), 'thr_mean': mn(thr), 'as_mean': mn(spd), 'gs_mean': mn(gs),
                          'roll_max': mx(np.abs(roll)), 'pitch_max': mx(np.abs(pitch))}
            s.pop('i0'); s.pop('i1')
        self.phases = out

    # ------------------------------------------------------------ olaylar
    def _events(self):
        L = self.L; E = []
        for t, num, _, rsn in L.modes:
            E.append({'t': t, 'cat': 'mode', 'sev': 1 if rsn in K.FAILSAFE_REASONS else 0,
                      'text': F('ev_mode', mode=K.mode_name(self.vehicle, num), reason=rsn)})
        for t, sub, code in L.errors:
            E.append({'t': t, 'cat': 'err', 'sev': 0 if code == 0 else 2, 'text': F('ev_err', sub=sub, code=code)})
        for t, i in L.events:
            E.append({'t': t, 'cat': 'ev', 'sev': 0, 'text': F('ev_ev', id=i)})
        warn_words = ('fail', 'error', 'bad', 'lost', 'low', 'critical', 'crash', 'glitch', 'variance', 'unhealthy',
                      'emergency', 'stall', 'clip', 'prearm', 'warning', 'timeout', 'reset', 'lane switch')
        for t, txt in L.texts:
            lw = txt.lower()
            sev = 2 if any(w in lw for w in ('crash', 'critical', 'emergency', 'fail')) else (1 if any(w in lw for w in warn_words) else 0)
            E.append({'t': t, 'cat': 'msg', 'sev': sev, 'text': F('ev_msg', msg=txt)})
        for a, b in self.flights:
            E.append({'t': a, 'cat': 'flight', 'sev': 0, 'text': F('ev_takeoff')})
            E.append({'t': b, 'cat': 'flight', 'sev': 0, 'text': F('ev_landing')})
        E.sort(key=lambda e: e['t'])
        self.events = E

    # ----------------------------------------------------------- sağlık
    def _dom(self, name, score, metrics, findings):
        score = int(max(0, min(100, round(score))))
        st = 'good' if score >= 80 else ('warn' if score >= 55 else 'bad')
        self.health[name] = {'score': score, 'status': st, 'metrics': metrics, 'findings': findings}

    def _health(self):
        L = self.L; P = L.params
        fl = self.flights
        def fmask(s):
            return self.in_flight(s['t']) if fl else np.ones(len(s['t']), bool)
        # GPS
        g = L.s('GPS')
        if g.has('NSats'):
            m = fmask(g)
            ns = g['NSats'][m] if m.any() else g['NSats']; hd = g['HDop'][m] if g.has('HDop') and m.any() else (g['HDop'] if g.has('HDop') else np.array([]))
            stt = g['Status'][m] if g.has('Status') and m.any() else (g['Status'] if g.has('Status') else np.array([]))
            TH = self.th
            bad = ((ns < TH['sat_min']) | ((hd > TH['hdop_max']) if len(hd) == len(ns) else False) | ((stt < 3) if len(stt) == len(ns) else False))
            pct = float(bad.mean() * 100) if len(ns) else 0
            glitches = sum(1 for _, s, c in L.errors if s in (7, 11) and c != 0)
            sc = 100 - pct * 2.2 - glitches * 8
            fnd = []
            if pct > 2: fnd.append(F('gps_bad_pct', pct=round(pct, 1)))
            if len(ns) and np.nanmin(ns) < self.th['sat_min']: fnd.append(F('gps_min_sats', n=int(np.nanmin(ns))))
            if glitches: fnd.append(F('gps_glitch', n=glitches))
            self._dom('gps', sc, {'min_sats': float(np.nanmin(ns)) if len(ns) else None, 'mean_sats': float(np.nanmean(ns)) if len(ns) else None,
                                  'max_hdop': float(np.nanmax(hd)) if len(hd) else None, 'bad_pct': pct, 'glitches': glitches}, fnd)
        # Titreşim
        v = L.s('VIBE')
        if v.has('VibeZ'):
            m = fmask(v)
            vx, vy, vz = (v[k][m] if m.any() else v[k] for k in ('VibeX', 'VibeY', 'VibeZ'))
            mxv = float(np.nanmax([np.nanmax(vx), np.nanmax(vy), np.nanmax(vz)]))
            p95 = float(np.nanpercentile(np.concatenate([vx, vy, vz]), 95))
            clipk = [k for k in ('Clip', 'Clip0', 'Clip1', 'Clip2') if v.has(k)]
            clip = float(np.nanmax(v[clipk[0]]) - np.nanmin(v[clipk[0]])) if clipk else 0.0
            vw, vb = self.th['vibe_warn'], self.th['vibe_bad']
            sc = 100 - max(0, p95 - (vw - 5)) * 1.6 - min(30, clip / 10)
            fnd = []
            if p95 > vb: fnd.append(F('vibe_high', v=round(p95, 1)))
            elif p95 > vw: fnd.append(F('vibe_mid', v=round(p95, 1)))
            if clip > 0: fnd.append(F('vibe_clip', n=int(clip)))
            self._dom('vibration', sc, {'p95': p95, 'max': mxv, 'z_mean': float(np.nanmean(vz)), 'clip': clip}, fnd)
        # Güç
        b = L.s('BAT')
        if b.has('Volt'):
            m = fmask(b)
            vv = b['Volt'][m] if m.any() else b['Volt']
            vmin = float(np.nanmin(vv)); vmax = float(np.nanmax(b['Volt']))
            cells = max(1, round(vmax / 4.2)) if vmax > 5 else 1
            try:
                uc = int(str(self.info.get('cells') or '').rstrip('sS'))
                if uc > 0: cells = uc
            except ValueError: pass
            per = vmin / cells
            curr = b['Curr'] if b.has('Curr') else np.array([])
            cur_ok = len(_fin(curr)) > 0 and np.nanmax(np.abs(curr)) > 0.5
            used = float(np.nanmax(b['CurrTot'])) if b.has('CurrTot') else None
            cap = P.get('BATT_CAPACITY')
            fnd = []
            sc = 100
            if per < self.th['cell_bad']: sc -= 45; fnd.append(F('bat_low_cell', v=round(per, 2), n=cells))
            elif per < self.th['cell_warn']: sc -= 20; fnd.append(F('bat_mid_cell', v=round(per, 2), n=cells))
            ice = self.info.get('power') in ('gas', 'glow', 'turbine')
            if not cur_ok and not ice: sc -= 15; fnd.append(F('bat_no_current'))
            if ice: fnd.append(F('fi_ice_power'))
            if cur_ok and used and cap and used > cap * 0.8: sc -= 15; fnd.append(F('bat_used', used=int(used), cap=int(cap)))
            for _, s, c in L.errors:
                if s == 6 and c != 0: sc -= 20; fnd.append(F('bat_fs', code=c)); break
            pw = L.s('POWR')
            vcc = float(np.nanmin(pw['Vcc'])) if pw.has('Vcc') else None
            if vcc is not None and vcc < 4.8: sc -= 15; fnd.append(F('vcc_low', v=round(vcc, 2)))
            sag = None
            if cur_ok:
                try:
                    i_hi = np.nanargmax(curr); sag = float(np.nanmax(b['Volt']) - b['Volt'][i_hi])
                except Exception: pass
            self._dom('power', sc, {'vmin': vmin, 'vmax': vmax, 'cells': cells, 'per_cell_min': per, 'current_sensor': bool(cur_ok),
                                    'used_mah': used, 'capacity': cap, 'vcc_min': vcc, 'max_curr': float(np.nanmax(curr)) if cur_ok else None}, fnd)
        # EKF / pusula
        x = L.s('XKF4') if L.s('XKF4').has('SV') else L.s('NKF4')
        fnd = []; sc = 100; met = {}
        if x.has('SV'):
            m = fmask(x)
            for k in ('SV', 'SP', 'SH', 'SM'):
                if x.has(k):
                    a = x[k][m] if m.any() else x[k]; mx_ = float(np.nanmax(a)); met[k] = mx_
                    if mx_ > self.th['ekf_bad']: sc -= 18; fnd.append(F('ekf_bad', k=k, v=round(mx_, 2)))
                    elif mx_ > self.th['ekf_warn']: sc -= 7; fnd.append(F('ekf_warn', k=k, v=round(mx_, 2)))
        mg = L.s('MAG')
        if mg.has('MagX'):
            fieldm = np.sqrt(mg['MagX'] ** 2 + mg['MagY'] ** 2 + mg['MagZ'] ** 2)
            fm = _fin(fieldm)
            if len(fm) > 10:
                var = float((np.nanpercentile(fm, 95) - np.nanpercentile(fm, 5)) / max(1, np.nanmedian(fm)) * 100)
                met['mag_var_pct'] = var
                ct = L.s('CTUN')
                if ct.has('ThO'):
                    thr = np.interp(mg['t'], ct['t'], ct['ThO'])
                    ok = np.isfinite(thr) & np.isfinite(fieldm)
                    if ok.sum() > 20 and np.nanstd(thr[ok]) > 1:
                        cor = float(np.corrcoef(thr[ok], fieldm[ok])[0, 1]); met['mag_thr_corr'] = cor
                        if abs(cor) > 0.5 and var > 5: sc -= 25; fnd.append(F('mag_interf', c=round(cor, 2), v=round(var, 1)))
                if var > 25 and not any(f['k'] == 'mag_interf' for f in fnd): sc -= 12; fnd.append(F('mag_var', v=round(var, 1)))
        for _, s, c in L.errors:
            if s in (16, 17, 24) and c != 0: sc -= 15; fnd.append(F('ekf_err')); break
        if met: self._dom('ekf', sc, met, fnd)
        # Kontrol (tutum takibi)
        a = L.s('ATT')
        if a.has('DesRoll') and a.has('Roll'):
            m = fmask(a)
            er = np.abs(a['DesRoll'] - a['Roll'])[m] if m.any() else np.abs(a['DesRoll'] - a['Roll'])
            ep = np.abs(a['DesPitch'] - a['Pitch'])[m] if m.any() else np.abs(a['DesPitch'] - a['Pitch'])
            rr = float(np.sqrt(np.nanmean(er ** 2))); rp = float(np.sqrt(np.nanmean(ep ** 2)))
            mr = float(np.nanmax(np.abs(a['Roll'][m]))) if m.any() else float(np.nanmax(np.abs(a['Roll'])))
            mp = float(np.nanmax(np.abs(a['Pitch'][m]))) if m.any() else float(np.nanmax(np.abs(a['Pitch'])))
            sc = 100 - max(0, rr - 2) * 5 - max(0, rp - 2) * 5
            fnd = []
            if rr > self.th['att_err_warn']: fnd.append(F('att_roll_err', v=round(rr, 1)))
            if rp > self.th['att_err_warn']: fnd.append(F('att_pitch_err', v=round(rp, 1)))
            lim = P.get('ROLL_LIMIT_DEG', P.get('LIM_ROLL_CD', 4500) / 100)
            if mr > lim + 15: sc -= 15; fnd.append(F('att_roll_exceed', v=round(mr), lim=round(lim)))
            self._dom('control', sc, {'roll_rms': rr, 'pitch_rms': rp, 'roll_max': mr, 'pitch_max': mp}, fnd)
        # Servo doyması
        o = L.s('RCOU')
        if o.has('C1'):
            m = fmask(o)
            sat = {}
            for ch in ('C1', 'C2', 'C3', 'C4'):
                if o.has(ch):
                    arr = o[ch][m] if m.any() else o[ch]
                    arr = _fin(arr)
                    if len(arr):
                        lo, hi = np.percentile(arr, 1), np.percentile(arr, 99)
                        mn = P.get(f'SERVO{ch[1:]}_MIN', 1100); mxp = P.get(f'SERVO{ch[1:]}_MAX', 1900)
                        s_ = float(((arr <= mn + 5) | (arr >= mxp - 5)).mean() * 100)
                        sat[ch] = s_
            fnd = []
            thr_ch = 'C3'
            thr_sat = sat.pop(thr_ch, 0)
            worst = max(sat.values()) if sat else 0
            sc = 100 - worst * 2.5
            if worst > 5: fnd.append(F('servo_sat', ch=max(sat, key=sat.get), v=round(worst, 1)))
            ct = L.s('CTUN')
            if ct.has('ThO'):
                th = ct['ThO'][fmask(ct)] if fl else ct['ThO']
                th = _fin(th)
                if len(th) and np.nanmax(th) <= 1.05: th = th * 100   # Copter: ThO 0..1
                if len(th):
                    p_full = float((th >= 98).mean() * 100)
                    if p_full > self.th['thr_full_pct']: sc -= 15; fnd.append(F('thr_full', v=round(p_full, 1)))
                    sat['thr_full_pct'] = p_full; sat['thr_mean'] = float(th.mean())
            self._dom('servo', sc, sat, fnd)
        # RC bağlantısı
        r = L.s('RCIN')
        fnd = []; sc = 100; met = {}
        rf = sum(1 for _, s, c in L.errors if s in (2, 5) and c != 0)
        if rf: sc -= 30 + 5 * rf; fnd.append(F('rc_fs', n=rf))
        if r.has('C3'):
            fsv = P.get('THR_FS_VALUE', P.get('FS_THR_VALUE', 950))
            low = float((r['C3'] < fsv).mean() * 100); met['below_fs_pct'] = low
            if low > 0.5 and not rf: sc -= 15; fnd.append(F('rc_low', v=round(low, 1)))
        rs = L.s('RSSI')
        if rs.has('RXRSSI'):
            met['rssi_min'] = float(np.nanmin(rs['RXRSSI']))
        met['radio_failsafes'] = rf
        self._dom('rc', sc, met, fnd)
        # Hava hızı (uçak)
        ap = L.s('ARSP'); ct = L.s('CTUN')
        if self.vehicle == 'Plane' and (ap.has('Airspeed') or ct.has('As')):
            src = ap if ap.has('Airspeed') else ct
            f_ = 'Airspeed' if ap.has('Airspeed') else 'As'
            m = self.cruise_mask(src['t'])
            if not m.any(): m = fmask(src)
            asp = src[f_][m] if m.any() else src[f_]
            amin = P.get('AIRSPEED_MIN', P.get('ARSPD_FBW_MIN', 9))
            low = float((asp < amin * 0.9).mean() * 100) if len(asp) else 0
            sc = 100 - low * 3
            fnd = []
            if low > 1: fnd.append(F('as_low', v=round(low, 1), min=amin))
            gps = L.s('GPS'); met = {'as_mean': float(np.nanmean(asp)) if len(asp) else None, 'as_min': float(np.nanmin(asp)) if len(asp) else None, 'below_min_pct': low}
            if gps.has('Spd') and len(asp) > 10:
                gsp = np.interp(src['t'][m] if m.any() else src['t'], gps['t'], gps['Spd'])
                diff = float(np.nanmean(asp - gsp)); met['as_minus_gs'] = diff
            if P.get('ARSPD_TYPE', 1) == 0 or P.get('ARSPD_USE', 1) == 0:
                fnd.append(F('as_not_used'))
            self._dom('airspeed', sc, met, fnd)
        # İşlemci / log
        pm = L.s('PM')
        if pm.has('Load'):
            load = float(np.nanmax(pm['Load']) / 10.0)
            nl = float(np.nansum(pm['NLon'])) if pm.has('NLon') else 0
            sc = 100 - max(0, load - 60) * 1.5
            fnd = [F('cpu_high', v=round(load))] if load > 80 else []
            self._dom('cpu', sc, {'load_max': load, 'long_loops': nl}, fnd)
    def _overall(self):
        # Genel puan: zayıf alanlar ağır bassın
        if self.health:
            ws = {'gps': 1.2, 'vibration': 1.0, 'power': 1.3, 'ekf': 1.2, 'control': 1.0, 'servo': 0.8, 'rc': 1.0, 'airspeed': 1.0, 'cpu': 0.5}
            tot = sum(ws.get(k, 1) for k in self.health)
            avg = sum(v['score'] * ws.get(k, 1) for k, v in self.health.items()) / tot
            worst = min(v['score'] for v in self.health.values())
            self.overall = int(round(0.6 * avg + 0.4 * worst))

    # --------------------------------------------------------- kırım tespiti
    def _crash(self):
        L = self.L; ev = []; score = 0
        st = L.s('STAT')
        if st.has('Crash') and np.nanmax(st['Crash']) > 0:
            t = float(st['t'][np.argmax(st['Crash'] > 0)]); score += 60; ev.append(F('cr_stat', t=t))
        for t, s, c in L.errors:
            if s == 12 and c != 0: score += 50; ev.append(F('cr_err', t=t)); break
        for t, txt in L.texts:
            if 'crash' in txt.lower(): score += 30; ev.append(F('cr_msg', t=t, msg=txt)); break
        tr = self.track
        end_t = L.duration
        if tr is not None and self.flights:
            last_f = self.flights[-1]
            rel = tr['rel']; t = tr['t']
            # Son uçuş noktasındaki irtifa ve alçalma hızı
            i_end = int(np.searchsorted(t, last_f[1])) - 1
            i_end = max(0, min(i_end, len(t) - 1))
            w = (t > last_f[1] - 6) & (t <= last_f[1])
            if w.sum() > 3:
                vz = np.gradient(rel[w], t[w]); min_vz = float(np.nanmin(vz))
                if min_vz < -self.th['sink_crash']: score += 25; ev.append(F('cr_sink', v=round(-min_vz, 1), t=float(last_f[1])))
            # log uçuş halinde bitti mi
            land_ev = [t_ for t_, i in L.events if i == 18 and last_f[0] <= t_ <= last_f[1] + 5]
            if L.duration - last_f[1] < 3 and rel[-1] > 15:
                score += 35; ev.append(F('cr_log_end', alt=round(float(rel[-1])), t=float(L.duration)))
            elif L.duration - last_f[1] < 3 and rel[-1] > 3 and not land_ev and self.vehicle == 'Copter':
                score += 30; ev.append(F('cr_log_end', alt=round(float(rel[-1])), t=float(L.duration)))
            # iniş tamamlandı olayı yalnız son uçuşta ve alçakta, yumuşak alçalmayla gelmişse 'normal iniş' sayılır
            # (kırımda ArduCopter yere çarpınca da 'iniş tamamlandı' yazar; havada yazılan olay iniş değildir)
            landed = False
            for t_ in land_ev:
                k = max(0, min(int(np.searchsorted(t, t_)), len(t) - 1))
                w_ = (t > t_ - 4) & (t <= t_)
                vz_ = float(np.nanmin(np.gradient(rel[w_], t[w_]))) if w_.sum() > 3 else 0.0
                if rel[k] < 5 and vz_ > -self.th['sink_crash']: landed = True
            mode_last = L.modes[-1][1] if L.modes else None
            att = L.s('ATT')
            if att.has('Roll'):
                w2 = (att['t'] > last_f[1] - 8) & (att['t'] <= last_f[1] + 2)
                if w2.any():
                    mr = float(np.nanmax(np.abs(att['Roll'][w2]))); mp = float(np.nanmax(np.abs(att['Pitch'][w2])))
                    if mr > self.th['roll_crash'] or mp > self.th['pitch_crash']:
                        score += 20; ev.append(F('cr_attitude', r=round(mr), p=round(mp)))
            v = L.s('VIBE')
            if v.has('VibeZ'):
                w3 = (v['t'] > last_f[1] - 2) & (v['t'] <= last_f[1] + 3)
                if w3.any() and np.nanmax(v['VibeZ'][w3]) > self.th['vibe_crash']:
                    score += 15; ev.append(F('cr_impact', v=round(float(np.nanmax(v['VibeZ'][w3])))))
            hard = any(x.get('k') in ('cr_stat', 'cr_err', 'cr_msg') for x in ev) or getattr(self, 'flip', None)
            if landed and not hard: score -= 25; ev.append(F('cr_landed'))
        # Kontrolsüz düşüş: son uçuşta hızlı irtifa kaybı yere kadar sürdü (motorlar yerde dönmeye devam etse de)
        self.fall = None
        if self.flights:
            fl = self._fall(self.flights[-1])
            if fl is not None:
                self.fall = fl
                score += 40; ev.append(F('cr_fall', h=round(fl['h']), v=round(fl['v'], 1), t=fl['t'], a=round(fl['ang'])))
                if not any(x.get('k') == 'cr_attitude' for x in ev) and fl['ang'] > 45:
                    score += 20; ev.append(F('cr_attitude', r=round(fl['roll']), p=round(fl['pitch'])))
                ev[:] = [x for x in ev if x.get('k') != 'cr_landed']
                if any(x.get('k') == 'cr_landed' for x in ev): score += 25
        # Çok rotorlu: son 10 s içinde yön (yaw) kontrolü kaybı (istenen/gerçek fark >60°, ≥1 s)
        if tr is not None and self.flights and self.vehicle == 'Copter':
            att = L.s('ATT'); last_f = self.flights[-1]
            if att.has('DesYaw') and att.has('Yaw'):
                w = (att['t'] > last_f[1] - 10) & (att['t'] <= last_f[1] + 1)
                if w.sum() > 5:
                    e = np.abs((att['DesYaw'][w] - att['Yaw'][w] + 180) % 360 - 180)
                    runs = self._runs(att['t'][w], e > 60, 1.0)
                    if runs:
                        self.yaw_loss = float(runs[0][0])
                        score += 25; ev.append(F('cr_yaw', v=round(float(np.nanmax(e))), t=self.yaw_loss))
        if self.flights and getattr(self, 'flip', None):
            score += 45; ev.append(F('cr_flip', t=self.flip[0], a=round(self.flip[1])))
        if self.flights and (L.duration - self.armed[-1][1] < 1.0 if self.armed else True) and \
                L.duration - self.flights[-1][1] < 2.0 and not any(x.get('k') == 'cr_log_end' for x in ev) and \
                not any(i == 11 for _, i in L.events):
            # kurulu ve uçuşta iken log kesildi (güç kaybı / ani düşüş)
            score += 30; ev.append(F('cr_log_cut', t=float(L.duration)))
        # 'kötü' sağlık alanları: tek başına servo/hava hızı/kontrol uyarısı (ör. ayar aşamasındaki uçuş) olay sayılmaz
        bad_dom = {k for k, h in self.health.items() if h.get('status') == 'bad'}
        if not self.flights:
            kind = 'noflight'
        elif score >= 60:
            kind = 'crash'
        elif score >= 25 or (score > 0 and bad_dom) or len(bad_dom) >= 2 or bad_dom & {'gps', 'ekf', 'vibration', 'power', 'motors'} or \
                any(r in K.FAILSAFE_REASONS for _, _, _, r in L.modes) or \
                any(s in (2, 5, 6, 7, 8, 9, 12, 16, 17) and c != 0 for _, s, c in L.errors):
            kind = 'incident'
        else:
            kind = 'normal'
        # 'sorunlu' kararının derecesi: ciddi (kaza riski/kanıtı) ya da küçük uyarı (tek başına önemsiz sağlık bulgusu)
        fs = any(r in K.FAILSAFE_REASONS for _, _, _, r in L.modes)
        crit_err = any(s in (2, 5, 6, 7, 8, 9, 12, 16, 17) and c != 0 for _, s, c in L.errors)
        serious = score >= 25 or (score > 0 and bool(bad_dom)) or bool(bad_dom & {'gps', 'ekf', 'power', 'motors', 'rc', 'control'}) \
            or len(bad_dom) >= 3 or ((fs or crit_err) and bool(bad_dom))
        # kullanıcının cevabı (uçuş bilgileri formu)
        uc = self.info.get('crashed')
        hard_ev = any(x.get('k') in ('cr_stat', 'cr_err', 'cr_msg', 'cr_flip') for x in ev)
        if uc == 'yes':
            ev.append(F('cr_user'))
            if kind != 'crash': kind = 'crash'; score = max(score, 60)
            if not hard_ev and score < 60: ev.append(F('cr_user_weak'))
        elif uc == 'hard':
            ev.append(F('cr_user_hard'))
            if kind in ('normal', 'noflight') and self.flights: kind = 'incident'
        elif uc == 'no' and kind == 'crash':
            if hard_ev: ev.append(F('cr_user_conflict'))
            else: kind = 'incident'; ev.append(F('cr_user_no'))
        self.verdict = {'kind': kind, 'score': max(0, min(100, score)), 'evidence': ev,
                        'severity': ('serious' if serious or uc == 'hard' else 'minor') if kind == 'incident' else None}
        # öğrenen ikinci görüş (uzman etiketli gerçek loglarla eğitildi); yalnız ölçülmüş yararı varsa sınır kararı düzeltir
        self.ml_p = None
        try:
            from . import mlmodel
            self.ml_p = mlmodel.prob({'verdict': self.verdict, 'health': self.health, 'vehicle': self.vehicle})
            if uc not in ('yes', 'no', 'hard'):
                k2 = mlmodel.adjust(kind, score, self.ml_p, self.verdict.get('severity'))
                if k2 != kind:
                    self.verdict['ml'] = True
                    if k2 == 'normal' and self.verdict.get('severity') == 'serious':
                        self.verdict['severity'] = 'minor'      # bulgular duruyor; ama kaza riski taşımadığı ölçüldü → küçük uyarı
                    else:
                        self.verdict['kind'] = k2
                        self.verdict['severity'] = 'serious' if k2 == 'incident' else None
        except Exception:
            pass

    # ----------------------------------------------------------- kök neden
    def _root_cause(self):
        L = self.L; P = L.params
        if self.verdict.get('kind') not in ('crash', 'incident'):
            self.root = {}; return
        end = self.flights[-1][1] if self.flights else L.duration
        # Kırım anı: otopilotun kendi kırım kaydı uçuş bitişinden sonra ise (uçuş algılanamadıysa) onu esas al
        hard_t = [e['a'].get('t') for e in self.verdict.get('evidence', []) if e['k'] in ('cr_stat', 'cr_err', 'cr_msg', 'cr_flip')
                  and isinstance((e.get('a') or {}).get('t'), (int, float))]
        if hard_t and min(hard_t) > end + 2: end = float(min(hard_t))
        if getattr(self, 'fall', None) and self.vehicle == 'Plane' and self.fall['t'] < end:
            end = float(self.fall['t'])   # VTOL: çarpmadan sonra kaldırma motorları yerde dönmeye devam edebilir
        win0 = max(0, end - 240) if self.verdict.get('kind') == 'crash' else (self.flights[0][0] if self.flights else 0)
        cands = []
        def first(cond_list):
            return min(cond_list) if cond_list else None
        # GPS
        tg = first([t for t, s, c in L.errors if s in (7, 11) and c != 0 and t >= win0] +
                   [t for t, x in L.texts if ('gps' in x.lower() and ('lost' in x.lower() or 'glitch' in x.lower())) and t >= win0])
        if tg is not None: cands.append(('gps', tg))
        # EKF
        te = first([t for t, s, c in L.errors if s in (16, 17) and c != 0 and t >= win0] + [t for t, x in L.texts if 'variance' in x.lower() and t >= win0])
        if te is not None: cands.append(('ekf', te))
        # Batarya
        tb = first([t for t, s, c in L.errors if s == 6 and c != 0 and t >= win0] + [t for t, x in L.texts if 'battery' in x.lower() and ('low' in x.lower() or 'critical' in x.lower())])
        if tb is not None: cands.append(('battery', tb))
        # Radyo
        trd = first([t for t, s, c in L.errors if s in (2, 5) and c != 0 and t >= win0])
        if trd is not None: cands.append(('radio', trd))
        # Stall
        if self.vehicle == 'Plane':
            src = L.s('ARSP') if L.s('ARSP').has('Airspeed') else L.s('CTUN')
            f_ = 'Airspeed' if src.has('Airspeed') else 'As'
            if src.has(f_):
                amin = P.get('AIRSPEED_MIN', P.get('ARSPD_FBW_MIN', 9))
                relh = np.interp(src['t'], self.track['t'], self.track['rel']) if self.track is not None else np.full(len(src['t']), 99.0)
                m = (src['t'] >= win0) & (src['t'] <= end - 1) & (src[f_] < amin * 0.75) & self.in_flight(src['t']) & (relh > 8)
                qt = L.s('QTUN')        # VTOL: dikey uçuşta (QTUN kaydı akarken) düşük hava hızı stall değildir
                if qt.has('ThO') and len(qt['ThO']) > 5:
                    qi = np.searchsorted(qt['t'], src['t']); qi = np.clip(qi, 1, len(qt['t']) - 1)
                    near = np.minimum(np.abs(qt['t'][qi] - src['t']), np.abs(qt['t'][qi - 1] - src['t'])) < 1.0
                    m &= ~near
                lastph = [p for p in self.phases if p['name'] == 'landing' and p['t0'] > win0]
                if lastph and self.verdict.get('kind') != 'crash': m &= src['t'] < lastph[-1]['t0']
                if m.any(): cands.append(('stall', float(src['t'][np.argmax(m)])))
        # Titreşim
        v = L.s('VIBE')
        if v.has('VibeZ'):
            m = (v['t'] >= win0) & (v['t'] <= end - 3) & (np.maximum(v['VibeZ'], v['VibeX']) > 60)
            if m.sum() > 5: cands.append(('vibration', float(v['t'][np.argmax(m)])))
        # Pusula
        h = self.health.get('ekf', {})
        if any(f['k'] in ('mag_interf',) for f in h.get('findings', [])):
            x = L.s('XKF4')
            t_ = win0
            if x.has('SM'):
                m = (x['t'] >= win0) & (x['SM'] > 0.6)
                if m.any(): t_ = float(x['t'][np.argmax(m)])
            cands.append(('compass', t_))
        wc0 = min(win0, self.flights[-1][0] - 30) if self.flights else win0     # 'ground mag anomaly' kalkışta yazılır
        tc = first([t for t, x in L.texts if wc0 <= t <= end + 1 and ('mag anomaly' in x.lower() or 'compass error' in x.lower()
                                                                   or 'compass variance' in x.lower() or 'mag inconsistent' in x.lower())] +
                   [t for t, s, c in L.errors if s == 3 and c != 0 and wc0 <= t <= end + 1])
        if tc is not None and not any(c[0] == 'compass' and c[1] <= tc for c in cands):
            cands = [c for c in cands if c[0] != 'compass'] + [('compass', tc)]
        # Güç kesintisi (log havada bitti / kurulu iken kesildi)
        if any(e['k'] in ('cr_log_end', 'cr_log_cut') for e in self.verdict['evidence']):
            cands.append(('power', end - 0.1))
        # Ters takılmış kumanda yüzeyi: zincirin en başı (kalkıştan itibaren)
        if getattr(self, 'surf_rev', None):
            cands.append(('control', max(win0, self.surf_rev[0])))
        # Kontrol kaybı/mekanik (tutum hatası büyük)
        a = L.s('ATT')
        if a.has('DesRoll'):
            err = np.abs(a['DesRoll'] - a['Roll'])
            m = (a['t'] >= win0) & (a['t'] <= end) & (err > 30)
            if m.sum() > 3: cands.append(('control', float(a['t'][np.argmax(m)])))
        # Motor / ESC / pervane (çok rotorlu): bir motor tavana dayanırken diğerleri düşük kalır
        # ya da araç kalkıştan hemen sonra devrilir (yanlış motor sırası/yönü, pervane)
        tm = None
        if self.profile in ('copter', 'heli', 'vtol') or self.vehicle == 'Copter':
            o = L.s('RCOU'); mx, mn = self._mot_limits()
            mch = self.motor_channels(); ch = [c for _, c in mch]; mno = {c: n for n, c in mch}
            if len(ch) >= 3:
                w = (o['t'] >= max(win0, end - 15)) & (o['t'] <= end + 1.5)   # doygunluk devrilmeyle aynı anda başlayabilir
                if self.vehicle == 'Plane' and not getattr(self, 'fall', None):
                    w &= False                  # VTOL: dikey uçuşta tek motor doygunluğu (yön kontrolü) olağandır; yalnız düşüşle birlikte ara
                if self.vehicle == 'Plane':     # VTOL: kaldırma motorları yalnız dikey uçuşta (QTUN akarken) anlamlı
                    qt = L.s('QTUN')
                    if qt.has('ThO') and len(qt['ThO']) > 5:
                        qi = np.clip(np.searchsorted(qt['t'], o['t']), 1, len(qt['t']) - 1)
                        w &= np.minimum(np.abs(qt['t'][qi] - o['t']), np.abs(qt['t'][qi - 1] - o['t'])) < 1.0
                    else:
                        w &= False
                if w.sum() > 5:
                    M = np.vstack([o[c][w] for c in ch]); tt = o['t'][w]
                    # gözlenen tavan (MOT_SPIN_MAX'tan da düşük bir sınır olabilir: ör. PWM aralığı farklı kalibre edilmiş)
                    top = min(mx, float(np.nanmax(M))) if np.nanmax(M) > mn + 300 else mx
                    hi = M.max(axis=0); med = np.median(M, axis=0); lo = M.min(axis=0)
                    # bir motor tavana dayanmış, diğerleri çok aşağıda (itki kaybını telafi ediyor)
                    sat = (hi >= top - 8) & (hi - med > 200)
                    # ya da bir motor tabana çekilmiş, diğerleri yüksek (karşı koldaki itki kaybı)
                    floor = (lo <= mn + 8) & (med - lo > 250) & (med > mn + 250)
                    rs = [r for r in self._runs(tt, sat, 0.4) if r[0] <= end + 0.3][:1]
                    rf = [r for r in self._runs(tt, floor, 1.0) if r[0] <= end][:1]
                    runs = rs + rf
                    if not runs and self.verdict.get('kind') == 'crash':
                        # kronik zayıf motor: kırımdan önceki 10 s boyunca aynı motor ötekilerden belirgin yüksek çalışıyor
                        q = (tt >= end - 10) & (tt <= end - 0.5)
                        if q.sum() > 10:
                            Mq = M[:, q]; am = np.argmax(Mq, axis=0)
                            k0 = int(np.bincount(am, minlength=len(ch)).argmax())
                            others = np.delete(Mq, k0, axis=0)
                            gap = float(np.nanmean(Mq[k0]) - np.nanmean(others))
                            if (am == k0).mean() >= 0.7 and gap >= 130 and np.nanmean(others) > mn + 150:
                                tm = float(tt[q][0])
                                self.motor_fault = {'kind': 'weak', 'm': mno[ch[k0]], 'o': None, 't': tm, 'gap': round(gap)}
                    if runs:
                        tm = float(min(r[0] for r in runs))
                        k = int(np.searchsorted(tt, tm)); k = min(k, len(tt) - 1)
                        col = M[:, k]
                        kw = (tt >= tm) & (tt <= tm + 1.5)
                        colw = np.nanmean(M[:, kw], axis=1) if kw.sum() > 1 else col   # dengeleyen motor birkaç örnek sonra tabana iner
                        if rs and rs[0][0] == tm:      # tavandaki motor itki kaybediyor; tabandaki onu dengeliyor
                            self.motor_fault = {'kind': 'sat', 'm': mno[ch[int(np.argmax(col))]], 'o': mno[ch[int(np.argmin(colw))]], 't': tm}
                        else:                           # tabana çekilen motorun karşısındaki (en yüksek) motor zayıf
                            self.motor_fault = {'kind': 'floor', 'm': mno[ch[int(np.argmax(col))]], 'o': mno[ch[int(np.argmin(col))]], 't': tm}
            # ESC telemetrisi: bir motorun devri diğerleri dönerken birden sıfıra iner (motor/ESC durması, pervane kopması)
            te_ = self._esc_stop(max(win0, end - 15), end - 0.2)
            if te_ is not None:
                self.esc_stop = te_
                if tm is None or te_[0] <= tm:
                    self.motor_fault = {'kind': 'esc', 'm': int(te_[1]), 'o': None, 't': float(te_[0])}
                tm = min(tm, te_[0]) if tm is not None else te_[0]
            if self.flip and self.flights and self.flip[0] - self.flights[-1][0] < 6.5:
                tm = min(tm, self.flip[0]) if tm is not None else self.flip[0]
            if tm is not None:
                cands.append(('motor', tm))
        if not cands and getattr(self, 'yaw_loss', None) is not None:
            cands.append(('motor', self.yaw_loss))     # başka belirti yokken yön kaybı: çoğunlukla motor/ESC itki kaybı
        if not cands:
            self.root = {'cause': 'unknown', 'chain': [], 'prevent': 'unknown', 't': end}; return
        cands = [c for c in cands if c[1] <= end + 2]       # kırımdan sonraki uyarılar neden olamaz
        if not cands:
            self.root = {'cause': 'unknown', 'chain': [], 'prevent': 'unknown', 't': end}; return
        cands.sort(key=lambda c: c[1])
        # Öncelik: kırımdan önceki son 60 s içinde zincirde ilk ortaya çıkan (eski/kalıcı uyarılar değil);
        # EKF genelde GPS/pusula/titreşimin, tutum hatası (control) da motor/güç sorununun sonucudur.
        pool = [c for c in cands if c[1] >= end - 60] or cands
        nonp = [c for c in pool if c[0] != 'power']
        if any(c[0] == 'power' for c in pool) and not any(c[1] >= end - 20 for c in nonp):
            primary = next(c for c in pool if c[0] == 'power')      # log havada aniden kesildi, öncesinde belirti yok
        else:
            pool = nonp or pool
            primary = pool[0]
            if primary[0] == 'ekf' and len(pool) > 1:
                primary = next((c for c in pool if c[0] != 'ekf'), primary)
            if tm is not None and tm >= end - 20 and (primary[0] in ('control', 'compass') or
                                                     (primary[0] == 'vibration' and primary[1] < end - 30)):
                primary = ('motor', tm)   # tutum/yön hatası, kırımdan hemen önceki motor doygunluğunun sonucu
        chain = []
        for name, t in cands:
            chain.append({'t': t, 'step': name})
        # Mod değişimleri zincire
        for t, num, _, rsn in L.modes:
            if t >= cands[0][1] - 1 and t <= end:
                chain.append({'t': t, 'step': 'mode', 'mode': K.mode_name(self.vehicle, num), 'reason': rsn})
        chain.append({'t': end, 'step': 'end_' + self.verdict['kind']})
        chain.sort(key=lambda c: c['t'])
        if primary[0] == 'motor' and self.motor_fault:
            mf = dict(self.motor_fault)
        else:
            mf = None
        self.root = {'cause': primary[0], 't': primary[1], 'chain': chain, 'prevent': primary[0], 'motor': mf,
                     'others': [c[0] for c in cands if c[0] != primary[0]]}

    def motor_channels(self):
        """[(motor_no, 'Cn')]: hangi RCOU kanalının hangi motor olduğu (SERVOn_FUNCTION 33–40 = motor 1–8, 82–85 = 9–12).
        Parametre yoksa (eski sürümler) FRAME_CLASS'a göre C1..Cn."""
        P = self.L.params; o = self.L.s('RCOU'); out = []
        for n in range(1, 17):
            f = P.get(f'SERVO{n}_FUNCTION', P.get(f'RC{n}_FUNCTION'))
            if f is None: continue
            f = int(f)
            m = f - 32 if 33 <= f <= 40 else (f - 73 if 82 <= f <= 85 else None)
            if m and o.has(f'C{n}'): out.append((m, f'C{n}'))
        if len(out) >= 3:
            return sorted(out)
        fr = int(P.get('FRAME_CLASS', 1) or 1)
        nm = {1: 4, 2: 6, 3: 8, 4: 8, 5: 6, 7: 3, 10: 2, 12: 12, 14: 10}.get(fr, 4)   # FRAME_CLASS → motor sayısı
        return [(i, f'C{i}') for i in range(1, nm + 1) if o.has(f'C{i}')]

    def _mot_limits(self):
        """Motor çıkışının gerçek üst/alt sınırı (PWM). ArduCopter çıkışı MOT_SPIN_MAX/MIN ile sınırlar:
        üst = PWM_MIN + (PWM_MAX-PWM_MIN)·SPIN_MAX. Doygunluk bu değere göre aranır (MOT_PWM_MAX'a göre değil)."""
        P = self.L.params
        q = 'Q_M_' if self.vehicle == 'Plane' else 'MOT_'      # VTOL (QuadPlane) kaldırma motorları Q_M_* ile sınırlanır
        lo = float(P.get(q + 'PWM_MIN', 0) or 0) or float(P.get('RC3_MIN', 0) or 0) or 1000.0
        hi = float(P.get(q + 'PWM_MAX', 0) or 0) or float(P.get('RC3_MAX', 0) or 0) or 2000.0
        if hi - lo < 300: lo, hi = 1000.0, 2000.0
        smax = float(P.get(q + 'SPIN_MAX', 0.95) or 0.95); smin = float(P.get(q + 'SPIN_MIN', 0.15) or 0.15)
        if not 0.5 < smax <= 1: smax = 0.95
        if not 0 <= smin < 0.5: smin = 0.15
        return lo + (hi - lo) * smax, lo + (hi - lo) * smin

    def _esc_stop(self, t0, t1):
        """(zaman, motor no) — diğer motorlar >1500 rpm dönerken bir motor ≥0.5 s boyunca ortancanın %15'inin altına düşerse.
        Uçuşun önceki kısmında o ESC'nin normal devir bildirdiği doğrulanır (bildirmeyen ESC yanlış alarm vermesin)."""
        L = self.L
        E = [L.s(f'ESC[{i}]') for i in range(12)]
        E = [(i, e) for i, e in enumerate(E) if e.has('RPM') and len(e['t']) > 20]
        if len(E) < 3 or t1 - t0 < 1: return None
        g = np.arange(t0, t1, 0.1)
        if len(g) < 10: return None
        R = np.vstack([np.interp(g, e['t'], e['RPM']) for _, e in E])
        med = np.median(R, axis=0)
        f0 = self.flights[-1][0] if self.flights else 0
        best = None
        for j, (i, e) in enumerate(E):
            pm = (e['t'] > f0 + 5) & (e['t'] < t0)
            if pm.sum() > 10:
                allm = np.median(np.vstack([np.interp(e['t'][pm], x['t'], x['RPM']) for _, x in E]), axis=0)
                ok = np.nanmedian(e['RPM'][pm] / np.maximum(allm, 1))
                if not (0.5 < ok < 2.0): continue
            bad = (R[j] < 0.15 * med) & (med > 1500)
            for a, b in self._runs(g, bad, 0.5)[:1]:
                if best is None or a < best[0]: best = (float(a), i + 1)
        return best

    # ------------------------------------------------------ parametre denetimi
    def _params(self):
        P = self.L.params; out = []
        if not P:
            self.param_findings = [{'sev': 1, 'text': F('pa_none')}]; return
        def add(sev, key, **kw): out.append({'sev': sev, 'text': F(key, **kw), 'param': kw.get('p')})
        ac = P.get('ARMING_CHECK')
        if ac is not None and ac == 0: add(2, 'pa_arming_off', p='ARMING_CHECK')
        sk = P.get('ARMING_SKIPCHK')
        if sk not in (None, 0): add(1, 'pa_skipchk', p='ARMING_SKIPCHK', v=int(sk))
        bm = P.get('BATT_MONITOR')
        if bm is not None:
            if bm == 0: add(2, 'pa_batt_mon_off', p='BATT_MONITOR')
            elif bm == 3: add(1, 'pa_batt_volt_only', p='BATT_MONITOR')
        if P.get('BATT_FS_LOW_ACT', 1) == 0 and bm not in (None, 0): add(2, 'pa_batt_fs_off', p='BATT_FS_LOW_ACT')
        if P.get('BATT_LOW_VOLT', 1) == 0 and P.get('BATT_LOW_MAH', 0) == 0 and bm not in (None, 0): add(1, 'pa_batt_low_unset', p='BATT_LOW_VOLT')
        if P.get('BATT_CAPACITY', 1) == 0 and bm not in (None, 0): add(1, 'pa_batt_cap', p='BATT_CAPACITY')
        if self.vehicle == 'Plane':
            if P.get('THR_FAILSAFE', 1) == 0: add(2, 'pa_thr_fs_off', p='THR_FAILSAFE')
            if P.get('FS_LONG_ACTN', 1) == 0 and P.get('THR_FAILSAFE', 1) != 0: add(1, 'pa_fs_long_none', p='FS_LONG_ACTN')
            if P.get('ARSPD_TYPE', 1) == 0: add(1, 'pa_no_airspeed', p='ARSPD_TYPE')
            amin = P.get('AIRSPEED_MIN', P.get('ARSPD_FBW_MIN'))
            if amin is not None and amin < 9: add(1, 'pa_as_min_low', p='AIRSPEED_MIN', v=amin)
            if P.get('STALL_PREVENTION', 1) == 0: add(1, 'pa_stall_prev', p='STALL_PREVENTION')
            if P.get('THR_MAX', 100) < 70: add(1, 'pa_thr_max', p='THR_MAX', v=P['THR_MAX'])
        else:
            if P.get('FS_THR_ENABLE', 1) == 0: add(2, 'pa_thr_fs_off', p='FS_THR_ENABLE')
            if P.get('FS_EKF_ACTION', 1) == 0: add(1, 'pa_ekf_fs_off', p='FS_EKF_ACTION')
            if P.get('MOT_THST_HOVER', 0.35) > 0.7: add(1, 'pa_hover_high', p='MOT_THST_HOVER', v=round(P['MOT_THST_HOVER'], 2))
        if P.get('FS_GCS_ENABL', 1) == 0 and P.get('FS_GCS_ENABLE', 1) == 0: add(0, 'pa_gcs_fs_off', p='FS_GCS_ENABL')
        if P.get('COMPASS_USE', 1) == 0 and P.get('COMPASS_ENABLE', 1) != 0: add(1, 'pa_compass_off', p='COMPASS_USE')
        if P.get('LOG_BITMASK', 1) == 0: add(1, 'pa_log_off', p='LOG_BITMASK')
        if P.get('AHRS_EKF_TYPE', 3) not in (2, 3, 10, 11): add(1, 'pa_ekf_type', p='AHRS_EKF_TYPE', v=P.get('AHRS_EKF_TYPE'))
        if P.get('GPS_TYPE', 1) == 0: add(2, 'pa_gps_off', p='GPS_TYPE')
        if P.get('RTL_AUTOLAND', 1) == 0 and self.vehicle == 'Plane': add(0, 'pa_rtl_autoland', p='RTL_AUTOLAND')
        if P.get('INS_HNTCH_ENABLE', 0) == 0 and self.vehicle == 'Copter': add(0, 'pa_notch_off', p='INS_HNTCH_ENABLE')
        if not out: add(0, 'pa_ok')
        self.param_findings = out

    # ---------------------------------------------------------- olgular (QA)
    def _facts(self):
        L = self.L; f = {}
        f['duration'] = L.duration
        f['vehicle'] = self.vehicle; f['version'] = L.version
        if self.flights:
            f['takeoff_t'] = self.flights[0][0]; f['land_t'] = self.flights[-1][1]
            f['flight_time'] = sum(b - a for a, b in self.flights); f['n_flights'] = len(self.flights)
        if self.armed:
            f['arm_t'] = self.armed[0][0]; f['disarm_t'] = self.armed[-1][1]
        tr = self.track
        if tr is not None:
            i = int(np.nanargmax(tr['rel'])); f['max_alt'] = float(tr['rel'][i]); f['max_alt_t'] = float(tr['t'][i])
            d = hav(tr['lat'][0], tr['lon'][0], tr['lat'], tr['lon'])
            j = int(np.nanargmax(d)); f['max_dist'] = float(d[j]); f['max_dist_t'] = float(tr['t'][j])
            seg = hav(tr['lat'][:-1], tr['lon'][:-1], tr['lat'][1:], tr['lon'][1:])
            f['distance'] = float(np.nansum(seg[seg < 500]))
            f['home'] = (float(tr['lat'][0]), float(tr['lon'][0]))
        g = L.s('GPS')
        if g.has('Spd'):
            k = int(np.nanargmax(g['Spd'])); f['max_gs'] = float(g['Spd'][k]); f['max_gs_t'] = float(g['t'][k])
        src = L.s('ARSP') if L.s('ARSP').has('Airspeed') else L.s('CTUN')
        fa = 'Airspeed' if src.has('Airspeed') else ('As' if src.has('As') else None)
        if fa:
            k = int(np.nanargmax(src[fa])); f['max_as'] = float(src[fa][k]); f['max_as_t'] = float(src['t'][k])
        b = L.s('BAT')
        if b.has("Volt") and np.any(b["Volt"] > 1):
            k = int(np.nanargmin(np.where(b['Volt'] > 1, b['Volt'], np.nan))); f['min_volt'] = float(b['Volt'][k]); f['min_volt_t'] = float(b['t'][k])
        if b.has('CurrTot'): f['used_mah'] = float(np.nanmax(b['CurrTot']))
        f['modes'] = [(t, K.mode_name(self.vehicle, n), r) for t, n, _, r in L.modes]
        f['first_error'] = next(((t, s, c) for t, s, c in L.errors if c != 0), None)
        f['profile'] = self.profile
        self.facts = f
        self.summary = {'overall': self.overall, 'verdict': self.verdict.get('kind'), **{k: v for k, v in f.items() if not isinstance(v, list)}}

    # ---------------------------------------------------------- dışa aktarım
    def to_json(self):
        """Arşiv ve AI için özet (dizi verisi içermez)."""
        def clean(o):
            if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)): return [clean(v) for v in o]
            if isinstance(o, (np.floating,)): return float(o)
            if isinstance(o, (np.integer,)): return int(o)
            if isinstance(o, float) and not math.isfinite(o): return None
            return o
        return clean({'vehicle': self.vehicle, 'version': self.L.version, 'duration': self.L.duration,
                      'overall': self.overall, 'verdict': self.verdict, 'root': self.root, 'health': self.health,
                      'phases': self.phases, 'flights': self.flights, 'armed': self.armed,
                      'params': self.param_findings, 'facts': self.facts, 'profile': self.profile,
                      'anomalies': self.anomalies, 'pilot': self.pilot, 'wind': self.wind, 'weather': self.weather,
                      'events': [e for e in self.events if e['sev'] > 0 or e['cat'] in ('mode', 'flight')][:300]})
