# -*- mode: python ; coding: utf-8 -*-

# Configuration Wizard

configure_a = Analysis(
    ['configure.py'],
    pathex=[],
    binaries=[],
    datas=[('res', 'res'), ('config.yaml', '.'), ('external', 'external')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
configure_pyz = PYZ(configure_a.pure)

configure_exe = EXE(
    configure_pyz,
    configure_a.scripts,
    [],
    exclude_binaries=True,
    name='configure',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['res\\icons\\monitor-icon-17865\\icon.ico'],
    contents_directory='.',
    version='tools\\windows-installer\\pyinstaller-version-info.txt',
)

# System Monitor main program

main_a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('res', 'res'), ('config.yaml', '.'), ('external', 'external')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
main_pyz = PYZ(main_a.pure)

main_exe = EXE(
    main_pyz,
    main_a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['res\\icons\\monitor-icon-17865\\icon.ico'],
    contents_directory='.',
    version='tools\\windows-installer\\pyinstaller-version-info.txt',
)

# Theme Editor

editor_a = Analysis(
    ['theme-editor.py'],
    pathex=[],
    binaries=[],
    datas=[('res', 'res'), ('config.yaml', '.'), ('external', 'external')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
editor_pyz = PYZ(editor_a.pure)

editor_exe = EXE(
    editor_pyz,
    editor_a.scripts,
    [],
    exclude_binaries=True,
    name='theme-editor',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['res\\icons\\monitor-icon-17865\\icon.ico'],
    contents_directory='.',
    version='tools\\windows-installer\\pyinstaller-version-info.txt',
)

# Common collect task

coll = COLLECT(
    configure_exe,
    configure_a.binaries,
    configure_a.datas,
    main_exe,
    main_a.binaries,
    main_a.datas,
    editor_exe,
    editor_a.binaries,
    editor_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='turing-system-monitor',
)
