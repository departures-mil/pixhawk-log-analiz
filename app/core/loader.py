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
    'VER': 0, 'CMD': 0, 'ORGN': 0, 'RPM': 5, 'ESC': 5, 'DSF': 0, 'PIDR': 10, 'PIDP': 10, 'PIDY': 10,
    'RAD': 2, 'MAV': 2,
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


def load(path: str, progress=None, cancel=None) -> LogData:
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.tlog',):
        return _load_tlog(path, progress, cancel)
    return _load_bin(path, progress, cancel)


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
        if name in ('ATT', 'POS', 'CTUN', 'NTUN', 'TECS', 'AETR', 'RCIN', 'RCOU', 'PM', 'STAT', 'AHR2', 'AOA', 'POWR', 'RSSI', 'DSF', 'ORGN', 'CMD', 'PIDR', 'PIDP', 'PIDY', 'RAD', 'MAV'):
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
    # Birincil örnekler: GPS[0], BAT[0], VIBE[0] vb. düz adla da erişilebilir olsun
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
