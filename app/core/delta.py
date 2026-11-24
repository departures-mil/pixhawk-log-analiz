"""Yalnızca değişen kısımlar (delta / yama) güncellemesi.

Yama dosyası (patch-from-X.Y.Z*.zip) bir ZIP'tir:
  patch.json  → {"format":1,"from":"1.0.5","to":"1.0.6","kind":"tree"|"file",
                 "manifest": {yol: [boyut, sha256]}   # hedef sürümün TAM listesi
                 "files": [{"p":yol,"op":"diff"|"add","old":sha256,"sha":sha256,"size":n,"e":"f/0"}],
                 "delete": [yol, ...]}
  f/N         → bsdiff4 farkı (op=diff) ya da dosyanın kendisi (op=add)

Uygulama: değişen dosyalar geçici bir klasörde üretilir, her biri SHA-256 ile
doğrulanır; değişmeyen dosyaların da kurulu hâlleri hedef listeyle karşılaştırılır.
Tek bir uyumsuzlukta DeltaError atılır → güncelleyici tam dosyaya geçer.
Aynı kod CI'da yamayı üretip eski klasöre uygulayarak tam sürümle birebir aynı
olduğunu doğrulamak için de kullanılır (tools_ci/make_patches.py).
"""
from __future__ import annotations
import hashlib, json, os, shutil, zipfile

FORMAT = 1
MAX_RATIO = 0.70          # yama tam dosyanın %70'inden büyükse yayınlanmaz
BSDIFF_MAX = 400 * 1024 * 1024   # bundan büyük dosyalarda fark yerine dosyanın kendisi
SKIP = ('unins',)          # Inno Setup kaldırıcı dosyaları (kuruluma özgü) karşılaştırılmaz


class DeltaError(Exception):
    pass


def sha256_file(p, bufsize=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(bufsize)
            if not b: break
            h.update(b)
    return h.hexdigest()


def _skip(rel):
    base = rel.rsplit('/', 1)[-1].lower()
    return '/' not in rel and base.startswith(SKIP)


def manifest(root):
    """{posix_yol: [boyut, sha256]} — kaldırıcı dosyaları hariç."""
    out = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root).replace(os.sep, '/')
            if _skip(rel): continue
            out[rel] = [os.path.getsize(full), sha256_file(full)]
    return out


def _bsdiff():
    import bsdiff4
    return bsdiff4


