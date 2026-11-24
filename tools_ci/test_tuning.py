"""PID / TECS ayar önerisi testleri (sentetik uçuş verisi; bilinen kusur → beklenen öneri)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.loader import LogData, Series
from app.core import tuning


class A_:
    def __init__(self, L, prof, dur): self.L = L; self.profile = prof; self.flights = [(0.0, dur)]


def _first_order(x, hz, tau):
    a = 1.0 / (1.0 + tau * hz); y = np.zeros_like(x)
    for i in range(1, len(x)): y[i] = y[i - 1] + a * (x[i] - y[i - 1])
    return y


def _pid(t, des, act, kp=1.0, kd=0.0, ff=0.5, i_bias=0.0):
    e = des - act
    return Series(t=t, Tar=des, Act=act, P=kp * e, I=np.full_like(t, i_bias) + 0.01 * np.cumsum(e) / len(e),
                  D=kd * np.gradient(e) * 50, FF=ff * des)


def make(case, prof='plane', dur=300.0, hz=50.0, seed=1):
    rnd = np.random.default_rng(seed)
    t = np.arange(0, dur, 1 / hz)
    des = 30 * np.sign(np.sin(2 * np.pi * t / 6.0)) * (np.sin(2 * np.pi * t / 23) > -0.3) + 5 * rnd.standard_normal(len(t)).cumsum() / 200
    des = _first_order(des, hz, 0.15)
    tau = {'good': 0.05, 'slug': 0.05, 'osc': 0.05, 'over': 0.05}.get(case, 0.05)
    act = _first_order(des, hz, tau)
    if case == 'slug': act *= 0.55
    if case == 'over': act *= 1.45
    if case == 'osc': act += 9 * np.sin(2 * np.pi * 7.0 * t) * (1 + 0.2 * rnd.standard_normal(len(t)))
    act += 0.4 * rnd.standard_normal(len(t))
    L = LogData(); L.duration = dur
    kd = 0.8 if case == 'osc' else 0.05
    pr = _pid(t, des, act, kd=kd)
    if prof == 'copter':
        pr = Series({k: (v / 57.2958 if k in ('Tar', 'Act') else v) for k, v in pr.items()}); pr['t'] = t
    L.msgs['PIDR'] = pr; L.msgs['PIDP'] = _pid(t, des * 0.5, _first_order(des * 0.5, hz, 0.05), kd=0.05)
    if prof == 'copter':
        L.msgs['PIDP'] = Series({k: (v / 57.2958 if k in ('Tar', 'Act') else v) for k, v in L.msgs['PIDP'].items()}); L.msgs['PIDP']['t'] = t
    L.params = {'RLL_RATE_P': 0.08, 'RLL_RATE_I': 0.15, 'RLL_RATE_D': 0.004, 'RLL_RATE_FF': 0.35, 'RLL2SRV_TCONST': 0.5,
                'PTCH_RATE_P': 0.08, 'PTCH_RATE_D': 0.004, 'PTCH_RATE_FF': 0.4, 'PTCH2SRV_TCONST': 0.5,
                'ATC_RAT_RLL_P': 0.135, 'ATC_RAT_RLL_D': 0.0036, 'ATC_RAT_RLL_I': 0.135, 'ATC_ANG_RLL_P': 4.5,
                'ATC_RAT_PIT_P': 0.135, 'ATC_RAT_PIT_D': 0.0036, 'ATC_ANG_PIT_P': 4.5,
                'TECS_CLMB_MAX': 5.0, 'TECS_SINK_MAX': 5.0, 'TECS_PTCH_DAMP': 0.3, 'TECS_THR_DAMP': 0.5, 'TECS_TIME_CONST': 5.0,
                'THR_MAX': 100, 'THR_MIN': 0, 'TRIM_THROTTLE': 45, 'MOT_THST_HOVER': 0.35, 'MOT_HOVER_LEARN': 0}
    if prof == 'plane':
        # TECS: tam gazda yalnız 2 m/s tırmanabilen uçak, düz uçuş gazı %60, irtifada 20 sn periyotlu salınım
        tt = np.arange(0, dur, 0.1)
        climb = (tt % 120) < 40
        dh = np.where(climb, 2.0 + 0.2 * rnd.standard_normal(len(tt)), 0.1 * rnd.standard_normal(len(tt)))
        h = 100 + np.cumsum(dh) * 0.1
        hdem = h + np.where(climb, -15, 0) + (6 * np.sin(2 * np.pi * tt / 20.0) if case == 'porp' else 0.3 * rnd.standard_normal(len(tt)))
        th = np.where(climb, 1.0, 0.60 + 0.02 * rnd.standard_normal(len(tt)))
        sp = 20 + np.where(climb, -3, 0) + 0.3 * rnd.standard_normal(len(tt))
        L.msgs['TECS'] = Series(t=tt, h=h, hdem=hdem, dh=dh, sp=sp, spdem=np.full_like(tt, 20.0), th=th, f=np.zeros_like(tt))
    if prof == 'copter':
        tt = np.arange(0, dur, 0.1)
        L.msgs['CTUN'] = Series(t=tt, ThO=0.46 + 0.01 * rnd.standard_normal(len(tt)), Alt=30 + 0.05 * rnd.standard_normal(len(tt)),
                                DAlt=np.full_like(tt, 30.0), CRt=0.05 * rnd.standard_normal(len(tt)))
    return A_(L, prof, dur)


def recs(res, axis_key):
    a = next(x for x in res['axes'] if x['axis'] == axis_key)
    return {r['param']: r for r in a['recs']}, a


def run():
    ok = 0; fails = []

    def check(name, cond, info=''):
        nonlocal ok
        if cond: ok += 1
        else: fails.append(f'{name}: {info}')

    r = tuning.analyze(make('good'), 'tr'); rr, a = recs(r, 'roll')
    check('good', a['status'] == 'good' and not rr, a.get('metrics'))
    r = tuning.analyze(make('slug'), 'en'); rr, a = recs(r, 'roll')
    check('sluggish->FF up', 'RLL_RATE_FF' in rr and rr['RLL_RATE_FF']['new'] > 0.35 and rr['RLL_RATE_FF']['new'] <= 0.35 * 1.26, (a['metrics'], rr))
    r = tuning.analyze(make('over'), 'en'); rr, a = recs(r, 'roll')
    check('overshoot->down', any(v['new'] < v['cur'] for v in rr.values()), (a['metrics'], rr))
    r = tuning.analyze(make('osc'), 'ar'); rr, a = recs(r, 'roll')
    check('osc->D down', a['status'] == 'bad' and 'RLL_RATE_D' in rr and rr['RLL_RATE_D']['new'] < 0.004, (a['metrics'], rr))
    check('osc freq ~7Hz', abs((a['metrics'].get('f_osc') or 0) - 7.0) < 0.6, a['metrics'])
    # TECS
    r = tuning.analyze(make('good'), 'tr'); tr, a = recs(r, 'tecs')
    check('tecs clmb', 'TECS_CLMB_MAX' in tr and 1.5 <= tr['TECS_CLMB_MAX']['new'] <= 3.75, (a['metrics'], tr))
    check('tecs trim', 'TRIM_THROTTLE' in tr and 54 <= tr['TRIM_THROTTLE']['new'] <= 57, tr.get('TRIM_THROTTLE'))
    r = tuning.analyze(make('porp'), 'tr'); tr, a = recs(r, 'tecs')
    check('tecs porpoise', 'TECS_PTCH_DAMP' in tr and tr['TECS_PTCH_DAMP']['new'] > 0.3, (a['metrics'], tr))
    # Copter (rad/s ölçeği) + hover
    r = tuning.analyze(make('osc', prof='copter'), 'tr'); rr, a = recs(r, 'roll')
    check('copter osc', 'ATC_RAT_RLL_D' in rr or 'ATC_RAT_RLL_P' in rr, (a['metrics'], rr))
    rr, a = recs(r, 'alt')
    check('copter hover', 'MOT_THST_HOVER' in rr and abs(rr['MOT_THST_HOVER']['new'] - 0.46) < 0.02, rr)
    r = tuning.analyze(make('good', prof='copter'), 'tr'); rr, a = recs(r, 'pitch')
    check('copter good pitch', not rr, (a['metrics'], rr))
    # .param çıktısı geçerli satırlar içermeli
    pf = tuning.param_file(tuning.analyze(make('slug'), 'tr'), 'Plane')
    check('param file', any(l.startswith('RLL_RATE_FF,') for l in pf.splitlines()), pf)
    # veri yok
    from app.core.loader import LogData as LD
    A0 = A_(LD(), 'plane', 100); r = tuning.analyze(A0, 'tr')
    check('nodata', all(x['status'] == 'na' for x in r['axes']), r)
    n = 13
    print(f'tuning: {ok}/{n} OK'); [print('  FAIL', f) for f in fails]
    return ok == n


if __name__ == '__main__':
    sys.exit(0 if run() else 1)
