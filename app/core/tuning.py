"""PID ve TECS log verilerinden somut ayar (tuning) önerileri — araç profiline göre (TR / EN / AR).

Ölçülenler (yalnız uçuş sırasında):
  * Hız döngüsü (PIDR/PIDP/PIDY, yoksa RATE): istenen/gerçek kazanç oranı (eğim), gecikme (ms),
    izleme hatası, salınım frekansı ve gücü, P/I/D/FF katkı payları, I teriminin sürekli yüklenmesi.
  * TECS (sabit kanat / VTOL ileri uçuş): irtifa ve hız izleme hatası, gaz/pitch sınırda kalma oranı,
    ölçülen gerçek tırmanma / alçalma kapasitesi, düz uçuşta gaz (TRIM_THROTTLE), irtifa/hız salınımı.
  * Multikopter irtifa: hover gazı (MOT_THST_HOVER), irtifa izleme.
Öneriler tek adımda en çok ±%25 değişiklik önerir (güvenli adım); mevcut değer logdaki PARM'dan okunur.
Uyarı: öneriler bir başlangıç noktasıdır; uygulamadan önce güvenli irtifada deneme uçuşu yapın.
"""
from __future__ import annotations
import math
import numpy as np

LI = {'tr': 0, 'en': 1, 'ar': 2}

