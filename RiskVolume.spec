# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Logo', 'Logo'),
        ('ScalpSettings_Py.json', '.'),
        ('scalp_settings.json', '.'),
    ],
    hiddenimports=[
        'keyboard',
        'pyautogui',
        'pyperclip',
        'qrcode',
        'PIL',
        'mouseinfo',
        'pyscreeze',
        'pygetwindow',
        'pymsgbox',
        'pytweening',
        'pyrect',
        'ccxt',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RiskVolume',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Logo\\Logo.png'],
    contents_directory='internal',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RiskVolume',
)
