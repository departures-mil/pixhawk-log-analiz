"""Log okuyucu: ArduPilot DataFlash .BIN/.log ve MAVLink .tlog dosyalarını ortak bir yapıya dönüştürür.

Büyük dosyalar (GB seviyesi) için yalnızca analizde gereken mesaj türleri okunur ve yüksek frekanslı
mesajlar seyreltilir; böylece bellek kullanımı sınırlı kalır.
"""
from __future__ import annotations
import os, math, time
import numpy as np

# Okunacak mesaj türleri ve azami örnekleme hızı (Hz; 0 = hepsi)
WANT = {
    'ATT': 25, 'AHR2': 5, 'POS': 10, 'GPS': 10, 'GPA': 5, 'BARO': 10, 'BAT': 10, 'CURR': 10,
    'CTUN': 10, 'NTUN': 10, 'TECS': 10, 'AETR': 10, 'ARSP': 10, 'AOA': 5, 'VIBE': 10, 'IMU': 25,
    'MAG': 10, 'RCIN': 10, 'RCOU': 10, 'RSSI': 2, 'POWR': 2, 'PM': 0, 'STAT': 0, 'XKF4': 5, 'NKF4': 5,
    'XKF1': 5, 'XKF3': 5, 'XKFS': 0, 'MODE': 0, 'MSG': 0, 'ERR': 0, 'EV': 0, 'ARM': 0, 'PARM': 0,
    'VER': 0, 'CMD': 0, 'ORGN': 0, 'RPM': 5, 'ESC': 5, 'DSF': 0, 'PIDR': 50, 'PIDP': 50, 'PIDY': 50, 'RATE': 50,
    'RAD': 2, 'MAV': 2, 'XKF2': 2, 'NKF2': 2, 'QTUN': 10, 'TSYN': 0,
}


class Series(dict):
    """Bir mesaj türünün alanları: alan adı -> numpy dizisi. 't' = saniye (log başından)."""
    @property
    def t(self):
        return self.get('t', np.array([]))

    def has(self, f):
        return f in self and len(self[f]) > 0

    def at(self, f, t):
        """t anına en yakın değer."""
        if not self.has(f):
            return None
        i = int(np.searchsorted(self['t'], t))
        i = min(max(i, 0), len(self['t']) - 1)
        if i > 0 and abs(self['t'][i - 1] - t) < abs(self['t'][i] - t):
            i -= 1
        return float(self[f][i])


class LogData:
    def __init__(self):
        self.path = ''
        self.kind = 'bin'
        self.size = 0
        self.msgs: dict[str, Series] = {}
        self.params: dict[str, float] = {}
        self.texts: list[tuple[float, str]] = []
        self.modes: list[tuple[float, int, str, int]] = []   # t, num, ad, neden
        self.errors: list[tuple[float, int, int]] = []       # t, subsys, code
        self.events: list[tuple[float, int]] = []            # t, id
        self.arm: list[tuple[float, bool]] = []
        self.version = ''
        self.vehicle = 'Plane'
        self.board = ''
        self.duration = 0.0
        self.t0_us = 0
        self.gps_time0 = None  # (t_log, unix) eşlemesi
        self.types_seen: dict[str, int] = {}
        self.truncated = False

    def s(self, name) -> Series:
        return self.msgs.get(name, Series())

    def unix_at(self, t):
        if not self.gps_time0:
            return None
        return self.gps_time0[1] + (t - self.gps_time0[0])


def _finish(acc: dict) -> dict:
    out = {}
    for name, inst in acc.items():
        for key, cols in inst.items():
            s = Series()
            for f, vals in cols.items():
                try:
                    s[f] = np.asarray(vals, dtype=float)
                except Exception:
                    continue
            nm = name if key is None else f'{name}[{key}]'
            out[nm] = s
            if key is not None and name not in out:
                out[name] = s
    return out


def _vehicle_from(text):
    t = text.lower()
    if 'arduplane' in t: return 'Plane'
    if 'arducopter' in t: return 'Copter'
    if 'ardurover' in t or 'rover' in t: return 'Rover'
    if 'ardusub' in t: return 'Sub'
    if 'heli' in t: return 'Copter'
    return None


