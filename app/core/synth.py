"""Eğitim senaryoları için sentetik ArduPilot DataFlash (.BIN) logu üretir.

Üretilen loglar gerçek uçuş değildir; senaryo kütüphanesinde öğrencinin arıza belirtilerini tanıması için
gerçekçi fizik ve ArduPilot mesaj yapısıyla hazırlanır.
"""
from __future__ import annotations
import struct, math, random

HEAD = b'\xa3\x95'
FMT_ID = 128

_FMTCHARS = {'b': 'b', 'B': 'B', 'h': 'h', 'H': 'H', 'i': 'i', 'I': 'I', 'f': 'f', 'd': 'd', 'n': '4s', 'N': '16s',
             'Z': '64s', 'c': 'h', 'C': 'H', 'e': 'i', 'E': 'I', 'L': 'i', 'M': 'B', 'q': 'q', 'Q': 'Q'}
_SCALE = {'c': 100, 'C': 100, 'e': 100, 'E': 100, 'L': 1e7}

MSGS = {
    'PARM': (129, 'QNf', 'TimeUS,Name,Value'),
    'MSG': (130, 'QZ', 'TimeUS,Message'),
    'MODE': (131, 'QMBB', 'TimeUS,Mode,ModeNum,Rsn'),
    'EV': (132, 'QB', 'TimeUS,Id'),
    'ERR': (133, 'QBB', 'TimeUS,Subsys,ECode'),
    'ATT': (134, 'QccccCCCC', 'TimeUS,DesRoll,Roll,DesPitch,Pitch,DesYaw,Yaw,ErrRP,ErrYaw'),
    'POS': (135, 'QLLfff', 'TimeUS,Lat,Lng,Alt,RelHomeAlt,RelOriginAlt'),
    'GPS': (136, 'QBBIHBcLLeffff', 'TimeUS,I,Status,GMS,GWk,NSats,HDop,Lat,Lng,Alt,Spd,GCrs,VZ,Yaw'),
    'BAT': (137, 'QBfffffff', 'TimeUS,Inst,Volt,VoltR,Curr,CurrTot,EnrgTot,Temp,Res'),
    'VIBE': (138, 'QBfffI', 'TimeUS,IMU,VibeX,VibeY,VibeZ,Clip'),
    'CTUN': (139, 'Qccccffffff', 'TimeUS,NavRoll,Roll,NavPitch,Pitch,ThO,RdrOut,ThD,As,SAs,E2T'),
    'RCIN': (140, 'QHHHHHHHH', 'TimeUS,C1,C2,C3,C4,C5,C6,C7,C8'),
    'RCOU': (141, 'QHHHHHHHH', 'TimeUS,C1,C2,C3,C4,C5,C6,C7,C8'),
    'ARSP': (142, 'QBffcffBBfB', 'TimeUS,I,Airspeed,DiffPress,Temp,RawPress,Offset,U,H,Hp,Pri'),
    'STAT': (143, 'QBfBBBBBBB', 'TimeUS,isFlying,isFlyProb,Armed,Safety,Crash,Still,Stage,Hit,Sup'),
    'MAG': (144, 'QBhhhhhhhhhBI', 'TimeUS,I,MagX,MagY,MagZ,OfsX,OfsY,OfsZ,MOX,MOY,MOZ,Health,S'),
    'XKF4': (145, 'QBcccccfbbHBIHb', 'TimeUS,C,SV,SP,SH,SM,SVT,errRP,OFN,OFE,FS,TS,SS,GPS,PI'),
    'POWR': (146, 'QffHH', 'TimeUS,Vcc,VServo,Flags,AccFlags'),
    'PM': (147, 'QHHIIHH', 'TimeUS,NLon,NLoop,MaxT,Mem,Load,ErrL'),
    'VER': (148, 'QBHBBBBIZH', 'TimeUS,BT,BST,Maj,Min,Pat,FWT,GH,FWS,APJ'),
    'NTUN': (149, 'QfCCcfffff', 'TimeUS,Dist,TBrg,NavBrg,AltErr,XT,XTi,AsErr,TAW,TAT'),
    'BARO': (150, 'QBfffcfIffB', 'TimeUS,I,Alt,AltAMSL,Press,Temp,CRt,SMS,Offset,GndTemp,H'),
}


