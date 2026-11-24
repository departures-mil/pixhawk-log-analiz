"""Sürüm notları ("Neler yeni" + release-notes.json). Yeni sürümde EN ÜSTE eklenir; tr/en/ar zorunlu."""

NEWS = [
    {'v': '1.1.0',
     'tr': 'Yeni Falcon görünümü, renk şeması seçici (eski görünüm: Klasik), koyu/açık tema ve yazı boyutu\n'
           'Sağ üstte Eşitle · Wi-Fi · Güncelle · tema · dil | Küçült · Orta · Tam ekran · Kapat; program tam ekran açılır\n'
           'Güncelleme: yalnızca değişen kısımlar (yama), SHA-256 doğrulaması; yüzde, MB, kalan ve hız\n'
           'Eşitlemede hiçbir kayıt silinmez ya da ezilmez: uzak silme arşivlenir, çakışmada eski hal yedeğe alınır\n'
           'İlk açılış rehberi, "Neler yeni", Kullanım Limitleri (yapay zekâ çağrıları), otomatik hata raporu',
     'en': 'New Falcon look, colour scheme picker (previous look: Classic), dark/light theme and font size\n'
           'Top right: Sync · Wi-Fi · Update · theme · language | Minimize · Half · Full screen · Close; opens full screen\n'
           'Updates: changed parts only (patch), SHA-256 verified; percent, MB, remaining and speed\n'
           'Sync never deletes or overwrites a record: remote deletions are archived, the older side of a conflict is backed up\n'
           'First-run guide, "What\'s new", Usage limits (AI calls), automatic error reports',
     'ar': 'مظهر Falcon الجديد، منتقي أنظمة الألوان (المظهر السابق: الكلاسيكي)، سمة داكنة/فاتحة وحجم الخط\n'
           'أعلى اليمين: مزامنة · Wi-Fi · تحديث · السمة · اللغة | تصغير · نصف · ملء الشاشة · إغلاق؛ يفتح بملء الشاشة\n'
           'التحديث: الأجزاء المتغيرة فقط (رقعة) مع تحقق SHA-256؛ النسبة والميغابايت والمتبقي والسرعة\n'
           'المزامنة لا تحذف أي سجل ولا تستبدله: الحذف البعيد يُؤرشف، والنسخة الأقدم عند التعارض تُحفظ احتياطياً\n'
           'دليل التشغيل الأول، "ما الجديد"، حدود الاستخدام (استدعاءات الذكاء الاصطناعي)، تقارير الأخطاء التلقائية'},
]


def notes_for(v):
    for n in NEWS:
        if n['v'] == str(v):
            return {k: n[k] for k in ('tr', 'en', 'ar')}
    return None
