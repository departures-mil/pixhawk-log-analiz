#!/usr/bin/env python3
# Gömülü kopya: ortak-cekirdek/delta/python/fcdelta.py (değiştirmeden). Güncellemek için yeniden kopyalayın.
"""fcdelta — FCD1 ikili yama aracı, yalnızca Python standart kütüphanesi (3.8+).

Format: ../FORMAT.md

Kütüphane:
    import fcdelta
    fcdelta.apply_file(old_path, patch_path, out_path)   # sabit bellek, akış halinde
    fcdelta.make_file(old_path, new_path, patch_path)    # referans; saf Python olduğu için yavaş
    fcdelta.apply(old_bytes, patch_bytes) -> bytes
    fcdelta.make(old_bytes, new_bytes) -> bytes
    fcdelta.read_header(patch_path_or_bytes) -> dict

CLI:
    python3 fcdelta.py make   <old> <new> <patch>
    python3 fcdelta.py apply  <old> <patch> <out>
    python3 fcdelta.py verify <old> <patch> <new>   (uyuşmazlıkta çıkış kodu 1)
    python3 fcdelta.py info   <patch>

Not: make saf Python'da ~1-3 MB/sn parçalar; CI'da Node sürümünü kullanın.
"""
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
import zlib

MAGIC = b"FCD1"
CODEC_ZLIB = 0x01
HEADER_LEN = 85
OP_END, OP_COPY, OP_INSERT = 0, 1, 2
MIN_CHUNK = 2 * 1024
MAX_CHUNK = 64 * 1024
MASK = 0xFFF80000
IO_BLOCK = 1 << 20


class FcDeltaError(Exception):
    pass


def _build_gear():
    g = []
    x = 0x9E3779B97F4A7C15
    m = (1 << 64) - 1
    for _ in range(256):
        x ^= (x << 13) & m
        x ^= x >> 7
        x ^= (x << 17) & m
        g.append(x & 0xFFFFFFFF)
    return g


GEAR = _build_gear()


def parse_header(h):
    if len(h) < HEADER_LEN:
        raise FcDeltaError("FCD1: yama çok kısa")
    if h[0:4] != MAGIC:
        raise FcDeltaError("FCD1: yama dosyası değil (magic)")
    if h[4] != CODEC_ZLIB:
        raise FcDeltaError("FCD1: bilinmeyen codec %d" % h[4])
    src_len, = struct.unpack_from("<Q", h, 5)
    dst_len, = struct.unpack_from("<Q", h, 45)
    return {
        "magic": "FCD1", "codec": "zlib",
        "srcLen": src_len, "srcSha256": bytes(h[13:45]).hex(),
        "dstLen": dst_len, "dstSha256": bytes(h[53:85]).hex(),
    }


def build_header(src_len, src_hash, dst_len, dst_hash):
    return MAGIC + bytes([CODEC_ZLIB]) + struct.pack("<Q", src_len) + src_hash + struct.pack("<Q", dst_len) + dst_hash


# ---------------------------------------------------------------------------
# APPLY
# ---------------------------------------------------------------------------

class _OpParser:
    """Açılmış op akışını parça parça işler (durum makinesi)."""

    def __init__(self, src_len, dst_len, on_copy, on_insert):
        self.src_len, self.dst_len = src_len, dst_len
        self.on_copy, self.on_insert = on_copy, on_insert
        self.state = 0
        self.op = 0
        self.fields = []
        self.need = 0
        self.v = 0
        self.shift = 0
        self.remain = 0
        self.written = 0
        self.ended = False

    def feed(self, c):
        i, n = 0, len(c)
        mv = memoryview(c)
        while i < n:
            if self.ended:
                raise FcDeltaError("FCD1: END sonrası fazla veri")
            if self.state == 0:
                op = c[i]
                i += 1
                if op == OP_END:
                    self.ended = True
                    continue
                if op == OP_COPY:
                    self.need = 2
                elif op == OP_INSERT:
                    self.need = 1
                else:
                    raise FcDeltaError("FCD1: geçersiz op %d" % op)
                self.op, self.fields, self.v, self.shift, self.state = op, [], 0, 0, 1
            elif self.state == 1:
                b = c[i]
                i += 1
                if self.shift > 56:
                    raise FcDeltaError("FCD1: varint çok uzun")
                self.v |= (b & 0x7F) << self.shift
                self.shift += 7
                if b < 0x80:
                    self.fields.append(self.v)
                    self.v, self.shift = 0, 0
                    if len(self.fields) == self.need:
                        self._exec()
            else:
                k = min(self.remain, n - i)
                self.on_insert(mv[i:i + k])
                i += k
                self.remain -= k
                if self.remain == 0:
                    self.state = 0

    def _grow(self, ln):
        self.written += ln
        if self.written > self.dst_len:
            raise FcDeltaError("FCD1: çıktı dstLen değerini aşıyor")

    def _exec(self):
        if self.op == OP_COPY:
            off, ln = self.fields
            if off + ln > self.src_len:
                raise FcDeltaError("FCD1: COPY aralığı kaynak dışında")
            self._grow(ln)
            if ln:
                self.on_copy(off, ln)
            self.state = 0
        else:
            ln = self.fields[0]
            self._grow(ln)
            self.remain = ln
            self.state = 2 if ln else 0

    def finish(self):
        if not self.ended:
            raise FcDeltaError("FCD1: END op yok (yama kesik)")
        if self.written != self.dst_len:
            raise FcDeltaError("FCD1: çıktı uzunluğu dstLen ile uyuşmuyor")


