"""Video ↔ log eşleme, OSD bindirme ve birleştirilmiş video dışa aktarma.

Videolar: ana video (uçak kamerası ya da yerden çekim) + isteğe bağlı ikinci video (FPV gözlük / DVR kaydı, OSD'li yayın).
Eşleme: log_zamanı = video_zamanı + ofset. Ofset üç yoldan bulunur: videonun kayıt saati (creation_time ya da dosya
tarihi − süre) ile logun GPS saati, videoda ve logda aynı olayın işaretlenmesi (kalkış, ARM, mod değişimi, kırım) ya da elle.
Çözme/kodlama programla gelen ffmpeg (imageio-ffmpeg) ile yapılır; OSD Pillow ile çizilir.
"""
from __future__ import annotations
import calendar, math, os, re, subprocess, sys, threading, time
import numpy as np

from .video import ffmpeg_exe

LI = {'tr': 0, 'en': 1, 'ar': 2}
_NOWIN = 0x08000000 if sys.platform.startswith('win') else 0


def _run(args, **kw):
    return subprocess.run(args, capture_output=True, creationflags=_NOWIN, **kw)


# ------------------------------------------------------------------ video bilgisi
def probe(path):
    """{'dur','w','h','fps','created' (unix|None),'created_src','rot','audio'}"""
    exe = ffmpeg_exe()
    if not exe: raise RuntimeError('ffmpeg')
    r = _run([exe, '-hide_banner', '-i', path])
    s = r.stderr.decode('utf-8', 'replace')
    info = {'path': path, 'dur': 0.0, 'w': 0, 'h': 0, 'fps': 30.0, 'created': None, 'created_src': None, 'rot': 0, 'audio': False}
    m = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', s)
    if m: info['dur'] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    vm = re.search(r'Stream #[^\n]*Video:[^\n]*?(\d{2,5})x(\d{2,5})[^\n]*', s)
    if vm:
        info['w'], info['h'] = int(vm.group(1)), int(vm.group(2))
        fm = re.search(r'([\d.]+)\s*fps', vm.group(0)) or re.search(r'([\d.]+)\s*tbr', vm.group(0))
        if fm:
            try: info['fps'] = max(1.0, min(240.0, float(fm.group(1))))
            except ValueError: pass
    if re.search(r'Stream #[^\n]*Audio:', s): info['audio'] = True
    rm = re.search(r'rotation of (-?[\d.]+)', s) or re.search(r'rotate\s*:\s*(-?\d+)', s)
    if rm:
        rot = int(round(float(rm.group(1)))) % 360
        info['rot'] = rot
        if rot in (90, 270): info['w'], info['h'] = info['h'], info['w']
    cm = re.search(r'creation_time\s*:\s*(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z?', s)
    if cm:
        y, mo, d, hh, mi, ss = (int(x) for x in cm.groups())
        if y > 2005:
            info['created'] = calendar.timegm((y, mo, d, hh, mi, ss, 0, 0, 0)); info['created_src'] = 'meta'
    if info['created'] is None:
        try:
            info['created'] = os.path.getmtime(path) - info['dur']; info['created_src'] = 'mtime'
        except OSError: pass
    if not info['w']: raise RuntimeError('no_video')
    return info


def auto_offset(L, info):
    """(ofset, kaynak) — video başlangıç saati ile logun GPS saatinden. Bulunamazsa (None, None)."""
    if not info.get('created') or not getattr(L, 'gps_time0', None): return None, None
    u0 = L.unix_at(0.0)
    off = float(info['created'] - u0)
    # bazı kameralar yerel saati UTC diye yazar: logun içine düşmüyorsa saat dilimi kaydırmalarını dene
    dur = float(L.duration or 0)
    def inside(o): return -info['dur'] <= o <= dur + 5
    if not inside(off):
        for h in sorted(range(-14, 15), key=abs):
            if inside(off - h * 3600):
                return off - h * 3600, info['created_src'] + f'{-h:+d}h'
    return off, info['created_src']


