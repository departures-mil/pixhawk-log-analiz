"""Log mesajları kütüphanesinde arama: mesaj/alan adlarında VE açıklamalarda, üç dilde (TR/EN/AR) birden.

- Harf/aksan duyarsız: 'titresim' = 'titreşim', 'İRTİFA' = 'irtifa', Arapçada hareke ve elif/ye/te-merbuta biçimleri eşlenir.
- Çok kelimeli aramada her kelime mesajın bir yerinde geçmeli (VE); sıralama: ad eşleşmesi > alan adı > açıklama.
- Sonuç hangi alanların ve hangi dillerin eşleştiğini söyler (liste ipucu + ayrıntıda vurgulama için).
"""
from __future__ import annotations
import re
import unicodedata

_TR = str.maketrans({'ı': 'i', 'İ': 'i', 'ş': 's', 'Ş': 's', 'ğ': 'g', 'Ğ': 'g', 'ü': 'u', 'Ü': 'u', 'ö': 'o', 'Ö': 'o',
                     'ç': 'c', 'Ç': 'c', 'â': 'a', 'î': 'i', 'û': 'u',
                     'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ئ': 'ي', 'ؤ': 'و', 'ة': 'ه', 'ـ': ''})
_AR_MARKS = re.compile('[ً-ٰٟۖ-ۭ]')
LANGS = ('tr', 'en', 'ar')


def norm(s):
    """Arama için sadeleştirilmiş metin (küçük harf, aksansız, Arapça harekesiz)."""
    if not s: return ''
    s = str(s).translate(_TR)
    s = _AR_MARKS.sub('', s)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.casefold()


# eş anlamlılar (TR/EN/AR): bir kelime aranınca grubun diğerleri de eşleşir
SYN = [('voltaj', 'gerilim', 'volt', 'voltage', 'الجهد'), ('akim', 'current', 'curr', 'التيار'),
       ('titresim', 'vibration', 'vibe', 'اهتزاز'), ('irtifa', 'yukseklik', 'altitude', 'الارتفاع'),
       ('pusula', 'manyetometre', 'compass', 'magnetometer', 'البوصله'), ('batarya', 'pil', 'aku', 'battery', 'البطاريه'),
       ('hiz', 'speed', 'velocity', 'السرعه'), ('gaz', 'throttle', 'الخانق'), ('ruzgar', 'wind', 'الرياح'),
       ('sicaklik', 'temperature', 'temp', 'الحراره'), ('kumanda', 'radio', 'rc', 'transmitter'),
       ('ivme', 'acceleration', 'accel', 'التسارع'), ('jiroskop', 'gyro', 'الجيروسكوب'), ('basinc', 'pressure', 'الضغط'),
       ('yatis', 'roll'), ('yunuslama', 'pitch'), ('sapma', 'yaw'), ('hata', 'error', 'خطا'), ('motor', 'engine', 'المحرك')]
_SYN = {}
for _g in SYN:
    for _w in _g: _SYN.setdefault(norm(_w), set()).update(norm(x) for x in _g)


def alts(w):
    """w ve eş anlamlıları (w bir grubun kelimesiyse ya da en az 4 harfle onun başıysa)."""
    out = {w}
    for k, g in _SYN.items():
        if k == w or (len(w) >= 4 and k.startswith(w)): out |= g
    return out


def _ws(a, text):
    return re.search(r'(?<![^\W_])' + re.escape(a), text) is not None


def words(q):
    """Sorgu kelimeleri ('VIBE.VibeX' gibi nokta/alt çizgili ifadeler de bölünür; tırnak içi ifade tek parça)."""
    q = (q or '').strip()
    out = [norm(x) for x in re.findall(r'"([^"]+)"', q)]
    q = re.sub(r'"[^"]+"', ' ', q)
    out += [norm(w) for w in re.split(r'[\s,;.]+', q) if w.strip()]
    return [w for w in out if w]


