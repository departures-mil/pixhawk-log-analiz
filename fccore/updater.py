"""fccore.updater — GitHub Releases latest.json ile tek tuşla güncelleme (SPEC "Güncelleme manifesti" / "Yama kuralları").
Web FC.updater ile aynı kurallar: semver, kanal seçimi, minVersion → setupChannel, önce yama (FCD1), SHA-256,
yama yolunda HERHANGİ bir hata → kendiliğinden tam dosya. "Atla" yoktur.

PyInstaller one-dir uygulaması için kanallar:
  win-app   : uygulama klasörünün belirlenimci zip'i (fcpack). Yama tabanı: (1) son güncellemede saklanan zip,
              (2) kurulu klasörden yeniden üretilen zip — yamanın kaynak SHA-256'sı tutmazsa tam zip indirilir.
              Kurulum: zip → <klasör>.new, program kapanınca yardımcı betik klasörleri takas eder, yeni sürümü açar;
              yeni sürüm 90 sn içinde "açıldım" işareti bırakmazsa eski klasör geri konur (rollback).
  win-setup : kurulum exe'si — doğrulanır, ayrık süreç olarak çalıştırılır, program kapanır.
              Updater(setup_args='inno'|'nsis'|[...]) → program kapanınca sessiz kurulum, bitince program yeniden açılır.
  Yardımcı betikler güncelleme klasöründe (staging) çalışır; çalışma klasörü kurulum klasörü olmaz.
  win-exe   : tek exe — aynı takas yöntemiyle dosya değiştirilir.

    u = Updater(repo='pixhawk-log-analiz', app='pixhawk-log-analiz', version='1.4.0')
    u.subscribe(lambda st: ...)      # durum sözlüğü (iş parçacığından çağrılabilir; Qt'de UpdateController kullanın)
    u.check(); u.run()
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import progress as _progress
from . import storage, i18n

OWNER = 'departures-mil'
UA = 'FalconCekirdek-Qt/1.0'
_HOSTS = re.compile(r'^https://([a-z0-9-]+\.)*(github\.com|githubusercontent\.com)(/|$)')


class UpdateError(Exception):
    def __init__(self, code, msg=None, **kw):
        super().__init__(msg or code)
        self.code = code
        for k, v in kw.items():
            setattr(self, k, v)


# ---------------------------------------------------------------- saf yardımcılar (test edilir)
_SEMVER = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+.*)?$')


def parse(v):
    m = _SEMVER.match(str(v or '').strip())
    return {'n': [int(m.group(1)), int(m.group(2)), int(m.group(3))], 'pre': m.group(4) or ''} if m else None


def cmp(a, b):
    x, y = parse(a), parse(b)
    if not x or not y:
        raise UpdateError('BAD_VERSION')
    for i in range(3):
        if x['n'][i] != y['n'][i]:
            return -1 if x['n'][i] < y['n'][i] else 1
    if x['pre'] == y['pre']:
        return 0
    if not x['pre']:
        return 1
    if not y['pre']:
        return -1
    return -1 if x['pre'] < y['pre'] else 1


def norm_ver(v):
    return re.sub(r'^v', '', str(v))


def asset_url(o, version, file):
    return 'https://github.com/%s/%s/releases/download/v%s/%s' % (o.get('owner') or OWNER, o['repo'], version, urllib.parse.quote(file))


def manifest_url(o):
    return o.get('manifestUrl') or 'https://github.com/%s/%s/releases/latest/download/latest.json' % (o.get('owner') or OWNER, o['repo'])


def good_asset(a):
    try:
        return isinstance(a, dict) and isinstance(a.get('file'), str) and a['file'] and \
            re.fullmatch(r'[0-9a-fA-F]{64}', a.get('sha256') or '') is not None and float(a.get('size') or 0) > 0
    except (TypeError, ValueError):
        return False


def plan(man, o):
    """Manifestten ne indirileceğini seçer → None (güncel) ya da
    {version, notes, channel, mode:'patch'|'full', file, size, sha256, url, full:{...}, targetSha256, targetSize, belowMin}"""
    if not isinstance(man, dict) or man.get('schema') != 1 or not parse(man.get('version')):
        raise UpdateError('BAD_MANIFEST')
    if o.get('app') and man.get('app') and man['app'] != o['app']:
        raise UpdateError('WRONG_APP')
    if cmp(man['version'], o['version']) <= 0:
        return None
    assets = man.get('assets') or {}
    ch = o.get('channel')
    below = bool(man.get('minVersion') and parse(man['minVersion']) and cmp(o['version'], man['minVersion']) < 0)
    if below and o.get('setupChannel') and good_asset(assets.get(o['setupChannel'])):
        ch = o['setupChannel']
    a = assets.get(ch)
    if not good_asset(a):
        raise UpdateError('NO_CHANNEL', channel=ch)
    ver = norm_ver(man['version'])
    full = {'file': a['file'], 'size': int(a['size']), 'sha256': a['sha256'].lower(), 'url': asset_url(o, ver, a['file'])}
    p = (a.get('patches') or {}).get(norm_ver(o['version'])) if not below else None
    r = {'version': ver, 'notes': man.get('notes') or {}, 'published': man.get('published') or '', 'channel': ch,
         'belowMin': below, 'full': full, 'targetSha256': full['sha256'], 'targetSize': full['size']}
    if good_asset(p) and int(p['size']) < full['size']:
        r.update(mode='patch', file=p['file'], size=int(p['size']), sha256=p['sha256'].lower(), url=asset_url(o, ver, p['file']))
    else:
        r.update(mode='full', file=full['file'], size=full['size'], sha256=full['sha256'], url=full['url'])
    # win-app klasörü yazılamazsa kullanılacak kurulum kanalı
    sc = o.get('setupChannel')
    if sc and sc != ch and good_asset(assets.get(sc)):
        s = assets[sc]
        r['setup'] = {'channel': sc, 'file': s['file'], 'size': int(s['size']), 'sha256': s['sha256'].lower(), 'url': asset_url(o, ver, s['file'])}
    return r


def sha256_file(path):
    h = hashlib.sha256()
    n = 0
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
            n += len(b)
    return n, h.hexdigest()


def error_text(code, lang=None):
    if code == 'BAD_HASH':
        return i18n.t('fc.update.bad', None, lang)
    if code == 'OFFLINE':
        return i18n.t('fc.update.offline', None, lang)
    return i18n.t('fc.update.failed', {'e': code}, lang)


# ---------------------------------------------------------------- HTTP
def default_open(url, timeout=30):
    """urllib ile açar; yalnız GitHub alan adları (yönlendirmeler dahil)."""
    if not _HOSTS.match(url):
        raise UpdateError('BAD_HOST')
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity'})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise UpdateError('HTTP_%d' % e.code, status=e.code)
    except (urllib.error.URLError, OSError) as e:
        raise UpdateError('OFFLINE', str(e))
    if not _HOSTS.match(r.geturl()):
        r.close()
        raise UpdateError('BAD_HOST')
    return r


# ---------------------------------------------------------------- ortam
def frozen():
    return bool(getattr(sys, 'frozen', False))


def app_dir():
    return os.path.dirname(os.path.abspath(sys.executable if frozen() else sys.argv[0] or '.'))


class Updater:
    def __init__(self, repo=None, app=None, version='0.0.0', owner=None, channel='win-app', setup_channel='win-setup',
                 manifest_url=None, opener=None, app_dir=None, exe=None, staging=None, can_update=None, keep_base=True,
                 on_quit=None, open_url=None, spawn=None, setup_args='nsis', setup_relaunch=None, auto_install=True):
        self.cfg = {'repo': repo, 'owner': owner, 'app': app or repo, 'version': norm_ver(version), 'channel': channel,
                    'setupChannel': setup_channel, 'manifestUrl': manifest_url}
        self.opener = opener or default_open
        self.app_dir = app_dir or globals()['app_dir']()
        self.exe = exe or (sys.executable if frozen() else None)
        self.staging = staging or os.path.join(os.path.dirname(storage.path() or tempfile.gettempdir()), 'guncelleme')
        self._can = can_update
        self.keep_base = keep_base
        self.on_quit = on_quit
        self.open_url = open_url
        self.spawn = spawn or _spawn_detached
        # win-setup: varsayılan 'nsis' (sessiz). None → kurulum exe'si argümansız (görünür) açılır, program kapanır (eski davranış).
        # 'inno' | 'nsis' | [argümanlar] → program kapanınca sessiz kurulum (bekleyerek), sonra program yeniden açılır
        # (setup_relaunch: açılacak exe; None → çalışan exe, False → açma).
        self.setup_args = setup_args
        self.setup_relaunch = setup_relaunch
        self.state = {'status': 'idle', 'current': self.cfg['version'], 'plan': None, 'progress': None, 'mode': None,
                      'error': None, 'checkedAt': None, 'fallback': False, 'patchError': None}
        self._subs = []
        self._lock = threading.Lock()
        self._running = False
        self._timer = None
        # Otomatik güncelleme: yeni sürüm bulununca sorulmadan arka planda indirilir/hazırlanır (status 'ready');
        # program kapanınca (apply_pending) pencere açmadan kurulur. Güncelle düğmesi → hemen kur + yeniden aç.
        self.auto_install = auto_install
        self._pending = None

    # -------- durum
    def snapshot(self):
        return dict(self.state)

    def _set(self, **kw):
        self.state.update(kw)
        s = self.snapshot()
        for f in list(self._subs):
            try:
                f(s)
            except Exception:
                pass

    def subscribe(self, f):
        self._subs.append(f)
        try:
            f(self.snapshot())
        except Exception:
            pass
        return lambda: self._subs.remove(f) if f in self._subs else None

    def can_update(self):
        if self._can is not None:
            return bool(self._can)
        return frozen() and sys.platform.startswith('win')

    # -------- ağ
    def _read_json(self, url):
        try:
            r = self.opener(url)
        except UpdateError as e:
            if e.code == 'HTTP_404':
                return None
            raise
        try:
            st = getattr(r, 'status', 200)
            if st == 404:
                return None
            if st and st >= 400:
                raise UpdateError('HTTP_%d' % st)
            return json.loads(r.read().decode('utf-8'))
        finally:
            try:
                r.close()
            except Exception:
                pass

    def download(self, item, dest, mode):
        """Akışlı indirme + ilerleme + boyut/SHA-256 denetimi. Hata → UpdateError."""
        self._set(status='downloading', mode=mode, progress={'done': 0, 'total': item['size'], 'pct': 0, 'remaining': item['size'], 'speed': 0, 'finished': False})
        tr = _progress.tracker(item['size'])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        h = hashlib.sha256()
        n = 0
        last = 0
        r = self.opener(item['url'])
        try:
            st = getattr(r, 'status', 200)
            if st and st >= 400:
                raise UpdateError('HTTP_%d' % st)
            with open(dest + '.part', 'wb') as f:
                while True:
                    b = r.read(256 * 1024)
                    if not b:
                        break
                    f.write(b)
                    h.update(b)
                    n += len(b)
                    if n > item['size']:
                        raise UpdateError('BAD_HASH')
                    t = time.monotonic()
                    if t - last > 0.15:
                        last = t
                        self._set(progress=tr.update(n))
        finally:
            try:
                r.close()
            except Exception:
                pass
        self._set(progress=tr.update(n, True), status='verifying')
        if n != item['size'] or h.hexdigest() != item['sha256']:
            _rm(dest + '.part')
            raise UpdateError('BAD_HASH')
        os.replace(dest + '.part', dest)
        return dest

    # -------- denetle
    def check(self, silent=False):
        if self._running or self.state['status'] in ('checking', 'queued', 'ready'):
            return self.state['plan']
        return self._check(silent)

    def _check(self, silent=False):
        if not self.cfg['repo'] and not self.cfg['manifestUrl']:
            return None
        prev = self.state['status']
        if not silent:
            self._set(status='checking', error=None)
        try:
            man = self._read_json(manifest_url(self.cfg))
            p = plan(man, self.cfg) if man else None
            if p:
                storage.set('whatsnew.pending', {'version': p['version'], 'notes': p['notes']})
            bg = bool(p) and self.auto_install and self.can_update() and self._pending is None
            self._set(status=('queued' if bg else 'available') if p else 'none', plan=p, current=self.cfg['version'],
                      checkedAt=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), error=None)
            if bg:
                threading.Thread(target=self._background, name='fc-update-bg', daemon=True).start()
            return p
        except Exception as e:
            code = getattr(e, 'code', None) or type(e).__name__
            self._set(status=(prev if prev != 'checking' else 'idle') if silent else 'error', error=code)
            return None
        finally:
            if self.state['status'] == 'checking':
                self._set(status='idle')

    def start(self, interval_hours=6, first_delay=6.0):
        """Arka plan denetimi: açılıştan first_delay sn sonra, sonra her interval_hours saatte."""
        def loop():
            time.sleep(first_delay)
            while True:
                self.check(silent=True)
                time.sleep(max(1, interval_hours) * 3600)
        self._timer = threading.Thread(target=loop, name='fc-updater', daemon=True)
        self._timer.start()
        return self

    # -------- otomatik (arka plan)
    def _background(self):
        self._set(bg=True)
        try:
            self.run(deferred=True)
            if self._pending is not None:
                self._set(status='ready', progress=None)
        except Exception:
            self._pending = None
            self._set(status='available', error=None)
        finally:
            self._set(bg=False)

    def apply_pending(self, relaunch=False):
        """Hazırlanmış güncellemeyi kurar (yardımcı betik program kapanınca çalışır). Program kapanırken (aboutToQuit) çağrılır;
        relaunch=True → kurulumdan sonra program yeniden açılır (Güncelle düğmesi)."""
        f, self._pending = self._pending, None
        if f is None:
            return False
        f(relaunch)
        return True

    # -------- tek tuş
    def run(self, deferred=False):
        """İndir → doğrula → kur. Döner 'patch' | 'full' | 'setup' | 'browser' | None. Hata → UpdateError.
        deferred=True → yalnız hazırla (program kapanınca apply_pending kurar). Hazır güncelleme varsa run() onu hemen kurar."""
        if not deferred and self._pending is not None:
            self._set(status='restarting')
            self.apply_pending(relaunch=True)
            self._quit()
            return 'staged'
        with self._lock:
            if self._running:
                return None
            self._running = True
        self._deferred = deferred
        try:
            p = self.state['plan'] or self._check()
            if not p:
                return None
            if not self.can_update():
                self._set(status='available')
                url = 'https://github.com/%s/%s/releases/latest' % (self.cfg.get('owner') or OWNER, self.cfg['repo'])
                (self.open_url or _open_url)(url)
                return 'browser'
            self._set(error=None, fallback=False, patchError=None)
            storage.set('whatsnew.pending', {'version': p['version'], 'notes': p['notes']})
            os.makedirs(self.staging, exist_ok=True)
            try:
                if p['mode'] == 'patch':
                    try:
                        out = self._patch(p)
                        self._install(p, out, p['channel'])
                        return 'patch'
                    except UpdateError as e:
                        if e.code in ('NO_WRITE', 'SPAWN_FAILED'):
                            raise
                        self._set(fallback=True, patchError=e.code)
                    except Exception as e:  # yama yolundaki her hata → tam dosya
                        self._set(fallback=True, patchError=type(e).__name__)
                dest = os.path.join(self.staging, _safe_name(p['full']['file']))
                self.download(p['full'], dest, 'full')
                self._install(p, dest, p['channel'])
                return 'setup' if self._is_setup(p['channel'], dest) else 'full'
            except UpdateError as e:
                if e.code == 'NO_WRITE' and p.get('setup'):
                    s = p['setup']
                    dest = os.path.join(self.staging, _safe_name(s['file']))
                    self.download(s, dest, 'full')
                    self._install(p, dest, s['channel'])
                    return 'setup'
                raise
        except Exception as e:
            code = getattr(e, 'code', None) or type(e).__name__
            self._set(status='error', error=code)
            raise
        finally:
            self._running = False

    # -------- yama
    def _patch(self, p):
        pf = os.path.join(self.staging, _safe_name(p['file']))
        self.download(p, pf, 'patch')
        from . import _fcdelta
        hd = _fcdelta.read_header(open(pf, 'rb').read(_fcdelta.HEADER_LEN))
        base = self._base_for(p, hd)
        self._set(status='installing')
        out = os.path.join(self.staging, _safe_name(p['full']['file']))
        _fcdelta.apply_file(base, pf, out)
        n, hx = sha256_file(out)
        if n != p['targetSize'] or hx != p['targetSha256']:
            _rm(out)
            raise UpdateError('BAD_HASH')
        _rm(pf)
        return out

    def _base_for(self, p, hd):
        """Kurulu sürümün kanal dosyası: saklanan taban ya da yeniden üretilen zip / exe. Kaynak SHA'sı tutmazsa NO_BASE."""
        cands = []
        cached = storage.get('update.base')
        if isinstance(cached, dict) and cached.get('version') == self.cfg['version'] and cached.get('channel') == p['channel']:
            cands.append(cached.get('path'))
        if p['channel'] in ('win-exe',) and self.exe:
            cands.append(self.exe)
        for c in cands:
            if c and os.path.isfile(c):
                n, hx = sha256_file(c)
                if n == hd['srcLen'] and hx == hd['srcSha256']:
                    return c
        if p['channel'] == 'win-app' and os.path.isdir(self.app_dir):
            from . import fcpack
            out = os.path.join(self.staging, 'base-yeniden.zip')
            fcpack.pack(self.app_dir, out)
            n, hx = sha256_file(out)
            if n == hd['srcLen'] and hx == hd['srcSha256']:
                return out
            _rm(out)
        raise UpdateError('NO_BASE')

    # -------- kurulum
    def _is_setup(self, channel, path):
        return channel == self.cfg.get('setupChannel') or channel == 'win-setup'

    def _install(self, p, path, channel):
        self._set(status='installing')
        if self._is_setup(channel, path):
            exe = path if path.lower().endswith('.exe') else path + '.exe'
            if exe != path:
                os.replace(path, exe)
            args = setup_args_for(self.setup_args)
            ver = p.get('version', '') if isinstance(p, dict) else ''

            def go(relaunch_after=True):
                try:
                    if args is None:
                        self._spawn([exe])
                    else:
                        relaunch = (self.exe if self.setup_relaunch is None else (self.setup_relaunch or None)) if relaunch_after else None
                        script = write_setup_script(self.staging, os.getpid(), exe, args, relaunch, version=ver)
                        self._spawn(['cmd.exe', '/c', script] if script.endswith('.cmd') else ['/bin/sh', script])
                except Exception:
                    raise UpdateError('SPAWN_FAILED')
            if getattr(self, '_deferred', False):
                self._pending = go
                return
            go()
            self._set(status='restarting')
            self._quit()
            return
        if channel == 'win-app':
            self._install_dir(p, path)
        else:
            self._install_file(p, path)
        if self._pending is not None and getattr(self, '_deferred', False):
            return
        self._set(status='restarting')
        self._quit()

    def _writable(self, d):
        try:
            fd, t = tempfile.mkstemp(prefix='.fc-w-', dir=d)
            os.close(fd)
            os.unlink(t)
            return True
        except OSError:
            return False

    def _install_dir(self, p, zip_path):
        from . import fcpack
        app = os.path.abspath(self.app_dir)
        parent = os.path.dirname(app)
        if not self._writable(parent) or not self._writable(app):
            raise UpdateError('NO_WRITE')
        new = app + '.new'
        shutil.rmtree(new, ignore_errors=True)
        try:
            fcpack.safe_extract(zip_path, new)
        except ValueError:
            shutil.rmtree(new, ignore_errors=True)
            raise UpdateError('BAD_ZIP')
        exe_rel = os.path.relpath(self.exe, app) if self.exe else None
        if exe_rel and not os.path.isfile(os.path.join(new, exe_rel)):
            shutil.rmtree(new, ignore_errors=True)
            raise UpdateError('BAD_ZIP')
        if self.keep_base:
            base = os.path.join(self.staging, 'base-win-app.zip')
            old = storage.get('update.base')
            os.replace(zip_path, base)
            storage.set('update.base', {'version': p['version'], 'channel': 'win-app', 'path': base, 'sha256': p['targetSha256']})
            if isinstance(old, dict) and old.get('path') not in (None, base):
                _rm(old['path'])
        else:
            _rm(zip_path)
        self._helper(kind='dir', target=app, new=new, exe_rel=exe_rel, version=p['version'])

    def _install_file(self, p, path):
        if not self.exe:
            raise UpdateError('NOT_PACKAGED')
        d = os.path.dirname(os.path.abspath(self.exe))
        if not self._writable(d):
            raise UpdateError('NO_WRITE')
        new = self.exe + '.new'
        shutil.copyfile(path, new)
        if self.keep_base:
            base = os.path.join(self.staging, 'base-' + p['channel'] + '.bin')
            os.replace(path, base)
            storage.set('update.base', {'version': p['version'], 'channel': p['channel'], 'path': base, 'sha256': p['targetSha256']})
        self._helper(kind='file', target=os.path.abspath(self.exe), new=new, exe_rel=None, version=p['version'])

    def marker(self, version):
        return os.path.join(self.staging, 'acildi-%s.ok' % version)

    def _helper(self, kind, target, new, exe_rel, version):
        exe = os.path.join(target, exe_rel) if kind == 'dir' else target
        mk = self.marker(version)
        _rm(mk)
        def go(relaunch=True):
            if relaunch:
                storage.set('update.pending', {'version': version, 'from': self.cfg['version'], 'at': int(time.time())})
            script = write_swap_script(self.staging, os.getpid(), kind, target, new, exe, mk, version, relaunch=relaunch)
            try:
                if sys.platform.startswith('win'):
                    self._spawn(['cmd.exe', '/c', script])
                else:
                    self._spawn(['/bin/sh', script])
            except Exception:
                raise UpdateError('SPAWN_FAILED')
        if getattr(self, '_deferred', False):
            self._pending = go
            return
        go()

    def _spawn(self, args):
        """Ayrık süreç; çalışma klasörü güncelleme klasörü (kurulum klasörü değil — yoksa Windows klasörü taşıyamaz).
        Uygulamanın verdiği spawn(args) cwd almıyorsa eskisi gibi çağrılır."""
        os.makedirs(self.staging, exist_ok=True)
        if _accepts_cwd(self.spawn):
            return self.spawn(args, cwd=self.staging)
        return self.spawn(args)

    def _quit(self):
        if self.on_quit:
            try:
                self.on_quit()
            except Exception:
                pass


