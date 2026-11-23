"""3B uçuş tekrarını ders anlatımıyla MP4 (H.264 + AAC) olarak dışa aktarma — sınıfta oynatmak için.

Akış: ders rehberi adımları (lessons.build) → her adım için sesli anlatım (online: Microsoft Edge nöral sesleri,
offline: Windows'un kendi konuşma motoru) → zaman çizelgesi (adımlar arasında hızlı geçiş, adımda yavaş çekim +
altyazı) → matplotlib ile kare kare çizim → ffmpeg (imageio-ffmpeg içindeki) ile kodlama. Yanına .srt altyazı da yazılır.
"""
from __future__ import annotations
import io, os, shutil, subprocess, sys, tempfile, textwrap, wave
import numpy as np
from .analysis import fmt_t, hav
from . import knowledge as K, texts

SR = 24000
VOICES = {'tr': 'tr-TR-AhmetNeural', 'en': 'en-US-GuyNeural', 'ar': 'ar-SA-HamedNeural'}
CULT = {'tr': 'tr', 'en': 'en', 'ar': 'ar'}
LBL = {'alt': ('İrtifa', 'Altitude', 'الارتفاع'), 'spd': ('Yer hızı', 'Ground speed', 'السرعة الأرضية'), 'roll': ('Yatış', 'Roll', 'الدوران'),
       'pitch': ('Yunuslama', 'Pitch', 'الميلان'), 'mode': ('Mod', 'Mode', 'الوضع'), 'time': ('Zaman', 'Time', 'الزمن'),
       'verdict': ('Karar', 'Verdict', 'القرار'), 'cause': ('Kök neden', 'Root cause', 'السبب الجذري'),
       'title': ('3B Uçuş Tekrarı — Ders', '3D Flight Replay — Lesson', 'إعادة الرحلة ثلاثية الأبعاد — درس'),
       'step': ('Adım', 'Step', 'الخطوة'), 'end': ('Ders sonu', 'End of lesson', 'نهاية الدرس')}
LI = {'tr': 0, 'en': 1, 'ar': 2}


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which('ffmpeg')


def _L(k, lg): return LBL[k][LI.get(lg, 0)]


def track3d(A, maxn=6000):
    tr = A.track
    if tr is None or len(tr['t']) < 5: return None
    n = len(tr['t']); step = max(1, n // maxn)
    t_ = np.asarray(tr['t'][::step], float); lat = np.asarray(tr['lat'][::step], float); lon = np.asarray(tr['lon'][::step], float)
    alt = np.asarray(tr['rel'][::step], float)
    x = hav(lat[0], lon[0], lat[0], lon) * np.sign(lon - lon[0]); y = hav(lat[0], lon[0], lat, lon[0]) * np.sign(lat - lat[0])
    att = A.L.s('ATT'); gps = A.L.s('GPS')
    return {'t': t_, 'x': x, 'y': y, 'z': alt,
            'roll': np.interp(t_, att['t'], att['Roll']) if att.has('Roll') else np.zeros_like(t_),
            'pitch': np.interp(t_, att['t'], att['Pitch']) if att.has('Pitch') else np.zeros_like(t_),
            'gs': np.interp(t_, gps['t'], gps['Spd']) if gps.has('Spd') else np.zeros_like(t_)}


# ------------------------------------------------------------------ ses
def _read_wav(p):
    with wave.open(p, 'rb') as w:
        n = w.getnframes(); sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
        b = w.readframes(n)
    a = np.frombuffer(b, dtype=np.int16 if sw == 2 else np.uint8).astype(np.float32)
    if sw == 1: a = (a - 128) * 256
    if ch > 1: a = a.reshape(-1, ch).mean(1)
    if sr != SR and len(a):
        a = np.interp(np.linspace(0, len(a) - 1, int(len(a) * SR / sr)), np.arange(len(a)), a)
    return a


def _tts_online(text, lang, out_wav, ff):
    import asyncio, edge_tts
    mp3 = out_wav + '.mp3'

    async def go():
        await edge_tts.Communicate(text, VOICES.get(lang, VOICES['en'])).save(mp3)
    asyncio.run(go())
    subprocess.run([ff, '-y', '-loglevel', 'error', '-i', mp3, '-ac', '1', '-ar', str(SR), out_wav], check=True, **_noconsole())
    return out_wav


def _tts_offline(text, lang, out_wav):
    if os.name != 'nt': raise RuntimeError('offline voice: Windows only')
    txt = out_wav + '.txt'
    open(txt, 'w', encoding='utf-8').write(text)
    ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$v=$s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Culture.Name -like '{CULT.get(lang, 'en')}*' }} | Select-Object -First 1; "
          "if (-not $v) { exit 3 }; $s.SelectVoice($v.VoiceInfo.Name); $s.Rate=0; "
          f"$s.SetOutputToWaveFile('{out_wav}'); $s.Speak([IO.File]::ReadAllText('{txt}', [Text.Encoding]::UTF8)); $s.Dispose()")
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps], capture_output=True, timeout=120, **_noconsole())
    if r.returncode != 0 or not os.path.exists(out_wav): raise RuntimeError(f'no {lang} voice installed')
    return out_wav


