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
# Anahtarsız ücretsiz yedek: kimsenin kişisel limitinden yemez; hız sınırı vardır. Anahtar girilince otomatik olarak Gemini/Claude kullanılır.
PROVIDERS['free'] = {'name': 'Ücretsiz (anahtarsız)', 'key_url': '', 'prefix': (), 'default': 'openai',
                     'fallback': ['openai', 'openai-fast', 'mistral'],
                     'urls': ['https://text.pollinations.ai/openai']}


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
    if provider == 'free':
        ms = PROVIDERS['free']['fallback']; last = None
        for m in [model] + [x for x in ms if x != model] if model else ms:
            try:
                FreeAdvisor(None, m, 'en', usage).chat('Reply with one word.', 'ping', 16); return ms, m
            except Exception as e:
                last = e
        raise last or RuntimeError('free AI unavailable')
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
        d = self._gen({'systemInstruction': {'parts': [{'text': 'You are a professional aviation/UAV technical translator. Translate faithfully, keep ArduPilot parameter names, units and numbers unchanged. Output only the translation. ' + _gl(target)}]},
                       'contents': [{'role': 'user', 'parts': [{'text': f'Translate into {LANG_NAME[target]}:\n\n{text}'}]}],
                       'generationConfig': self._cfg(4000)})
        c = (d.get('candidates') or [{}])[0].get('content') or {}
        return ''.join(p.get('text', '') for p in c.get('parts', []) if not p.get('thought')).strip()


# --------------------------------------------------- ücretsiz (anahtarsız) danışman
def _free_post(body, timeout=120):
    """OpenAI uyumlu anahtarsız uç noktaya istek; yoğunlukta kısa bekleyip yeniden dener."""
    body = dict(body, referrer='pixhawk-log-analiz', private=True)
    last = None
    for url in PROVIDERS['free']['urls']:
        for i in range(3):
            req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST',
                                         headers={'Content-Type': 'application/json', 'User-Agent': 'PixhawkLogAnaliz'})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read().decode() or '{}')
            except urllib.error.HTTPError as e:
                last = RuntimeError(f"{e.code}: {e.read().decode('utf-8', 'replace')[:200]}"); last.status = e.code
                if e.code in (429, 500, 502, 503, 504): time.sleep((4, 10, 16)[i]); continue
                break
            except (TimeoutError, OSError) as e:
                last = e; time.sleep((2, 5, 10)[i])
    raise last or RuntimeError('free AI unavailable')


_AD = re.compile(r'\n+\s*(?:-{3,}|\*{3,})\s*\n[^\n]*(?:pollinations|sponsor|\bad\b)[\s\S]*$', re.I)


def _free_text(d):
    m = ((d.get('choices') or [{}])[0].get('message') or {})
    txt = _AD.sub('', (m.get('content') or '')).strip()   # servis cevabın sonuna reklam/destek notu eklerse temizle
    return txt, m