NONE_KEY = ('ATT', 'POS', 'CTUN', 'NTUN', 'TECS', 'AETR', 'RCIN', 'RCOU', 'PM', 'STAT', 'AHR2', 'AOA', 'POWR', 'RSSI', 'DSF', 'ORGN', 'RATE',
            'CMD', 'PIDR', 'PIDP', 'PIDY', 'RAD', 'MAV')
LOADER_VER = 4


def load(path: str, progress=None, cancel=None, use_cache=True) -> LogData:
    """Logu okur. Aynı dosya ikinci kez açıldığında önbellekten (saniyenin altında) gelir."""
    ext = os.path.splitext(path)[1].lower()
    if use_cache:
        try:
            from . import cache
            L = cache.get(path)
            if L is not None:
                if progress: progress(1.0)
                return L
        except Exception:
            pass
    if ext in ('.tlog',):
        L = _load_tlog(path, progress, cancel)
    elif ext == '.log':
        L = _load_bin(path, progress, cancel)
    else:
        try:
            L = _load_bin_fast(path, progress, cancel)
        except InterruptedError:
            raise
        except Exception:
            import traceback; traceback.print_exc()
            L = _load_bin(path, progress, cancel)
    if use_cache:
        try:
            from . import cache
            cache.put(path, L)
        except Exception:
            pass
    return L


def _load_bin_fast(path, progress=None, cancel=None) -> LogData:
    from . import fastbin as FB
    L = LogData(); L.path = path; L.size = os.path.getsize(path); L.kind = 'bin'
    rd = FB.Reader(path, WANT, NONE_KEY, progress=(lambda f: progress(f * 0.97)) if progress else None, cancel=cancel).run()
    arrs = rd.arrays()
    if not arrs:
        raise ValueError('no messages')
    L.types_seen = dict(rd.counts)
    # Zaman başlangıcı: ilk sıfırdan büyük TimeUS
    t0 = None
    for n, (f, a) in arrs.items():
        if 'TimeUS' in a.dtype.names and len(a):
            tt = a['TimeUS']; tt = tt[tt > 0]
            if len(tt):
                v = int(tt.min()); t0 = v if t0 is None else min(t0, v)
    t0 = t0 or 0

    def tsec(f, a):
        if 'TimeUS' in a.dtype.names: return (a['TimeUS'].astype(np.float64) - t0) / 1e6
        if 'TimeMS' in a.dtype.names: return (a['TimeMS'].astype(np.float64) * 1000 - t0) / 1e6
        return np.zeros(len(a))

    def S(b):
        return b.split(b'\0', 1)[0].decode('utf-8', 'replace') if isinstance(b, bytes) else str(b)
    special = {}
    for n in ('PARM', 'MSG', 'VER', 'MODE', 'ERR', 'EV', 'ARM'):
        if n in arrs: special[n] = arrs.pop(n)
    if 'PARM' in special:
        f, a = special['PARM']
        for nm, v in zip(a['Name'], FB.col(f, a, 'Value')):
            L.params[S(nm)] = float(v)
    if 'MSG' in special:
        f, a = special['MSG']
        for t, m in zip(tsec(f, a), a['Message']):
            txt = S(m).strip(); L.texts.append((float(t), txt))
            v = _vehicle_from(txt)
            if v and not L.version: L.version = txt; L.vehicle = v
    if 'VER' in special:
        f, a = special['VER']
        if len(a):
            r = a[-1]
            L.board = str(int(r['BU'])) if 'BU' in a.dtype.names else (str(int(r['APJ'])) if 'APJ' in a.dtype.names else '')
            if 'FWS' in a.dtype.names:
                fw = S(r['FWS'])
                if fw:
                    L.version = fw; v = _vehicle_from(fw)
                    if v: L.vehicle = v
    if 'MODE' in special:
        f, a = special['MODE']; nm = a.dtype.names
        mn = a['ModeNum'] if 'ModeNum' in nm else a['Mode']
        rs = a['Rsn'] if 'Rsn' in nm else np.full(len(a), -1)
        L.modes = [(float(t), int(m), '', int(r)) for t, m, r in zip(tsec(f, a), mn, rs)]
    if 'ERR' in special:
        f, a = special['ERR']
        L.errors = [(float(t), int(s_), int(c)) for t, s_, c in zip(tsec(f, a), a['Subsys'], a['ECode'])]
    if 'EV' in special:
        f, a = special['EV']
        L.events = [(float(t), int(i)) for t, i in zip(tsec(f, a), a['Id'])]
    if 'ARM' in special:
        f, a = special['ARM']
        if 'ArmState' in a.dtype.names:
            L.arm = [(float(t), bool(x)) for t, x in zip(tsec(f, a), a['ArmState'])]
    out = {}
    for n, (f, a) in arrs.items():
        t = tsec(f, a)
        cols = [c for c in a.dtype.names if c not in ('TimeUS', 'TimeMS')]
        kf = None if n in NONE_KEY else next((k for k in ('I', 'C', 'Instance') if k in a.dtype.names and a.dtype[k].kind in 'iuf'), None)
        keys = np.unique(a[kf]) if kf else [None]
        for k in keys:
            m = (a[kf] == k) if kf else slice(None)
            s = Series(); s['t'] = t[m]
            for c in cols:
                v = FB.col(f, a, c)
                if v is not None: s[c] = v[m]
            kk = None if k is None else (int(k) if a.dtype[kf].kind in 'iu' else float(k))
            nm = n if kk is None else f'{n}[{kk}]'
            out[nm] = s
            if kk is not None and n not in out: out[n] = s
        if n == 'GPS' and 'GWk' in a.dtype.names and L.gps_time0 is None:
            ok = np.flatnonzero((a['Status'] >= 3) & (a['GWk'] > 0))
            if len(ok):
                i = ok[0]
                L.gps_time0 = (float(t[i]), 315964800 + float(a['GWk'][i]) * 604800 + float(a['GMS'][i]) / 1000.0 - 18)
    L.msgs = out
    _post(L, t0)
    if progress: progress(1.0)
    return L


