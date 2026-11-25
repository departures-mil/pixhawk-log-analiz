"""Telefonla sınav ve telefonla optik okuma (aynı Wi-Fi / modem, internet gerekmez).

Sınav Hazırlama Sistemi'nin (departures-mil/sinav-hazirlama, src/canli.js + canli-sayfa.js) Python karşılığı:
- Eğitimcinin bilgisayarı küçük bir web sunucusu açar; öğrenciler telefon tarayıcısından adrese (ya da QR'a) girer,
  ad + numara + 4 haneli sınav kodu ile başlar. Süre her öğrencinin girişinden işler; bitince sunucuda teslim edilir.
- Doğru cevaplar telefona gönderilmez. Soru ve şık sırası öğrenciye göre karışabilir (cevaplar asıl sıraya çevrilir).
- Cevaplar her işaretlemede bilgisayara yazılır (telefon kapansa da kaybolmaz); teslimde sonuç arşive (eşitlenir) kaydedilir.
- Aynı numarayla ikinci telefondan girilemez (eğitimci izin verebilir).
- /okut: eğitimcinin telefonu optik formların fotoğrafını yollar; bilgisayar hemen okur, puanlar, kaydeder.
- Görseller /img/<n> adresinden (yalnız açık oturumun soruları).
Oturum dosyası: <veri>/canli-sinav/<oturum>.json (atomik yazılır; silinmez).
"""
from __future__ import annotations
import json, os, random, secrets, socket, threading, time, base64
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORTS = [47880, 47881, 47882, 47883, 47884, 47885]
MAX_BODY = 12 * 1024 * 1024


def addrs():
    """Yerel ağ IPv4 adresleri (sanal bağdaştırıcılar sona)."""
    out = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.255.255.255', 1)); out.append(s.getsockname()[0]); s.close()
    except Exception:
        pass
    try:
        for a in socket.gethostbyname_ex(socket.gethostname())[2]:
            if a not in out and not a.startswith('127.'): out.append(a)
    except Exception:
        pass
    return out or ['127.0.0.1']


