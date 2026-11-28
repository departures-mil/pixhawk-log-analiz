"""Log Gezgini çekirdeği (v1.1.14): Mission Planner 'Review a Log' penceresinin tüm mesaj ağacı + programın analizi ve öğretici katmanı.

- ensure_all(L): analizde okunmayan tüm mesaj türlerini (ör. QBRK, PIQR, TEC2, MOTB…) ve FMTU/UNIT/MULT birim tablolarını
  ikinci bir hızlı geçişle okur (yalnız .BIN; en çok EXTRA_HZ örnek/sn). Sonuç bellekte kalır, önbelleğe yazılmaz.
- tree(A): mesaj → örnek (IMU[0], BAT[1], ESC[2]…) → alan ağacı; RCOU/RCIN kanalları görev adıyla (C1 · Kanatçık).
- field_info(A, key): anlam, birim, olağan aralık, ilgili parametreler (değeriyle).
- limit_lines(A, key): grafiğe çizilecek parametre eşikleri (ör. ARSP.Airspeed → AIRSPEED_MIN) ve başvuru çizgileri.
- problems(A): programın bulduğu sorunlu bölgeler (kök neden adımları, ML anomali, kritik mesajlar, kırım anı).
- build(A, sel, opts): sol/sağ eksenli grafik + Mod/Hata/MSG/Olay katmanları + kırmızı sorun bölgeleri + eşik çizgileri.
- PRESETS (uçak/VTOL ağırlıklı), expert_steps(A): 'Uzman ne bakardı?' adım adım inceleme.
"""
from __future__ import annotations
import fnmatch, re
import numpy as np

EXTRA_HZ = 25
LI = {'tr': 0, 'en': 1, 'ar': 2}


def tx(tup, lg):
    if not isinstance(tup, (tuple, list)): return str(tup)
    return tup[LI.get(lg, 1)] if len(tup) > LI.get(lg, 1) else tup[0]


# ====================================================================== ek mesajlar ve birimler
_SPECIAL = ('PARM', 'MSG', 'VER', 'MODE', 'ERR', 'EV', 'ARM', 'FMT', 'FMTU', 'UNIT', 'MULT', 'FILE')
_MULT = {'-': 0.0, '?': 1.0, '2': 1e2, '1': 1e1, '0': 1.0, 'A': 1e-1, 'B': 1e-2, 'C': 1e-3, 'D': 1e-4, 'E': 1e-5, 'F': 1e-6, 'G': 1e-7,
         'I': 1e-9, '!': 3.6, '/': 3600.0}


def _S(b):
    return b.split(b'\0', 1)[0].decode('utf-8', 'replace') if isinstance(b, bytes) else str(b)


def missing(L):
    """Logda olup analizde okunmamış (ağaçta ⏳ görünen) mesaj türleri."""
    have = {k.split('[', 1)[0] for k in L.msgs}
    return sorted(n for n, c in (L.types_seen or {}).items() if c and n not in have and n not in _SPECIAL)


def ensure_all(L, progress=None, cancel=None):
    """Eksik mesaj türlerini ve birim tablolarını okur. Döndürür: yeni eklenen mesaj anahtarı sayısı."""
    if getattr(L, '_browse_done', False): return 0
    if L.kind != 'bin' or not L.path:
        L._browse_done = True; L.units = getattr(L, 'units', {}) or {}; return 0
    from . import fastbin as FB
    from .loader import Series, NONE_KEY
    want = {n: EXTRA_HZ for n in missing(L)}
    want.update({'FMTU': 0, 'UNIT': 0, 'MULT': 0})
    rd = FB.Reader(L.path, want, NONE_KEY, progress=progress, cancel=cancel).run()
    arrs = rd.arrays()
    byid = {f.mid: f for f in rd.fmts.values() if f.ok}
    byname = {f.name: f for f in rd.fmts.values() if f.ok}
    # birimler
    units = {}
    try:
        un = {}; mu = {}
        if 'UNIT' in arrs:
            for i, lab in zip(arrs['UNIT'][1]['Id'], arrs['UNIT'][1]['Label']): un[chr(int(i))] = _S(lab)
        if 'MULT' in arrs:
            for i, m in zip(arrs['MULT'][1]['Id'], arrs['MULT'][1]['Mult']): mu[chr(int(i))] = float(m)
        if 'FMTU' in arrs:
            for ft, ui, mi in zip(arrs['FMTU'][1]['FmtType'], arrs['FMTU'][1]['UnitIds'], arrs['FMTU'][1]['MultIds']):
                f = byid.get(int(ft))
                if f is None: continue
                us, ms = _S(ui), _S(mi); d = {}
                for k, c in enumerate(f.cols):
                    u = un.get(us[k], '') if k < len(us) else ''
                    if u in ('UNKNOWN',): u = ''
                    m = mu.get(ms[k], _MULT.get(ms[k] if k < len(ms) else '-', 0.0)) if k < len(ms) else 0.0
                    if c in f.scale: m = 0.0          # biçim karakteri ölçeği zaten uygulandı (c, C, e, E, L)
                    if u or (m and m != 1.0): d[c] = (u, m)
                units[f.name] = d
    except Exception:
        units = {}
    L.units = units
    L.fmt_cols = {n: [c for c in f.cols if c not in ('TimeUS', 'TimeMS')] for n, f in byname.items()}
    t0 = L.t0_us or 0
    n_new = 0
    new = {}
    for n, (f, a) in arrs.items():
        if n in ('FMTU', 'UNIT', 'MULT') or not len(a): continue
        if 'TimeUS' in a.dtype.names: t = (a['TimeUS'].astype(np.float64) - t0) / 1e6
        elif 'TimeMS' in a.dtype.names: t = (a['TimeMS'].astype(np.float64) * 1000 - t0) / 1e6
        else: continue
        okt = ((t >= 0) & (t <= L.duration)) if getattr(L, 'cut', None) else ((t > -5) & (t < (L.duration or 1e9) + 60))   # kesilmiş log: yalnız aralık
        cols = [c for c in a.dtype.names if c not in ('TimeUS', 'TimeMS')]
        kf = None if n in NONE_KEY else next((k for k in ('I', 'C', 'Instance') if k in a.dtype.names and a.dtype[k].kind in 'iu'), None)
        keys = np.unique(a[kf][okt]) if kf else [None]
        if kf and len(keys) > 16: kf = None; keys = [None]
        for k in keys:
            m = okt & (a[kf] == k) if kf else okt
            if not m.any(): continue
            s = Series(); s['t'] = t[m]
            for c in cols:
                v = FB.col(f, a, c)
                if v is not None: s[c] = v[m]
            nm = n if k is None else f'{n}[{int(k)}]'
            if nm in L.msgs or nm in new: continue
            new[nm] = s; n_new += 1
            if k is not None and n not in L.msgs and n not in new: new[n] = s
    if new: L.msgs = {**L.msgs, **new}       # tek atamayla: başka iş parçacıkları sözlüğü dolaşırken değişmesin
    L._browse_done = True
    return n_new


# birim tablosu yoksa (eski loglar, tlog) alan adından tahmin
_UNIT_GUESS = [
    (r'^(Des)?(Roll|Pitch|Yaw)$|^Nav(Roll|Pitch)$|^(Roll|Pitch|Yaw)$|^AOA$|^SSA$|^Tilt$', 'deg'),
    (r'^(Alt|BAlt|DAlt|RelHomeAlt|RelOriginAlt|TAlt|h|hdem|AltE|WpDist|Dist|XT|PN|PE|PD)$', 'm'),
    (r'^(Spd|Airspeed|As|SAs|sp|spdem|VN|VE|VD|VWN|VWE|GS|EAS|TAS|CRt|DCRt|VZ|dh|dhdem)$', 'm/s'),
    (r'^Volt|^V$|^Vcc$|^VServo$', 'V'), (r'^Curr$|^C$|^Amp', 'A'), (r'^CurrTot$|^EnrgTot$', 'mAh'),
    (r'^C\d+$', 'µs'), (r'^Vibe[XYZ]$|^Acc[XYZ]$', 'm/s²'), (r'^Gyr[XYZ]$', 'rad/s'), (r'^Mag[XYZ]$|^Ofs[XYZ]$', 'mGauss'),
    (r'^Temp$|^T$', '°C'), (r'^RPM$|^RawRPM$', 'rpm'), (r'^HDop$|^VDop$|^HAcc$|^VAcc$|^SAcc$', ''), (r'^Press$', 'Pa'),
    (r'^ThO$|^ThI$|^ThH$|^Load$', '%'),
]