def _post(L, t0):
    for base in ('GPS', 'BAT', 'VIBE', 'IMU', 'MAG', 'BARO', 'ARSP', 'XKF4', 'XKF1', 'XKF3', 'GPA', 'RPM', 'ESC', 'CURR', 'NKF4'):
        if base not in L.msgs:
            for k in ('[0]', '[0.0]'):
                if base + k in L.msgs:
                    L.msgs[base] = L.msgs[base + k]
                    break
    if 'BAT' not in L.msgs and 'CURR' in L.msgs:
        L.msgs['BAT'] = L.msgs['CURR']
    L.duration = max((s['t'][-1] for s in L.msgs.values() if len(s.get('t', [])) > 0), default=0.0)
    for t, _ in L.texts[-1:]:
        L.duration = max(L.duration, t)
    L.t0_us = t0 or 0


def _load_bin(path, progress=None, cancel=None) -> LogData:
    from pymavlink import DFReader
    L = LogData(); L.path = path; L.size = os.path.getsize(path); L.kind = 'bin'
    if path.lower().endswith('.log'):
        r = DFReader.DFReader_text(path, zero_time_base=False)
    else:
        r = DFReader.DFReader_binary(path, zero_time_base=False)
    acc: dict[str, dict] = {}
    last_t: dict = {}
    t0 = None
    types = list(WANT.keys())
    total = max(1, getattr(r, 'data_len', L.size))
    last_prog = 0.0
    n = 0
    while True:
        try:
            m = r.recv_match(type=types)
        except Exception:
            L.truncated = True
            break
        if m is None:
            break
        n += 1
        if n % 5000 == 0:
            if cancel and cancel():
                raise InterruptedError
            if progress:
                now = time.time()
                if now - last_prog > 0.15:
                    last_prog = now
                    try:
                        progress(min(0.999, r.offset / total))
                    except Exception:
                        pass
        name = m.get_type()
        d = m.to_dict()
        tus = d.get('TimeUS')
        if tus is None:
            tus = d.get('TimeMS', 0) * 1000 if 'TimeMS' in d else None
        if tus is None:
            ts = getattr(m, '_timestamp', None)
            tus = int(ts * 1e6) if ts else 0
        if t0 is None and tus:
            t0 = tus
        t = (tus - (t0 or 0)) / 1e6 if tus else 0.0
        L.types_seen[name] = L.types_seen.get(name, 0) + 1
        if name == 'PARM':
            try: L.params[d['Name']] = float(d['Value'])
            except Exception: pass
            continue
        if name == 'MSG':
            txt = str(d.get('Message', '')).strip()
            L.texts.append((t, txt))
            v = _vehicle_from(txt)
            if v and not L.version:
                L.version = txt; L.vehicle = v
            continue
        if name == 'VER':
            L.board = str(d.get('BU', d.get('APJ', '')))
            fw = d.get('FWS') or ''
            if fw:
                L.version = str(fw)
                v = _vehicle_from(str(fw))
                if v: L.vehicle = v
            continue
        if name == 'MODE':
            num = int(d.get('ModeNum', d.get('Mode', 0)))
            L.modes.append((t, num, '', int(d.get('Rsn', -1))))
            continue
        if name == 'ERR':
            L.errors.append((t, int(d.get('Subsys', 0)), int(d.get('ECode', 0))))
            continue
        if name == 'EV':
            L.events.append((t, int(d.get('Id', 0))))
            continue
        if name == 'ARM':
            L.arm.append((t, bool(d.get('ArmState', 0))))
            continue
        if name == 'GPS' and L.gps_time0 is None:
            try:
                if int(d.get('Status', 0)) >= 3 and d.get('GWk', 0) > 0:
                    unix = 315964800 + d['GWk'] * 604800 + d['GMS'] / 1000.0 - 18
                    L.gps_time0 = (t, unix)
            except Exception:
                pass
        rate = WANT.get(name, 0)
        key = d.get('I', d.get('C', d.get('Instance', None)))
        if name in NONE_KEY:
            key = None
        if rate:
            lk = (name, key)
            lt = last_t.get(lk)
            if lt is not None and t - lt < 1.0 / rate:
                continue
            last_t[lk] = t
        inst = acc.setdefault(name, {}).setdefault(key, {})
        if 't' not in inst:
            inst['t'] = []
        inst['t'].append(t)
        for f, v in d.items():
            if f in ('mavpackettype', 'TimeUS', 'TimeMS'):
                continue
            if isinstance(v, (int, float)):
                lst = inst.get(f)
                if lst is None:
                    lst = inst[f] = [math.nan] * (len(inst['t']) - 1)
                lst.append(v)
        # Eksik alanları hizala
        ln = len(inst['t'])
        for f, lst in inst.items():
            if len(lst) < ln:
                lst.extend([math.nan] * (ln - len(lst)))
    L.msgs = _finish(acc)
    _post(L, t0)
    if progress: progress(1.0)
    return L


