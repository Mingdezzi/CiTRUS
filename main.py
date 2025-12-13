import sys
import os
import subprocess
import importlib.util
import tkinter as tk
import tkinter.ttk as ttk
import traceback
from tkinter import messagebox

from ui.theme import Colors

application_path = os.path.dirname(os.path.abspath(__file__))
if application_path not in sys.path:
    sys.path.insert(0, application_path)

services_path = os.path.join(application_path, "services")
if os.path.isdir(services_path) and services_path not in sys.path:
    sys.path.insert(0, services_path)

try:
    from services.auth_service import initialize_database
    initialize_database()
except ImportError:
    pass
except Exception as e:
    print(f"Error during DB initialization: {e}")

def install_package(package_name, output_func=print):
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

def check_dependencies(output_func=print):
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

def launch_main_app(root_window):
    try:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=Colors.WHITE, borderwidth=1)
        style.configure("TNotebook.Tab",
                        background=Colors.GREY,
                        foreground=Colors.WHITE,
                        padding=[10, 5], borderwidth=0,
                        lightcolor=Colors.GREY, focusthickness=0,
                        focuscolor=style.lookup("TNotebook.Tab", "background"))

        style.map("TNotebook.Tab",
                  background=[("selected", Colors.MAIN_RED),
                              ("!selected", "hover", Colors.DARK_GREY)],
                  foreground=[("selected", Colors.WHITE)],
                  lightcolor=[("selected", Colors.MAIN_RED)])

        root_window.config(bg=Colors.WHITE)
        root_window.style = style

    except Exception as e:
        traceback.print_exc()
        root_window.style = None
        root_window.config(bg=Colors.WHITE)

    root_window.title("CiTRUS")
    root_window.geometry("1400x900")
    root_window.minsize(1200, 800)

    from app import App
    App(root_window)

    root_window.deiconify()

if __name__ == '__main__':
    root = None
    try:
        dnd_available = False
        try:
            results = check_dependencies(output_func=print)
            if results['dnd_spec']: dnd_available = True
            if results['missing_required']:
                missing_str = ", ".join(results['missing_required'])
                messagebox.showerror("Cannot Run", f"Missing required libraries:\n{missing_str}\n\nPlease install with 'pip install {missing_str}'.")
                sys.exit("Missing required libraries")
        except Exception as e:
            print(f"[WARN] Dependency check failed, proceeding anyway: {e}")

        ROOT_WINDOW_TYPE = tk.Tk
        if dnd_available:
            try:
                 from tkinterdnd2 import TkinterDnD
                 ROOT_WINDOW_TYPE = TkinterDnD.Tk
            except ImportError:
                 pass

        root = ROOT_WINDOW_TYPE()
        root.withdraw()

        from ui.login_window import LoginWindow

        try:
            login_window = LoginWindow(
                parent=root, check_func=check_dependencies,
                install_func=install_package, launch_func=launch_main_app
            )
        except Exception as login_init_error:
            traceback.print_exc()
            messagebox.showerror("Initialization Error", f"Login window initialization error:\n{login_init_error}")
            sys.exit("Login window initialization failed")

        root.mainloop()

    except Exception as e:
        traceback.print_exc()
        try: messagebox.showerror("Fatal Error", f"An error occurred during program execution:\n{e}")
        except tk.TclError: pass
        if root:
            try: root.destroy()
            except: pass
        sys.exit("Program terminated abnormally")