T = {
    'axis_roll': ('Yatış (roll)', 'Roll', 'الدوران (Roll)'),
    'axis_pitch': ('Yunuslama (pitch)', 'Pitch', 'الميلان (Pitch)'),
    'axis_yaw': ('Sapma (yaw)', 'Yaw', 'الانعراج (Yaw)'),
    'tecs': ('TECS (irtifa / hız)', 'TECS (height / speed)', 'TECS (الارتفاع / السرعة)'),
    'alt': ('İrtifa tutma', 'Altitude hold', 'تثبيت الارتفاع'),
    'nodata': ('Bu eksende ayar verisi yok ({m} mesajı kaydedilmemiş). LOG_BITMASK’ta ilgili bitleri açın.',
               'No tuning data for this axis ({m} not logged). Enable the related bits in LOG_BITMASK.',
               'لا توجد بيانات ضبط لهذا المحور (الرسالة {m} غير مسجلة). فعّل البتات المناسبة في LOG_BITMASK.'),
    'lowexc': ('Yetersiz manevra: istenen hız çok küçük ({x}). Güvenilir öneri için keskin manevralı bir deneme uçuşu ya da AUTOTUNE yapın.',
               'Not enough excitation: the demanded rate is very small ({x}). Fly sharp manoeuvres or AUTOTUNE for a reliable recommendation.',
               'إثارة غير كافية: المعدل المطلوب صغير جداً ({x}). نفّذ مناورات حادة أو AUTOTUNE للحصول على توصية موثوقة.'),
    'lowrate': ('Ayar verisi {hz} Hz ile kaydedilmiş; hız döngüsü için en az 25 Hz gerekir (Copter: LOG_BITMASK’ta PID + FAST_ATT, Plane: ATTITUDE_FAST). Öneri üretilmedi.',
                'Tuning data was logged at {hz} Hz; the rate loop needs at least 25 Hz (Copter: PID + FAST_ATT in LOG_BITMASK, Plane: ATTITUDE_FAST). No recommendation made.',
                'سُجّلت بيانات الضبط بتردد {hz} هرتز؛ تحتاج حلقة المعدل 25 هرتز على الأقل (Copter: PID + FAST_ATT في LOG_BITMASK، Plane: ATTITUDE_FAST). لم تُقدَّم توصية.'),
    'lowrate2': ('Kayıt hızı {hz} Hz: yalnız büyük kazanç hataları ve yavaş salınımlar değerlendirildi (güven düşük). Kesin ayar için LOG_BITMASK’ta hızlı tutum / PID kaydını açın.',
                 'Log rate {hz} Hz: only large gain errors and slow oscillations were assessed (low confidence). Enable fast attitude / PID logging in LOG_BITMASK for precise tuning.',
                 'معدل التسجيل {hz} هرتز: قُيّمت أخطاء الكسب الكبيرة والتذبذبات البطيئة فقط (ثقة منخفضة). فعّل تسجيل الوضع السريع / PID في LOG_BITMASK لضبط دقيق.'),
    'lowcorr': ('İstenen ve gerçek hız arasında ilişki zayıf (r = {c}): veri yerde, kontrol dışı ya da mekanik arızalı bir bölümden geliyor. Ayar önerisi güvenilir olmaz.',
                'Weak relation between demanded and actual rate (r = {c}): the data comes from the ground, an out-of-control segment or a mechanical fault. A tuning recommendation would not be reliable.',
                'علاقة ضعيفة بين المعدل المطلوب والفعلي (r = {c}): البيانات من الأرض أو من مقطع خارج السيطرة أو عطل ميكانيكي. لن تكون توصية الضبط موثوقة.'),
    'noflight': ('Uçuş bulunamadı; ayar analizi yalnız havadaki veriyle yapılır.', 'No flight found; tuning analysis uses airborne data only.', 'لم يُعثر على طيران؛ يعتمد تحليل الضبط على بيانات الطيران فقط.'),
    'metrics': ('Kazanç oranı {g}  ·  gecikme {lag} ms  ·  izleme hatası %{e}  ·  salınım {osc}',
                'Gain ratio {g}  ·  lag {lag} ms  ·  tracking error {e}%  ·  oscillation {osc}',
                'نسبة الكسب {g}  ·  التأخير {lag} مللي ث  ·  خطأ التتبع {e}%  ·  التذبذب {osc}'),
    'osc_none': ('yok', 'none', 'لا يوجد'),
    'osc_f': ('{f} Hz (güç ×{p})', '{f} Hz (power ×{p})', '{f} هرتز (القدرة ×{p})'),
    'ok': ('Ayar iyi görünüyor; değişiklik gerekmiyor.', 'Tuning looks good; no change needed.', 'الضبط يبدو جيداً؛ لا حاجة لتغيير.'),
    'r_osc_hf_d': ('Yüksek frekanslı salınım ve D payı yüksek: D kazancını düşürün.', 'High-frequency oscillation with a large D share: reduce D.',
                   'تذبذب عالي التردد مع حصة D كبيرة: خفّض D.'),
    'r_osc_hf_p': ('Yüksek frekanslı salınım: P kazancını düşürün (D de yüksekse onu da).', 'High-frequency oscillation: reduce P (and D if it is high).',
                   'تذبذب عالي التردد: خفّض P (وD إن كان مرتفعاً).'),
    'r_osc_lf': ('Düşük frekanslı salınım (dış döngü): açı/servo zaman sabitini yumuşatın.', 'Low-frequency oscillation (outer loop): soften the angle loop / servo time constant.',
                 'تذبذب منخفض التردد (الحلقة الخارجية): خفّف حلقة الزاوية / ثابت زمن المؤازر.'),
    'r_overshoot': ('Gerçek hız istenenden büyük (aşma): kazancı düşürün.', 'Actual rate exceeds demand (overshoot): reduce the gain.',
                    'المعدل الفعلي أكبر من المطلوب (تجاوز): خفّض الكسب.'),
    'r_sluggish_ff': ('Gerçek hız istenene yetişmiyor (kazanç oranı {g}): FF’yi artırın.', 'Actual rate does not reach demand (gain ratio {g}): increase FF.',
                      'المعدل الفعلي لا يصل للمطلوب (نسبة الكسب {g}): زد FF.'),
    'r_sluggish_p': ('Tepki yavaş (kazanç oranı {g}, gecikme {lag} ms): P kazancını artırın.', 'Response is slow (gain ratio {g}, lag {lag} ms): increase P.',
                     'الاستجابة بطيئة (نسبة الكسب {g}، التأخير {lag} مللي ث): زد P.'),
    'r_i_load': ('I terimi sürekli yüklü (çıkışın %{x}’i): sorun ayarda değil; ağırlık merkezi, trim, servo/motor hizası veya karışım. Önce mekanik trimi düzeltin.',
                 'I term permanently loaded ({x}% of output): not a tuning problem; check CG, trim, servo/motor alignment or mixing. Fix mechanical trim first.',
                 'حد I محمّل باستمرار ({x}% من الخرج): ليست مشكلة ضبط؛ افحص مركز الثقل والتريم ومحاذاة المؤازر/المحرك أو الخلط. صحّح التريم الميكانيكي أولاً.'),
    'r_lag': ('Gecikme yüksek ({lag} ms): servo hızı/bağlantı boşluğunu kontrol edin; zaman sabitini düşürün.', 'High lag ({lag} ms): check servo speed / linkage slop; lower the time constant.',
              'تأخير مرتفع ({lag} مللي ث): افحص سرعة المؤازر/خلوص الوصلات؛ خفّض ثابت الزمن.'),
    't_metrics': ('İrtifa hatası RMS {h} m  ·  hız hatası RMS {s} m/s  ·  gaz tavanda %{tm}  ·  gaz tabanda %{tn}  ·  düşük hız bayrağı %{u}',
                  'Height error RMS {h} m  ·  speed error RMS {s} m/s  ·  throttle at max {tm}%  ·  at min {tn}%  ·  underspeed flag {u}%',
                  'خطأ الارتفاع RMS {h} م  ·  خطأ السرعة RMS {s} م/ث  ·  الخانق عند الحد الأقصى {tm}%  ·  عند الأدنى {tn}%  ·  علم السرعة المنخفضة {u}%'),
    'r_clmb': ('Tam gazda ölçülen sürekli tırmanma {x} m/s; TECS_CLMB_MAX bundan yüksek olduğu için gaz tavanda kalıyor ve hız düşüyor.',
               'Sustained climb measured at full throttle is {x} m/s; TECS_CLMB_MAX is higher, so throttle saturates and speed drops.',
               'التسلق المستمر المقاس بالخانق الكامل {x} م/ث؛ TECS_CLMB_MAX أعلى منه، لذلك يتشبع الخانق وتنخفض السرعة.'),
    'r_sink': ('Rölantide ölçülen alçalma {x} m/s; TECS_SINK_MAX bundan yüksek, alçalırken hız artıyor.',
               'Sink rate measured at idle is {x} m/s; TECS_SINK_MAX is higher, so speed builds up in descents.',
               'معدل الهبوط المقاس عند الخمول {x} م/ث؛ TECS_SINK_MAX أعلى منه، لذلك تزداد السرعة أثناء الهبوط.'),
    'r_trim_thr': ('Düz uçuşta ölçülen ortalama gaz %{x}; TRIM_THROTTLE bununla eşleşmeli.', 'Measured average level-flight throttle is {x}%; TRIM_THROTTLE should match it.',
                   'متوسط الخانق المقاس في الطيران المستوي {x}%؛ يجب أن يطابقه TRIM_THROTTLE.'),
    'r_porp': ('İrtifada {p} sn periyotlu salınım (±{a} m): TECS_PTCH_DAMP’ı artırın / TECS_TIME_CONST’u yükseltin.',
               'Height oscillates with a {p} s period (±{a} m): increase TECS_PTCH_DAMP / raise TECS_TIME_CONST.',
               'يتذبذب الارتفاع بدورة {p} ث (±{a} م): زد TECS_PTCH_DAMP / ارفع TECS_TIME_CONST.'),
    'r_spd_osc': ('Hava hızında salınım (±{a} m/s): TECS_THR_DAMP’ı artırın.', 'Airspeed oscillates (±{a} m/s): increase TECS_THR_DAMP.',
                  'تتذبذب السرعة الجوية (±{a} م/ث): زد TECS_THR_DAMP.'),
    'r_h_lag': ('İrtifa hedefi geç izleniyor (RMS {h} m, gaz sınırda değil): TECS_TIME_CONST’u düşürün.',
                'Height demand is followed slowly (RMS {h} m, throttle not saturated): lower TECS_TIME_CONST.',
                'يُتابَع هدف الارتفاع ببطء (RMS {h} م، الخانق غير متشبع): خفّض TECS_TIME_CONST.'),
    'r_underspeed': ('Düşük hız koruması uçuşun %{u}’inde devrede: tırmanma isteğini düşürün, ARSPD_FBW_MIN ve hava hızı sensörünü kontrol edin.',
                     'Underspeed protection active in {u}% of flight: reduce climb demand, check ARSPD_FBW_MIN and the airspeed sensor.',
                     'حماية السرعة المنخفضة نشطة في {u}% من الرحلة: خفّض طلب التسلق، افحص ARSPD_FBW_MIN وحساس السرعة الجوية.'),
    'r_no_arspd': ('Hava hızı sensörü kullanılmıyor (ARSPD_USE=0): TECS sentetik hızla çalışır; hız önerileri daha az kesindir.',
                   'Airspeed sensor not used (ARSPD_USE=0): TECS runs on synthetic airspeed; speed recommendations are less precise.',
                   'حساس السرعة الجوية غير مستخدم (ARSPD_USE=0): يعمل TECS بسرعة تقديرية؛ توصيات السرعة أقل دقة.'),
    'r_hover': ('Ölçülen hover gazı {x}; MOT_THST_HOVER = {c} (öğrenme kapalı). Eşleştirin.', 'Measured hover throttle is {x}; MOT_THST_HOVER = {c} (learning off). Match it.',
                'خانق التحويم المقاس {x}؛ MOT_THST_HOVER = {c} (التعلم معطل). طابقهما.'),
    'r_alt_osc': ('İrtifada {p} sn periyotlu salınım (±{a} m): PSC_ACCZ_P / PSC_ACCZ_I’yi %20 düşürün.',
                  'Altitude oscillates with a {p} s period (±{a} m): reduce PSC_ACCZ_P / PSC_ACCZ_I by 20%.',
                  'يتذبذب الارتفاع بدورة {p} ث (±{a} م): خفّض PSC_ACCZ_P / PSC_ACCZ_I بنسبة 20%.'),
    'conf': ('Güven: {c}', 'Confidence: {c}', 'الثقة: {c}'),
    'c_hi': ('yüksek', 'high', 'عالية'), 'c_mid': ('orta', 'medium', 'متوسطة'), 'c_lo': ('düşük', 'low', 'منخفضة'),
    'disclaimer': ('Öneriler logdan ölçülen değerlere dayanır ve tek adımda en çok %25 değişiklik önerir. Uygulamadan önce mevcut .param dosyanızı yedekleyin, değişiklikleri güvenli irtifada tek tek deneyin; AUTOTUNE mümkünse önce onu kullanın.',
                   'Recommendations are based on values measured in the log and change a value by at most 25% per step. Back up your .param file first, try changes one by one at a safe altitude; use AUTOTUNE first where possible.',
                   'تستند التوصيات إلى قيم مقاسة من السجل ولا تغيّر أي قيمة بأكثر من 25% في الخطوة الواحدة. انسخ ملف .param احتياطياً أولاً، وجرّب التغييرات واحداً تلو الآخر على ارتفاع آمن؛ استخدم AUTOTUNE أولاً إن أمكن.'),
}