_PRETTY = {'m/s/s': 'm/s²', 'us': 'µs', 'degheading': 'deg', 'deglatitude': '°', 'deglongitude': '°', 'instance': '', 'degC': '°C',
           'percent': '%', 'mGauss': 'mGauss', 'rad/s/s': 'rad/s²', 'deg/s/s': 'deg/s²'}


def unit(L, key):
    """'IMU[0].AccX' → 'm/s/s' (logun FMTU tablosundan; yoksa tahmin). Çarpan gerekiyorsa '×0.01' eklenir."""
    base, _, f = key.partition('.')
    base = base.split('[', 1)[0]
    d = (getattr(L, 'units', None) or {}).get(base) or {}
    if f in d:
        u, m = d[f]
        u = _PRETTY.get(u, u)
        return u + (f' ×{m:g}' if m and m != 1.0 else '')
    for rx, u in _UNIT_GUESS:
        if re.search(rx, f): return u
    return ''


# ====================================================================== olağan aralıklar ve ilgili parametreler
# desen (MESAJ.ALAN, örnek numarası atılır) → (açıklama tr/en/ar, ilgili parametreler)
NORMAL = [
    ('VIBE.Vibe[XYZ]', ('İyi < 15 m/s², kabul edilebilir < 30, 60 üstü EKF\'yi bozar.', 'Good < 15 m/s², acceptable < 30, above 60 breaks the EKF.',
                        'جيد < 15 م/ث²، مقبول < 30، وفوق 60 يفسد EKF.'), ['INS_HNTCH_ENABLE', 'INS_GYRO_FILTER', 'INS_ACCEL_FILTER']),
    ('VIBE.Clip*', ('0 olmalı; uçuşta artıyorsa ivmeölçer doyuyor (pervane dengesi, montaj).', 'Should stay 0; rising in flight means the accelerometer saturates (prop balance, mounting).',
                    'يجب أن يبقى 0؛ ارتفاعه أثناء الطيران يعني تشبّع مقياس التسارع (توازن المروحة، التثبيت).'), []),
    ('ARSP.Airspeed', ('Seyirde AIRSPEED_CRUISE civarı; AIRSPEED_MIN altına inmemeli (stall payı).', 'Near AIRSPEED_CRUISE in cruise; must not drop below AIRSPEED_MIN (stall margin).',
                       'قرب AIRSPEED_CRUISE في الطيران المستوي؛ يجب ألا تنخفض تحت AIRSPEED_MIN (هامش الانهيار).'),
     ['AIRSPEED_MIN', 'ARSPD_FBW_MIN', 'AIRSPEED_CRUISE', 'AIRSPEED_MAX', 'ARSPD_FBW_MAX', 'AIRSPEED_STALL', 'ARSPD_RATIO', 'Q_ASSIST_SPEED']),
    ('CTUN.As', ('Hava hızı kestirimi; ARSP ile aynı olmalı. Sensörsüzse rüzgârdan sapabilir.', 'Airspeed estimate; should match ARSP. Without a sensor it can drift with wind.',
                 'تقدير السرعة الجوية؛ يجب أن يطابق ARSP. بدون حساس قد ينحرف مع الرياح.'), ['AIRSPEED_MIN', 'ARSPD_FBW_MIN', 'ARSPD_USE']),
    ('TECS.sp*', ('İstenen (spdem) ile gerçek (sp) birbirini izlemeli; açılan fark enerji yetersizliğidir.', 'Demanded (spdem) and actual (sp) should track; a growing gap means not enough energy.',
                  'يجب أن يتبع المطلوب (spdem) الفعلي (sp)؛ الفارق المتزايد يعني نقص الطاقة.'), ['TECS_SPDWEIGHT', 'TECS_TIME_CONST', 'THR_MAX']),
    ('TECS.h*', ('İstenen irtifa (hdem) ile gerçek (h) farkı birkaç metre içinde kalmalı.', 'Demanded (hdem) and actual (h) altitude should stay within a few metres.',
                 'يجب أن يبقى الفرق بين الارتفاع المطلوب (hdem) والفعلي (h) بضعة أمتار.'), ['TECS_CLMB_MAX', 'TECS_SINK_MAX', 'TECS_PTCH_DAMP']),
    ('ATT.*Roll', ('İstenen ile gerçek arası fark seyirde < 5°; sürekli fark ayar ya da mekanik sorundur.', 'Desired vs actual gap < 5° in cruise; a persistent gap means tuning or mechanical issues.',
                   'الفرق بين المطلوب والفعلي < 5° في الطيران المستوي؛ الفرق المستمر يعني مشكلة ضبط أو ميكانيكية.'),
     ['ROLL_LIMIT_DEG', 'LIM_ROLL_CD', 'RLL2SRV_P', 'RLL_RATE_P', 'RLL_RATE_FF', 'Q_A_RAT_RLL_P']),
    ('ATT.*Pitch', ('İstenen ile gerçek arası fark < 5°; burun sürekli aşağıdaysa ağırlık merkezi ya da trim.', 'Desired vs actual gap < 5°; nose persistently low suggests CG or trim.',
                    'الفرق < 5°؛ إذا بقيت المقدمة منخفضة باستمرار فالسبب مركز الثقل أو الضبط.'),
     ['PTCH_LIM_MAX_DEG', 'PTCH_LIM_MIN_DEG', 'LIM_PITCH_MAX', 'LIM_PITCH_MIN', 'PTCH_RATE_P', 'PTCH_RATE_FF', 'TRIM_PITCH_CD']),
    ('ATT.*Yaw', ('Uçakta istenen yön genelde dümen koordinasyonundan gelir; ani sıçrama pusula sorunudur.', 'In a plane desired yaw comes from turn coordination; sudden jumps point to compass trouble.',
                  'في الطائرة يأتي الانعراج المطلوب من تنسيق الانعطاف؛ القفزات المفاجئة تدل على مشكلة البوصلة.'), ['YAW2SRV_DAMP', 'KFF_RDDRMIX']),
    ('CTUN.Nav*', ('Navigasyonun istediği açı; ATT ile birlikte okuyun.', 'Angle demanded by navigation; read it together with ATT.', 'الزاوية التي تطلبها الملاحة؛ اقرأها مع ATT.'),
     ['ROLL_LIMIT_DEG', 'NAVL1_PERIOD']),
    ('CTUN.ThO', ('Seyirde %40–70. Uzun süre THR_MAX\'ta kalıyorsa uçak güçsüz ya da hız/irtifa isteği fazla.', '40–70 % in cruise. Staying at THR_MAX means underpowered or too much demand.',
                  '40–70٪ في الطيران المستوي. البقاء عند THR_MAX يعني ضعف القدرة أو طلب زائد.'), ['THR_MAX', 'THR_MIN', 'TRIM_THROTTLE', 'TKOFF_THR_MAX']),
    ('QTUN.*', ('VTOL askı: ThO askıda %30–60; DAlt ile Alt birbirini izlemeli.', 'VTOL hover: ThO 30–60 % in hover; DAlt and Alt should track.',
                'التحويم العمودي: ThO بين 30–60٪؛ يجب أن يتبع DAlt الارتفاع Alt.'), ['Q_M_THST_HOVER', 'Q_M_SPIN_MIN', 'Q_M_SPIN_MAX', 'Q_ASSIST_SPEED', 'Q_TRANSITION_MS']),
    ('BAT.Volt', ('Hücre başına yükte > 3,5 V (LiPo). Gaz artınca ani düşüş iç direnç ya da zayıf pil.', '> 3.5 V per cell under load (LiPo). Sharp sag on throttle = high internal resistance.',
                  '> 3.5 فولت لكل خلية تحت الحمل (ليبو). الهبوط الحاد مع الخانق يعني مقاومة داخلية عالية.'),
     ['BATT_LOW_VOLT', 'BATT_CRT_VOLT', 'BATT_FS_LOW_ACT', 'BATT_VOLT_MULT']),
    ('BAT.Curr', ('Sıfır ya da sabitse akım sensörü yok/ayarsız. Ani sıçrama motor/ESC zorlanması.', 'Zero or flat means no/uncalibrated current sensor. Spikes = motor/ESC strain.',
                  'إذا كان صفراً أو ثابتاً فلا يوجد حساس تيار أو غير معاير. القفزات تعني إجهاد المحرك/ESC.'), ['BATT_AMP_PERVLT', 'BATT_AMP_OFFSET']),
    ('BAT.CurrTot', ('Harcanan mAh; kapasitenin %80\'ini geçmemeli.', 'Used mAh; should not exceed 80 % of capacity.', 'الاستهلاك بالـ mAh؛ يجب ألا يتجاوز 80٪ من السعة.'),
     ['BATT_CAPACITY', 'BATT_LOW_MAH', 'BATT_CRT_MAH']),
    ('POWR.Vcc', ('Kart beslemesi 4,8–5,3 V. 4,5 V altı ani düşüşler kart resetine (brownout) yol açar.', 'Board supply 4.8–5.3 V. Dips below 4.5 V can reset the board (brownout).',
                  'تغذية اللوحة 4.8–5.3 فولت. الانخفاض تحت 4.5 فولت قد يعيد تشغيل اللوحة.'), []),
    ('GPS.NSats', ('≥ 10 iyi, 6\'nın altı güvenilmez.', '≥ 10 is good, below 6 is unreliable.', '≥ 10 جيد، وأقل من 6 غير موثوق.'), ['GPS_TYPE', 'GPS_GNSS_MODE']),
    ('GPS.HDop', ('< 1,0 çok iyi, 2\'nin üstü kötü.', '< 1.0 very good, above 2 is poor.', '< 1.0 ممتاز، وفوق 2 سيئ.'), ['GPS_HDOP_GOOD']),
    ('GPS.Spd', ('Yer hızı; hava hızı ile farkı rüzgârı gösterir.', 'Ground speed; its difference from airspeed shows the wind.', 'السرعة الأرضية؛ فرقها عن السرعة الجوية يدل على الرياح.'), []),
    ('GPA.*Acc', ('Yatay doğruluk < 2 m, hız doğruluğu < 0,5 m/s iyi.', 'Horizontal accuracy < 2 m, speed accuracy < 0.5 m/s is good.', 'دقة أفقية < 2 م ودقة سرعة < 0.5 م/ث جيدة.'), []),
    ('XKF4.S[VPHM]', ('Yenilik oranları < 0,5 iyi; 1\'i geçerse EKF o ölçümü reddeder.', 'Innovation ratios < 0.5 good; above 1 the EKF rejects that measurement.',
                      'نسب الابتكار < 0.5 جيدة؛ فوق 1 يرفض EKF ذلك القياس.'), ['FS_EKF_THRESH', 'EK3_GPS_CHECK', 'EK3_MAG_CAL']),
    ('XKF3.I*', ('Ölçüm yenilikleri sıfır etrafında küçük salınmalı.', 'Measurement innovations should oscillate around zero.', 'يجب أن تتذبذب ابتكارات القياس حول الصفر.'), []),
    ('MAG.Mag[XYZ]', ('Gaz/akım ile birlikte değişiyorsa manyetik girişim var.', 'If it changes with throttle/current there is magnetic interference.',
                      'إذا تغيّر مع الخانق/التيار فهناك تداخل مغناطيسي.'), ['COMPASS_USE', 'COMPASS_MOTCT', 'COMPASS_ORIENT']),
    ('BARO.Alt', ('Barometre irtifası; GPS ile fark büyürse hava akımı ya da sıcaklık etkisi.', 'Barometric altitude; a large gap to GPS means airflow or temperature effects.',
                  'الارتفاع البارومتري؛ الفرق الكبير عن GPS يعني تأثير تدفق الهواء أو الحرارة.'), ['EK3_SRC1_POSZ']),
    ('RCOU.C*', ('Servo/motor çıkışı (µs). Uzun süre MIN/MAX\'ta kalıyorsa yüzey ya da motor doyumdadır.', 'Servo/motor output (µs). Staying at MIN/MAX means the surface or motor is saturated.',
                 'خرج المؤازر/المحرك (ميكروثانية). البقاء عند الحد الأدنى/الأعلى يعني التشبع.'), []),
    ('RCIN.C*', ('Kumanda girişi (µs), ~1000–2000. Gaz kanalı THR_FS_VALUE altına inerse failsafe.', 'Pilot input (µs), ~1000–2000. Throttle below THR_FS_VALUE triggers failsafe.',
                 'إدخال الطيار (ميكروثانية) ~1000–2000. انخفاض الخانق تحت THR_FS_VALUE يفعّل الحماية.'), ['THR_FS_VALUE', 'THR_FAILSAFE']),
    ('RSSI.RXRSSI', ('Alıcı sinyal gücü; düşüşler bağlantı kaybı riskidir.', 'Receiver signal strength; drops mean link-loss risk.', 'قوة إشارة المستقبل؛ الانخفاضات تعني خطر فقدان الاتصال.'), ['RSSI_TYPE']),
    ('ESC.RPM', ('Motorlar birlikte hareket etmeli; biri sıfıra düşüyorsa ESC/motor durması.', 'Motors should move together; one dropping to zero is an ESC/motor stop.',
                 'يجب أن تتحرك المحركات معاً؛ هبوط أحدها إلى الصفر يعني توقف ESC/المحرك.'), ['SERVO_BLH_POLES']),
    ('ESC.Temp', ('< 80 °C olmalı.', 'Should be < 80 °C.', 'يجب أن تكون < 80 °م.'), []),
    ('PM.Load', ('İşlemci yükü < %80; yüksekse log/özellik fazlası.', 'CPU load < 80 %; high means too much logging/features.', 'حمل المعالج < 80٪؛ ارتفاعه يعني تسجيلاً أو ميزات زائدة.'), ['SCHED_LOOP_RATE', 'LOG_BITMASK']),
    ('PM.NLon', ('Geciken döngü sayısı; sürekli yüksekse kart yetişemiyor.', 'Long loops count; persistently high means the board cannot keep up.', 'عدد الحلقات المتأخرة؛ ارتفاعه المستمر يعني أن اللوحة لا تواكب.'), []),
    ('AOA.AOA', ('Hücum açısı; ani artış ve hız düşüşü stall belirtisidir.', 'Angle of attack; a sudden rise with speed loss is a stall sign.', 'زاوية الهجوم؛ ارتفاعها المفاجئ مع فقدان السرعة علامة انهيار.'), ['AIRSPEED_MIN']),
    ('IMU.Acc[XYZ]', ('Ham ivme; AccZ duruşta ≈ −9,8. Tepe değerleri darbe ya da titreşimdir.', 'Raw acceleration; AccZ ≈ −9.8 at rest. Peaks are impacts or vibration.',
                      'التسارع الخام؛ AccZ ≈ −9.8 عند السكون. القمم صدمات أو اهتزاز.'), []),
    ('NTUN.XT', ('Rota dışı sapma; seyirde birkaç metre.', 'Cross-track error; a few metres in cruise.', 'الانحراف عن المسار؛ بضعة أمتار في الطيران المستوي.'), ['NAVL1_PERIOD', 'NAVL1_DAMPING']),
]


