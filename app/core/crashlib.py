"""Gerçek kaza logları kütüphanesi (discuss.ardupilot.org'dan derlenen test seti) — liste, indirme."""
from __future__ import annotations
import io, json, os, re, urllib.request, zipfile
from .paths import res, data_dir


def load():
    try:
        d = json.load(open(res('data', 'crashlib.json'), encoding='utf-8'))
    except Exception:
        return {'score': None, 'cases': []}
    if isinstance(d, list): d = {'score': None, 'cases': d}
    return d


def direct(u):
    m = re.search(r'drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([A-Za-z0-9_-]{20,})', u)
    if m: return f'https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t'
    if 'dropbox.com' in u:
        u = re.sub(r'([?&])dl=0', r'\1dl=1', u)
        if 'dl=1' not in u: u += ('&' if '?' in u else '?') + 'dl=1'
    return u


def download(case, progress=None):
    """Logu indirir (önbellekli) ve yerel .bin yolunu döndürür."""
    d = os.path.join(data_dir(), 'crashlib'); os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, f"{case['id']}.bin")
    if os.path.exists(dst) and os.path.getsize(dst) > 1000: return dst
    req = urllib.request.Request(direct(case['log_url']), headers={'User-Agent': 'Mozilla/5.0 PixhawkLogAnaliz'})
    buf = io.BytesIO()
    with urllib.request.urlopen(req, timeout=60) as r:
        while True:
            b = r.read(1 << 18)
            if not b: break
            buf.write(b)
            if progress: progress(buf.tell() / 1e6)
    b = buf.getvalue()
    if b[:2] == b'PK':
        z = zipfile.ZipFile(io.BytesIO(b))
        names = sorted((n for n in z.namelist() if n.lower().endswith('.bin')), key=lambda n: -z.getinfo(n).file_size)
        if not names: raise RuntimeError('zip: no .bin')
        b = z.read(names[0])
    if b[:2] != b'\xa3\x95': raise RuntimeError('not a DataFlash .bin log')
    open(dst, 'wb').write(b)
    return dst
