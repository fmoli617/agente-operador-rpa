# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller installer/app.spec --noconfirm
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), ".."))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=["win32com.client", "win32timezone"],
    hookspath=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OperacaoAssistida",
    debug=False,
    console=False,
    icon=os.path.join(ROOT, "installer", "assets", "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="OperacaoAssistida",
)