def _pat_key(key):
    base, _, f = key.partition('.')
    return base.split('[', 1)[0] + '.' + f


def normal_of(key):
    k = _pat_key(key)
    for pat, txt, ps in NORMAL:
        if fnmatch.fnmatchcase(k, pat): return txt, ps
    return None, []


# ====================================================================== parametre eşik çizgileri
def _p(P, *names, div=1.0):
    for n in names:
        if n in P and P[n] not in (None,):
            try: return n, float(P[n]) / div
            except Exception: pass
    return None


def limit_lines(A, key):
    """[(etiket, değer, renk, tür)] — tür 'param' (Full Parameter List'teki ad) ya da 'ref' (başvuru değeri)."""
    P = A.L.params; k = _pat_key(key); f = k.split('.', 1)[1]; out = []

    def add(r, col='#B91C1C', sign=1.0):
        if r: out.append((f'{r[0]}={r[1] * sign:g}' if sign == 1 else f'−{r[0]}', r[1] * sign, col, 'param'))
    if k in ('ARSP.Airspeed', 'CTUN.As', 'CTUN.SAs', 'TECS.sp', 'TECS.spdem') or fnmatch.fnmatchcase(k, 'ARSP*.Airspeed'):
        add(_p(P, 'AIRSPEED_MIN', 'ARSPD_FBW_MIN')); add(_p(P, 'AIRSPEED_MAX', 'ARSPD_FBW_MAX'), '#7C2D12')
        add(_p(P, 'AIRSPEED_CRUISE') or _p(P, 'TRIM_ARSPD_CM', div=100.0), '#15803D')
        add(_p(P, 'AIRSPEED_STALL'), '#DC2626')
        q = _p(P, 'Q_ASSIST_SPEED')
        if q and q[1] > 0 and 'Q_ENABLE' in P and P.get('Q_ENABLE'): add(q, '#7C3AED')
    elif k in ('ATT.Roll', 'ATT.DesRoll', 'CTUN.Roll', 'CTUN.NavRoll'):
        r = _p(P, 'ROLL_LIMIT_DEG') or _p(P, 'LIM_ROLL_CD', div=100.0)
        if r: add(r); add(r, sign=-1.0)
    elif k in ('ATT.Pitch', 'ATT.DesPitch', 'CTUN.Pitch', 'CTUN.NavPitch'):
        add(_p(P, 'PTCH_LIM_MAX_DEG') or _p(P, 'LIM_PITCH_MAX', div=100.0))
        add(_p(P, 'PTCH_LIM_MIN_DEG') or _p(P, 'LIM_PITCH_MIN', div=100.0))
    elif k in ('CTUN.ThO', 'TECS.th'):
        add(_p(P, 'THR_MAX')); add(_p(P, 'TRIM_THROTTLE'), '#15803D')
    elif fnmatch.fnmatchcase(k, 'BAT*.Volt'):
        add(_p(P, 'BATT_LOW_VOLT'), '#D97706'); add(_p(P, 'BATT_CRT_VOLT'))
    elif fnmatch.fnmatchcase(k, 'BAT*.CurrTot'):
        add(_p(P, 'BATT_LOW_MAH'), '#D97706'); add(_p(P, 'BATT_CRT_MAH')); add(_p(P, 'BATT_CAPACITY'), '#475569')
    elif re.fullmatch(r'RCOU\.C(\d+)', k):
        n = int(f[1:])
        from .viz import motor_map
        mot = dict((c, m) for m, c in motor_map(A))
        if f in mot and (P.get('Q_M_PWM_MIN') or 0) > 0:
            add(_p(P, 'Q_M_PWM_MIN'), '#475569'); add(_p(P, 'Q_M_PWM_MAX'), '#475569')
        else:
            add(_p(P, f'SERVO{n}_MIN'), '#475569'); add(_p(P, f'SERVO{n}_TRIM'), '#15803D'); add(_p(P, f'SERVO{n}_MAX'), '#475569')
    elif re.fullmatch(r'RCIN\.C(\d+)', k):
        n = int(f[1:])
        add(_p(P, f'RC{n}_MIN'), '#475569'); add(_p(P, f'RC{n}_MAX'), '#475569')
        from .viz import rc_map
        if rc_map(A).get('thr') == n:
            fs = _p(P, 'THR_FS_VALUE', 'FS_THR_VALUE')
            if fs: add(fs)
    elif k == 'GPS.HDop':
        add(_p(P, 'GPS_HDOP_GOOD', div=100.0), '#D97706')
    elif fnmatch.fnmatchcase(k, 'XKF4.S[VPHM]'):
        add(_p(P, 'FS_EKF_THRESH'))
    if fnmatch.fnmatchcase(k, 'VIBE.Vibe[XYZ]'):
        out += [('30 m/s²', 30.0, '#D97706', 'ref'), ('60 m/s²', 60.0, '#B91C1C', 'ref')]
    elif k == 'POWR.Vcc':
        out += [('4.8 V', 4.8, '#D97706', 'ref'), ('5.3 V', 5.3, '#D97706', 'ref')]
    elif k == 'GPS.NSats':
        out += [('6', 6.0, '#B91C1C', 'ref'), ('10', 10.0, '#15803D', 'ref')]
    return out