class Canli:
    def __init__(self, archive, data_dir, on_change=None):
        self.archive = archive; self.dir = os.path.join(data_dir, 'canli-sinav'); os.makedirs(self.dir, exist_ok=True)
        self.on_change = on_change; self.s = None; self.srv = None; self.port = 0; self.lock = threading.RLock()
        self.tries = {}; self.scan_exam = None; self.scan_students = []; self.scans = []
        threading.Thread(target=self._ticker, daemon=True).start()

    # ---------------------------------------------------------------- oturum
    def start(self, exam, students=(), dur=None, shuffle_q=True, shuffle_o=True):
        from . import exam as X
        exam = X.ensure_code(self.archive, exam)
        with self.lock:
            self.s = {'id': time.strftime('%Y-%m-%d-%H-%M-%S') + '-' + secrets.token_hex(3), 'created': time.time(), 'exam_id': exam['id'],
                      'title': exam.get('title', ''), 'code': exam['code'], 'open': True,
                      'dur': int(exam.get('time_limit_min', 0) if dur is None else dur), 'shuffle_q': bool(shuffle_q), 'shuffle_o': bool(shuffle_o),
                      'lang': exam.get('lang', 'tr'), 'students': {}, 'roster': list(students)}
            self.exam = exam
        self.set_scan(exam, students)
        self._listen(); self._save(); self._changed()
        return self.status()

    def set_scan(self, exam, students=()):
        """Telefonla optik okuma hangi sınava gidecek (sınav kodu bu sınavın kodu olmalı)."""
        from . import exam as X
        self.scan_exam = X.ensure_code(self.archive, exam); self.scan_students = list(students)
        self._listen()
        return self.status()

    def set_open(self, on):
        with self.lock:
            if self.s: self.s['open'] = bool(on)
        self._changed()

    def allow_re(self, sid, reopen=False):
        with self.lock:
            st = (self.s or {}).get('students', {}).get(sid)
            if st: st['allow_re'] = True; st['reopen'] = bool(reopen)
        self._changed()

    def finish_all(self):
        with self.lock:
            if self.s:
                for st in self.s['students'].values():
                    if not st['done']: self._finish(st)
                self.s['open'] = False
        self._save(); self._changed()

    def stop(self):
        with self.lock:
            if self.s: self.s['open'] = False; self._save()
            self.s = None; self.scan_exam = None
        if self.srv:
            try: self.srv.shutdown(); self.srv.server_close()
            except Exception: pass
        self.srv = None; self.port = 0
        self._changed()

    def urls(self):
        return [f'http://{a}:{self.port}/' for a in addrs()] if self.port else []

    def status(self):
        with self.lock:
            s = self.s
            pub = None
            if s:
                pub = {k: s[k] for k in ('id', 'title', 'code', 'open', 'dur', 'created')}
                pub['n'] = len(self.exam['questions'])
                pub['students'] = [{'id': k, 'ad': x['ad'], 'no': x['no'], 'start': x['start'], 'end': x['end'], 'done': x['done'],
                                    'answered': sum(1 for a in x['answers'] if a not in (-1, '', None)), 'olay': x.get('olay', 0),
                                    'pct': x.get('pct'), 'allow_re': x.get('allow_re', False)} for k, x in s['students'].items()]
            return {'running': bool(self.srv), 'port': self.port, 'urls': self.urls(), 'session': pub,
                    'scan_code': (self.scan_exam or {}).get('code'), 'scans': list(self.scans[-50:])}

    # ---------------------------------------------------------------- yardımcılar
    def _changed(self):
        if self.on_change:
            try: self.on_change()
            except Exception: pass

    def _save(self):
        s = self.s
        if not s: return
        p = os.path.join(self.dir, s['id'] + '.json')
        try:
            with open(p + '.tmp', 'w', encoding='utf-8') as f: json.dump(dict(s, exam=self.exam), f, ensure_ascii=False)
            os.replace(p + '.tmp', p)
        except Exception:
            pass

    def _left(self, st):
        return max(0.0, st['start'] + self.s['dur'] * 60 - time.time()) if self.s['dur'] else None

    def _late(self, st):
        if not st['done'] and self.s['dur'] and self._left(st) <= 0:
            self._finish(st, auto=True); return True
        return False

    def _finish(self, st, auto=False):
        from . import exam as X
        st['done'] = True; st['end'] = time.time(); st['auto'] = auto
        try:
            r = X.save_result(self.archive, self.exam, st['ad'] + (f" ({st['no']})" if st['no'] else ''), list(st['answers']), st['start'], st['end'])
            r = dict(r, via='phone', no=st['no'], olay=st.get('olay', 0)); self.archive.rec_put('result', r['id'], r)
            st['pct'] = r['pct']; st['rid'] = r['id']
        except Exception:
            pass

    def _ticker(self):
        while True:
            time.sleep(5)
            ch = False
            with self.lock:
                if self.s:
                    for st in self.s['students'].values():
                        if self._late(st): ch = True
            if ch: self._save(); self._changed()

    def _paper(self, st):
        qs = self.exam['questions']; out = []
        for qi in st['order']:
            q = qs[qi]
            d = {'type': q.get('type', 'mc'), 'text': q['q'], 'img': f'/img/{qi}' if q.get('img') else ''}
            if d['type'] != 'open': d['options'] = [q['opts'][k] for k in st['perm'][qi]]
            out.append(d)
        return out

    def _shown(self, st):
        qs = self.exam['questions']; out = []
        for qi in st['order']:
            a = st['answers'][qi]
            if qs[qi].get('type') == 'open': out.append(a or '')
            else: out.append(st['perm'][qi].index(a) if isinstance(a, int) and a >= 0 else -1)
        return out

    def _limited(self, ip):
        now = time.time(); a = [x for x in self.tries.get(ip, []) if now - x < 60]; a.append(now); self.tries[ip] = a
        return len(a) > 20

    def _enter(self, st):
        from .paper import LETTERS
        return {'ok': True, 'token': st['token'], 'ad': st['ad'], 'no': st['no'], 'done': st['done'], 'left': self._left(st),
                'paper': [] if st['done'] else self._paper(st), 'answers': self._shown(st), 'title': self.s['title'],
                'lang': self.s['lang'], 'letters': LETTERS.get(self.s['lang'], LETTERS['tr'])}

    # ---------------------------------------------------------------- istekler
    def handle(self, method, path, body, ip):
        u = urlparse(path).path
        if method == 'GET' and u in ('/', '/index.html'): return 200, PAGE('exam', self._lang()), 'text/html; charset=utf-8'
        if method == 'GET' and u == '/okut': return 200, PAGE('scan', self._lang()), 'text/html; charset=utf-8'
        if method == 'GET' and u.startswith('/img/'):
            from . import qbank as QB
            with self.lock:
                ex = self.exam if self.s else None
            try: q = ex['questions'][int(u[5:])] if ex else None
            except Exception: q = None
            raw = QB.img_bytes((q or {}).get('img'))
            if not raw: return 404, b'', 'text/plain'
            return 200, raw, 'image/jpeg' if raw[:2] == b'\xff\xd8' else 'image/png'
        if method == 'GET' and u == '/api/bilgi':
            with self.lock:
                s = self.s
                if not s: return 200, {'ok': False, 'error': 'NO_EXAM'}, None
                return 200, {'ok': True, 'title': s['title'], 'dur': s['dur'], 'n': len(self.exam['questions']), 'open': s['open'], 'lang': s['lang']}, None
        if method != 'POST': return 404, {'ok': False}, None
        try:
            j = json.loads(body.decode('utf-8') or '{}')
        except Exception:
            return 400, {'ok': False, 'error': 'JSON'}, None
        if u == '/api/okut': return self._scan(j, ip)
        with self.lock:
            s = self.s
            if not s: return 200, {'ok': False, 'error': 'NO_EXAM'}, None
            if u == '/api/giris':
                if self._limited(ip): return 429, {'ok': False, 'error': 'SLOW'}, None
                if j.get('token'):
                    st = next((x for x in s['students'].values() if x['token'] == j['token']), None)
                    if not st: return 200, {'ok': False, 'error': 'TOKEN'}, None
                    if self._late(st): self._save()
                    return 200, self._enter(st), None
                if str(j.get('code', '')).strip() != s['code']: return 200, {'ok': False, 'error': 'CODE'}, None
                if not s['open']: return 200, {'ok': False, 'error': 'CLOSED'}, None
                ad = ' '.join(str(j.get('ad', '')).split())[:80]; no = ''.join(str(j.get('no', '')).split())[:30]
                if len(ad) < 2 or not no: return 200, {'ok': False, 'error': 'NAME'}, None
                key = no.lower(); st = s['students'].get(key)
                if st and not st.get('allow_re'): return 200, {'ok': False, 'error': 'DONE' if st['done'] else 'TAKEN'}, None
                if st:
                    st['token'] = secrets.token_hex(16); st['allow_re'] = False; st['ip'] = ip
                    if st['done'] and st.get('reopen'): st['done'] = False; st['end'] = 0; st['start'] = time.time()
                    st['reopen'] = False
                else:
                    qs = self.exam['questions']; n = len(qs); rnd = random.SystemRandom()
                    order = list(range(n))
                    if s['shuffle_q']: rnd.shuffle(order)
                    perm = []
                    for q in qs:
                        p = list(range(len(q.get('opts') or [])))
                        if s['shuffle_o']: rnd.shuffle(p)
                        perm.append(p)
                    st = s['students'][key] = {'ad': ad, 'no': no, 'token': secrets.token_hex(16), 'ip': ip, 'start': time.time(), 'end': 0, 'done': False,
                                               'answers': ['' if q.get('type') == 'open' else -1 for q in qs], 'order': order, 'perm': perm, 'last': time.time()}
                self._save(); res = self._enter(st)
            else:
                st = next((x for x in s['students'].values() if x['token'] == j.get('token')), None) if j.get('token') else None
                if not st: return 200, {'ok': False, 'error': 'TOKEN'}, None
                if u == '/api/cevap':
                    self._late(st)
                    if st['done']: res = {'ok': False, 'error': 'DONE'}
                    else:
                        qs = self.exam['questions']
                        for i, a in enumerate((j.get('answers') or [])[:len(st['order'])]):
                            qi = st['order'][i]
                            if qs[qi].get('type') == 'open': st['answers'][qi] = str(a or '')[:4000]
                            else:
                                st['answers'][qi] = st['perm'][qi][a] if isinstance(a, int) and 0 <= a < len(st['perm'][qi]) else -1
                        st['last'] = time.time(); st['ip'] = ip
                        if j.get('final'): self._finish(st)
                        self._save(); res = {'ok': True, 'done': st['done'], 'left': self._left(st)}
                elif u == '/api/olay':
                    if not st['done']: st['olay'] = st.get('olay', 0) + 1; self._save()
                    res = {'ok': True, 'n': st.get('olay', 0)}
                else:
                    return 404, {'ok': False}, None
        self._changed()
        return 200, res, None

    def _scan(self, j, ip):
        from . import omr, paper
        ex = self.scan_exam
        if not ex or str(j.get('code', '')).strip() != ex.get('code'):
            self._limited(ip); return 200, {'ok': False, 'error': 'CODE'}, None
        if self._limited(ip): return 429, {'ok': False, 'error': 'SLOW'}, None
        img = j.get('image') or ''
        if not img.startswith('data:image/'): return 200, {'ok': False, 'error': 'IMG'}, None
        try: raw = base64.b64decode(img.split(',', 1)[1])
        except Exception: return 200, {'ok': False, 'error': 'IMG'}, None
        n_opts = max([len(q['opts']) for q in ex['questions'] if q.get('type') != 'open'] or [4])
        r = omr.read(raw, len(ex['questions']), n_opts)
        if not r['ok']:
            self.scans.append({'t': time.time(), 'ok': False, 'err': r['err']}); self._changed()
            return 200, {'ok': True, 'read': False, 'error': r['err']}, None
        res = paper.grade_sheet(self.archive, ex, r, self.scan_students)
        self.scans.append({'t': time.time(), 'ok': True, 'student': res['student'], 'no': res.get('no'), 'score': res['score'], 'total': res['total'], 'pct': res['pct']})
        self._changed()
        return 200, {'ok': True, 'read': True, 'ad': res['student'], 'no': res.get('no') or '?', 'd': res['score'], 'n': res['total']}, None

    def _lang(self):
        return (self.s or {}).get('lang') or (self.scan_exam or {}).get('lang') or 'tr'

    # ---------------------------------------------------------------- sunucu
    def _listen(self):
        if self.srv: return self.port
        me = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass

            def _do(self, method):
                ip = self.client_address[0]; body = b''
                if method == 'POST':
                    n = int(self.headers.get('Content-Length') or 0)
                    if n > MAX_BODY: return self._send(413, {'ok': False, 'error': 'BIG'})
                    body = self.rfile.read(n)
                try:
                    code, out, typ = me.handle(method, self.path, body, ip)
                except Exception:
                    code, out, typ = 500, {'ok': False, 'error': 'ERR'}, None
                self._send(code, out, typ)

            def _send(self, code, out, typ=None):
                if isinstance(out, (dict, list)): out = json.dumps(out, ensure_ascii=False).encode(); typ = 'application/json; charset=utf-8'
                elif isinstance(out, str): out = out.encode('utf-8')
                self.send_response(code); self.send_header('Content-Type', typ or 'text/plain')
                self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff'); self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Content-Length', str(len(out))); self.end_headers(); self.wfile.write(out)

            def do_GET(self): self._do('GET')

            def do_POST(self): self._do('POST')
        for p in PORTS:
            try:
                srv = ThreadingHTTPServer(('0.0.0.0', p), H); srv.daemon_threads = True
            except OSError:
                continue
            self.srv = srv; self.port = p
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            return p
        raise OSError('PORT')


