"""Yapay zeka danışman.

* Çevrimiçi: Claude (kullanıcının kendi API anahtarı) logu araçlarla sorgulayarak cevap verir; her sayıyı logdan çeker.
* Çevrimdışı: kural tabanlı soru motoru (TR/EN/AR) sık sorulan soruları logdan kesin zaman ve değerle cevaplar.
"""
from __future__ import annotations
import json, re, time, math, os
import numpy as np
from .analysis import Analysis, fmt_t, _fin
from . import texts, knowledge as K

DEFAULT_MODEL = 'claude-opus-5-5'
MODELS = ['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5', 'claude-fable-5-2']

LANG_NAME = {'tr': 'Turkish', 'en': 'English', 'ar': 'Arabic'}


def _tl(t, A):
    """Zamanı hem log saniyesi hem saat olarak yaz."""
    s = f'{fmt_t(t)} (T+{t:.1f} s)'
    u = A.L.unix_at(t)
    if u:
        s += ' · ' + time.strftime('%H:%M:%S', time.localtime(u))
    return s


# ---------------------------------------------------------------- araçlar
class LogTools:
    def __init__(self, A: Analysis):
        self.A = A; self.L = A.L

    def _series(self, msg, field):
        s = self.L.msgs.get(msg)
        if s is None or not s.has(field):
            raise KeyError(f'{msg}.{field} not in log')
        return s

    def _range(self, t0=None, t1=None, phase=None):
        if phase:
            ps = [p for p in self.A.phases if p['name'] == phase]
            if not ps: raise KeyError(f'phase {phase} not found')
            return ps[0]['t0'], ps[-1]['t1']
        return (t0 if t0 is not None else 0.0), (t1 if t1 is not None else self.L.duration)

    def overview(self):
        A = self.A
        return {'vehicle': A.vehicle, 'firmware': self.L.version, 'log_duration_s': round(self.L.duration, 1),
                'verdict': A.verdict.get('kind'), 'overall_health': A.overall,
                'health': {k: {'score': v['score'], 'status': v['status'], 'metrics': {mk: (round(mv, 3) if isinstance(mv, float) else mv) for mk, mv in v['metrics'].items()}} for k, v in A.health.items()},
                'flights': [{'takeoff_s': round(a, 1), 'landing_s': round(b, 1)} for a, b in A.flights],
                'armed': [{'arm_s': round(a, 1), 'disarm_s': round(b, 1)} for a, b in A.armed],
                'phases': [{'name': p['name'], 't0': round(p['t0'], 1), 't1': round(p['t1'], 1), **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in p.get('stats', {}).items()}} for p in A.phases],
                'root_cause': A.root.get('cause'), 'root_others': A.root.get('others'),
                'facts': {k: (round(v, 2) if isinstance(v, float) else v) for k, v in A.facts.items() if k not in ('modes',)},
                'gps_clock_available': bool(self.L.gps_time0)}

    def list_messages(self):
        return {k: {'fields': [f for f in v.keys() if f != 't'], 'samples': len(v.get('t', []))} for k, v in self.L.msgs.items() if '[' not in k}

    def field_stats(self, msg, field, t0=None, t1=None, phase=None):
        s = self._series(msg, field); a, b = self._range(t0, t1, phase)
        m = (s['t'] >= a) & (s['t'] <= b); v = s[field][m]; t = s['t'][m]
        ok = np.isfinite(v)
        if not ok.any(): return {'error': 'no samples in range'}
        v, t = v[ok], t[ok]
        return {'msg': msg, 'field': field, 't0': round(a, 2), 't1': round(b, 2), 'n': int(len(v)), 'min': float(v.min()), 't_min': float(t[v.argmin()]),
                'max': float(v.max()), 't_max': float(t[v.argmax()]), 'mean': float(v.mean()), 'std': float(v.std()),
                'first': float(v[0]), 'last': float(v[-1])}

    def value_at(self, msg, field, t):
        s = self._series(msg, field)
        return {'msg': msg, 'field': field, 't': t, 'value': s.at(field, t)}

    def sample(self, msg, field, t0=None, t1=None, n=40, phase=None):
        s = self._series(msg, field); a, b = self._range(t0, t1, phase)
        n = int(max(5, min(200, n)))
        ts = np.linspace(a, b, n)
        vals = np.interp(ts, s['t'], s[field])
        return {'msg': msg, 'field': field, 'points': [[round(float(x), 2), round(float(y), 3)] for x, y in zip(ts, vals)]}

    def find_threshold(self, msg, field, op, value, t0=None, t1=None):
        s = self._series(msg, field); a, b = self._range(t0, t1)
        m = (s['t'] >= a) & (s['t'] <= b)
        v = s[field]
        cond = {'>': v > value, '<': v < value, '>=': v >= value, '<=': v <= value, '==': v == value}.get(op)
        if cond is None: raise ValueError('op')
        c = cond & m
        runs = []; start = None
        for i in range(len(c)):
            if c[i] and start is None: start = s['t'][i]
            if not c[i] and start is not None: runs.append([round(start, 2), round(s['t'][i], 2)]); start = None
        if start is not None: runs.append([round(start, 2), round(s['t'][-1], 2)])
        return {'first_t': runs[0][0] if runs else None, 'intervals': runs[:30], 'n_intervals': len(runs),
                'total_s': round(sum(b - a for a, b in runs), 2)}

    def events(self, category=None, min_severity=0, t0=None, t1=None, lang='en'):
        out = []
        for e in self.A.events:
            if category and e['cat'] != category: continue
            if e['sev'] < min_severity: continue
            if t0 is not None and e['t'] < t0: continue
            if t1 is not None and e['t'] > t1: continue
            out.append({'t': round(e['t'], 2), 'cat': e['cat'], 'sev': e['sev'], 'text': texts.render(e['text'], lang)})
        return {'events': out[:250], 'total': len(out)}

    def params(self, names=None, prefix=None):
        P = self.L.params
        if names: return {n: P.get(n) for n in names}
        if prefix: return {k: v for k, v in P.items() if k.startswith(prefix)}
        return {'count': len(P), 'audit': [texts.render(f['text'], 'en') for f in self.A.param_findings]}

    def search_text(self, pattern):
        rx = re.compile(pattern, re.I)
        return {'matches': [{'t': round(t, 2), 'text': x} for t, x in self.L.texts if rx.search(x)][:100]}


