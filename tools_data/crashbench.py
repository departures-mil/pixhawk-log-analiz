"""Gerçek kırım logları test seti: discuss.ardupilot.org'daki kamuya açık konulardan DataFlash (.bin) logları toplar,
programın teşhisini konu başlığından çıkan etiketle karşılaştırır ve doğruluk tablosu yazar.

Adımlar (GitHub Actions'ta):
  python tools_data/crashbench.py harvest   -> /tmp/bench/*.bin + manifest.json
  python tools_data/crashbench.py run       -> tools_data/crashbench/results.json, docs/kirim_test_sonuclari.md, app/data/crashlib.json

Etiket kuralı: başlıkta crash/crashed/fell/flip/fly-away/lost control... geçen konu = 'crash';
first flight/maiden/tuning/review geçip kaza kelimesi geçmeyen = 'normal'. Kök neden ipucu başlık ve ilk mesajdan alınır.
Bu etiketler kesin değildir (forum başlığı); tablo her logu kaynağıyla listeler ki insan gözden geçirebilsin.
"""
from __future__ import annotations
import html, json, os, re, subprocess, sys, time, urllib.parse, urllib.request, zipfile, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORUM = 'https://discuss.ardupilot.org'
BENCH = os.environ.get('BENCH_DIR', '/tmp/bench')
MAX_MB = float(os.environ.get('BENCH_MAX_MB', '160'))
TOTAL_MB = float(os.environ.get('BENCH_TOTAL_MB', '3500'))
N_CRASH = int(os.environ.get('BENCH_N_CRASH', '45')); N_NORMAL = int(os.environ.get('BENCH_N_NORMAL', '20'))
UA = {'User-Agent': 'Mozilla/5.0 (pixhawk-log-analiz crash benchmark; GitHub Actions)', 'Accept': 'application/json'}

CRASH_Q = ['crash log', 'crashed', 'crash analysis', 'crash help log', 'fell from sky', 'fell out of the sky', 'sudden crash',
           'flipped on takeoff', 'fly away', 'flyaway', 'lost control crash', 'crash bin', 'quadplane crash', 'plane crash log',
           'rover crash', 'crash after takeoff', 'crash in auto', 'crash loiter', 'crash rtl', 'motor failure crash',
           'vibration crash', 'gps glitch crash', 'ekf failsafe crash', 'battery failsafe crash', 'compass crash', 'stall crash',
           'crash', 'crash help', 'crash report', 'crash analysis log', 'helicopter crash', 'heli crash', 'vtol crash', 'esc failure',
           'motor stopped mid air', 'dropped from the sky', 'flipped over', 'crash during autotune', 'crash during landing',
           'crash poshold', 'crash althold', 'crash stabilize', 'crash guided', 'crashed log attached', 'tailsitter crash']
NORMAL_Q = ['first flight log review', 'maiden flight log', 'please review my log', 'log review tuning', 'autotune log',
            'tuning log review', 'hover log review', 'check my log first flight', 'quadplane first flight log', 'plane tuning log',
            'log review', 'please check my log', 'vibration log review', 'tuning help log', 'notch filter log', 'autotune results',
            'althold log', 'loiter log', 'quadplane transition log', 'plane autotune', 'first hover', 'maiden quadplane',
            'harmonic notch setup log', 'quicktune', 'review my tune', 'log analysis help', 'flight log check', 'maiden flight']
CRASH_RX = re.compile(r'\b(crash(?:ed|es|ing)?|fell|falls?|fall(?:en|ing)|flip(?:ped|s)?|fly ?away|flew away|lost control|loss of control|'
                      r'went down|dropped (?:out|from)|destroyed|death roll|nose ?dive[ds]?)\b', re.I)
NORMAL_RX = re.compile(r'\b(first flight|maiden|tun(?:e|ing)|autotune|review|check(?:ing)? my log|hover(?:ing)?|log analysis)\b', re.I)
CAUSES = [('vibration', r'vibrat|clipping|vibe'), ('gps', r'\bgps\b|glitch|satellite'), ('ekf', r'\bekf\b|variance'),
          ('battery', r'batter|voltage|brownout|power loss'), ('compass', r'compass|mag(?:netometer)?\b|toilet ?bowl|yaw'),
          ('radio', r'radio failsafe|rc failsafe|signal loss|lost signal|rc loss'), ('motor', r'motor|esc|prop(?:eller)?|desync'),
          ('stall', r'\bstall'), ('control', r'oscillat|tuning|pid')]


def get(url, binary=False, timeout=60, limit_mb=None):
    req = urllib.request.Request(url, headers=UA if not binary else {'User-Agent': UA['User-Agent']})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if not binary: return json.loads(r.read().decode('utf-8', 'replace'))
        out = io.BytesIO(); lim = (limit_mb or MAX_MB) * 1e6
        while True:
            b = r.read(1 << 20)
            if not b: break
            out.write(b)
            if out.tell() > lim: raise RuntimeError('too big')
        return out.getvalue(), r.geturl()


def label(title, text=''):
    t = title or ''
    if CRASH_RX.search(t): return 'crash'
    if NORMAL_RX.search(t) and not CRASH_RX.search(text[:600]): return 'normal'
    return None


def cause_hint(title, text):
    blob = (title + ' ' + text[:1500]).lower()
    for c, rx in CAUSES:
        if re.search(rx, blob): return c
    return None


LINK = re.compile(r'href="([^"]+)"', re.I)


def links(cooked):
    out = []
    for u in LINK.findall(cooked or ''):
        u = html.unescape(u)
        if u.startswith('/'): u = FORUM + u
        lu = u.lower()
        if re.search(r'\.(bin|zip)(\?|$)', lu) and ('/uploads/' in lu or 'dropbox' in lu): out.append(u)
        elif 'drive.google.com' in lu and ('/file/d/' in lu or 'id=' in lu): out.append(u)
        elif 'dropbox.com' in lu and re.search(r'\.(bin|zip)', lu): out.append(u)
    return out