# ==================================================================== telefon sayfaları
CSS = """*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans Arabic",Tahoma,sans-serif;background:#0f172a;color:#e5e7eb;font-size:17px;-webkit-text-size-adjust:100%}
header{position:sticky;top:0;z-index:5;background:#111c33;border-bottom:1px solid #22304d;padding:10px 14px;display:flex;gap:10px;align-items:center}
header h1{font-size:16px;margin:0;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.timer{font-variant-numeric:tabular-nums;font-weight:700;background:#1e293b;border-radius:8px;padding:4px 10px}.timer.low{background:#7f1d1d;color:#fff}
select,input,button,textarea{font:inherit}select{background:#1e293b;color:#e5e7eb;border:1px solid #334155;border-radius:8px;padding:4px 6px}
main{max-width:860px;margin:0 auto;padding:14px}
.card{background:#111c33;border:1px solid #22304d;border-radius:14px;padding:16px;margin-bottom:14px}
label{display:block;margin:10px 0 4px;color:#94a3b8;font-size:14px}
input[type=text],input[type=tel],textarea{width:100%;padding:12px;border-radius:10px;border:1px solid #334155;background:#0b1222;color:#fff}
textarea{min-height:170px;line-height:1.45}
.btn{display:inline-block;border:0;border-radius:10px;padding:12px 18px;background:#2563eb;color:#fff;font-weight:600;cursor:pointer}.btn.sec{background:#334155}.btn:disabled{opacity:.5}
.btn.wide{width:100%;margin-top:14px}
.err{color:#fca5a5;margin-top:10px;min-height:20px}.ok{color:#86efac}
.q .n{font-weight:700;color:#93c5fd;margin-bottom:6px}.q .s{white-space:pre-wrap;line-height:1.45;margin-bottom:10px}
.q img{width:100%;display:block;margin:6px auto;background:#fff;border-radius:8px}
.opt{display:flex;gap:10px;align-items:center;width:100%;text-align:start;background:#0b1222;color:#e5e7eb;border:2px solid #22304d;border-radius:12px;padding:12px;margin:7px 0;cursor:pointer}
.opt b{min-width:30px;height:30px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:#1e293b}
.opt.on{border-color:#3b82f6;background:#13254a}.opt.on b{background:#2563eb;color:#fff}
.nav{display:grid;grid-template-columns:repeat(auto-fill,minmax(42px,1fr));gap:6px}.nav button{padding:8px 0;border-radius:8px;border:1px solid #334155;background:#0b1222;color:#cbd5e1}
.nav button.a{background:#14532d;border-color:#166534;color:#fff}.nav button.cur{outline:2px solid #60a5fa}
.row{display:flex;gap:10px;justify-content:space-between;align-items:center}
.big{font-size:22px;text-align:center;padding:30px 10px}
[dir=rtl] .opt{text-align:right}"""

