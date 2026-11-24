"""Asistan Agent bağlantısı (app/ui/fc_agent.py = ortak-cekirdek/python/fc_agent.py)."""
AJAN = None
WIN = None


def _ai():
    try:
        s = WIN.settings
        prov = s.get('ai_provider', 'gemini')
        key = s.get('gemini_key') if prov == 'gemini' else s.get('api_key')
        return {'provider': prov, 'key': key} if key and prov in ('gemini', 'anthropic') else None
    except Exception:
        return None


def kur():
    global AJAN
    try:
        from . import fc_agent
        from .i18n import lang
        from ..version import VERSION
        AJAN = fc_agent.Agent('pixhawk-log-analiz', VERSION, lang=lang, ai=_ai, sync=False)
    except Exception:
        AJAN = None
    return AJAN


def baslat(app, win):
    global WIN
    WIN = win
    if AJAN is not None:
        try:
            AJAN.start(app, win)
        except Exception:
            pass
