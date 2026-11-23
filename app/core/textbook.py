"""Ders kitabı modu: kütüphaneler, senaryolar, alıştırmalar ve gerçek kaza örneklerinden otomatik, antetli
eğitim kitabı (PDF, TR / EN / AR). Arapçada sağdan sola; antet ve içerik çakışmaz (pdf_kit kenar boşlukları);
Besmele (açıksa) yalnızca ilk sayfadadır. Ayrıca Parametre Merkezi için antetli parametre raporu.
"""
from __future__ import annotations
import io, json, os, tempfile, time
from . import report as RP, texts, pcritical as CR
from .paths import res

LI = {'tr': 0, 'en': 1, 'ar': 2}
SECTIONS = ['intro', 'causes', 'scen', 'params', 'msgs', 'quiz', 'crash']

TX = {
    'book': ('Pixhawk / ArduPilot Uçuş Logu Analizi', 'Pixhawk / ArduPilot Flight Log Analysis', 'تحليل سجلات طيران Pixhawk و ArduPilot'),
    'sub': ('Eğitim Kitabı', 'Training Book', 'الكتاب التدريبي'),
    'gen': ('Pixhawk Log Analiz programı tarafından otomatik hazırlanmıştır · {d}', 'Generated automatically by Pixhawk Log Analyzer · {d}', 'أُعدّ تلقائياً بواسطة برنامج محلل سجلات Pixhawk · {d}'),
    'toc': ('İçindekiler', 'Contents', 'المحتويات'),
    'ch_intro': ('Giriş ve log analizi yöntemi', 'Introduction and analysis method', 'المقدمة وطريقة التحليل'),
    'ch_causes': ('Kazaların kök nedenleri ve önlemler', 'Crash root causes and prevention', 'الأسباب الجذرية للحوادث والوقاية'),
    'ch_scen': ('Örnek senaryolar', 'Example scenarios', 'سيناريوهات نموذجية'),
    'ch_params': ('Bilinmesi gereken kritik parametreler', 'Must-know critical parameters', 'المعاملات الحرجة الواجب معرفتها'),
    'ch_msgs': ('Log mesajları sözlüğü', 'Log messages glossary', 'مسرد رسائل السجل'),
    'ch_quiz': ('Alıştırma soruları', 'Exercises', 'التمارين'),
    'ch_key': ('Cevap anahtarı', 'Answer key', 'مفتاح الإجابة'),
    'ch_crash': ('Gerçek kaza örnekleri', 'Real crash cases', 'حالات حوادث حقيقية'),
    'why': ('Neden olur?', 'Why does it happen?', 'لماذا يحدث؟'), 'prev': ('Nasıl önlenir?', 'How to prevent it?', 'كيف نمنعه؟'),
    'verdict': ('Programın kararı', 'Program verdict', 'قرار البرنامج'), 'root': ('Kök neden', 'Root cause', 'السبب الجذري'),
    'steps': ('Ders adımları (3B tekrarda izlenecekler)', 'Lesson steps (what to watch in the 3D replay)', 'خطوات الدرس (ما يجب مراقبته في الإعادة)'),
    'time': ('Zaman', 'Time', 'الزمن'), 'step': ('Adım', 'Step', 'الخطوة'), 'watch': ('Ne izlenir', 'What to watch', 'ما يُراقب'),
    'param': ('Parametre', 'Parameter', 'المعامل'), 'name': ('Ad', 'Name', 'الاسم'), 'whyimp': ('Neden önemli', 'Why it matters', 'لماذا هو مهم'),
    'def': ('Varsayılan', 'Default', 'الافتراضي'), 'field': ('Alan', 'Field', 'الحقل'), 'meaning': ('Anlamı', 'Meaning', 'المعنى'),
    'q': ('Soru', 'Question', 'السؤال'), 'ans': ('Cevap', 'Answer', 'الإجابة'), 'exp': ('Açıklama', 'Explanation', 'الشرح'),
    'topic': ('Konu', 'Topic', 'الموضوع'), 'label': ('Forum', 'Forum', 'المنتدى'), 'prog': ('Program', 'Program', 'البرنامج'),
    'acc': ('Programın gerçek forum loglarıyla ölçülen doğruluğu: %{a:.0f} ({n} log). Kırımı yakalama %{r:.0f}, normali tanıma %{s:.0f}.',
            'Accuracy measured on real forum logs: {a:.0f}% ({n} logs). Crash recall {r:.0f}%, normal specificity {s:.0f}%.',
            'الدقة المقاسة على سجلات المنتدى الحقيقية: {a:.0f}% ({n} سجل). اكتشاف التحطم {r:.0f}%، تمييز الطبيعي {s:.0f}%.'),
    'scen_of': ('Senaryo', 'Scenario', 'السيناريو'),
}
INTRO = [
    ('Bu kitap, Pixhawk uçuş kartlarında çalışan ArduPilot yazılımının kaydettiği uçuş loglarını (.BIN / .tlog) okumayı, bir uçuşun normal mi, olaylı mı yoksa kırımla mı bittiğini anlamayı ve kök nedeni bulmayı öğretir. Bölümler programdaki kütüphanelerden, senaryolardan ve alıştırmalardan otomatik derlenmiştir.',
     'This book teaches how to read the flight logs (.BIN / .tlog) recorded by ArduPilot on Pixhawk flight controllers, to tell whether a flight ended normally, with an incident or in a crash, and to find the root cause. Chapters are compiled automatically from the program\'s libraries, scenarios and exercises.',
     'يعلّم هذا الكتاب قراءة سجلات الطيران (.BIN / .tlog) التي يسجلها ArduPilot على لوحات Pixhawk، ومعرفة ما إذا انتهت الرحلة بشكل طبيعي أو بحادثة أو بتحطم، وإيجاد السبب الجذري. جُمعت الفصول تلقائياً من مكتبات البرنامج وسيناريوهاته وتمارينه.'),
    ('Analiz yöntemi beş adımdır: (1) Uçuşun ana hatları: arm/disarm, kalkış, iniş, süre ve uçuş modları. (2) Sağlık alanları: GPS, EKF, batarya, titreşim, pusula, kumanda ve kontrol başarımı ayrı ayrı puanlanır. (3) Olay zaman çizelgesi: hata (ERR), olay (EV) ve mesajlar (MSG) zamana göre dizilir. (4) Kök neden zinciri: ilk bozulan alan bulunur; sonra gelen belirtiler bunun sonucudur. (5) Parametre denetimi: failsafe ve güvenlik ayarları kontrol edilir.',
     'The method has five steps: (1) Flight outline: arm/disarm, take-off, landing, duration and flight modes. (2) Health domains: GPS, EKF, battery, vibration, compass, radio and control performance are scored separately. (3) Event timeline: errors (ERR), events (EV) and messages (MSG) in time order. (4) Root-cause chain: find the first domain to fail; later symptoms are its consequences. (5) Parameter audit: failsafe and safety settings are checked.',
     'تتكون الطريقة من خمس خطوات: (1) ملامح الرحلة: التسليح ونزعه والإقلاع والهبوط والمدة وأوضاع الطيران. (2) مجالات السلامة: يُقيَّم كل من GPS وEKF والبطارية والاهتزاز والبوصلة والراديو وأداء التحكم على حدة. (3) الخط الزمني: الأخطاء (ERR) والأحداث (EV) والرسائل (MSG) بالترتيب الزمني. (4) سلسلة السبب الجذري: يُحدد أول مجال تعطل؛ وما بعده نتائج له. (5) تدقيق المعاملات: تُفحص إعدادات الطوارئ والسلامة.'),
    ('Kırım belirtileri: log havadayken aniden biter; irtifa hızla düşer; tutum (yatış/yunuslama) aşırı büyür; ivmede darbe görülür. Olaylı uçuşta failsafe, mod değişimi veya ciddi uyarılar vardır ama araç güvenle iner. Normal uçuşta tüm sağlık alanları yeşildir.',
     'Crash signs: the log ends abruptly while airborne; altitude drops fast; attitude (roll/pitch) becomes extreme; acceleration shows an impact. In an incident flight there are failsafes, mode changes or serious warnings but the vehicle lands safely. In a normal flight all health domains are green.',
     'علامات التحطم: ينتهي السجل فجأة والمركبة في الجو؛ ينخفض الارتفاع بسرعة؛ تصبح الوضعية (الدوران/الميلان) مفرطة؛ ويظهر اصطدام في التسارع. في الرحلة ذات الحادثة توجد حالات طوارئ أو تغيير أوضاع أو تحذيرات جدية لكن المركبة تهبط بأمان. في الرحلة الطبيعية تكون جميع المجالات خضراء.'),
    ('Programda her bölümün karşılığı vardır: Grafikler ve Dersler, Harita ve 3B Tekrar (adım adım ders rehberi ve MP4 video), Olay Zaman Çizelgesi, Yapay Zekâ Danışman, Alıştırma, Sınav ve Sertifika, Parametre Merkezi (tüm araç sınıflarının tam parametre listesi) ve Gerçek Kaza Logları.',
     'Each chapter has a counterpart in the program: Charts & Lessons, Map & 3D Replay (step-by-step lesson guide and MP4 video), Event Timeline, AI Advisor, Practice, Exam & Certificate, Parameter Center (full parameter list for every vehicle class) and Real Crash Logs.',
     'لكل فصل ما يقابله في البرنامج: الرسوم والدروس، والخريطة والإعادة ثلاثية الأبعاد (دليل درس خطوة بخطوة وفيديو MP4)، والخط الزمني للأحداث، والمستشار الذكي، والتدريب، والاختبار والشهادة، ومركز المعاملات (القائمة الكاملة لكل فئات المركبات)، وسجلات الحوادث الحقيقية.'),
]
CAUSES = ['gps', 'ekf', 'battery', 'radio', 'stall', 'vibration', 'compass', 'power', 'control', 'motor']