I18N = {
    'title': ['Telefonla sınav', 'Phone exam', 'اختبار بالهاتف'],
    'name': ['Adınız soyadınız', 'Your full name', 'الاسم الكامل'],
    'no': ['Öğrenci numaranız', 'Your student number', 'رقمك الطلابي'],
    'code': ['Sınav kodu (eğitimcinizden)', 'Exam code (from your instructor)', 'رمز الاختبار (من المدرّب)'],
    'start': ['Sınava başla', 'Start the exam', 'ابدأ الاختبار'],
    'info': ['{n} soru · süre {d} dakika', '{n} questions · {d} minutes', '{n} سؤالاً · المدة {d} دقيقة'],
    'infoNoTime': ['{n} soru · süre sınırı yok', '{n} questions · no time limit', '{n} سؤالاً · بلا حد زمني'],
    'q': ['Soru {i} / {n}', 'Question {i} / {n}', 'السؤال {i} / {n}'],
    'open': ['✎ Yorumunuzu yazın (grafikte ne görüyorsunuz, neden, ne önerirsiniz?)', '✎ Write your interpretation (what do you see, why, what do you recommend?)', '✎ اكتب تفسيرك (ماذا ترى، ولماذا، وما توصيتك؟)'],
    'zoom': ['Görsele dokunun: büyür', 'Tap the image to enlarge', 'اضغط على الصورة لتكبيرها'],
    'prev': ['‹ Önceki', '‹ Previous', 'السابق ›'], 'next': ['Sonraki ›', 'Next ›', '‹ التالي'],
    'finish': ['Sınavı bitir ve gönder', 'Finish and submit', 'إنهاء الاختبار وإرساله'],
    'confirm': ['{a}/{n} soruyu cevapladınız. Sınavı bitirmek istiyor musunuz? Bitirdikten sonra değiştiremezsiniz.', 'You answered {a}/{n}. Finish the exam? You cannot change your answers afterwards.', 'أجبت عن {a}/{n}. هل تريد إنهاء الاختبار؟ لا يمكنك تغيير الإجابات بعد ذلك.'],
    'done': ['✅ Cevaplarınız eğitimcinize ulaştı. Teşekkürler!', '✅ Your answers have reached your instructor. Thank you!', '✅ وصلت إجاباتك إلى المدرّب. شكرًا لك!'],
    'timeup': ['⏰ Süre doldu; cevaplarınız otomatik gönderildi.', '⏰ Time is up; your answers were submitted automatically.', '⏰ انتهى الوقت؛ أُرسلت إجاباتك تلقائيًا.'],
    'offline': ['Bağlantı yok — cevaplar telefonda tutuluyor, bağlantı gelince gönderilecek', 'No connection — answers are kept on the phone and will be sent when reconnected', 'لا يوجد اتصال — تُحفظ الإجابات في الهاتف وتُرسل عند عودة الاتصال'],
    'e_CODE': ['Sınav kodu yanlış.', 'Wrong exam code.', 'رمز الاختبار غير صحيح.'], 'e_CLOSED': ['Sınav şu anda girişe kapalı.', 'The exam is closed for entry.', 'الاختبار مغلق أمام الدخول حاليًا.'],
    'e_NAME': ['Adınızı ve numaranızı yazın.', 'Enter your name and number.', 'اكتب اسمك ورقمك.'], 'e_TAKEN': ['Bu numarayla başka bir cihazdan girilmiş. Eğitimcinize söyleyin.', 'This number is already in use on another device. Tell your instructor.', 'هذا الرقم مستخدم على جهاز آخر. أخبر المدرّب.'],
    'e_DONE': ['Bu numarayla sınav zaten teslim edilmiş.', 'An exam has already been submitted with this number.', 'سُلّم اختبار بهذا الرقم بالفعل.'], 'e_NO_EXAM': ['Şu anda açık sınav yok.', 'No exam is open right now.', 'لا يوجد اختبار مفتوح حاليًا.'],
    'e_SLOW': ['Çok fazla deneme. Bir dakika bekleyin.', 'Too many attempts. Wait a minute.', 'محاولات كثيرة. انتظر دقيقة.'], 'e_NET': ['Bilgisayara ulaşılamadı. Aynı Wi-Fi ağında olduğunuzdan emin olun.', 'Cannot reach the computer. Make sure you are on the same Wi-Fi.', 'تعذّر الوصول إلى الحاسوب. تأكد أنك على شبكة Wi-Fi نفسها.'],
    'e_IMG': ['Görüntü açılamadı', 'Image could not be opened', 'تعذّر فتح الصورة'], 'e_CORNERS': ['dört köşe karesi bulunamadı', 'the four corner squares were not found', 'لم يُعثر على مربعات الزوايا الأربعة'],
    'left': ['⚠ Sınav sayfasından çıkışınız kaydedildi ({n}).', '⚠ Leaving the exam page was recorded ({n}).', '⚠ سُجّلت مغادرتك صفحة الاختبار ({n}).'],
    'scanTitle': ['Optik form okut', 'Scan answer sheets', 'قراءة أوراق الإجابة'],
    'scanHelp': ['Formu düz bir yere koyun, dört köşedeki siyah kare görünecek şekilde yukarıdan çekin. Her fotoğraf bilgisayara gider ve hemen puanlanır.', 'Lay the sheet flat and photograph it from above so that all four black corner squares are visible. Each photo is sent to the computer and scored at once.', 'ضع الورقة على سطح مستوٍ وصوّرها من الأعلى بحيث تظهر المربعات السوداء الأربعة في الزوايا. تُرسل كل صورة إلى الحاسوب وتُصحَّح فورًا.'],
    'scanBtn': ['📷 Fotoğraf çek / seç', '📷 Take / choose photo', '📷 التقط / اختر صورة'],
    'scanCode': ['Sınav kodu (kitapçıkta ve bilgisayarda yazar)', 'Exam code (printed on the booklet and shown on the computer)', 'رمز الاختبار (مطبوع على الكراسة ويظهر على الحاسوب)'],
    'scanSending': ['Gönderiliyor… {p}', 'Sending… {p}', 'جارٍ الإرسال… {p}'],
    'scanOk': ['✅ {ad} — {no}: {d} puan / {n}', '✅ {ad} — {no}: {d} points / {n}', '✅ {ad} — {no}: {d} درجة / {n}'],
    'scanFail': ['Okunamadı: {e}. Daha düz ve aydınlık çekip tekrar deneyin.', 'Could not read: {e}. Try again with a flatter, brighter photo.', 'تعذّرت القراءة: {e}. أعد المحاولة بصورة أوضح وأكثر استواءً.'],
}

