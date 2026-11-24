"""fccore.progress — indirme ilerlemesi: ölçüm ve biçim (web FC.progress ile aynı metin).
Gösterilen: yüzde, "X,X MB / Y,Y MB", "kalan Z,Z MB", hız "N,N MB/sn"; yama kipinde "yalnızca değişen kısımlar".
Görünüm (ProgressBox) widgets.py içindedir."""
import math
import time

from . import i18n

MB = 1048576


def tracker(total=0, now=None):
    """Hız son ~3 saniyelik kayan pencereden. now() milisaniye döner (testte verilebilir)."""
    now = now or (lambda: time.monotonic() * 1000)
    st = {'total': total or 0, 'samples': [(now(), 0)]}

    class T:
        @staticmethod
        def update(d, finished=False):
            done = max(0, d or 0)
            t = now()
            s = st['samples']
            s.append((t, done))
            while len(s) > 2 and t - s[0][0] > 3000:
                s.pop(0)
            a = s[0]
            sec = (t - a[0]) / 1000
            speed = (done - a[1]) / sec if sec >= 0.25 else 0
            total_ = st['total']
            tot = total_ if total_ and done <= total_ else (done if finished else 0)
            return {'done': done, 'total': tot, 'pct': min(100, done / tot * 100) if tot else 0,
                    'remaining': max(0, tot - done) if tot else 0, 'speed': max(0, speed), 'finished': bool(finished)}

        @staticmethod
        def set_total(n):
            st['total'] = n or 0
    return T


def mb(b, l=None):
    return i18n.num(b / MB, 1, l) + ' MB'


def pct(p, l=None):
    n = int(math.floor(p))
    return ('%' + str(n)) if (i18n.norm(l) or i18n.lang()) == 'tr' else (str(n) + '%')


def format(p, patch=False, lang=None):  # noqa: A001
    """p → {percent, pctText, sizeText, leftText, speedText, modeText, detail}"""
    l = i18n.norm(lang) or i18n.lang()
    T = lambda k, v=None: i18n.t(k, v, l)  # noqa: E731
    r = {'percent': math.floor(p['pct']) if p.get('total') else None, 'pctText': '', 'sizeText': '', 'leftText': '',
         'speedText': '', 'modeText': T('fc.update.patchMode') if patch else ''}
    if p.get('finished'):
        r['percent'] = 100
        r['pctText'] = pct(100, l)
        r['sizeText'] = mb(p['total'], l) if p.get('total') else ''
        r['detail'] = ' · '.join(x for x in (T('fc.p.done'), r['sizeText'], r['modeText']) if x)
        return r
    if p.get('total'):
        r['pctText'] = pct(p['pct'], l)
        r['sizeText'] = mb(p['done'], l) + ' / ' + mb(p['total'], l)
        r['leftText'] = T('fc.p.left', {'x': mb(p['remaining'], l)})
    else:
        r['sizeText'] = mb(p['done'], l)
    r['speedText'] = (i18n.num(p['speed'] / MB, 1, l) + ' ' + T('fc.p.speed')) if p.get('speed', 0) > 0 else T('fc.p.calc')
    r['detail'] = ' · '.join(x for x in (r['pctText'], r['sizeText'], r['leftText'], r['speedText']) if x)
    return r