def confirm_started(staging=None, version=None):
    """Yeni sürüm açıldığında çağrılır (fccore.init kendisi yapar): takas betiğine "açıldım" işareti bırakır."""
    pend = storage.get('update.pending')
    if not isinstance(pend, dict):
        return False
    version = version or pend.get('version')
    staging = staging or os.path.join(os.path.dirname(storage.path() or tempfile.gettempdir()), 'guncelleme')
    try:
        os.makedirs(staging, exist_ok=True)
        with open(os.path.join(staging, 'acildi-%s.ok' % version), 'w') as f:
            f.write(str(os.getpid()))
    except OSError:
        return False
    storage.remove('update.pending')
    return True


def write_swap_script(staging, pid, kind, target, new, exe, marker, version, wait_s=90, windows=None, relaunch=True):
    """Program kapanınca çalışan takas betiği (Windows .cmd, diğerleri sh). Hata → eski sürüm geri konur ve
    eski sürüm --fc-update-failed ile yeniden açılır (takas hiç başlayamadıysa da)."""
    os.makedirs(staging, exist_ok=True)
    bak = target + '.bak'
    log = os.path.join(staging, 'takas.log')
    if sys.platform.startswith('win') if windows is None else windows:
        q = lambda s: '"%s"' % s  # noqa: E731
        mv = 'move /Y' if kind == 'file' else 'move'
        rm = (lambda x: 'if exist %s rmdir /S /Q %s' % (q(x), q(x))) if kind == 'dir' else (lambda x: 'if exist %s del /F /Q %s' % (q(x), q(x)))
        body = r'''@echo off
chcp 65001 >NUL
setlocal
set N=0
:bekle
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  set /A N+=1
  if %N% GEQ 120 goto hata
  ping -n 2 127.0.0.1 >NUL
  goto bekle
)
{rm_bak}
set N=0
:tasi
{mv} {target} {bak} >NUL 2>&1
if not errorlevel 1 goto yeni
set /A N+=1
if %N% GEQ 20 goto hata
ping -n 2 127.0.0.1 >NUL
goto tasi
:yeni
{mv} {new} {target} >NUL 2>&1
if errorlevel 1 goto geri
if not exist {exe} goto geri
{norelaunch}
start "" {exe} --fc-updated={ver}
set N=0
:onay
if exist {marker} goto tamam
set /A N+=1
if %N% GEQ {wait} goto geri
ping -n 2 127.0.0.1 >NUL
goto onay
:tamam
{rm_bak}
echo ok {ver}> {log}
goto son
:geri
{rm_target}
{mv} {bak} {target} >NUL 2>&1
echo geri-alindi {ver}> {log}
start "" {exe} --fc-update-failed={ver}
goto son
:hata
echo hata {ver}> {log}
if exist {exe} start "" {exe} --fc-update-failed={ver}
:son
(goto) 2>NUL & del "%~f0"
'''.format(pid=pid, rm_bak=rm(bak), mv=mv, target=q(target), bak=q(bak), new=q(new), exe=q(exe), ver=version,
           marker=q(marker), wait=wait_s, log=q(log), rm_target=rm(target),
           norelaunch='' if relaunch else ('echo ok {0}> {1}\ngoto son'.format(version, q(log))))
        path = os.path.join(staging, 'takas-%s.cmd' % version)
        with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(body)
        return path
    sq = lambda s: "'" + str(s).replace("'", "'\\''") + "'"  # noqa: E731
    body = '''#!/bin/sh
# fccore takas betiği (otomatik)
n=0
while kill -0 {pid} 2>/dev/null; do n=$((n+1)); [ $n -ge 240 ] && {{ echo "hata {ver}" > {log}; exit 1; }}; sleep 0.5; done
rm -rf {bak}
mv {target} {bak} || {{ echo "hata {ver}" > {log}; [ -e {exe} ] && {{ {exe} --fc-update-failed={ver} >/dev/null 2>&1 & }}; exit 1; }}
if ! mv {new} {target} || [ ! -e {exe} ]; then rm -rf {target}; mv {bak} {target}; echo "geri-alindi {ver}" > {log}; exit 1; fi
chmod +x {exe} 2>/dev/null
{norelaunch}
{exe} --fc-updated={ver} >/dev/null 2>&1 &
n=0
while [ ! -e {marker} ]; do
  n=$((n+1))
  if [ $n -ge {wait2} ]; then rm -rf {target}; mv {bak} {target}; echo "geri-alindi {ver}" > {log}; {exe} --fc-update-failed={ver} >/dev/null 2>&1 & exit 1; fi
  sleep 0.5
done
rm -rf {bak}
echo "ok {ver}" > {log}
rm -f "$0"
'''.format(pid=pid, ver=version, log=sq(log), bak=sq(bak), target=sq(target), new=sq(new), exe=sq(exe), marker=sq(marker), wait2=wait_s * 2,
           norelaunch='' if relaunch else 'echo "ok {0}" > {1}; rm -f "$0"; exit 0'.format(version, sq(log)))
    path = os.path.join(staging, 'takas-%s.sh' % version)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(body)
    os.chmod(path, 0o755)
    return path


