"""CI: son 5 sürümün her biri için 'yalnızca değişen kısımlar' yamalarını üretir ve doğrular.

Her eski sürüm X için:
  patch-from-X.zip           → Setup ile kurulu klasör (eski Setup sessizce geçici klasöre kurulur)
  patch-from-X-portable.zip  → taşınabilir tek exe
Yama, eski dosyalara CI içinde uygulanır; sonuç yeni sürümle SHA-256 düzeyinde birebir aynı
değilse ya da yama tam dosyanın %70'inden büyükse yayınlanmaz. Hiçbir hata derlemeyi durdurmaz;
o yama atlanır ve program tam dosyaya geçer.

Kullanım: python tools_ci/make_patches.py --version 1.0.6 --new-dir dist/PixhawkLogAnaliz
          --new-portable dist/PixhawkLogAnaliz.exe --setup dist/PixhawkLogAnaliz_Setup_1.0.6.exe --out dist/patches
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time, traceback, urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core import delta  # noqa: E402

REPO = os.environ.get('GITHUB_REPOSITORY', 'departures-mil/pixhawk-log-analiz')
APPID_KEY = r'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{8C3F7B2E-5A1D-4E7B-9C2F-6D1A0B4E3F21}_is1'


def _v(s):
    try: return tuple(int(x) for x in s.lstrip('v').split('.'))
    except Exception: return None


def api(path):
    h = {'User-Agent': 'make-patches', 'Accept': 'application/vnd.github+json'}
    tok = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if tok: h['Authorization'] = f'Bearer {tok}'
    with urllib.request.urlopen(urllib.request.Request(f'https://api.github.com/{path}', headers=h), timeout=60) as r:
        return json.load(r)


def fetch(url, dst):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'make-patches'}), timeout=120) as r, open(dst, 'wb') as f:
                shutil.copyfileobj(r, f, 1 << 20)
            return dst
        except Exception:
            if i == 3: raise
            time.sleep(3 * (i + 1))


def previous(cur, keep):
    rels = [r for r in api(f'repos/{REPO}/releases?per_page=50') if not r['draft'] and not r['prerelease']]
    out = []
    for r in rels:
        v = _v(r['tag_name'])
        if v and len(v) == 3 and v < _v(cur): out.append((v, r))
    out.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in out[:keep]]


def install_old(setup, d):
    if os.path.isdir(d): shutil.rmtree(d, ignore_errors=True)
    subprocess.run([setup, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/NOICONS', '/TASKS=',
                    '/CURRENTUSER', f'/DIR={d}'], check=False, timeout=900)
    # Kayıt defterindeki kurulum kaydını sil: bir sonraki eski sürüm /DIR'i yok saymasın.
    subprocess.run(['reg', 'delete', APPID_KEY, '/f'], check=False, capture_output=True)
    if not os.path.isfile(os.path.join(d, 'PixhawkLogAnaliz.exe')):
        raise RuntimeError('old setup did not install')


def build_one(old_root, new_root, out, frm, to, kind, files, full_size):
    st = delta.make_patch(old_root, new_root, out, frm, to, kind=kind, files=files)
    ratio = st['size'] / max(full_size, 1)
    if ratio > delta.MAX_RATIO:
        os.remove(out); return None, f'{ratio:.0%} > %70, yayınlanmadı'
    # Doğrulama: eski dosyaların kopyasına uygula → yeni sürümle birebir aynı mı?
    work = tempfile.mkdtemp(prefix='verify_')
    try:
        base = os.path.join(work, 'base'); stg = os.path.join(work, 'stage')
        if kind == 'tree':
            shutil.copytree(old_root, base)
        else:
            os.makedirs(base)
            for p in files: shutil.copyfile(os.path.join(old_root, p), os.path.join(base, p))
        meta = delta.stage(base, out, stg, expect_from=frm, expect_to=to)
        delta.apply_inplace(base, stg, meta)
        delta.verify_tree(base, delta.manifest(new_root) if kind == 'tree' else meta['manifest'], kind)
        if kind == 'file':
            for p in files:
                if delta.sha256_file(os.path.join(base, p)) != delta.sha256_file(os.path.join(new_root, p)):
                    raise delta.DeltaError('file mismatch ' + p)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    st['ratio'] = round(ratio, 4)
    return st, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', required=True); ap.add_argument('--new-dir', required=True)
    ap.add_argument('--new-portable', required=True); ap.add_argument('--setup', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--keep', type=int, default=5)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    work = tempfile.mkdtemp(prefix='patches_')
    idx = {'format': delta.FORMAT, 'version': a.version, 'max_ratio': delta.MAX_RATIO,
           'setup': {'name': os.path.basename(a.setup), 'size': os.path.getsize(a.setup), 'sha256': delta.sha256_file(a.setup)},
           'portable': {'name': 'PixhawkLogAnaliz.exe', 'size': os.path.getsize(a.new_portable), 'sha256': delta.sha256_file(a.new_portable)},
           'patches': {}, 'log': []}
    newp = os.path.join(work, 'newp'); os.makedirs(newp); shutil.copyfile(a.new_portable, os.path.join(newp, 'PixhawkLogAnaliz.exe'))
    try:
        olds = previous(a.version, a.keep)
    except Exception as e:
        olds = []; idx['log'].append(f'release list failed: {e}')
    for r in olds:
        frm = r['tag_name'].lstrip('v'); ent = {}
        assets = {x['name']: x['browser_download_url'] for x in r.get('assets', [])}
        # 1) Setup ile kurulu klasör
        sname = next((n for n in assets if 'setup' in n.lower() and n.lower().endswith('.exe')), None)
        if sname:
            t0 = time.time()
            try:
                s = fetch(assets[sname], os.path.join(work, sname))
                od = os.path.join(work, 'old_' + frm); install_old(s, od)
                out = os.path.join(a.out, f'patch-from-{frm}.zip')
                st, msg = build_one(od, a.new_dir, out, frm, a.version, 'tree', None, idx['setup']['size'])
                if st:
                    ent['tree'] = {'name': os.path.basename(out), 'size': st['size'], 'sha256': delta.sha256_file(out),
                                   'ratio': st['ratio'], 'changed': st['changed'], 'added': st['added'], 'deleted': st['deleted']}
                idx['log'].append(f'{frm} tree: {msg} ({time.time() - t0:.0f}s) {st or ""}')
                shutil.rmtree(od, ignore_errors=True); os.remove(s)
            except Exception as e:
                idx['log'].append(f'{frm} tree FAILED: {e}'); traceback.print_exc()
        # 2) Taşınabilir exe
        if 'PixhawkLogAnaliz.exe' in assets:
            t0 = time.time()
            try:
                op = os.path.join(work, 'oldp_' + frm); os.makedirs(op, exist_ok=True)
                fetch(assets['PixhawkLogAnaliz.exe'], os.path.join(op, 'PixhawkLogAnaliz.exe'))
                out = os.path.join(a.out, f'patch-from-{frm}-portable.zip')
                st, msg = build_one(op, newp, out, frm, a.version, 'file', ['PixhawkLogAnaliz.exe'], idx['portable']['size'])
                if st:
                    ent['file'] = {'name': os.path.basename(out), 'size': st['size'], 'sha256': delta.sha256_file(out), 'ratio': st['ratio']}
                idx['log'].append(f'{frm} portable: {msg} ({time.time() - t0:.0f}s)')
                shutil.rmtree(op, ignore_errors=True)
            except Exception as e:
                idx['log'].append(f'{frm} portable FAILED: {e}'); traceback.print_exc()
        if ent: idx['patches'][frm] = ent
    with open(os.path.join(a.out, 'delta-index.json'), 'w', encoding='utf-8') as f:
        json.dump(idx, f, indent=1)
    print('\n'.join(idx['log']))
    print(json.dumps({k: {kk: (vv['size'], vv['ratio']) for kk, vv in v.items()} for k, v in idx['patches'].items()}, indent=1))
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