TOOLS = [
    {'name': 'overview', 'description': 'Flight overview: vehicle, verdict (normal/incident/crash), health scores with metrics, take-off/landing times, phases with stats, root cause, key facts. Call this first.', 'input_schema': {'type': 'object', 'properties': {}, 'required': []}},
    {'name': 'list_messages', 'description': 'List log message types available and their fields.', 'input_schema': {'type': 'object', 'properties': {}, 'required': []}},
    {'name': 'field_stats', 'description': 'Min/max/mean (with the times they happened) of one log field over a time range or a named flight phase (ground, takeoff, climb, cruise, descent, landing). Times are seconds from log start.', 'input_schema': {'type': 'object', 'properties': {'msg': {'type': 'string'}, 'field': {'type': 'string'}, 't0': {'type': 'number'}, 't1': {'type': 'number'}, 'phase': {'type': 'string'}}, 'required': ['msg', 'field']}},
    {'name': 'value_at', 'description': 'Value of a log field at a given time (seconds from log start).', 'input_schema': {'type': 'object', 'properties': {'msg': {'type': 'string'}, 'field': {'type': 'string'}, 't': {'type': 'number'}}, 'required': ['msg', 'field', 't']}},
    {'name': 'sample', 'description': 'Evenly resampled points [t, value] of a field to see its shape over time.', 'input_schema': {'type': 'object', 'properties': {'msg': {'type': 'string'}, 'field': {'type': 'string'}, 't0': {'type': 'number'}, 't1': {'type': 'number'}, 'n': {'type': 'integer'}, 'phase': {'type': 'string'}}, 'required': ['msg', 'field']}},
    {'name': 'find_threshold', 'description': 'Find when a field crosses a threshold (op one of > < >= <= ==). Returns first time and intervals.', 'input_schema': {'type': 'object', 'properties': {'msg': {'type': 'string'}, 'field': {'type': 'string'}, 'op': {'type': 'string'}, 'value': {'type': 'number'}, 't0': {'type': 'number'}, 't1': {'type': 'number'}}, 'required': ['msg', 'field', 'op', 'value']}},
    {'name': 'events', 'description': 'Timeline events: category one of mode, err, ev, msg, flight; min_severity 0 info,1 warning,2 critical.', 'input_schema': {'type': 'object', 'properties': {'category': {'type': 'string'}, 'min_severity': {'type': 'integer'}, 't0': {'type': 'number'}, 't1': {'type': 'number'}}, 'required': []}},
    {'name': 'params', 'description': 'Parameter values by exact names or prefix; without arguments returns the parameter audit findings.', 'input_schema': {'type': 'object', 'properties': {'names': {'type': 'array', 'items': {'type': 'string'}}, 'prefix': {'type': 'string'}}, 'required': []}},
    {'name': 'search_text', 'description': 'Regex search in autopilot text messages (MSG / STATUSTEXT).', 'input_schema': {'type': 'object', 'properties': {'pattern': {'type': 'string'}}, 'required': ['pattern']}},
]


