# File path: main.py (Final modified version - No ttkbootstrap)

import sys
import os
import subprocess
import importlib.util
from tkinter import messagebox
# [MODIFIED] ttkbootstrap import 제거
# import ttkbootstrap as ttk
# from ttkbootstrap.constants import *
import tkinter as tk
import tkinter.ttk as ttk # [NEW] 표준 ttk 모듈 사용 (Notebook 등)
import traceback

# [ ★★★★★ NEW: 테마 임포트 ★★★★★ ]
from ui.theme import Colors

# --- Add project root and services path (유지) ---
application_path = os.path.dirname(os.path.abspath(__file__))
if application_path not in sys.path:
    sys.path.insert(0, application_path)
    print(f"DEBUG: Added to sys.path: {application_path}")
else:
    print(f"DEBUG: Already in sys.path: {application_path}")
services_path = os.path.join(application_path, "services")
if os.path.isdir(services_path) and services_path not in sys.path:
    sys.path.insert(0, services_path)
    print(f"DEBUG: Added to sys.path (services): {services_path}")
print(f"DEBUG: Current sys.path: {sys.path}")
# --- End of path addition ---

# --- Debugging code (유지) ---
try:
    import services.auth_service
    print("DEBUG: Direct import of services.auth_service successful!")
except ImportError as e:
    print(f"DEBUG: Direct import of services.auth_service failed: {e}")
    print(f"DEBUG: sys.path at the time of import failure: {sys.path}")
# --- End of debugging code ---

# --- Existing auth_service import and initialization (유지) ---
try:
    from services.auth_service import initialize_database
    initialize_database()
except ImportError:
    print("Warning: Could not find services/auth_service.py.")
except Exception as e:
    print(f"Error during DB initialization: {e}")
# --- End of initialization ---

