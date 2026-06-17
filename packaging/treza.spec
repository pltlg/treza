# PyInstaller spec for Treza (onedir).
#
# onedir (not onefile) is intentional: the bundled LGPL libraries stay as
# separate files the user can inspect/replace, which keeps us aligned with the
# LGPL "relinking" obligation. Build with:
#
#     pyinstaller packaging/treza.spec --noconfirm
#
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

datas, binaries, hiddenimports = [], [], []

# Pull in submodules + data + native libs for packages PyInstaller's static
# analysis misses (dynamic imports, hidapi native lib, etc.).
for pkg in ("libagent", "trezorlib", "ecdsa", "mnemonic", "bech32"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# trezorlib selects transports dynamically.
hiddenimports += collect_submodules("trezorlib.transport")

# Our own package: ensure lazily-imported GUI/device modules are bundled.
hiddenimports += collect_submodules("treza")

# libagent reads distribution metadata for --version; ship it so that path works.
for dist in ("libagent", "trezor", "trezor_agent"):
    try:
        datas += copy_metadata(dist)
    except Exception:  # noqa: BLE001
        pass

# Windows named-pipe server needs pywin32 modules.
if sys.platform == "win32":
    hiddenimports += [
        "win32file", "win32pipe", "win32api", "win32event", "winerror", "pywintypes",
    ]

entry = os.path.join(SPECPATH, "treza_launcher.py")  # noqa: F821 (SPECPATH is injected)

repo_root = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821

a = Analysis(
    [entry],
    pathex=[repo_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="treza",
    # GUI app ships windowed; set TREZA_CONSOLE=1 for a console debug build.
    console=bool(os.environ.get("TREZA_CONSOLE")),
    disable_windowed_traceback=False,
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    name="treza",
)
