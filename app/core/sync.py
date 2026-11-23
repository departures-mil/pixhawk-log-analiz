"""Eşitleme: 1) GitHub (kullanıcının kendi gizli gist'i)  2) Aynı modem/router üzerinden LAN (internet gerekmez).
İki yöntemde de kayıtlar birleştirilir: hiçbir kayıt silinmez, üst üste yazılmaz (yeni olan kazanır, notlar birleşir)."""
from __future__ import annotations
import gzip, json, socket, struct, threading, time, urllib.request
from ..version import VERSION, APP_ID

GIST_FILE = 'pixhawk-log-analiz-sync.json'
GIST_DESC = 'Pixhawk Log Analiz - eşitleme (otomatik)'
TOKEN_URL = 'https://github.com/settings/tokens/new?scopes=gist&description=Pixhawk%20Log%20Analiz'
UDP_PORT = 47811
TCP_PORT = 47812


# ------------------------------------------------------------------ yük
def build_payload(settings, archive):
    return {'app': APP_ID, 'v': VERSION, 'device': settings['device_id'], 'name': settings['device_name'],
            'time': time.strftime('%Y-%m-%d %H:%M:%S'), **archive.export(),
            'templates': settings['templates'], 'param_tx_cache': settings.get('param_tx_cache', {})}


def merge_payload(settings, archive, data):
    """Gelen veriyi yerel veriye ekler. (eklenen, güncellenen) döner."""
    if not data or data.get('app') != APP_ID:
        return 0, 0
    a, u = archive.merge(data)
    for name, lh in (data.get('templates') or {}).items():
        cur = settings['templates'].get(name)
        if cur is None:
            settings['templates'][name] = lh; a += 1
        elif cur != lh and name != 'default':
            alt = f"{name} ({data.get('name') or 'remote'})"
            if alt not in settings['templates']:
                settings['templates'][alt] = lh; a += 1
    cache = settings.setdefault('param_tx_cache', {})
    for k, v in (data.get('param_tx_cache') or {}).items():
        if k not in cache: cache[k] = v
    settings.save()
    return a, u


