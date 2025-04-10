# build.spec

block_cipher = None

# Список дополнительных скрытых импортов (если PyInstaller их не обнаружил автоматически)
hidden_imports = []

# Список исключаемых модулей (для уменьшения размера)
excludes = [
    'tkinter',
    'unittest',
    'email',
    'pydoc',
    'pdb',
    'curses',
    'test',
    'distutils',
]

a = Analysis(
    ['hard_resize.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    upx=True,  # Использовать UPX для сжатия
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ImageResizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Без консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Укажите путь к иконке приложения
)

# Для создания одного исполняемого файла (без папки с зависимостями)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ImageResizer',
    onefile=True,  # Важно: создает один .exe файл
)