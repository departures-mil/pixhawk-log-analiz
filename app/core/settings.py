"""Kullanıcı ayarları (JSON, %APPDATA%/PixhawkLogAnaliz/settings.json)."""
from __future__ import annotations
import json, os, uuid
from .paths import data_dir

DEFAULTS = {
    'lang': 'tr',
    'api_key': '',
    'model': 'claude-opus-5-5',
    'effort': 'medium',
    'online': True,            # İnternet varsa yapay zekâ + çevrimiçi harita
    'map_src': 'osm',
    'report_lang': 'tr',
    'report_fmt': 'pdf',
    'report_ai': True,
    'template': 'default',
    'templates': {},           # ad -> letterhead dict
    'gh_token': '',
    'gist_id': '',
    'last_sync': '',
    'device_id': '',
    'device_name': '',
    'archive_copy_logs': True,
    'archive_copy_max_mb': 200,
    'auto_update_check': True,
    'param_tx_cache': {},      # 'NAME|lang' -> [name, desc] (AI ile çevrilen parametreler)
    'practice_best': 0,
    # v1.0.2
    'ai_provider': 'gemini',   # gemini (ücretsiz katman) / anthropic
    'gemini_key': '',
    'gemini_model': 'gemini-flash-latest',
    'gemini_models': [], 'claude_models': [],
    'profile': 'auto',
    'report_sections': None,   # [[bölüm, açık], …]
    'report_mode': 'long',
    'watch_enabled': True, 'watch_dirs': [], 'auto_analyze': False,
    'encrypt_local': False, 'require_login': False,
    'weather_online': True,
    'cache_max_mb': 3000,
}
SECRETS = ('api_key', 'gemini_key', 'gh_token')


class Settings(dict):
    def __init__(self):
        super().__init__(DEFAULTS)
        self.path = os.path.join(data_dir(), 'settings.json')
        try:
            with open(self.path, encoding='utf-8') as f:
                self.update(json.load(f))
        except Exception:
            pass
        from .security import unprotect
        for k in SECRETS:
            if self.get(k): self[k] = unprotect(self[k])
        if not self.get('device_id'):
            self['device_id'] = uuid.uuid4().hex
        if not self.get('device_name'):
            import platform
            self['device_name'] = os.environ.get('COMPUTERNAME') or platform.node() or 'PC'
        if 'default' not in self['templates']:
            from .report import DEFAULT_LH
            self['templates']['default'] = dict(DEFAULT_LH)
        # v1.0.1: gömülü hazır antet (Savunma Bakanlığı – Sabit Kanat) bir kez eklenir ve seçilir
        if not self.get('preset_lh_v1'):
            from .letterhead import PRESET_NAME, PRESET
            self['templates'].setdefault(PRESET_NAME, dict(PRESET))
            self['template'] = PRESET_NAME
            self['preset_lh_v1'] = True

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + '.tmp'
        from .security import protect
        out = dict(self)
        for k in SECRETS:
            if out.get(k): out[k] = protect(out[k])
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def letterhead(self):
        return self['templates'].get(self.get('template') or 'default') or self['templates']['default']
