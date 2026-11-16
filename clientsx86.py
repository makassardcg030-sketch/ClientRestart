import os
import sys
import json
import ctypes
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
        config["TARGET_EXE_NAME"] = os.path.basename(config.get("TARGET_APP_PATH", "PGDCNEWPicking.exe"))
        
    return config

def save_client_config(config):
    """Menyimpan konfigurasi baru ke config_client.json."""
    try:
        with open(CONFIG_CLIENT_FILE, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"⚠️ Gagal menyimpan file konfigurasi: {e}")
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
    root.geometry("480x150")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    config = load_client_config()

    tk.Label(root, text="Path File Executable (.exe):", font=("Arial", 9, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
    
    frame_input = tk.Frame(root)
    frame_input.pack(fill="x", padx=15)

    entry_path = tk.Entry(frame_input, font=("Arial", 9))
    entry_path.insert(0, config.get("TARGET_APP_PATH", ""))
    entry_path.pack(side="left", fill="x", expand=True, padx=(0, 5))

    btn_browse = tk.Button(frame_input, text="Browse...", command=browse_file)
    btn_browse.pack(side="right")

    btn_save = tk.Button(root, text="Simpan Pengaturan", bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=simpan)
    btn_save.pack(pady=15)

    root.mainloop()

# Koordinat Makro
KOORDINAT_MERAH = (416, 67)  # X, Y untuk Klik 1 (Makro Awal)
KOORDINAT_BIRU = (254, 65)  # X, Y untuk Klik 2


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
# 2. LOGIKA 1: MAKRO AWAL (TANPA RESTART)
# ==========================================
def eksekusi_makro_biasa():
    """Menjalankan fungsi makro awal yang persis seperti sebelumnya."""
    print("Mengeksekusi makro biasa (tanpa restart)...")
    
    for _ in range(3):
        pyautogui.click(KOORDINAT_MERAH[0], KOORDINAT_MERAH[1])
        time.sleep(0.2)
        
    time.sleep(0.5)
    
    pyautogui.hotkey('alt', 'p')
    time.sleep(0.3)
    pyautogui.press('p')
    
    time.sleep(0.5)
    
    for _ in range(2):
        pyautogui.click(KOORDINAT_BIRU[0], KOORDINAT_BIRU[1])
        time.sleep(0.2)
        
    print("✅ Makro biasa selesai!")
    return True


# ==========================================
# 3. LOGIKA 2: RESTART (TASKKILL & REOPEN)
# ==========================================
def eksekusi_restart_dan_makro():
    config = load_client_config()
    app_path = config["TARGET_APP_PATH"]
    exe_name = config["TARGET_EXE_NAME"]
    
    print(f"Menghentikan proses {exe_name}...")
    
    try:
        subprocess.run(["taskkill", "/F", "/IM", exe_name, "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.system(f'taskkill /F /IM "{exe_name}" /T >nul 2>&1')
    except Exception as e:
        print(f"⚠️ Warning Taskkill: {e}")
        
    time.sleep(2)
    
    print(f"Membuka kembali {app_path}...")
    if os.path.exists(app_path):
        os.startfile(app_path)
    else:
        print(f"❌ Error: Path '{app_path}' tidak ditemukan!")
        return
            
    print("Menunggu aplikasi siap...")
    time.sleep(5)

    pyautogui.click(KOORDINAT_MERAH[0], KOORDINAT_MERAH[1])
    time.sleep(0.5)

    print("Memulai input login & navigasi...")

    pyautogui.write('dpd', interval=0.1)
    pyautogui.press('tab')
    pyautogui.write('dpd', interval=0.1)
    pyautogui.press('enter')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(1.0)
    
    pyautogui.hotkey('alt', 'p')
    time.sleep(0.5)
    pyautogui.press('p')
    time.sleep(0.8)
    
    for _ in range(2):
        pyautogui.click(KOORDINAT_BIRU[0], KOORDINAT_BIRU[1])
        time.sleep(0.2)
    
    print("✅ Restart dan makro PGDCNewPicking sukses dieksekusi!")


# ==========================================
# 4. SERVER SOCKET LISTENER (BACKGROUND)
# ==========================================
is_running = True
macro_lock = threading.Lock()  # Pengaman atomic lock


def jalankan_tugas(fungsi_target):
    """Fungsi pembungkus untuk memastikan kunci dilepas setelah selesai atau error."""
    try:
        fungsi_target()
    except Exception as e:
        print(f"Error saat mengeksekusi makro: {e}")
    finally:
        macro_lock.release()
        print("🔓 Proses selesai, kunci dilepas. Siap menerima request baru.")


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
            
            if data in ["RUN_MACRO", "RESTART_PROGRAM"]:
                # Tolak request jika sedang ada proses yang berjalan
                if not macro_lock.acquire(blocking=False):
                    print(f"⚠️ Menolak request '{data}' dari {addr[0]}: Makro sedang berjalan!")
                    conn.send("BUSY".encode('utf-8'))
                    conn.close()
                    continue
                
                print(f"🔒 Kunci diambil oleh {addr[0]} untuk perintah '{data}'.")
                conn.send("OK".encode('utf-8'))
                time.sleep(0.1)
                conn.close()
                
                # Eksekusi fungsi menggunakan wrapper
                if data == "RUN_MACRO":
                    threading.Thread(target=jalankan_tugas, args=(eksekusi_makro_biasa,), daemon=True).start()
                elif data == "RESTART_PROGRAM":
                    threading.Thread(target=jalankan_tugas, args=(eksekusi_restart_dan_makro,), daemon=True).start()
                
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
# 5. SYSTEM TRAY ICON (PYSTRAY)
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
        pystray.MenuItem("Pengaturan Aplikasi...", lambda: threading.Thread(target=buka_gui_settings, daemon=True).start()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", stop_application)
    )
    
    icon = pystray.Icon("ClientBot", icon_image, "Bot Client RestartDPD (Aktif)", menu)
    
    server_thread = threading.Thread(target=start_client, daemon=True)
    server_thread.start()
    
    icon.run()

if __name__ == "__main__":
    setup_tray()