"""Program içi çeviri motoru (Türkçe / English / العربية) — havacılık literatürüne sadık, resmî dil.

Sıra (ayar 'tx_mode' = 'auto'): önce ÇEVRİMİÇİ, internet yoksa ya da hata olursa ÇEVRİMDIŞI.
  1. Kullanıcının kendi Gemini / Claude anahtarı (büyük dil modeli; sözlük + iki aşamalı kalite denetimi)
  2. Anahtarsız ücretsiz dil modeli (Pollinations; kimsenin kişisel limitinden yemez)
  3. Anahtarsız Google Translate uç noktası (terimler yer tutucuyla korunur, sonra sözlük karşılığı konur)
  4. Çevrimdışı: Meta NLLB-200 3.3B (ya da 1.3B) CTranslate2 paketi — İngilizce dışı çiftlerde İngilizce üzerinden
     (sözlük yalnız İngilizce anahtarlı olduğundan pivot terimleri korur)
  0. Her şeyden önce çeviri hafızası: kullanıcının düzelttiği çeviriler > önbellek > programın gömülü 10.890 çevirisi.
'tx_mode' = 'offline' (ya da 'tx_private' açık): belge hiçbir sunucuya gönderilmez, yalnız çevrimdışı paket.

Kalite denetimi (her motorda): sözlük terimleri, sayılar, parametre adları / uçuş modları / kısaltmalar kaynakla
karşılaştırılır. Dil modeli motorlarında eksik bulunursa bir düzeltme turu yapılır; 'tx_quality' = 'max' ise
taslak ikinci bir "havacılık editörü" turundan geçer.
"""
from __future__ import annotations
import gzip, hashlib, json, os, re, sqlite3, threading, time, urllib.parse, urllib.request
from . import glossary as GL

LANGS = ('tr', 'en', 'ar')
LANG_NAME = {'tr': 'Turkish', 'en': 'English', 'ar': 'Arabic'}
NLLB_CODE = {'en': 'eng_Latn', 'tr': 'tur_Latn', 'ar': 'arb_Arab'}
RANK = {'user': 100, 'llm': 50, 'free_llm': 40, 'google': 30, 'nllb': 20, 'builtin': 15}

_AR = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')
_TR_CH = re.compile(r'[çğışöüÇĞİŞÖÜ]')
_TR_W = re.compile(r'\b(?:ve|bir|bu|için|ile|olarak|olan|değil|veya|gibi|daha|çok|kadar|sonra|önce|uçuş|uçak|motor[uü]|'
                   r'irtifa|hız[ıi]?|arıza|bakım|kontrol|yapılmalı|edilir|edildi|olur|var|yok|da|de|mi|mı)\b', re.I)
_EN_W = re.compile(r'\b(?:the|and|of|to|is|are|for|with|on|in|this|that|be|by|aircraft|flight|check|must|should|will)\b', re.I)
_LET = re.compile(r'[A-Za-zÀ-ɏ؀-ۿ]{2}')
_NUM = re.compile(r'\d+(?:[.,]\d+)*')
_AR_DIG = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')
_SENT = re.compile(r'(?<=[.!?؟;])\s+(?=\S)')


def detect(text):
    """Kaynak dili kestir: 'ar' | 'tr' | 'en'."""
    t = text or ''
    ar = len(_AR.findall(t)); lat = len(re.findall(r'[A-Za-z]', t))
    if ar and ar >= lat * 0.3: return 'ar'
    tr = len(_TR_CH.findall(t)) * 2 + len(_TR_W.findall(t)) * 3
    en = len(_EN_W.findall(t)) * 3
    return 'tr' if tr > en else 'en'


def needs(text):
    """Çevrilecek harf var mı (yalnız sayı / sembol / kod değil)."""
    if not text or not _LET.search(text): return False
    s = text.strip()
    if GL._IDENT.fullmatch(s) or GL._KEEP.fullmatch(s): return False
    if re.fullmatch(r'(?:https?://|www\.)\S+|[\w.+-]+@[\w-]+\.[\w.]+', s): return False
    return True


