"""
Build dengan cx_Freeze — pengganti PyInstaller.
Jalan di: Windows 7 SP1 (32 & 64-bit) dan Windows 10/11.

WAJIB: build pakai Python 3.8.10, BUKAN Python 3.11+ / 3.14.
Python 3.9+ sudah drop Windows 7. Kalau build pakai Python 3.14,
hasilnya TIDAK akan jalan di Win7 walau build-nya sukses.

Cara pakai lokal (Windows):
    py -3.8 -m venv .venv38
    .venv38\\Scripts\\activate
    pip install -r requirements.txt
    python build.py build_exe

Hasil:
    dist/build_<suffix>/clientDCP_<suffix>.exe  (+ DLL & lib di folder yg sama)
    dist/build_<suffix>/clients_<suffix>.exe

PENTING: jangan pindahkan .exe-nya sendirian — pindahkan 1 folder utuh.
"""

import os
import sys
import shutil

# --- Cek versi Python, gagal cepat kalau bukan 3.8 ---
if sys.version_info[:2] != (3, 8):
    print(f"[build] ERROR: Python {sys.version_info.major}.{sys.version_info.minor} terdeteksi.")
    print("[build] Build untuk Windows 7 HARUS pakai Python 3.8.10.")
    print("[build] Install dari https://www.python.org/downloads/release/python-3.8.10/")
    print("[build] Lalu:  py -3.8 -m venv .venv38  ->  .venv38\\Scripts\\activate")
    sys.exit(1)

from cx_Freeze import setup, Executable

# --- Suffix dari env (diisi workflow) atau default lokal ---
SUFFIX = os.environ.get("BUILD_SUFFIX", "local")
# BUILD_SUFFIX contoh: win7_32bit / win64

# --- File VC++ Redist (wajib ada di repo, di folder redist/) ---
# Kode ensure_vcredist() di clientDCPx86.py & clientsx86.py nyari file ini
# di sebelah .exe. Kalau tidak ada, app tetap jalan di PC yg sudah ada
# VC++ 2015-2022, tapi akan gagal di Windows 7 fresh install.
# Download dari Microsoft, taruh di:
#   redist/VC_redist.x86.exe
#   redist/VC_redist.x64.exe
include_files = []
for fname in ["VC_redist.x86.exe", "VC_redist.x64.exe"]:
    src = os.path.join("redist", fname)
    if os.path.exists(src):
        include_files.append((src, fname))
    else:
        print(f"[build] WARNING: {src} tidak ditemukan, dilewati. "
              f"App bisa gagal di Win7 fresh install tanpa VC++ Redist.")

# --- Opsi build ---
# JANGAN exclude tkinter: dipakai buka_gui_settings() di kedua script.
# JANGAN exclude PIL / pyautogui / pystray: dipakai di runtime.
build_exe_options = {
    "packages": [
        "tkinter",
        "PIL",
        "pyautogui",
        "pystray",
        "pygetwindow",
        "pymsgbox",
        "mouseinfo",
        "pyrect",
        "pyscreeze",
        "pyperclip",
        "pyexpat",
    ],
    "excludes": [
        "pkg_resources",
        "unittest",
        "test",
        "distutils",
        "email",
        "html",
        "http",
        "xmlrpc",
        "pydoc",
    ],
    "include_files": include_files,
    # Zip semua .pyc ke library.zip -> folder lebih rapi, startup sedikit lebih cepat
    "zip_include_packages": "*",
    "zip_exclude_packages": [],
    "optimize": 1,
    # cx_Freeze otomatis bundling vcruntime140.dll (Python 3.8) -> jalan di Win7 & Win10
    # tanpa install Python.
}

# --- Base GUI: nama beda antar versi cx_Freeze ---
# cx_Freeze 6.x (Python 3.8, yg dipakai workflow)  -> "Win32GUI"
# cx_Freeze 7/8 (Python 3.11+, kalau nekat build lokal) -> "gui"
# Deteksi dari versi yg ter-install, biar tidak error:
#   "no base named 'legacy/win32gui'"
try:
    from importlib.metadata import version as _pkg_version
    _cx_ver = _pkg_version("cx-Freeze")
    _major = int(str(_cx_ver).split(".")[0])
except Exception:
    _major = 6
BASE_GUI = "gui" if _major >= 7 else "Win32GUI"
print(f"[build] cx_Freeze {_cx_ver if '_cx_ver' in dir() else '?'} -> base={BASE_GUI!r}")

base = BASE_GUI if sys.platform == "win32" else None

executables = [
    Executable(
        "clientDCPx86.py",
        base=base,
        target_name=f"clientDCP_{SUFFIX}.exe",
    ),
    Executable(
        "clientsx86.py",
        base=base,
        target_name=f"clients_{SUFFIX}.exe",
    ),
]

# Bersihkan dist lama biar tidak kecampur build 32/64-bit
if os.path.exists("dist"):
    shutil.rmtree("dist")

setup(
    name="ClientDCP",
    version="1.0",
    description="Client Listener Restart DCP (Port 5005)",
    options={"build_exe": build_exe_options},
    executables=executables,
)
