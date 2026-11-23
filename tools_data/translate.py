"""params_full.json.gz içindeki bütün metinleri (görünen ad, açıklama, seçenek ve bit adları) offline makine
çevirisiyle Türkçe / Arapçaya çevirir. GitHub Actions'ta çalışır; sonuç app/data/params_tx_<dil>.json.gz.

Model: Meta NLLB-200 (CTranslate2, int8). Daha önce çevrilmiş metinler atlanır (artımlı).
Elle yazılmış çeviriler (parametredeki 'tr'/'ar') her zaman makine çevirisinden önce gelir; bunlar burada çevrilmez.
Teknik terimler (arm, failsafe, parametre adları) korunur.
"""
from __future__ import annotations
import gzip, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODES = {'tr': 'tur_Latn', 'ar': 'arb_Arab'}
SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9(])')
# Makinenin "kol / silah" diye çevirmemesi için önce yer tutucuya alınan terimler
PRE = [(re.compile(r'\bdisarm(?:ed|ing)?\b', re.I), 'DISARM'), (re.compile(r'\barm(?:ed|ing)?\b', re.I), 'ARM'),
       (re.compile(r'\bfail-?safe\b', re.I), 'FAILSAFE')]
POST = {'tr': [(r'\bDISARM\b', 'disarm'), (r'\bARM\b', 'arm'), (r'\bFAILSAFE\b', 'failsafe')],
        'ar': [(r'\bDISARM\b', 'نزع التسليح'), (r'\bARM\b', 'التسليح'), (r'\bFAILSAFE\b', 'وضع الطوارئ (failsafe)')]}


def strings(D):
    """(öncelik, metin) — önce kısa/önemli olanlar."""
    out = {}
    for k, p in D['params'].items():
        std = 0 if p.get('usr') == 'Standard' else 1
        for e in [p] + list((p.get('var') or {}).values()):
            if not e: continue
            if e.get('dn') and 'tr' not in p: out.setdefault(e['dn'], 0)
            for f in ('vals', 'bits'):
                for x in (e.get(f) or {}).values(): out.setdefault(x, 1)
            if e.get('d') and 'tr' not in p: out[e['d']] = min(out.get(e['d'], 9), 2 + std)
    for g, x in D['groups'].items():
        if 'tr' not in x and x.get('en'): out.setdefault(x['en'], 0)
    return sorted(out, key=lambda s: (out[s], len(s)))


def main(lang):
    D = json.load(gzip.open(os.path.join(ROOT, 'app', 'data', 'params_full.json.gz'), 'rt', encoding='utf-8'))
    dst = os.path.join(ROOT, 'app', 'data', f'params_tx_{lang}.json.gz')
    have = json.load(gzip.open(dst, 'rt', encoding='utf-8')) if os.path.exists(dst) else {}
    todo = [s for s in strings(D) if s not in have and re.search('[A-Za-z]{2}', s)]
    print(lang, 'total', len(todo), 'have', len(have))
    import ctranslate2, transformers
    mdir = os.environ.get('NLLB_DIR', 'nllb')
    tok = transformers.AutoTokenizer.from_pretrained(os.environ.get('NLLB_HF', 'facebook/nllb-200-distilled-1.3B'), src_lang='eng_Latn')
    tr = ctranslate2.Translator(mdir, device='cpu', compute_type='int8', inter_threads=1, intra_threads=os.cpu_count() or 4)
    tgt = CODES[lang]
    deadline = time.time() + float(os.environ.get('MAX_MIN', '320')) * 60
    t0 = time.time(); done = 0; B = 64
    for i in range(0, len(todo), B):
        if time.time() > deadline: print('deadline reached'); break
        chunk = todo[i:i + B]
        segs = []; idx = []
        for j, s in enumerate(chunk):
            x = s
            for rx, rep in PRE: x = rx.sub(rep, x)
            parts = [p for p in SENT.split(x) if p.strip()] or [x]
            for p in parts: segs.append(p); idx.append(j)
        toks = [tok.convert_ids_to_tokens(tok.encode(p))[:400] for p in segs]
        res = tr.translate_batch(toks, target_prefix=[[tgt]] * len(toks), beam_size=3, max_batch_size=32, max_decoding_length=400,
                                 repetition_penalty=1.1)
        outs = [''] * len(chunk)
        for j, r in zip(idx, res):
            hyp = r.hypotheses[0][1:] if r.hypotheses[0] and r.hypotheses[0][0] == tgt else r.hypotheses[0]
            txt = tok.decode(tok.convert_tokens_to_ids(hyp), skip_special_tokens=True).strip()
            outs[j] = (outs[j] + ' ' + txt).strip()
        for s, o in zip(chunk, outs):
            for a, b in POST[lang]: o = re.sub(a, b, o)
            have[s] = o
        done += len(chunk)
        if (i // B) % 20 == 0:
            el = time.time() - t0
            print(f'{done}/{len(todo)}  {done / max(el, 1):.1f}/s', flush=True)
            with gzip.open(dst, 'wt', encoding='utf-8') as f: json.dump(have, f, ensure_ascii=False, separators=(',', ':'))
    with gzip.open(dst, 'wt', encoding='utf-8', compresslevel=9) as f:
        json.dump(have, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    print('written', dst, len(have), os.path.getsize(dst) // 1024, 'KB')


if __name__ == '__main__':
    main(sys.argv[1])