# ================================================================== sözlük
def _base(s):
    return re.sub(r'\s*\([^)]*\)', '', s or '').strip()


def _alias(s):
    m = re.search(r'\(([^)]*)\)', s or '')
    return m.group(1).strip() if m else ''


def _form_rx(term, lg):
    b = _base(term)
    if not b: return None
    if lg == 'ar':
        words = [re.sub(r'^(?:ال|لل)', '', w) for w in b.split()]
        pre = r'(?:[وفبكل]?(?:ال|لل)?)'
        return re.compile(r'\s+'.join(pre + re.escape(w) for w in words if w))
    return re.compile(r'(?<![\w])' + r'\s+'.join(re.escape(w) for w in b.split()) + r'\w*', re.I)


class Entry:
    __slots__ = ('en', 'tr', 'ar', 'soft', 'user', 'rx')

    def __init__(self, en, tr, ar, rx_en=None, soft=False, user=False):
        self.en, self.tr, self.ar, self.soft, self.user = en, tr, ar, soft, user
        self.rx = {'en': rx_en or _form_rx(en, 'en'), 'tr': _form_rx(tr, 'tr'), 'ar': _form_rx(ar, 'ar')}
        al_tr, al_ar = _alias(tr), _alias(ar)
        self.rx['tr_alias'] = _form_rx(al_tr, 'en') if al_tr else None
        self.rx['ar_alias'] = _form_rx(al_ar, 'en') if al_ar else None

    def get(self, lg):
        return {'en': self.en, 'tr': self.tr, 'ar': self.ar}[lg]

    def found(self, text, lg):
        rx = self.rx.get(lg)
        return bool(rx and rx.search(text or ''))

    def found_out(self, text, lg):
        """Çeviride bu terimin hedef karşılığı (ya da parantez içindeki uluslararası adı) var mı?"""
        if self.found(text, lg): return True
        a = self.rx.get(lg + '_alias')
        return bool(a and a.search(text or ''))


_ENTRIES = None
_JOIN = {'fail-safe': 'failsafe', 'way-point': 'waypoint', 'geo-fence': 'geofence', 'bit-mask': 'bitmask', 'dead-zone': 'deadzone',
         'swash-plate': 'swashplate', 'tail-sitter': 'tailsitter', 'quad-plane': 'QuadPlane', 'ground speed': 'groundspeed',
         'brown-out': 'brownout', 'geo-location': 'geolocation', 'range finder': 'rangefinder', 'auto-arm': 'auto-arm'}


def _en_name(p):
    """Sözlük deseninden okunur İngilizce ad: 'fail-?safes?' → 'failsafe', 'pre-?arm(?:ing)?(?: checks?)?' → 'pre-arm'."""
    x = re.sub(r'\(\?:[^()]*\)\??', '', p).split('|')[0]
    x = x.replace('-?', '-').replace(' ?', ' ')
    x = re.sub(r'(\w)\?', '', x) if re.search(r'[a-z]s\?$', x) else x
    x = re.sub(r'.\?', lambda m: '' if m.group(0)[0] != '-' else '-', x)
    x = re.sub(r'[()\[\]\\]', '', x).strip()
    return _JOIN.get(x.lower(), x)


def builtin_entries():
    global _ENTRIES
    if _ENTRIES is None:
        _ENTRIES = [Entry(_en_name(p), tr, ar, rx, soft=tr in GL.SOFT) for (p, tr, ar), (rx, _, _) in zip(GL.TERMS, GL._COMPILED)]
    return _ENTRIES