def direct(u):
    m = re.search(r'drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([A-Za-z0-9_-]{20,})', u)
    if m: return f'https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t'
    if 'dropbox.com' in u:
        u = re.sub(r'([?&])dl=0', r'\1dl=1', u)
        if 'dl=1' not in u: u += ('&' if '?' in u else '?') + 'dl=1'
    return u


def to_bin(b):
    if b[:2] == b'\xa3\x95': return b
    if b[:2] == b'PK':
        z = zipfile.ZipFile(io.BytesIO(b))
        for n in sorted(z.namelist(), key=lambda n: -z.getinfo(n).file_size):
            if n.lower().endswith('.bin'):
                d = z.read(n)
                if d[:2] == b'\xa3\x95': return d
    return None


def harvest():
    os.makedirs(BENCH, exist_ok=True)
    mf = os.path.join(BENCH, 'manifest.json')
    man = json.load(open(mf)) if os.path.exists(mf) else {}
    tf = os.path.join(BENCH, 'tried.json')
    seen = set(man) | (set(json.load(open(tf))) if os.path.exists(tf) else set())
    if os.environ.get('BENCH_SKIP_KNOWN'):      # ayrı (dokunulmamış) test seti: geliştirme setindeki konular alınmaz
        seen |= set(labels())
        try:
            import gzip
            seen |= set(json.load(gzip.open(os.path.join(ROOT, 'tools_data', 'crashbench', 'threads.json.gz'), 'rt', encoding='utf-8')))
        except Exception:
            pass
        for extra in ('holdout_threads.json.gz', 'more_threads.json.gz'):   # önceki ek taramalar da tekrar alınmaz
            try: seen |= set(json.load(gzip.open(os.path.join(ROOT, 'tools_data', 'crashbench', extra), 'rt', encoding='utf-8')))
            except Exception: pass
    total = sum(x.get('mb', 0) for x in man.values())
    need = {'crash': N_CRASH - sum(1 for x in man.values() if x['label'] == 'crash'),
            'normal': N_NORMAL - sum(1 for x in man.values() if x['label'] == 'normal')}
    for kind, qs in (('crash', CRASH_Q), ('normal', NORMAL_Q)):
        for q in qs:
            if need[kind] <= 0 or total > TOTAL_MB: break
            for page in range(1, int(os.environ.get('BENCH_PAGES', '3')) + 1):
                if need[kind] <= 0: break
                try:
                    d = get(f'{FORUM}/search.json?q={urllib.parse.quote(q)}&page={page}'); time.sleep(1.2)
                except Exception as e:
                    print('search fail', q, e); time.sleep(5); continue
                tops = d.get('topics') or []
                if not tops: break
                for tp in tops:
                    tid = str(tp['id'])
                    if tid in seen or need[kind] <= 0: continue
                    seen.add(tid)
                    lb = label(tp.get('title', ''))
                    if lb != kind: continue
                    try:
                        T = get(f'{FORUM}/t/{tid}.json'); time.sleep(1.2)
                    except Exception as e:
                        print('topic fail', tid, e); continue
                    posts = (T.get('post_stream') or {}).get('posts') or []
                    first = re.sub('<[^>]+>', ' ', posts[0].get('cooked', '')) if posts else ''
                    lb = label(T.get('title', ''), first)
                    if lb != kind: continue
                    cand = []
                    for p in posts[:6]:
                        if p.get('post_number', 1) == 1 or p.get('username') == (posts[0].get('username') if posts else None):
                            cand += links(p.get('cooked', ''))
                    for u in cand[:3]:
                        try:
                            b, final = get(direct(u), binary=True, timeout=180)
                            data = to_bin(b)
                        except Exception as e:
                            print('  dl fail', u[:90], e); continue
                        if not data or len(data) < 200_000: continue
                        path = os.path.join(BENCH, f'{tid}.bin'); open(path, 'wb').write(data)
                        mb = len(data) / 1e6; total += mb; need[kind] -= 1
                        man[tid] = {'id': tid, 'title': T.get('title'), 'url': f"{FORUM}/t/{T.get('slug', '')}/{tid}", 'log_url': u,
                                    'label': kind, 'cause_hint': cause_hint(T.get('title', ''), first), 'mb': round(mb, 1),
                                    'category_id': T.get('category_id'), 'created': (T.get('created_at') or '')[:10]}
                        print(f'+ {kind:6s} {mb:6.1f} MB  {T.get("title")[:80]}', flush=True)
                        json.dump(man, open(mf, 'w'), indent=1)
                        break
    json.dump(sorted(seen), open(os.path.join(BENCH, 'tried.json'), 'w'))
    json.dump(man, open(mf, 'w'), indent=1)
    print('logs:', len(man), 'total MB', round(total))


PLANE_RX = re.compile(r'plane|quad ?plane|vtol|tail ?sitter|tilt ?rotor|fixed ?wing|glider|flying ?wing', re.I)
PLANE_Q = ['plane crash', 'arduplane crash', 'fixed wing crash', 'quadplane crash log', 'vtol crash log', 'tailsitter crash',
           'tiltrotor crash', 'plane stall crash', 'plane spiral dive', 'plane nose dive', 'plane crashed auto', 'plane crashed rtl',
           'plane crash takeoff', 'hand launch crash', 'catapult launch crash', 'plane crash landing', 'quadplane transition crash',
           'quadplane fell', 'vtol motor failure', 'qassist crash', 'plane lost control', 'flying wing crash', 'glider crash',
           'plane fbwa crash', 'tecs crash', 'airspeed sensor crash', 'plane death spiral', 'plane flyaway', 'plane servo crash',
           'plane first flight log', 'plane autotune log', 'quadplane maiden', 'vtol first flight log', 'plane tuning log review',
           'quadplane tuning log', 'tecs tuning log', 'plane log review', 'quadplane log review', 'tailsitter tuning']


