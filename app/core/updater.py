"""GitHub Releases üzerinden tek tuşla güncelleme (yüzde, MB, kalan, hız)."""
from __future__ import annotations
import json, os, subprocess, sys, tempfile, time, urllib.request
from ..version import VERSION, REPO, APP_ID

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
    return {'version': tag.lstrip('v'), 'url': asset['browser_download_url'], 'size': asset.get('size', 0),
            'notes': d.get('body') or '', 'name': asset['name'], 'kind': kind}


def download(info, progress=None, cancel=None):
    """progress(done_bytes, total_bytes, speed_bps, eta_s). İndirilen dosya yolunu döner."""
    d = os.path.join(tempfile.gettempdir(), APP_ID + '_update'); os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, (f"{APP_ID}-Setup-{info['version']}.exe" if info.get('kind') == 'setup' else f"{APP_ID}-{info['version']}.exe") + '.part')
    req = urllib.request.Request(info['url'], headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r, open(dst, 'wb') as f:
        total = int(r.headers.get('Content-Length') or info.get('size') or 0)
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