# ====================================================================== ağaç
def _roles(A, lg):
    from . import viz
    out = {}
    try:
        for r in viz.channel_roles(A, lg): out['RCOU.' + r['ch']] = viz.role_label(r, lg, A)
    except Exception: pass
    try:
        RC = {'roll': ('Roll stick', 'Roll stick', 'عصا الدوران'), 'pitch': ('Pitch stick', 'Pitch stick', 'عصا الميلان'),
              'thr': ('Gaz stick', 'Throttle stick', 'عصا الخانق'), 'yaw': ('Yaw stick', 'Yaw stick', 'عصا الانعراج'),
              'mode': ('Mod anahtarı', 'Mode switch', 'مفتاح الأوضاع')}
        for k, n in viz.rc_map(A).items():
            out[f'RCIN.C{n}'] = f'C{n} · {tx(RC[k], lg)}'
    except Exception: pass
    return out


def _inst_label(A, base, k, lg):
    from . import viz
    if base == 'ESC':
        try:
            mm = dict(viz.motor_map(A))
            if (k + 1) in mm or not mm: return f'ESC[{k}] · ' + viz.motor_name(A, k + 1, lg)
        except Exception: pass
    if base.startswith('XK') or base.startswith('NK'):
        return f'{base}[{k}] · ' + tx(('EKF çekirdeği', 'EKF core', 'نواة EKF'), lg) + f' {k}'
    if base in ('IMU', 'MAG', 'BARO', 'GPS', 'GPA', 'BAT', 'ARSP'):
        return f'{base}[{k}] · ' + tx(('sensör', 'sensor', 'حساس'), lg) + f' {k + 1}'
    return f'{base}[{k}]'


def _fields(L, key):
    s = L.msgs.get(key)
    if s is None: return []
    n = len(s.get('t', []))
    out = []
    for f in s:
        if f == 't': continue
        a = s[f]
        if hasattr(a, 'dtype') and a.dtype.kind in 'fiub' and len(a) == n: out.append(f)
    return out


def _cnum(f):
    m = re.fullmatch(r'C(\d+)', f)
    return (0, int(m.group(1))) if m else (1, 0)


def tree(A, lg='tr'):
    """[{base, desc, count, loaded, insts: [{key, label, fields: [{key, name, label, unit}]}]}] — alfabetik."""
    from . import sources
    L = A.L
    bases = {}
    for k in L.msgs:
        b, br, inst = k.partition('[')
        bases.setdefault(b, set())
        if br: bases[b].add(int(float(inst.rstrip(']'))))
    roles = _roles(A, lg)
    out = []
    for b in sorted(set(bases) | set(missing(L))):
        cnt = (L.types_seen or {}).get(b, 0)
        node = {'base': b, 'desc': sources.msg_meaning(b, lg), 'count': cnt, 'loaded': b in bases, 'insts': []}
        if b in bases:
            ins = sorted(bases[b])
            keys = [(f'{b}[{i}]', _inst_label(A, b, i, lg)) for i in ins] if len(ins) > 1 or (ins and f'{b}' not in L.msgs) else [(b, b)]
            if len(ins) == 1 and b in L.msgs: keys = [(b, b)]
            for key, lab in keys:
                fl = sorted(_fields(L, key), key=lambda f: (_cnum(f), f)) if b in ('RCOU', 'RCIN', 'RCO2', 'RCI2') else _fields(L, key)
                fs = []
                for f in fl:
                    fk = f'{key}.{f}'
                    rl = roles.get(f'{b}.{f}', '')
                    fs.append({'key': fk, 'name': f, 'label': rl or f, 'unit': unit(L, fk)})
                node['insts'].append({'key': key, 'label': lab, 'fields': fs})
        out.append(node)
    return out