def _topic_ok(tid, title, need, seen, unknown_ok):
    """Başlıktan etiket: crash/normal; Plane kategorisinde başlık bir şey söylemiyorsa 'unknown' (uzman yanıtları karar verir)."""
    if tid in seen: return None
    lb = label(title or '')
    if lb and need.get(lb, 0) > 0: return lb
    if lb is None and unknown_ok and need.get('unknown', 0) > 0 and re.search(r'\b(log|help|problem|issue|why|what happened|analy[sz])', title or '', re.I):
        return 'unknown'
    return None


def _grab(tid, kind, man, mf, need, tot):
    """Konuyu açar, ilk 6 mesajdaki (konu sahibinin) log bağlantılarından ilk geçerli .bin'i indirir. → eklenen MB ya da 0"""
    try:
        T = get(f'{FORUM}/t/{tid}.json'); time.sleep(1.2)
    except Exception as e:
        print('topic fail', tid, e); return 0
    posts = (T.get('post_stream') or {}).get('posts') or []
    first = re.sub('<[^>]+>', ' ', posts[0].get('cooked', '')) if posts else ''
    if kind != 'unknown':
        lb = label(T.get('title', ''), first)
        if lb != kind: return 0
    cand = []
    for p in posts[:6]:
        if p.get('post_number', 1) == 1 or p.get('username') == (posts[0].get('username') if posts else None):
            cand += links(p.get('cooked', ''))
    for u in cand[:3]:
        try:
            b, final = get(direct(u), binary=True, timeout=180)
            data = to_bin(b)
        except Exception as e:
            print('  dl fail', u[:90], e); continue
        if not data or len(data) < 200_000: continue
        open(os.path.join(BENCH, f'{tid}.bin'), 'wb').write(data)
        mb = len(data) / 1e6; need[kind] -= 1
        man[tid] = {'id': tid, 'title': T.get('title'), 'url': f"{FORUM}/t/{T.get('slug', '')}/{tid}", 'log_url': u,
                    'label': kind, 'cause_hint': cause_hint(T.get('title', ''), first), 'mb': round(mb, 1),
                    'category_id': T.get('category_id'), 'created': (T.get('created_at') or '')[:10]}
        print(f'+ {kind:7s} {mb:6.1f} MB  {T.get("title")[:80]}', flush=True)
        json.dump(man, open(mf, 'w'), indent=1)
        return mb
    return 0


def _known():
    import gzip
    seen = set(labels())
    for extra in ('threads.json.gz', 'holdout_threads.json.gz', 'more_threads.json.gz', 'plane_threads.json.gz', 'pn_threads.json.gz'):
        try: seen |= set(json.load(gzip.open(os.path.join(ROOT, 'tools_data', 'crashbench', extra), 'rt', encoding='utf-8')))
        except Exception: pass
    return seen


def harvest_plane():
    """Uçak ağırlıklı geniş tarama: Plane/QuadPlane/VTOL kategorilerinin TÜM sayfaları (en eskiye kadar) + uçak aramaları.
    Kategori listesi başlıkları verdiği için yalnız uygun başlıklı konular açılır. Önceki setlerdeki konular alınmaz."""
    os.makedirs(BENCH, exist_ok=True)
    mf = os.path.join(BENCH, 'manifest.json')
    man = json.load(open(mf)) if os.path.exists(mf) else {}
    seen = set(man) | _known()
    total = sum(x.get('mb', 0) for x in man.values())
    need = {'crash': int(os.environ.get('BENCH_N_CRASH', '400')), 'normal': int(os.environ.get('BENCH_N_NORMAL', '150')),
            'unknown': int(os.environ.get('BENCH_N_UNK', '150'))}
    for x in man.values(): need[x['label']] = need.get(x['label'], 0) - 1
    deadline = time.time() + float(os.environ.get('BENCH_MINUTES', '250')) * 60
    cats = []
    try:
        C = get(f'{FORUM}/categories.json?include_subcategories=true'); time.sleep(1.2)
        def walk(cs, parent=''):
            for c in cs:
                nm = (parent + ' / ' + (c.get('name') or '')).strip(' /')
                if PLANE_RX.search(nm) or PLANE_RX.search(c.get('slug') or ''): cats.append((c['id'], c.get('slug'), nm))
                walk(c.get('subcategory_list') or [], nm)
        walk((C.get('category_list') or {}).get('categories') or [])
        for c in list(cats):          # alt kategoriler ayrıca listelenmemişse
            try:
                S = get(f'{FORUM}/c/{c[0]}/show.json'); time.sleep(1.2)
                for sid in (S.get('category') or {}).get('subcategory_ids') or []:
                    if sid not in {x[0] for x in cats}: cats.append((sid, '', c[2] + ' / sub'))
            except Exception: pass
    except Exception as e:
        print('categories fail', e)
    print('plane categories:', cats, flush=True)
    full = lambda: total > TOTAL_MB or time.time() > deadline or all(v <= 0 for v in need.values())
    # 1) uçak aramaları (alaka sırası)
    for q in PLANE_Q:
        if full(): break
        for page in range(1, int(os.environ.get('BENCH_PAGES', '10')) + 1):
            if full(): break
            try:
                d = get(f'{FORUM}/search.json?q={urllib.parse.quote(q)}&page={page}'); time.sleep(1.2)
            except Exception as e:
                print('search fail', q, e); time.sleep(5); continue
            tops = d.get('topics') or []
            if not tops: break
            for tp in tops:
                tid = str(tp['id']); kind = _topic_ok(tid, tp.get('title'), need, seen, False)
                seen.add(tid)
                if kind: total += _grab(tid, kind, man, mf, need, total)
    # 2) kategorilerin bütün sayfaları
    for cid, slug, nm in cats:
        page = 0
        while not full():
            try:
                L = get(f'{FORUM}/c/{slug}/{cid}.json?page={page}' if slug else f'{FORUM}/c/{cid}.json?page={page}'); time.sleep(1.2)
            except Exception as e:
                print('cat fail', cid, page, e); break
            tops = (L.get('topic_list') or {}).get('topics') or []
            if not tops: break
            for tp in tops:
                if full(): break
                tid = str(tp['id']); kind = _topic_ok(tid, tp.get('title'), need, seen, True)
                seen.add(tid)
                if kind: total += _grab(tid, kind, man, mf, need, total)
            page += 1
            if page % 20 == 0: print(f'  cat {nm} page {page}  logs={len(man)} MB={round(total)}', flush=True)
    json.dump(man, open(mf, 'w'), indent=1)
    print('logs:', len(man), 'total MB', round(total), 'need left', need)