def _x(k, lg, **a):
    s = TX[k][LI.get(lg, 0)]
    return s.format(**a) if a else s


def _mark_cls():
    from reportlab.platypus import Flowable

    class Mark(Flowable):
        def __init__(self, key, rec):
            super().__init__(); self.key = key; self.rec = rec
        def wrap(self, *a): return (0, 0)
        def draw(self): self.rec[self.key] = self.canv.getPageNumber()
    return Mark


def _scenario_data(lg, progress=None):
    from . import synth, loader, analysis, charts, lessons, practice
    from .scenarios import SCEN
    d = tempfile.mkdtemp(); out = []
    for i, k in enumerate(SCEN):
        if progress: progress(0.1 + 0.5 * i / len(SCEN))
        p = os.path.join(d, k + '.BIN'); synth.generate(p, k)
        A = analysis.Analysis(loader.load(p))
        cause = (A.root or {}).get('cause')
        imgs = []
        for key in ('c_alt', {'gps': 'c_gps', 'battery': 'c_bat', 'vibration': 'c_vibe', 'radio': 'c_rcou', 'stall': 'c_alt', 'compass': 'c_mag', 'ekf': 'c_ekf'}.get(cause)):
            if key and key not in [x[0] for x in imgs]:
                try:
                    b = charts.render_marked(key, A, lg, (A.root or {}).get('t') if key != 'c_alt' or cause == 'stall' else None)
                    if b: imgs.append((key, b))
                except Exception:
                    pass
        try: steps = lessons.build(A, lg, max_steps=10)
        except Exception: steps = []
        try: qs = practice.generate(A, lg, n=4, seed=11 + i)
        except Exception: qs = []
        out.append({'k': k, 'name': SCEN[k][0][LI[lg]], 'desc': SCEN[k][1][LI[lg]], 'A': A, 'imgs': imgs, 'steps': steps, 'qs': qs})
    return out


