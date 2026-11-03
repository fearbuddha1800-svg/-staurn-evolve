# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/voidk/.hermes/workspace/signal-relay/relay_main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/voidk/.hermes/workspace/signal-relay/config.json', '.'), ('C:/Users/voidk/.hermes/workspace/signal-relay/signals.db', '.')],
    hiddenimports=['MetaTrader5', 'telethon', 'notify', 'parser', 'broker_lifecycle', 'event_bus', 'loss_halt', 'stop_legality', 'manager_connection'],
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
    a.binaries,
    a.datas,
    [],
    name='signal_relay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