PN_Q = ['plane first flight log', 'maiden flight log plane', 'plane autotune log', 'plane autotune results', 'quadplane autotune',
        'qautotune log', 'quicktune quadplane', 'tecs tuning', 'tecs tuning log', 'plane log review', 'please review my log plane',
        'check my log plane', 'quadplane log review', 'vtol log review', 'vtol transition log', 'transition tuning quadplane',
        'tailsitter tuning log', 'tiltrotor tuning log', 'flying wing tuning log', 'plane tuning advice log', 'plane pid tuning log',
        'airspeed calibration log', 'plane waypoint mission log', 'auto landing log plane', 'plane loiter tuning', 'l1 tuning',
        'npfg tuning', 'plane vibration log', 'quadplane hover vibration', 'plane oscillation log', 'quadplane hover tuning log',
        'plane long range flight log', 'fpv wing log', 'glider log', 'plane battery consumption log', 'plane log analysis help',
        'arduplane log', 'quadplane log', 'vtol flight log', 'plane flight log']
PN_REL = re.compile(r'\bplane\b.*\b\d\.\d+(\.\d+)?\b.*\b(beta|release|stable|rc\d?)\b|\b(beta|release)\b.*\bplane\b.*\d\.\d', re.I)
PN_BAD = re.compile(r'\b(crash(?:ed|es|ing)?|fell|flip(?:ped)?|fly ?away|lost control|loss of control|destroyed|nose ?dived?|'
                    r'spiral(?:led)?|death roll|went down|dropped out of|hit the ground|broke)\b', re.I)


