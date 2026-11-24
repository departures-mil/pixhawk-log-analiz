"""KÖPRÜ: kurulu v1.0.x programları GitHub API releases/latest okur (latest.json bilmez).
Yeni release'in asset listesiyle eski güncelleyici kodu (tests/legacy/updater_v107.py = v1.0.7'nin birebir kopyası)
çalıştırılır: Setup exe'yi bulup sessiz kurmalı; v1.0.0 ise listedeki ilk .exe'yi (taşınabilir) almalı."""
import io, json, os, sys, types
import pytest

NEW = '1.1.0'


def release_json(version=NEW):
    """reusable-release.yml'in yükleyeceği asset'ler (release.yml files: ile aynı adlar, sıralı)."""
    names = sorted([f'PixhawkLogAnaliz-{version}-win-app.zip', 'PixhawkLogAnaliz.exe', f'PixhawkLogAnaliz_Setup_{version}.exe',
                    'latest.json', 'PixhawkLogAnaliz-win-app.patch-from-1.0.9.bin'])
    return {'tag_name': 'v' + version, 'body': 'notlar',
            'assets': [{'name': n, 'size': 1000 + i, 'browser_download_url': f'https://github.com/departures-mil/pixhawk-log-analiz/releases/download/v{version}/{n}'}
                       for i, n in enumerate(names)]}


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


@pytest.fixture
def legacy(monkeypatch):
    from legacy import updater_v107 as U
    seen = []

    def fake_open(req, timeout=0):
        url = req.full_url if hasattr(req, 'full_url') else req
        seen.append(url)
        if url.endswith('/releases/latest'):
            return _Resp(json.dumps(release_json()).encode())
        raise AssertionError('beklenmeyen istek ' + url)
    monkeypatch.setattr(U.urllib.request, 'urlopen', fake_open)
    U._seen = seen
    return U


def test_old_updater_finds_new_setup(legacy):
    info = legacy.check()
    assert info and info['version'] == NEW
    assert info['kind'] == 'setup' and info['name'] == f'PixhawkLogAnaliz_Setup_{NEW}.exe'
    assert info['patch'] is None                          # delta-index.json yok → tam kurulum (dev modunda zaten yok)


def test_old_installed_updater_ignores_new_patches(legacy, monkeypatch, tmp_path):
    # Kurulu (frozen) v1.0.7: delta-index.json yayınlanmadığı için eski biçim yamaya girmez, Setup'a gider
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    exe = tmp_path / 'PixhawkLogAnaliz.exe'; exe.write_bytes(b'x'); (tmp_path / 'unins000.exe').write_bytes(b'x')
    monkeypatch.setattr(sys, 'executable', str(exe))
    info = legacy.check()
    assert info['kind'] == 'setup' and info['patch'] is None


def test_old_updater_runs_setup_silently_then_reopens(legacy, monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    exe = tmp_path / 'PixhawkLogAnaliz.exe'; exe.write_bytes(b'x'); (tmp_path / 'unins000.exe').write_bytes(b'x')
    monkeypatch.setattr(sys, 'executable', str(exe))
    got = {}
    monkeypatch.setattr(legacy, '_launch_script', lambda body, nf: got.update(body=body))
    setup = tmp_path / f'PixhawkLogAnaliz-Setup-{NEW}.exe'; setup.write_bytes(b'MZ')
    assert legacy.apply_and_restart(str(setup)) is True
    assert '/VERYSILENT' in got['body'] and str(setup) in got['body'] and '--updated' in got['body']


def test_v100_picks_first_exe_portable():
    # v1.0.0 güncelleyicisi: listedeki ilk .exe (ada göre sıralı ya da yükleme sırası; ikisinde de taşınabilir önce)
    names = [a['name'] for a in release_json()['assets'] if a['name'].lower().endswith('.exe')]
    assert names[0] == 'PixhawkLogAnaliz.exe'


def test_new_app_accepts_old_restart_flag():
    # eski betik yeni programı '--updated' ile açar; main() bunu dosya sanmamalı
    from app import main
    src = open(main.__file__, encoding='utf-8').read()
    assert "os.path.isfile(a)" in src


def test_new_manifest_plan_for_new_clients():
    from fccore.updater import plan
    sha = 'a' * 64
    man = {'schema': 1, 'app': 'pixhawk-log-analiz', 'version': '1.2.0', 'minVersion': '1.0.0', 'notes': {},
           'assets': {'win-app': {'file': 'PixhawkLogAnaliz-1.2.0-win-app.zip', 'size': 100, 'sha256': sha,
                                  'patches': {NEW: {'file': 'PixhawkLogAnaliz-win-app.patch-from-1.1.0.bin', 'size': 10, 'sha256': sha}}},
                      'win-setup': {'file': 'PixhawkLogAnaliz_Setup_1.2.0.exe', 'size': 200, 'sha256': sha},
                      'win-exe': {'file': 'PixhawkLogAnaliz.exe', 'size': 150, 'sha256': sha}}}
    p = plan(man, {'repo': 'pixhawk-log-analiz', 'app': 'pixhawk-log-analiz', 'version': NEW, 'channel': 'win-app', 'setupChannel': 'win-setup'})
    assert p['mode'] == 'patch' and p['setup']['file'].startswith('PixhawkLogAnaliz_Setup_')
    p2 = plan(man, {'repo': 'pixhawk-log-analiz', 'app': 'pixhawk-log-analiz', 'version': NEW, 'channel': 'win-exe', 'setupChannel': 'win-setup'})
    assert p2['channel'] == 'win-exe' and p2['mode'] == 'full'