def entries(settings=None):
    """Gömülü havacılık sözlüğü + kullanıcının kendi terimleri (Çeviri > Sözlük). Kullanıcı terimleri önce gelir."""
    out = []
    for u in (settings or {}).get('tx_terms') or []:
        if all((u.get(k) or '').strip() for k in LANGS):
            try: out.append(Entry(u['en'].strip(), u['tr'].strip(), u['ar'].strip(), user=True))
            except re.error: pass
    return out + builtin_entries()


def relevant(text, src, ents):
    seen = set(); out = []
    for e in ents:
        k = e.en.lower()
        if k in seen: continue
        if e.found(text, src): out.append(e); seen.add(k)
    return out


def _ids(text):
    return set(GL._IDENT.findall(text or '')) | set(GL._KEEP.findall(text or ''))


def _nums(text):
    return [re.sub(r'[.,]', '', n) for n in _NUM.findall((text or '').translate(_AR_DIG))]


def check(src_text, out, src, tgt, ents):
    """Kalite denetimi: [(tür, kaynak, beklenen)] — tür: 'term' | 'num' | 'id' | 'empty'."""
    iss = []
    if needs(src_text) and not (out or '').strip():
        return [('empty', src_text[:60], '')]
    for e in relevant(src_text, src, ents):
        if e.soft and not e.user: continue
        if not e.found_out(out, tgt): iss.append(('term', e.get(src), e.get(tgt)))
    have = _nums(out)
    for n in _nums(src_text):
        if n in have: have.remove(n)
        else: iss.append(('num', n, n))
    for i in _ids(src_text):
        if i not in (out or ''): iss.append(('id', i, i))
    return iss


def glossary_lines(ents, src, tgt, limit=120):
    return '\n'.join(f'- {e.get(src)} = {e.get(tgt)}' for e in ents[:limit])