# MAVLink (tlog) -> ortak yapı eşlemesi
def _load_tlog(path, progress=None, cancel=None) -> LogData:
    from pymavlink import mavutil
    L = LogData(); L.path = path; L.size = os.path.getsize(path); L.kind = 'tlog'
    mlog = mavutil.mavlink_connection(path, dialect='ardupilotmega', robust_parsing=True)
    acc: dict[str, dict] = {}
    t0 = None
    types = ['HEARTBEAT', 'GLOBAL_POSITION_INT', 'ATTITUDE', 'VFR_HUD', 'SYS_STATUS', 'GPS_RAW_INT',
             'STATUSTEXT', 'PARAM_VALUE', 'RC_CHANNELS', 'SERVO_OUTPUT_RAW', 'VIBRATION', 'BATTERY_STATUS',
             'EKF_STATUS_REPORT', 'NAV_CONTROLLER_OUTPUT', 'AUTOPILOT_VERSION', 'RADIO_STATUS']
    last_mode = None; last_armed = None
    def add(name, t, **kw):
        inst = acc.setdefault(name, {}).setdefault(None, {'t': []})
        inst['t'].append(t)
        for k, v in kw.items():
            inst.setdefault(k, [math.nan] * (len(inst['t']) - 1)).append(v)
        ln = len(inst['t'])
        for lst in inst.values():
            if len(lst) < ln: lst.extend([math.nan] * (ln - len(lst)))
    n = 0; last_prog = 0
    from pymavlink.mavutil import mode_mapping_apm, mode_mapping_acm
    while True:
        m = mlog.recv_match(type=types)
        if m is None: break
        n += 1
        if n % 3000 == 0:
            if cancel and cancel(): raise InterruptedError
            if progress and time.time() - last_prog > 0.15:
                last_prog = time.time()
                try: progress(min(0.999, mlog.f.tell() / max(1, L.size)))
                except Exception: pass
        ts = getattr(m, '_timestamp', 0.0)
        if t0 is None: t0 = ts; L.gps_time0 = (0.0, ts)
        t = ts - t0
        k = m.get_type()
        if k == 'HEARTBEAT':
            if m.type in (6,):  # GCS
                continue
            if m.type == 1: L.vehicle = 'Plane'
            elif m.type in (2, 3, 4, 13, 14, 15): L.vehicle = 'Copter'
            armed = bool(m.base_mode & 128)
            if armed != last_armed:
                L.arm.append((t, armed)); L.events.append((t, 10 if armed else 11)); last_armed = armed
            if m.custom_mode != last_mode:
                L.modes.append((t, int(m.custom_mode), '', -1)); last_mode = m.custom_mode
        elif k == 'GLOBAL_POSITION_INT':
            add('POS', t, Lat=m.lat / 1e7, Lng=m.lon / 1e7, Alt=m.alt / 1000.0, RelHomeAlt=m.relative_alt / 1000.0)
            add('GPSV', t, VN=m.vx / 100, VE=m.vy / 100, VD=m.vz / 100)
        elif k == 'ATTITUDE':
            add('ATT', t, Roll=math.degrees(m.roll), Pitch=math.degrees(m.pitch), Yaw=math.degrees(m.yaw) % 360)
        elif k == 'VFR_HUD':
            add('CTUN', t, ThO=m.throttle, As=m.airspeed, GSpd=m.groundspeed, Climb=m.climb)
            add('ARSP', t, Airspeed=m.airspeed)
        elif k == 'SYS_STATUS':
            add('BAT', t, Volt=m.voltage_battery / 1000.0, Curr=(m.current_battery / 100.0 if m.current_battery >= 0 else math.nan), RemPct=m.battery_remaining)
            add('PM', t, Load=m.load)
        elif k == 'GPS_RAW_INT':
            add('GPS', t, Status=m.fix_type, NSats=m.satellites_visible, HDop=m.eph / 100.0, Lat=m.lat / 1e7, Lng=m.lon / 1e7, Alt=m.alt / 1000.0, Spd=m.vel / 100.0)
        elif k == 'STATUSTEXT':
            L.texts.append((t, m.text.strip()))
            v = _vehicle_from(m.text)
            if v and not L.version: L.version = m.text.strip(); L.vehicle = v
        elif k == 'PARAM_VALUE':
            L.params[m.param_id] = float(m.param_value)
        elif k == 'RC_CHANNELS':
            add('RCIN', t, **{f'C{i}': getattr(m, f'chan{i}_raw') for i in range(1, 17)})
            add('RSSI', t, RXRSSI=m.rssi / 255.0)
        elif k == 'SERVO_OUTPUT_RAW':
            add('RCOU', t, **{f'C{i}': getattr(m, f'servo{i}_raw') for i in range(1, 9)})
        elif k == 'VIBRATION':
            add('VIBE', t, VibeX=m.vibration_x, VibeY=m.vibration_y, VibeZ=m.vibration_z, Clip0=m.clipping_0)
        elif k == 'EKF_STATUS_REPORT':
            add('XKF4', t, SV=m.velocity_variance, SP=m.pos_horiz_variance, SH=m.pos_vert_variance, SM=m.compass_variance)
        elif k == 'NAV_CONTROLLER_OUTPUT':
            add('NTUN', t, Dist=m.wp_dist, AltE=m.alt_error, AsE=m.aspd_error, XT=m.xtrack_error)
        elif k == 'RADIO_STATUS':
            add('RAD', t, RSSI=m.rssi, RemRSSI=m.remrssi)
    L.msgs = _finish(acc)
    L.duration = max((s['t'][-1] for s in L.msgs.values() if len(s.get('t', [])) > 0), default=0.0)
    if progress: progress(1.0)
    return L