INNO_SILENT = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/CLOSEAPPLICATIONS']
NSIS_SILENT = ['/S']


def setup_args_for(v):
    """'inno' → Inno Setup sessiz, 'nsis' | True → NSIS /S, liste → olduğu gibi, None → None (eski davranış)."""
    if v is None or v is False:
        return None
    if v is True or v == 'nsis':
        return list(NSIS_SILENT)
    if v == 'inno':
        return list(INNO_SILENT)
    return [str(x) for x in v]


def write_setup_script(staging, pid, setup_exe, args, relaunch=None, windows=None, version=''):
    """Program kapanınca kurulumu sessiz çalıştırıp bitmesini bekleyen, sonra programı yeniden açan betik."""
    os.makedirs(staging, exist_ok=True)
    log = os.path.join(staging, 'kurulum.log')
    if sys.platform.startswith('win') if windows is None else windows:
        q = lambda s: '"%s"' % s  # noqa: E731
        lines = ['@echo off', 'chcp 65001 >NUL', 'setlocal', 'set N=0', ':bekle',
                 'tasklist /FI "PID eq {0}" 2>NUL | find "{0}" >NUL'.format(pid),
                 'if errorlevel 1 goto kur', 'set /A N+=1', 'if %N% GEQ 120 goto kur', 'ping -n 2 127.0.0.1 >NUL', 'goto bekle',
                 ':kur', 'start "" /wait {0} {1}'.format(q(setup_exe), ' '.join(args)).rstrip(),
                 'echo kurulum %ERRORLEVEL%> {0}'.format(q(log))]
        if relaunch:
            lines.append('if exist {0} start "" {0} --fc-updated{1}'.format(q(relaunch), '=' + version if version else ''))
        lines.append('(goto) 2>NUL & del "%~f0"')
        path = os.path.join(staging, 'kurulum.cmd')
        with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write('\n'.join(lines) + '\n')
        return path
    sq = lambda s: "'" + str(s).replace("'", "'\\''") + "'"  # noqa: E731
    body = '#!/bin/sh\nn=0\nwhile kill -0 {pid} 2>/dev/null; do n=$((n+1)); [ $n -ge 240 ] && break; sleep 0.5; done\n' \
           '{exe} {args}\necho "kurulum $?" > {log}\n'.format(pid=pid, exe=sq(setup_exe), args=' '.join(sq(a) for a in args), log=sq(log))
    if relaunch:
        body += '[ -e {0} ] && {{ {0} --fc-updated{1} >/dev/null 2>&1 & }}\n'.format(sq(relaunch), '=' + version if version else '')
    body += 'rm -f "$0"\n'
    path = os.path.join(staging, 'kurulum.sh')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(body)
    os.chmod(path, 0o755)
    return path