def _noconsole():
    if os.name == 'nt':
        return {'creationflags': 0x08000000}
    return {}


def narrate(text, lang, out_wav, voice, ff):
    """Döner: numpy ses dizisi ya da None."""
    if voice == 'none': return None
    if voice in ('auto', 'online'):
        try: return _read_wav(_tts_online(text, lang, out_wav, ff))
        except Exception:
            if voice == 'online': return None
    try: return _read_wav(_tts_offline(text, lang, out_wav))
    except Exception: return None


# ------------------------------------------------------------------ zaman çizelgesi
def plan(tr, steps, durs, target_s, intro=4.0, outro=5.0):
    """Video segmentleri: (v0, v1, f0, f1, adım_indeksi) — adım: -1 giriş kartı, -2 bitiş kartı, None hızlı geçiş."""
    t0, t1 = float(tr['t'][0]), float(tr['t'][-1])
    dwell = [max(5.0, (d or 0) + 1.6) for d in durs]
    pts = [min(max(s['t'], t0), t1) for s in steps]

    def build(speed):
        seg = [(0.0, intro, t0, t0, -1)]; v = intro; cur = t0
        for i, p in enumerate(pts):
            a = max(cur, p - 2.0)
            if a > cur:
                dv = (a - cur) / speed; seg.append((v, v + dv, cur, a, None)); v += dv; cur = a
            b = min(t1, cur + dwell[i] * 0.5)
            seg.append((v, v + dwell[i], cur, b, i)); v += dwell[i]; cur = b
        if t1 > cur:
            dv = (t1 - cur) / speed; seg.append((v, v + dv, cur, t1, None)); v += dv
        seg.append((v, v + outro, t1, t1, -2))
        return seg, v + outro
    seg, _ = build(1.0)
    transit = sum(f1 - f0 for _, _, f0, f1, si in seg if si is None)
    budget = max(15.0, target_s - intro - outro - sum(dwell))
    return build(max(1.0, transit / budget))


def _wrap(s, lg, width):
    from .charts import mshape as shape
    lines = textwrap.wrap(s, width) or ['']
    return '\n'.join(shape(x, lg) for x in lines[:3])