class FreeAdvisor:
    """Anahtarsız ücretsiz model: önce log araçlarıyla (function calling), desteklenmezse logun özetini bağlam olarak vererek."""
    def __init__(self, A, model='openai', lang='tr', usage=None):
        from .advisor import LogTools, TOOLS
        self.A = A; self.model = model or 'openai'; self.lang = lang; self.usage = usage
        self.tools = LogTools(A) if A is not None else None
        self.decl = [{'type': 'function', 'function': {'name': t['name'], 'description': t['description'], 'parameters': t['input_schema']}}
                     for t in TOOLS]
        self.messages = []; self.no_tools = False

    def _note(self, d):
        u = d.get('usage') or {}
        if self.usage:
            try: self.usage.add_generic('free', u.get('prompt_tokens', 0), u.get('completion_tokens', 0), {})
            except Exception: pass

    def chat(self, system, prompt, max_tokens=4000):
        d = _free_post({'model': self.model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}],
                        'max_tokens': max_tokens, 'temperature': 0.3})
        self._note(d); return _free_text(d)[0]

    def ask(self, question, on_status=None, max_rounds=6):
        from .advisor import SYSTEM, LANG_NAME
        system = SYSTEM.replace('{lang}', LANG_NAME.get(self.lang, 'Turkish'))
        if not self.no_tools:
            try:
                return self._ask_tools(system, question, on_status, max_rounds)
            except Exception:
                self.no_tools = True; self.messages = []
        # araçsız: logun özeti bağlam olarak
        ctx = json.dumps(self.tools.overview(), ensure_ascii=False, default=float)[:24000] if self.tools else ''
        hist = ''.join(f"\n\nQ: {q}\nA: {a}" for q, a in self.messages[-4:])
        ans = self.chat(system, f"LOG OVERVIEW (JSON):\n{ctx}{hist}\n\nQUESTION: {question}")
        self.messages.append((question, ans[:2000]))
        return ans

    def _ask_tools(self, system, question, on_status, max_rounds):
        msgs = [{'role': 'system', 'content': system}] + [m for m in self.messages if isinstance(m, dict)] + [{'role': 'user', 'content': question}]
        for rnd in range(max_rounds):
            body = {'model': self.model, 'messages': msgs, 'max_tokens': 4000, 'temperature': 0.3}
            if rnd < max_rounds - 1: body['tools'] = self.decl
            d = _free_post(body); self._note(d)
            txt, m = _free_text(d)
            calls = m.get('tool_calls') or []
            if not calls:
                if not txt: raise RuntimeError('empty answer')
                self.messages += [{'role': 'user', 'content': question}, {'role': 'assistant', 'content': txt}]
                return txt
            msgs.append({'role': 'assistant', 'content': m.get('content') or '', 'tool_calls': calls})
            for c in calls:
                fn = (c.get('function') or {}); name = fn.get('name')
                if on_status: on_status(name)
                try:
                    inp = json.loads(fn.get('arguments') or '{}')
                    if name == 'events': inp = dict(inp, lang='en')
                    res = getattr(self.tools, name)(**inp)
                except Exception as e:
                    res = {'error': str(e)}
                msgs.append({'role': 'tool', 'tool_call_id': c.get('id'), 'content': json.dumps(res, ensure_ascii=False, default=float)[:12000]})
        raise RuntimeError('too many steps')

    def translate(self, text, target):
        from .advisor import LANG_NAME
        return self.chat('You are a professional aviation/UAV technical translator. Translate faithfully, keep ArduPilot parameter names, units and numbers unchanged. Output only the translation. ' + _gl(target),
                         f'Translate into {LANG_NAME[target]}:\n\n{text}')


# ------------------------------------------------------------------ fabrika
def _keys(settings):
    return {'gemini': (settings.get('gemini_key') or '').strip(), 'anthropic': (settings.get('api_key') or '').strip()}


def current(settings):
    """(sağlayıcı, anahtar, model). Seçili sağlayıcının anahtarı yoksa diğerinin anahtarı, o da yoksa anahtarsız ücretsiz model."""
    prov = settings.get('ai_provider') or 'gemini'
    keys = _keys(settings)
    if prov != 'free' and not keys.get(prov):
        other = 'gemini' if prov == 'anthropic' else 'anthropic'
        prov = other if keys.get(other) else 'free'
    key = keys.get(prov, '')
    model = {'gemini': settings.get('gemini_model'), 'anthropic': settings.get('model'), 'free': settings.get('free_model')}[prov]
    return prov, key, (model or PROVIDERS[prov]['default'])


def available(settings):
    """Çevrimiçi ise her zaman: anahtar yoksa ücretsiz model kullanılır (ayarlardan kapatılabilir)."""
    if not settings.get('online', True): return False
    prov, key, _ = current(settings)
    return bool(key) or (prov == 'free' and settings.get('free_ai', True))


def _fallback(settings, e):
    """Claude/Gemini her türlü hata verirse (kredi yok, anahtar geçersiz, kota, bağlantı) sıradaki sağlayıcıya geçilir."""
    return True


class _Chain:
    """Danışman zinciri: birincisi hata verirse (ör. Claude kredisi yok) otomatik olarak Gemini, sonra ücretsiz model."""
    def __init__(self, items, lang):
        self.items = items; self.lang = lang; self.i = 0

    @property
    def messages(self):
        a = self.items[self.i]; return getattr(a, 'messages', None) or getattr(a, 'contents', None)

    def ask(self, q, on_status=None):
        last = None
        while self.i < len(self.items):
            try:
                return self.items[self.i].ask(q, on_status=on_status)
            except Exception as e:
                last = e
                if not _fallback({}, e) or self.i + 1 >= len(self.items): raise
                self.i += 1
        raise last

    def translate(self, text, target):
        return self.items[self.i].translate(text, target)


