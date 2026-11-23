"""Güvenlik: şifreli paylaşım, yerel veri şifreleme, kullanıcı rolleri.

* Paylaşım: dosyalar AES-256-GCM ile parolayla şifrelenir (PBKDF2-SHA256, 200 000 tur). PDF raporlar ayrıca
  standart PDF parolasıyla korunabilir (her PDF okuyucu açar).
* Yerel veri: API anahtarları ve token'lar Windows DPAPI ile (yalnızca bu Windows kullanıcısı çözebilir),
  arşive kopyalanan loglar isteğe bağlı olarak cihaz anahtarıyla şifrelenir.
* Roller: yönetici / eğitimci / öğrenci. Parolalar yalnızca tuzlu PBKDF2 özeti olarak saklanır.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, sys, time, uuid

MAGIC = b'PXENC1'
ROLES = ('admin', 'instructor', 'student')
ROLE_NAMES = {'admin': ('Yönetici', 'Administrator', 'المسؤول'), 'instructor': ('Eğitimci', 'Instructor', 'المدرّب'),
              'student': ('Öğrenci', 'Student', 'الطالب')}
# Rollere kapalı sayfalar
HIDDEN = {'student': {'batch', 'archive', 'fleet', 'pilots'}, 'instructor': set(), 'admin': set()}


def role_name(r, lang='tr'):
    return ROLE_NAMES.get(r, (r, r, r))[('tr', 'en', 'ar').index(lang) if lang in ('tr', 'en', 'ar') else 0]


# ------------------------------------------------------------ parolalı şifreleme
def _kdf(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200_000, 32)


def is_encrypted(data: bytes) -> bool:
    return data[:len(MAGIC)] == MAGIC


def encrypt(data: bytes, password: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt = os.urandom(16); nonce = os.urandom(12)
    return MAGIC + salt + nonce + AESGCM(_kdf(password, salt)).encrypt(nonce, data, MAGIC)


def decrypt(blob: bytes, password: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not is_encrypted(blob): return blob
    o = len(MAGIC); salt = blob[o:o + 16]; nonce = blob[o + 16:o + 28]
    try:
        return AESGCM(_kdf(password, salt)).decrypt(nonce, blob[o + 28:], MAGIC)
    except Exception:
        raise ValueError('wrong password')


def encrypt_file(src, dst, password):
    with open(src, 'rb') as f: data = f.read()
    with open(dst, 'wb') as f: f.write(encrypt(data, password))
    return dst


def decrypt_file(src, dst, password):
    with open(src, 'rb') as f: blob = f.read()
    with open(dst, 'wb') as f: f.write(decrypt(blob, password))
    return dst


# ------------------------------------------------------------ Windows DPAPI
def _dpapi(data: bytes, protect=True) -> bytes:
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]
    buf = ctypes.create_string_buffer(data, len(data))
    bi = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))); bo = BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if not fn(ctypes.byref(bi), None, None, None, None, 0x01, ctypes.byref(bo)):
        raise OSError('DPAPI failed')
    try:
        return ctypes.string_at(bo.pbData, bo.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(bo.pbData)


def protect(s: str) -> str:
    """Gizli ayarı bu Windows kullanıcısına bağlı şifreli metne çevirir."""
    if not s or s.startswith(('dpapi:', 'lk:')): return s
    try:
        if sys.platform.startswith('win'):
            return 'dpapi:' + base64.b64encode(_dpapi(s.encode(), True)).decode()
    except Exception:
        pass
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        n = os.urandom(12)
        return 'lk:' + base64.b64encode(n + AESGCM(local_key()).encrypt(n, s.encode(), b'pla')).decode()
    except Exception:
        return s


def unprotect(s: str) -> str:
    if not s: return s
    try:
        if s.startswith('dpapi:'):
            return _dpapi(base64.b64decode(s[6:]), False).decode()
        if s.startswith('lk:'):
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            b = base64.b64decode(s[3:])
            return AESGCM(local_key()).decrypt(b[:12], b[12:], b'pla').decode()
    except Exception:
        return ''
    return s


def local_key() -> bytes:
    """Cihaz anahtarı (yerel arşiv şifrelemesi için). Windows'ta DPAPI ile korunur."""
    from .paths import data_dir
    p = os.path.join(data_dir(), 'local.key')
    if os.path.exists(p):
        raw = open(p, 'rb').read()
        if raw.startswith(b'DP'):
            try: return _dpapi(raw[2:], False)
            except Exception: pass
        elif len(raw) == 32:
            return raw
    k = os.urandom(32)
    try:
        if sys.platform.startswith('win'):
            open(p, 'wb').write(b'DP' + _dpapi(k, True)); return k
    except Exception:
        pass
    with open(p, 'wb') as f: f.write(k)
    try: os.chmod(p, 0o600)
    except Exception: pass
    return k


def encrypt_local_file(src, dst):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    n = os.urandom(12)
    with open(src, 'rb') as f: data = f.read()
    with open(dst, 'wb') as f: f.write(b'PXLOC1' + n + AESGCM(local_key()).encrypt(n, data, b'log'))
    return dst


def open_local_file(path):
    """Şifreli arşiv kopyasını geçici dosyaya açar; düz dosyayı olduğu gibi döner."""
    with open(path, 'rb') as f: head = f.read(6)
    if head != b'PXLOC1': return path
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import tempfile
    blob = open(path, 'rb').read()
    data = AESGCM(local_key()).decrypt(blob[6:18], blob[18:], b'log')
    name = os.path.basename(path)[:-6] if path.endswith('.pxloc') else os.path.basename(path)
    d = os.path.join(tempfile.gettempdir(), 'PixhawkLogAnaliz'); os.makedirs(d, exist_ok=True)
    out = os.path.join(d, name)
    with open(out, 'wb') as f: f.write(data)
    return out


# ------------------------------------------------------------ kullanıcılar
def hash_pw(pw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    return base64.b64encode(salt).decode() + '$' + base64.b64encode(hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 200_000)).decode()


def check_pw(pw: str, h: str) -> bool:
    try:
        s, d = h.split('$'); return hmac.compare_digest(hash_pw(pw, base64.b64decode(s)).split('$')[1], d)
    except Exception:
        return False


def add_user(archive, name, role, pw):
    uid = uuid.uuid4().hex[:10]
    archive.rec_put('user', uid, {'id': uid, 'name': name.strip(), 'role': role if role in ROLES else 'student', 'pw': hash_pw(pw),
                                  'created': time.strftime('%Y-%m-%d')})
    return uid


def users(archive):
    return archive.rec_list('user')


def login(archive, name, pw):
    for u in users(archive):
        if u['name'].lower() == (name or '').strip().lower() and check_pw(pw, u.get('pw', '')):
            return u
    return None