def export(A, path, lang='tr', target_s=180, voice='auto', size=(1280, 720), fps=20, org='', progress=None, cancel=None):
    from . import lessons
    from .charts import mshape as shape
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    lg = lang
    tr = track3d(A)
    if tr is None: raise RuntimeError('no track')
    ff = ffmpeg_exe()
    if not ff: raise RuntimeError('ffmpeg not found')
    steps = lessons.build(A, lg, max_steps=12)
    work = tempfile.mkdtemp(prefix='pxvid_')
    # 1) anlatım sesleri
    audio = []
    for i, s in enumerate(steps):
        if cancel and cancel(): raise RuntimeError('cancelled')
        audio.append(narrate(f"{s['title']}. {s['text']}", lg, os.path.join(work, f's{i}.wav'), voice, ff))
        if progress: progress(0.12 * (i + 1) / max(1, len(steps)))
    durs = [len(a) / SR if a is not None else 0.0 for a in audio]
    seg, total = plan(tr, steps, durs, target_s)
    nfr = int(total * fps)
    # 2) ses izi
    has_audio = any(a is not None for a in audio)
    wav = None
    if has_audio:
        buf = np.zeros(int((total + 1) * SR), np.float32)
        for v0, v1, f0, f1, si in seg:
            if si is not None and si >= 0 and audio[si] is not None:
                a = audio[si]; o = int((v0 + 0.6) * SR); buf[o:o + len(a)] += a[:max(0, len(buf) - o)]
        buf = np.clip(buf, -32767, 32767).astype(np.int16)
        wav = os.path.join(work, 'narration.wav')
        with wave.open(wav, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(buf.tobytes())
    # 3) altyazı dosyası
    srt = os.path.splitext(path)[0] + '.srt'

    def ts(x):
        h, r = divmod(x, 3600); m, s_ = divmod(r, 60); return f'{int(h):02d}:{int(m):02d}:{int(s_):02d},{int((s_ % 1) * 1000):03d}'
    with open(srt, 'w', encoding='utf-8') as f:
        n = 0
        for v0, v1, f0, f1, si in seg:
            if si is not None and si >= 0:
                n += 1; s = steps[si]
                f.write(f"{n}\n{ts(v0)} --> {ts(v1)}\n{s['time']} · {s['title']}\n{s['text']}\n\n")
    # 4) çizim
    W, H = size; dpi = 100
    fig = Figure(figsize=(W / dpi, H / dpi), dpi=dpi, facecolor='#0B1222'); cv = FigureCanvasAgg(fig)
    ax = fig.add_axes([0.0, 0.17, 0.64, 0.75], projection='3d'); ax.set_facecolor('#0B1222')
    for a_ in (ax.xaxis, ax.yaxis, ax.zaxis):
        a_.set_pane_color((0.07, 0.1, 0.18, 1)); a_.label.set_color('#CBD5E1')
    ax.tick_params(colors='#94A3B8', labelsize=7)
    x, y, z = tr['x'], tr['y'], tr['z']
    ax.plot(x, y, np.zeros_like(z), color='#334155', lw=0.8); ax.plot(x, y, z, color='#3B82F6', lw=1.0, alpha=0.55)
    ax.scatter([0], [0], [0], color='#16A34A', s=40, marker='^')
    if A.verdict.get('kind') == 'crash': ax.scatter([x[-1]], [y[-1]], [z[-1]], color='#DC2626', s=70, marker='X')
    ax.set_xlabel('E (m)', fontsize=8); ax.set_ylabel('N (m)', fontsize=8); ax.set_zlabel('Alt (m)', fontsize=8)
    pt = ax.plot([x[0]], [y[0]], [z[0]], 'o', color='#F59E0B', ms=10)[0]
    stem = ax.plot([x[0]] * 2, [y[0]] * 2, [0, z[0]], color='#F59E0B', lw=0.8, ls=':')[0]
    trail = ax.plot([], [], [], color='#F59E0B', lw=2.4)[0]
    a2 = fig.add_axes([0.69, 0.58, 0.29, 0.30], facecolor='#0F1A30')
    a2.plot(tr['t'], z, color='#60A5FA', lw=1); a2.tick_params(colors='#94A3B8', labelsize=7)
    for sp in a2.spines.values(): sp.set_color('#334155')
    a2.set_title(shape(_L('alt', lg) + ' (m)', lg), color='#CBD5E1', fontsize=9)
    a2.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt_t(v)))
    cur = a2.axvline(tr['t'][0], color='#F59E0B', lw=1.2)
    hud = fig.text(0.70, 0.52, '', color='#E2E8F0', fontsize=11, va='top', family='DejaVu Sans', linespacing=1.6)
    title = fig.text(0.015, 0.965, shape(_L('title', lg) + (' · ' + org if org else ''), lg), color='#F8FAFC', fontsize=14, weight='bold', va='top')
    sub = fig.text(0.015, 0.925, shape(os.path.basename(A.L.path) + ' · ' + texts.T('v_' + A.verdict.get('kind', 'normal'), lg), lg), color='#94A3B8', fontsize=9.5, va='top')
    band = fig.add_axes([0.0, 0.0, 1.0, 0.165]); band.axis('off'); band.set_facecolor('#000000')
    band.add_patch(matplotlib.patches.Rectangle((0, 0), 1, 1, color='#020617', alpha=0.92, transform=band.transAxes))
    cap_t = band.text(0.5, 0.80, '', color='#FBBF24', fontsize=15, weight='bold', ha='center', va='center', transform=band.transAxes)
    cap = band.text(0.5, 0.38, '', color='#F8FAFC', fontsize=12.5, ha='center', va='center', transform=band.transAxes, linespacing=1.35)
    card = fig.text(0.5, 0.55, '', color='#F8FAFC', fontsize=22, ha='center', va='center', weight='bold', linespacing=1.6,
                    bbox=dict(boxstyle='round,pad=1.0', fc='#1E3A8A', ec='#3B82F6', alpha=0.95))
    pad = max(5.0, float(np.nanmax(np.abs(np.r_[x, y]))) * 0.05)
    ax.set_xlim(np.nanmin(x) - pad, np.nanmax(x) + pad); ax.set_ylim(np.nanmin(y) - pad, np.nanmax(y) + pad); ax.set_zlim(0, max(10.0, float(np.nanmax(z)) * 1.1))
    modes = A.L.modes
    cause = (A.root or {}).get('cause')
    end_txt = '\n'.join([_L('end', lg), f"{_L('verdict', lg)}: {texts.T('v_' + A.verdict.get('kind', 'normal'), lg)}"] +
                        ([f"{_L('cause', lg)}: {texts.T('cause_' + cause, lg)}"] if cause else []))
    cmd = [ff, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-']
    if wav: cmd += ['-i', wav]
    cmd += ['-i', srt, '-map', '0:v'] + (['-map', '1:a'] if wav else []) + ['-map', f'{2 if wav else 1}:s',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', '-c:s', 'mov_text',
            '-metadata:s:s:0', f'language={ {"tr": "tur", "en": "eng", "ar": "ara"}[lg] }']
    if wav: cmd += ['-c:a', 'aac', '-b:a', '128k']
    cmd += ['-movflags', '+faststart', path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, **_noconsole())
    si_cur = None
    try:
        for fi in range(nfr):
            if cancel and cancel(): raise RuntimeError('cancelled')
            vt = fi / fps
            sg = next((s for s in seg if s[0] <= vt < s[1]), seg[-1])
            v0, v1, f0, f1, si = sg
            ft = f0 + (f1 - f0) * (vt - v0) / max(1e-6, v1 - v0)
            i = int(np.clip(np.searchsorted(tr['t'], ft), 0, len(tr['t']) - 1))
            pt.set_data_3d([x[i]], [y[i]], [z[i]]); stem.set_data_3d([x[i]] * 2, [y[i]] * 2, [0, z[i]])
            k0 = max(0, i - 80); trail.set_data_3d(x[k0:i + 1], y[k0:i + 1], z[k0:i + 1])
            ax.view_init(elev=24, azim=-60 + 40 * np.sin(vt / 25.0))
            cur.set_xdata([ft, ft])
            m = '-'
            for mt, n_, _, _ in modes:
                if mt <= ft: m = K.mode_name(A.vehicle, n_)
            hud.set_text('\n'.join(shape(s, lg) for s in (
                f"{_L('time', lg)}: {fmt_t(ft)}", f"{_L('alt', lg)}: {z[i]:.1f} m", f"{_L('spd', lg)}: {tr['gs'][i]:.1f} m/s",
                f"{_L('roll', lg)}: {tr['roll'][i]:.0f}°   {_L('pitch', lg)}: {tr['pitch'][i]:.0f}°", f"{_L('mode', lg)}: {m}")))
            if si != si_cur:
                si_cur = si
                if si == -1:
                    card.set_text(shape(_L('title', lg), lg) + '\n' + shape(os.path.basename(A.L.path), lg)); card.set_visible(True); cap_t.set_text(''); cap.set_text('')
                elif si == -2:
                    card.set_text('\n'.join(shape(s, lg) for s in end_txt.split('\n'))); card.set_visible(True); cap_t.set_text(''); cap.set_text('')
                elif si is not None:
                    st = steps[si]; card.set_visible(False); cap_t.set_color('#FBBF24'); cap.set_color('#F8FAFC')
                    cap_t.set_text(shape(f"{_L('step', lg)} {si + 1}/{len(steps)} · {st['time']} · {st['title']}", lg))
                    cap.set_text(_wrap(st['text'], lg, 120))
                else:   # hızlı geçiş: son adımın altyazısı soluk kalır
                    card.set_visible(False); cap_t.set_color('#64748B'); cap.set_color('#64748B')
            cv.draw()
            proc.stdin.write(bytes(cv.buffer_rgba()))
            if progress and fi % 10 == 0: progress(0.12 + 0.86 * fi / max(1, nfr))
        proc.stdin.close()
        err = proc.stderr.read().decode('utf-8', 'replace'); rc = proc.wait()
        if rc != 0: raise RuntimeError('ffmpeg: ' + err[-400:])
    except Exception:
        try: proc.kill()
        except Exception: pass
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if progress: progress(1.0)
    return {'path': path, 'srt': srt, 'seconds': round(total, 1), 'steps': len(steps), 'audio': has_audio}