def tx(k, lang='tr', **kw):
    s = T[k][LI.get(lang, 0)]
    return s.format(**kw) if kw else s


# ------------------------------------------------------------------ yardımcılar
def _mask(t, flights, pad=3.0):
    m = np.zeros(len(t), bool)
    for a, b in flights or []:
        m |= (t >= a + pad) & (t <= b - pad)
    return m


def _grid(s, fields, flights, hz=None):
    """Mesajı uçuş aralıklarında düzgün zaman ızgarasına taşır. Döner (t, {alan: dizi}, hz) ya da None."""
    if not s.has('t') or any(not s.has(f) for f in fields): return None
    t = s['t']
    if len(t) < 50: return None
    dt = np.median(np.diff(t)) if len(t) > 2 else 0.1
    rate = 1.0 / max(dt, 1e-3)
    hz = hz or min(max(rate, 5.0), 100.0)
    segs = []
    for a, b in flights or [(t[0], t[-1])]:
        a, b = max(a + 3, t[0]), min(b - 3, t[-1])
        if b - a < 5: continue
        segs.append(np.arange(a, b, 1.0 / hz))
    if not segs: return None
    g = np.concatenate(segs)
    out = {f: np.interp(g, t, s[f]) for f in fields}
    return g, out, hz, rate


def _lag_ms(des, act, hz, maxlag_s=0.6):
    des = des - des.mean(); act = act - act.mean()
    n = int(maxlag_s * hz)
    if n < 1 or len(des) < 4 * n: return 0.0
    best, bl = -1e18, 0
    for k in range(0, n + 1):
        c = float(np.dot(des[:len(des) - k], act[k:]))
        if c > best: best, bl = c, k
    return 1000.0 * bl / hz


