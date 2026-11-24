"""GitHub Releases üzerinden tek tuşla güncelleme (yüzde, MB, kalan, hız)."""
from __future__ import annotations
import json, os, subprocess, sys, tempfile, time, urllib.request
VERSION, REPO, APP_ID = "1.0.7", "departures-mil/pixhawk-log-analiz", "PixhawkLogAnaliz"  # v1.0.7 güncelleyicisinin kopyası (köprü testi)

UA = f'{APP_ID}/{VERSION}'


def _v(s):
    s = (s or '').lstrip('vV').split('-')[0]
    try: return tuple(int(x) for x in s.split('.'))
    except Exception: return (0,)


def check(timeout=12):
    """Yeni sürüm varsa {'version','url','size','notes','name'} döner, yoksa None."""
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/releases/latest',
                                 headers={'User-Agent': UA, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    tag = d.get('tag_name', '')
    if _v(tag) <= _v(VERSION):
        return None
    assets = d.get('assets', [])
    # Öncelik: kurulum paketi (Setup). Yoksa eski usul taşınabilir exe.
    asset = next((a for a in assets if 'setup' in a['name'].lower() and a['name'].lower().endswith('.exe')), None)
    kind = 'setup'
    if not asset:
        asset = next((a for a in assets if a['name'].lower().endswith('.exe')), None); kind = 'exe'
    if not asset:
        return None
    info = {'version': tag.lstrip('v'), 'url': asset['browser_download_url'], 'size': asset.get('size', 0),
            'notes': d.get('body') or '', 'name': asset['name'], 'kind': kind, 'patch': None}
    try:
        info['patch'] = _find_patch(assets, info, timeout)
    except Exception:
        info['patch'] = None
    return info


def current_mode():
    """'tree' = Setup ile kurulu klasör, 'file' = taşınabilir exe, None = geliştirici çalıştırması."""
    if not getattr(sys, 'frozen', False): return None
    return 'tree' if is_installed() else 'file'


def _find_patch(assets, info, timeout=12):
    """Kendi sürümümüz için yayınlanmış yama varsa {'url','size','sha256','name','kind','full_sha256'}."""
    mode = current_mode()
    if not mode: return None
    ix = next((a for a in assets if a['name'] == 'delta-index.json'), None)
    if not ix: return None
    req = urllib.request.Request(ix['browser_download_url'], headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        idx = json.load(r)
    if idx.get('version') != info['version']: return None
    ent = (idx.get('patches') or {}).get(VERSION, {}).get(mode)
    if not ent: return None
    a = next((x for x in assets if x['name'] == ent['name']), None)
    if not a: return None
    # Tam dosyaya geçişte indirilen dosya da SHA-256 ile doğrulanabilsin
    full = idx.get('setup' if info['kind'] == 'setup' else 'portable') or {}
    if full.get('name') == info['name']: info['sha256'] = full.get('sha256')
    return {'url': a['browser_download_url'], 'size': a.get('size') or ent['size'], 'sha256': ent['sha256'],
            'name': ent['name'], 'kind': mode, 'ratio': ent.get('ratio')}


def _workdir():
    d = os.path.join(tempfile.gettempdir(), APP_ID + '_update'); os.makedirs(d, exist_ok=True)
    return d


def download(info, progress=None, cancel=None, on_mode=None, force_full=False):
    """Önce 'yalnızca değişen kısımlar' (yama) dener; yama yoksa ya da herhangi bir hata olursa
    otomatik olarak tam dosyaya geçer. progress(done, total, speed_bps, eta_s);
    on_mode('delta'|'full', toplam_bayt). Döner: tam dosya yolu (str) ya da
    yama için {'stage','delete','kind','version'}."""
    p = info.get('patch')
    if p and not force_full and current_mode():
        try:
            if on_mode: on_mode('delta', p['size'])
            return _download_patch(info, p, progress, cancel)
        except Exception as e:
            if str(e) == 'cancelled': raise
            info['delta_error'] = str(e)
    if on_mode: on_mode('full', info.get('size') or 0)
    path = _download_full(info, progress, cancel)
    if info.get('sha256'):
        from .delta import sha256_file
        if sha256_file(path) != info['sha256']:
            os.remove(path); raise RuntimeError('SHA-256 mismatch')
    return path


def _download_patch(info, p, progress, cancel):
    from . import delta
    d = _workdir()
    z = _fetch(p['url'], os.path.join(d, p['name'] + '.part'), p.get('size'), progress, cancel)
    if delta.sha256_file(z) != p['sha256']:
        raise delta.DeltaError('patch sha256')
    base = os.path.dirname(sys.executable)
    stage = os.path.join(d, 'stage_' + info['version'])
    meta = delta.stage(base, z, stage, expect_from=VERSION, expect_to=info['version'])
    try: os.remove(z)
    except OSError: pass
    return {'stage': stage, 'delete': meta.get('delete', []), 'kind': meta['kind'], 'version': info['version'],
            'files': [e['p'] for e in meta['files']]}


def _download_full(info, progress, cancel):
    d = _workdir()
    dst = os.path.join(d, (f"{APP_ID}-Setup-{info['version']}.exe" if info.get('kind') == 'setup' else f"{APP_ID}-{info['version']}.exe") + '.part')
    return _fetch(info['url'], dst, info.get('size'), progress, cancel)


def _fetch(url, dst, size, progress, cancel):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r, open(dst, 'wb') as f:
        total = int(r.headers.get('Content-Length') or size or 0)
        done = 0; t0 = time.time(); last = 0
        while True:
            if cancel and cancel():
                raise RuntimeError('cancelled')
            b = r.read(256 * 1024)
            if not b: break
            f.write(b); done += len(b)
            now = time.time()
            if progress and (now - last > 0.2 or done == total):
                sp = done / max(now - t0, 1e-3)
                progress(done, total, sp, (total - done) / sp if sp > 0 and total else 0)
                last = now
    final = dst[:-5]
    if os.path.exists(final): os.remove(final)
    os.replace(dst, final)
    return final


INSTALL_DIR = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'), 'Programs', 'Pixhawk Log Analiz')


def is_installed():
    """Program Setup ile kurulmuşsa True (kaldırıcı exe'nin yanında durur)."""
    if not getattr(sys, 'frozen', False): return False
    d = os.path.dirname(sys.executable)
    return any(f.lower().startswith('unins') and f.lower().endswith('.exe') for f in os.listdir(d))


def _launch_script(body, new_file):
    script = os.path.join(os.path.dirname(new_file), 'apply.cmd')
    with open(script, 'w', encoding='mbcs' if os.name == 'nt' else 'utf-8') as f:
        f.write(body)
    flags = 0x08000000 if os.name == 'nt' else 0
    subprocess.Popen(['cmd.exe', '/c', script], creationflags=flags, close_fds=True)


def _apply_patch_script(r, wait):
    """Yama: program kapanınca hazırlanan dosyalar kurulu klasöre kopyalanır, eskiler silinir."""
    target_dir = os.path.dirname(sys.executable)
    exe = sys.executable
    lines = [wait, 'set n=0', ':copy',
             f'robocopy "{r["stage"]}" "{target_dir}" /E /R:5 /W:1 /NFL /NDL /NJH /NJS /NP >nul',
             'if not errorlevel 8 goto copied', 'set /a n+=1', 'if %n% geq 10 goto fail',
             'ping -n 3 127.0.0.1 >nul', 'goto copy', ':copied']
    for p in r.get('delete', []):
        lines.append(f'del /f /q "{os.path.join(target_dir, *p.split("/"))}" >nul 2>&1')
    if r['kind'] == 'tree':
        lines.append(f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{{8C3F7B2E-5A1D-4E7B-9C2F-6D1A0B4E3F21}}_is1" '
                     f'/v DisplayVersion /d "{r["version"]}" /f >nul 2>&1')
    lines += [f'rmdir /s /q "{r["stage"]}" >nul 2>&1', f'start "" "{exe}" --updated', 'del "%~f0"', 'exit /b',
              ':fail', f'start "" "{exe}" --update-failed', 'del "%~f0"', '']
    _launch_script('\n'.join(lines), os.path.join(r['stage'], '..', 'x'))
    return True


def apply_and_restart(new_file):
    """Güncellemeyi uygular ve programı yeniden açar (yalnızca paketlenmiş sürümde).
    Setup paketi: program kapanınca sessizce kurulur (/VERYSILENT), kurulu sürüm açılır.
    Taşınabilir exe: dosya değiştirilir ve yeniden başlatılır."""
    if not getattr(sys, 'frozen', False):
        return False
    pid = os.getpid()
    wait = f'''@echo off
:wait
tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul && (ping -n 2 127.0.0.1 >nul & goto wait)
'''
    if isinstance(new_file, dict):
        return _apply_patch_script(new_file, wait)
    if 'setup' in os.path.basename(new_file).lower():
        target = sys.executable if is_installed() else os.path.join(INSTALL_DIR, 'PixhawkLogAnaliz.exe')
        log = os.path.join(os.path.dirname(new_file), 'setup.log')
        _launch_script(wait + f'''start "" /wait "{new_file}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /CLOSEAPPLICATIONS /LOG="{log}"
del "{new_file}" >nul 2>&1
start "" "{target}" --updated
del "%~f0"
''', new_file)
        return True
    cur = sys.executable
    _launch_script(wait + f'''set n=0
:copy
copy /y "{new_file}" "{cur}" >nul && goto ok
set /a n+=1
if %n% lss 30 (ping -n 2 127.0.0.1 >nul & goto copy)
:ok
del "{new_file}" >nul 2>&1
start "" "{cur}" --updated
del "%~f0"
''', new_file)
    return True