# ============================================================ çeviri hafızası
class TM:
    """sqlite çeviri hafızası (%APPDATA%/PixhawkLogAnaliz/ceviri_tm.sqlite) + gömülü parametre / log mesajı çevirileri."""
    _lock = threading.Lock()
    _builtin = {}

    def __init__(self, path=None):
        if path is None:
            from .paths import data_dir
            path = os.path.join(data_dir(), 'ceviri_tm.sqlite')
        self.path = path
        with self._lock, self._db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS tm (src TEXT, tgt TEXT, h TEXT, text TEXT, out TEXT, engine TEXT, ts REAL, '
                      'PRIMARY KEY (src, tgt, h, engine))')

    def _db(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def h(text):
        return hashlib.sha256(re.sub(r'\s+', ' ', text.strip()).encode('utf-8')).hexdigest()[:32]

    def get(self, text, src, tgt, min_rank=0):
        """(çeviri, motor) ya da None. En yüksek dereceli kayıt; min_rank altındaki önbellek yok sayılır."""
        with self._lock, self._db() as c:
            rows = c.execute('SELECT out, engine FROM tm WHERE src=? AND tgt=? AND h=?', (src, tgt, self.h(text))).fetchall()
        rows = sorted(rows, key=lambda r: -RANK.get(r[1], 0))
        if rows and RANK.get(rows[0][1], 0) >= min_rank: return rows[0][0], rows[0][1]
        if src == 'en' and tgt in ('tr', 'ar') and RANK['builtin'] >= min_rank:
            b = self.builtin(tgt).get(text.strip())
            if b: return GL.fix(b, tgt), 'builtin'
        return None

    def put(self, text, src, tgt, out, engine):
        if not out or not text.strip(): return
        with self._lock, self._db() as c:
            c.execute('INSERT OR REPLACE INTO tm VALUES (?,?,?,?,?,?,?)', (src, tgt, self.h(text), text, out, engine, time.time()))

    def user_entries(self, limit=500):
        with self._lock, self._db() as c:
            return c.execute("SELECT src, tgt, text, out, ts FROM tm WHERE engine='user' ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()

    def delete_user(self, text, src, tgt):
        with self._lock, self._db() as c:
            c.execute("DELETE FROM tm WHERE engine='user' AND src=? AND tgt=? AND h=?", (src, tgt, self.h(text)))

    def clear_cache(self):
        with self._lock, self._db() as c:
            c.execute("DELETE FROM tm WHERE engine!='user'")

    @classmethod
    def builtin(cls, lg):
        if lg not in cls._builtin:
            d = {}
            try:
                from .paths import res
                p = res('data', f'params_tx_{lg}.json.gz')
                if os.path.exists(p):
                    with gzip.open(p, 'rt', encoding='utf-8') as f: d = json.load(f)
                    d.pop('__gv', None)
            except Exception:
                d = {}
            cls._builtin[lg] = d
        return cls._builtin[lg]


# ================================================================== motorlar
class Engine:
    name = ''; kind = 'online'; rank = 0; markup = False   # markup: <1>…</1> biçim etiketlerini korur

    def batch(self, segs, src, tgt, ents, issues_out):
        raise NotImplementedError


SYSTEM = ("You are a senior aviation technical translator and editor (ICAO / EASA / FAA terminology, ArduPilot and PX4 UAV "
          "documentation, maintenance manuals, flight-test reports and official military aviation correspondence). "
          "Translate from {src} into {tgt}.\n"
          "Rules:\n"
          "1. Formal, official register only; never colloquial. Turkish: resmî yazışma ve havacılık dili. Arabic: Modern Standard "
          "Arabic (الفصحى) in formal military/aviation style, Western digits 0-9.\n"
          "2. Use EXACTLY the glossary equivalents below; keep the established aviation term even if a common word seems natural.\n"
          "3. Keep unchanged: ArduPilot parameter names (e.g. Q_ASSIST_SPEED), flight-mode names (FBWA, QLOITER, RTL…), acronyms "
          "(EKF, GPS, PWM, ESC…), units, numbers, part/serial numbers, e-mails, URLs, file names.\n"
          "4. Preserve formatting tags like <1>…</1> exactly (same numbers, same nesting), line breaks, bullets and numbering.\n"
          "5. Translate everything; no omissions, no additions, no notes, no transliteration.\n"
          "{gl}")


def _parse_array(txt, n):
    t = (txt or '').strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t)
    a, b = t.find('['), t.rfind(']')
    if a < 0 or b <= a: raise ValueError('no JSON array')
    arr = json.loads(t[a:b + 1])
    if not isinstance(arr, list) or len(arr) != n: raise ValueError(f'array length {len(arr) if isinstance(arr, list) else "?"} != {n}')
    return [x if isinstance(x, str) else str(x) for x in arr]


class LLMEngine(Engine):
    """Kullanıcının kendi Gemini / Claude anahtarı ya da anahtarsız ücretsiz model (ai._chat1)."""
    markup = True

    def __init__(self, settings, usage, prov, quality='max'):
        self.s, self.usage, self.prov, self.quality = settings, usage, prov, quality
        self.name = {'gemini': 'Google Gemini', 'anthropic': 'Anthropic Claude', 'free': 'Pollinations (ücretsiz)'}.get(prov, prov)
        self.rank = RANK['free_llm' if prov == 'free' else 'llm']
        self.tag = 'free_llm' if prov == 'free' else 'llm'

    def _chat(self, system, prompt, max_tokens):
        from . import ai
        return ai._chat1(self.s, self.usage, self.prov, system, prompt, max_tokens)

    def _system(self, segs, src, tgt, ents):
        rel = []
        for s in segs: rel += [e for e in relevant(s, src, ents) if e not in rel]
        gl = ('Glossary (' + LANG_NAME[src] + ' = ' + LANG_NAME[tgt] + '):\n' + glossary_lines(rel, src, tgt)) if rel else ''
        return SYSTEM.format(src=LANG_NAME[src], tgt=LANG_NAME[tgt], gl=gl)

    def batch(self, segs, src, tgt, ents, issues_out):
        system = self._system(segs, src, tgt, ents)
        mt = min(16000, 400 + sum(len(s) for s in segs) * 4)
        prompt = ('Translate each string of this JSON array. Return ONLY a JSON array of the same length, translations in the '
                  'same order:\n' + json.dumps(segs, ensure_ascii=False))
        out = _parse_array(self._chat(system, prompt, mt), len(segs))
        iss = [check(s, o, src, tgt, ents) for s, o in zip(segs, out)]
        if self.quality == 'max' or any(iss):
            notes = []
            for i, x in enumerate(iss):
                for kind, a, b in x:
                    notes.append(f'#{i}: ' + {'term': f'use the glossary term "{b}" for "{a}"', 'num': f'number {a} missing',
                                              'id': f'keep "{a}" unchanged', 'empty': 'translation missing'}[kind])
            rp = ('You are reviewing draft translations as the chief aviation editor. For each item compare draft with source: fix '
                  'mistranslations, omissions, wrong or informal terminology, word order and register (formal aviation/military). '
                  + (('Automatic checks found:\n' + '\n'.join(notes[:80]) + '\n') if notes else '')
                  + 'Return ONLY a JSON array of the final translations, same length and order.\n'
                  + json.dumps([{'source': s, 'draft': o} for s, o in zip(segs, out)], ensure_ascii=False))
            try:
                out2 = _parse_array(self._chat(system, rp, mt), len(segs))
                # editör bir maddeyi bozduysa (boş / etiket kaybı) taslak kalır
                out = [b if b.strip() and _tags(b) == _tags(a) else a for a, b in zip(out, out2)]
            except Exception:
                pass
        return out


class GoogleEngine(Engine):
    """Anahtarsız Google Translate uç noktası. İngilizce kaynakta sözlük terimleri yer tutucuyla korunur."""
    name = 'Google Translate'; rank = RANK['google']; tag = 'google'
    URL = 'https://translate.googleapis.com/translate_a/single'

    def _one(self, text, src, tgt):
        q = urllib.parse.urlencode({'client': 'gtx', 'sl': src, 'tl': tgt, 'dt': 't', 'ie': 'UTF-8', 'oe': 'UTF-8'})
        req = urllib.request.Request(self.URL + '?' + q, data=urllib.parse.urlencode({'q': text}).encode(), method='POST',
                                     headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                                              'User-Agent': 'Mozilla/5.0 PixhawkLogAnaliz'})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode('utf-8'))
        return ''.join(x[0] for x in (d[0] or []) if x and x[0])

    def batch(self, segs, src, tgt, ents, issues_out):
        from concurrent.futures import ThreadPoolExecutor

        def one(s):
            p, toks = protect(s, src)
            o = GL.restore(self._one(p, src, tgt), toks, tgt) if toks else None
            if o is None: o = self._one(s, src, tgt)
            return GL.fix(o, tgt)
        with ThreadPoolExecutor(6) as ex:
            return list(ex.map(one, segs))


