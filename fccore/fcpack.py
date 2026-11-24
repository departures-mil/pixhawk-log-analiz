"""fccore.fcpack — PyInstaller one-dir klasörünün BELİRLENİMCİ zip'i (win-app kanalı).

Aynı dosyalar → bayt bayt aynı zip (sıralı yollar, sabit tarih/izin, create_system=0, deflate düzey 6).
Böylece istemci kurulu klasörden önceki sürümün zip'ini yeniden üretebilir ve CI'ın ürettiği FCD1 yamasını
ona uygulayabilir (yama başlığındaki kaynak SHA-256 eşleşmezse istemci kendiliğinden tam dosyaya geçer).

CI:   python -m fccore.fcpack dist/PixhawkLogAnaliz PixhawkLogAnaliz-win-app.zip
"""
import os
import sys
import zipfile
import zlib

SKIP_DIRS = {'__pycache__'}
SKIP_PREFIX = ('.fc-', '.fcdelta-')
DATE = (1980, 1, 1, 0, 0, 0)


def files(root):
    out = []
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(SKIP_PREFIX)]
        for f in fs:
            if f.startswith(SKIP_PREFIX) or f.endswith('.pyc') and '__pycache__' in d:
                continue
            p = os.path.join(d, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            out.append(os.path.relpath(p, root).replace(os.sep, '/'))
    return sorted(out, key=lambda s: s.encode('utf-8'))


def pack(root, out_path, on_progress=None):
    names = files(root)
    total = sum(os.path.getsize(os.path.join(root, n)) for n in names) or 1
    done = 0
    tmp = out_path + '.part'
    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for n in names:
            zi = zipfile.ZipInfo(n, DATE)
            zi.create_system = 0
            zi.external_attr = 0
            zi.compress_type = zipfile.ZIP_DEFLATED
            p = os.path.join(root, n)
            with open(p, 'rb') as src, z.open(zi, 'w', force_zip64=os.path.getsize(p) > 0x7fff0000) as dst:
                while True:
                    b = src.read(1 << 20)
                    if not b:
                        break
                    dst.write(b)
                    done += len(b)
                    if on_progress:
                        on_progress(done, total)
    os.replace(tmp, out_path)
    return out_path


def safe_extract(zip_path, dest):
    """Yol kaçışına (../, mutlak yol, sürücü harfi) izin vermeden açar."""
    os.makedirs(dest, exist_ok=True)
    base = os.path.realpath(dest)
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            n = info.filename.replace('\\', '/')
            if n.startswith('/') or ':' in n or '..' in n.split('/'):
                raise ValueError('BAD_ZIP_PATH')
            target = os.path.realpath(os.path.join(base, n))
            if not (target == base or target.startswith(base + os.sep)):
                raise ValueError('BAD_ZIP_PATH')
        z.extractall(base)


def main(argv=None):
    """python -m fccore.fcpack <klasör> <zip>. Windows CI konsolu (cp1252) Türkçe harfte çökmesin: stdout UTF-8'e
    çevrilir (olmazsa yerine '?'), durum satırı yalnız ASCII."""
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    pack(argv[0], argv[1])
    print('written', argv[1], 'zlib', zlib.ZLIB_RUNTIME_VERSION)
    return 0


if __name__ == '__main__':
    sys.exit(main())
