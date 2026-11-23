"""Hızlı DataFlash (.BIN) okuyucu — numpy ile vektörel ayrıştırma.

pymavlink'in mesaj mesaj Python döngüsü yerine dosya bellek eşlemesiyle (mmap) parça parça taranır:
1) 0xA3 0x95 başlık adayları bulunur, FMT mesajlarından mesaj boyları öğrenilir,
2) zincir denetimiyle (başlık + boy = sonraki başlık) yalnızca gerçek mesajlar tutulur,
3) her mesaj türü numpy yapılandırılmış dizisine tek seferde dönüştürülür,
4) yüksek frekanslı türler okunmadan önce zaman damgasına göre seyreltilir.

GB seviyesindeki loglar sabit bellekle ve pymavlink'e göre ~20-50 kat hızlı okunur.
"""
from __future__ import annotations
import mmap, os, time
import numpy as np

HEAD0, HEAD1, FMT_ID = 0xA3, 0x95, 128
CHUNK = 48 << 20

# DataFlash biçim karakteri -> (numpy tipi, ölçek)
FMT = {'b': ('i1', None), 'B': ('u1', None), 'h': ('<i2', None), 'H': ('<u2', None), 'i': ('<i4', None), 'I': ('<u4', None),
       'f': ('<f4', None), 'd': ('<f8', None), 'n': ('S4', None), 'N': ('S16', None), 'Z': ('S64', None),
       'c': ('<i2', 0.01), 'C': ('<u2', 0.01), 'e': ('<i4', 0.01), 'E': ('<u4', 0.01), 'L': ('<i4', 1e-7),
       'M': ('u1', None), 'q': ('<i8', None), 'Q': ('<u8', None), 'a': (('<i2', (32,)), None)}


class Fmt:
    __slots__ = ('mid', 'length', 'name', 'fmt', 'cols', 'dtype', 'scale', 'ok', 'toff', 'tdt', 'kfield')

    def __init__(self, mid, length, name, fmt, cols):
        self.mid, self.length, self.name, self.fmt, self.cols = mid, length, name, fmt, cols
        self.ok = False; self.scale = {}; self.toff = None; self.tdt = None; self.kfield = None
        try:
            if len(fmt) != len(cols): return
            fields = []; off = 0; offs = {}
            for ch, c in zip(fmt, cols):
                dt, sc = FMT[ch]
                d = np.dtype(dt)
                fields.append((c, d)); offs[c] = (off, d); off += d.itemsize
                if sc: self.scale[c] = sc
            if off + 3 != length: return
            self.dtype = np.dtype(fields)
            if 'TimeUS' in offs: self.toff, self.tdt = offs['TimeUS'][0], offs['TimeUS'][1]
            elif 'TimeMS' in offs: self.toff, self.tdt = offs['TimeMS'][0], offs['TimeMS'][1]
            for k in ('I', 'C', 'Instance'):
                if k in offs and offs[k][1].kind in 'iu':
                    self.kfield = (k, offs[k][0], offs[k][1]); break
            self.ok = True
        except Exception:
            self.ok = False


def _s(b):
    return b.split(b'\0', 1)[0].decode('latin-1', 'replace')