def event_list(A, lg='tr'):
    """Eşleme için olaylar: [(log_t, ad)]"""
    from . import viz
    T = {'arm': ('ARM (motorlar açıldı)', 'ARM (motors armed)', 'التسليح'), 'disarm': ('DISARM', 'DISARM', 'نزع التسليح'),
         'to': ('Kalkış', 'Takeoff', 'الإقلاع'), 'land': ('İniş / uçuş sonu', 'Landing / flight end', 'الهبوط / نهاية الطيران'),
         'mode': ('Mod', 'Mode', 'الوضع'), 'root': ('İlk belirti (kök neden)', 'First symptom (root cause)', 'أول عرض')}
    tx = lambda k: T[k][LI.get(lg, 0)]  # noqa: E731
    out = []
    for t_, on in getattr(A, 'armed', None) or []:
        out.append((t_, tx('arm') if on else tx('disarm')))
    if not out:
        for t_, on in A.L.arm: out.append((t_, tx('arm') if on else tx('disarm')))
    for a, b in A.flights or []:
        out.append((a, tx('to'))); out.append((b, tx('land')))
    for s in viz.segments(A, lg)[1:40]:
        out.append((s['t0'], f"{tx('mode')}: {s['prev']} → {s['name']}"))
    r = (A.root or {}).get('t')
    if r is not None: out.append((r, tx('root')))
    seen = set(); res = []
    for t_, n in sorted(out):
        k = (round(t_, 1), n)
        if k in seen: continue
        seen.add(k); res.append((float(t_), n))
    return res


# ------------------------------------------------------------------ kare okuyucu
def out_size(info, width):
    w = int(width) // 2 * 2
    h = int(round(w * info['h'] / max(1, info['w']) / 2)) * 2
    return w, max(2, h)


class FrameReader:
    """ffmpeg ile belirli bir andan başlayarak RGB kareler (numpy HxWx3) okur."""
    def __init__(self, info, width=960, fps=None, start=0.0):
        self.info = info; self.W, self.H = out_size(info, width)
        self.fps = float(fps or min(30.0, info['fps'])); self.t = float(max(0.0, start)); self.n = 0
        exe = ffmpeg_exe()
        args = [exe, '-hide_banner', '-loglevel', 'error', '-ss', f'{self.t:.3f}', '-i', info['path'], '-an',
                '-vf', f'fps={self.fps:g},scale={self.W}:{self.H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
        self.p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                                  creationflags=_NOWIN, bufsize=self.W * self.H * 3 * 2)
        self.size = self.W * self.H * 3

    def read(self):
        """(video_zamanı, kare) ya da None (bitti)."""
        buf = b''
        while len(buf) < self.size:
            b = self.p.stdout.read(self.size - len(buf))
            if not b: return None
            buf += b
        t = self.t + self.n / self.fps; self.n += 1
        return t, np.frombuffer(buf, np.uint8).reshape(self.H, self.W, 3)

    def close(self):
        try:
            self.p.stdout.close()
        except Exception: pass
        try:
            self.p.kill(); self.p.wait(timeout=2)
        except Exception: pass


def grab(info, t, width=960):
    r = FrameReader(info, width, fps=min(30.0, info['fps']), start=t)
    try:
        f = r.read()
        return f[1] if f else None
    finally:
        r.close()