def protect(text, src, to_en=False):
    """Yer tutucu: parametre adları, uçuş modları, kısaltmalar (her dilde) + İngilizce kaynakta sözlük terimleri.
    to_en: Türkçe/Arapça kaynaktaki sözlük terimleri de yer tutucuya alınır ve İngilizce pivotta sözlükteki İngilizce adıyla geri
    konur (ör. 'المروحة' → 'propeller'; makine 'fan' demesin). İkinci adımda bu ad hedef dildeki sözlük karşılığına çevrilir."""
    if src == 'en': return GL.protect(text)
    out = []; n = [0]

    def sub(m):
        t = GL._tok(n[0]); n[0] += 1; out.append((t, 'keep', m.group(0))); return t
    text = GL._IDENT.sub(sub, text)
    text = GL._KEEP.sub(sub, text)
    if to_en and src in ('tr', 'ar'):
        ents = sorted(builtin_entries(), key=lambda e: -len(_base(e.get(src))))
        for e in ents:
            rx = e.rx.get(src)
            if rx is None or len(_base(e.get(src))) < 3 or (e.soft and src == 'tr'): continue   # Türkçede genel kelimeler akıcılık için serbest

            def sub_t(m, e=e):
                t = GL._tok(n[0]); n[0] += 1; out.append((t, 'keep', e.en)); return t
            text = rx.sub(sub_t, text)
    return text, out