class Reader:
    """Bir .BIN dosyasını tarar. want: tür adı -> azami Hz (0 = hepsi). none_key: örnek anahtarı kullanılmayan türler."""

    def __init__(self, path, want: dict, none_key=(), progress=None, cancel=None):
        self.path = path; self.want = want; self.none_key = set(none_key)
        self.progress = progress; self.cancel = cancel
        self.fmts: dict[int, Fmt] = {}
        self.lens = np.zeros(256, np.int64)
        self.lens[FMT_ID] = 89
        self.out: dict[str, list] = {}       # ad -> [yapılandırılmış dizi parçaları]
        self.counts: dict[str, int] = {}
        self.last_bucket: dict = {}
        self.t0 = None
        self.truncated = False

    # ------------------------------------------------------------------
    def _add_fmts(self, buf, pos):
        for p in pos:
            b = bytes(buf[p + 3:p + 89])
            if len(b) < 86: continue
            mid, ln = b[0], b[1]
            name = _s(b[2:6]); fmt = _s(b[6:22]); cols = _s(b[22:86]).split(',')
            if mid == FMT_ID or ln < 3: continue
            f = Fmt(mid, ln, name, fmt, cols)
            old = self.fmts.get(mid)
            if old is None or not old.ok:
                self.fmts[mid] = f
                self.lens[mid] = ln

    def run(self):
        size = os.path.getsize(self.path)
        with open(self.path, 'rb') as fh:
            mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                buf = np.frombuffer(mm, np.uint8)
                self._scan(buf, size)
                del buf
            finally:
                try: mm.close()
                except BufferError: pass
        return self

    def _scan(self, buf, N):
        prev_end = 0
        s = 0
        last_prog = 0.0
        while s < N - 3:
            if self.cancel and self.cancel():
                raise InterruptedError
            e = min(N, s + CHUNK)
            ext = min(N, e + 300)
            seg = buf[s:ext - 1]
            c = np.flatnonzero(seg == HEAD0)
            c = c[seg[np.minimum(c + 1, len(seg) - 1)] == HEAD1] + s
            c = c[c + 3 <= N]
            if len(c) == 0:
                s = e; continue
            typ = buf[c + 2].astype(np.int64)
            # Bu parçadaki FMT mesajlarını önce öğren
            fm = c[(typ == FMT_ID) & (c < e) & (c + 89 <= N)]
            if len(fm): self._add_fmts(buf, fm)
            ln = self.lens[typ]
            nxt = c + ln
            okm = (ln > 0) & (nxt <= N)
            # Zincir: sonraki mesaj da bir başlıkla başlamalı (ya da dosya sonu)
            mark = np.zeros(ext - s + 400, bool); mark[c - s] = True
            nn = np.clip(nxt - s, 0, len(mark) - 1)
            chain = mark[nn] | (nxt >= N - 2)
            v = okm & chain
            P = c[v]; L_ = ln[v]; T_ = typ[v]; NX = nxt[v]
            # Gerçek zincir düğümleri: başka bir geçerli mesajın hedefi olanlar
            tgt = np.zeros(len(mark), bool); tgt[np.clip(NX - s, 0, len(mark) - 1)] = True
            targeted = tgt[P - s]
            keep = targeted.copy()
            # Hedeflenmeyen adaylar: tutulan bir mesajın içinde değilse (yeniden eşleme noktası) tut
            un = np.flatnonzero(~targeted)
            if len(un):
                kp = P[keep]; ke = (P + L_)[keep]
                if len(kp):
                    j = np.searchsorted(kp, P[un], side='right') - 1
                    inside = (j >= 0) & (ke[np.maximum(j, 0)] > P[un])
                else:
                    inside = np.zeros(len(un), bool)
                inside |= P[un] < prev_end
                keep[un[~inside]] = True
            keep &= (P < e) & (P >= prev_end) | ((P < e) & targeted & (P >= prev_end))
            P, L_, T_ = P[keep], L_[keep], T_[keep]
            if len(P):
                prev_end = int(P[-1] + L_[-1])
            self._consume(buf, P, T_)
            s = e
            if self.progress and time.time() - last_prog > 0.12:
                last_prog = time.time()
                try: self.progress(min(0.999, e / N))
                except Exception: pass
        if prev_end < N - 512: self.truncated = False

    def _consume(self, buf, P, T_):
        order = np.argsort(T_, kind='stable')
        P, T_ = P[order], T_[order]
        bounds = np.flatnonzero(np.diff(T_)) + 1
        starts = np.r_[0, bounds]; ends = np.r_[bounds, len(T_)]
        for a, b in zip(starts, ends):
            mid = int(T_[a]); f = self.fmts.get(mid)
            if f is None or not f.ok or mid == FMT_ID: continue
            if f.name not in self.want:
                self.counts[f.name] = self.counts.get(f.name, 0) + int(b - a)
                continue
            pos = P[a:b]
            self.counts[f.name] = self.counts.get(f.name, 0) + len(pos)
            rate = self.want.get(f.name, 0)
            if rate and f.toff is not None:
                tb = buf[(pos + 3 + f.toff)[:, None] + np.arange(f.tdt.itemsize)].copy().view(f.tdt).ravel().astype(np.float64)
                if f.toff is not None and 'TimeMS' in f.dtype.names and 'TimeUS' not in f.dtype.names: tb = tb * 1000
                if f.kfield and f.name not in self.none_key:
                    k_, ko, kd = f.kfield
                    kv = buf[(pos + 3 + ko)[:, None] + np.arange(kd.itemsize)].copy().view(kd).ravel().astype(np.int64)
                else:
                    kv = np.zeros(len(pos), np.int64)
                bucket = np.floor(tb / 1e6 * rate).astype(np.int64)
                sel = np.zeros(len(pos), bool)
                for kk in np.unique(kv):
                    m = np.flatnonzero(kv == kk)
                    bk = bucket[m]
                    first = np.r_[True, bk[1:] != bk[:-1]]
                    lb = self.last_bucket.get((f.name, int(kk)))
                    if lb is not None: first[0] = bk[0] != lb
                    sel[m[first]] = True
                    self.last_bucket[(f.name, int(kk))] = int(bk[-1])
                pos = pos[sel]
                if f.name == 'GPS' and not getattr(self, '_gps_raw_done', False):
                    pass
            if not len(pos): continue
            rows = buf[(pos + 3)[:, None] + np.arange(f.length - 3)]
            arr = np.ascontiguousarray(rows).view(f.dtype).ravel()
            self.out.setdefault(f.name, []).append(arr)

    def arrays(self):
        """ad -> (Fmt, tek yapılandırılmış dizi)"""
        res = {}
        byname = {f.name: f for f in self.fmts.values() if f.ok}
        for n, parts in self.out.items():
            f = byname.get(n)
            if f is None: continue
            try:
                res[n] = (f, np.concatenate(parts) if len(parts) > 1 else parts[0])
            except Exception:
                # Aynı ada farklı biçim (nadiren): ilk biçimi koru
                res[n] = (f, parts[0])
        return res


def col(f: Fmt, arr, c):
    """Ölçeklenmiş sayısal sütun (float64)."""
    v = arr[c]
    if v.dtype.kind in 'S' or v.ndim > 1: return None
    v = v.astype(np.float64)
    sc = f.scale.get(c)
    return v * sc if sc else v
