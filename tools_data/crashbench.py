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
        if tid in out and out[tid].get('posts'): continue
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
    {'harvest': harvest, 'run': run, 'threads': threads}[sys.argv[1]]()