def harvest_planenormal():
    """Plane NORMAL uçuş taraması. (1) Plane sürüm/beta konuları: test pilotlarının her yazısındaki log ayrı örnek
    ('r<konu>_<yazı>'), bağlamı = o yazı + ona verilen cevaplar; (2) ayar/ilk uçuş/log inceleme aramaları (başlık ve ilk yazıda
    kırım sözcüğü olmayanlar). Konu metinleri doğrudan BENCH_THREADS_OUT'a yazılır (etiketleme için)."""
    import gzip
    os.makedirs(BENCH, exist_ok=True)
    mf = os.path.join(BENCH, 'manifest.json'); man = json.load(open(mf)) if os.path.exists(mf) else {}
    out_p = os.path.join(ROOT, 'tools_data', 'crashbench', os.environ.get('BENCH_THREADS_OUT', 'pn_threads.json.gz'))
    th = json.load(gzip.open(out_p, 'rt', encoding='utf-8')) if os.path.exists(out_p) else {}
    seen = set(man) | _known()
    total = sum(x.get('mb', 0) for x in man.values()); n_max = int(os.environ.get('BENCH_N_NORMAL', '400'))
    deadline = time.time() + float(os.environ.get('BENCH_MINUTES', '280')) * 60
    full = lambda: total > TOTAL_MB or time.time() > deadline or len(man) >= n_max
    def save():
        json.dump(man, open(mf, 'w'), indent=1)
        with gzip.open(out_p, 'wt', encoding='utf-8') as f: json.dump(th, f, ensure_ascii=False)
    def row(p):
        likes = sum(a.get('count', 0) for a in (p.get('actions_summary') or []) if a.get('id') == 2)
        return {'n': p.get('post_number'), 'u': p.get('username'), 'tl': p.get('trust_level'), 'r': p.get('reply_to_post_number'),
                'staff': bool(p.get('staff') or p.get('moderator') or p.get('admin')), 'likes': likes,
                'acc': bool(p.get('accepted_answer')), 'd': (p.get('created_at') or '')[:10], 'x': _plain(p.get('cooked'))[:3500]}
    def all_posts(tid, cap=1500):
        T = get(f'{FORUM}/t/{tid}.json'); time.sleep(1.2)
        posts = list((T.get('post_stream') or {}).get('posts') or [])
        ids = [i for i in ((T.get('post_stream') or {}).get('stream') or []) if i not in {p['id'] for p in posts}][:cap]
        for k in range(0, len(ids), 20):
            if time.time() > deadline: break
            q = '&'.join(f'post_ids[]={i}' for i in ids[k:k + 20])
            try:
                more = get(f'{FORUM}/t/{tid}/posts.json?{q}'); time.sleep(1.2)
                posts += (more.get('post_stream') or {}).get('posts') or []
            except Exception as e:
                print('  more fail', tid, e)
        return T, sorted(posts, key=lambda p: p.get('post_number', 0))
    def fetch(u):
        try:
            b, _ = get(direct(u), binary=True, timeout=180, limit_mb=MAX_MB)
            d = to_bin(b)
            return d if d and len(d) >= 200_000 else None
        except Exception as e:
            print('  dl fail', u[:90], e); return None
    def add(key, d, title, url, u, src, extra=None):
        nonlocal total
        open(os.path.join(BENCH, f'{key}.bin'), 'wb').write(d); mb = len(d) / 1e6; total += mb
        man[key] = {'id': key, 'title': title, 'url': url, 'log_url': u, 'label': 'unknown', 'src': src, 'mb': round(mb, 1), **(extra or {})}
        print(f'+ {src:4s} {mb:6.1f} MB  {title[:70]}', flush=True)
    # 1) sürüm / beta konuları
    rel = {}
    for q in ['Plane beta', 'Plane stable release', 'ArduPlane beta', 'Plane 4.0', 'Plane 4.1', 'Plane 4.2', 'Plane 4.3', 'Plane 4.4',
              'Plane 4.5', 'Plane 4.6', 'Plane 4.7', 'Plane 3.9', 'Plane 3.8', 'plane release candidate']:
        for page in (1, 2, 3):
            try:
                d = get(f'{FORUM}/search.json?q={urllib.parse.quote(q + " in:title")}&page={page}'); time.sleep(1.2)
            except Exception as e:
                print('search fail', q, e); break
            tops = d.get('topics') or []
            if not tops: break
            for tp in tops:
                if PN_REL.search(tp.get('title') or ''): rel[str(tp['id'])] = tp.get('title')
    print('release topics:', len(rel), flush=True)
    for tid, title in sorted(rel.items(), key=lambda x: -int(x[0])):
        if full(): break
        try: T, posts = all_posts(tid)
        except Exception as e: print('rel fail', tid, e); continue
        url = f"{FORUM}/t/{T.get('slug', '')}/{tid}"
        for i, p in enumerate(posts):
            if full(): break
            n = p.get('post_number'); key = f'r{tid}_{n}'
            if n == 1 or key in seen: continue
            txt = _plain(p.get('cooked'))
            if PN_BAD.search(txt[:1500]): continue
            ls = links(p.get('cooked', ''))
            if not ls: continue
            seen.add(key)
            d = next((x for x in (fetch(u) for u in ls[:2]) if x), None)
            if not d: continue
            ctx = [row(p)] + [row(q) for q in posts[i + 1:i + 40] if q.get('reply_to_post_number') == n or
                              (q.get('username') == p.get('username'))][:10]
            add(key, d, f'{title} #{n}', f'{url}/{n}', ls[0], 'rel')
            th[key] = {'title': f'{title} #{n}', 'url': f'{url}/{n}', 'posts': ctx}
            save()
    # 2) ayar / ilk uçuş / log inceleme aramaları
    for q in PN_Q:
        if full(): break
        for page in range(1, int(os.environ.get('BENCH_PAGES', '8')) + 1):
            if full(): break
            try:
                d = get(f'{FORUM}/search.json?q={urllib.parse.quote(q)}&page={page}'); time.sleep(1.2)
            except Exception as e:
                print('search fail', q, e); time.sleep(5); continue
            tops = d.get('topics') or []
            if not tops: break
            for tp in tops:
                if full(): break
                tid = str(tp['id']); title = tp.get('title') or ''
                if tid in seen or PN_BAD.search(title): seen.add(tid); continue
                seen.add(tid)
                try: T, posts = all_posts(tid, cap=60)
                except Exception as e: print('topic fail', tid, e); continue
                if not posts: continue
                if PN_BAD.search(_plain(posts[0].get('cooked'))[:1500]): continue
                if not PLANE_RX.search(title + ' ' + _plain(posts[0].get('cooked'))[:1500] + ' ' + str(T.get('category_id'))): continue
                op = posts[0].get('username'); cand = []
                for p in posts[:6]:
                    if p.get('post_number') == 1 or p.get('username') == op: cand += links(p.get('cooked', ''))
                d = next((x for x in (fetch(u) for u in cand[:3]) if x), None)
                if not d: continue
                url = f"{FORUM}/t/{T.get('slug', '')}/{tid}"
                add(tid, d, title, url, cand[0], 'srch', {'category_id': T.get('category_id'), 'created': (T.get('created_at') or '')[:10]})
                th[tid] = {'title': title, 'url': url, 'posts': [row(p) for p in posts[:80]]}
                save()
    save()
    print('logs:', len(man), 'MB', round(total))


def refetch():
    """Bir tarama manifestindeki logları (log_url) yeniden indirir: BENCH_MANIFEST=tools_data/crashbench/pn_manifest.json."""
    os.makedirs(BENCH, exist_ok=True)
    src = os.path.join(ROOT, os.environ.get('BENCH_MANIFEST', 'tools_data/crashbench/pn_manifest.json'))
    man = json.load(open(src)); ok = {}
    for k, m in man.items():
        p = os.path.join(BENCH, f'{k}.bin')
        if os.path.exists(p): ok[k] = m; continue
        try:
            b, _ = get(direct(m['log_url']), binary=True, timeout=180)
            d = to_bin(b)
        except Exception as e:
            print('  dl fail', k, e); continue
        if not d: print('  not bin', k); continue
        open(p, 'wb').write(d); ok[k] = m
        print(f'+ {k} {len(d) / 1e6:.1f} MB', flush=True)
        time.sleep(0.5)
    json.dump(ok, open(os.path.join(BENCH, 'manifest.json'), 'w'), indent=1)
    print('refetched', len(ok), 'of', len(man))


