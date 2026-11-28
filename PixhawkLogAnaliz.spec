# PyInstaller: tek dosya Windows exe
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
# sentencepiece: _sentencepiece.pyd'nin DLL'leri (delvewheel *.libs / paket içi) hem kendi klasörüne hem köke
from PyInstaller.utils.hooks import collect_all as _ca
import glob as _glob, importlib.util as _iu
_d, _b, _h = _ca('sentencepiece'); datas += _d; bins += _b; hidden += _h
_spd = _os.path.dirname(_iu.find_spec('sentencepiece').origin)
for _f in _glob.glob(_os.path.join(_spd, '*.dll')) + _glob.glob(_os.path.join(_os.path.dirname(_spd), 'sentencepiece*.libs', '*.dll')):
    bins += [(_f, '.'), (_f, 'sentencepiece'), (_f, 'sentencepiece.libs')]
hidden += collect_submodules('reportlab.pdfbase') + collect_submodules('edge_tts') + ['imageio_ffmpeg', 'aiohttp', 'certifi']
excl = ['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQuick', 'PySide6.QtQml',
        'PySide6.Qt3DCore', 'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PyQt5', 'PyQt6', 'IPython', 'scipy', 'pandas', 'pytest']
a = Analysis(['run.py'], pathex=['.'], datas=datas, binaries=bins, hiddenimports=hidden, excludes=excl, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='PixhawkLogAnaliz', console=False, upx=False,
          icon='app/data/app.ico', version=None)
