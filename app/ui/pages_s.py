"""Problem Çözücü sayfası: belirti seç / yaz → derin, hedefli testler → teşhis ve adım adım çözüm."""
from __future__ import annotations
import html, os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QTextBrowser, QPlainTextEdit, QCheckBox,
                               QSplitter, QWidget, QFileDialog)
from .i18n import t, lang
from .common import label, button, run_bg, error
from .pages_a import Page, _md
from ..core import solver as SV

E = html.escape


class SolverPage(Page):
    def __init__(self, win):
        super().__init__(win)
        lg = lang()
        v = QVBoxLayout(self); v.setContentsMargins(16, 12, 16, 12)
        v.addWidget(label('🩺 ' + t('nav_solver'), 'h1'))
        v.addWidget(label(t('sv_intro'), 'muted', wrap=True))
        self.info = label('', 'muted'); v.addWidget(self.info)
        sp = QSplitter(Qt.Horizontal)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(label(t('sv_pick'), 'h2'))
        self.sy = QListWidget()
        for sid, lab, _k, _c in SV.SYMPTOMS:
            it = QListWidgetItem(SV._l(lab, lg)); it.setData(Qt.UserRole, sid)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Unchecked); self.sy.addItem(it)
        lv.addWidget(self.sy, 1)
        lv.addWidget(label(t('sv_free'), 'h2'))
        self.txt = QPlainTextEdit(); self.txt.setPlaceholderText(t('sv_free_ph')); self.txt.setMaximumHeight(90); lv.addWidget(self.txt)
        self.ai = QCheckBox('🤖 ' + t('sv_ai')); lv.addWidget(self.ai)
        bh = QHBoxLayout()
        bh.addWidget(button('🔍 ' + t('sv_run'), self.run, primary=True)); bh.addWidget(button('🧪 ' + t('sv_all'), lambda: self.run(all_=True)))
        lv.addLayout(bh)
        sp.addWidget(left)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        self.out = QTextBrowser(); self.out.setOpenExternalLinks(False); rv.addWidget(self.out, 1)
        rb = QHBoxLayout(); rb.addStretch(1); rb.addWidget(button('💾 ' + t('sv_save'), self.save)); rv.addLayout(rb)
        sp.addWidget(right); sp.setSizes([360, 900])
        v.addWidget(sp, 1)
        if lg == 'ar': self.out.setLayoutDirection(Qt.RightToLeft)
        self.md = ''
        self.on_show()

    def on_show(self):
        from ..core import ai as AI
        ok = AI.available(self.win.settings)
        self.ai.setEnabled(ok); self.ai.setChecked(ok and self.win.settings.get('sv_ai', True))
        A = self.win.A
        self.info.setText(t('sv_nolog') if not A else f"{os.path.basename(A.L.path)} · {A.vehicle}")

    def on_analysis(self, A):
        self.on_show(); self.out.clear(); self.md = ''

    def run(self, all_=False):
        A = self.win.A
        if not A: return error(self, t('no_log'))
        lg = lang()
        sy = [] if all_ else [self.sy.item(i).data(Qt.UserRole) for i in range(self.sy.count()) if self.sy.item(i).checkState() == Qt.Checked]
        text = '' if all_ else self.txt.toPlainText().strip()
        use_ai = self.ai.isChecked(); self.win.settings['sv_ai'] = use_ai
        self.out.setHtml(f'<p style="color:#94A3B8">⏳ {E(t("sv_working"))}</p>')

        def job():
            R = SV.solve(A, sy, text, lg)
            md = SV.to_markdown(R, lg)
            if use_ai:
                try:
                    x = SV.ai_solve(A, R, self.win.settings, self.win.usage, lg, text)
                    if x: md = '## 🤖 ' + t('sv_ai_h') + '\n' + x + '\n\n' + md
                except Exception as e:
                    md = f'> 🤖 {t("sv_ai_fail")}: {e}\n\n' + md
            return md

        def ok(md):
            self.md = md
            d = 'rtl' if lg == 'ar' else 'ltr'
            self.out.setHtml(f'<div dir="{d}">' + _md(md) + '</div>')

        run_bg(job, on_done=ok, on_fail=lambda e: error(self, e))

    def save(self):
        if not self.md: return
        p, _ = QFileDialog.getSaveFileName(self, t('sv_save'), 'problem_cozucu.md', 'Markdown (*.md)')
        if p:
            with open(p, 'w', encoding='utf-8') as f: f.write(self.md)
