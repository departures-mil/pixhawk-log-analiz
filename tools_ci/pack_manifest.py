"""packs.yml yardımcıları.
  python tools_ci/pack_manifest.py piece <id> <klasör> <çıktı.json> [--unzip]   klasördeki dosyalardan paket parçası (model.bin.pNN → parts)
  python tools_ci/pack_manifest.py merge <eski packs.json|-> <parça klasörü> <çıktı packs.json>
Asset adları: <id>--<dosya>; URL: releases/download/packs/<asset>.
"""
import datetime, glob, hashlib, json, os, re, sys

REPO = os.environ.get('GITHUB_REPOSITORY', 'departures-mil/pixhawk-log-analiz')
BASE = f'https://github.com/{REPO}/releases/download/packs/'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()


def piece(pid, d, out, unzip=False):
    files = {}
    for p in sorted(os.listdir(d)):
        fp = os.path.join(d, p)
        if not os.path.isfile(fp) or p.startswith('.'): continue
        m = re.match(r'(.+)\.p(\d\d)$', p)
        asset = f'{pid}--{p}'
        e = {'url': BASE + asset, 'size': os.path.getsize(fp), 'sha256': sha(fp)}
        if m:
            f = files.setdefault(m.group(1), {'path': m.group(1), 'parts': []})
            f['parts'].append(e)
        else:
            files[p] = dict(e, path=p)
            if unzip and p.endswith('.zip'): files[p]['unzip'] = True
    for f in files.values():
        if 'parts' in f:
            f['size'] = sum(x['size'] for x in f['parts'])
            whole = os.environ.get('WHOLE_SHA_' + re.sub(r'\W', '_', f['path']))
            if whole: f['sha256'] = whole
    json.dump({'id': pid, 'version': datetime.date.today().isoformat(), 'files': list(files.values())}, open(out, 'w'), indent=1)
    print(json.dumps(json.load(open(out)), indent=1)[:3000])


def merge(old, pieces, out):
    man = {'packs': {}}
    if old != '-' and os.path.exists(old):
        try: man = json.load(open(old))
        except Exception: pass
    for p in glob.glob(os.path.join(pieces, '**', '*.json'), recursive=True):
        x = json.load(open(p)); man['packs'][x['id']] = {k: v for k, v in x.items() if k != 'id'}
    man['updated'] = datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    json.dump(man, open(out, 'w'), indent=1)
    print(json.dumps({k: len(v['files']) for k, v in man['packs'].items()}))


if __name__ == '__main__':
    if sys.argv[1] == 'piece': piece(sys.argv[2], sys.argv[3], sys.argv[4], '--unzip' in sys.argv)
    else: merge(sys.argv[2], sys.argv[3], sys.argv[4])
