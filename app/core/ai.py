"""Yapay zekâ sağlayıcıları: Anthropic Claude ve Google Gemini.

Herkes kendi anahtarını kullanır (programın içinde ortak anahtar YOKTUR). Gemini'nin ücretsiz katmanı vardır;
anahtar Google AI Studio'dan birkaç tıkla alınır. Danışman, rapor yorumu ve çeviri iki sağlayıcıyla da çalışır.
Model listesi sağlayıcıdan otomatik çekilir; geçersiz model seçilirse en uygun model otomatik kullanılır.
"""
from __future__ import annotations
import json, re, time, urllib.request, urllib.error

PROVIDERS = {
    'gemini': {'name': 'Google Gemini', 'key_url': 'https://aistudio.google.com/apikey', 'prefix': ('AIza', 'AQ.'),
               'default': 'gemini-flash-latest', 'fallback': ['gemini-flash-latest', 'gemini-pro-latest']},
    'anthropic': {'name': 'Anthropic Claude', 'key_url': 'https://console.anthropic.com/settings/keys', 'prefix': ('sk-ant-',),
                  'default': 'claude-sonnet-5-5', 'fallback': ['claude-sonnet-5-5', 'claude-opus-5-5', 'claude-haiku-5-5', 'claude-fable-5-2']},
}
GEM = 'https://generativelanguage.googleapis.com/v1beta'


def detect_provider(key: str):
    k = (key or '').strip()
    if k.startswith('sk-ant-'): return 'anthropic'
    if k.startswith(('AIza', 'AQ.')): return 'gemini'
    return None


def find_key(text: str):
    """Panodaki metinden API anahtarı yakala (sağlayıcı, anahtar)."""
    t = text or ''
    m = re.search(r'sk-ant-[A-Za-z0-9_\-]{20,}', t)
    if m: return 'anthropic', m.group(0)
    m = re.search(r'\b(AIza[0-9A-Za-z_\-]{30,}|AQ\.[0-9A-Za-z_\-\.]{20,})', t)
    if m: return 'gemini', m.group(1)
    return None, None


def _http(method, url, key, body=None, timeout=120, retries=3):
    """Geçici hatalarda (503 yoğunluk, 500, zaman aşımı) artan beklemeyle yeniden dener."""
    for i in range(retries + 1):
        try:
            return _http1(method, url, key, body, timeout)
        except RuntimeError as e:
            if getattr(e, 'status', 0) in (500, 502, 503, 504) and i < retries:
                time.sleep((2, 5, 10, 20)[i]); continue
            raise
        except (TimeoutError, OSError) as e:
            if i < retries and not isinstance(e, urllib.error.HTTPError):
                time.sleep((2, 5, 10, 20)[i]); continue
            raise