_HEAD = """<!doctype html><html lang="{lg}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>Pixhawk</title><style>{css}</style></head><body>
<header><h1 id="h"></h1><span class="timer" id="tm" style="display:none"></span><select id="lg"><option value="tr">TR</option><option value="en">EN</option><option value="ar">AR</option></select></header>
<main id="m"></main>
<script>
const I={i18n};
let L=localStorage.getItem('px.lang')||'{lg}';if(!['tr','en','ar'].includes(L))L='tr';
const t=(k,v)=>{{const a=I[k]||[k];let s=a[{{tr:0,en:1,ar:2}}[L]]||a[0];if(v)for(const x in v)s=s.split('{{'+x+'}}').join(v[x]);return s}};
const $=(s)=>document.querySelector(s);const esc=(s)=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
async function post(p,b){{const r=await fetch(p,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(b)}});return r.json()}}
function dirSet(){{document.documentElement.lang=L;document.documentElement.dir=L==='ar'?'rtl':'ltr';$('#lg').value=L}}
$('#lg').onchange=(e)=>{{L=e.target.value;localStorage.setItem('px.lang',L);dirSet();render()}};
dirSet();
"""

EXAM_JS = r"""
let S={info:null,tok:localStorage.getItem('px.tok')||'',paper:null,ans:[],cur:0,left:null,done:false,auto:false,lastSync:0,dirty:false,err:'',letters:null};
const dirOf=(s)=>/[؀-ۿ]/.test(s)?'rtl':'auto';
const answered=(a)=>typeof a==='string'?a.trim().length>0:a>=0;
function fmt(ms){const s=Math.ceil(ms/1000),m=Math.floor(s/60);return (m>=60?Math.floor(m/60)+':'+String(m%60).padStart(2,'0'):m)+':'+String(s%60).padStart(2,'0')}
async function boot(){try{const r=await fetch('/api/bilgi');S.info=await r.json()}catch(e){S.info={ok:false,error:'NET'}}
 if(S.tok){try{const j=await post('/api/giris',{token:S.tok});if(j.ok)return enter(j);localStorage.removeItem('px.tok');S.tok=''}catch(e){}}
 render()}
function enter(j){S.tok=j.token;localStorage.setItem('px.tok',j.token);S.paper=j.paper;S.ans=j.answers||[];S.done=j.done;S.left=j.left==null?null:j.left*1000;S.t0=Date.now();S.title=j.title;S.letters=j.letters;
 const pend=localStorage.getItem('px.pend.'+S.tok);if(pend&&!S.done){try{const a=JSON.parse(pend);if(Array.isArray(a)&&a.length===S.ans.length){S.ans=a;S.dirty=true}}catch(e){}}
 render();tick()}
let olayT=0;
document.addEventListener('visibilitychange',()=>{if(document.hidden&&S.tok&&S.paper&&!S.done){const now=Date.now();if(now-olayT<3000)return;olayT=now;post('/api/olay',{token:S.tok}).then((j)=>{if(j&&j.ok){S.olayN=j.n}}).catch(()=>{})}});
function leftNow(){return S.left==null?null:Math.max(0,S.left-(Date.now()-S.t0))}
function tick(){clearInterval(S.iv);S.iv=setInterval(()=>{const l=leftNow();const tm=$('#tm');if(l==null||S.done){tm.style.display='none';return}tm.style.display='';tm.textContent='⏱ '+fmt(l);tm.classList.toggle('low',l<120000);if(l<=0){sync(true,true)}else if(S.dirty&&Date.now()-S.lastSync>1500)sync(false)},500)}
async function sync(final,auto){if(S.busy)return;S.busy=true;localStorage.setItem('px.pend.'+S.tok,JSON.stringify(S.ans));
 try{const j=await post('/api/cevap',{token:S.tok,answers:S.ans,final:!!final});S.lastSync=Date.now();S.err='';
  if(j.ok){S.dirty=false;if(j.left!=null){S.left=j.left*1000;S.t0=Date.now()}if(j.done){S.done=true;S.auto=!!auto;localStorage.removeItem('px.pend.'+S.tok)}}
  else if(j.error==='DONE'){S.done=true;S.auto=true}
 }catch(e){S.err=t('offline')}
 S.busy=false;if(final||S.done)render()}
function render(){
 $('#h').textContent=S.title||(S.info&&S.info.title)||t('title');document.title=$('#h').textContent;
 const m=$('#m');
 if(S.done){m.innerHTML='<div class="card big">'+esc(S.auto?t('timeup'):t('done'))+'</div>';return}
 if(!S.paper){const i=S.info||{};
  if(!i.ok){m.innerHTML='<div class="card big">'+esc(t('e_'+(i.error||'NET')))+'</div><p style="text-align:center"><button class="btn sec" onclick="location.reload()">↻</button></p>';return}
  m.innerHTML='<div class="card"><h2 style="margin:0 0 4px">'+esc(i.title||t('title'))+'</h2><div style="color:#94a3b8">'+esc(i.dur?t('info',{n:i.n,d:i.dur}):t('infoNoTime',{n:i.n}))+'</div>'+
  '<label>'+esc(t('name'))+'</label><input id="fa" type="text" autocomplete="name" value="'+esc(localStorage.getItem('px.ad')||'')+'">'+
  '<label>'+esc(t('no'))+'</label><input id="fn" type="tel" value="'+esc(localStorage.getItem('px.no')||'')+'">'+
  '<label>'+esc(t('code'))+'</label><input id="fc" type="tel" inputmode="numeric" maxlength="4">'+
  '<button class="btn wide" id="go">'+esc(t('start'))+'</button><div class="err" id="er">'+esc(S.err)+'</div></div>';
  $('#go').onclick=async()=>{const ad=$('#fa').value.trim(),no=$('#fn').value.trim(),code=$('#fc').value.trim();localStorage.setItem('px.ad',ad);localStorage.setItem('px.no',no);
   $('#go').disabled=true;try{const j=await post('/api/giris',{ad,no,code});if(j.ok)return enter(j);S.err=t('e_'+j.error)}catch(e){S.err=t('e_NET')}$('#go').disabled=false;$('#er').textContent=S.err};return}
 const P=S.paper,n=P.length,i=Math.min(S.cur,n-1),q=P[i],Ls=S.letters||['A','B','C','D','E'];
 let h='';
 h+='<div class="card q"><div class="n">'+esc(t('q',{i:i+1,n}))+'</div><div class="s" dir="'+dirOf(q.text)+'">'+esc(q.text)+'</div>'+(q.img?'<a href="'+q.img+'" target="_blank"><img src="'+q.img+'" alt=""></a><div style="color:#94a3b8;font-size:13px">'+esc(t('zoom'))+'</div>':'');
 if(q.type==='open'){h+='<label>'+esc(t('open'))+'</label><textarea id="ta" dir="auto">'+esc(S.ans[i]||'')+'</textarea>'}
 else q.options.forEach((o,k)=>{h+='<button class="opt'+(S.ans[i]===k?' on':'')+'" data-k="'+k+'"><b>'+esc(Ls[k]||String.fromCharCode(65+k))+'</b><span dir="'+dirOf(o)+'">'+esc(o)+'</span></button>'});
 h+='<div class="row" style="margin-top:10px"><button class="btn sec" id="pv"'+(i?'':' disabled')+'>'+esc(t('prev'))+'</button><button class="btn sec" id="nx"'+(i<n-1?'':' disabled')+'>'+esc(t('next'))+'</button></div></div>';
 h+='<div class="card"><div class="nav">'+P.map((_,k)=>'<button data-g="'+k+'" class="'+(answered(S.ans[k])?'a ':'')+(k===i?'cur':'')+'">'+(k+1)+'</button>').join('')+'</div>'+
  (S.olayN?'<div class="err">'+esc(t('left',{n:S.olayN}))+'</div>':'')+
  '<button class="btn wide" id="fin">'+esc(t('finish'))+'</button><div class="err">'+esc(S.err)+'</div></div>';
 m.innerHTML=h;
 m.querySelectorAll('.opt').forEach((b)=>{b.onclick=()=>{const k=+b.dataset.k;S.ans[i]=S.ans[i]===k?-1:k;S.dirty=true;localStorage.setItem('px.pend.'+S.tok,JSON.stringify(S.ans));render();sync(false)}});
 const ta=$('#ta');if(ta)ta.oninput=()=>{S.ans[i]=ta.value;S.dirty=true;localStorage.setItem('px.pend.'+S.tok,JSON.stringify(S.ans))};
 m.querySelectorAll('[data-g]').forEach((b)=>{b.onclick=()=>{S.cur=+b.dataset.g;render();window.scrollTo(0,0)}});
 $('#pv').onclick=()=>{S.cur=i-1;render();window.scrollTo(0,0)};$('#nx').onclick=()=>{S.cur=i+1;render();window.scrollTo(0,0)};
 $('#fin').onclick=()=>{const a=S.ans.filter(answered).length;if(confirm(t('confirm',{a,n})))sync(true)};
}
boot();"""