# --- Library installation function (유지) ---
def install_package(package_name, output_func=print):
    """Installs a package using pip and prints the result to output_func."""
    try:
        output_func(f"Attempting to install '{package_name}'...")
        result = subprocess.check_output(
            [sys.executable, "-m", "pip", "install", package_name],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
        output_func(f"Successfully installed '{package_name}'!\n{result}")
        return True
    except subprocess.CalledProcessError as e:
        output_func(f"Failed to install '{package_name}':\n{e.output}")
        messagebox.showerror("Installation Error", f"Error while installing '{package_name}' library...\n\n{e.output}\n\n...")
        return False
    except Exception as e:
        output_func(f"An unexpected error occurred during installation of '{package_name}': {e}")
        messagebox.showerror("Installation Error", f"An unexpected error occurred while installing '{package_name}' library...\n\n{e}\n\n...")
        return False

# --- Dependency check function (유지) ---
def check_dependencies(output_func=print):
    """Checks for required libraries and returns the results as a dictionary."""
    # [MODIFIED] ttkbootstrap 제거
    required = {"PIL": "Pillow", "supabase": "supabase-py"}
    optional = {"tkinterdnd2": "tkinterdnd2", "rembg": "rembg"}
    missing_required = []
    missing_optional = []
    dnd_spec = None

    output_func("--- Starting library check ---")
    for import_name, install_name in required.items():
        output_func(f"Checking '{install_name}'...")
        spec = importlib.util.find_spec(import_name)
        if spec is None:
            output_func(f"-> '{install_name}' library is not installed.")
            missing_required.append(install_name)
        else:
            output_func(f"-> '{install_name}' check complete.")

    for import_name, install_name in optional.items():
        output_func(f"Checking '{install_name}'...")
        spec = importlib.util.find_spec(import_name)
        if spec is None:
            output_func(f"-> '{install_name}' library is not installed.")
            missing_optional.append(install_name)
        else:
            output_func(f"-> '{install_name}' check complete.")
            if import_name == "tkinterdnd2":
                dnd_spec = spec

    output_func("--- Library check finished ---")
    return {'missing_required': missing_required, 'missing_optional': missing_optional, 'dnd_spec': dnd_spec}

# --- Main app execution function ---
def launch_main_app(root_window):
    """Sets up and runs the main application window."""
    print("[DEBUG] Launching main application window...")

    # --- [ ★★★★★ 표준 ttk 스타일 커스터마이징 (Notebook용) ★★★★★ ] ---
    print("[DEBUG] Applying custom colors using tkinter.ttk.Style...")
    try:
        # 표준 ttk 스타일 객체 생성
        style = ttk.Style()

        # --- [ ★★★★★ MODIFIED: 테마에서 색상 가져오기 ★★★★★ ] ---
        # Notebook 스타일 설정
        style.theme_use("clam") # 'clam' 테마가 커스터마이징 용이
        style.configure("TNotebook", background=Colors.WHITE, borderwidth=1)
        style.configure("TNotebook.Tab",
                        background=Colors.GREY,          # 비활성 탭 배경
                        foreground=Colors.WHITE,         # 비활성 탭 글씨
                        padding=[10, 5], borderwidth=0,
                        lightcolor=Colors.GREY, focusthickness=0,
                        focuscolor=style.lookup("TNotebook.Tab", "background")) # 포커스 색 = 배경색

        # Notebook 탭 상태별 스타일 설정
        style.map("TNotebook.Tab",
                  background=[("selected", Colors.MAIN_RED), # 선택 시 배경
                              ("!selected", "hover", Colors.DARK_GREY)], # 호버 시 배경
                  foreground=[("selected", Colors.WHITE)],   # 선택 시 글씨
                  lightcolor=[("selected", Colors.MAIN_RED)]) # 선택 시 테두리 색상 강조 (미미함)
        # --- [ ★★★★★ 수정 완료 ★★★★★ ] ---

        # 메인 앱 전체 배경색 설정 (root_window 자체가 tk.Tk 이므로 config 사용)
        root_window.config(bg=Colors.WHITE)
        root_window.style = style # 참고용으로 저장
        print(f"[DEBUG] Custom ttk styles applied.")

    except Exception as e:
        print(f"ERROR: Failed to apply custom ttk styles: {e}")
        traceback.print_exc()
        root_window.style = None
        root_window.config(bg=Colors.WHITE) # 최소한 배경색은 흰색으로
    # --- [ ★★★★★ 수정 완료 ★★★★★ ] ---

    root_window.title("CiTRUS")
    root_window.geometry("1400x900")
    root_window.minsize(1200, 800)

    print("[DEBUG] Importing App class...")
    from app import App # app.py는 tk/ttk 위젯을 사용하도록 수정되어야 함
    print("[DEBUG] Creating App instance...")
    App(root_window) # root_window를 부모로 전달
    print("[DEBUG] App instance created.")

    root_window.deiconify()

# --- Program entry point ---
if __name__ == '__main__':
    root = None
    try:
        print("[DEBUG] Starting __main__ block...")
        print("[DEBUG] Checking dependencies before creating root...")
        dnd_available = False
        try:
            results = check_dependencies(output_func=print)
            if results['dnd_spec']: dnd_available = True
            if results['missing_required']:
                missing_str = ", ".join(results['missing_required'])
                print(f"!!! Missing required libraries: {missing_str}")
                messagebox.showerror("Cannot Run", f"Missing required libraries:\n{missing_str}\n\nPlease install with 'pip install {missing_str}'.")
                sys.exit("Missing required libraries")
        except Exception as e:
            print(f"[WARN] Dependency check failed, proceeding anyway: {e}")

        ROOT_WINDOW_TYPE = tk.Tk
        if dnd_available:
            try:
                 from tkinterdnd2 import TkinterDnD
                 ROOT_WINDOW_TYPE = TkinterDnD.Tk
                 print("INFO: Using TkinterDnD.Tk")
            except ImportError:
                 print("ERROR: Failed to re-import tkinterdnd2. Using standard Tk.")

        print("[DEBUG] Creating *SINGLE* root window...")
        root = ROOT_WINDOW_TYPE()
        root.withdraw() # 로그인 창 먼저 보이도록 숨김

        print("[DEBUG] Importing LoginWindow...")
        from ui.login_window import LoginWindow

        print("[DEBUG] Creating LoginWindow instance...")
        try:
            login_window = LoginWindow(
                parent=root, check_func=check_dependencies,
                install_func=install_package, launch_func=launch_main_app
            )
            print("[DEBUG] LoginWindow instance created successfully.")
        except Exception as login_init_error:
            print(f"[ERROR] Failed to create LoginWindow instance: {login_init_error}")
            traceback.print_exc()
            messagebox.showerror("Initialization Error", f"Login window initialization error:\n{login_init_error}")
            sys.exit("Login window initialization failed")

        print("[DEBUG] Starting mainloop (Login window will show first)...")
        root.mainloop()
        print("[DEBUG] Mainloop finished.")

    except Exception as e:
        print(f"[ERROR] Unexpected error in main: {e}")
        traceback.print_exc()
        try: messagebox.showerror("Fatal Error", f"An error occurred during program execution:\n{e}")
        except tk.TclError: pass
        if root:
            try: root.destroy()
            except: pass
        sys.exit("Program terminated abnormally")
    finally:
        print("[DEBUG] CiTRUS program exiting __main__ block.")