def _psd(x, hz, seg):
    win = np.hanning(seg); acc = None
    for i in range(0, len(x) - seg, seg // 2):
        y = x[i:i + seg]; y = (y - y.mean()) * win
        p = np.abs(np.fft.rfft(y)) ** 2
        acc = p if acc is None else acc + p
    return acc, np.fft.rfftfreq(seg, 1.0 / hz)


def _osc(err, hz, fmin=0.6, ref=None):
    """Sinyaldeki baskın salınım: (frekans Hz, tepe/medyan güç oranı).
    ref verilirse (istenen sinyal), istenen sinyalin kendisinde bulunan frekanslar salınım sayılmaz:
    pilotun/otopilotun komutladığı hareket değil, aracın kendi ürettiği titreşim aranır."""
    n = len(err)
    seg = 1024 if n >= 8192 else 512 if n >= 2048 else 256
    if n < seg + 2: return None, 0.0
    pe, f = _psd(err, hz, seg)
    if pe is None: return None, 0.0
    m = f >= fmin
    if m.sum() < 5: return None, 0.0
    score = pe.copy()
    if ref is not None:
        pr, _ = _psd(ref, hz, seg)
        # komutta güçlü olan frekansları bastır
        score = pe / (1.0 + 4.0 * pr / max(float(np.median(pe[m])), 1e-12))
    pp = score[m]; ff = f[m]
    i = int(np.argmax(pp)); med = float(np.median(pe[m])) or 1e-12
    return float(ff[i]), float(pe[m][i] / med) if pp[i] > 0.25 * pe[m][i] else 0.0


def _periodic(x, hz, f):
    """Gerçek salınım mı? Sinyalin bir periyot gecikmeli kendisiyle ilintisi (otokorelasyon) yüksek olmalı."""
    if not f: return 0.0
    k = int(round(hz / f))
    if k < 2 or len(x) < 4 * k: return 0.0
    x = x - np.mean(x); d = float(np.dot(x, x))
    if d <= 0: return 0.0
    return float(np.dot(x[:-k], x[k:]) / d)


def _acf_period(parts, hz, lo_s, hi_s):
    """Parçalar içinde otokorelasyonun en yüksek olduğu periyot: (periyot sn, ilinti)."""
    best = (None, 0.0)
    lags = np.arange(max(int(lo_s * hz), 2), int(hi_s * hz) + 1)
    if not len(lags): return best
    acc = np.zeros(len(lags)); w = 0.0
    for x in parts:
        x = x - np.mean(x); d = float(np.dot(x, x))
        if d <= 0 or len(x) < lags[-1] + 10 * hz: continue
        acc += np.array([np.dot(x[:-k], x[k:]) / d * len(x) / (len(x) - k) for k in lags]) * len(x); w += len(x)
    if w == 0: return best
    acc /= w
    # ilk tepe: ilinti önce sıfırın altına inmeli, sonra yeniden yükselmeli (gerçek periyot)
    neg = np.where(acc < 0)[0]
    if not len(neg): return best
    i = int(neg[0] + np.argmax(acc[neg[0]:]))
    return float(lags[i] / hz), float(acc[i])


def _r(x, n=2):
    try: return round(float(x), n)
    except Exception: return x


def _step(cur, factor, lo=0.75, hi=1.25):
    factor = min(max(factor, lo), hi)
    v = cur * factor
    mag = 10 ** math.floor(math.log10(abs(v))) if v else 1
    return round(v / mag * 100) / 100 * mag   # 3 anlamlı basamak


def _rec(P, name, factor, why, conf, lang, alt=None):
    """Mevcut değeri olan ilk parametre adı için öneri."""
    for n in [name] + list(alt or []):
        if n in P and isinstance(P[n], (int, float)):
            cur = float(P[n])
            if cur == 0 and factor > 1: continue
            new = _step(cur, factor) if cur else 0.0
            if abs(new - cur) < 1e-9: return None
            return {'param': n, 'cur': _r(cur, 4), 'new': _r(new, 4), 'why': why, 'conf': conf}
    return None


# Parametre adları (yeni ArduPilot → eski adlar yedek)
PLANE_AX = {
    'roll': dict(msg='PIDR', P=['RLL_RATE_P', 'RLL2SRV_P'], I=['RLL_RATE_I', 'RLL2SRV_I'], D=['RLL_RATE_D', 'RLL2SRV_D'],
                 FF=['RLL_RATE_FF', 'RLL2SRV_FF'], TC=['RLL2SRV_TCONST']),
    'pitch': dict(msg='PIDP', P=['PTCH_RATE_P', 'PTCH2SRV_P'], I=['PTCH_RATE_I', 'PTCH2SRV_I'], D=['PTCH_RATE_D', 'PTCH2SRV_D'],
                  FF=['PTCH_RATE_FF', 'PTCH2SRV_FF'], TC=['PTCH2SRV_TCONST']),
    'yaw': dict(msg='PIDY', P=['YAW_RATE_P', 'YAW2SRV_DAMP'], I=['YAW_RATE_I', 'YAW2SRV_INT'], D=['YAW_RATE_D'], FF=['YAW_RATE_FF'], TC=[]),
}


def _copter_ax(prefix='ATC_'):
    a = prefix  # 'ATC_' (Copter) ya da 'Q_A_' (QuadPlane)
    return {
        'roll': dict(msg='PIDR', rate=('RDes', 'R'), P=[a + 'RAT_RLL_P'], I=[a + 'RAT_RLL_I'], D=[a + 'RAT_RLL_D'], FF=[a + 'RAT_RLL_FF'], ANG=[a + 'ANG_RLL_P']),
        'pitch': dict(msg='PIDP', rate=('PDes', 'P'), P=[a + 'RAT_PIT_P'], I=[a + 'RAT_PIT_I'], D=[a + 'RAT_PIT_D'], FF=[a + 'RAT_PIT_FF'], ANG=[a + 'ANG_PIT_P']),
        'yaw': dict(msg='PIDY', rate=('YDes', 'Y'), P=[a + 'RAT_YAW_P'], I=[a + 'RAT_YAW_I'], D=[a + 'RAT_YAW_D'], FF=[a + 'RAT_YAW_FF'], ANG=[a + 'ANG_YAW_P']),
    }


# ------------------------------------------------------------------ hız döngüsü
def rate_axis(L, flights, ax, spec, P, lang, multirotor, hf_hz):
    """Bir eksenin hız döngüsünü ölçer ve öneri üretir."""
    out = {'axis': ax, 'title': tx('axis_' + ax, lang), 'recs': [], 'notes': [], 'metrics': {}}
    s = L.s(spec['msg'])
    if s.has('Des') and not s.has('Tar'):
        # Eski sürüm (≤3.8): yalnız istenen hız (Des) var → gerçek hız IMU jiroskopundan (rad/s → °/s)
        imu = L.s('IMU'); gk = {'roll': 'GyrX', 'pitch': 'GyrY', 'yaw': 'GyrZ'}[ax]
        if imu.has(gk):
            s = type(s)(s); s['Tar'] = s['Des']; s['Act'] = np.interp(s['t'], imu['t'], imu[gk]) * 57.2958
    fields = ['Tar', 'Act']
    have_terms = all(s.has(f) for f in ('P', 'I', 'D'))
    G = _grid(s, fields + (['P', 'I', 'D'] + (['FF'] if s.has('FF') else []) if have_terms else []), flights)
    src = spec['msg']
    if G is None and 'rate' in spec:
        r = L.s('RATE'); G0 = _grid(r, list(spec['rate']), flights)
        if G0:
            g, d, hz, rate = G0
            G = (g, {'Tar': d[spec['rate'][0]], 'Act': d[spec['rate'][1]]}, hz, rate); src = 'RATE'; have_terms = False
    if G is None:
        out['notes'].append(tx('nodata', lang, m=spec['msg'] + (' / RATE' if 'rate' in spec else ''))); out['status'] = 'na'
        return out
    g, d, hz, rate = G
    des, act = d['Tar'], d['Act']
    # ölçek: rad/s mı derece/s mi?
    sc = 57.2958 if np.nanpercentile(np.abs(act), 99) < 12 else 1.0
    des_d, act_d = des * sc, act * sc
    exc = float(np.std(des_d))
    out['metrics'].update(src=src, hz=_r(rate, 0), exc=_r(exc, 1), n=len(g))
    if exc < 3.0:
        out['notes'].append(tx('lowexc', lang, x=f'{exc:.1f}°/s')); out['status'] = 'lowexc'
        return out
    low_rate = rate < 18
    if rate < 8:
        out['notes'].append(tx('lowrate', lang, hz=int(round(rate)))); out['status'] = 'na'
        return out
    lag0 = _lag_ms(des_d, act_d, hz); k0 = int(round(lag0 / 1000.0 * hz))
    dd0, aa0 = (des_d[:len(des_d) - k0], act_d[k0:]) if k0 > 0 else (des_d, act_d)
    cc = float(np.corrcoef(dd0, aa0)[0, 1]) if np.std(aa0) > 0 else 0.0   # gecikme düzeltilmiş ilinti
    out['metrics']['corr'] = _r(cc)
    if not np.isfinite(cc) or cc < 0.5:
        out['notes'].append(tx('lowcorr', lang, c=_r(cc))); out['status'] = 'na'
        return out
    # Yalnız manevra içeren örnekler üzerinden kazanç oranı (|istenen| > 2°/s)
    m = np.abs(des_d) > 2.0
    gain = float(np.dot(des_d[m], act_d[m]) / max(np.dot(des_d[m], des_d[m]), 1e-9)) if m.sum() > 20 else 1.0
    lag = _lag_ms(des_d, act_d, hz)
    # gecikmeyi düzelterek kazanç oranını yeniden ölç (gecikme kazancı düşük gösterir)
    k = int(round(lag / 1000.0 * hz))
    if k > 0 and m.sum() > 20:
        dd, aa = des_d[:-k], act_d[k:]; mm = np.abs(dd) > 2.0
        if mm.sum() > 20: gain = float(np.dot(dd[mm], aa[mm]) / max(np.dot(dd[mm], dd[mm]), 1e-9))
    err = act_d - des_d
    e_pct = 100.0 * float(np.sqrt(np.mean(err ** 2)) / max(np.sqrt(np.mean(des_d ** 2)), 1e-6))
    # Salınım: komutla açıklanamayan kalıntıda (gecikme + kazanç düzeltilmiş) aranır
    res = (act_d[k:] - gain * des_d[:len(des_d) - k]) if k > 0 else act_d - gain * des_d
    f_osc, p_osc = _osc(res, hz, ref=des_d[:len(res)])
    nyq = hz / 2.0
    osc = f_osc is not None and p_osc >= 25.0 and np.std(res) > 1.5 and _periodic(res, hz, f_osc) > 0.3
    shares = {}
    if have_terms:
        tot = np.abs(d['P']) + np.abs(d['I']) + np.abs(d['D']) + (np.abs(d['FF']) if 'FF' in d else 0) + 1e-9
        for k_ in ('P', 'I', 'D', 'FF'):
            if k_ in d: shares[k_] = float(np.mean(np.abs(d[k_]) / tot))
        # I sürekli yüklü mü: I'nın işaretli ortalaması toplamın büyük kısmı
        i_load = float(abs(np.mean(d['I'])) / max(np.mean(tot), 1e-9))
    else:
        i_load = 0.0
    out['metrics'].update(gain=_r(gain), lag=_r(lag, 0), err=_r(e_pct, 0), f_osc=_r(f_osc, 1) if osc else None,
                          p_osc=_r(p_osc, 0) if osc else None, shares={k_: _r(v, 2) for k_, v in shares.items()}, i_load=_r(i_load, 2))
    out['metrics_text'] = tx('metrics', lang, g=_r(gain), lag=int(lag), e=int(e_pct),
                             osc=tx('osc_f', lang, f=_r(f_osc, 1), p=int(p_osc)) if osc else tx('osc_none', lang))
    # güven: veri süresi + uyarım
    dur = len(g) / hz
    conf = 'c_hi' if (dur > 120 and exc > 8) else 'c_mid' if (dur > 40 and exc > 4) else 'c_lo'
    if low_rate:
        # 10 Hz kayıt: yalnız büyük kazanç hataları ve düşük frekanslı salınım güvenle görülür
        conf = 'c_lo'; out['notes'].append(tx('lowrate2', lang, hz=int(round(rate))))
        gain_ok = (0.6 <= gain <= 1.35) or cc < 0.7
    else:
        gain_ok = None
    recs = []
    if osc:
        hf = f_osc >= min(hf_hz, nyq * 0.7)
        if hf and shares.get('D', 0) > 0.25:
            r_ = _rec(P, spec['D'][0], 0.75, tx('r_osc_hf_d', lang), conf, lang, spec['D'][1:]); r_ and recs.append(r_)
        elif hf:
            r_ = _rec(P, spec['P'][0], 0.8, tx('r_osc_hf_p', lang), conf, lang, spec['P'][1:]); r_ and recs.append(r_)
            if shares.get('D', 0) > 0.15:
                r_ = _rec(P, spec['D'][0], 0.85, tx('r_osc_hf_p', lang), conf, lang, spec['D'][1:]); r_ and recs.append(r_)
        else:
            if multirotor:
                r_ = _rec(P, spec['ANG'][0], 0.85, tx('r_osc_lf', lang), conf, lang); r_ and recs.append(r_)
            elif spec.get('TC'):
                r_ = _rec(P, spec['TC'][0], 1.2, tx('r_osc_lf', lang), conf, lang); r_ and recs.append(r_)
            else:
                r_ = _rec(P, spec['P'][0], 0.85, tx('r_osc_lf', lang), conf, lang, spec['P'][1:]); r_ and recs.append(r_)
    elif gain_ok:
        pass
    elif gain > 1.2:
        name_ = spec['FF'] if (not multirotor and shares.get('FF', 0) > shares.get('P', 0)) else spec['P']
        r_ = _rec(P, name_[0], 1.0 / gain, tx('r_overshoot', lang), conf, lang, name_[1:]); r_ and recs.append(r_)
    elif gain < 0.75:
        if multirotor:
            r_ = _rec(P, spec['P'][0], min(1.25, 0.9 / max(gain, 0.3)), tx('r_sluggish_p', lang, g=_r(gain), lag=int(lag)), conf, lang); r_ and recs.append(r_)
        else:
            r_ = _rec(P, spec['FF'][0], min(1.25, 1.0 / max(gain, 0.3)), tx('r_sluggish_ff', lang, g=_r(gain)), conf, lang, spec['FF'][1:])
            if not r_:  # FF yok / 0 → P
                r_ = _rec(P, spec['P'][0], 1.15, tx('r_sluggish_p', lang, g=_r(gain), lag=int(lag)), conf, lang, spec['P'][1:])
            r_ and recs.append(r_)
    if not low_rate and not osc and lag > (180 if not multirotor else 90) and gain >= 0.75 and spec.get('TC'):
        r_ = _rec(P, spec['TC'][0], 0.85, tx('r_lag', lang, lag=int(lag)), 'c_lo', lang); r_ and recs.append(r_)
    if i_load > 0.45 and ax != 'yaw':
        out['notes'].append(tx('r_i_load', lang, x=int(100 * i_load)))
    out['recs'] = recs
    out['status'] = 'bad' if osc else 'warn' if recs or i_load > 0.45 else 'good'
    if out['status'] == 'good': out['notes'].append(tx('ok', lang))
    out['conf'] = conf
    return out


# ------------------------------------------------------------------ TECS
def tecs(L, flights, P, lang):
    out = {'axis': 'tecs', 'title': tx('tecs', lang), 'recs': [], 'notes': [], 'metrics': {}}
    s = L.s('TECS')
    s = type(s)(s)
    for a, b in (('h_dem', 'hdem'), ('dh_dem', 'dhdem'), ('sp_dem', 'spdem'), ('dsp_dem', 'dspdem')):   # eski sürüm alan adları
        if a in s and b not in s: s[b] = s[a]
    G = _grid(s, ['h', 'hdem', 'dh', 'sp', 'spdem'], flights, hz=10.0)
    if G is None:
        out['notes'].append(tx('nodata', lang, m='TECS')); out['status'] = 'na'; return out
    g, d, hz, rate = G
    # gaz: TECS.th (0..1) ya da CTUN.ThO (%)
    ct = L.s('CTUN')
    if s.has('th'):
        thr = np.interp(g, s['t'], s['th']); thr = thr * 100 if np.nanmax(thr) <= 1.5 else thr
    elif ct.has('ThO'):
        thr = np.interp(g, ct['t'], ct['ThO'])
    else:
        thr = None
    he = d['h'] - d['hdem']; se = d['sp'] - d['spdem']
    # Kalkış / iniş dışında (hdem değişimi makul) ölç
    hrms = float(np.sqrt(np.mean(he ** 2))); srms = float(np.sqrt(np.mean(se ** 2)))
    tmax_p = float(P.get('THR_MAX', 100)); tmin_p = float(P.get('THR_MIN', 0))
    tm = float(np.mean(thr >= tmax_p - 2)) * 100 if thr is not None else 0.0
    tn = float(np.mean(thr <= tmin_p + 2)) * 100 if thr is not None else 0.0
    us = 0.0
    if s.has('f'):
        fl = np.interp(g, s['t'], s['f']).astype(int); us = float(np.mean((fl & 1) > 0)) * 100
    out['metrics'] = dict(h_rms=_r(hrms, 1), s_rms=_r(srms, 1), thr_max_pct=_r(tm, 0), thr_min_pct=_r(tn, 0), underspeed_pct=_r(us, 0), n=len(g))
    out['metrics_text'] = tx('t_metrics', lang, h=_r(hrms, 1), s=_r(srms, 1), tm=int(tm), tn=int(tn), u=int(us))
    dur = len(g) / hz
    conf = 'c_hi' if dur > 300 else 'c_mid' if dur > 90 else 'c_lo'
    recs = []
    dh = d['dh']
    if P.get('ARSPD_USE', 1) == 0: out['notes'].append(tx('r_no_arspd', lang))
    if thr is not None:
        # gerçek tırmanma kapasitesi: tam gazda en az 5 sn süren tırmanma örnekleri
        full = thr >= tmax_p - 2
        if full.sum() > 5 * hz:
            clmb = float(np.percentile(dh[full], 75))
            cur = float(P.get('TECS_CLMB_MAX', 5.0))
            if clmb > 0.5 and cur > clmb * 1.15 and tm > 8:
                r_ = _rec(P, 'TECS_CLMB_MAX', (clmb * 0.9) / cur, tx('r_clmb', lang, x=_r(clmb, 1)), conf, lang); r_ and recs.append(r_)
        idle = thr <= tmin_p + 2
        if idle.sum() > 5 * hz:
            sink = float(-np.percentile(dh[idle], 25))
            cur = float(P.get('TECS_SINK_MAX', 5.0))
            spd_up = float(np.mean(se[idle] > 2.0))
            if sink > 0.5 and cur > sink * 1.2 and spd_up > 0.3:
                r_ = _rec(P, 'TECS_SINK_MAX', (sink * 0.95) / cur, tx('r_sink', lang, x=_r(sink, 1)), conf, lang); r_ and recs.append(r_)
        # düz uçuş gazı: |dh| küçük, hız hedefte, gaz sınırda değil
        lvl = (np.abs(dh) < 0.5) & (np.abs(se) < 1.5) & (thr > tmin_p + 2) & (thr < tmax_p - 2)
        if lvl.sum() > 30 * hz and 'TRIM_THROTTLE' in P:
            trim = float(np.median(thr[lvl])); cur = float(P['TRIM_THROTTLE'])
            if abs(trim - cur) > max(5.0, 0.12 * cur):
                recs.append({'param': 'TRIM_THROTTLE', 'cur': _r(cur, 0), 'new': float(int(round(min(max(trim, cur * 0.75), cur * 1.25)))),
                             'why': tx('r_trim_thr', lang, x=int(round(trim))), 'conf': conf})
    # irtifa salınımı (porpoising): 4–40 sn periyot
    # Yalnız hedef irtifanın sabit olduğu (düz uçuş) bölümlerde: tırmanma/alçalma adımları salınım sanılmasın
    k2 = max(int(2 * hz), 1); hd = d['hdem']
    dhd = np.abs(np.concatenate([np.zeros(k2), (hd[k2:] - hd[:-k2]) / 2.0]))   # 2 sn'lik ortalama eğim
    lvl_h = np.convolve((dhd < 0.3).astype(float), np.ones(int(5 * hz)) / int(5 * hz), mode='same') > 0.99
    parts = []; seg_idx = []; i = 0; n_ = len(he)
    while i < n_:
        if lvl_h[i]:
            j = i
            while j < n_ and lvl_h[j]: j += 1
            if j - i > 60 * hz: parts.append(he[i:j] - np.mean(he[i:j])); seg_idx.append((i, j))
            i = j
        else:
            i += 1
    per, ac = _acf_period(parts, hz, 4.0, 40.0)
    amp = float(np.std(np.concatenate(parts))) if parts else 0.0
    if per and ac > 0.4 and amp > 2.0:
        a = _r(amp * 1.41, 1); why = tx('r_porp', lang, p=_r(per, 0), a=a)
        if P.get('TECS_PTCH_DAMP', 0):
            r_ = _rec(P, 'TECS_PTCH_DAMP', 1.25, why, conf, lang); r_ and recs.append(r_)
        elif 'TECS_PTCH_DAMP' in P:
            recs.append({'param': 'TECS_PTCH_DAMP', 'cur': 0.0, 'new': 0.1, 'why': why, 'conf': conf})
    # hız salınımı: aynı düz uçuş bölümlerinde hız hatası
    sp_parts = [se[a:b] - np.mean(se[a:b]) for a, b in seg_idx]
    per_s, ac_s = _acf_period(sp_parts, hz, 3.0, 40.0)
    amp_s = float(np.std(np.concatenate(sp_parts))) if sp_parts else 0.0
    if per_s and ac_s > 0.4 and amp_s > 1.2:
        r_ = _rec(P, 'TECS_THR_DAMP', 1.25, tx('r_spd_osc', lang, a=_r(amp_s * 1.41, 1)), conf, lang); r_ and recs.append(r_)
    if not recs and hrms > 6 and tm < 5 and tn < 5:
        r_ = _rec(P, 'TECS_TIME_CONST', 0.8, tx('r_h_lag', lang, h=_r(hrms, 1)), 'c_mid', lang); r_ and recs.append(r_)
    if us > 5: out['notes'].append(tx('r_underspeed', lang, u=int(us)))
    out['recs'] = recs; out['conf'] = conf
    out['status'] = 'warn' if recs or us > 5 else 'good'
    if out['status'] == 'good': out['notes'].append(tx('ok', lang))
    return out


# ------------------------------------------------------------------ multikopter irtifa
FW_MODES = {1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15}    # sabit kanat PID'lerinin çalıştığı modlar (MANUAL ve Q modları hariç)
TECS_MODES = {6, 7, 10, 11, 12, 15}                       # FBWB, CRUISE, AUTO, RTL, LOITER, GUIDED: TECS irtifa/hız kontrolü
ALT_MODES = {2, 3, 4, 5, 6, 9, 15, 16, 17, 21}   # ALT_HOLD, AUTO, GUIDED, LOITER, RTL, LAND, AUTOTUNE, POSHOLD, BRAKE, SMART_RTL


def _mode_windows(L, flights, modes):
    """Uçuş aralıklarını yalnız verilen modlardaki parçalara indirger."""
    ms = L.modes or []
    if not ms: return flights
    out = []
    for i, (t, num, _, _) in enumerate(ms):
        if int(num) not in modes: continue
        t1 = ms[i + 1][0] if i + 1 < len(ms) else 1e12
        for a, b in flights:
            lo, hi = max(a, t), min(b, t1)
            if hi - lo > 15: out.append((lo, hi))
    return out
def copter_alt(L, flights, P, lang, prefix='MOT_', psc='PSC_'):
    out = {'axis': 'alt', 'title': tx('alt', lang), 'recs': [], 'notes': [], 'metrics': {}}
    s = L.s('CTUN')
    # İrtifa denetimi yalnız irtifa tutan modlarda anlamlı (STABILIZE/ACRO'da DAlt pilotu izler)
    flights = _mode_windows(L, flights, ALT_MODES) or []
    G = _grid(s, ['ThO', 'Alt', 'DAlt'], flights, hz=10.0)
    if G is None:
        out['notes'].append(tx('nodata', lang, m='CTUN')); out['status'] = 'na'; return out
    g, d, hz, rate = G
    ae = d['Alt'] - d['DAlt']
    out['metrics'] = dict(alt_rms=_r(np.sqrt(np.mean(ae ** 2)), 2), n=len(g))
    recs = []
    crt = np.interp(g, s['t'], s['CRt']) if s.has('CRt') else np.gradient(d['Alt'], 1.0 / hz)
    hov = np.abs(crt) < 0.3
    if hov.sum() > 20 * hz and P.get(prefix + 'HOVER_LEARN', 2) == 0 and (prefix + 'THST_HOVER') in P:
        x = float(np.median(d['ThO'][hov])); x = x / 100 if x > 1.5 else x
        cur = float(P[prefix + 'THST_HOVER'])
        if abs(x - cur) > 0.04:
            recs.append({'param': prefix + 'THST_HOVER', 'cur': _r(cur, 3), 'new': _r(min(max(x, 0.125), 0.6875), 3),
                         'why': tx('r_hover', lang, x=_r(x, 3), c=_r(cur, 3)), 'conf': 'c_hi' if hov.sum() > 60 * hz else 'c_mid'})
    cut = np.where(np.diff(g) > 1.5 / hz)[0] + 1
    parts = [x for x in np.split(ae, cut) if len(x) > 30 * hz]
    per, ac = _acf_period(parts, hz, 1.5, 12.0)
    amp = float(np.std(np.concatenate(parts))) if parts else 0.0
    out['metrics'].update(alt_osc_s=_r(per, 1) if per else None, alt_osc_r=_r(ac, 2))
    if per and ac > 0.45 and amp > 0.5:
        why = tx('r_alt_osc', lang, p=_r(per, 1), a=_r(amp * 1.41, 2))
        for n_ in (psc + 'ACCZ_P', psc + 'ACCZ_I'):
            r_ = _rec(P, n_, 0.8, why, 'c_mid', lang); r_ and recs.append(r_)
    out['recs'] = recs; out['status'] = 'warn' if recs else 'good'
    if not recs: out['notes'].append(tx('ok', lang))
    return out


# ------------------------------------------------------------------ giriş
def analyze(A, lang='tr'):
    """A: analysis.Analysis. Döner {'profile','axes':[...], 'recs':[...], 'disclaimer'}."""
    L = A.L; P = L.params or {}; prof = getattr(A, 'profile', 'plane')
    flights = [f for f in (A.flights or []) if f[1] - f[0] > 15]
    if not flights:
        return {'profile': prof, 'axes': [], 'recs': [], 'disclaimer': tx('disclaimer', lang), 'note': tx('noflight', lang)}
    axes = []
    if prof in ('copter', 'heli'):
        spec = _copter_ax('ATC_')
        for ax in ('roll', 'pitch', 'yaw'):
            axes.append(rate_axis(L, flights, ax, spec[ax], P, lang, True, hf_hz=3.0))
        axes.append(copter_alt(L, flights, P, lang))
    elif prof == 'rover':
        pass
    else:
        fw = _mode_windows(L, flights, FW_MODES) if L.modes else flights
        for ax in ('roll', 'pitch', 'yaw'):
            if ax == 'yaw' and P.get('YAW_RATE_ENABLE', 0) == 0 and not L.s('PIDY').has('Tar'): continue
            axes.append(rate_axis(L, fw, ax, PLANE_AX[ax], P, lang, False, hf_hz=2.0))
        axes.append(tecs(L, _mode_windows(L, flights, TECS_MODES) if L.modes else flights, P, lang))
        if prof == 'vtol' and L.s('RATE').has('RDes'):
            # QuadPlane: Q modlarındaki çok rotorlu ayar (RATE mesajı, Q_A_ parametreleri)
            qf = _q_flights(A) or flights
            spec = _copter_ax('Q_A_')
            for ax in ('roll', 'pitch'):
                spec[ax] = dict(spec[ax]); spec[ax]['msg'] = '__none__'   # PID mesajları sabit kanada ait → RATE kullan
                r_ = rate_axis(L, qf, ax, spec[ax], P, lang, True, hf_hz=3.0)
                r_['title'] = 'VTOL · ' + r_['title']; r_['axis'] = 'q_' + ax
                axes.append(r_)
    recs = []
    for a in axes:
        for r_ in a.get('recs', []):
            r_ = dict(r_); r_['axis'] = a['title']; r_['conf_t'] = tx(r_['conf'], lang); recs.append(r_)
    return {'profile': prof, 'axes': axes, 'recs': recs, 'disclaimer': tx('disclaimer', lang)}


def _q_flights(A):
    try:
        from .profiles import Q_MODES
        out = []; ms = A.L.modes
        for i, (t, num, nm, _) in enumerate(ms):
            if num in Q_MODES:
                t1 = ms[i + 1][0] if i + 1 < len(ms) else A.L.duration
                if t1 - t > 10: out.append((t, t1))
        return out
    except Exception:
        return []


def param_file(res, vehicle=''):
    """Önerilen değişiklikleri Mission Planner .param biçiminde döndürür."""
    lines = [f'# Pixhawk Log Analiz — tuning recommendations ({vehicle}). Back up first; test one change at a time.']
    for r_ in res.get('recs', []):
        lines.append(f"# {r_['param']}: {r_['cur']} -> {r_['new']}")
        lines.append(f"{r_['param']},{r_['new']}")
    return '\n'.join(lines) + '\n'