class Index:
    """Her mesaj için: ad, açıklama (3 dil), alanlar (ad + 3 dilde açıklama)."""

    def __init__(self, M):
        from . import glossary as GL
        self.M = M; self.rows = {}
        for k, m in M.items():
            d = {lg: GL.lt(m.get('desc') or {}, lg) for lg in LANGS}
            fl = []
            for f, x in (m.get('fields') or {}).items():
                fl.append((f, norm(f), {lg: norm(GL.lt(x or {}, lg)) for lg in LANGS}))
            self.rows[k] = (norm(k), {lg: norm(v) for lg, v in d.items()}, fl)

    def match(self, k, ws):
        """Mesaj k bütün kelimeleri (ya da eş anlamlılarını) içeriyorsa {'score', 'fields', 'langs', 'where'}; yoksa None."""
        nk, desc, fl = self.rows[k]
        score = 0.0; fsc = {}; langs = set(); where = set()
        for w in ws:
            best = 0.0
            for a in alts(w):
                ex = 1.0 if a == w else 0.8   # eş anlamlı eşleşme biraz daha düşük puan
                if a != w and not _ws(a, nk + ' ' + ' '.join(desc.values()) + ' ' + ' '.join(nf + ' ' + ' '.join(fd.values()) for _, nf, fd in fl)):
                    continue  # eş anlamlı yalnız kelime başında eşleşir ('rc' → 'source' sayılmaz)
                if nk == a: b = 100
                elif nk.startswith(a): b = 50
                elif a in nk: b = 30
                else: b = 0
                if b: where.add('name'); best = max(best, b * ex)
                for lg in LANGS:
                    if a in desc[lg]:
                        b = 8 + (2 if re.search(r'(?<!\w)' + re.escape(a), desc[lg]) else 0)
                        best = max(best, b * ex); langs.add(lg); where.add('desc')
                for f, nf, fd in fl:
                    if nf == a: hit = 25
                    elif nf.startswith(a): hit = 15
                    elif a in nf: hit = 10
                    else: hit = 0
                    for lg in LANGS:
                        if a in fd[lg]:
                            hit = max(hit, 5); langs.add(lg)
                    if hit:
                        best = max(best, hit * ex); where.add('field'); fsc[f] = fsc.get(f, 0) + hit * ex
            if not best: return None
            score += best
        fields = [f for f, _ in sorted(fsc.items(), key=lambda x: -x[1])]
        return {'score': score, 'fields': fields, 'langs': langs, 'where': where}

    def search(self, q, keys=None):
        """[(ad, eşleşme)] en iyi önce; q boşsa []."""
        ws = words(q)
        if not ws: return []
        out = []
        for k in (keys if keys is not None else self.rows):
            r = self.match(k, ws)
            if r: out.append((k, r))
        out.sort(key=lambda x: (-x[1]['score'], x[0]))
        return out


def highlight(text, q, esc):
    """text içinde sorgu kelimelerini <mark> ile vurgular (aksan duyarsız). esc: HTML kaçış fonksiyonu."""
    ws = set()
    for w in words(q):
        ws |= {a for a in alts(w) if a == w or len(a) >= 3}
    ws = sorted(ws, key=len, reverse=True)
    if not ws or not text: return esc(text or '')
    # karakter karakter normalleştir; her normal karakterin özgün konumu tutulur (hareke/uzunluk değişse de doğru vurgu)
    nt = []; pos = []
    for i, c in enumerate(text):
        for x in norm(c):
            nt.append(x); pos.append(i)
    nt = ''.join(nt)
    spans = []
    for w in ws:
        i = nt.find(w)
        while i >= 0:
            spans.append((pos[i], pos[i + len(w) - 1] + 1)); i = nt.find(w, i + len(w))
    if not spans: return esc(text)
    spans.sort(); merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    out = []; p = 0
    for a, b in merged:
        out.append(esc(text[p:a])); out.append('<span style="background:#FDE047;color:#111">' + esc(text[a:b]) + '</span>'); p = b
    out.append(esc(text[p:]))
    return ''.join(out)