def _accepts_cwd(fn):
    if fn is _spawn_detached:
        return True
    try:
        import inspect
        ps = inspect.signature(fn).parameters
        return 'cwd' in ps or any(p.kind == p.VAR_KEYWORD for p in ps.values())
    except (TypeError, ValueError):
        return False


def _spawn_detached(args, cwd=None):
    kw = {'close_fds': True, 'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if cwd:
        kw['cwd'] = cwd
    if sys.platform.startswith('win'):
        # CREATE_NO_WINDOW | NEW_PROCESS_GROUP — DETACHED_PROCESS YOK: betiğin cmd'si gizli bir konsol alır, içindeki tasklist/find/ping
        # aynı gizli konsolu kullanır. (DETACHED_PROCESS ile her komut ayrı SİYAH PENCERE açıyor, Windows Terminal varsayılan
        # konsolken `find` girdisiz kalıp güncelleme takılıyordu.) Bekleme `timeout` değil `ping`: girdisi yönlendirilmiş
        # konsolda `timeout` hemen çıkıp bekleme döngüsünü bozuyordu.
        kw['creationflags'] = 0x08000000 | 0x00000200
        si = subprocess.STARTUPINFO()
        si.dwFlags |= 1  # STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        kw['startupinfo'] = si
    else:
        kw['start_new_session'] = True
    return subprocess.Popen(args, **kw)


def _open_url(u):
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(u))
    except Exception:
        import webbrowser
        webbrowser.open(u)


def _safe_name(n):
    n = re.sub(r'[^A-Za-z0-9._-]', '_', os.path.basename(str(n)))
    return n or 'indirme.bin'


def _rm(p):
    try:
        if p and os.path.exists(p):
            os.unlink(p)
    except OSError:
        pass
