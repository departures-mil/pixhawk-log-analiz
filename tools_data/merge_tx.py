"""Parçalı (shard) çeviri çıktılarını birleştirir: /tmp/art/tx_<dil>_<n>/*.json.gz → app/data/params_tx_<dil>.json.gz.
Bir parça eksikse eski çevirideki karşılıklar korunur (hiçbir şey kaybolmaz)."""
import glob, gzip, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.core import glossary as GL

art = sys.argv[1]
for lang in ('tr', 'ar'):
    parts = sorted(glob.glob(os.path.join(art, f'tx_{lang}_*', '*.json.gz')))
    if not parts: print(lang, 'no parts'); continue
    dst = os.path.join(ROOT, 'app', 'data', f'params_tx_{lang}.json.gz')
    old = json.load(gzip.open(dst, 'rt', encoding='utf-8')) if os.path.exists(dst) else {}
    new = {}
    for p in parts:
        new.update(json.load(gzip.open(p, 'rt', encoding='utf-8')))
    out = {k: GL.fix(v, lang) for k, v in old.items() if k != '__gv'}
    out.update({k: v for k, v in new.items() if k != '__gv'})
    out['__gv'] = str(GL.GV) if len(parts) >= 8 else old.get('__gv', '')
    with gzip.open(dst, 'wt', encoding='utf-8', compresslevel=9) as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    print(lang, 'parts', len(parts), 'new', len(new), 'total', len(out))