def field_info(A, key, lg='tr'):
    """{meaning, unit, normal, params: [(ad, değer, açıklama)], mp, msg}"""
    from . import sources
    L = A.L
    base = key.split('.', 1)[0].split('[', 1)[0]
    nr, ps = normal_of(key)
    pp = []
    for p in ps:
        if p in L.params:
            pp.append((p, L.params[p], sources.param_text(p, A.vehicle, lg)[0]))
    for lab, v, _, kind in limit_lines(A, key):
        if kind == 'param':
            n = lab.split('=', 1)[0].lstrip('−')
            if n in L.params and n not in [x[0] for x in pp]: pp.append((n, L.params[n], sources.param_text(n, A.vehicle, lg)[0]))
    mp = ''
    try: mp = sources.mp_log_path(key, lg)
    except Exception: pass
    return {'meaning': sources.field_meaning(key, lg), 'unit': unit(L, key), 'normal': tx(nr, lg) if nr else '', 'params': pp,
            'msg': sources.msg_meaning(base, lg), 'mp': mp, 'role': _roles(A, lg).get(_pat_key(key), '')}


def tooltip(A, key, lg='tr'):
    d = field_info(A, key, lg)
    lines = [f"<b>{key}</b>" + (f" [{d['unit']}]" if d['unit'] else '')]
    if d['role']: lines.append('🎛 ' + d['role'])
    if d['meaning']: lines.append(d['meaning'])
    if d['normal']: lines.append('✅ ' + d['normal'])
    if d['params']: lines.append('⚙ ' + ', '.join(f'{n}={v:g}' for n, v, _ in d['params'][:6]))
    return '<br>'.join(lines)


# ====================================================================== seri
def series(L, key):
    """(t, y) ya da None"""
    m, _, f = key.partition('.')
    s = L.msgs.get(m)
    if s is None or f not in s: return None
    t = np.asarray(s['t'], float); y = np.asarray(s[f], float)
    if not len(t): return None
    return t, y


def resolve(A, tok):
    """Hazır görünüm belirteci → logdaki alan anahtarları. 'ARSP.Airspeed|CTUN.As' (ilk bulunan), 'RCOU@R' (yatış yüzeyleri),
    'RCOU@motor', 'RCOU@thr', 'RCIN@roll|pitch|thr|yaw|mode'."""
    from . import viz
    L = A.L
    if '@' in tok:
        msg, role = tok.split('@', 1)
        if msg == 'RCOU':
            try: rr = viz.channel_roles(A, 'en')
            except Exception: rr = []
            if role == 'motor': cs = [r['ch'] for r in rr if r['kind'] == 'motor']
            elif role == 'thr': cs = [r['ch'] for r in rr if r['kind'] == 'thr']
            else: cs = [r['ch'] for r in rr if r['kind'] == 'ctrl' and role in (r['axes'] or '')]
            return [f'RCOU.{c}' for c in cs if L.s('RCOU').has(c)]
        if msg == 'RCIN':
            n = viz.rc_map(A).get(role)
            return [f'RCIN.C{n}'] if n and L.s('RCIN').has(f'C{n}') else []
        return []
    for alt in tok.split('|'):
        if series(L, alt) is not None: return [alt]
    return []