def harvest_gh():
    """ArduPilot GitHub hata kayıtları: gövdesinde .bin/.zip log bağlantısı olan kırım/uçuş sorunları + geliştirici yorumları.
    Kimlik 'gh<numara>'. Uzman yanıtları doğrudan plane_threads dosyasına eklenir (BENCH_THREADS_OUT)."""
    import gzip
    tok = os.environ.get('GH_TOKEN', '')
    H = {'User-Agent': UA['User-Agent'], 'Accept': 'application/vnd.github+json', **({'Authorization': f'Bearer {tok}'} if tok else {})}
    def gj(url):
        with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60) as r: return json.loads(r.read())
    os.makedirs(BENCH, exist_ok=True)
    mf = os.path.join(BENCH, 'manifest.json'); man = json.load(open(mf)) if os.path.exists(mf) else {}
    out_p = os.path.join(ROOT, 'tools_data', 'crashbench', os.environ.get('BENCH_THREADS_OUT', 'plane_threads.json.gz'))
    th = json.load(gzip.open(out_p, 'rt', encoding='utf-8')) if os.path.exists(out_p) else {}
    seen = set(man) | _known(); n_max = int(os.environ.get('BENCH_N_GH', '120')); got = 0
    QS = ['crash log', 'crashed', 'plane crash', 'quadplane crash', 'fell', 'lost control', 'flipped', 'log attached crash', 'vtol crash']
    for q in QS:
        for page in range(1, 11):
            if got >= n_max: break
            try:
                d = gj('https://api.github.com/search/issues?per_page=50&page=%d&q=%s' % (page, urllib.parse.quote(f'repo:ArduPilot/ardupilot is:issue {q}')))
                time.sleep(2.5)
            except Exception as e:
                print('gh search fail', q, e); time.sleep(20); break
            items = d.get('items') or []
            if not items: break
            for it in items:
                tid = 'gh%d' % it['number']
                if tid in seen: continue
                seen.add(tid)
                body = it.get('body') or ''
                lb = label(it.get('title') or '', body)
                if lb not in ('crash', 'normal'): continue
                urls = re.findall(r'https?://[^\s)\]"\'<>]+', body)
                cand = [u for u in urls if re.search(r'\.(bin|zip)(\?|$)', u.lower()) or 'drive.google.com' in u or
                        ('github.com/user-attachments/files' in u)]
                for u in cand[:3]:
                    try:
                        b, _ = get(direct(u), binary=True, timeout=180); data = to_bin(b)
                    except Exception as e:
                        print('  dl fail', u[:90], e); continue
                    if not data or len(data) < 200_000: continue
                    open(os.path.join(BENCH, f'{tid}.bin'), 'wb').write(data); mb = len(data) / 1e6; got += 1
                    man[tid] = {'id': tid, 'title': it.get('title'), 'url': it.get('html_url'), 'log_url': u, 'label': lb,
                                'cause_hint': cause_hint(it.get('title') or '', body), 'mb': round(mb, 1), 'category_id': 'github',
                                'created': (it.get('created_at') or '')[:10]}
                    rows = [{'n': 1, 'u': (it.get('user') or {}).get('login'), 'tl': 1, 'staff': False, 'likes': 0, 'acc': False,
                             'd': (it.get('created_at') or '')[:10], 'x': body[:3500]}]
                    try:
                        cm = gj(it['comments_url'] + '?per_page=60'); time.sleep(1)
                        for i, c in enumerate(cm, 2):
                            aa = c.get('author_association') or ''
                            rows.append({'n': i, 'u': (c.get('user') or {}).get('login'), 'tl': 3 if aa in ('MEMBER', 'OWNER', 'COLLABORATOR') else 1,
                                         'staff': aa in ('MEMBER', 'OWNER'), 'likes': (c.get('reactions') or {}).get('+1', 0), 'acc': False,
                                         'd': (c.get('created_at') or '')[:10], 'x': (c.get('body') or '')[:3500]})
                    except Exception as e:
                        print('  comments fail', tid, e)
                    th[tid] = {'title': it.get('title'), 'url': it.get('html_url'), 'posts': rows}
                    print(f'+ gh {lb:6s} {mb:6.1f} MB  {it.get("title", "")[:80]}', flush=True)
                    json.dump(man, open(mf, 'w'), indent=1)
                    break
    with gzip.open(out_p, 'wt', encoding='utf-8') as f: json.dump(th, f, ensure_ascii=False)
    json.dump(man, open(mf, 'w'), indent=1)
    print('github logs:', got)


def _plain(cooked):
    t = re.sub(r'<aside class="quote.*?</aside>', ' ', cooked or '', flags=re.S)   # alıntıları at
    t = re.sub(r'<(br|p|li|div)[^>]*>', '\n', t); t = re.sub('<[^>]+>', ' ', t)
    return re.sub(r'[ \t]+', ' ', html.unescape(t)).strip()


def threads():
    """Etiket temizliği için her konunun TÜM yanıtlarını (uzman cevapları dahil) indirir →
    tools_data/crashbench/threads.json.gz. Etiketler bu metinlerden elle çıkarılıp labels.json'a yazılır."""
    import gzip
    man = json.load(open(os.path.join(BENCH, 'manifest.json')))
    out_p = os.path.join(ROOT, 'tools_data', 'crashbench', os.environ.get('BENCH_THREADS_OUT', 'threads.json.gz'))
    out = {}
    if os.path.exists(out_p):
        try: out = json.load(gzip.open(out_p, 'rt', encoding='utf-8'))
        except Exception: out = {}
    for tid in sorted(man):
        if (tid in out and out[tid].get('posts')) or tid.startswith('gh'): continue
        try:
            T = get(f'{FORUM}/t/{tid}.json'); time.sleep(1.2)
            posts = list((T.get('post_stream') or {}).get('posts') or [])
            ids = [i for i in ((T.get('post_stream') or {}).get('stream') or []) if i not in {p['id'] for p in posts}][:60]
            for k in range(0, len(ids), 20):
                q = '&'.join(f'post_ids[]={i}' for i in ids[k:k + 20])
                try:
                    more = get(f'{FORUM}/t/{tid}/posts.json?{q}'); time.sleep(1.2)
                    posts += (more.get('post_stream') or {}).get('posts') or []
                except Exception as e:
                    print('  more fail', tid, e)
            rows = []
            for p in sorted(posts, key=lambda p: p.get('post_number', 0))[:80]:
                likes = sum(a.get('count', 0) for a in (p.get('actions_summary') or []) if a.get('id') == 2)
                rows.append({'n': p.get('post_number'), 'u': p.get('username'), 'tl': p.get('trust_level'),
                             'staff': bool(p.get('staff') or p.get('moderator') or p.get('admin')), 'likes': likes,
                             'acc': bool(p.get('accepted_answer')), 'd': (p.get('created_at') or '')[:10], 'x': _plain(p.get('cooked'))[:3500]})
            out[tid] = {'title': T.get('title'), 'url': man[tid]['url'], 'posts': rows}
            print(f'{tid}: {len(rows)} posts  {T.get("title", "")[:70]}', flush=True)
        except Exception as e:
            print('thread fail', tid, e)
    os.makedirs(os.path.dirname(out_p), exist_ok=True)
    with gzip.open(out_p, 'wt', encoding='utf-8') as f: json.dump(out, f, ensure_ascii=False)
    print('threads:', len(out))