# ------------------------------------------------------------------ OSD verisi
class OSDData:
    """Logdan OSD için hızlı örnekleme (searchsorted)."""
    def __init__(self, A, lg='tr'):
        from . import viz
        self.A = A; L = A.L; self.lg = lg
        self.segs = viz.segments(A, lg)

        def ser(m, f):
            s = L.s(m)
            if s.has(f): return (np.asarray(s['t'], float), np.asarray(s[f], float))
            return None
        self.roll = ser('ATT', 'Roll'); self.pitch = ser('ATT', 'Pitch'); self.yaw = ser('ATT', 'Yaw')
        tr = A.track
        self.alt = (np.asarray(tr['t'], float), np.asarray(tr['rel'], float)) if tr is not None else ser('BARO', 'Alt')
        self.gs = ser('GPS', 'Spd'); self.asp = ser('ARSP', 'Airspeed') or ser('CTUN', 'As')
        self.volt = ser('BAT', 'Volt'); self.curr = ser('BAT', 'Curr'); self.mah = ser('BAT', 'CurrTot')
        self.sats = ser('GPS', 'NSats'); self.hdop = ser('GPS', 'HDop')
        self.vz = ser('CTUN', 'CRt') or ser('QTUN', 'CRt')
        self.thr = ser('CTUN', 'ThO') or ser('CTUN', 'ThrOut')
        self.home = None
        if tr is not None and len(tr['t']):
            lat0, lon0 = float(tr['lat'][0]), float(tr['lon'][0])
            from .analysis import hav
            self.dist = (np.asarray(tr['t'], float), np.asarray([hav(lat0, lon0, a, b) for a, b in zip(tr['lat'][::1], tr['lon'][::1])], float)) \
                if len(tr['t']) < 200000 else None
            self.lat = (np.asarray(tr['t'], float), np.asarray(tr['lat'], float)); self.lon = (np.asarray(tr['t'], float), np.asarray(tr['lon'], float))
        else:
            self.dist = None; self.lat = self.lon = None
        self.rc = None
        try:
            if viz.rc_active(A):
                m = viz.rc_map(A); r = L.s('RCIN')
                self.rc = {k: (np.asarray(r['t'], float), np.asarray(viz.stick_norm(A, m[k], r[f'C{m[k]}'], centred=k != 'thr'), float))
                           for k in ('roll', 'pitch', 'thr', 'yaw') if r.has(f'C{m[k]}')}
        except Exception:
            self.rc = None
        ww = ('fail', 'error', 'bad', 'lost', 'low', 'critical', 'crash', 'glitch', 'variance', 'unhealthy', 'emergency', 'stall', 'clip',
              'prearm', 'warning', 'timeout', 'reset', 'lane switch', 'failsafe', 'land', 'takeoff', 'armed', 'mission', 'transition')
        self.msgs = [(float(t_), s_) for t_, s_ in L.texts if any(w in s_.lower() for w in ww)]
        try:
            self.mev = [(e['t'], viz.event_text(A, e, lg)) for e in viz.motor_events(A, lg).get('events', [])]
        except Exception:
            self.mev = []

    @staticmethod
    def at(s, t):
        if s is None: return None
        tt, yy = s
        if not len(tt) or t < tt[0] - 2 or t > tt[-1] + 2: return None
        i = int(np.searchsorted(tt, t)); i = min(max(i, 0), len(tt) - 1)
        v = float(yy[i]); return v if math.isfinite(v) else None

    def sample(self, t):
        from . import viz
        g = lambda s: self.at(s, t)  # noqa: E731
        md = viz.mode_at(self.A, t, self.segs)
        d = {'t': t, 'roll': g(self.roll), 'pitch': g(self.pitch), 'yaw': g(self.yaw), 'alt': g(self.alt), 'gs': g(self.gs), 'as': g(self.asp),
             'volt': g(self.volt), 'curr': g(self.curr), 'mah': g(self.mah), 'sats': g(self.sats), 'hdop': g(self.hdop), 'vz': g(self.vz),
             'thr': g(self.thr), 'dist': g(self.dist), 'mode': md['name'] if md else '', 'mode_col': md['col'] if md else '#64748B',
             'fs': bool(md and md.get('fs')), 'clock': viz.clock(self.A, t) or ''}
        if self.rc: d['rc'] = {k: self.at(v, t) for k, v in self.rc.items()}
        d['msg'] = [s_ for t_, s_ in self.msgs if t - 4 <= t_ <= t + 0.2][-2:]
        d['mev'] = [s_ for t_, s_ in self.mev if t_ - 1 <= t <= t_ + 6][-1:]
        return d


# ------------------------------------------------------------------ OSD çizimi
OSD_KEYS = ['mode', 'alt', 'speed', 'bat', 'horizon', 'gps', 'sticks', 'warn', 'clock', 'thr']
OSD_LBL = {
    'mode': ('Uçuş modu', 'Flight mode', 'وضع الطيران'), 'alt': ('İrtifa + tırmanma', 'Altitude + climb', 'الارتفاع + الصعود'),
    'speed': ('Hız (hava / yer)', 'Speed (air / ground)', 'السرعة (جوية / أرضية)'), 'bat': ('Batarya (V, A, mAh)', 'Battery (V, A, mAh)', 'البطارية'),
    'horizon': ('Yapay ufuk', 'Artificial horizon', 'الأفق الاصطناعي'), 'gps': ('GPS ve eve uzaklık', 'GPS and home distance', 'GPS والمسافة للمنزل'),
    'sticks': ('Kumanda stickleri', 'RC sticks', 'عصي التحكم'), 'warn': ('Uyarılar ve mesajlar', 'Warnings and messages', 'التحذيرات والرسائل'),
    'clock': ('Saat ve log zamanı', 'Clock and log time', 'الساعة وزمن السجل'), 'thr': ('Gaz %', 'Throttle %', 'الخانق %'),
}
_FONTS = {}