# ====================================================================== hazır görünümler
PRESETS = [
    {'id': 'overview', 'name': ('Genel bakış: irtifa, hız, gaz', 'Overview: altitude, speed, throttle', 'نظرة عامة: الارتفاع والسرعة والخانق'),
     'L': ['POS.RelHomeAlt|CTUN.BAlt|BARO.Alt'], 'R': ['ARSP.Airspeed|CTUN.As', 'GPS.Spd', 'CTUN.ThO|QTUN.ThO'],
     'look': ('Önce bütün uçuşu görün: mod değişimleri, irtifa kaybı, hız düşüşü ve gazın %100\'e dayandığı yerler.',
              'See the whole flight first: mode changes, altitude loss, speed drops and where throttle hits 100 %.',
              'شاهد الرحلة كاملة أولاً: تغييرات الأوضاع وفقدان الارتفاع وانخفاض السرعة وأين يصل الخانق إلى 100٪.')},
    {'id': 'stall', 'plane': True, 'name': ('Hava hızı ve stall', 'Airspeed and stall', 'السرعة الجوية والانهيار'),
     'L': ['ARSP.Airspeed|CTUN.As', 'GPS.Spd'], 'R': ['ATT.Pitch', 'AOA.AOA'],
     'look': ('Hava hızı AIRSPEED_MIN çizgisinin altına iniyor mu? Burun yukarıdayken hız düşüp ardından ani yatış/burun düşmesi stall\'dır. '
              'Yer hızı ile hava hızı farkı rüzgârı gösterir; rüzgâr arkadan gelirken yapılan dönüşler tehlikelidir.',
              'Does airspeed drop below the AIRSPEED_MIN line? Speed falling with the nose up followed by a sudden roll/nose drop is a stall. '
              'The gap between ground and airspeed shows the wind; downwind turns are dangerous.',
              'هل تنخفض السرعة الجوية تحت خط AIRSPEED_MIN؟ انخفاض السرعة والمقدمة مرتفعة ثم دوران أو سقوط مفاجئ للمقدمة يعني انهياراً. '
              'الفرق بين السرعة الأرضية والجوية يدل على الرياح؛ والانعطاف مع الريح خطير.')},
    {'id': 'tecs', 'plane': True, 'name': ('TECS enerji (irtifa + hız)', 'TECS energy (height + speed)', 'طاقة TECS (الارتفاع + السرعة)'),
     'L': ['TECS.h', 'TECS.hdem'], 'R': ['TECS.sp', 'TECS.spdem', 'CTUN.ThO'],
     'look': ('TECS, gazla toplam enerjiyi, yunuslamayla hız/irtifa dengesini yönetir. hdem ile h ve spdem ile sp birlikte açılıyor ve gaz THR_MAX\'ta ise '
              'uçak istenen enerjiyi üretemiyor (güçsüz, ağır ya da pervane/motor sorunu).',
              'TECS manages total energy with throttle and the speed/height balance with pitch. If hdem vs h and spdem vs sp both open up while throttle sits at THR_MAX, '
              'the aircraft cannot make the energy demanded (underpowered, heavy, or prop/motor trouble).',
              'يدير TECS الطاقة الكلية بالخانق وتوازن السرعة/الارتفاع بالميلان. إذا اتسع الفرق بين hdem وh وبين spdem وsp والخانق عند THR_MAX '
              'فالطائرة لا تنتج الطاقة المطلوبة (ضعف قدرة أو ثقل أو مشكلة في المروحة/المحرك).')},
    {'id': 'servo', 'plane': True, 'name': ('Servolar ve ters yüzey', 'Servos and reversed surfaces', 'المؤازرات والأسطح المعكوسة'),
     'L': ['ATT.DesRoll', 'ATT.Roll'], 'R': ['RCOU@R'],
     'look': ('Sağa yatış istendiğinde kanatçık çıkışı hep aynı yöne gitmeli. İstenen yatış artarken gerçek yatış ters yöne kaçıyorsa yüzey ters (SERVOn_REVERSED). '
              'Çıkış MIN/MAX\'ta yapışıp yatış yine de gelmiyorsa yüzey yetersiz, bağlantı kopuk ya da servo zayıf.',
              'When right roll is demanded the aileron output should always move the same way. If actual roll runs opposite to a growing demand the surface is reversed (SERVOn_REVERSED). '
              'If the output sticks at MIN/MAX and roll still does not come, the surface is too small, the linkage is broken or the servo is weak.',
              'عند طلب دوران لليمين يجب أن يتحرك خرج الجنيح دائماً في الاتجاه نفسه. إذا انحرف الدوران الفعلي عكس الطلب المتزايد فالسطح معكوس (SERVOn_REVERSED). '
              'وإذا التصق الخرج بالحد الأدنى/الأعلى ولم يتحقق الدوران فالسطح صغير أو الوصلة مقطوعة أو المؤازر ضعيف.')},
    {'id': 'transition', 'plane': True, 'vtol': True, 'name': ('Geçiş ve Q_ASSIST', 'Transition and Q_ASSIST', 'الانتقال وQ_ASSIST'),
     'L': ['ARSP.Airspeed|CTUN.As', 'POS.RelHomeAlt|QTUN.Alt|BARO.Alt'], 'R': ['RCOU@motor', 'CTUN.ThO'],
     'look': ('İleri geçişte hava hızı ARSPD_FBW_MIN\'e ulaşmadan VTOL motorları kesilmemeli; MSG\'de "Transition done" anına bakın. '
              'Hız Q_ASSIST_SPEED altına inince VTOL motorları yeniden devreye girer (Q_ASSIST). Geçişte irtifa kaybı itki ya da hız yetersizliğidir.',
              'In forward transition the VTOL motors must not stop before airspeed reaches ARSPD_FBW_MIN; look for "Transition done" in MSG. '
              'When speed falls below Q_ASSIST_SPEED the VTOL motors come back (Q_ASSIST). Height loss during transition means not enough thrust or speed.',
              'في الانتقال الأمامي يجب ألا تتوقف محركات الإقلاع العمودي قبل بلوغ ARSPD_FBW_MIN؛ ابحث عن "Transition done" في MSG. '
              'عندما تنخفض السرعة تحت Q_ASSIST_SPEED تعود المحركات العمودية (Q_ASSIST). فقدان الارتفاع أثناء الانتقال يعني نقص الدفع أو السرعة.')},
    {'id': 'vtol_motor', 'vtol': True, 'name': ('VTOL motor payı', 'VTOL motor headroom', 'هامش محركات الإقلاع العمودي'),
     'L': ['RCOU@motor'], 'R': ['QTUN.ThO|CTUN.ThO', 'BAT.Volt'],
     'look': ('Askıda VTOL motorları ortada (Q_M_PWM_MIN–MAX arası %40–70) olmalı. Bir motor sürekli MAX\'a, karşısındaki MIN\'e gidiyorsa o motor zayıf, '
              'pervanesi ters/yanlış ya da ağırlık merkezi kaymış. Hepsi birden MAX\'taysa araç güçsüz ya da batarya çöküyor.',
              'In hover the VTOL motors should sit mid-range (40–70 % between Q_M_PWM_MIN and MAX). If one motor goes to MAX and the opposite to MIN, '
              'that motor is weak, its prop is wrong/reversed, or the CG has shifted. All at MAX means underpowered or a collapsing battery.',
              'في التحويم يجب أن تكون المحركات العمودية في الوسط (40–70٪ بين Q_M_PWM_MIN وMAX). إذا ذهب محرك إلى الحد الأعلى ومقابله إلى الأدنى '
              'فذلك المحرك ضعيف أو مروحته خاطئة/معكوسة أو انزاح مركز الثقل. وإذا كانت كلها عند الحد الأعلى فالمركبة ضعيفة أو البطارية تنهار.')},
    {'id': 'vibe', 'name': ('Titreşim', 'Vibration', 'الاهتزاز'),
     'L': ['VIBE.VibeX', 'VIBE.VibeY', 'VIBE.VibeZ'], 'R': ['VIBE.Clip|VIBE.Clip0', 'CTUN.ThO|QTUN.ThO'],
     'look': ('30 m/s² çizgisinin üstü sorunludur, 60 üstü EKF\'yi bozar. Clip artıyorsa ivmeölçer doymuştur. Titreşim gazla birlikte artıyorsa pervane/motor dengesi, '
              'sabitse montaj (köpük, kablo gerginliği) sorunudur.',
              'Above the 30 m/s² line is a problem, above 60 breaks the EKF. Rising Clip means the accelerometer saturated. Vibration rising with throttle points to prop/motor balance; '
              'constant vibration points to mounting (foam, cable tension).',
              'فوق خط 30 م/ث² مشكلة، وفوق 60 يفسد EKF. ارتفاع Clip يعني تشبّع مقياس التسارع. ارتفاع الاهتزاز مع الخانق يشير إلى توازن المروحة/المحرك، '
              'والاهتزاز الثابت يشير إلى التثبيت (الإسفنج، شد الكابلات).')},
    {'id': 'att', 'name': ('Tutum: istenen / gerçek', 'Attitude: desired / actual', 'الوضعية: المطلوبة / الفعلية'),
     'L': ['ATT.DesRoll', 'ATT.Roll'], 'R': ['ATT.DesPitch', 'ATT.Pitch'],
     'look': ('İstenen çizgiyi gerçek çizgi birkaç derece içinde izlemeli. Fark yavaş açılıyorsa ayar/yüzey yetersiz, birden açılıyorsa mekanik arıza ya da stall.',
              'The actual line should follow the desired line within a few degrees. A slowly opening gap = tuning/surface authority, a sudden gap = mechanical failure or stall.',
              'يجب أن يتبع الخط الفعلي الخط المطلوب ضمن بضع درجات. الفارق البطيء يعني ضعف الضبط/الأسطح، والمفاجئ يعني عطلاً ميكانيكياً أو انهياراً.')},
    {'id': 'battery', 'name': ('Batarya ve güç', 'Battery and power', 'البطارية والطاقة'),
     'L': ['BAT.Volt'], 'R': ['BAT.Curr', 'CTUN.ThO|QTUN.ThO', 'POWR.Vcc'],
     'look': ('Gaz artınca gerilim ne kadar düşüyor? BATT_LOW_VOLT çizgisine yaklaşıyorsa ve akım sıçrıyorsa pil zayıf/küçük. Vcc 4,8 V altına iniyorsa kart beslemesi (BEC) yetersiz.',
              'How much does voltage sag when throttle rises? Approaching the BATT_LOW_VOLT line with current spikes means a weak/small pack. Vcc below 4.8 V means a weak board supply (BEC).',
              'كم ينخفض الجهد عند زيادة الخانق؟ الاقتراب من خط BATT_LOW_VOLT مع قفزات التيار يعني بطارية ضعيفة/صغيرة. وانخفاض Vcc تحت 4.8 فولت يعني ضعف تغذية اللوحة (BEC).')},
    {'id': 'gps', 'name': ('GPS ve EKF', 'GPS and EKF', 'GPS وEKF'),
     'L': ['GPS.NSats', 'GPS.HDop'], 'R': ['XKF4.SV', 'XKF4.SP', 'XKF4.SH', 'XKF4.SM'],
     'look': ('Uydu sayısı düşüp HDop yükselirken EKF yenilik oranları (SV, SP) 1\'i geçiyorsa konum kestirimi bozuldu. SM yüksekse pusula sorunludur.',
              'If sat count falls and HDop rises while EKF innovation ratios (SV, SP) exceed 1, the position estimate failed. High SM points to the compass.',
              'إذا انخفض عدد الأقمار وارتفع HDop وتجاوزت نسب ابتكار EKF ‏(SV، SP) القيمة 1 فقد فسد تقدير الموقع. ارتفاع SM يشير إلى البوصلة.')},
    {'id': 'rc', 'name': ('Kumanda girişleri', 'Pilot inputs', 'مدخلات الطيار'),
     'L': ['RCIN@roll', 'RCIN@pitch', 'RCIN@thr', 'RCIN@yaw'], 'R': ['RCIN@mode', 'RSSI.RXRSSI'],
     'look': ('Kırımdan önce pilot ne yaptı? Stickler hareketsizken araç düşüyorsa arıza; ani sert stick hareketi ya da gazın kesilmesi pilot hatası olabilir. '
              'Gaz kanalı THR_FS_VALUE altına iniyorsa radyo failsafe.',
              'What did the pilot do before the crash? Falling with motionless sticks means a failure; sudden hard stick input or cutting throttle can be pilot error. '
              'Throttle channel below THR_FS_VALUE means radio failsafe.',
              'ماذا فعل الطيار قبل الحادث؟ السقوط مع ثبات العصي يعني عطلاً؛ والحركة الحادة المفاجئة أو قطع الخانق قد يكون خطأ طيار. '
              'انخفاض قناة الخانق تحت THR_FS_VALUE يعني حماية فقدان الراديو.')},
]


def presets(A):
    vt = bool(A.L.params.get('Q_ENABLE')) or getattr(A, 'profile', '') == 'vtol'
    out = []
    for p in PRESETS:
        if p.get('vtol') and not p.get('plane') and not vt: continue
        if p.get('plane') and A.vehicle != 'Plane': continue
        if p['id'] == 'transition' and not vt: continue
        out.append(p)
    return out


def preset_sel(A, p):
    sel = []
    for side in ('L', 'R'):
        for tok in p.get(side, []):
            for k in resolve(A, tok):
                if k not in [s['key'] for s in sel]: sel.append({'key': k, 'side': side})
    return sel


# ====================================================================== sorun bölgeleri
def _cause_name(c, lg):
    from . import texts
    if c == 'normal': return tx(('Normal uçuş: kök neden yok', 'Normal flight: no root cause', 'طيران طبيعي: لا يوجد سبب جذري'), lg)
    try: return texts.T('cause_' + c, lg)
    except Exception: return c


