"""Eşitleme kuralı (ortak çekirdek): hiçbir kayıt silinmez ya da sessizce ezilmez."""
import json, os, tempfile


def mk():
    from app.core.archive import Archive
    return Archive(os.path.join(tempfile.mkdtemp(), 'a.db'))


def test_remote_delete_is_archived_locally_not_lost():
    a = mk()
    a.rec_put('pilot', 'p1', {'name': 'Ali', 'note': 'yerel'}, ts='2026-01-01 10:00:00')
    remote = {'records': [{'kind': 'pilot', 'id': 'p1', 'data': json.dumps({'name': 'Ali'}), 'updated_at': '2026-01-02 10:00:00', 'deleted': 1}]}
    a.merge(remote, source='laptop')
    row = a.db.execute("SELECT data, deleted FROM records WHERE kind='pilot' AND id='p1'").fetchone()
    assert row[1] == 1                                   # arşivlendi (listede görünmez)
    assert json.loads(row[0])['note'] == 'yerel'          # yerel veri korunur
    bk = a.backups()
    assert any(b['reason'] == 'archived' and b['id'] == 'p1' for b in bk)


def test_conflict_newer_wins_older_backed_up():
    a = mk()
    a.rec_put('aircraft', 'x', {'name': 'eski'}, ts='2026-01-01 10:00:00')
    remote = {'records': [{'kind': 'aircraft', 'id': 'x', 'data': json.dumps({'name': 'yeni'}), 'updated_at': '2026-01-03 10:00:00', 'deleted': 0}]}
    added, updated = a.merge(remote)
    assert updated == 1 and a.rec_get('aircraft', 'x')['name'] == 'yeni'
    lost = [json.loads(b['data']) for b in a.backups() if b['reason'] == 'conflict']
    assert lost and json.loads(lost[0]['data'])['name'] == 'eski'
    # aynı birleştirme tekrarlanınca yedek çoğalmaz
    a.merge(remote); a.merge(remote)
    assert len([b for b in a.backups() if b['reason'] == 'conflict']) == 1


def test_local_newer_keeps_local_and_backs_up_remote():
    a = mk()
    a.rec_put('aircraft', 'y', {'name': 'yerel-yeni'}, ts='2026-02-01 10:00:00')
    remote = {'records': [{'kind': 'aircraft', 'id': 'y', 'data': json.dumps({'name': 'uzak-eski'}), 'updated_at': '2026-01-01 10:00:00', 'deleted': 0}]}
    a.merge(remote)
    assert a.rec_get('aircraft', 'y')['name'] == 'yerel-yeni'
    assert any('uzak-eski' in b['data'] for b in a.backups())


def test_remote_new_records_added_and_reports_never_removed():
    a = mk()
    remote = {'records': [{'kind': 'pilot', 'id': 'n', 'data': '{"name":"Ayşe"}', 'updated_at': '2026-01-01 00:00:00', 'deleted': 0}],
              'reports': [{'report_id': 'R1', 'log_uid': 'u', 'sha256': 'x', 'verdict': 'normal', 'overall': 90, 'lang': 'tr', 'fmt': 'pdf'}]}
    added, _ = a.merge(remote)
    assert added == 2 and a.rec_get('pilot', 'n')['name'] == 'Ayşe' and a.find_report(rid='R1')
    a.merge({'records': [], 'reports': []})              # boş uzak veri hiçbir şeyi silmez
    assert a.rec_get('pilot', 'n') and a.find_report(rid='R1')


def test_analysis_conflict_backup():
    a = mk()
    base = {c: None for c in __import__('app.core.archive', fromlist=['COLS']).COLS}
    a._upsert(dict(base, uid='L1', name='log.BIN', verdict='normal', notes='not A', updated_at='2026-01-01 00:00:00'))
    a.merge({'analyses': [dict(base, uid='L1', name='log.BIN', verdict='crash', notes='not B', updated_at='2026-01-05 00:00:00')]})
    cur = a.get('L1')
    assert cur['verdict'] == 'crash' and 'not A' in cur['notes'] and 'not B' in cur['notes']
    assert any(b['tbl'] == 'analyses' and 'normal' in b['data'] for b in a.backups())


def test_template_conflict_backed_up(tmp_path):
    from app.core import sync
    a = mk()

    class S(dict):
        def save(self): pass
    s = S(templates={'default': {'org': 'A'}}, param_tx_cache={})
    sync.merge_payload(s, a, {'app': 'PixhawkLogAnaliz', 'name': 'pc2', 'templates': {'default': {'org': 'B'}}, 'records': []})
    assert s['templates']['default'] == {'org': 'A'}
    assert any(b['tbl'] == 'templates' and '"B"' in b['data'] for b in a.backups())