def _font(sz, bold=True):
    from PIL import ImageFont
    k = (sz, bold)
    if k not in _FONTS:
        f = None
        try:
            import matplotlib
            p = os.path.join(matplotlib.get_data_path(), 'fonts', 'ttf', 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
            f = ImageFont.truetype(p, sz)
        except Exception:
            f = ImageFont.load_default()
        _FONTS[k] = f
    return _FONTS[k]


_RAQM = None


def _sh(s, lg):
    """Pillow raqm ile derlenmişse Arapçayı kendisi şekillendirir; değilse elle şekillendir."""
    global _RAQM
    if lg != 'ar': return s
    if _RAQM is None:
        try:
            from PIL import features
            _RAQM = bool(features.check('raqm'))
        except Exception:
            _RAQM = False
    if _RAQM: return s
    from .charts import shape
    return shape(s, lg)


def _hex(c, a=255):
    c = c.lstrip('#'); return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


def draw_osd(img, d, opts=None, lg='tr', fmt_t=None):
    """img: PIL RGBA (değiştirilir). d: OSDData.sample(). opts: gösterilecek öğeler kümesi."""
    from PIL import ImageDraw
    opts = set(OSD_KEYS if opts is None else opts)
    W, H = img.size; s = W / 1280.0
    from PIL import Image as _I
    ov = _I.new('RGBA', img.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    F = _font(max(10, int(22 * s))); Fs = _font(max(9, int(16 * s))); Fb = _font(max(12, int(30 * s)))
    pad = int(14 * s); white = (255, 255, 255, 255); sh = (0, 0, 0, 170)

    def txt(x, y, s_, f=F, col=white, anchor='la'):
        s_ = _sh(s_, lg)
        for dx, dy in ((1, 1), (2, 2)):
            dr.text((x + dx, y + dy), s_, font=f, fill=sh, anchor=anchor)
        dr.text((x, y), s_, font=f, fill=col, anchor=anchor)

    def box(x0, y0, x1, y1, col=(0, 0, 0, 110)):
        dr.rounded_rectangle((x0, y0, x1, y1), radius=int(8 * s), fill=col)

    def f1(v, n=1, u=''):
        return '—' if v is None else f'{v:.{n}f}{u}'

    # üst: mod + saat
    if 'mode' in opts and d.get('mode'):
        m = d['mode']; w_ = int(dr.textlength(_sh(m, lg), font=Fb)) + 2 * pad
        box(pad, pad, pad + w_, pad + int(44 * s), _hex(d['mode_col'], 215))
        txt(pad + pad, pad + int(6 * s), m, Fb)
        if d.get('fs'): txt(pad + w_ + pad, pad + int(10 * s), 'FAILSAFE', F, (255, 80, 80, 255))
    if 'clock' in opts:
        c = d.get('clock') or ''
        lt = fmt_t(d['t']) if fmt_t else f"{d['t']:.1f}s"
        txt(W - pad, pad, (f'{c}   ' if c else '') + f'LOG {lt}', Fs, anchor='ra')
    # batarya sağ üst
    if 'bat' in opts and d.get('volt') is not None:
        y = pad + int(30 * s)
        v = f1(d['volt'], 2, ' V')
        if d.get('curr') is not None and abs(d['curr']) > 0.2: v += f'   {f1(d["curr"], 1, " A")}'
        if d.get('mah'): v += f'   {d["mah"]:.0f} mAh'
        txt(W - pad, y, v, F, anchor='ra')
    # sol: irtifa
    cy = H // 2
    if 'alt' in opts:
        box(pad, cy - int(46 * s), pad + int(170 * s), cy + int(46 * s))
        txt(pad + int(10 * s), cy - int(40 * s), {'tr': 'İRTİFA', 'en': 'ALT', 'ar': 'الارتفاع'}.get(lg, 'ALT'), Fs, (180, 220, 255, 255))
        txt(pad + int(10 * s), cy - int(18 * s), f1(d.get('alt'), 0, ' m'), Fb)
        if d.get('vz') is not None:
            vz = d['vz'] / (100.0 if abs(d['vz']) > 60 else 1.0)
            txt(pad + int(10 * s), cy + int(18 * s), ('▲ ' if vz >= 0 else '▼ ') + f'{abs(vz):.1f} m/s', Fs)
    # sağ: hız
    if 'speed' in opts:
        x1 = W - pad; x0 = x1 - int(190 * s)
        box(x0, cy - int(46 * s), x1, cy + int(46 * s))
        a_ = d.get('as'); g_ = d.get('gs')
        txt(x1 - int(10 * s), cy - int(40 * s), ({'tr': 'HAVA HIZI', 'en': 'AIRSPEED', 'ar': 'السرعة الجوية'} if a_ is not None else
                                                 {'tr': 'YER HIZI', 'en': 'GROUND SPD', 'ar': 'السرعة الأرضية'}).get(lg, 'SPD'), Fs, (180, 255, 200, 255), anchor='ra')
        txt(x1 - int(10 * s), cy - int(18 * s), f1(a_ if a_ is not None else g_, 1, ' m/s'), Fb, anchor='ra')
        if a_ is not None and g_ is not None:
            txt(x1 - int(10 * s), cy + int(18 * s), ({'tr': 'yer ', 'en': 'gnd ', 'ar': 'أرضية '}.get(lg, '')) + f1(g_, 1, ' m/s'), Fs, anchor='ra')
    # yapay ufuk
    if 'horizon' in opts and d.get('roll') is not None:
        r = math.radians(d['roll']); p = d.get('pitch') or 0.0
        cx = W // 2; L_ = int(220 * s); off = p * 4.0 * s
        dx, dy = math.cos(r) * L_, math.sin(r) * L_
        ox, oy = -math.sin(r) * off, math.cos(r) * off
        for wdt, col in ((int(5 * s) + 2, (0, 0, 0, 140)), (max(2, int(3 * s)), (255, 255, 255, 230))):
            dr.line((cx - dx + ox, cy + dy + oy - 0, cx - int(0.25 * dx) + ox, cy + int(0.25 * dy) + oy), fill=col, width=wdt)
            dr.line((cx + int(0.25 * dx) + ox, cy - int(0.25 * dy) + oy, cx + dx + ox, cy - dy + oy), fill=col, width=wdt)
        dr.line((cx - int(40 * s), cy, cx - int(12 * s), cy), fill=(255, 210, 60, 255), width=max(2, int(3 * s)))
        dr.line((cx + int(12 * s), cy, cx + int(40 * s), cy), fill=(255, 210, 60, 255), width=max(2, int(3 * s)))
        dr.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(255, 210, 60, 255))
        txt(cx, cy + int(60 * s), f"R {d['roll']:+.0f}°   P {p:+.0f}°" + (f"   Y {d['yaw']:.0f}°" if d.get('yaw') is not None else ''), Fs, anchor='ma')
    # alt: GPS, uzaklık, gaz
    yb = H - pad - int(26 * s)
    parts = []
    if 'gps' in opts:
        if d.get('sats') is not None: parts.append(f"GPS {d['sats']:.0f}" + (f" · HDOP {d['hdop']:.1f}" if d.get('hdop') is not None else ''))
        if d.get('dist') is not None: parts.append(('⌂ ' if lg != 'ar' else '') + f"{d['dist']:.0f} m")
    if 'thr' in opts and d.get('thr') is not None:
        th = d['thr'] * (100 if abs(d['thr']) <= 1.5 else 1)
        parts.append(({'tr': 'GAZ', 'en': 'THR', 'ar': 'الخانق'}.get(lg, 'THR')) + f' {th:.0f}%')
    if parts: txt(pad, yb, '    '.join(parts), F)
    # stickler (sağ alt)
    if 'sticks' in opts and d.get('rc'):
        sz = int(70 * s); gap = int(10 * s); x0 = W - pad - 2 * sz - gap; y0 = H - pad - sz - int(34 * s)
        for j, (hx, hy) in enumerate(((d['rc'].get('yaw'), d['rc'].get('thr')), (d['rc'].get('roll'), d['rc'].get('pitch')))):
            bx = x0 + j * (sz + gap)
            dr.rounded_rectangle((bx, y0, bx + sz, y0 + sz), radius=int(8 * s), outline=(255, 255, 255, 200), width=2, fill=(0, 0, 0, 90))
            dr.line((bx + sz // 2, y0 + 4, bx + sz // 2, y0 + sz - 4), fill=(255, 255, 255, 80)); dr.line((bx + 4, y0 + sz // 2, bx + sz - 4, y0 + sz // 2), fill=(255, 255, 255, 80))
            if hx is None or hy is None: continue
            px = bx + sz / 2 + max(-1, min(1, hx / 100)) * (sz / 2 - 6); py = y0 + sz / 2 - max(-1, min(1, hy / 100)) * (sz / 2 - 6)
            dr.ellipse((px - 6 * s, py - 6 * s, px + 6 * s, py + 6 * s), fill=(251, 191, 36, 255))
    # uyarılar
    if 'warn' in opts:
        y = pad + int(56 * s)
        for m in (d.get('mev') or []) + (d.get('msg') or []):
            m = str(m)[:70]
            col = (255, 90, 90, 255) if m in (d.get('mev') or []) or any(w in m.lower() for w in ('fail', 'crash', 'error', 'emergency', 'critical', 'lost')) else (255, 230, 140, 255)
            txt(W // 2, y, m, Fs, col, anchor='ma'); y += int(24 * s)
    img.alpha_composite(ov)
    return img


def osd_frame(frame, d, opts, lg, fmt_t=None):
    from PIL import Image
    im = Image.fromarray(frame).convert('RGBA')
    draw_osd(im, d, opts, lg, fmt_t)
    return im.convert('RGB')


# ------------------------------------------------------------------ yan panel (küçük harita + irtifa)
def side_panel(A, w, h, lg='tr'):
    """Önceden çizilmiş panel arka planı (PIL RGB) ve dönüştürücü: (img, to_xy_map(t), to_xy_alt(t))."""
    from PIL import Image
    import io
    from matplotlib.figure import Figure
    tr = A.track
    fig = Figure(figsize=(w / 100, h / 100), dpi=100); fig.patch.set_facecolor('#0F172A')
    ax1 = fig.add_axes([0.08, 0.40, 0.88, 0.56]); ax2 = fig.add_axes([0.08, 0.07, 0.88, 0.26])
    for ax in (ax1, ax2):
        ax.set_facecolor('#111C33'); ax.tick_params(colors='#94A3B8', labelsize=6)
        for sp in ax.spines.values(): sp.set_color('#334155')
    if tr is not None and len(tr['t']) > 2:
        lat, lon = np.asarray(tr['lat']), np.asarray(tr['lon'])
        ax1.plot(lon, lat, color='#60A5FA', lw=1); ax1.plot(lon[0], lat[0], '*', color='#FBBF24', ms=8)
        ax1.set_aspect('equal', adjustable='datalim'); ax1.set_xticks([]); ax1.set_yticks([])
        ax2.plot(tr['t'], tr['rel'], color='#34D399', lw=0.8); ax2.set_xlim(0, max(1, float(A.L.duration)))
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    cv = FigureCanvasAgg(fig); cv.draw()
    b = io.BytesIO(); fig.savefig(b, format='png', dpi=100, facecolor=fig.get_facecolor()); b.seek(0)
    bg = Image.open(b).convert('RGB').resize((w, h))
    t1 = ax1.transData; t2 = ax2.transData

    def xy(tf, x, y):
        px, py = tf.transform((x, y)); return px * w / (fig.get_figwidth() * 100), h - py * h / (fig.get_figheight() * 100)

    def at_map(t):
        if tr is None: return None
        i = int(np.searchsorted(tr['t'], t)); i = min(max(i, 0), len(tr['t']) - 1)
        return xy(t1, float(tr['lon'][i]), float(tr['lat'][i]))

    def at_alt(t):
        if tr is None: return None
        i = int(np.searchsorted(tr['t'], t)); i = min(max(i, 0), len(tr['t']) - 1)
        return xy(t2, float(t), float(tr['rel'][i]))
    return bg, at_map, at_alt


# ------------------------------------------------------------------ dışa aktarma
def export(A, out, main, off_main, second=None, off_second=0.0, layout='single', osd=True, osd_opts=None, panel=False,
           t0=None, t1=None, width=1280, lg='tr', progress=None, cancel=None):
    """Birleştirilmiş video üretir.
    main/second: probe() sözlükleri · off_*: log_t = video_t + off · layout: 'single' | 'pip' | 'side'
    t0/t1: ana video zamanı aralığı (None → tamamı) · panel: sağda küçük harita + irtifa paneli."""
    from PIL import Image, ImageDraw
    from .analysis import fmt_t
    exe = ffmpeg_exe()
    if not exe: raise RuntimeError('ffmpeg')
    t0 = max(0.0, float(t0 or 0.0)); t1 = min(float(main['dur']), float(t1 if t1 is not None else main['dur']))
    if t1 - t0 < 0.2: raise RuntimeError('range')
    fps = min(30.0, main['fps'])
    mw = width if layout != 'side' or not second else width // 2
    W1, H1 = out_size(main, mw)
    W, H = W1, H1
    sec_r = None; sw = sh_ = 0
    if second:
        if layout == 'side':
            sw, sh_ = out_size(second, W1); sh_ = min(sh_, H1)
            W = W1 + sw
        else:
            sw, sh_ = out_size(second, max(160, W1 // 4))
    pw = int(H * 0.62) // 2 * 2 if panel else 0
    W += pw
    W, H = W // 2 * 2, H // 2 * 2
    D = OSDData(A, lg) if osd or panel else None
    pbg = pat_map = pat_alt = None
    if panel: pbg, pat_map, pat_alt = side_panel(A, pw, H, lg)
    rd1 = FrameReader(main, W1, fps, t0)
    if second:
        st2 = t0 + off_main - off_second
        sec_r = FrameReader(second, sw, fps, max(0.0, st2)); sec_lead = max(0.0, -st2)   # ikinci video henüz başlamadıysa siyah
    args = [exe, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', f'{fps:g}', '-i', '-']
    if main.get('audio'): args += ['-ss', f'{t0:.3f}', '-t', f'{t1 - t0:.3f}', '-i', main['path'], '-map', '0:v', '-map', '1:a?', '-c:a', 'aac', '-b:a', '128k']
    args += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-shortest', out]
    enc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=_NOWIN)
    n_tot = max(1, int((t1 - t0) * fps)); n = 0; last2 = None; tstart = time.time()
    try:
        while n < n_tot:
            if cancel and cancel(): raise RuntimeError('cancelled')
            f = rd1.read()
            if f is None: break
            vt, fr = f
            lt = vt + off_main
            canvas = Image.new('RGB', (W, H), (0, 0, 0))
            base = Image.fromarray(fr)
            if osd and D is not None:
                base = base.convert('RGBA'); draw_osd(base, D.sample(lt), osd_opts, lg, fmt_t); base = base.convert('RGB')
            canvas.paste(base, (0, 0))
            if sec_r is not None:
                if n / fps >= sec_lead:
                    g = sec_r.read()
                    if g is not None: last2 = g[1]
                if last2 is not None:
                    im2 = Image.fromarray(last2)
                    if layout == 'side':
                        canvas.paste(im2.crop((0, 0, sw, min(sh_, im2.size[1]))), (W1, (H1 - sh_) // 2))
                    else:
                        x2, y2 = 12, H1 - sh_ - int(56 * H1 / 720)
                        ImageDraw.Draw(canvas).rectangle((x2 - 3, y2 - 3, x2 + sw + 2, y2 + sh_ + 2), outline=(255, 255, 255))
                        canvas.paste(im2, (x2, y2))
            if panel and pbg is not None:
                pn = pbg.copy(); dd = ImageDraw.Draw(pn)
                p1 = pat_map(lt); p2 = pat_alt(lt)
                if p1: dd.ellipse((p1[0] - 5, p1[1] - 5, p1[0] + 5, p1[1] + 5), fill=(239, 68, 68), outline=(255, 255, 255))
                if p2: dd.line((p2[0], int(H * 0.67), p2[0], H - 4), fill=(251, 191, 36), width=2)
                canvas.paste(pn, (W - pw, 0))
            enc.stdin.write(canvas.tobytes())
            n += 1
            if progress and n % 5 == 0:
                el = time.time() - tstart
                progress({'p': n / n_tot, 'n': n, 'tot': n_tot, 'fps': n / el if el > 0 else 0, 'eta': (n_tot - n) / (n / el) if el > 0 and n else 0})
        enc.stdin.close(); err = enc.stderr.read().decode('utf-8', 'replace'); rc = enc.wait()
        if rc != 0: raise RuntimeError('ffmpeg: ' + err[-400:])
    except BaseException:
        try: enc.kill()
        except Exception: pass
        try: os.remove(out)
        except OSError: pass
        raise
    finally:
        rd1.close()
        if sec_r is not None: sec_r.close()
    return out
