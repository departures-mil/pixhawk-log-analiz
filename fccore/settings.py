"""fccore.settings — Falcon ayarlar ızgarası. Sıra: [Görünüm] · uygulamanın kartları · [Kullanım Limitleri] ·
[Otomatik hata raporu] · [Hakkında] · Admin ile iletişim (HER ZAMAN SON).
    grid = settings.build(cards=[benim_kartim], usage={'firebase': False, 'ai': False}, about={'version': '2.2.0', 'on_check': ctl.check})
    grid.add(yeni_kart)   # iletişim kartı yine sonda kalır
"""
from .widgets import Columns
from . import cards as C


class SettingsGrid(Columns):
    def __init__(self):
        super().__init__(min_col=320, gap=18, max_cols=3)
        self.contact = None

    def add(self, w, before=None):
        if before is None and self.contact is not None and w is not self.contact:
            before = self.contact
        return super().add(w, before)


def build(cards=None, look=True, usage=None, crash=True, about=None, onboarding=None, contact=True):
    g = SettingsGrid()
    if look:
        g.add(C.look_card())
    for c in cards or []:
        if c is not None:
            g.add(c)
    if usage is not False:
        g.add(C.usage_card(**(usage or {})))
    if crash:
        g.add(C.crash_card())
    if about is not False:
        a = dict(about or {})
        g.add(C.about_card(version=a.get('version', ''), on_check=a.get('on_check'), whatsnew=a.get('whatsnew', True),
                           onboarding=onboarding))
    if contact:
        g.contact = C.contact_card()
        g.add(g.contact)
    return g
