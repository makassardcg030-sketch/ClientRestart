import os
import sys
import json
import ctypes
from ctypes import wintypes
import socket
import threading
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui
from PIL import Image, ImageDraw
import pystray

# PyAutoGUI safety pause
pyautogui.PAUSE = 0.2

CONFIG_CLIENT_FILE = "config_client.json"

DEFAULT_CLIENT_CONFIG = {
    "TARGET_APP_PATH": r"D:\release_induk\PGDCNEWPicking.exe",
    "TARGET_EXE_NAME": "PGDCNEWPicking.exe"
}

# Win32 shortcuts
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


# ==========================================
# 0. MANAJEMEN KONFIGURASI & GUI SETTINGS
# ==========================================
def load_client_config():
    """Membaca konfigurasi dari config_client.json secara fleksibel."""
    config = DEFAULT_CLIENT_CONFIG.copy()
    if os.path.exists(CONFIG_CLIENT_FILE):
        try:
            with open(CONFIG_CLIENT_FILE, "r") as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception as e:
            print(f"⚠️ Gagal membaca {CONFIG_CLIENT_FILE}, menggunakan default: {e}")
    else:
        save_client_config(config)

    if not config.get("TARGET_EXE_NAME"):
        config["TARGET_EXE_NAME"] = os.path.basename(
            config.get("TARGET_APP_PATH", "PGDCNEWPicking.exe")
        )
    return config


def save_client_config(config):
    """Menyimpan konfigurasi baru ke config_client.json."""
    try:
        with open(CONFIG_CLIENT_FILE, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"⚠️ Gagal menyimpan file konfigurasi JSON: {e}")
        return False


def buka_gui_settings():
    """Menampilkan jendela GUI untuk memilih file EXE aplikasi secara visual."""
    def browse_file():
        file_path = filedialog.askopenfilename(
            title="Pilih File Executable Target",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if file_path:
            entry_path.delete(0, tk.END)
            entry_path.insert(0, file_path)

    def simpan():
        path = entry_path.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "File .exe tidak ditemukan atau path kosong!")
            return

        exe_name = os.path.basename(path)
        new_config = {
            "TARGET_APP_PATH": path,
            "TARGET_EXE_NAME": exe_name
        }
        if save_client_config(new_config):
            messagebox.showinfo("Sukses", f"Pengaturan tersimpan!\nEXE: {exe_name}")
            root.destroy()
        else:
            messagebox.showerror("Error", "Gagal menyimpan file konfigurasi JSON.")

    root = tk.Tk()
    root.title("Pengaturan Aplikasi Client")
    root.geometry("480x160")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    config = load_client_config()

    tk.Label(root, text="Path File Executable (.exe):",
             font=("Arial", 9, "bold")).pack(anchor="w", padx=15, pady=(15, 5))

    frame_input = tk.Frame(root)
    frame_input.pack(fill="x", padx=15)

    entry_path = tk.Entry(frame_input, font=("Arial", 9))
    entry_path.insert(0, config.get("TARGET_APP_PATH", ""))
    entry_path.pack(side="left", fill="x", expand=True, padx=(0, 5))

    btn_browse = tk.Button(frame_input, text="Browse...", command=browse_file)
    btn_browse.pack(side="right")

    btn_save = tk.Button(root, text="Simpan Pengaturan", bg="#28a745", fg="white",
                         font=("Arial", 9, "bold"), command=simpan)
    btn_save.pack(pady=15)

    root.mainloop()


# Koordinat Akhir
KOORDINAT_OPEN = (350, 95)

import struct

def ensure_vcredist():
    try:
        ctypes.CDLL("vcruntime140.dll")
    except OSError:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # Deteksi apakah Python berjalan di arsitektur 32-bit atau 64-bit
        is_64bits = struct.calcsize("P") * 8 == 64
        vcredist_name = "VC_redist.x64.exe" if is_64bits else "VC_redist.x86.exe"
        vcredist_path = os.path.join(base_dir, vcredist_name)

        if os.path.exists(vcredist_path):
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", vcredist_path, "/passive /norestart", None, 1
            )
            sys.exit(0)


ensure_vcredist()


