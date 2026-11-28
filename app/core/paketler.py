"""Çevrimdışı paketler: NLLB-200 çeviri modelleri ve Tesseract OCR (tessdata_best: Türkçe, İngilizce, Arapça).

Paketler GitHub Actions'ta (.github/workflows/packs.yml) üretilip bu deponun 'packs' ön sürümüne yüklenir; program
packs.json bildirimini okur, dosyaları parça parça (kaldığı yerden devam ederek) indirir, her parçayı SHA-256 ile doğrular
ve birleştirir. Konum: %LOCALAPPDATA%\\PixhawkLogAnaliz\\packs (dolaşım profiline girmez, kurulum klasörüne yazılmaz).
"""
from __future__ import annotations
import hashlib, json, os, shutil, time, urllib.request, zipfile

REPO = 'departures-mil/pixhawk-log-analiz'
MANIFEST_URL = f'https://github.com/{REPO}/releases/download/packs/packs.json'
PACKS = {
    'nllb-3.3b': {'name': 'NLLB-200 3.3B', 'kind': 'mt', 'approx_mb': 3400, 'best': True},
    'nllb-1.3b': {'name': 'NLLB-200 1.3B', 'kind': 'mt', 'approx_mb': 1400},
    'ocr': {'name': 'Tesseract OCR (tessdata_best)', 'kind': 'ocr', 'approx_mb': 120, 'best': True},
}
MT_ORDER = ('nllb-3.3b', 'nllb-1.3b')
_MAN = {'t': 0, 'd': None}


def base_dir():
    b = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA') or os.path.join(os.path.expanduser('~'), '.local', 'share')
    d = os.environ.get('PX_PACKS_DIR') or os.path.join(b, 'PixhawkLogAnaliz', 'packs')
    os.makedirs(d, exist_ok=True)
    return d


def pack_dir(pid):
    return os.path.join(base_dir(), pid)


def installed(pid):
    d = pack_dir(pid)
    return d if os.path.isfile(os.path.join(d, '.ok')) else None


def info(pid):
    d = installed(pid)
    if not d: return None
    try:
        return json.load(open(os.path.join(d, '.ok'), encoding='utf-8'))
    except Exception:
        return {}


def nllb_dir(pref=None):
    for pid in ([pref] if pref in MT_ORDER else []) + list(MT_ORDER):
        d = installed(pid)
        if d: return d
    return None


def nllb_id(d):
    return os.path.basename(os.path.normpath(d)) if os.path.basename(os.path.normpath(d)) in PACKS else 'nllb-3.3b'


def tesseract_exe():
    d = installed('ocr')
    if not d: return None
    for root, _, files in os.walk(d):
        for f in files:
            if f.lower() in ('tesseract.exe', 'tesseract'): return os.path.join(root, f)
    return None


def tessdata_dir():
    exe = tesseract_exe()
    if not exe: return None
    for c in (os.path.join(os.path.dirname(exe), 'tessdata'), os.path.join(installed('ocr'), 'tessdata')):
        if os.path.isdir(c): return c
    return None


def size_on_disk(pid):
    d = installed(pid)
    if not d: return 0
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs)


def remove(pid):
    shutil.rmtree(pack_dir(pid), ignore_errors=True)
    shutil.rmtree(pack_dir(pid) + '.part', ignore_errors=True)


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'PixhawkLogAnaliz'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def manifest(force=False, url=None):
    if not force and _MAN['d'] and time.time() - _MAN['t'] < 600: return _MAN['d']
    d = json.loads(_get(url or os.environ.get('PX_PACKS_URL') or MANIFEST_URL).decode('utf-8'))
    _MAN.update(t=time.time(), d=d)
    return d


def total_size(entry):
    return sum(sum(p['size'] for p in f['parts']) if f.get('parts') else f['size'] for f in entry['files'])


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


class Cancelled(Exception):
    pass


def _download(url, dst, size, sha, prog, cancel):
    """Kaldığı yerden devam (HTTP Range). prog(eklenen_bayt)."""
    have = os.path.getsize(dst) if os.path.exists(dst) else 0
    if have == size and (not sha or _sha(dst) == sha):
        prog(size); return
    if have > size: os.remove(dst); have = 0
    prog(have)
    for attempt in range(6):
        try:
            hdr = {'User-Agent': 'PixhawkLogAnaliz'}
            if have: hdr['Range'] = f'bytes={have}-'
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=60) as r:
                if have and r.status != 206: have = 0   # sunucu devamı desteklemiyor
                with open(dst, 'ab' if have else 'wb') as f:
                    while True:
                        if cancel and cancel(): raise Cancelled()
                        b = r.read(1 << 18)
                        if not b: break
                        f.write(b); have += len(b); prog(len(b))
            break
        except Cancelled:
            raise
        except Exception:
            if attempt == 5: raise
            time.sleep((2, 4, 8, 15, 30)[attempt])
            have = os.path.getsize(dst) if os.path.exists(dst) else 0
    if sha and _sha(dst) != sha:
        os.remove(dst)
        raise RuntimeError('SHA-256 mismatch: ' + os.path.basename(dst))


def download(pid, on_progress=None, cancel=None, man=None):
    """Paketi indir + doğrula + kur. on_progress(done_bytes, total_bytes). Kurulu klasörü döner."""
    m = (man or manifest())['packs'][pid]
    total = total_size(m)
    tmp = pack_dir(pid) + '.part'; os.makedirs(tmp, exist_ok=True)
    st = {'done': 0}

    def prog(n):
        st['done'] += n
        if on_progress: on_progress(min(st['done'], total), total)
    for f in m['files']:
        out = os.path.join(tmp, f['path']); os.makedirs(os.path.dirname(out), exist_ok=True)
        if f.get('parts'):
            pfs = []
            for i, p in enumerate(f['parts']):
                pf = out + f'.p{i:02d}'
                base = st['done']
                _download(p['url'], pf, p['size'], p.get('sha256'), prog, cancel)
                st['done'] = base + p['size']; pfs.append(pf)
            with open(out + '.join', 'wb') as w:
                for pf in pfs:
                    with open(pf, 'rb') as r: shutil.copyfileobj(r, w, 1 << 22)
            if f.get('sha256') and _sha(out + '.join') != f['sha256']:
                raise RuntimeError('SHA-256 mismatch: ' + f['path'])
            os.replace(out + '.join', out)
            for pf in pfs: os.remove(pf)
        elif not (os.path.exists(out) and f.get('sha256') and os.path.getsize(out) == f['size'] and _sha(out) == f['sha256']):
            base = st['done']
            _download(f['url'], out + '.dl', f['size'], f.get('sha256'), prog, cancel)
            os.replace(out + '.dl', out); st['done'] = base + f['size']
        else:
            prog(f['size'])
        if f.get('unzip'):
            with zipfile.ZipFile(out) as z: z.extractall(tmp)
            os.remove(out)
    with open(os.path.join(tmp, '.ok'), 'w', encoding='utf-8') as w:
        json.dump({'id': pid, 'version': m.get('version', ''), 'ts': time.time(), 'size': total}, w)
    final = pack_dir(pid)
    shutil.rmtree(final, ignore_errors=True)
    os.replace(tmp, final)
    return final