# ------------------------------------------------------------------ üretim
def make_patch(old_root, new_root, out_zip, v_from, v_to, kind='tree', files=None, log=print):
    """Eski → yeni yama üretir. kind='file' ise yalnız `files` listesindeki yollar (taşınabilir exe).
    Döner: {'size', 'changed', 'added', 'deleted', 'unchanged'}"""
    if kind == 'file':
        om = {p: [os.path.getsize(os.path.join(old_root, p)), sha256_file(os.path.join(old_root, p))] for p in files}
        nm = {p: [os.path.getsize(os.path.join(new_root, p)), sha256_file(os.path.join(new_root, p))] for p in files}
    else:
        om, nm = manifest(old_root), manifest(new_root)
    entries, st = [], {'changed': 0, 'added': 0, 'deleted': 0, 'unchanged': 0}
    tmp = out_zip + '.tmp'
    with zipfile.ZipFile(tmp, 'w', allowZip64=True) as z:
        for i, (p, (size, sha)) in enumerate(sorted(nm.items())):
            if p in om and om[p][1] == sha:
                st['unchanged'] += 1; continue
            new_b = open(os.path.join(new_root, p), 'rb').read()
            e = {'p': p, 'sha': sha, 'size': size, 'e': f'f/{i}'}
            payload = None
            if p in om and size <= BSDIFF_MAX and om[p][0] <= BSDIFF_MAX:
                old_b = open(os.path.join(old_root, p), 'rb').read()
                d = _bsdiff().diff(old_b, new_b)
                if len(d) < len(new_b) * 0.9:
                    payload = d; e['op'] = 'diff'; e['old'] = om[p][1]
                    z.writestr(zipfile.ZipInfo(e['e']), d, compress_type=zipfile.ZIP_STORED)
            if payload is None:
                e['op'] = 'add'
                z.writestr(zipfile.ZipInfo(e['e']), new_b, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            st['changed' if p in om else 'added'] += 1
            entries.append(e)
        dele = sorted(p for p in om if p not in nm) if kind == 'tree' else []
        st['deleted'] = len(dele)
        meta = {'format': FORMAT, 'from': v_from, 'to': v_to, 'kind': kind, 'manifest': nm,
                'files': entries, 'delete': dele}
        z.writestr('patch.json', json.dumps(meta, separators=(',', ':')), compress_type=zipfile.ZIP_DEFLATED)
    os.replace(tmp, out_zip)
    st['size'] = os.path.getsize(out_zip)
    return st


# --------------------------------------------------------------- uygulama
def read_meta(patch_zip):
    with zipfile.ZipFile(patch_zip) as z:
        m = json.loads(z.read('patch.json'))
    if m.get('format') != FORMAT:
        raise DeltaError('patch format')
    return m


def stage(base_root, patch_zip, stage_root, expect_from=None, expect_to=None, progress=None):
    """Değişen dosyaları stage_root altına üretir ve HER ŞEYİ SHA-256 ile doğrular.
    base_root'a dokunmaz. Döner: meta (delete listesiyle)."""
    m = read_meta(patch_zip)
    if expect_from and m['from'] != expect_from: raise DeltaError(f"from {m['from']} != {expect_from}")
    if expect_to and m['to'] != expect_to: raise DeltaError(f"to {m['to']} != {expect_to}")
    changed = {e['p'] for e in m['files']}
    # 1) değişmeyecek dosyalar kurulu hâlleriyle hedefte aynı olmalı
    keep = [p for p in m['manifest'] if p not in changed]
    total = len(keep) + len(m['files']); done = 0
    for p in keep:
        full = os.path.join(base_root, *p.split('/'))
        size, sha = m['manifest'][p]
        if not os.path.isfile(full) or os.path.getsize(full) != size or sha256_file(full) != sha:
            raise DeltaError(f'local file differs: {p}')
        done += 1
        if progress and done % 50 == 0: progress(done, total)
    # 2) değişen/yeni dosyaları üret ve doğrula
    if os.path.isdir(stage_root): shutil.rmtree(stage_root, ignore_errors=True)
    os.makedirs(stage_root, exist_ok=True)
    with zipfile.ZipFile(patch_zip) as z:
        for e in m['files']:
            data = z.read(e['e'])
            if e['op'] == 'diff':
                full = os.path.join(base_root, *e['p'].split('/'))
                if not os.path.isfile(full) or sha256_file(full) != e['old']:
                    raise DeltaError(f"base mismatch: {e['p']}")
                with open(full, 'rb') as f:
                    data = _bsdiff().patch(f.read(), data)
            if len(data) != e['size'] or hashlib.sha256(data).hexdigest() != e['sha']:
                raise DeltaError(f"sha256 mismatch: {e['p']}")
            dst = os.path.join(stage_root, *e['p'].split('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f: f.write(data)
            done += 1
            if progress: progress(done, total)
    return m


def apply_inplace(base_root, stage_root, meta):
    """(CI/test) Hazırlanan dosyaları base_root'a kopyalar, silinecekleri siler."""
    for e in meta['files']:
        src = os.path.join(stage_root, *e['p'].split('/')); dst = os.path.join(base_root, *e['p'].split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(src, dst)
    for p in meta.get('delete', []):
        f = os.path.join(base_root, *p.split('/'))
        if os.path.isfile(f): os.remove(f)


def verify_tree(root, target_manifest, kind='tree'):
    """Klasör hedef listeyle birebir aynı mı? (kind='tree' ise fazla dosya da hata)"""
    got = manifest(root) if kind == 'tree' else {p: [os.path.getsize(os.path.join(root, p)), sha256_file(os.path.join(root, p))] for p in target_manifest}
    if got != target_manifest:
        miss = [p for p in target_manifest if got.get(p) != target_manifest[p]][:5]
        extra = [p for p in got if p not in target_manifest][:5]
        raise DeltaError(f'tree mismatch missing/diff={miss} extra={extra}')
    return True