# ==========================================
# 1b. WIN32 HELPERS
# ==========================================
def _find_pid_by_name(exe_name):
    """Ambil PID berdasarkan nama exe via tasklist."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True
        )
        for line in out.splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2 and parts[0].lower() == exe_name.lower():
                try:
                    return int(parts[1])
                except ValueError:
                    continue
    except Exception:
        pass
    return None


# ==========================================
# 2. LOGIKA UTAMA
# ==========================================
def eksekusi_restart_dan_makro():
    config = load_client_config()
    app_path = config["TARGET_APP_PATH"]
    exe_name = config["TARGET_EXE_NAME"]

    # 1. Taskkill & tunggu proses hilang
    print(f"Menghentikan proses {exe_name}...")
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", exe_name, "/T"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10
        )
    except Exception as e:
        print(f"⚠️ Warning Taskkill: {e}")

    for _ in range(10):
        if _find_pid_by_name(exe_name) is None:
            break
        time.sleep(0.5)
    print("Proses target sudah berhenti.")

    # 2. Reopen
    if not os.path.exists(app_path):
        print(f"❌ Error: Path '{app_path}' tidak ditemukan!")
        return
    print(f"Membuka kembali {app_path}...")
    os.startfile(app_path)

    # 3. Tunggu beberapa detik agar aplikasi terbuka sempurna di layar
    print("Menunggu aplikasi siap (4 detik)...")
    time.sleep(4.0)

    # 4. Alur input login langsung ke koordinat (722, 345)
    print("Memulai alur input login ke koordinat (722, 345)...")
    
    pyautogui.moveTo(722, 345, duration=0.5)
    pyautogui.click(clicks=2, interval=0.1)
    time.sleep(1.0) 
    
    print("Mengetik username...")
    pyautogui.write('dpd', interval=0.05)
    time.sleep(0.5)
    
    pyautogui.press('tab')
    time.sleep(0.6)
    
    print("Mengetik password...")
    pyautogui.write('dpd', interval=0.05)
    time.sleep(0.5)
    
    pyautogui.press('enter')
    time.sleep(0.7)
    pyautogui.press('enter')
    time.sleep(2.0)

    # 5. Tunggu proses login masuk ke menu utama
    print("Menunggu proses login selesai...")
    time.sleep(3.0)

    # 6. ALT + P > D
    print("Membuka menu picking (Alt+P > D)...")
    pyautogui.hotkey('alt', 'p')
    time.sleep(0.5)
    pyautogui.press('d')
    time.sleep(0.5)

    # 7. Klik di koordinat akhir
    pyautogui.click(KOORDINAT_OPEN[0], KOORDINAT_OPEN[1])

    print("✅ Restart dan makro sukses dieksekusi!")


# ==========================================
# 3. SERVER SOCKET LISTENER (BACKGROUND)
# ==========================================
is_running = True
macro_lock = threading.Lock()  # Pengaman agar hanya 1 makro berjalan dalam satu waktu


def jalankan_tugas_aman(fungsi_target):
    """Menjalankan makro dan otomatis melepas kunci setelah selesai atau terjadi error."""
    try:
        fungsi_target()
    except Exception as e:
        print(f"Error saat mengeksekusi makro: {e}")
    finally:
        macro_lock.release()
        print("🔓 Kunci dilepas. Siap menerima perintah baru.")


def start_client():
    global is_running
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 5005))
    server_socket.listen(5)
    server_socket.settimeout(1.0)

    print("Client siap menerima perintah di port 5005...")

    while is_running:
        try:
            conn, addr = server_socket.accept()
            data = conn.recv(1024).decode('utf-8').strip()

            if data in ["RESTART_PROGRAM", "RUN_MACRO"] or data.startswith("RESTART_DCP_"):
                # Tolak request jika kunci sedang dipegang oleh proses lain
                if not macro_lock.acquire(blocking=False):
                    print(f"⚠️ Menolak request '{data}' dari {addr[0]}: Makro sedang berjalan!")
                    conn.send("BUSY".encode('utf-8'))
                    conn.close()
                    continue

                print(f"🔒 Kunci diambil oleh {addr[0]} untuk perintah '{data}'.")
                conn.send("OK".encode('utf-8'))
                time.sleep(0.1)
                conn.close()
                threading.Thread(
                    target=jalankan_tugas_aman,
                    args=(eksekusi_restart_dan_makro,),
                    daemon=True
                ).start()
            else:
                conn.send("UNKNOWN_COMMAND".encode('utf-8'))
                conn.close()

        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error socket: {e}")

    server_socket.close()
    print("Server socket berhenti.")


# ==========================================
# 4. SYSTEM TRAY ICON (PYSTRAY)
# ==========================================
def create_dummy_icon():
    image = Image.new('RGB', (64, 64), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=(40, 167, 69))
    return image


def stop_application(icon, item):
    global is_running
    is_running = False
    icon.stop()
    print("Aplikasi dihentikan oleh pengguna.")


def setup_tray():
    icon_image = create_dummy_icon()

    menu = pystray.Menu(
        pystray.MenuItem("Client Listener (Running Port 5005)", None, enabled=False),
        pystray.MenuItem(
            "Pengaturan Aplikasi...",
            lambda: threading.Thread(target=buka_gui_settings, daemon=True).start()
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", stop_application)
    )

    icon = pystray.Icon("ClientBot", icon_image, "Bot Client RestartDCP", menu)

    server_thread = threading.Thread(target=start_client, daemon=True)
    server_thread.start()

    icon.run()


if __name__ == "__main__":
    setup_tray()