def crash_t(A):
    """Kırım/sorun anı (s) ya da None."""
    k = (A.verdict or {}).get('kind')
    if k not in ('crash', 'incident'): return None
    try:
        from .why import _end_t
        return float(_end_t(A))
    except Exception:
        return float(A.flights[-1][1]) if A.flights else None


def problems(A, lg='tr'):
    """[{id, t0, t1, kind, title, html}] — programın işaretlediği bölgeler (zamana göre)."""
    from . import expert
    from .analysis import fmt_t
    out = []
    root = A.root or {}
    seen = set()
    for c in root.get('chain', []):
        st = c.get('step', '')
        if st == 'mode' or st.startswith('end_') or (st, round(c['t'])) in seen: continue
        seen.add((st, round(c['t'])))
        t = float(c['t'])
        main = st == root.get('cause')
        h = f"<h3>{'🎯 ' if main else '⚠ '}{_cause_name(st, lg)}</h3><p>⏱ {fmt_t(t)}</p>"
        h += expert.html_for(st, lg, n=2) or ''
        out.append({'t0': t - 2.0, 't1': t + 2.0, 'kind': 'root' if main else 'cand', 'title': _cause_name(st, lg), 'html': h})
    for it in (getattr(A, 'anomalies', None) or [])[:6]:
        fe = ', '.join(f"{f['k']} {f['v']}" + (f" (≈{f['exp']})" if f.get('exp') is not None else '') for f in it.get('feats', []))
        tt = tx(('Alışılmadık bölüm (ML)', 'Unusual section (ML)', 'مقطع غير معتاد (تعلم آلي)'), lg)
        out.append({'t0': it['t0'], 't1': it['t1'], 'kind': 'anom', 'title': tt,
                    'html': f"<h3>🧠 {tt}</h3><p>⏱ {fmt_t(it['t0'])} – {fmt_t(it['t1'])} · z={it.get('score')}</p><p>{fe}</p>"})
    from .texts import render
    for e in A.events or []:
        if e.get('sev', 0) < 2: continue
        try: txt = render(e['text'], lg)
        except Exception: txt = str(e.get('text'))
        out.append({'t0': e['t'] - 0.7, 't1': e['t'] + 0.7, 'kind': 'event', 'title': txt[:80], 'html': f'<h3>❗ {txt}</h3><p>⏱ {fmt_t(e["t"])}</p>'})
    ct = crash_t(A)
    if ct is not None:
        from . import texts
        vt = texts.T('v_' + texts.vkey(A.verdict), lg)
        out.append({'t0': ct - 1.0, 't1': ct + 1.0, 'kind': 'crash', 'title': vt,
                    'html': f'<h3>💥 {vt}</h3><p>⏱ {fmt_t(ct)}</p>' + (f"<p>{_cause_name(root['cause'], lg)}</p>" if root.get('cause') else '')})
    out.sort(key=lambda p: p['t0'])
    for i, p in enumerate(out): p['id'] = i + 1
    return out


# ====================================================================== 'Uzman ne bakardı?'
CAUSE_PRESETS = {'stall': ['stall', 'att', 'tecs'], 'battery': ['battery', 'tecs'], 'power': ['battery'], 'gps': ['gps'], 'ekf': ['gps', 'vibe'],
                 'compass': ['gps'], 'radio': ['rc'], 'pilot': ['rc', 'att'], 'vibration': ['vibe', 'att'],
                 'control': ['att', 'servo', 'vtol_motor', 'tecs'], 'motor': ['vtol_motor', 'tecs', 'battery']}
STEP_T = {
    'all': ('Önce bütün uçuşa bakın: modlar (renkli bantlar), MSG ve hata işaretleri. Kırmızı bölgeler programın şüphelendiği yerlerdir.',
            'Look at the whole flight first: modes (coloured bands), MSG and error marks. Red regions are where the program is suspicious.',
            'انظر إلى الرحلة كاملة أولاً: الأوضاع (الأشرطة الملونة) ورسائل MSG وعلامات الأخطاء. المناطق الحمراء هي ما يشتبه فيه البرنامج.'),
    'zoom': ('Şimdi olay anına ±30 sn yakınlaşın. Uzmanlar hep şunu sorar: ilk ne bozuldu? Kırımdan geriye doğru okuyun.',
             'Now zoom to ±30 s around the event. Experts always ask: what broke first? Read backwards from the crash.',
             'الآن كبّر إلى ±30 ثانية حول الحدث. يسأل الخبراء دائماً: ما الذي تعطّل أولاً؟ اقرأ من الحادث إلى الوراء.'),
    'lesson': ('Uzman kuralı', 'Expert rule', 'قاعدة الخبراء'),
}


def expert_steps(A, lg='tr'):
    """[{title, preset, zoom: 'all'|'crash', text}]"""
    from . import expert
    pr = {p['id']: p for p in presets(A)}
    cause = (A.root or {}).get('cause') or ''
    steps = [{'title': tx(pr['overview']['name'], lg), 'preset': 'overview', 'zoom': 'all', 'text': tx(STEP_T['all'], lg)}]
    if crash_t(A) is not None:
        steps.append({'title': tx(('Olay anı ±30 sn', 'Event ±30 s', 'لحظة الحدث ±30 ث'), lg), 'preset': 'overview', 'zoom': 'crash', 'text': tx(STEP_T['zoom'], lg)})
    order = CAUSE_PRESETS.get(cause, [])
    base = ['att', 'stall', 'tecs', 'servo', 'transition', 'vtol_motor', 'battery', 'vibe', 'gps', 'rc'] if A.vehicle == 'Plane' else \
        ['att', 'vibe', 'battery', 'gps', 'rc']
    les = expert.for_cause(cause)[:2] if cause else []
    for pid in order + [b for b in base if b not in order]:
        p = pr.get(pid)
        if not p: continue
        if not preset_sel(A, p): continue
        txt = tx(p['look'], lg)
        if pid in order and les:
            k = les[order.index(pid) % len(les)]
            txt += f"\n\n🎓 {tx(STEP_T['lesson'], lg)}: {expert.txt(k, 'rule', lg)}\n🔎 {expert.txt(k, 'look', lg)}"
        steps.append({'title': tx(p['name'], lg), 'preset': pid, 'zoom': 'crash' if crash_t(A) is not None and pid in order else 'all', 'text': txt})
    return steps


# ====================================================================== veri tablosu
def table(A, keys, t0=None, t1=None, max_rows=1500):
    """(başlıklar, satırlar) — ilk seçili alanın zaman tabanında, diğerleri en yakın örnekle."""
    from . import viz
    from .analysis import fmt_t
    L = A.L
    ss = [(k, series(L, k)) for k in keys]
    ss = [(k, s) for k, s in ss if s is not None]
    if not ss: return [], []
    tb = ss[0][1][0]
    m = np.ones(len(tb), bool)
    if t0 is not None: m &= tb >= t0
    if t1 is not None: m &= tb <= t1
    idx = np.flatnonzero(m)
    if len(idx) > max_rows: idx = idx[np.linspace(0, len(idx) - 1, max_rows).astype(int)]
    T = tb[idx]
    cols = []
    for k, (t, y) in ss:
        j = np.clip(np.searchsorted(t, T), 0, len(t) - 1)
        jm = np.clip(j - 1, 0, len(t) - 1)
        j = np.where(np.abs(t[jm] - T) < np.abs(t[j] - T), jm, j)
        cols.append(y[j])
    segs = viz.segments(A)
    rows = []
    for i, tt in enumerate(T):
        md = viz.mode_at(A, float(tt), segs)
        rows.append([fmt_t(float(tt)), viz.clock(A, float(tt)) or '', md['name'] if md else ''] + [float(c[i]) for c in cols])
    return ['t', 'clock', 'mode'] + [k for k, _ in ss], rows


# ====================================================================== grafik
PAL_L = ['#2563EB', '#16A34A', '#9333EA', '#0D9488', '#CA8A04', '#475569', '#0EA5E9', '#65A30D']
PAL_R = ['#EA580C', '#DC2626', '#DB2777', '#A16207', '#7C3AED', '#BE123C', '#C2410C', '#B45309']


