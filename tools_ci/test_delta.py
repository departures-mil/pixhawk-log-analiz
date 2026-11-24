"""Delta (yama) güncelleme testleri: üret → uygula → SHA-256 ile birebir doğrula; bozuk/uyumsuz durumda hata."""
import os, random, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core import delta


def _w(p, b):
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(b)


def run():
    rnd = random.Random(7); root = tempfile.mkdtemp(); ok = 0
    try:
        old, new = os.path.join(root, 'old'), os.path.join(root, 'new')
        big = bytes(rnd.getrandbits(8) for _ in range(600_000))
        _w(f'{old}/PixhawkLogAnaliz.exe', big); _w(f'{new}/PixhawkLogAnaliz.exe', big[:1000] + b'NEWCODE' * 50 + big[1000:])
        _w(f'{old}/_internal/same.dll', b'D' * 200_000); _w(f'{new}/_internal/same.dll', b'D' * 200_000)
        _w(f'{old}/_internal/gone.pyd', b'x'); _w(f'{new}/_internal/app/data/yeni.json', b'{"a":1}')
        _w(f'{old}/unins000.exe', b'u'); _w(f'{old}/unins000.dat', b'u')
        out = os.path.join(root, 'patch-from-1.0.5.zip')
        st = delta.make_patch(old, new, out, '1.0.5', '1.0.6')
        assert st['changed'] == 1 and st['added'] == 1 and st['deleted'] == 1 and st['unchanged'] == 1, st
        assert st['size'] < 0.7 * 600_000, st
        base = os.path.join(root, 'base'); shutil.copytree(old, base)
        meta = delta.stage(base, out, os.path.join(root, 'stg'), expect_from='1.0.5', expect_to='1.0.6')
        delta.apply_inplace(base, os.path.join(root, 'stg'), meta)
        delta.verify_tree(base, delta.manifest(new)); ok += 1
        assert delta.sha256_file(f'{base}/PixhawkLogAnaliz.exe') == delta.sha256_file(f'{new}/PixhawkLogAnaliz.exe'); ok += 1
        assert os.path.isfile(f'{base}/unins000.exe'); ok += 1          # kaldırıcıya dokunulmaz
        # kurulu dosya kullanıcı tarafından değişmişse → DeltaError (tam dosyaya geçilir)
        b2 = os.path.join(root, 'b2'); shutil.copytree(old, b2); _w(f'{b2}/_internal/same.dll', b'Z' * 10)
        try: delta.stage(b2, out, os.path.join(root, 's2')); raise AssertionError('mismatch not detected')
        except delta.DeltaError: ok += 1
        # yanlış sürümden yama → DeltaError
        try: delta.stage(base, out, os.path.join(root, 's3'), expect_from='1.0.4'); raise AssertionError('version not checked')
        except delta.DeltaError: ok += 1
        # taşınabilir tek dosya
        po = os.path.join(root, 'po'); pn = os.path.join(root, 'pn')
        _w(f'{po}/PixhawkLogAnaliz.exe', big); _w(f'{pn}/PixhawkLogAnaliz.exe', big[:5000] + b'Q' * 99 + big[5000:])
        _w(f'{po}/kullanici_notu.txt', b'dokunma')
        out2 = os.path.join(root, 'p2.zip')
        delta.make_patch(po, pn, out2, '1.0.5', '1.0.6', kind='file', files=['PixhawkLogAnaliz.exe'])
        m = delta.stage(po, out2, os.path.join(root, 's4'))
        assert m['delete'] == [] and m['kind'] == 'file'; ok += 1
        print(f'delta: {ok}/6 OK, tree patch {st["size"]} B')
        return ok == 6
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(0 if run() else 1)