def build_book(path, lang='tr', lh=None, sections=None, progress=None):
    from reportlab.platypus import Spacer, PageBreak, KeepTogether, CondPageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    lg = lang; secs = [s for s in SECTIONS if s in (sections or SECTIONS)]
    data = _scenario_data(lg, progress) if ('scen' in secs or 'quiz' in secs) else []
    if progress: progress(0.65)
    msgs = json.load(open(res('data', 'logmsgs.json'), encoding='utf-8')) if 'msgs' in secs else {}
    from . import crashlib
    CL = crashlib.load() if 'crash' in secs else {'cases': []}
    Mark = _mark_cls()

    def story(pages, K_):
        P, tbl, img, base, small, H1, H2, TT, W_ = (K_[k] for k in ('P', 'tbl', 'img', 'base', 'small', 'H1', 'H2', 'TT', 'W'))
        colors, cm = K_['colors'], K_['cm']
        center = ParagraphStyle('c', parent=base, alignment=TA_CENTER, fontSize=11, leading=15)
        big = ParagraphStyle('big', parent=TT, fontSize=24, leading=30)
        st = K_['besmele']()
        st += [Spacer(1, 3.2 * cm), P(_x('book', lg), big), Spacer(1, 10), P(_x('sub', lg), ParagraphStyle('s2', parent=TT, fontSize=16, leading=20)),
               Spacer(1, 18), P(K_['lh'].get('org') or '', center), Spacer(1, 6),
               P(_x('gen', lg, d=time.strftime('%Y-%m-%d')), ParagraphStyle('g', parent=small, alignment=TA_CENTER, textColor=colors.HexColor('#6B7280'))),
               PageBreak()]
        st.append(P(_x('toc', lg), H1))
        rows = []
        for i, s in enumerate(secs, 1):
            rows.append([f'{i}. ' + _x('ch_' + s, lg), str(pages.get(s, '…'))])
        if 'quiz' in secs: rows.append([f'{len(secs) + 1}. ' + _x('ch_key', lg), str(pages.get('key', '…'))])
        st.append(tbl(rows, None, [W_ * 0.85, W_ * 0.15], fs=10.5))
        n_ = 0
        for s in secs:
            n_ += 1
            st += [PageBreak() if n_ == 1 else CondPageBreak(7 * cm), Mark(s, pages), P(f'{n_}. ' + _x('ch_' + s, lg), H1)]
            if s == 'intro':
                for para in INTRO: st += [P(para[LI[lg]]), Spacer(1, 5)]
            elif s == 'causes':
                for c in CAUSES:
                    st.append(KeepTogether([P(texts.T('cause_' + c, lg), H2), P(_x('why', lg) + ' ' + texts.T('why_' + c, lg)),
                                            Spacer(1, 2), P(_x('prev', lg) + ' ' + texts.T('prevent_' + c, lg)), Spacer(1, 6)]))
            elif s == 'scen':
                for j, sc in enumerate(data, 1):
                    A = sc['A']; v = A.verdict.get('kind', 'normal'); cause = (A.root or {}).get('cause')
                    blk = [P(f'{n_}.{j} {sc["name"]}', H2), P(sc['desc']), Spacer(1, 3),
                           tbl([[_x('verdict', lg), texts.T('v_' + v, lg)], [_x('root', lg), texts.T('cause_' + cause, lg) if cause else '-']], None, [W_ * 0.3, W_ * 0.7], fs=9)]
                    st.append(KeepTogether(blk))
                    for key, b in sc['imgs'][:2]:
                        im_ = img(b, W_ * 0.92); im_.hAlign = 'CENTER'; st += [Spacer(1, 4), im_]
                    if sc['steps']:
                        st += [Spacer(1, 4), P(_x('steps', lg), H2),
                               tbl([[x['time'], x['title'], x['text']] for x in sc['steps']], [_x('time', lg), _x('step', lg), _x('watch', lg)],
                                   [W_ * 0.12, W_ * 0.28, W_ * 0.60], fs=8)]
                    st.append(Spacer(1, 10))
            elif s == 'params':
                from . import pcenter as PC
                db = PC.PDB.get()
                for c, nm in CR.CATS.items():
                    rows = []
                    for cc, p, v, why in CR.CRIT:
                        if cc != c: continue
                        vv = (v or ['Plane'])[0]
                        m = db.meta(p, vv) or {}
                        dn = db.text(p, vv, lg)[0] if m else ''
                        d = m.get('default')
                        rows.append([p + ('\n' + '/'.join(v) if v else ''), dn, why[LI[lg]], PC.fmt(d) if d is not None else '-'])
                    if rows:
                        st += [P(nm[LI[lg]], H2), tbl(rows, [_x('param', lg), _x('name', lg), _x('whyimp', lg), _x('def', lg)],
                                                         [W_ * 0.22, W_ * 0.22, W_ * 0.44, W_ * 0.12], fs=7.8), Spacer(1, 6)]
            elif s == 'msgs':
                core = sorted(k for k, m in msgs.items() if m.get('core'))
                for k in core:
                    m = msgs[k]; d = m['desc'].get(lg) or m['desc'].get('en', '')
                    rows = [[f, (fd.get(lg) or fd.get('en') or '')] for f, fd in list((m.get('fields') or {}).items())[:24]]
                    blk = [P(f'{k} — {d}', H2)]
                    if rows: blk.append(tbl(rows, [_x('field', lg), _x('meaning', lg)], [W_ * 0.2, W_ * 0.8], fs=7.6))
                    st += [KeepTogether(blk[:2]) if len(rows) < 14 else blk[0]] + ([] if len(rows) < 14 else blk[1:]) + [Spacer(1, 5)]
            elif s == 'quiz':
                qn = 0
                for sc in data:
                    if not sc['qs']: continue
                    st.append(P(f'{_x("scen_of", lg)}: {sc["name"]}', H2))
                    for q in sc['qs']:
                        qn += 1; q['_n'] = qn
                        opts = [f'{"ABCDEFGHIJ"[i]}) {o}' for i, o in enumerate(q['opts'])]
                        st.append(KeepTogether([P(f'{qn}. {q["q"]}'), P('\n'.join(opts), small), Spacer(1, 5)]))
            elif s == 'crash':
                sc_ = CL.get('score')
                if sc_: st += [P(_x('acc', lg, a=sc_['accuracy'] * 100, n=sc_['n'], r=sc_['recall_crash'] * 100, s=sc_['specificity'] * 100)), Spacer(1, 4)]
                rows = []
                lab = {'crash': texts.T('v_crash', lg), 'normal': texts.T('v_normal', lg), 'incident': texts.T('v_incident', lg)}
                for c in (CL.get('cases') or [])[:80]:
                    rows.append([c.get('title') or '', c.get('vehicle') or '', lab.get(c.get('label'), c.get('label') or ''),
                                 lab.get(c.get('got'), c.get('got') or '') + (' · ' + texts.T('cause_' + c['got_cause'], lg) if c.get('got_cause') else ''), c.get('url') or ''])
                if rows: st.append(tbl(rows, [_x('topic', lg), 'ArduPilot', _x('label', lg), _x('prog', lg), 'URL'],
                                       [W_ * 0.32, W_ * 0.1, W_ * 0.1, W_ * 0.2, W_ * 0.28], fs=6.8))
        if 'quiz' in secs:
            st += [PageBreak(), Mark('key', pages), P(f'{len(secs) + 1}. ' + _x('ch_key', lg), H1)]
            rows = []
            for sc in data:
                for q in sc['qs']:
                    rows.append([str(q.get('_n', '')), f'{"ABCDEFGHIJ"[q["ans"]]}) {q["opts"][q["ans"]]}', q.get('exp', '')])
            if rows: st.append(tbl(rows, ['#', _x('ans', lg), _x('exp', lg)], [W_ * 0.07, W_ * 0.33, W_ * 0.60], fs=8))
        return st

    pages = {}
    title = _x('book', lg) + ' — ' + _x('sub', lg)
    K1 = RP.pdf_kit(lg, lh, footer_extra=_x('sub', lg))
    K1['build'](os.path.join(tempfile.mkdtemp(), 'pass1.pdf'), story(pages, K1), title)     # 1. geçiş: sayfa numaraları
    if progress: progress(0.85)
    K2 = RP.pdf_kit(lg, lh, footer_extra=_x('sub', lg))
    final = dict(pages)
    K2['build'](path, story(final, K2), title)
    if progress: progress(1.0)
    return path