def build(A, sel, opts=None, lg='tr'):
    """sel = [{'key', 'side': 'L'|'R'}]; opts: modes, errors, msg, events, problems, params, quiz, clock.
    → (Figure, {'problems': [...], 'lines': [{key, side, color}]})"""
    from . import charts as B, charts2 as C2, knowledge as K, viz
    from .analysis import fmt_t
    from matplotlib.ticker import FuncFormatter
    from matplotlib.transforms import blended_transform_factory as btf
    o = {'modes': True, 'errors': True, 'msg': True, 'events': True, 'problems': True, 'params': True, 'quiz': False, 'clock': False}
    o.update(opts or {})
    L = A.L
    fig = B._fig(5.2, 10.5)
    ax = fig.add_subplot(111); B._style(ax, lg)
    if o['modes']: B._phases(ax, A)
    axr = None
    info = {'problems': [], 'lines': []}
    nl = nr = 0
    for s in sel:
        r = series(L, s['key'])
        if r is None: continue
        side = s.get('side', 'L')
        if side == 'R' and axr is None:
            axr = ax.twinx(); axr.tick_params(labelsize=7)
            for sp in ('top',): axr.spines[sp].set_visible(False)
        a = axr if side == 'R' else ax
        col = (PAL_R[nr % len(PAL_R)] if side == 'R' else PAL_L[nl % len(PAL_L)])
        if side == 'R': nr += 1
        else: nl += 1
        u = unit(L, s['key'])
        lab = s.get('label') or s['key']
        lab = lab + (f' [{u}]' if u else '') + (' ▶' if side == 'R' else '')
        t, y = r
        a.plot(*B._dec(t, y), color=col, lw=0.85, label=B.mshape(lab, lg), ls='-' if side == 'L' else '-')
        info['lines'].append({'key': s['key'], 'side': side, 'color': col})
        if o['params']:
            for txt, v, c, kind in limit_lines(A, s['key']):
                C2._plim(a, v, txt, c, ls='--' if kind == 'param' else ':', lw=0.7, x=0.004 if side == 'L' else 0.82)
    tr = btf(ax.transData, ax.transAxes)
    if o['errors']:
        for t, sub, code in L.errors:
            col = '#16A34A' if code == 0 else '#DC2626'
            ax.axvline(t, color=col, lw=0.8, ls='-', alpha=0.8, zorder=3)
            ax.text(t, 0.985, ' ' + B.mshape(K.err_text(sub, code, lg)[:38], lg), transform=tr, rotation=90, fontsize=4.4, color=col, va='top', ha='right',
                    clip_on=True, zorder=8)
    if o['events']:
        for t, i in L.events:
            ax.axvline(t, color='#7C3AED', lw=0.6, ls=':', alpha=0.8, zorder=3)
            ax.text(t, 0.02, ' ' + B.mshape(K.ev_text(i, lg)[:34], lg), transform=tr, rotation=90, fontsize=4.2, color='#6D28D9', va='bottom', ha='right',
                    clip_on=True, zorder=8)
    if o['msg']:
        tx_ = [(t, m) for t, m in L.texts if t > 0.5]
        if len(tx_) > 90: tx_ = tx_[:: int(np.ceil(len(tx_) / 90))]
        for t, m in tx_:
            ax.plot([t], [0.0], marker='|', ms=7, color='#334155', transform=tr, zorder=6, clip_on=True)
            ax.text(t, 0.06, ' ' + m[:40], transform=tr, rotation=90, fontsize=3.9, color='#334155', va='bottom', ha='left', clip_on=True, zorder=8,
                    family='DejaVu Sans')
    if o['problems'] and not o['quiz']:
        for p in problems(A, lg):
            col = {'root': '#DC2626', 'crash': '#B91C1C', 'cand': '#F97316', 'anom': '#E11D48', 'event': '#EF4444'}.get(p['kind'], '#DC2626')
            ax.axvspan(p['t0'], p['t1'], color=col, alpha=0.20 if p['kind'] in ('root', 'crash') else 0.12, lw=0, zorder=1)
            ax.text((p['t0'] + p['t1']) / 2, 1.0, f"⚠{p['id']}", transform=tr, fontsize=5.2, color='white', ha='center', va='top', zorder=9, clip_on=True,
                    bbox=dict(fc=col, ec='none', pad=0.6, alpha=0.95))
            info['problems'].append(p)
    if o['modes']:
        if o['quiz']: B.quiz(True)
        try: B._modes(ax, A, lg, label=True)
        finally:
            if o['quiz']: B.quiz(False)
    elif not o['quiz'] and o['problems']:
        B._crash(ax, A)
    ax.set_xlim(0, max(1.0, float(L.duration or 1)))
    if o['clock'] and viz.clock(A, 0.0):
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: viz.clock(A, x) or fmt_t(x)[:-2]))
    hs, ls = ax.get_legend_handles_labels()
    if axr is not None:
        h2, l2 = axr.get_legend_handles_labels(); hs += h2; ls += l2
    if hs: C2._leg(ax, hs, ls, ncol=4)
    if not sel:
        ax.text(0.5, 0.5, B.mshape(tx(('Sağdaki ağaçtan alan işaretleyin', 'Tick fields in the tree', 'اختر حقولاً من الشجرة'), lg), lg),
                transform=ax.transAxes, ha='center', va='center', fontsize=10, color='#64748B')
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try: fig.tight_layout()
        except Exception: pass
    flds = [s['key'] for s in sel]
    if flds:
        from .customchart import _footer_text
        _footer_text(fig, 'log: ' + '  '.join(flds[:14]), lg)
    return fig, info


def problem_at(info, t):
    """Tıklanan zamana denk gelen sorun bölgesi (en dar olanı)."""
    hit = [p for p in info.get('problems', []) if p['t0'] <= t <= p['t1']]
    return min(hit, key=lambda p: p['t1'] - p['t0']) if hit else None


# ====================================================================== alıştırma
def practice_causes(A):
    return ['normal', 'stall', 'battery', 'power', 'gps', 'ekf', 'compass', 'radio', 'vibration', 'control', 'motor', 'pilot']


def truth(A):
    k = (A.verdict or {}).get('kind')
    if k in ('normal', 'noflight', None): return 'normal'
    return (A.root or {}).get('cause') or 'unknown'


def check_guess(A, guess, lg='tr'):
    """{ok, truth, truth_name, guess_name, html}"""
    from . import expert
    tr_ = truth(A)
    others = (A.root or {}).get('others') or []
    ok = guess == tr_
    near = (not ok) and guess in others
    h = []
    if ok: h.append('<h3>✅ ' + tx(('Doğru! Uzmanlarla aynı yere baktınız.', 'Correct! You looked where the experts look.', 'صحيح! نظرت حيث ينظر الخبراء.'), lg) + '</h3>')
    elif near: h.append('<h3>🟡 ' + tx(('Yakın: bu da zincirde var ama ana neden değil.', 'Close: it is in the chain but not the main cause.',
                                        'قريب: موجود في السلسلة لكنه ليس السبب الرئيسي.'), lg) + '</h3>')
    else: h.append('<h3>❌ ' + tx(('Farklı bir neden.', 'A different cause.', 'سبب مختلف.'), lg) + '</h3>')
    h.append('<p><b>' + tx(('Programın kök nedeni', 'Program\'s root cause', 'السبب الجذري حسب البرنامج'), lg) + ':</b> ' + _cause_name(tr_, lg) + '</p>')
    if not ok and guess:
        h.append('<p><b>' + tx(('Sizin tahmininiz', 'Your guess', 'تخمينك'), lg) + ':</b> ' + _cause_name(guess, lg) + '</p>')
    if tr_ not in ('normal', 'unknown'): h.append(expert.html_for(tr_, lg, n=2) or '')
    if not ok and guess and guess not in (tr_, 'normal'):
        ks = expert.for_cause(guess)[:1]
        if ks:
            k = ks[0]
            h.append('<p><i>' + tx(('Tahmininiz doğru olsaydı logda şunu görürdünüz', 'If your guess were right you would see this in the log',
                                    'لو كان تخمينك صحيحاً لرأيت هذا في السجل'), lg) + ':</i> ' + expert.txt(k, 'look', lg) + '</p>')
    return {'ok': ok, 'near': near, 'truth': tr_, 'html': '\n'.join(h)}