def _pyfmt(f):
    return '<' + ''.join(_FMTCHARS[c] for c in f)


class Writer:
    def __init__(self):
        self.buf = bytearray()
        self._fmt(FMT_ID, 89, 'FMT', 'BBnNZ', 'Type,Length,Name,Format,Columns')
        for name, (mid, fmt, cols) in MSGS.items():
            ln = struct.calcsize(_pyfmt(fmt)) + 3
            self._fmt(mid, ln, name, fmt, cols)

    def _fmt(self, mid, ln, name, fmt, cols):
        self.buf += HEAD + bytes([FMT_ID]) + struct.pack('<BB4s16s64s', mid, ln, name.encode(), fmt.encode(), cols.encode())

    def w(self, name, **kw):
        mid, fmt, cols = MSGS[name]
        vals = []
        for c, col in zip(fmt, cols.split(',')):
            v = kw.get(col, 0)
            if c in 'nNZ':
                v = str(v).encode()
            elif c in _SCALE:
                v = int(round(v * _SCALE[c]))
            elif c in 'bBhHiIMqQ':
                v = int(round(v))
            vals.append(v)
        self.buf += HEAD + bytes([mid]) + struct.pack(_pyfmt(fmt), *vals)


SCENARIOS = ['normal', 'gps_loss', 'battery', 'vibration', 'radio_loss', 'stall', 'compass']