SYSTEM = """You are a senior ArduPilot flight-test engineer, accident investigator and flight instructor acting as an advisor inside a Pixhawk log analysis program.
You answer questions about ONE flight log that you can query with the provided tools.
Rules:
- Never guess numbers. Get every value, time and fact from the tools. Call `overview` first if you have not yet.
- Be efficient: `overview` and `events` usually contain the answer; use at most 4-5 tool calls, then answer.
- Times: tools use seconds from log start. Always show times as mm:ss (and the seconds value), e.g. 05:12.4 (T+312.4 s).
- Be precise and practical like a consultant: give the direct answer first, then the evidence (values, times), then what it means and what to do.
- Explain technical terms briefly so a student can learn. Use ArduPilot parameter and message names exactly.
- If the log does not contain the data needed, say so plainly and say which message would be needed.
- Reply in {lang}. Use short paragraphs and lists; no tables wider than 4 columns."""


class Usage:
    """Kullanıcının kendi API kullanımı ve limitleri (ayarlar ekranında gösterilir)."""
    def __init__(self, path):
        self.path = path
        self.data = {'calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'cache_read': 0, 'by_day': {}, 'limits': {}, 'last': None}
        try:
            with open(path, encoding='utf-8') as f: self.data.update(json.load(f))
        except Exception: pass

    def add_generic(self, provider, it, ot, limits):
        d = self.data
        d['calls'] += 1; d['input_tokens'] += it or 0; d['output_tokens'] += ot or 0
        day = time.strftime('%Y-%m-%d')
        bd = d['by_day'].setdefault(day, {'calls': 0, 'in': 0, 'out': 0}); bd['calls'] += 1; bd['in'] += it or 0; bd['out'] += ot or 0
        bp = d.setdefault('by_provider', {}).setdefault(provider, {'calls': 0, 'in': 0, 'out': 0, 'today': {}})
        bp['calls'] += 1; bp['in'] += it or 0; bp['out'] += ot or 0
        td = bp['today'] if bp['today'].get('day') == day else {'day': day, 'calls': 0, 'tokens': 0}
        td['calls'] += 1; td['tokens'] += (it or 0) + (ot or 0); bp['today'] = td
        if limits: d.setdefault('plimits', {})[provider] = limits
        d['last'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self._save()

    def note_quota(self, provider, details):
        q = []
        for dt in details or []:
            for v in dt.get('violations', []) or []:
                q.append(f"{v.get('quotaMetric', '').split('/')[-1]}: {v.get('quotaValue', '?')} ({v.get('quotaId', '')})")
            if dt.get('retryDelay'): q.append('retry ' + dt['retryDelay'])
        self.data.setdefault('plimits', {})[provider] = {'quota_hit': time.strftime('%Y-%m-%d %H:%M'), 'details': q[:6]}
        self._save()

    def month_tokens(self, days=30):
        import datetime
        lim = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        return sum(v['in'] + v['out'] for k, v in self.data['by_day'].items() if k >= lim), sum(v['calls'] for k, v in self.data['by_day'].items() if k >= lim)

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f: json.dump(self.data, f)
        except Exception: pass

    def add(self, usage, headers):
        d = self.data
        d['calls'] += 1
        it = getattr(usage, 'input_tokens', 0) or 0; ot = getattr(usage, 'output_tokens', 0) or 0
        bp = d.setdefault('by_provider', {}).setdefault('anthropic', {'calls': 0, 'in': 0, 'out': 0, 'today': {}})
        bp['calls'] += 1; bp['in'] += it; bp['out'] += ot
        d['input_tokens'] += it; d['output_tokens'] += ot
        d['cache_read'] += getattr(usage, 'cache_read_input_tokens', 0) or 0
        day = time.strftime('%Y-%m-%d')
        bd = d['by_day'].setdefault(day, {'calls': 0, 'in': 0, 'out': 0}); bd['calls'] += 1; bd['in'] += it; bd['out'] += ot
        lim = {}
        for k in ('requests-limit', 'requests-remaining', 'requests-reset', 'input-tokens-limit', 'input-tokens-remaining',
                  'input-tokens-reset', 'output-tokens-limit', 'output-tokens-remaining', 'output-tokens-reset',
                  'tokens-limit', 'tokens-remaining', 'tokens-reset'):
            v = headers.get('anthropic-ratelimit-' + k) if headers else None
            if v is not None: lim[k] = v
        if lim: d['limits'] = lim; d.setdefault('plimits', {})['anthropic'] = lim
        d['last'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self._save()


class OnlineAdvisor:
    def __init__(self, A: Analysis, api_key: str, model=DEFAULT_MODEL, lang='tr', usage: Usage | None = None, effort='medium'):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=180)
        self.anthropic = anthropic
        self.A = A; self.tools = LogTools(A); self.model = model; self.lang = lang; self.usage = usage
        self.effort = effort
        self.messages = []

    def _call_tool(self, name, inp):
        try:
            fn = getattr(self.tools, name)
            if name == 'events': inp = dict(inp, lang=self.lang if self.lang == 'en' else 'en')
            return json.dumps(fn(**inp), ensure_ascii=False, default=float)[:60000], False
        except Exception as e:
            return f'error: {e}', True

    def ask(self, question, on_status=None, max_rounds=12):
        self.messages.append({'role': 'user', 'content': question})
        system = SYSTEM.replace('{lang}', LANG_NAME.get(self.lang, 'Turkish'))
        for rnd in range(max_rounds):
            kw = dict(model=self.model, max_tokens=16000, system=system, tools=TOOLS, messages=self.messages)
            if rnd >= max_rounds - 1: kw['tool_choice'] = {'type': 'none'}
            if self.model.startswith(('claude-opus-5', 'claude-sonnet-5', 'claude-fable', 'claude-haiku-5')):
                kw['thinking'] = {'type': 'adaptive'}
                kw['output_config'] = {'effort': self.effort}
            if self.model in ('claude-opus-5-5', 'claude-sonnet-5-5', 'claude-fable-5-2'):
                kw['betas'] = ['server-side-fallback-2026-07-01']; kw['fallbacks'] = 'default'
                raw = self.client.beta.messages.with_raw_response.create(**kw)
            else:
                raw = self.client.messages.with_raw_response.create(**kw)
            resp = raw.parse()
            if self.usage: self.usage.add(resp.usage, raw.headers)
            self.messages.append({'role': 'assistant', 'content': resp.content})
            if resp.stop_reason == 'refusal':
                return {'tr': 'Model bu isteği yanıtlamayı reddetti.', 'en': 'The model declined this request.', 'ar': 'رفض النموذج هذا الطلب.'}[self.lang]
            if resp.stop_reason != 'tool_use':
                return ''.join(getattr(b, 'text', '') for b in resp.content if getattr(b, 'type', '') == 'text').strip()
            results = []
            for b in resp.content:
                if getattr(b, 'type', '') == 'tool_use':
                    if on_status: on_status(b.name)
                    out, err = self._call_tool(b.name, b.input or {})
                    results.append({'type': 'tool_result', 'tool_use_id': b.id, 'content': out, 'is_error': err})
            self.messages.append({'role': 'user', 'content': results})
        return {'tr': 'Cevap için çok fazla adım gerekti; soruyu daraltın.', 'en': 'Too many steps were needed; narrow the question.', 'ar': 'تطلب الأمر خطوات كثيرة؛ ضيّق السؤال.'}[self.lang]

    def translate(self, text, target):
        resp = self.client.messages.create(model=self.model, max_tokens=4000,
            system='You are a professional aviation/UAV technical translator. Translate faithfully, keep ArduPilot parameter names, units and numbers unchanged. Output only the translation.',
            messages=[{'role': 'user', 'content': f'Translate into {LANG_NAME[target]}:\n\n{text}'}])
        if self.usage: self.usage.add(resp.usage, {})
        return ''.join(getattr(b, 'text', '') for b in resp.content if getattr(b, 'type', '') == 'text').strip()


# ------------------------------------------------------------ offline motor
_KW = {
    'takeoff': ['kalkış', 'kalktı', 'havalan', 'take off', 'takeoff', 'take-off', 'launch', 'إقلاع', 'اقلاع', 'أقلع'],
    'landing': ['iniş', 'indi', 'land', 'touchdown', 'هبوط', 'هبط'],
    'duration': ['ne kadar uçtu', 'uçuş süresi', 'kaç dakika', 'süre', 'how long', 'duration', 'flight time', 'مدة', 'كم دقيقة', 'زمن الطيران'],
    'max_alt': ['en yüksek irtifa', 'azami irtifa', 'maksimum irtifa', 'max alt', 'highest', 'maximum altitude', 'أعلى ارتفاع', 'أقصى ارتفاع', 'irtifa', 'yükseklik', 'altitude', 'ارتفاع'],
    'speed': ['hız', 'speed', 'سرعة'],
    'battery': ['batarya', 'pil', 'voltaj', 'gerilim', 'battery', 'voltage', 'بطارية', 'جهد'],
    'mode': ['mod', 'mode', 'وضع'],
    'error': ['hata', 'error', 'failsafe', 'arıza', 'uyarı', 'warning', 'خطأ', 'أخطاء', 'طوارئ', 'تحذير'],
    'crash': ['kırım', 'düştü', 'kaza', 'crash', 'neden', 'sebep', 'why', 'cause', 'تحطم', 'سقط', 'سبب', 'لماذا'],
    'gps': ['gps', 'uydu', 'satellite', 'hdop', 'أقمار', 'قمر'],
    'vibe': ['titreşim', 'vibration', 'vibe', 'اهتزاز'],
    'distance': ['mesafe', 'uzaklık', 'ne kadar uzağa', 'distance', 'far', 'مسافة', 'ابتعد'],
    'throttle': ['gaz', 'throttle', 'خانق'],
    'health': ['sağlık', 'puan', 'durum', 'health', 'score', 'صحة', 'تقييم'],
    'arm': ['arm', 'silah', 'تسليح'],
    'roll': ['yatış', 'roll', 'دوران'], 'pitch': ['yunuslama', 'pitch', 'ميلان'],
    'max': ['en yüksek', 'en fazla', 'azami', 'maks', 'max', 'highest', 'peak', 'أعلى', 'أقصى'],
    'min': ['en düşük', 'en az', 'asgari', 'min', 'lowest', 'أدنى', 'أقل'],
    'when': ['ne zaman', 'hangi saniye', 'kaçıncı saniye', 'saat kaç', 'when', 'what time', 'which second', 'متى', 'في أي ثانية'],
}
_PH = {'takeoff': ['kalkış sırasında', 'kalkışta', 'during takeoff', 'during take-off', 'أثناء الإقلاع'],
       'landing': ['iniş sırasında', 'inişte', 'during landing', 'أثناء الهبوط'],
       'cruise': ['seyir', 'cruise', 'الطيران المستقر'], 'climb': ['tırmanış', 'climb', 'الصعود'], 'descent': ['alçalma', 'descent', 'النزول']}


def _has(q, key):
    return any(w in q for w in _KW[key])


def _parse_time(q):
    m = re.search(r'(\d{1,2}):(\d{2}(?:\.\d+)?)', q)
    if m: return int(m.group(1)) * 60 + float(m.group(2))
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*\.?\s*(?:saniye|sn|s\b|sec|second|ثانية)', q)
    if m: return float(m.group(1).replace(',', '.'))
    return None


R = {
    'takeoff': ('Kalkış (havalanma) {t} anında gerçekleşti. Arm: {arm}.', 'Take-off (airborne) happened at {t}. Armed at: {arm}.', 'تم الإقلاع (أصبحت في الجو) عند {t}. التسليح عند: {arm}.'),
    'landing': ('İniş / uçuş sonu {t} anında. Disarm: {dis}.', 'Landing / end of flight at {t}. Disarmed at: {dis}.', 'الهبوط / نهاية الطيران عند {t}. نزع التسليح عند: {dis}.'),
    'duration': ('Toplam uçuş (havada) süresi {d}; log süresi {L}. Uçuş sayısı: {n}.', 'Total airborne time {d}; log length {L}. Number of flights: {n}.', 'إجمالي زمن الطيران {d}؛ طول السجل {L}. عدد الرحلات: {n}.'),
    'max_alt': ('En yüksek irtifa (eve göre) {v:.1f} m, {t} anında.', 'Maximum altitude (above home) {v:.1f} m at {t}.', 'أعلى ارتفاع (فوق نقطة الإقلاع) {v:.1f} م عند {t}.'),
    'speed': ('En yüksek yer hızı {g:.1f} m/s ({gt}). {a}', 'Maximum ground speed {g:.1f} m/s ({gt}). {a}', 'أعلى سرعة أرضية {g:.1f} م/ث ({gt}). {a}'),
    'speed_as': ('En yüksek hava hızı {v:.1f} m/s ({t}).', 'Maximum airspeed {v:.1f} m/s ({t}).', 'أعلى سرعة جوية {v:.1f} م/ث ({t}).'),
    'battery': ('En düşük batarya gerilimi {v:.2f} V ({t}). Kullanılan kapasite: {mah}. Durum: {st}.', 'Lowest battery voltage {v:.2f} V ({t}). Capacity used: {mah}. Status: {st}.', 'أدنى جهد للبطارية {v:.2f} فولت ({t}). السعة المستهلكة: {mah}. الحالة: {st}.'),
    'modes': ('Mod değişimleri:', 'Mode changes:', 'تغييرات الوضع:'),
    'errors': ('Uyarı ve hatalar:', 'Warnings and errors:', 'التحذيرات والأخطاء:'),
    'noerrors': ('Logda hata veya failsafe kaydı yok.', 'No error or failsafe records in the log.', 'لا توجد سجلات أخطاء أو طوارئ في السجل.'),
    'gps': ('GPS: en az {mn} uydu, ortalama {avg:.1f}, en yüksek HDOP {hd}. Uçuşun %{bad:.1f}\'inde GPS zayıftı.', 'GPS: min {mn} satellites, average {avg:.1f}, max HDOP {hd}. GPS was weak for {bad:.1f}% of the flight.', 'GPS: أدنى عدد أقمار {mn}، المتوسط {avg:.1f}، أعلى HDOP {hd}. كان GPS ضعيفاً خلال {bad:.1f}% من الطيران.'),
    'vibe': ('Titreşim: %95 değeri {p:.1f} m/s², en yüksek {m:.1f} m/s², kırpılma {c}. Değerlendirme: {st}. (30 altı iyi, 30–60 dikkat, 60 üstü tehlikeli)', 'Vibration: 95th percentile {p:.1f} m/s², max {m:.1f} m/s², clipping {c}. Assessment: {st}. (<30 good, 30–60 caution, >60 dangerous)', 'الاهتزاز: المئين 95 {p:.1f} م/ث²، الأقصى {m:.1f} م/ث²، القص {c}. التقييم: {st}. (أقل من 30 جيد، 30–60 انتباه، أكثر من 60 خطر)'),
    'distance': ('Evden en uzak mesafe {d:.0f} m ({t}); toplam katedilen yol {tot:.2f} km.', 'Maximum distance from home {d:.0f} m ({t}); total distance flown {tot:.2f} km.', 'أبعد مسافة عن نقطة الإقلاع {d:.0f} م ({t})؛ إجمالي المسافة المقطوعة {tot:.2f} كم.'),
    'health': ('Genel sağlık puanı {o}/100. Alanlar: {lst}', 'Overall health score {o}/100. Areas: {lst}', 'درجة الصحة العامة {o}/100. المجالات: {lst}'),
    'value_at': ('{t} anında: {lst}', 'At {t}: {lst}', 'عند {t}: {lst}'),
    'phase_field': ('{ph} aşamasında ({t0} – {t1}) {f}: ortalama {mean:.1f}, en düşük {mn:.1f}, en yüksek {mx:.1f}.', 'During {ph} ({t0} – {t1}) {f}: mean {mean:.1f}, min {mn:.1f}, max {mx:.1f}.', 'خلال {ph} ({t0} – {t1}) {f}: المتوسط {mean:.1f}، الأدنى {mn:.1f}، الأعلى {mx:.1f}.'),
    'unknown': ('Bu soruyu çevrimdışı motor anlayamadı. Örnek sorular: "Hangi saniyede kalkış yapıldı?", "En yüksek irtifa ne?", "İniş sırasında gaz neydi?", "05:30\'da irtifa kaçtı?", "Neden düştü?", "Hangi modlara geçildi?". Daha serbest sorular için Ayarlar\'dan API anahtarı girip çevrimiçi danışmanı kullanın.', 'The offline engine could not understand this question. Try: "When was take-off?", "What was the maximum altitude?", "What was the throttle during landing?", "Altitude at 05:30?", "Why did it crash?", "Which modes were used?". For free-form questions add your API key in Settings and use the online advisor.', 'لم يفهم المحرك دون اتصال هذا السؤال. جرّب: "متى تم الإقلاع؟"، "ما أعلى ارتفاع؟"، "ما قيمة الخانق أثناء الهبوط؟"، "الارتفاع عند 05:30؟"، "لماذا تحطمت؟"، "ما الأوضاع المستخدمة؟". للأسئلة الحرة أدخل مفتاح API في الإعدادات واستخدم المستشار المتصل.'),
    'noflight': ('Bu logda uçuş (havalanma) tespit edilmedi.', 'No flight (take-off) was detected in this log.', 'لم يُكتشف طيران (إقلاع) في هذا السجل.'),
    'nodata': ('Bu bilgi için logda veri yok.', 'The log has no data for this.', 'لا توجد بيانات لهذا في السجل.'),
    'crash': ('Sonuç: {v}. {desc}', 'Verdict: {v}. {desc}', 'النتيجة: {v}. {desc}'),
    'cause': ('Olası kök neden: {c} ({t}). {why}\nZincir: {chain}\nÖnlem: {prev}', 'Probable root cause: {c} ({t}). {why}\nChain: {chain}\nPrevention: {prev}', 'السبب الجذري المحتمل: {c} ({t}). {why}\nالتسلسل: {chain}\nالوقاية: {prev}'),
}


def _r(key, lang, **a):
    i = ('tr', 'en', 'ar').index(lang)
    return R[key][i].format(**a)


def offline_answer(A: Analysis, question: str, lang='tr') -> str:
    q = question.lower().strip()
    f = A.facts; L = A.L
    tl = lambda t: _tl(t, A)
    out = []
    t_q = _parse_time(q)
    phase = next((p for p, ws in _PH.items() if any(w in q for w in ws)), None)
    # Belirli bir anda değer
    if t_q is not None and not _has(q, 'when'):
        vals = []
        tr = A.track
        if tr is not None:
            vals.append(('Alt', float(np.interp(t_q, tr['t'], tr['rel'])), 'm'))
        for msg, fld, unit in (('GPS', 'Spd', 'm/s'), ('ARSP', 'Airspeed', 'm/s'), ('CTUN', 'ThO', '%'), ('BAT', 'Volt', 'V'), ('ATT', 'Roll', '°'), ('ATT', 'Pitch', '°'), ('GPS', 'NSats', '')):
            s = L.s(msg)
            if s.has(fld): vals.append((f'{msg}.{fld}', s.at(fld, t_q), unit))
        mode = None
        for t, n, _, _ in L.modes:
            if t <= t_q: mode = K.mode_name(A.vehicle, n)
        lst = ', '.join(f'{k} = {v:.1f} {u}'.strip() for k, v, u in vals if v is not None and math.isfinite(v))
        if mode: lst += f', MODE = {mode}'
        return _r('value_at', lang, t=tl(t_q), lst=lst)
    # Aşama + alan
    if phase and (_has(q, 'throttle') or _has(q, 'speed') or _has(q, 'max_alt') or _has(q, 'roll') or _has(q, 'pitch') or _has(q, 'battery') or _has(q, 'vibe')):
        ps = [p for p in A.phases if p['name'] == phase]
        if not ps: return _r('nodata', lang)
        t0, t1 = ps[0]['t0'], ps[-1]['t1']
        cands = []
        if _has(q, 'throttle'): cands.append(('CTUN', 'ThO', 'Gaz/Throttle %'))
        if _has(q, 'speed'): cands += [('ARSP', 'Airspeed', 'Airspeed m/s'), ('GPS', 'Spd', 'Ground speed m/s')]
        if _has(q, 'max_alt'): cands.append(('POS', 'RelHomeAlt', 'Alt m'))
        if _has(q, 'roll'): cands.append(('ATT', 'Roll', 'Roll °'))
        if _has(q, 'pitch'): cands.append(('ATT', 'Pitch', 'Pitch °'))
        if _has(q, 'battery'): cands.append(('BAT', 'Volt', 'Volt V'))
        if _has(q, 'vibe'): cands.append(('VIBE', 'VibeZ', 'VibeZ m/s²'))
        lt = LogTools(A)
        for msg, fld, lab in cands:
            try:
                st = lt.field_stats(msg, fld, t0, t1)
                if 'error' in st: continue
                out.append(_r('phase_field', lang, ph=texts.T('ph_' + phase, lang), t0=fmt_t(t0), t1=fmt_t(t1), f=lab, mean=st['mean'], mn=st['min'], mx=st['max']))
            except KeyError:
                continue
        return '\n'.join(out) if out else _r('nodata', lang)
    if _has(q, 'crash'):
        v = A.verdict.get('kind', 'normal')
        out.append(_r('crash', lang, v=texts.T('v_' + v, lang), desc=texts.T('v_desc_' + v, lang)))
        if A.root:
            c = A.root['cause']
            chain = ' → '.join(f"{fmt_t(s['t'])} {texts.chain_step(s, lang, fmt_t)}" for s in A.root.get('chain', []))
            out.append(_r('cause', lang, c=texts.T('cause_' + c, lang), t=tl(A.root.get('t', 0)), why=texts.T('why_' + c, lang), chain=chain, prev=texts.T('prevent_' + c, lang)))
        return '\n'.join(out)
    if _has(q, 'takeoff') and not _has(q, 'landing'):
        if 'takeoff_t' not in f: return _r('noflight', lang)
        return _r('takeoff', lang, t=tl(f['takeoff_t']), arm=tl(f['arm_t']) if 'arm_t' in f else '-')
    if _has(q, 'landing') and not _has(q, 'throttle'):
        if 'land_t' not in f: return _r('noflight', lang)
        return _r('landing', lang, t=tl(f['land_t']), dis=tl(f['disarm_t']) if 'disarm_t' in f else '-')
    if _has(q, 'duration'):
        return _r('duration', lang, d=fmt_t(f.get('flight_time', 0)), L=fmt_t(L.duration), n=f.get('n_flights', 0))
    if _has(q, 'gps'):
        h = A.health.get('gps')
        if not h: return _r('nodata', lang)
        m = h['metrics']
        return _r('gps', lang, mn=int(m['min_sats'] or 0), avg=m['mean_sats'] or 0, hd=round(m['max_hdop'], 2) if m['max_hdop'] else '-', bad=m['bad_pct'])
    if _has(q, 'vibe'):
        h = A.health.get('vibration')
        if not h: return _r('nodata', lang)
        m = h['metrics']
        return _r('vibe', lang, p=m['p95'], m=m['max'], c=int(m['clip']), st=texts.T('st_' + h['status'], lang))
    if _has(q, 'battery'):
        if 'min_volt' not in f: return _r('nodata', lang)
        h = A.health.get('power', {})
        return _r('battery', lang, v=f['min_volt'], t=tl(f['min_volt_t']), mah=f"{f['used_mah']:.0f} mAh" if f.get('used_mah') else '-', st=texts.T('st_' + h.get('status', 'good'), lang))
    if _has(q, 'mode'):
        lines = [_r('modes', lang)] + [f'• {tl(t)} → {n}' + (f" ({K.tr3(K.MODE_REASON[r], lang)})" if r in K.MODE_REASON else '') for t, n, r in f.get('modes', [])]
        return '\n'.join(lines)
    if _has(q, 'error'):
        evs = [e for e in A.events if e['sev'] > 0]
        if not evs: return _r('noerrors', lang)
        return '\n'.join([_r('errors', lang)] + [f"• {tl(e['t'])} — {texts.render(e['text'], lang)}" for e in evs[:40]])
    if _has(q, 'distance'):
        if 'max_dist' not in f: return _r('nodata', lang)
        return _r('distance', lang, d=f['max_dist'], t=tl(f['max_dist_t']), tot=f.get('distance', 0) / 1000)
    if _has(q, 'speed'):
        if 'max_gs' not in f and 'max_as' not in f: return _r('nodata', lang)
        a = _r('speed_as', lang, v=f['max_as'], t=tl(f['max_as_t'])) if 'max_as' in f else ''
        return _r('speed', lang, g=f.get('max_gs', 0), gt=tl(f.get('max_gs_t', 0)), a=a)
    if _has(q, 'max_alt'):
        if 'max_alt' not in f: return _r('nodata', lang)
        return _r('max_alt', lang, v=f['max_alt'], t=tl(f['max_alt_t']))
    if _has(q, 'health'):
        lst = '; '.join(f"{texts.T('dom_' + k, lang)} {v['score']}" for k, v in A.health.items())
        return _r('health', lang, o=A.overall, lst=lst)
    if _has(q, 'arm'):
        return '\n'.join(f'• ARM {tl(a)} → DISARM {tl(b)}' for a, b in A.armed) or _r('nodata', lang)
    return _r('unknown', lang)
