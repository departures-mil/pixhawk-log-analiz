"""CI: app/news.py içindeki geçerli sürümün notlarını release-notes.json olarak yazar (ortak reusable-release notes_json)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.version import VERSION  # noqa: E402
from app.news import notes_for  # noqa: E402

n = notes_for(VERSION)
if not n or not all(n.get(k) for k in ('tr', 'en', 'ar')):
    sys.exit(f'app/news.py: v{VERSION} için tr/en/ar notu yok')
out = sys.argv[1] if len(sys.argv) > 1 else 'release-notes.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(n, f, ensure_ascii=False, indent=1)
print('yazıldı', out)