# ------------------------------------------------------------------ parametre raporu
PR = {'title': ('Parametre Denetim Raporu', 'Parameter Audit Report', 'تقرير تدقيق المعاملات'),
      'risks': ('Riskler ve uyarılar', 'Risks and warnings', 'المخاطر والتحذيرات'),
      'changed': ('Varsayılandan farklı / dikkat gerektiren parametreler', 'Changed / attention-needing parameters', 'المعاملات المغيرة / التي تحتاج انتباهاً'),
      'crit': ('Kritik parametrelerin değerleri', 'Values of critical parameters', 'قيم المعاملات الحرجة'),
      'none': ('Risk bulunmadı.', 'No risk found.', 'لم يُعثر على خطر.'),
      'info': ('Dosya: {n} · Araç: {v} · {c} parametre · {d}', 'File: {n} · Vehicle: {v} · {c} parameters · {d}', 'الملف: {n} · المركبة: {v} · {c} معاملاً · {d}'),
      'val': ('Değer', 'Value', 'القيمة'), 'st': ('Durum', 'Status', 'الحالة')}
STN = {'changed': ('değiştirilmiş', 'changed', 'مغيّر'), 'range': ('aralık dışı', 'out of range', 'خارج النطاق'), 'enum': ('tanımsız seçenek', 'undefined option', 'خيار غير معرّف'),
       'bits': ('bilinmeyen bit', 'unknown bit', 'بت غير معروف'), 'unknown': ('tanımsız', 'unknown', 'غير معروف'), 'ro': ('salt okunur', 'read-only', 'للقراءة فقط')}


