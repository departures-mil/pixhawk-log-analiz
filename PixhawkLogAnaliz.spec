# PyInstaller: tek dosya Windows exe
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
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
hidden += collect_submodules('reportlab.pdfbase') + collect_submodules('edge_tts') + ['imageio_ffmpeg', 'aiohttp', 'certifi']
excl = ['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQuick', 'PySide6.QtQml',
        'PySide6.Qt3DCore', 'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PyQt5', 'PyQt6', 'IPython', 'scipy', 'pandas', 'pytest']
a = Analysis(['run.py'], pathex=['.'], datas=datas, hiddenimports=hidden, excludes=excl, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='PixhawkLogAnaliz', console=False, upx=False,
          icon='app/data/app.ico', version=None)