class NLLBEngine(Engine):
    """Çevrimdışı Meta NLLB-200 (CTranslate2 int8). İngilizce dışı çiftlerde İngilizce pivotu (sözlük terimleri korunur)."""
    kind = 'offline'; rank = RANK['nllb']; tag = 'nllb'
    _loaded = {}
    _lock = threading.Lock()

    def __init__(self, pack_dir, name='NLLB-200'):
        self.dir = pack_dir; self.name = name

    def _model(self):
        with self._lock:
            m = self._loaded.get(self.dir)
            if m is None:
                import ctranslate2, sentencepiece as spm
                spf = [f for f in os.listdir(self.dir) if f.endswith('.model')]
                if not spf: raise RuntimeError('sentencepiece model missing in ' + self.dir)
                sp = spm.SentencePieceProcessor(model_file=os.path.join(self.dir, spf[0]))
                dev = 'cuda' if getattr(ctranslate2, 'get_cuda_device_count', lambda: 0)() > 0 else 'cpu'
                tr = ctranslate2.Translator(self.dir, device=dev, compute_type='auto', intra_threads=max(1, (os.cpu_count() or 4) - 1))
                m = self._loaded[self.dir] = (tr, sp)
            return m

    def _raw(self, sents, src, tgt):
        tr, sp = self._model()
        toks = [[NLLB_CODE[src]] + sp.encode(s, out_type=str)[:480] + ['</s>'] for s in sents]
        res = tr.translate_batch(toks, target_prefix=[[NLLB_CODE[tgt]]] * len(toks), beam_size=5, max_batch_size=16,
                                 max_decoding_length=512, repetition_penalty=1.1, no_repeat_ngram_size=0)
        out = []
        for r in res:
            h = r.hypotheses[0]
            if h and h[0] == NLLB_CODE[tgt]: h = h[1:]
            out.append(sp.decode(h).strip())
        return out

    def _pair(self, segs, src, tgt):
        """Paragrafları cümlelere böl, yer tutucuyla çevir, birleştir."""
        prot = [protect(s, src, to_en=tgt == 'en') for s in segs]
        sents = []; idx = []
        for j, (p, _) in enumerate(prot):
            lines = p.split('\n')
            for li, line in enumerate(lines):
                parts = [x for x in _SENT.split(line) if x.strip()] or ['']
                for k, x in enumerate(parts):
                    sents.append(x); idx.append((j, li, k))
        raw = self._raw([s for s in sents if s.strip()], src, tgt) if any(s.strip() for s in sents) else []
        it = iter(raw)
        built = {}
        for s, (j, li, k) in zip(sents, idx):
            built.setdefault(j, {}).setdefault(li, []).append(next(it) if s.strip() else '')
        outs = []
        retry = []
        for j, (p, toks) in enumerate(prot):
            lines = built.get(j, {})
            o = '\n'.join(' '.join(x for x in lines[li] if x) for li in sorted(lines))
            r = GL.restore(o, toks, tgt) if toks else o
            if r is None: retry.append(j); r = ''
            outs.append(r)
        for j in retry:   # yer tutucu kayboldu: korumasız çevir
            outs[j] = ' '.join(self._raw([x for x in _SENT.split(segs[j]) if x.strip()] or [segs[j]], src, tgt))
        return [GL.fix(o, tgt) for o in outs]

    def batch(self, segs, src, tgt, ents, issues_out):
        if src != 'en' and tgt != 'en':
            return self._pair(self._pair(segs, src, 'en'), 'en', tgt)
        return self._pair(segs, src, tgt)