def _http1(method, url, key, body=None, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': key, 'User-Agent': 'PixhawkLogAnaliz'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or '{}'), dict(r.headers)
    except urllib.error.HTTPError as e:
        txt = e.read().decode('utf-8', 'replace')
        try: d = json.loads(txt)
        except Exception: d = {'error': {'message': txt[:400]}}
        err = d.get('error') or {}
        ex = RuntimeError(f"{e.code}: {err.get('message', '')[:300]}")
        ex.status = e.code; ex.details = err.get('details') or []
        raise ex


# ------------------------------------------------------------------ modeller
def list_models(provider, key):
    if provider == 'gemini':
        d, _ = _http('GET', GEM + '/models?pageSize=200', key, timeout=30)
        out = []
        for m in d.get('models', []):
            n = m.get('name', '').replace('models/', '')
            if 'generateContent' in (m.get('supportedGenerationMethods') or []) and n.startswith('gemini') and \
                    not any(x in n for x in ('tts', 'image', 'embedding', 'audio', 'live', 'robotics', 'computer-use')):
                out.append(n)
        return out
    import anthropic
    c = anthropic.Anthropic(api_key=key, timeout=30)
    return [m.id for m in c.models.list(limit=100).data]


def candidates(provider, models, wanted=None):
    """Denenecek modeller (en uygun önce)."""
    out = []
    if wanted and wanted in models: out.append(wanted)
    out += [m for m in PROVIDERS[provider]['fallback'] if m in models]
    if provider == 'gemini':
        def ver(m, kind):
            x = re.match(r'gemini-(\d+(?:\.\d+)?)-' + kind + '$', m)
            return float(x.group(1)) if x else -1
        out += sorted([m for m in models if ver(m, 'flash') > 0], key=lambda m: -ver(m, 'flash'))
        out += [m for m in ('gemini-flash-lite-latest',) if m in models]
        out += sorted([m for m in models if ver(m, 'flash-lite') > 0], key=lambda m: -ver(m, 'flash-lite'))
    out += models
    return list(dict.fromkeys(out)) or [PROVIDERS[provider]['default']]


def best_model(provider, models, wanted=None):
    return candidates(provider, models, wanted)[0]


def _gem_ping(key, m):
    return _http('POST', f'{GEM}/models/{m}:generateContent', key, {'contents': [{'role': 'user', 'parts': [{'text': 'ping'}]}],
                                                                   'generationConfig': {'maxOutputTokens': 16}}, timeout=60, retries=1)


def test(provider, key, model, usage=None):
    """Anahtarı dener; (model listesi, çalışan model) döner. Model yoğun/kotası dolu ise sıradakini dener."""
    models = list_models(provider, key)
    if provider == 'gemini':
        last = None
        for m in candidates(provider, models, model)[:6]:
            try:
                d, h = _gem_ping(key, m)
            except RuntimeError as e:
                last = e
                if getattr(e, 'status', 0) == 429 and usage: usage.note_quota('gemini', getattr(e, 'details', []))
                if getattr(e, 'status', 0) in (400, 404, 429, 500, 503): continue
                raise
            um = d.get('usageMetadata', {})
            if usage: usage.add_generic('gemini', um.get('promptTokenCount', 0), um.get('candidatesTokenCount', 0), {})
            return models, m
        raise last or RuntimeError('no model')
    m = best_model(provider, models, model)
    import anthropic
    c = anthropic.Anthropic(api_key=key, timeout=60)
    raw = c.messages.with_raw_response.create(model=m, max_tokens=16, messages=[{'role': 'user', 'content': 'ping'}])
    if usage: usage.add(raw.parse().usage, raw.headers)
    return models, m


# --------------------------------------------------------------- Gemini danışman
def _gem_schema(sch):
    """JSON şemasını Gemini OpenAPI alt kümesine çevir."""
    if not isinstance(sch, dict): return sch
    out = {}
    for k, v in sch.items():
        if k == 'type': out['type'] = str(v).upper()
        elif k == 'properties':
            if v: out['properties'] = {pk: _gem_schema(pv) for pk, pv in v.items()}
        elif k == 'items': out['items'] = _gem_schema(v)
        elif k == 'required':
            if v: out['required'] = v
        elif k in ('description', 'enum', 'format', 'nullable'): out[k] = v
    return out


class GeminiAdvisor:
    def __init__(self, A, api_key, model='gemini-flash-latest', lang='tr', usage=None, effort='medium'):
        from .advisor import LogTools, TOOLS
        self.key = api_key; self.model = model or PROVIDERS['gemini']['default']; self.lang = lang; self.usage = usage
        self.effort = effort; self.A = A
        self.tools = LogTools(A) if A is not None else None
        self.decl = []
        for t in TOOLS:
            d = {'name': t['name'], 'description': t['description']}
            ps = _gem_schema(t['input_schema'])
            if ps.get('properties'): d['parameters'] = ps
            self.decl.append(d)
        self.contents = []

    def _gen(self, body):
        tried = []
        while True:
            try:
                d, h = _http('POST', f'{GEM}/models/{self.model}:generateContent', self.key, body, retries=1)
                break
            except RuntimeError as e:
                st = getattr(e, 'status', 0)
                if st == 429 and self.usage: self.usage.note_quota('gemini', getattr(e, 'details', []))
                if st not in (404, 429, 500, 503) or len(tried) >= 4: raise
                tried.append(self.model)
                alt = [m for m in candidates('gemini', list_models('gemini', self.key)) if m not in tried]
                if not alt: raise
                self.model = alt[0]
        um = d.get('usageMetadata', {})
        if self.usage: self.usage.add_generic('gemini', um.get('promptTokenCount', 0), um.get('candidatesTokenCount', 0) + um.get('thoughtsTokenCount', 0), {})
        return d

    def _cfg(self, max_tokens=8192):
        g = {'maxOutputTokens': max_tokens}
        if '2.5' in self.model:
            b = {'low': 1024, 'medium': 4096, 'high': 12000, 'max': -1}.get(self.effort, 4096)
            if 'pro' in self.model and b == 0: b = 1024
            g['thinkingConfig'] = {'thinkingBudget': b}
        return g

    def ask(self, question, on_status=None, max_rounds=8):
        from .advisor import SYSTEM, LANG_NAME
        system = SYSTEM.replace('{lang}', LANG_NAME.get(self.lang, 'Turkish'))
        self.contents.append({'role': 'user', 'parts': [{'text': question}]})
        for rnd in range(max_rounds):
            body = {'systemInstruction': {'parts': [{'text': system}]}, 'contents': self.contents,
                    'tools': [{'functionDeclarations': self.decl}], 'generationConfig': self._cfg()}
            if rnd >= max_rounds - 1:   # son tur: araç çağırmadan elindeki bilgilerle cevapla
                body['toolConfig'] = {'functionCallingConfig': {'mode': 'NONE'}}
            d = self._gen(body)
            cand = (d.get('candidates') or [{}])[0]
            content = cand.get('content') or {'role': 'model', 'parts': []}
            content['role'] = 'model'
            self.contents.append(content)
            calls = [p['functionCall'] for p in content.get('parts', []) if 'functionCall' in p]
            if not calls:
                txt = ''.join(p.get('text', '') for p in content.get('parts', []) if not p.get('thought'))
                if not txt and cand.get('finishReason') in ('SAFETY', 'RECITATION', 'PROHIBITED_CONTENT'):
                    return {'tr': 'Model bu isteği yanıtlamadı.', 'en': 'The model did not answer this request.', 'ar': 'لم يُجب النموذج على هذا الطلب.'}[self.lang]
                return txt.strip()
            parts = []
            for c in calls:
                if on_status: on_status(c.get('name'))
                try:
                    fn = getattr(self.tools, c['name']); inp = dict(c.get('args') or {})
                    if c['name'] == 'events': inp = dict(inp, lang='en')
                    res = json.loads(json.dumps(fn(**inp), ensure_ascii=False, default=float))
                except Exception as e:
                    res = {'error': str(e)}
                parts.append({'functionResponse': {'name': c['name'], 'response': {'result': res}}})
            self.contents.append({'role': 'user', 'parts': parts})
        return {'tr': 'Cevap için çok fazla adım gerekti; soruyu daraltın.', 'en': 'Too many steps were needed; narrow the question.', 'ar': 'تطلب الأمر خطوات كثيرة؛ ضيّق السؤال.'}[self.lang]

    def translate(self, text, target):
        from .advisor import LANG_NAME
        d = self._gen({'systemInstruction': {'parts': [{'text': 'You are a professional aviation/UAV technical translator. Translate faithfully, keep ArduPilot parameter names, units and numbers unchanged. Output only the translation.'}]},
                       'contents': [{'role': 'user', 'parts': [{'text': f'Translate into {LANG_NAME[target]}:\n\n{text}'}]}],
                       'generationConfig': self._cfg(4000)})
        c = (d.get('candidates') or [{}])[0].get('content') or {}
        return ''.join(p.get('text', '') for p in c.get('parts', []) if not p.get('thought')).strip()


# ------------------------------------------------------------------ fabrika
def current(settings):
    """(sağlayıcı, anahtar, model) — ayarlardan."""
    prov = settings.get('ai_provider') or 'gemini'
    key = (settings.get('gemini_key') if prov == 'gemini' else settings.get('api_key')) or ''
    model = settings.get('gemini_model') if prov == 'gemini' else settings.get('model')
    return prov, key.strip(), (model or PROVIDERS[prov]['default'])


def available(settings):
    prov, key, _ = current(settings)
    return bool(key) and settings.get('online', True)


def make_advisor(A, settings, lang, usage):
    prov, key, model = current(settings)
    if not key: raise RuntimeError('no key')
    if prov == 'gemini':
        return GeminiAdvisor(A, key, model, lang, usage, settings.get('effort', 'medium'))
    from .advisor import OnlineAdvisor
    return OnlineAdvisor(A, key, model, lang, usage, settings.get('effort', 'medium'))


def translate(settings, usage, text, target):
    prov, key, model = current(settings)
    if prov == 'gemini':
        return GeminiAdvisor(None, key, model, 'en', usage, 'low').translate(text, target)
    from .advisor import OnlineAdvisor
    a = OnlineAdvisor.__new__(OnlineAdvisor)
    import anthropic
    a.client = anthropic.Anthropic(api_key=key, max_retries=2, timeout=180); a.model = model; a.usage = usage
    return OnlineAdvisor.translate(a, text, target)