def _hash_file(path):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(IO_BLOCK)
            if not b:
                break
            h.update(b)
            n += len(b)
    return n, h.hexdigest()


def _inflate_stream(f, parser):
    """Dosyadan (başlık sonrası) okuyup zlib açar ve parser'a verir."""
    d = zlib.decompressobj()
    while True:
        b = f.read(256 * 1024)
        if not b:
            break
        if d.eof:
            raise FcDeltaError("FCD1: zlib akışından sonra fazla veri")
        out = d.decompress(b, 0)
        if out:
            parser.feed(out)
        if d.unused_data:
            raise FcDeltaError("FCD1: zlib akışından sonra fazla veri")
    tail = d.flush()
    if tail:
        parser.feed(tail)
    if not d.eof:
        raise FcDeltaError("FCD1: zlib akışı kesik")
    parser.finish()


def apply_file(old_path, patch_path, out_path, on_progress=None):
    """Yamayı sabit bellekle uygular; geçici dosyaya yazar, doğrular, sonra out_path'e taşır."""
    with open(patch_path, "rb") as pf:
        hd = parse_header(pf.read(HEADER_LEN))
        n, hx = _hash_file(old_path)
        if n != hd["srcLen"] or hx != hd["srcSha256"]:
            raise FcDeltaError("FCD1: kaynak dosya yamanın kaynağı değil")
        out_dir = os.path.dirname(os.path.abspath(out_path))
        fd, tmp = tempfile.mkstemp(prefix=".fcdelta-", dir=out_dir)
        ok = False
        try:
            with open(old_path, "rb") as of, os.fdopen(fd, "wb") as wf:
                h = hashlib.sha256()
                state = {"w": 0}

                def emit(b):
                    wf.write(b)
                    h.update(b)
                    state["w"] += len(b)
                    if on_progress:
                        on_progress(state["w"], hd["dstLen"])

                def on_copy(off, ln):
                    of.seek(off)
                    while ln > 0:
                        b = of.read(min(ln, IO_BLOCK))
                        if not b:
                            raise FcDeltaError("FCD1: kaynak dosya beklenenden kısa")
                        emit(b)
                        ln -= len(b)

                _inflate_stream(pf, _OpParser(hd["srcLen"], hd["dstLen"], on_copy, emit))
                if h.hexdigest() != hd["dstSha256"]:
                    raise FcDeltaError("FCD1: sonuç SHA-256 uyuşmuyor")
            os.replace(tmp, out_path)
            ok = True
        finally:
            if not ok:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
    return hd


def apply(old, patch):
    """Bellekte uygular, yeni dosyanın baytlarını döndürür."""
    hd = parse_header(patch[:HEADER_LEN])
    if len(old) != hd["srcLen"] or hashlib.sha256(old).hexdigest() != hd["srcSha256"]:
        raise FcDeltaError("FCD1: kaynak dosya yamanın kaynağı değil")
    out = bytearray()
    mo = memoryview(old)
    p = _OpParser(hd["srcLen"], hd["dstLen"], lambda o, n: out.extend(mo[o:o + n]), out.extend)
    _inflate_stream(io.BytesIO(patch[HEADER_LEN:]), p)
    if hashlib.sha256(out).hexdigest() != hd["dstSha256"]:
        raise FcDeltaError("FCD1: sonuç SHA-256 uyuşmuyor")
    return bytes(out)


def read_header(src, inspect=False):
    data = src if isinstance(src, (bytes, bytearray)) else open(src, "rb").read()
    hd = parse_header(data[:HEADER_LEN])
    hd["patchLen"] = len(data)
    if inspect:
        st = {"copyOps": 0, "copyBytes": 0, "insertOps": 0, "insertBytes": 0}

        def c(o, n):
            st["copyOps"] += 1
            st["copyBytes"] += n

        def ins(b):
            st["insertBytes"] += len(b)

        _inflate_stream(io.BytesIO(data[HEADER_LEN:]), _OpParser(hd["srcLen"], hd["dstLen"], c, ins))
        hd.update(st)
    return hd


# ---------------------------------------------------------------------------
# MAKE (referans; Node sürümüyle aynı algoritma)
# ---------------------------------------------------------------------------

