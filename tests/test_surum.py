"""Sürüm, çekirdek kopyası, kurulum ve CI tutarlılığı."""
import json, os, re
from conftest import ROOT


def rd(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8-sig') as f:
        return f.read()


def test_version_semver_and_news():
    from app.version import VERSION
    from app.news import NEWS, notes_for
    assert re.fullmatch(r'\d+\.\d+\.\d+', VERSION)
    assert NEWS[0]['v'] == VERSION, 'app/news.py: yeni sürümün notu EN ÜSTTE olmalı'
    n = notes_for(VERSION)
    assert all(n[k].strip() for k in ('tr', 'en', 'ar'))


def test_core_vendored():
    v = rd('cekirdek', 'VERSION')
    assert 'ortak-cekirdek' in v and re.search(r'\b[0-9a-f]{40}\b', v)
    import fccore
    assert os.path.isfile(os.path.join(os.path.dirname(fccore.__file__), 'fonts', 'Inter-400.ttf'))


def test_installer_per_user_and_uninstaller_outside_app():
    s = rd('installer', 'setup.iss')
    assert 'PrivilegesRequired=lowest' in s and 'PrivilegesRequiredOverridesAllowed' not in s
    assert r'DefaultDirName={localappdata}\Programs\Pixhawk Log Analiz' in s
    assert 'UninstallFilesDir={app}-uninstall' in s
    assert 'OutputBaseFilename=PixhawkLogAnaliz_Setup_{#AppVersion}' in s   # eski güncelleyiciler 'setup' + '.exe' arar
    for l in ('Turkish.isl', 'Default.isl', 'Arabic.isl'):
        assert l in s


def test_specs_bundle_core():
    for f in ('PixhawkLogAnaliz.spec', 'PixhawkLogAnaliz_dir.spec'):
        s = rd(f)
        assert "collect_data_files('fccore')" in s and 'PySide6.QtSvg' in s
        assert "'PySide6.QtSvg'" not in s.split('excl =')[1]


def test_release_workflow_gates():
    s = rd('.github', 'workflows', 'release.yml')
    assert 'reusable-release.yml@main' in s
    assert re.search(r'needs:\s*\[test,\s*build\]', s)
    assert 'selftest.py' in s and 'unins000.exe' in s and 'pytest' in s
    assert 'win-app=' in s and 'win-setup=' in s and 'win-exe=' in s


def test_notes_json_tool(tmp_path):
    import subprocess, sys
    out = tmp_path / 'n.json'
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'tools_ci', 'release_notes.py'), str(out)])
    d = json.loads(out.read_text(encoding='utf-8'))
    assert set(d) == {'tr', 'en', 'ar'}