def generate(path, scenario='normal', seed=7, duration=600.0):
    rnd = random.Random(seed)
    W = Writer()
    us = lambda t: int(1_000_000 + t * 1e6)
    W.w('VER', TimeUS=us(0), BT=9, Maj=4, Min=5, Pat=7, FWT=0, FWS='ArduPlane V4.5.7 (synthetic)', APJ=9)
    W.w('MSG', TimeUS=us(0), Message='ArduPlane V4.5.7 (synthetic training log)')
    params = {'ARMING_CHECK': 1, 'BATT_MONITOR': 4, 'BATT_CAPACITY': 10000, 'BATT_FS_LOW_ACT': 1, 'BATT_LOW_VOLT': 21.0,
              'BATT_CRT_VOLT': 19.8, 'BATT_FS_CRT_ACT': 2, 'THR_MAX': 100, 'THR_FAILSAFE': 1, 'THR_FS_VALUE': 950,
              'FS_LONG_ACTN': 1, 'FS_SHORT_ACTN': 0, 'FS_GCS_ENABL': 1, 'AHRS_EKF_TYPE': 3, 'EK3_ENABLE': 1,
              'ARSPD_TYPE': 1, 'ARSPD_USE': 1, 'AIRSPEED_MIN': 14, 'AIRSPEED_CRUISE': 20, 'AIRSPEED_MAX': 28,
              'LOG_BITMASK': 65535, 'RTL_AUTOLAND': 0, 'COMPASS_USE': 1, 'GPS_TYPE': 1, 'STALL_PREVENTION': 1,
              'ROLL_LIMIT_DEG': 45, 'PTCH_LIM_MAX_DEG': 20, 'PTCH_LIM_MIN_DEG': -25, 'SCHED_LOOP_RATE': 300}
    if scenario == 'battery':
        params['BATT_FS_LOW_ACT'] = 0
    if scenario == 'radio_loss':
        params['THR_FAILSAFE'] = 0
    if scenario == 'compass':
        params['COMPASS_LEARN'] = 0
    for k, v in params.items():
        W.w('PARM', TimeUS=us(0.01), Name=k, Value=v)
    lat0, lon0 = 35.401, 35.948
    home_alt = 50.0
    mode_names = {0: 'MANUAL', 5: 'FBWA', 10: 'AUTO', 11: 'RTL', 13: 'TAKEOFF'}
    def mode(t, num, rsn=1):
        W.w('MODE', TimeUS=us(t), Mode=num, ModeNum=num, Rsn=rsn)
    mode(1, 0)
    W.w('MSG', TimeUS=us(2), Message='EKF3 IMU0 is using GPS')
    W.w('MSG', TimeUS=us(5), Message='Arming motors')
    W.w('EV', TimeUS=us(5), Id=10)
    mode(6, 13)
    t_end = duration
    crash_t = None
    if scenario in ('gps_loss', 'stall', 'compass'):
        crash_t = duration * 0.7
    if scenario == 'battery':
        crash_t = duration * 0.85
    lat, lon, alt, hdg, spd = lat0, lon0, 0.0, 90.0, 0.0
    capacity_used = 0.0
    dt = 0.1
    t = 0.0
    phase = 'ground'
    radio_ok = True
    gps_ok = True
    roll = pitch = 0.0
    mode_now = 13
    landed = False
    clip = 0
    while t < t_end:
        t += dt
        T = us(t)
        # Uçuş profili
        if t < 8:
            phase = 'ground'; thr = 0; tgt_alt = 0
        elif t < 20:
            phase = 'takeoff'; thr = 100; tgt_alt = 40
        elif t < t_end - 60:
            phase = 'cruise'; thr = 55 + (30 * math.sin(t / 12) if scenario == 'compass' else 0); tgt_alt = 120
            if mode_now == 13 and t > 30:
                mode(t, 10); mode_now = 10; W.w('EV', TimeUS=T, Id=29)
        else:
            phase = 'land'; thr = 20; tgt_alt = 0
            if mode_now != 11 and not crash_t:
                mode(t, 11, 1); mode_now = 11
        # Arızalar
        if scenario == 'gps_loss' and t > duration * 0.5:
            if gps_ok:
                gps_ok = False
                W.w('ERR', TimeUS=T, Subsys=11, ECode=2)
                W.w('MSG', TimeUS=T, Message='GPS 1: lost fix')
                W.w('MSG', TimeUS=us(t + 3), Message='EKF3 IMU0 lane switch 1')
            if t > duration * 0.55 and mode_now != 11:
                mode(t, 11, 6); mode_now = 11
                W.w('ERR', TimeUS=T, Subsys=16, ECode=2)
                W.w('MSG', TimeUS=T, Message='EKF variance')
        if scenario == 'radio_loss' and duration * 0.5 < t < duration * 0.6:
            if radio_ok:
                radio_ok = False
                W.w('ERR', TimeUS=T, Subsys=5, ECode=1)
                W.w('MSG', TimeUS=T, Message='Failsafe. Long event on: type=1/reason=3')
                mode(t, 11, 3); mode_now = 11
        elif scenario == 'radio_loss' and not radio_ok and t >= duration * 0.6:
            radio_ok = True; W.w('ERR', TimeUS=T, Subsys=5, ECode=0)
        # Dinamik
        if crash_t and t >= crash_t:
            phase = 'crash'
        if phase == 'crash':
            k = t - crash_t
            if scenario == 'stall':
                pitch = min(25, pitch + 2) if k < 3 else -60; roll = min(90, roll + 15 * dt * 10) if k > 2 else roll
                spd = max(8, spd - 2 * dt * 5) if k < 3 else spd + 3 * dt
                alt -= (2 if k < 3 else 25) * dt
            elif scenario == 'battery':
                alt -= 6 * dt; pitch = -8; spd = max(10, spd - 0.3 * dt)
            elif scenario == 'compass':
                roll = 35 * math.sin(k * 0.7); hdg += 25 * dt; alt -= 8 * dt; pitch = -15
            else:
                roll = 20 * math.sin(k); hdg += 15 * dt; alt -= 12 * dt; pitch = -20
            if alt <= 0:
                alt = 0
                W.w('STAT', TimeUS=T, isFlying=0, isFlyProb=0.1, Armed=1, Safety=0, Crash=1, Still=0, Stage=3, Hit=1, Sup=0)
                W.w('ERR', TimeUS=T, Subsys=12, ECode=1)
                W.w('MSG', TimeUS=T, Message='Crash: Disarming')
                W.w('EV', TimeUS=us(t + 0.5), Id=11)
                W.w('ATT', TimeUS=T, DesRoll=0, Roll=roll + 40, DesPitch=0, Pitch=-70, DesYaw=hdg, Yaw=hdg % 360)
                W.w('VIBE', TimeUS=T, IMU=0, VibeX=95, VibeY=110, VibeZ=140, Clip=clip + 250)
                break
        else:
            spd += ((22 if phase in ('cruise', 'takeoff') else (14 if phase == 'land' else 0)) - spd) * 0.05
            alt += (tgt_alt - alt) * 0.02 if phase != 'ground' else 0
            if phase == 'land' and alt < 0.5:
                alt = 0; spd = max(0, spd - 3 * dt)
                if not landed:
                    landed = True; W.w('EV', TimeUS=T, Id=18); W.w('MSG', TimeUS=T, Message='Landing complete')
            if phase == 'cruise':
                hdg += 0.8 * dt * 10 * (1 if int(t / 60) % 2 else -0.5)
            roll = (10 * math.sin(t / 15) if phase == 'cruise' else 0) + rnd.gauss(0, 1.2)
            pitch = (8 if phase == 'takeoff' else 2) + rnd.gauss(0, 0.6)
        if scenario == 'battery':
            thr = min(100, thr + (t / duration) * 30)
        hdg %= 360
        d = spd * dt
        lat += d * math.cos(math.radians(hdg)) / 111320
        lon += d * math.sin(math.radians(hdg)) / (111320 * math.cos(math.radians(lat)))
        relalt = max(0.0, alt)
        # Akım/gerilim
        cur = 0.8 + thr * 0.35 + rnd.gauss(0, 0.4)
        capacity_used += cur * dt / 3.6
        rest = 25.2 - 4.4 * (capacity_used / (params['BATT_CAPACITY'] * (0.22 if scenario == 'battery' else 1.6)))
        volt = rest - cur * 0.012 + rnd.gauss(0, 0.03)
        if scenario == 'battery' and volt < 21.0 and not hasattr(W, '_bl'):
            W._bl = 1; W.w('MSG', TimeUS=T, Message='Battery 1 is low 20.95V used %d mAh' % capacity_used); W.w('ERR', TimeUS=T, Subsys=6, ECode=1)
        if scenario == 'battery' and volt < 19.8 and not hasattr(W, '_bc'):
            W._bc = 1; W.w('MSG', TimeUS=T, Message='Battery 1 is critical'); W.w('ERR', TimeUS=T, Subsys=6, ECode=2)
            if not crash_t or t < crash_t:
                crash_t = t
        vib = (14 if phase != 'ground' else 3) + rnd.gauss(0, 2)
        if scenario == 'vibration' and phase != 'ground':
            vib = 45 + 15 * (t / duration) + rnd.gauss(0, 6)
            if vib > 60: clip += rnd.randint(0, 3)
        W.w('ATT', TimeUS=T, DesRoll=roll * 0.95, Roll=roll, DesPitch=pitch * 0.95, Pitch=pitch, DesYaw=hdg, Yaw=hdg, ErrRP=0.02, ErrYaw=0.05)
        W.w('POS', TimeUS=T, Lat=lat, Lng=lon, Alt=home_alt + relalt, RelHomeAlt=relalt, RelOriginAlt=relalt)
        if int(t * 10) % 2 == 0:
            ns = 16 + int(rnd.gauss(0, 1)); hd = 0.7 + abs(rnd.gauss(0, 0.05)); st = 6 if not scenario == 'gps_loss' else 3
            if not gps_ok:
                ns = max(0, 3 + int(rnd.gauss(0, 1))); hd = 9.99; st = 1
            gwk = 2340; gms = int((t + 100000) * 1000) % 604800000
            W.w('GPS', TimeUS=T, I=0, Status=st, GMS=gms, GWk=gwk, NSats=ns, HDop=hd, Lat=lat, Lng=lon, Alt=home_alt + relalt, Spd=spd, GCrs=hdg, VZ=0, Yaw=0)
            ias = spd if scenario != 'stall' or phase != 'crash' else spd * 0.7
            W.w('CTUN', TimeUS=T, NavRoll=roll * 0.95, Roll=roll, NavPitch=pitch, Pitch=pitch, ThO=thr if phase != 'crash' or scenario != 'battery' else 100, RdrOut=0, ThD=thr, As=ias, SAs=ias, E2T=1.0)
            W.w('ARSP', TimeUS=T, I=0, Airspeed=ias, DiffPress=0.5 * 1.2 * ias * ias, Temp=25, RawPress=0, Offset=0, U=1, H=1, Hp=1, Pri=0)
            W.w('VIBE', TimeUS=T, IMU=0, VibeX=vib * 0.7, VibeY=vib * 0.8, VibeZ=vib, Clip=clip)
            W.w('BAT', TimeUS=T, Inst=0, Volt=volt, VoltR=rest, Curr=cur, CurrTot=capacity_used, EnrgTot=capacity_used * 0.022, Temp=30, Res=0.012)
            rc3 = 1000 + thr * 10 if radio_ok else 900
            W.w('RCIN', TimeUS=T, C1=1500 + roll * 5, C2=1500, C3=rc3, C4=1500, C5=1700, C6=1500, C7=1000, C8=1000)
            W.w('RCOU', TimeUS=T, C1=1500 + roll * 10, C2=1500 - pitch * 10, C3=1000 + thr * 10, C4=1500, C5=1500, C6=1500, C7=1000, C8=1000)
            fly = 1 if phase not in ('ground',) and relalt > 1 or spd > 8 else 0
            W.w('STAT', TimeUS=T, isFlying=fly, isFlyProb=0.95 if fly else 0.05, Armed=1, Safety=0, Crash=0, Still=0, Stage=2 if fly else 1, Hit=0, Sup=0)
            mx = 220 + (90 * thr / 100 if scenario == 'compass' else 5 * rnd.random())
            W.w('MAG', TimeUS=T, I=0, MagX=mx * math.cos(math.radians(hdg)), MagY=-mx * math.sin(math.radians(hdg)), MagZ=-380, OfsX=40, OfsY=-25, OfsZ=12, MOX=0, MOY=0, MOZ=0, Health=1, S=0)
            sv = 0.1 + (0.9 if not gps_ok else 0) + abs(rnd.gauss(0, 0.03))
            sm = 0.15 + (0.6 * thr / 100 if scenario == 'compass' else 0) + abs(rnd.gauss(0, 0.03))
            W.w('XKF4', TimeUS=T, C=0, SV=sv, SP=sv * 1.2, SH=0.2, SM=sm, SVT=0, errRP=0.01, OFN=0, OFE=0, FS=0, TS=0, SS=0, GPS=0, PI=0)
            W.w('POWR', TimeUS=T, Vcc=5.08 + rnd.gauss(0, 0.02), VServo=5.2, Flags=1, AccFlags=1)
            W.w('NTUN', TimeUS=T, Dist=300, TBrg=hdg, NavBrg=hdg, AltErr=(tgt_alt - alt), XT=rnd.gauss(0, 3), XTi=0, AsErr=0, TAW=0, TAT=tgt_alt)
            W.w('BARO', TimeUS=T, I=0, Alt=relalt + rnd.gauss(0, 0.3), AltAMSL=home_alt + relalt, Press=101325 - relalt * 12, Temp=24, CRt=0, SMS=0, Offset=0, GndTemp=24, H=1)
        if int(t * 10) % 10 == 0:
            W.w('PM', TimeUS=T, NLon=0, NLoop=300, MaxT=4500, Mem=60000, Load=380 + int(rnd.gauss(0, 20)), ErrL=0)
    if not crash_t:
        W.w('EV', TimeUS=us(t + 1), Id=11)
        W.w('MSG', TimeUS=us(t + 1), Message='Disarming motors')
    with open(path, 'wb') as f:
        f.write(bytes(W.buf))
    return path