# ============================================================== işlem hattı
_NET = {'t': 0, 'ok': False}


def online_ok(settings=None, timeout=3):
    """İnternet var mı? (60 sn önbellek)"""
    if settings is not None and not settings.get('online', True): return False
    if time.time() - _NET['t'] < 60: return _NET['ok']
    ok = False
    for u in ('https://www.gstatic.com/generate_204', 'https://api.github.com'):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, method='HEAD', headers={'User-Agent': 'PixhawkLogAnaliz'}), timeout=timeout):
                ok = True; break
        except urllib.error.HTTPError:
            ok = True; break
        except Exception:
            continue
    _NET.update(t=time.time(), ok=ok)
    return ok


def mode(settings):
    s = settings or {}
    if s.get('tx_private'): return 'offline'
    return s.get('tx_mode') or 'auto'


def engines(settings, usage=None, net=None):
    """Kullanılacak motorlar (sırayla). net=None → bağlantı yoklanır."""
    from . import paketler
    s = settings or {}
    m = mode(s); out = []
    if m in ('auto', 'online') and (online_ok(s) if net is None else net):
        from . import ai
        for p in ai._order(s):
            if p == 'free' and not s.get('free_ai', True): continue
            if p != 'free' and not ai._keys(s).get(p): continue
            out.append(LLMEngine(s, usage, p, s.get('tx_quality') or 'max'))
        if s.get('tx_google', True): out.append(GoogleEngine())
    if m in ('auto', 'offline'):
        d = paketler.nllb_dir(s.get('tx_nllb'))
        if d: out.append(NLLBEngine(d, paketler.PACKS[paketler.nllb_id(d)]['name']))
    return out


NO_ENGINE = {'tr': 'Çeviri motoru yok: internet yok ve çevrimdışı NLLB-200 paketi kurulu değil (Çeviri Merkezi > Çevrimdışı paketler).',
             'en': 'No translation engine: no internet and the offline NLLB-200 pack is not installed (Translation Centre > Offline packs).',
             'ar': 'لا يوجد محرك ترجمة: لا إنترنت وحزمة NLLB-200 غير المتصلة غير مثبتة (مركز الترجمة > الحزم غير المتصلة).'}


class NoEngine(RuntimeError):
    pass


def _tags(s):
    return re.findall(r'</?\d+>', s or '')


def strip_tags(s):
    return re.sub(r'</?\d+>', '', s or '')


class Translator:
    """Bölüm listesi çevirir. on_progress(done, total, motor_adı), cancel() → True ise durur."""

    def __init__(self, settings=None, usage=None, tm=None, engine_list=None):
        self.s = settings or {}; self.usage = usage
        self.tm = tm if tm is not None else _tm()
        self.engines = engine_list
        self.report = {'engines': {}, 'issues': [], 'tm': 0, 'segments': 0}

    def _engines(self):
        if self.engines is None: self.engines = engines(self.s, self.usage)
        return self.engines

    def run(self, segs, src, tgt, on_progress=None, cancel=None):
        src = src if src in LANGS else detect(' '.join(segs[:50]))
        out = list(segs)
        if src == tgt: return out
        ents = entries(self.s)
        eng = self._engines()
        top = max([e.rank for e in eng], default=0)
        todo = []
        for i, s in enumerate(segs):
            if not needs(strip_tags(s)): continue
            hit = self.tm.get(s, src, tgt, min_rank=top)
            if hit:
                out[i] = hit[0]; self.report['tm'] += 1
            else:
                todo.append(i)
        self.report['segments'] += len(segs)
        if todo and not eng:
            raise NoEngine(NO_ENGINE.get(self.s.get('lang'), NO_ENGINE['en']) + ' (no engine)')
        total = len(todo); done = 0
        for batch in _batches(todo, segs):
            if cancel and cancel(): break
            got = None; last = None
            for e in eng:
                bsegs = [segs[i] for i in batch]
                if not e.markup and any(_tags(x) for x in bsegs): bsegs = [strip_tags(x) for x in bsegs]
                try:
                    got = e.batch(bsegs, src, tgt, ents, self.report['issues'])
                    if e.markup:
                        got = [g if _tags(g) == _tags(b) else strip_tags(g) for g, b in zip(got, bsegs)]
                    used = e; break
                except Exception as ex:
                    last = ex; continue
            if got is None:
                raise last or NoEngine('all engines failed')
            self.report['engines'][used.name] = self.report['engines'].get(used.name, 0) + len(batch)
            for i, o in zip(batch, got):
                out[i] = o
                self.tm.put(segs[i], src, tgt, o, used.tag)
                for kind, a, b in check(strip_tags(segs[i]), strip_tags(o), src, tgt, ents):
                    self.report['issues'].append((i, kind, a, b))
            done += len(batch)
            if on_progress: on_progress(done, total, used.name)
        return out