def next_cut(d, start):
    n = len(d)
    lim = min(n, start + MAX_CHUNK)
    first = start + MIN_CHUNK - 1
    if first >= lim:
        return lim
    g = GEAR
    h = 0
    for j in range(max(start, first - 32), first):
        h = ((h << 1) + g[d[j]]) & 0xFFFFFFFF
    for i in range(first, lim):
        h = ((h << 1) + g[d[i]]) & 0xFFFFFFFF
        if not (h & MASK):
            return i + 1
    return lim


def _varint(v):
    out = bytearray()
    while v >= 0x80:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v)
    return bytes(out)


def _diff(old, new, write):
    mo, mn = memoryview(old), memoryview(new)
    index = {}
    off = 0
    while off < len(old):
        end = next_cut(old, off)
        k = (end - off, hashlib.sha256(mo[off:end]).digest())
        index.setdefault(k, off)
        off = end

    pend = [-1, 0]  # bekleyen COPY (ofset, uzunluk)

    def flush_copy():
        if pend[1]:
            write(bytes([OP_COPY]) + _varint(pend[0]) + _varint(pend[1]))
        pend[0], pend[1] = -1, 0

    def add_copy(o, n):
        if pend[1] and pend[0] + pend[1] == o:
            pend[1] += n
            return
        flush_copy()
        pend[0], pend[1] = o, n

    def add_insert(a, b):
        if b <= a:
            return
        flush_copy()
        write(bytes([OP_INSERT]) + _varint(b - a))
        write(mn[a:b])

    N, O = len(new), len(old)
    pos = lit = 0
    while pos < N:
        end = next_cut(new, pos)
        ln = end - pos
        src = index.get((ln, hashlib.sha256(mn[pos:end]).digest()))
        if src is None or mo[src:src + ln] != mn[pos:end]:
            pos = end
            continue
        b = 0
        while pos - b > lit and src - b > 0 and new[pos - b - 1] == old[src - b - 1]:
            b += 1
        e, s = end, src + ln
        BLK = 4096
        while e + BLK <= N and s + BLK <= O and mn[e:e + BLK] == mo[s:s + BLK]:
            e += BLK
            s += BLK
        while e < N and s < O and new[e] == old[s]:
            e += 1
            s += 1
        add_insert(lit, pos - b)
        add_copy(src - b, e - (pos - b))
        pos = lit = e
    add_insert(lit, N)
    flush_copy()
    write(bytes([OP_END]))


def make(old, new, level=9):
    comp = zlib.compressobj(level)
    parts = [build_header(len(old), hashlib.sha256(old).digest(), len(new), hashlib.sha256(new).digest())]
    _diff(old, new, lambda b: parts.append(comp.compress(b)))
    parts.append(comp.flush())
    return b"".join(parts)


def make_file(old_path, new_path, patch_path):
    with open(old_path, "rb") as f:
        old = f.read()
    with open(new_path, "rb") as f:
        new = f.read()
    tmp = patch_path + ".tmp"
    comp = zlib.compressobj(9)
    with open(tmp, "wb") as out:
        out.write(build_header(len(old), hashlib.sha256(old).digest(), len(new), hashlib.sha256(new).digest()))
        _diff(old, new, lambda b: out.write(comp.compress(b)))
        out.write(comp.flush())
    os.replace(tmp, patch_path)
    size = os.path.getsize(patch_path)
    return {"patchLen": size, "newLen": len(new), "ratio": (size / len(new)) if new else 0}


# ---------------------------------------------------------------------------

def main(argv):
    if len(argv) >= 4 and argv[0] == "make":
        s = make_file(argv[1], argv[2], argv[3])
        print("patch %s: %d bytes (full %d) ratio=%.2f%%" % (argv[3], s["patchLen"], s["newLen"], s["ratio"] * 100))
        return 0
    if len(argv) >= 4 and argv[0] == "apply":
        hd = apply_file(argv[1], argv[2], argv[3])
        print("ok %s sha256=%s" % (argv[3], hd["dstSha256"]))
        return 0
    if len(argv) >= 4 and argv[0] == "verify":
        fd, tmp = tempfile.mkstemp(prefix="fcdelta-verify-")
        os.close(fd)
        try:
            apply_file(argv[1], argv[2], tmp)
            if _hash_file(tmp) != _hash_file(argv[3]):
                print("MISMATCH", file=sys.stderr)
                return 1
            print("verified")
            return 0
        except FcDeltaError as e:
            print("MISMATCH: %s" % e, file=sys.stderr)
            return 1
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    if len(argv) >= 2 and argv[0] == "info":
        print(json.dumps(read_header(argv[1], True), indent=2))
        return 0
    print("kullanım: fcdelta.py make|apply|verify|info ...", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except FcDeltaError as e:
        print("hata: %s" % e, file=sys.stderr)
        sys.exit(2)