SCAN_JS = r"""
let log=[];
function render(){$('#h').textContent=t('scanTitle');document.title=t('scanTitle');
 $('#m').innerHTML='<div class="card"><p>'+esc(t('scanHelp'))+'</p><label>'+esc(t('scanCode'))+'</label><input id="fc" type="tel" inputmode="numeric" maxlength="4" value="'+esc(sessionStorage.getItem('px.code')||'')+'">'+
 '<input id="fi" type="file" accept="image/*" capture="environment" multiple style="display:none"><button class="btn wide" id="go">'+esc(t('scanBtn'))+'</button></div>'+
 '<div class="card">'+log.map((x)=>'<div class="'+(x.ok?'ok':'err')+'" style="margin:6px 0">'+esc(x.m)+'</div>').join('')+'</div>';
 $('#go').onclick=()=>{sessionStorage.setItem('px.code',$('#fc').value.trim());$('#fi').click()};
 $('#fi').onchange=async(e)=>{for(const f of e.target.files)await send(f)};}
function shrink(f){return new Promise((res,rej)=>{const u=URL.createObjectURL(f);const im=new Image();im.onload=()=>{const s=Math.min(1,2000/Math.max(im.width,im.height));const c=document.createElement('canvas');c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);c.getContext('2d').drawImage(im,0,0,c.width,c.height);URL.revokeObjectURL(u);res(c.toDataURL('image/jpeg',0.88))};im.onerror=rej;im.src=u})}
async function send(f){const code=sessionStorage.getItem('px.code')||'';log.unshift({ok:true,m:t('scanSending',{p:f.name||''})});render();
 try{const image=await shrink(f);const r=await fetch('/api/okut',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code,image})});const j=await r.json();
  log[0]=j.ok?(j.read?{ok:true,m:t('scanOk',{ad:j.ad||'?',no:j.no||'?',d:j.d,n:j.n})}:{ok:false,m:t('scanFail',{e:t('e_'+(j.error||'IMG'))})}):{ok:false,m:t('e_'+j.error)};
 }catch(e){log[0]={ok:false,m:t('e_NET')}}render()}
render();"""


def PAGE(kind, lg='tr'):
    head = _HEAD.format(lg=lg, css=CSS, i18n=json.dumps(I18N, ensure_ascii=False))
    return head + (SCAN_JS if kind == 'scan' else EXAM_JS) + '\n</script></body></html>'