def _one(tid, m):
    p = os.path.join(BENCH, f'{tid}.bin'); out = os.path.join(BENCH, f'{tid}.json')
    if not os.path.exists(p): return None
    t0 = time.time()
    try:
        subprocess.run([sys.executable, os.path.join(ROOT, 'run.py'), '--analyze', p, '--json', out], timeout=900, check=True,
                       capture_output=True)
        d = json.load(open(out, encoding='utf-8'))
        v = d.get('verdict') or {}; r = d.get('root') or {}
        m = dict(m)
        if m['label'] == 'normal' and any(e.get('k') == 'cr_msg' and 'crash: disarming' in str((e.get('a') or {}).get('msg', '')).lower()
                                          for e in v.get('evidence', [])):
            m['label'] = 'crash'; m['label_src'] = 'autopilot'   # otopilot kırımı kendisi kaydetmiş: forum etiketi yanlış
        return {**m, 'vehicle': d.get('vehicle'), 'got': v.get('kind'), 'got_cause': r.get('cause'), 'others': r.get('others'),
                'overall': d.get('overall'), 'dur': round(d.get('duration') or 0), 'sec': round(time.time() - t0, 1),
                'verdict': v, 'facts': {k: x for k, x in (d.get('facts') or {}).items() if not isinstance(x, (list, dict))},
                'health': d.get('health'), 'events': [e for e in d.get('events', []) if e.get('sev', 0) >= 2][:25]}
    except Exception as e:
        return {**m, 'got': 'error', 'err': str(e)[:300]}


def labels():
    """Elle temizlenmiş etiketler (uzman yanıtlarından): {id: {label, cause, alt, src, note}}"""
    p = os.path.join(ROOT, 'tools_data', 'crashbench', 'labels.json')
    if not os.path.exists(p): return {}
    d = json.load(open(p, encoding='utf-8'))
    return d.get('labels', d) if isinstance(d, dict) else {}


def run():
    from concurrent.futures import ThreadPoolExecutor
    man = json.load(open(os.path.join(BENCH, 'manifest.json')))
    lab = labels()
    for tid, l in lab.items():
        if tid in man:
            man[tid] = {**man[tid], 'label_forum': man[tid]['label'], 'hint_forum': man[tid].get('cause_hint'),
                        'label': l.get('label', man[tid]['label']), 'cause_hint': l.get('cause'), 'cause_alt': l.get('alt') or [],
                        'label_src': 'expert', 'exclude': l.get('exclude', False), 'note': l.get('note', '')}
    jobs = int(os.environ.get('BENCH_JOBS', '2'))
    res = []
    with ThreadPoolExecutor(jobs) as ex:
        for r in ex.map(lambda kv: _one(*kv), sorted(man.items())):
            if r is None: continue
            res.append(r)
            print(f"{r['id']}: label={r['label']} got={r.get('got')} cause={r.get('got_cause')} hint={r.get('cause_hint')}", flush=True)
    write(res)


def score(res):
    ok = [r for r in res if r.get('got') not in (None, 'error') and not r.get('exclude')]
    def pos(r): return r['got'] == 'crash' or (r['got'] == 'incident' and (r.get('verdict') or {}).get('severity') != 'minor')
    tp = sum(1 for r in ok if r['label'] == 'crash' and pos(r)); fn = sum(1 for r in ok if r['label'] == 'crash' and not pos(r))
    fp = sum(1 for r in ok if r['label'] == 'normal' and pos(r)); tn = sum(1 for r in ok if r['label'] == 'normal' and not pos(r))
    ch = [r for r in ok if r['label'] == 'crash' and r.get('cause_hint')]
    def hit(r):
        want = {r['cause_hint'], *(r.get('cause_alt') or [])}
        return r.get('got_cause') in want
    cm = sum(1 for r in ch if hit(r))
    cm2 = sum(1 for r in ch if hit(r) or any(c in (r.get('others') or []) for c in {r['cause_hint'], *(r.get('cause_alt') or [])}))
    hard = sum(1 for r in ok if r['label'] == 'crash' and r['got'] == 'crash')
    fcr = sum(1 for r in ok if r['label'] == 'normal' and r['got'] == 'crash')
    return {'n': len(ok), 'errors': len(res) - len(ok), 'tp': tp, 'fn': fn, 'fp': fp, 'tn': tn,
            'crash_verdict': hard, 'false_crash': fcr,
            'accuracy': round((tp + tn) / max(len(ok), 1), 3), 'recall_crash': round(tp / max(tp + fn, 1), 3),
            'specificity': round(tn / max(tn + fp, 1), 3), 'cause_n': len(ch), 'cause_match': cm, 'cause_acc': round(cm / max(len(ch), 1), 3),
            'cause_any': cm2, 'cause_any_acc': round(cm2 / max(len(ch), 1), 3),
            'labels': 'expert' if any(r.get('label_src') == 'expert' for r in ok) else 'forum-title'}