def param_report(params, vehicle, name, lang, path, lh=None):
    from reportlab.platypus import Spacer
    from . import pcenter as PC
    lg = lang; i = LI.get(lg, 0); db = PC.PDB.get()
    K_ = RP.pdf_kit(lg, lh, footer_extra=PR['title'][i])
    P, tbl, H1, H2, TT, W_, small = (K_[k] for k in ('P', 'tbl', 'H1', 'H2', 'TT', 'W', 'small'))
    st = K_['besmele']() + [P(PR['title'][i], TT), Spacer(1, 4),
                            P(PR['info'][i].format(n=name, v=PC.vname(vehicle, lg), c=len(params), d=time.strftime('%Y-%m-%d %H:%M')), small), Spacer(1, 8)]
    rk = PC.risks(params, vehicle, lg)
    st.append(P(PR['risks'][i], H1))
    if rk:
        sev = {2: 'FECACA', 1: 'FEF3C7', 0: 'DBEAFE'}
        st.append(tbl([[('⛔' if r['sev'] >= 2 else '⚠' if r['sev'] == 1 else 'i'), r.get('param') or '', r['text']] for r in rk], None,
                      [W_ * 0.06, W_ * 0.22, W_ * 0.72], bg=[[sev[min(2, r['sev'])]] * 3 for r in rk], fs=8))
    else:
        st.append(P(PR['none'][i]))
    crit = [p for _, p, _ in CR.critical(vehicle) if p in params]
    if crit:
        st += [Spacer(1, 6), P(PR['crit'][i], H1)]
        st.append(tbl([[p, PC.fmt(params[p]), (PC.value_label(params[p], (db.meta(p, vehicle) or {}).get('vals')) or ''), CR.why(p, lg)[1] or ''] for p in crit],
                      [PR['val'][i] and 'Param', PR['val'][i], '', ''], [W_ * 0.22, W_ * 0.1, W_ * 0.18, W_ * 0.5], fs=7.6))
    rows = [r for r in PC.inspect(params, vehicle) if r['st'] and r['st'] != ['ro']]
    if rows:
        st += [Spacer(1, 6), P(PR['changed'][i], H1)]
        st.append(tbl([[r['name'], PC.fmt(r['value']), PC.fmt(r['default']), ', '.join(STN[s][i] for s in r['st']),
                        db.text(r['name'], vehicle, lg)[0] if db.P.get(r['name']) else ''] for r in rows[:400]],
                      ['Param', PR['val'][i], 'Default', PR['st'][i], ''], [W_ * 0.22, W_ * 0.1, W_ * 0.1, W_ * 0.16, W_ * 0.42], fs=7.2))
    K_['build'](path, st, PR['title'][i])
    return path