# ---------------------------------------------------------------- GitHub
def _gh(method, url, token, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                                          'User-Agent': f'{APP_ID}/{VERSION}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as r:
        rl = {k: r.headers.get('x-ratelimit-' + k) for k in ('limit', 'remaining', 'reset')}
        return json.loads(r.read() or b'{}'), rl


def github_sync(settings, archive):
    """Gist'i bulur/oluşturur, uzak veriyi birleştirir, birleşik veriyi geri yazar. (eklenen, güncellenen, limit) döner."""
    token = (settings.get('gh_token') or '').strip()
    if not token:
        raise ValueError('token')
    gid = settings.get('gist_id') or ''
    remote = None; rl = {}
    if not gid:
        lst, rl = _gh('GET', 'https://api.github.com/gists?per_page=100', token)
        for g in lst:
            if g.get('description') == GIST_DESC or GIST_FILE in (g.get('files') or {}):
                gid = g['id']; break
    if gid:
        try:
            g, rl = _gh('GET', f'https://api.github.com/gists/{gid}', token)
            f = (g.get('files') or {}).get(GIST_FILE)
            if f:
                txt = f.get('content') or ''
                if f.get('truncated') and f.get('raw_url'):
                    req = urllib.request.Request(f['raw_url'], headers={'Authorization': f'Bearer {token}', 'User-Agent': APP_ID})
                    with urllib.request.urlopen(req, timeout=60) as r: txt = r.read().decode('utf-8')
                remote = json.loads(txt) if txt else None
        except urllib.error.HTTPError as e:
            if e.code == 404: gid = ''
            else: raise
    added = updated = 0
    if remote:
        added, updated = merge_payload(settings, archive, remote)
    body = {'description': GIST_DESC, 'files': {GIST_FILE: {'content': json.dumps(build_payload(settings, archive), ensure_ascii=False)}}}
    if gid:
        _, rl = _gh('PATCH', f'https://api.github.com/gists/{gid}', token, body)
    else:
        body['public'] = False
        g, rl = _gh('POST', 'https://api.github.com/gists', token, body)
        gid = g['id']
    settings['gist_id'] = gid
    settings['last_sync'] = time.strftime('%Y-%m-%d %H:%M')
    settings['gh_rate'] = rl
    settings.save()
    return added, updated, rl


# ------------------------------------------------------------------- LAN
def _send(sock, obj):
    b = gzip.compress(json.dumps(obj, ensure_ascii=False).encode())
    sock.sendall(struct.pack('>I', len(b)) + b)


def _recv(sock):
    def n(k):
        buf = b''
        while len(buf) < k:
            c = sock.recv(min(65536, k - len(buf)))
            if not c: raise ConnectionError('closed')
            buf += c
        return buf
    ln = struct.unpack('>I', n(4))[0]
    if ln > 300 * 1024 * 1024: raise ValueError('too big')
    return json.loads(gzip.decompress(n(ln)))


class LanServer:
    """Uygulama açıkken arka planda diğer cihazların keşif ve eşitleme isteklerini yanıtlar."""
    def __init__(self, settings, archive, on_merged=None):
        self.s = settings; self.a = archive; self.on_merged = on_merged
        self.stop = False; self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._udp, daemon=True).start()
        threading.Thread(target=self._tcp, daemon=True).start()

    def _udp(self):
        try:
            u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            u.bind(('', UDP_PORT))
        except OSError:
            return
        while not self.stop:
            try:
                data, addr = u.recvfrom(2048)
                m = json.loads(data.decode())
                if m.get('t') == 'discover' and m.get('app') == APP_ID and m.get('dev') != self.s['device_id']:
                    if (m.get('code') or '') != (self.s.get('lan_code') or ''): continue
                    u.sendto(json.dumps({'t': 'here', 'app': APP_ID, 'dev': self.s['device_id'], 'name': self.s['device_name'],
                                         'port': TCP_PORT}).encode(), addr)
            except Exception:
                time.sleep(0.2)

    def _tcp(self):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(('', TCP_PORT)); srv.listen(4)
        except OSError:
            return
        while not self.stop:
            try:
                c, addr = srv.accept()
                threading.Thread(target=self._handle, args=(c,), daemon=True).start()
            except Exception:
                time.sleep(0.2)

    def _handle(self, c):
        try:
            c.settimeout(120)
            hello = _recv(c)
            if hello.get('app') != APP_ID or (hello.get('code') or '') != (self.s.get('lan_code') or ''):
                c.close(); return
            remote = hello.get('payload')
            with self.lock:
                res = merge_payload(self.s, self.a, remote)
                _send(c, {'app': APP_ID, 'payload': build_payload(self.s, self.a)})
            if self.on_merged: self.on_merged(res, remote.get('name', '?'))
        except Exception:
            pass
        finally:
            try: c.close()
            except Exception: pass


def discover(settings, wait=2.5):
    """Aynı ağdaki cihazları bulur: [{'dev','name','ip','port'}]."""
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    u.settimeout(0.4)
    msg = json.dumps({'t': 'discover', 'app': APP_ID, 'dev': settings['device_id'], 'code': settings.get('lan_code') or ''}).encode()
    for target in ('255.255.255.255', '<broadcast>'):
        try: u.sendto(msg, (target, UDP_PORT))
        except Exception: pass
    peers = {}; t0 = time.time()
    while time.time() - t0 < wait:
        try:
            data, addr = u.recvfrom(2048)
            m = json.loads(data.decode())
            if m.get('t') == 'here' and m.get('app') == APP_ID and m.get('dev') != settings['device_id']:
                peers[m['dev']] = {'dev': m['dev'], 'name': m.get('name', '?'), 'ip': addr[0], 'port': m.get('port', TCP_PORT)}
        except socket.timeout:
            continue
        except Exception:
            break
    u.close()
    return list(peers.values())


def lan_sync_with(settings, archive, peer):
    c = socket.create_connection((peer['ip'], peer['port']), timeout=30)
    c.settimeout(120)
    try:
        _send(c, {'app': APP_ID, 'code': settings.get('lan_code') or '', 'payload': build_payload(settings, archive)})
        resp = _recv(c)
        return merge_payload(settings, archive, resp.get('payload'))
    finally:
        c.close()
