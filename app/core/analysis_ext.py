"""Analiz eklentileri (v1.0.2): profile özel denetimler, kart seri numarası, rüzgâr kestirimi,
pilot performans ölçütleri ve ML anomali tespiti."""
from __future__ import annotations
import math, re
import numpy as np


def _F(key, **kw):
    return {'k': key, 'a': kw}


def _fin(a):
    a = np.asarray(a, dtype=float)
    return a[np.isfinite(a)]


MANUAL_MODES = {'Plane': {0, 2, 4, 5, 17, 23}, 'Copter': {0, 1, 2, 13}}  # MANUAL, STABILIZE, ACRO, FBWA, QSTABILIZE, QACRO …


class ExtMixin:
    # --------------------------------------------------- profile özel denetimler
    def _profile_checks(self):
        L = self.L; P = L.params; pr = self.profile
        if pr in ('copter', 'heli'):
            o = L.s('RCOU'); fnd = []; met = {}; sc = 100
            chans = [c for _, c in self.motor_channels()]
            if pr == 'copter' and len(chans) >= 3:
                m = self.in_flight(o['t']) if self.flights else np.ones(len(o['t']), bool)
                means = np.array([np.nanmean(o[c][m]) if m.any() else np.nan for c in chans])
                if np.all(np.isfinite(means)):
                    avg = float(np.mean(means)); dev = float(np.max(np.abs(means - avg)))
                    met['motor_pwm_mean'] = avg; met['motor_imbalance_us'] = dev
                    k = chans[int(np.argmax(np.abs(means - avg)))]
                    if dev > 75: sc -= 30; fnd.append(_F('mot_imbalance', ch=k, v=round(dev)))
                    elif dev > 45: sc -= 12; fnd.append(_F('mot_imbalance', ch=k, v=round(dev)))
                    hi = float(np.nanmax(means)); mx = P.get('MOT_PWM_MAX', 1950) or 1950
                    met['motor_headroom_us'] = float(mx - hi)
                    if mx - hi < 100: sc -= 15; fnd.append(_F('mot_headroom', v=round(mx - hi)))
            hov = P.get('MOT_THST_HOVER')
            if hov is not None:
                met['hover_thr'] = float(hov)
                if hov > 0.6: sc -= 15; fnd.append(_F('pa_hover_high', p='MOT_THST_HOVER', v=round(hov, 2)))
            if met: self._dom('motors', sc, met, fnd)
        if pr == 'vtol':
            fnd = []; met = {}; sc = 100
            qm = [(t, n) for t, n, _, _ in L.modes]
            from .profiles import Q_MODES
            trans = 0; q_time = 0.0; prev = None
            for i, (t, n) in enumerate(qm):
                isq = n in Q_MODES
                if prev is not None and isq != prev: trans += 1
                prev = isq
                if isq:
                    t_end = qm[i + 1][0] if i + 1 < len(qm) else L.duration
                    q_time += max(0.0, t_end - t)
            met['transitions'] = trans; met['vtol_time_s'] = q_time
            fnd.append(_F('vtol_summary', n=trans, t=round(q_time / 60, 1)))
            if P.get('Q_ASSIST_SPEED', 1) == 0: sc -= 15; fnd.append(_F('vtol_assist_off'))
            if P.get('Q_TRANSITION_MS', 5000) < 2000: sc -= 5; fnd.append(_F('vtol_trans_short', v=int(P.get('Q_TRANSITION_MS'))))
            qt = L.s('QTUN')
            if qt.has('ThO') or qt.has('ThH'):
                k = 'ThO' if qt.has('ThO') else 'ThH'
                th = _fin(qt[k]); th = th * (100 if len(th) and np.nanmax(th) <= 1.05 else 1)
                if len(th):
                    p_ = float((th >= 95).mean() * 100); met['q_thr_full_pct'] = p_
                    if p_ > 10: sc -= 20; fnd.append(_F('vtol_thr_full', v=round(p_, 1)))
            self._dom('vtol', sc, met, fnd)

    # --------------------------------------------------- kart seri numarası
    def _serial(self):
        L = self.L
        rx = re.compile(r'^(\S+)\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})')
        for _, txt in L.texts[:400]:
            m = rx.match(txt)
            if m:
                self.serial = ''.join(m.group(2, 3, 4)).upper(); self.board_name = m.group(1); break
        if not self.serial:
            sn = L.params.get('BRD_SERIAL_NUM')
            if sn: self.serial = f'SN{int(sn)}'
        self.facts['serial'] = self.serial

    # --------------------------------------------------- logdan rüzgâr
    def _wind(self):
        L = self.L
        x = L.s('XKF2') if L.s('XKF2').has('VWN') else L.s('NKF2')
        if not x.has('VWN'): return
        m = self.in_flight(x['t']) if self.flights else np.ones(len(x['t']), bool)
        if not m.any(): return
        vn, ve = x['VWN'][m], x['VWE'][m]
        sp = np.sqrt(vn ** 2 + ve ** 2)
        mn, me = float(np.nanmean(vn)), float(np.nanmean(ve))
        frm = (math.degrees(math.atan2(-me, -mn)) + 360) % 360
        self.wind = {'mean': float(np.nanmean(sp)), 'max': float(np.nanmax(sp)), 'from_deg': frm}
        self.facts['wind_mean'] = self.wind['mean']; self.facts['wind_max'] = self.wind['max']; self.facts['wind_from'] = frm
        if self.wind['mean'] > self.th['wind_warn']:
            self.param_findings.append({'sev': 1, 'text': _F('wind_high', v=round(self.wind['mean'], 1), lim=self.th['wind_warn']), 'param': None})

    # --------------------------------------------------- pilot performansı
    def _pilot_metrics(self):
        if not self.flights or self.track is None: return
        L = self.L; tr = self.track; sc = {}; met = {}
        t = tr['t']; rel = tr['rel']
        # İniş kalitesi
        a, b = self.flights[-1]
        if self.verdict.get('kind') == 'crash':
            sc['landing'] = 0; met['landing_vz'] = None
        else:
            w = (t > b - 3) & (t <= b + 0.5)
            vz = float(np.nanmean(np.gradient(rel[w], t[w]))) if w.sum() > 3 else 0.0
            att = L.s('ATT'); r_ = 0.0
            if att.has('Roll'):
                ww = (att['t'] > b - 2) & (att['t'] <= b + 1)
                if ww.any(): r_ = float(np.nanmax(np.abs(att['Roll'][ww])))
            w2 = (t > b - 12) & (t <= b + 2)
            bounce = 0
            if w2.sum() > 5:
                rr = rel[w2]; low = np.flatnonzero(rr < 1.5)
                if len(low): bounce = int(np.sum(np.diff(rr[low[0]:]) > 0.8))
            met.update(landing_vz=round(vz, 2), landing_roll=round(r_, 1), bounces=bounce)
            sc['landing'] = max(0, min(100, 100 - max(0, abs(vz) - 0.5) * (100 / max(0.5, self.th['landing_vz_hard'] * 2))
                                       - max(0, r_ - 10) * 2 - min(3, bounce) * 12))
        # Gaz yönetimi
        ct = L.s('CTUN')
        if ct.has('ThO'):
            m = self.in_flight(ct['t'])
            th = ct['ThO'][m]
            th = th * (100 if len(th) and np.nanmax(th) <= 1.05 else 1)
            th = _fin(th)
            if len(th) > 10:
                full = float((th >= 98).mean() * 100)
                jerk = float(np.nanmean(np.abs(np.diff(th))))
                met.update(thr_full_pct=round(full, 1), thr_mean=round(float(th.mean()), 1), thr_jerk=round(jerk, 2))
                sc['throttle'] = max(0, min(100, 100 - full * 1.2 - max(0, jerk - 3) * 4))
        # Hız kontrolü (uçak)
        h = self.health.get('airspeed')
        if h: sc['speed'] = max(0, min(100, 100 - h['metrics'].get('below_min_pct', 0) * 4)); met['below_min_pct'] = round(h['metrics'].get('below_min_pct', 0), 1)
        # Yumuşaklık (yatış hızı)
        att = L.s('ATT')
        if att.has('Roll'):
            m = self.in_flight(att['t'])
            if m.sum() > 20:
                rr = np.gradient(att['Roll'][m], att['t'][m]); rr = _fin(rr)
                rms = float(np.sqrt(np.mean(np.clip(rr, -400, 400) ** 2)))
                met['roll_rate_rms'] = round(rms, 1)
                sc['smooth'] = max(0, min(100, 100 - max(0, rms - 12) * 2.5))
        nt = L.s('NTUN')
        ae = next((k for k in ('AltE', 'AltErr') if nt.has(k)), None)
        if ae:
            m = self.in_flight(nt['t']); e = _fin(np.abs(nt[ae][m]))
            if len(e): met['alt_err'] = round(float(e.mean()), 2); sc['alt_hold'] = max(0, min(100, 100 - max(0, e.mean() - 1) * 6))
        if nt.has('XT'):
            m = self.in_flight(nt['t']); e = _fin(np.abs(nt['XT'][m]))
            if len(e): met['xtrack'] = round(float(e.mean()), 2); sc['nav'] = max(0, min(100, 100 - max(0, e.mean() - 2) * 3))
        # Manuel uçuş payı
        man = MANUAL_MODES.get(self.vehicle, set())
        mt = 0.0; fl = sum(b_ - a_ for a_, b_ in self.flights) or 1
        md = L.modes
        for i, (tm, n, _, _) in enumerate(md):
            te = md[i + 1][0] if i + 1 < len(md) else L.duration
            if n in man:
                for a_, b_ in self.flights:
                    mt += max(0.0, min(te, b_) - max(tm, a_))
        met['manual_pct'] = round(float(100 * mt / fl), 1)
        sc = {k: int(round(v)) for k, v in sc.items()}
        self.pilot = {'scores': sc, 'metrics': met, 'overall': int(round(np.mean(list(sc.values())))) if sc else None}

    # --------------------------------------------------- anomali (ML)
    def _anomaly(self):
        from . import anomaly
        r = anomaly.detect(self)
        self.anomalies = r['items']; self.anomaly_index = r['index']; self.anomaly_info = r
        self.facts['anomaly_index'] = r['index']
        if r['items']:
            top = r['items'][0]
            self.events.append({'t': top['t0'], 'cat': 'ev', 'sev': 1, 'text': _F('anom_ev', s=top['score'], f=top['feats'][0]['k'] if top['feats'] else '-')})
            self.events.sort(key=lambda e: e['t'])
