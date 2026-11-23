"""Hava aracı profilleri: sabit kanat, VTOL (QuadPlane), multikopter, helikopter, kara aracı.

Her profilin kendi eşikleri vardır; analiz motoru genel sabitler yerine bu değerleri kullanır.
Profil logdan otomatik bulunur (araç tipi + Q_ENABLE / H_ parametreleri), Ayarlar'dan elle de seçilebilir.
"""
from __future__ import annotations

PROFILES = {
    'plane': dict(vibe_warn=20, vibe_bad=30, vibe_crash=90, sink_crash=12, roll_crash=70, pitch_crash=50, fly_speed=6.0,
                  thr_full_pct=25, cell_warn=3.5, cell_bad=3.3, sat_min=6, hdop_max=2.0, ekf_warn=0.8, ekf_bad=1.0,
                  att_err_warn=5, wind_warn=12, landing_vz_hard=2.5),
    'vtol': dict(vibe_warn=20, vibe_bad=30, vibe_crash=90, sink_crash=10, roll_crash=70, pitch_crash=50, fly_speed=1.5,
                 thr_full_pct=30, cell_warn=3.5, cell_bad=3.3, sat_min=6, hdop_max=2.0, ekf_warn=0.8, ekf_bad=1.0,
                 att_err_warn=6, wind_warn=10, landing_vz_hard=1.5),
    'copter': dict(vibe_warn=15, vibe_bad=30, vibe_crash=90, sink_crash=8, roll_crash=60, pitch_crash=60, fly_speed=1.5,
                   thr_full_pct=10, cell_warn=3.5, cell_bad=3.3, sat_min=8, hdop_max=1.6, ekf_warn=0.8, ekf_bad=1.0,
                   att_err_warn=4, wind_warn=9, landing_vz_hard=1.2),
    'heli': dict(vibe_warn=20, vibe_bad=40, vibe_crash=90, sink_crash=8, roll_crash=60, pitch_crash=60, fly_speed=1.5,
                 thr_full_pct=15, cell_warn=3.5, cell_bad=3.3, sat_min=8, hdop_max=1.6, ekf_warn=0.8, ekf_bad=1.0,
                 att_err_warn=4, wind_warn=10, landing_vz_hard=1.2),
    'rover': dict(vibe_warn=30, vibe_bad=60, vibe_crash=999, sink_crash=999, roll_crash=80, pitch_crash=80, fly_speed=0.5,
                  thr_full_pct=60, cell_warn=3.5, cell_bad=3.3, sat_min=6, hdop_max=2.0, ekf_warn=0.8, ekf_bad=1.0,
                  att_err_warn=10, wind_warn=99, landing_vz_hard=99),
}

NAMES = {
    'auto': ('Otomatik (logdan)', 'Automatic (from log)', 'تلقائي (من السجل)'),
    'plane': ('Sabit kanat', 'Fixed wing', 'جناح ثابت'),
    'vtol': ('VTOL (QuadPlane)', 'VTOL (QuadPlane)', 'VTOL (طائرة رباعية هجينة)'),
    'copter': ('Multikopter', 'Multicopter', 'متعدد المراوح'),
    'heli': ('Helikopter', 'Helicopter', 'مروحية'),
    'rover': ('Kara / deniz aracı', 'Rover / boat', 'مركبة أرضية / قارب'),
}

# VTOL (Q) modları ArduPlane mod numaraları
Q_MODES = {17, 18, 19, 20, 21, 22, 23}


def name(p, lang='tr'):
    return NAMES.get(p, NAMES['plane'])[('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0]


def detect(L) -> str:
    P = L.params; v = L.vehicle
    if v == 'Plane':
        return 'vtol' if P.get('Q_ENABLE', 0) >= 1 or 'QTUN' in L.msgs else 'plane'
    if v == 'Copter':
        if any(k.startswith('H_SW_') or k.startswith('H_COL_') for k in P) or 'heli' in (L.version or '').lower():
            return 'heli'
        return 'copter'
    if v in ('Rover', 'Sub'):
        return 'rover'
    return 'plane'


def get(profile: str) -> dict:
    return dict(PROFILES.get(profile, PROFILES['plane']))
