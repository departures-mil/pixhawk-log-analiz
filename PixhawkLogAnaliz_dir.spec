# PyInstaller: klasör (onedir) derlemesi — Setup kurulum paketi bunu kullanır (hızlı açılış)
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
datas = [('app/data', 'app/data')]
datas += collect_data_files('arabic_reshaper') + collect_data_files('docx') + collect_data_files('certifi')
hidden = ['pymavlink.dialects.v20.ardupilotmega', 'pymavlink.dialects.v20.common', 'pymavlink.DFReader',
          'matplotlib.backends.backend_qtagg', 'matplotlib.backends.backend_agg', 'mpl_toolkits.mplot3d',
          'reportlab.graphics.barcode.common', 'bidi.algorithm']
hidden += collect_submodules('reportlab.pdfbase')
excl = ['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQuick', 'PySide6.QtQml',
        'PySide6.Qt3DCore', 'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PyQt5', 'PyQt6', 'IPython', 'scipy', 'pandas', 'pytest']
a = Analysis(['run.py'], pathex=['.'], datas=datas, hiddenimports=hidden, excludes=excl, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PixhawkLogAnaliz', console=False, upx=False,
          icon='app/data/app.ico', version=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PixhawkLogAnaliz')
