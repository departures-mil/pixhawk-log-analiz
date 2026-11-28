# PyInstaller: klasör (onedir) derlemesi — Setup kurulum paketi bunu kullanır (hızlı açılış)
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs
datas = [('app/data', 'app/data')]
datas += collect_data_files('arabic_reshaper') + collect_data_files('docx') + collect_data_files('certifi')
datas += collect_data_files('imageio_ffmpeg') + collect_data_files('edge_tts')
# ortak çekirdek: Inter + Noto Sans Arabic yazı tipleri (zorunlu). fccore kurulu paket değil (depo kökünde) → yolla ekle
datas += [('fccore/fonts', 'fccore/fonts')]
hidden = ['pymavlink.dialects.v20.ardupilotmega', 'pymavlink.dialects.v20.common', 'pymavlink.DFReader',
          'matplotlib.backends.backend_qtagg', 'matplotlib.backends.backend_agg', 'mpl_toolkits.mplot3d',
          'reportlab.graphics.barcode.common', 'bidi.algorithm', 'PySide6.QtNetwork', 'cryptography.hazmat.primitives.ciphers.aead',
          'PySide6.QtSvg', 'winreg']
import os as _os
hidden += ['fccore.' + f[:-3] for f in _os.listdir('fccore') if f.endswith('.py') and f != '__init__.py'] + ['fccore']
# çeviri / OCR / belge: CTranslate2 (NLLB çevrimdışı), sentencepiece, PyMuPDF
hidden += ['ctranslate2', 'sentencepiece', 'pymupdf', 'fitz'] + collect_submodules('pymupdf')
bins = collect_dynamic_libs('ctranslate2') + collect_dynamic_libs('pymupdf')
hidden += collect_submodules('reportlab.pdfbase') + collect_submodules('edge_tts') + ['imageio_ffmpeg', 'aiohttp', 'certifi']
excl = ['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQuick', 'PySide6.QtQml',
        'PySide6.Qt3DCore', 'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PyQt5', 'PyQt6', 'IPython', 'scipy', 'pandas', 'pytest']
a = Analysis(['run.py'], pathex=['.'], datas=datas, binaries=bins, hiddenimports=hidden, excludes=excl, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PixhawkLogAnaliz', console=False, upx=False,
          icon='app/data/app.ico', version=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PixhawkLogAnaliz')
