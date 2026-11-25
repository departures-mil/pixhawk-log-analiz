"""Güncelleme yapıştırıcısı: kurulum exe'si sessiz + yeniden açma, takas betiği kurulum klasöründe çalışmaz, fcpack belirlenimci."""
import hashlib, os, sys, subprocess


def test_setup_spawn_runs_inno_silently(monkeypatch, tmp_path):
    from app.ui import kabuk
    calls = []

    class P:
        def __init__(self, args, **kw): calls.append((args, kw))
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setattr(subprocess, 'Popen', P)
    setup = tmp_path / 'PixhawkLogAnaliz_Setup_1.2.0.exe'; setup.write_bytes(b'MZ')
    kabuk._spawn(str(tmp_path))([str(setup)])
    args, kw = calls[0]
    assert args[:2] == ['cmd.exe', '/c'] and kw['cwd'] == str(tmp_path)
    body = (tmp_path / 'kurulum.cmd').read_text(encoding='utf-8')
    for a in ('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', str(setup), '--fc-updated'):
        assert a in body


def test_swap_script_spawned_outside_install_dir(monkeypatch, tmp_path):
    from app.ui import kabuk
    calls = []
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setattr(subprocess, 'Popen', lambda args, **kw: calls.append((args, kw)))

    class SI:
        dwFlags = 0; wShowWindow = 1
    monkeypatch.setattr(subprocess, 'STARTUPINFO', SI, raising=False)
    kabuk._spawn(str(tmp_path))(['cmd.exe', '/c', str(tmp_path / 'takas-1.2.0.cmd')])
    kw = calls[0][1]
    assert kw['cwd'] == str(tmp_path)
    # DETACHED_PROCESS yok (her komut ayrı pencere açıp `find` takılıyordu), gizli konsol var
    assert not (kw['creationflags'] & 0x00000008) and kw['creationflags'] & 0x08000000
    assert kw['startupinfo'].wShowWindow == 0


def test_swap_script_failure_reopens_old(tmp_path, monkeypatch):
    from fccore import updater
    monkeypatch.setattr(sys, 'platform', 'win32')
    p = updater.write_swap_script(str(tmp_path), 1, 'dir', r'C:\A\App', r'C:\A\App.new', r'C:\A\App\x.exe', str(tmp_path / 'm'), '1.2.0')
    s = open(p, encoding='utf-8').read()
    hata = s[s.index(':hata'):]
    assert '--fc-update-failed=1.2.0' in hata


def test_fcpack_deterministic(tmp_path):
    from fccore import fcpack
    d = tmp_path / 'PixhawkLogAnaliz'; (d / '_internal' / 'app').mkdir(parents=True)
    (d / 'PixhawkLogAnaliz.exe').write_bytes(b'MZ' * 1000)
    (d / '_internal' / 'app' / 'x.json').write_text('{"a":1}')
    a, b = tmp_path / 'a.zip', tmp_path / 'b.zip'
    fcpack.pack(str(d), str(a))
    os.utime(d / 'PixhawkLogAnaliz.exe', (1, 1))         # tarih farkı zip'i değiştirmez
    fcpack.pack(str(d), str(b))
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    assert h(a) == h(b)


def test_channel_choice(monkeypatch, tmp_path):
    from app.ui import kabuk
    one = tmp_path / 'kurulu'; (one / '_internal').mkdir(parents=True)
    assert kabuk._installed_dir(str(one)) is True
    assert kabuk._installed_dir(str(tmp_path)) is False   # taşınabilir tek exe → win-exe
