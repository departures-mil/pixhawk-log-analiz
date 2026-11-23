"""Arşiv: analiz edilen loglar ve üretilen raporlar (SQLite). Eşitlemede hiçbir kayıt silinmez."""
from __future__ import annotations
import json, os, shutil, sqlite3, threading, time
from .paths import data_dir

COLS = ['uid', 'name', 'src_path', 'stored', 'size', 'vehicle', 'version', 'flight_date', 'duration', 'flight_time',
        'verdict', 'cause', 'overall', 'health', 'facts', 'analyzed_at', 'updated_at', 'device', 'notes', 'tags',
        'aircraft', 'pilot', 'profile', 'findings', 'pilot_scores', 'anomaly_index', 'flight_ts']
NEW_COLS = {'aircraft': 'TEXT', 'pilot': 'TEXT', 'profile': 'TEXT', 'findings': 'TEXT', 'pilot_scores': 'TEXT',
            'anomaly_index': 'INTEGER', 'flight_ts': 'REAL'}
# Genel kayıt türleri (filo, bakım, pilot, sınıf, sınav, sonuç, kullanıcı). Silme = işaret (eşitlemede geri gelmesin).
KINDS = ('aircraft', 'maint', 'pilot', 'class', 'exam', 'result', 'user')


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


class Archive:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), 'archive.db')
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS analyses(uid TEXT PRIMARY KEY, name TEXT, src_path TEXT, stored TEXT, size INTEGER,
            vehicle TEXT, version TEXT, flight_date TEXT, duration REAL, flight_time REAL, verdict TEXT, cause TEXT,
            overall INTEGER, health TEXT, facts TEXT, analyzed_at TEXT, updated_at TEXT, device TEXT, notes TEXT, tags TEXT);
        CREATE TABLE IF NOT EXISTS reports(report_id TEXT PRIMARY KEY, log_uid TEXT, sha256 TEXT, verdict TEXT, overall INTEGER,
            lang TEXT, fmt TEXT, path TEXT, created TEXT, device TEXT, log_name TEXT);
        CREATE INDEX IF NOT EXISTS rep_sha ON reports(sha256);
        CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, data TEXT, updated_at TEXT, deleted INTEGER DEFAULT 0, PRIMARY KEY(kind, id));
        ''')
        have = {r[1] for r in self.db.execute('PRAGMA table_info(analyses)').fetchall()}
        for c, typ in NEW_COLS.items():
            if c not in have: self.db.execute(f'ALTER TABLE analyses ADD COLUMN {c} {typ}')
        self.db.commit()

    def logs_dir(self):
        d = os.path.join(data_dir(), 'archive_logs'); os.makedirs(d, exist_ok=True); return d

    # ----------------------------------------------------------- analizler
    def add_analysis(self, uid, A, src_path, device='', copy=True, max_mb=200, encrypt=False):
        f = A.facts; L = A.L
        stored = ''
        old = self.get(uid)
        if old and old['stored'] and os.path.exists(old['stored']):
            stored = old['stored']
        elif copy and os.path.exists(src_path) and os.path.getsize(src_path) <= max_mb * 1e6:
            dst = os.path.join(self.logs_dir(), uid[:12] + '_' + os.path.basename(src_path)) + ('.pxloc' if encrypt else '')
            try:
                if not os.path.exists(dst):
                    if encrypt:
                        from .security import encrypt_local_file
                        encrypt_local_file(src_path, dst)
                    else:
                        shutil.copy2(src_path, dst)
                stored = dst
            except Exception:
                stored = ''
        health = {k: v['score'] for k, v in A.health.items()}
        fk = sorted({x['k'] for h in A.health.values() for x in h['findings']} | {x['text']['k'] for x in A.param_findings if x['sev'] > 0}
                    | ({'cause_' + A.root['cause']} if A.root.get('cause') else set()) | ({'anomaly'} if A.anomalies else set()))
        fts = None
        try: fts = A.L.unix_at(A.flights[0][0] if A.flights else 0)
        except Exception: pass
        row = dict(uid=uid, name=os.path.basename(src_path), src_path=src_path, stored=stored, size=L.size,
                   vehicle=A.vehicle, version=L.version or '', flight_date=_fdate(A),
                   duration=float(L.duration), flight_time=float(f.get('flight_time', 0)),
                   verdict=A.verdict.get('kind', ''), cause=(A.root or {}).get('cause', ''), overall=int(A.overall),
                   health=json.dumps(health), facts=json.dumps(_clean(f), ensure_ascii=False),
                   analyzed_at=old['analyzed_at'] if old else now(), updated_at=now(), device=device,
                   notes=old['notes'] if old else '', tags=old['tags'] if old else '',
                   aircraft=(old or {}).get('aircraft') or getattr(A, 'serial', '') or '', pilot=(old or {}).get('pilot') or '',
                   profile=A.profile, findings=json.dumps(fk), pilot_scores=json.dumps(_clean(A.pilot or {})),
                   anomaly_index=int(getattr(A, 'anomaly_index', 0) or 0), flight_ts=fts)
        self._upsert(row)
        return row

    def _upsert(self, row):
        with self.lock:
            self.db.execute(f"INSERT OR REPLACE INTO analyses({','.join(COLS)}) VALUES({','.join('?' * len(COLS))})",
                            [row.get(c) for c in COLS])
            self.db.commit()

    def get(self, uid):
        with self.lock:
            r = self.db.execute('SELECT * FROM analyses WHERE uid=?', (uid,)).fetchone()
        return dict(r) if r else None

    def list(self, q=''):
        with self.lock:
            if q:
                like = f'%{q}%'
                rs = self.db.execute('SELECT * FROM analyses WHERE name LIKE ? OR verdict LIKE ? OR cause LIKE ? OR notes LIKE ? OR tags LIKE ? ORDER BY analyzed_at DESC',
                                     (like,) * 5).fetchall()
            else:
                rs = self.db.execute('SELECT * FROM analyses ORDER BY analyzed_at DESC').fetchall()
        return [dict(r) for r in rs]

    def set_notes(self, uid, notes, tags=None):
        with self.lock:
            if tags is None:
                self.db.execute('UPDATE analyses SET notes=?, updated_at=? WHERE uid=?', (notes, now(), uid))
            else:
                self.db.execute('UPDATE analyses SET notes=?, tags=?, updated_at=? WHERE uid=?', (notes, tags, now(), uid))
            self.db.commit()

    def set_field(self, uid, **kw):
        with self.lock:
            for k, v in kw.items():
                if k in COLS: self.db.execute(f'UPDATE analyses SET {k}=?, updated_at=? WHERE uid=?', (v, now(), uid))
            self.db.commit()

    # ------------------------------------------------- genel kayıtlar
    def rec_put(self, kind, rid, data, ts=None):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?,0)', (kind, rid, json.dumps(_clean(data), ensure_ascii=False), ts or now()))
            self.db.commit()

    def rec_get(self, kind, rid):
        with self.lock:
            r = self.db.execute('SELECT data FROM records WHERE kind=? AND id=? AND deleted=0', (kind, rid)).fetchone()
        return json.loads(r[0]) if r else None

    def rec_list(self, kind):
        with self.lock:
            rs = self.db.execute('SELECT id, data FROM records WHERE kind=? AND deleted=0 ORDER BY updated_at', (kind,)).fetchall()
        out = []
        for rid, d in rs:
            x = json.loads(d); x.setdefault('id', rid); out.append(x)
        return out

    def rec_del(self, kind, rid):
        with self.lock:
            self.db.execute('UPDATE records SET deleted=1, updated_at=? WHERE kind=? AND id=?', (now(), kind, rid)); self.db.commit()

    def remove(self, uid):
        """Yalnızca kullanıcı açıkça isterse (arşivden kaldır)."""
        with self.lock:
            self.db.execute('DELETE FROM analyses WHERE uid=?', (uid,)); self.db.commit()

    # ------------------------------------------------------------- raporlar
    def add_report(self, rid, log_uid, sha, verdict, overall, lang, fmt, path, device='', log_name=''):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO reports VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                            (rid, log_uid, sha, verdict, int(overall), lang, fmt, path, now(), device, log_name))
            self.db.commit()

    def reports(self, log_uid=None):
        with self.lock:
            if log_uid:
                rs = self.db.execute('SELECT * FROM reports WHERE log_uid=? ORDER BY created DESC', (log_uid,)).fetchall()
            else:
                rs = self.db.execute('SELECT * FROM reports ORDER BY created DESC').fetchall()
        return [dict(r) for r in rs]

    def find_report(self, rid=None, sha=None):
        with self.lock:
            if sha:
                r = self.db.execute('SELECT * FROM reports WHERE sha256=?', (sha,)).fetchone()
                if r: return dict(r)
            if rid:
                r = self.db.execute('SELECT * FROM reports WHERE report_id=?', (rid.strip().upper(),)).fetchone()
                if r: return dict(r)
        return None

    # -------------------------------------------------------------- eşitleme
    def export(self):
        with self.lock:
            recs = [dict(kind=k, id=i, data=d, updated_at=u, deleted=x) for k, i, d, u, x in
                    self.db.execute('SELECT kind, id, data, updated_at, deleted FROM records').fetchall()]
        return {'analyses': self.list(), 'reports': self.reports(), 'records': recs}

    def merge(self, data):
        """Gelen kayıtları ekler; aynı kayıt varsa daha yeni olan kazanır, notlar birleştirilir. Hiçbir şey silinmez."""
        added = updated = 0
        for r in data.get('analyses', []):
            if not r.get('uid'): continue
            cur = self.get(r['uid'])
            if not cur:
                r = dict(r); r['stored'] = ''  # yerel dosya yolu başka cihazda geçersiz
                self._upsert(r); added += 1; continue
            merged = dict(cur)
            if (r.get('updated_at') or '') > (cur.get('updated_at') or ''):
                for c in COLS:
                    if c in ('stored', 'src_path'): continue
                    if r.get(c) not in (None, ''): merged[c] = r[c]
            merged['notes'] = _union_text(cur.get('notes'), r.get('notes'))
            merged['tags'] = ','.join(sorted(set(filter(None, (cur.get('tags') or '').split(',') + (r.get('tags') or '').split(',')))))
            if merged != cur:
                self._upsert(merged); updated += 1
        for r in data.get('records', []):
            if r.get('kind') not in KINDS or not r.get('id'): continue
            with self.lock:
                cur = self.db.execute('SELECT updated_at FROM records WHERE kind=? AND id=?', (r['kind'], r['id'])).fetchone()
                if cur is None or (r.get('updated_at') or '') > (cur[0] or ''):
                    self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?,?)', (r['kind'], r['id'], r.get('data') or '{}', r.get('updated_at') or now(), int(r.get('deleted') or 0)))
                    self.db.commit()
                    if cur is None: added += 1
                    else: updated += 1
        for r in data.get('reports', []):
            if not r.get('report_id'): continue
            if not self.find_report(rid=r['report_id']):
                with self.lock:
                    self.db.execute('INSERT OR IGNORE INTO reports VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                                    (r['report_id'], r.get('log_uid'), r.get('sha256'), r.get('verdict'), int(r.get('overall') or 0),
                                     r.get('lang'), r.get('fmt'), '', r.get('created'), r.get('device'), r.get('log_name')))
                    self.db.commit()
                added += 1
        return added, updated


def _fdate(A):
    try:
        u = A.L.unix_at(A.flights[0][0] if A.flights else 0)
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(u)) if u else ''
    except Exception:
        return ''


def _union_text(a, b):
    a = (a or '').strip(); b = (b or '').strip()
    if not a: return b
    if not b or b in a: return a
    if a in b: return b
    return a + '\n---\n' + b


def _clean(o):
    import numpy as np
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.ndarray): return o.tolist()
    return o


def file_uid(path):
    """Log dosyasının içerik kimliği (ilk+son 4 MB + boyut → hızlı ve cihazlar arası aynı)."""
    import hashlib
    h = hashlib.sha256()
    size = os.path.getsize(path)
    h.update(str(size).encode())
    with open(path, 'rb') as f:
        h.update(f.read(4 << 20))
        if size > 8 << 20:
            f.seek(-(4 << 20), 2); h.update(f.read())
    return h.hexdigest()