def write(res):
    s = score(res)
    os.makedirs(os.path.join(ROOT, 'tools_data', 'crashbench'), exist_ok=True)
    prev = os.path.join(ROOT, 'tools_data', 'crashbench', 'results.json')
    hist = []
    if os.path.exists(prev):
        try: hist = json.load(open(prev, encoding='utf-8')).get('history', [])
        except Exception: pass
    hist = [h for h in hist if h.get('tag') not in ('dev', '')]          # geliştirme ara ölçümleri geçmişe yazılmaz
    tag = os.environ.get('BENCH_TAG', '') or 'dev'
    hist.append({'date': time.strftime('%Y-%m-%d %H:%M'), 'tag': tag, **s})
    json.dump({'score': s, 'history': hist[-20:], 'results': res}, open(prev, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    lib = [{k: r.get(k) for k in ('id', 'title', 'url', 'log_url', 'label', 'cause_hint', 'mb', 'vehicle', 'got', 'got_cause', 'dur', 'created')}
           for r in res if r.get('got') not in (None, 'error')]
    json.dump({'score': s, 'date': hist[-1]['date'], 'cases': lib}, open(os.path.join(ROOT, 'app', 'data', 'crashlib.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)
    os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
    L = ['# Gerçek kırım logları ile teşhis doğruluğu', '',
         f"Kaynak: discuss.ardupilot.org kamuya açık konular · Tarih: {hist[-1]['date']} · Log sayısı: {s['n']} (+{s['errors']} okunamayan)", '',
         ("Etiket kaynağı: **uzman etiketleri** — her konudaki deneyimli/ekip üyelerinin yanıtları elle okunarak "
          "kırım/normal ve kök neden belirlendi (tools_data/crashbench/labels.json). Kök neden puanı yalnız uzmanların "
          "bir nedende birleştiği kırımlar üzerinden hesaplanır." if s.get('labels') == 'expert' else
          "Etiket kaynağı: forum başlığı (gürültülü)."), '',
         '| Ölçüt | Değer |', '|---|---|',
         f"| Genel doğruluk (kırım/olay ↔ normal) | %{s['accuracy']*100:.0f} |",
         f"| Kırımı yakalama oranı (duyarlılık) | %{s['recall_crash']*100:.0f} ({s['tp']}/{s['tp']+s['fn']}) |",
         f"| Normal uçuşu doğru tanıma (özgüllük) | %{s['specificity']*100:.0f} ({s['tn']}/{s['tn']+s['fp']}) |",
         f"| Kesin 'kırım' kararı verilen kırım logları | {s.get('crash_verdict', '-')}/{s['tp']+s['fn']} |",
         f"| Normal logda yanlış 'kırım' kararı | {s.get('false_crash', '-')} |",
         f"| Kök neden uyumu (ana neden) | %{s['cause_acc']*100:.0f} ({s['cause_match']}/{s['cause_n']}) |",
         f"| Kök neden uyumu (ana veya ikincil nedenlerde) | %{s.get('cause_any_acc', 0)*100:.0f} ({s.get('cause_any', '-')}/{s['cause_n']}) |", '',
         '## Sürüm geçmişi', '', '| Tarih | Sürüm / etiket | Log | Doğruluk | Duyarlılık | Özgüllük | Kök neden |', '|---|---|---|---|---|---|---|']
    for h in hist[-10:]:
        L.append(f"| {h['date']} | {h.get('tag') or h.get('labels') or '-'} | {h['n']} | %{h['accuracy']*100:.0f} | %{h['recall_crash']*100:.0f} | "
                 f"%{h['specificity']*100:.0f} | %{h['cause_acc']*100:.0f} |")
    try:
        cv = json.load(open(os.path.join(ROOT, 'app', 'data', 'ml_model.json'), encoding='utf-8'))
        c = cv['cv']
        L += ['', '## Öğrenen ikinci görüş (ML)', '',
              f"Aynı uzman etiketli {cv['n']} log üzerinde, her log dışarıda bırakılarak (leave-one-out) eğitilip ölçüldü. "
              f"Model {'**kullanımda**' if cv.get('use') else 'henüz kullanılmıyor'}: yalnız sınırdaki kararları düzeltir "
              "(kanıtsız 'sorunlu' → normal, model çok eminse normal → sorunlu); kesin kırım kanıtına dokunmaz.", '',
              '| | Doğruluk | Duyarlılık | Özgüllük |', '|---|---|---|---|',
              f"| Yalnız kurallar | %{c['rule_acc']*100:.0f} | %{c['rule_recall']*100:.0f} | %{c['rule_spec']*100:.0f} |",
              f"| Kurallar + model | %{c['combined_acc']*100:.0f} | %{c['combined_recall']*100:.0f} | %{c['combined_spec']*100:.0f} |"]
    except Exception:
        pass
    L += ['', '## Log listesi', '', '| Konu | Araç | Etiket | Program | Kök neden (program) | Kök neden (uzman) | Süre |', '|---|---|---|---|---|---|---|']
    for r in sorted(res, key=lambda r: (r['label'], r.get('got') or '')):
        ps = r.get('got') == 'crash' or (r.get('got') == 'incident' and (r.get('verdict') or {}).get('severity') != 'minor')
        mark = '✅' if ps == (r['label'] == 'crash') else '❌'
        ttl = (r.get('title') or '').replace('|', '/')[:70]
        L.append(f"| [{ttl}]({r['url']}) | {r.get('vehicle') or '-'} | {r['label']} | {mark} {r.get('got')} | {r.get('got_cause') or '-'} | "
                 f"{r.get('cause_hint') or '-'} | {r.get('dur') or '-'} sn |")
    open(os.path.join(ROOT, 'docs', 'kirim_test_sonuclari.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(json.dumps(s, indent=1))


if __name__ == '__main__':
    {'harvest': harvest, 'run': run, 'threads': threads, 'plane': harvest_plane, 'github': harvest_gh, 'planenormal': harvest_planenormal, 'refetch': refetch}[sys.argv[1]]()