def _batches(idx, segs, max_chars=4500, max_n=40):
    cur = []; n = 0
    for i in idx:
        L = len(segs[i])
        if cur and (n + L > max_chars or len(cur) >= max_n):
            yield cur; cur = []; n = 0
        cur.append(i); n += L
    if cur: yield cur


_TM = {}


def _tm():
    k = os.environ.get('APPDATA', '')
    if k not in _TM: _TM[k] = TM()
    return _TM[k]


def translate_text(text, src, tgt, settings=None, usage=None, on_progress=None, cancel=None, translator=None):
    """Serbest metin: satır/paragraf yapısı korunur. (çeviri, rapor)"""
    src = src if src in LANGS else detect(text)
    lines = (text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')
    # madde imi / numara önekleri ayrı tutulur
    pre = []; body = []
    for ln in lines:
        m = re.match(r'^(\s*(?:[-*•▪◦·]|\d+[.)]|[a-zA-Z][.)])?\s*)(.*)$', ln)
        pre.append(m.group(1)); body.append(m.group(2))
    T = translator or Translator(settings, usage)
    outs = T.run(body, src, tgt, on_progress, cancel)
    res = '\n'.join(p + o for p, o in zip(pre, outs))
    return res, T.report


def save_correction(text, src, tgt, out):
    """Kullanıcı düzeltmesi: bir sonraki çeviride her motordan önce gelir."""
    _tm().put(text, src, tgt, out, 'user')


def report_text(rep, lang='tr'):
    eng = ', '.join(f'{k} ({v})' for k, v in rep.get('engines', {}).items())
    iss = rep.get('issues') or []
    terms = sum(1 for x in iss if x[1] == 'term'); nums = sum(1 for x in iss if x[1] == 'num'); ids = sum(1 for x in iss if x[1] == 'id')
    L = {'tr': ('Motor', 'Çeviri hafızası', 'Denetim', 'sorun yok', 'terim', 'sayı', 'kod/ad'),
         'en': ('Engine', 'Translation memory', 'Check', 'no issues', 'term', 'number', 'code/name'),
         'ar': ('المحرك', 'ذاكرة الترجمة', 'التدقيق', 'لا مشكلات', 'مصطلح', 'رقم', 'رمز/اسم')}[lang if lang in LANGS else 'en']
    chk = L[3] if not iss else ', '.join(f'{n} {w}' for n, w in ((terms, L[4]), (nums, L[5]), (ids, L[6])) if n)
    parts = []
    if eng: parts.append(f'{L[0]}: {eng}')
    if rep.get('tm'): parts.append(f"{L[1]}: {rep['tm']}")
    parts.append(f'{L[2]}: {chk}')
    return ' · '.join(parts)