def _order(settings):
    prov, _, _ = current(settings)
    keys = _keys(settings); out = [prov]
    for p in ('gemini', 'anthropic'):
        if keys.get(p) and p not in out: out.append(p)
    if settings.get('free_ai', True) and 'free' not in out: out.append('free')
    return out


def _one(A, settings, prov, lang, usage, effort=None):
    keys = _keys(settings); eff = effort or settings.get('effort', 'medium')
    if prov == 'gemini':
        return GeminiAdvisor(A, keys['gemini'], settings.get('gemini_model') or PROVIDERS['gemini']['default'], lang, usage, eff)
    if prov == 'free':
        return FreeAdvisor(A, settings.get('free_model') or 'openai', lang, usage)
    from .advisor import OnlineAdvisor
    return OnlineAdvisor(A, keys['anthropic'], settings.get('model') or PROVIDERS['anthropic']['default'], lang, usage, eff)


def make_advisor(A, settings, lang, usage):
    if not available(settings): raise RuntimeError('no key')
    return _Chain([_one(A, settings, p, lang, usage) for p in _order(settings)], lang)


def translate(settings, usage, text, target):
    last = None
    for p in _order(settings):
        try:
            if p == 'anthropic': return _claude_translate(settings, usage, text, target)
            return _one(None, settings, p, 'en', usage, 'low').translate(text, target)
        except Exception as e:
            last = e
    raise last or RuntimeError('no AI')


def _claude_translate(settings, usage, text, target):
    prov, key, model = 'anthropic', _keys(settings)['anthropic'], settings.get('model') or PROVIDERS['anthropic']['default']
    from .advisor import OnlineAdvisor
    a = OnlineAdvisor.__new__(OnlineAdvisor)
    import anthropic
    a.client = anthropic.Anthropic(api_key=key, max_retries=2, timeout=180); a.model = model; a.usage = usage
    return OnlineAdvisor.translate(a, text, target)


def chat(settings, usage, system, prompt, max_tokens=6000):
    """Araçsız tek soru-cevap (Parametre Merkezi, ders kitabı vb.). Sıra: seçili sağlayıcı → diğer anahtar → ücretsiz model."""
    if not available(settings): raise RuntimeError('no key')
    last = None
    for p in _order(settings):
        try:
            return _chat1(settings, usage, p, system, prompt, max_tokens)
        except Exception as e:
            last = e
    raise last


def _chat1(settings, usage, prov, system, prompt, max_tokens):
    key = _keys(settings).get(prov, '')
    model = {'gemini': settings.get('gemini_model'), 'anthropic': settings.get('model')}.get(prov) or PROVIDERS[prov]['default']
    if prov == 'free':
        return FreeAdvisor(None, settings.get('free_model') or 'openai', 'en', usage).chat(system, prompt, max_tokens)
    if prov == 'gemini':
        g = GeminiAdvisor(None, key, model, 'en', usage, settings.get('effort', 'medium'))
        d = g._gen({'systemInstruction': {'parts': [{'text': system}]}, 'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                    'generationConfig': g._cfg(max_tokens)})
        c = (d.get('candidates') or [{}])[0].get('content') or {}
        return ''.join(p.get('text', '') for p in c.get('parts', []) if not p.get('thought')).strip()
    import anthropic
    cl = anthropic.Anthropic(api_key=key, max_retries=2, timeout=180)
    resp = cl.messages.create(model=model, max_tokens=max_tokens, system=system, messages=[{'role': 'user', 'content': prompt}])
    if usage:
        try: usage.add(resp.usage, {})
        except Exception: pass
    return ''.join(getattr(b, 'text', '') for b in resp.content if getattr(b, 'type', '') == 'text').strip()


def _gl(target):
    try:
        from .glossary import prompt
        return prompt(target) if target in ('tr', 'ar') else ''
    except Exception:
        return ''
