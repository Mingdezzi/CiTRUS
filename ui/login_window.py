# File path: ui/login_window.py (No ttkbootstrap - Final version - Indentation Fix 3)

import tkinter as tk
import tkinter.scrolledtext as tkst
from tkinter import messagebox
import importlib.util
import traceback # For debugging
import os # Added for image path

try: from PIL import Image, ImageTk; PIL_AVAILABLE = True
except ImportError: PIL_AVAILABLE = False; print("WARNING: Pillow not found.")

# [ ★★★★★ NEW: 테마 임포트 ★★★★★ ]
from ui.theme import Colors

from ui.dialogs import SignupDialog
from services.auth_service import create_user, check_user_login

class LoginWindow(tk.Toplevel):
    BG_IMAGE_FILENAME = "login_background.png"; BG_WIDTH = 900; BG_HEIGHT = 500

    def __init__(self, parent, check_func, install_func, launch_func):
        print("[DEBUG] LoginWindow __init__ started.")
        try: super().__init__(parent)
        except Exception as e: print(f"[ERROR] super().__init__ failed: {e}"); traceback.print_exc(); parent.destroy(); return
        self.parent = parent; self.check_dependencies = check_func; self.install_package = install_func; self.launch_main_app = launch_func
        self.dnd_available = False; self._bg_image_ref = None; self._image_refs = {}
        self.title("CiTRUS Login"); self.resizable(False, False); self.overrideredirect(True)
        self.magic_color = '#abcdef'; self.config(bg=self.magic_color, bd=0, highlightthickness=0)
        try: self.update_idletasks(); self.wm_attributes("-transparentcolor", self.magic_color); print(f"[DEBUG] Applied transparentcolor: {self.magic_color}")
        except tk.TclError as e: print(f"WARNING: -transparentcolor failed: {e}")
        self.bg_width, self.bg_height = self._get_image_size(self.BG_IMAGE_FILENAME) or (900, 500)
        try:
            print("[DEBUG] Creating Canvas container...")
            self.canvas = tk.Canvas(self, width=self.bg_width, height=self.bg_height, bg=self.magic_color, bd=0, highlightthickness=0)
            self.canvas.pack(fill="both", expand=True); self._load_background_image(self.BG_IMAGE_FILENAME)
            self.form_frame = tk.Frame(self.canvas, width=450, height=300)
            self.form_frame.config(bg=Colors.WHITE, bd=0, relief='flat') # Use Colors.WHITE
            self.form_frame.grid_propagate(False); self.form_frame.columnconfigure(0, weight=1); self.form_frame.rowconfigure(1, weight=1)
            self._create_input_fields(self.form_frame) # row=0
            self.console_output = tkst.ScrolledText(self.form_frame, height=5, wrap=tk.WORD, state="disabled", bg=Colors.WHITE, fg=Colors.GREY) # Use Colors
            self.console_output.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="nsew")
            install_btn_frame = tk.Frame(self.form_frame, bg=self.form_frame.cget('bg')); install_btn_frame.grid(row=2, column=0, columnspan=2, pady=(5, 5))
            self.install_button = tk.Button(install_btn_frame, text="Install Add-ons", command=self._install_optional_packages, width=15, relief="flat", bg=Colors.GREY, fg=Colors.WHITE, activebackground=Colors.DARK_GREY) # Use Colors
            self.install_button.pack()
            self._create_action_buttons(self.form_frame) # row=3
            self.form_frame.update_idletasks()
            form_w, form_h = self.form_frame.winfo_reqwidth(), self.form_frame.winfo_reqheight(); print(f"[DEBUG] Form requested size: {form_w}x{form_h}")
            form_anchor_x = int(self.bg_width * 0.47); form_anchor_y = int(self.bg_height * 0.66 - form_h / 2)
            self.canvas.create_window(form_anchor_x, form_anchor_y, window=self.form_frame, anchor="nw"); print(f"[DEBUG] Form placed at ({form_anchor_x}, {form_anchor_y}) anchor=nw")
            self._create_custom_title_bar()
            print("[DEBUG] UI elements OK.")
            self.bind("<Return>", lambda event: self.attempt_login() if self.login_button['state'] == 'normal' else None); self.bind_all("<Alt-F4>", lambda event: self.on_close()); print("[DEBUG] Events bound.")
            self.withdraw(); self.update_idletasks(); self.center_window(); self.deiconify(); print("[DEBUG] Window positioned/deiconified.")
            self.username_entry.focus_set(); print("[DEBUG] Focus set.")
            self.after(100, self.run_dependency_checks_safe); print("[DEBUG] LoginWindow __init__ finished.")
        except Exception as init_error:
            print(f"[ERROR] UI Init: {init_error}"); traceback.print_exc()
            try: messagebox.showerror("UI Error", f"Error during UI creation:\n{init_error}", parent=parent)
            except: pass
            try: parent.destroy()
            except: pass

    # --- UI creation helper functions ---
    def _get_image_size(self, filename):
        if not PIL_AVAILABLE: return None, None
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base, filename)
            if os.path.exists(path):
                with Image.open(path) as img:
                    print(f"DEBUG: Found image {filename}, size={img.size}")
                    return img.size
            else:
                print(f"WARN: Image file not found at {path}")
                return None, None
        except Exception as e:
            print(f"ERROR getting image size: {e}")
            return None, None

    def _load_background_image(self, filename):
        if PIL_AVAILABLE:
            try: # [ ★★★★★ Corrected Try Block Start ★★★★★ ]
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                path = os.path.join(base, filename)
                print(f"[DEBUG] Loading BG: {path}")
                if os.path.exists(path):
                    img = Image.open(path)
                    if img.size != (self.bg_width, self.bg_height):
                        print(f"WARN: BG size mismatch. Resizing.")
                        img = img.resize((self.bg_width, self.bg_height), Image.Resampling.LANCZOS)
                    if img.mode != 'RGBA':
                        print("WARNING: Converting BG to RGBA.")
                        img = img.convert('RGBA')
                    self._bg_image_ref = ImageTk.PhotoImage(img)
                    self.canvas.create_image(0, 0, image=self._bg_image_ref, anchor="nw")
                    print("[DEBUG] BG placed.")
                else:
                    print(f"WARN: BG not found: {path}")
                    self.canvas.create_text(self.bg_width/2, self.bg_height/2, text="BG not found", anchor="center")
            # [ ★★★★★ Corrected Except Block Indentation ★★★★★ ]
            except Exception as e:
                print(f"ERROR loading BG: {e}")
                traceback.print_exc()
                self.canvas.create_text(self.bg_width/2, self.bg_height/2, text="BG Load Error", anchor="center")
        else:
            self.canvas.create_text(self.bg_width/2, self.bg_height/2, text="Pillow required", anchor="center")
    # [ ★★★★★ Corrected Try/Except End ★★★★★ ]


    def _create_input_fields(self, parent):
        frame = tk.Frame(parent, bg=parent.cget('bg')); frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5)); frame.columnconfigure(1, weight=1)
        tk.Label(frame, text="Username :", width=10, bg=parent.cget('bg'), fg=Colors.DARK_TEAL).grid(row=0, column=0, padx=5, pady=5, sticky="w") # Use Colors.DARK_TEAL
        self.username_entry = tk.Entry(frame); self.username_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        tk.Label(frame, text="Password :", width=10, bg=parent.cget('bg'), fg=Colors.DARK_TEAL).grid(row=1, column=0, padx=5, pady=5, sticky="w") # Use Colors.DARK_TEAL
        self.password_entry = tk.Entry(frame, show="*"); self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    def _create_action_buttons(self, parent):
        frame = tk.Frame(parent, bg=parent.cget('bg')); frame.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="ew"); frame.columnconfigure((0, 1), weight=1)
        self.login_button = tk.Button(frame, text="Login", command=self.attempt_login, state="disabled", width=12, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief="flat", activebackground=Colors.DARKER_RED, activeforeground=Colors.WHITE) # Use Colors
        self.login_button.grid(row=0, column=0, sticky="e", padx=5)
        self.signup_button = tk.Button(frame, text="Sign Up", command=self._open_signup_window, width=12, bg=Colors.WHITE, fg=Colors.MAIN_RED, relief="solid", bd=1, highlightthickness=0, activebackground="#f0f0f0") # Use Colors
        self.signup_button.grid(row=0, column=1, sticky="w", padx=5)

    def _create_custom_title_bar(self):
        button_bar = tk.Frame(self.canvas, bg=self.magic_color)
        close_btn = tk.Button(button_bar, text="✕", width=3, command=self.on_close, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief="flat", activebackground=Colors.DARKER_RED) # Use Colors
        close_btn.pack(side="right", padx=(2, 5), pady=5)
        min_btn = tk.Button(button_bar, text="＿", width=3, command=self._minimize_window, bg=Colors.GREY, fg=Colors.WHITE, relief="flat", activebackground=Colors.DARK_GREY) # Use Colors
        min_btn.pack(side="right", pady=5)
        self.canvas.create_window(self.bg_width, 0, window=button_bar, anchor="ne")
    # --- End of UI creation helper functions ---

    # --- Functional methods (유지) ---
    def _minimize_window(self): self.iconify()
    def run_dependency_checks_safe(self):
        print("[DEBUG] Starting dep check...")
        try: self.run_dependency_checks()
        except Exception as e: print(f"[ERROR] Dep check: {e}"); traceback.print_exc(); self.log_to_console(f"Error checking libraries: {e}"); messagebox.showerror("Error", f"Library check error:\n{e}", parent=self)
        print("[DEBUG] Dep check finished.")
    def log_to_console(self, msg):
        try: print(f"[LOG] {msg}"); self.console_output.config(state="normal"); self.console_output.insert(tk.END, msg+"\n"); self.console_output.see(tk.END); self.console_output.config(state="disabled"); self.update_idletasks()
        except Exception as e: print(f"[ERROR] log: {e}")
    def center_window(self):
        try: self.update_idletasks(); w, h = self.bg_width, self.bg_height; sw, sh = self.winfo_screenwidth(), self.winfo_screenheight(); x, y = (sw-w)//2, (sh-h)//2; print(f"[DEBUG] center: {w}x{h}+{x}+{y}"); self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception as e: print(f"[ERROR] center: {e}"); traceback.print_exc()
    def _install_optional_packages(self):
        print("[DEBUG] Install optional..."); self.log_to_console("Checking add-ons..."); self.install_button.config(state="disabled", text="Checking..."); self.update_idletasks()
        missing = [pkg for pkg in ["tkinterdnd2", "rembg"] if importlib.util.find_spec(pkg) is None]
        if not missing: self.log_to_console("All add-ons installed."); messagebox.showinfo("Info", "All add-ons installed.", parent=self)
        else:
            self.log_to_console(f"Installing: {', '.join(missing)}"); self.install_button.config(text="Installing..."); self.update_idletasks()
            all_ok = all(self._install_single_optional(pkg) for pkg in missing); msg = "Add-on install complete." if all_ok else "Some failed."
            func = messagebox.showinfo if all_ok else messagebox.showwarning; self.log_to_console(msg); func("Install Result", msg, parent=self)
        self.install_button.config(state="normal", text="Install Add-ons")
    def _install_single_optional(self, pkg):
        self.log_to_console(f"Installing '{pkg}'..."); ok = self.install_package(pkg, self.log_to_console); self.log_to_console(f"'{pkg}' install {'OK' if ok else 'failed'}.")
        if ok and pkg == "tkinterdnd2": self.log_to_console("Restart required for Drag & Drop.")
        return ok
    def run_dependency_checks(self):
        print("[DEBUG] run dep checks (req)..."); self.log_to_console("Checking libraries...")
        results = self.check_dependencies(self.log_to_console); missing = results['missing_required']
        if missing:
            if messagebox.askyesno("Libs Missing", f"Missing:\n{', '.join(missing)}\nInstall now?", parent=self):
                if not all(self.install_package(p, self.log_to_console) for p in missing): messagebox.showerror("Error", "Failed to install required libs.", parent=self); self.destroy(); return
                if self.check_dependencies(self.log_to_console)['missing_required']: messagebox.showerror("Error", "Libs not recognized after install.", parent=self); self.destroy(); return
            else: messagebox.showerror("Cannot Run", "Cannot run without required libs.", parent=self); self.destroy(); return
        print("[DEBUG] Required OK."); self.log_to_console("Libs ready. Please log in."); self.login_button.config(state="normal")
        try: self.grab_set(); self.lift(); self.focus_force(); print("[DEBUG] Grab/lift/focus OK.")
        except tk.TclError as e: print(f"[WARN] Grab/lift/focus failed: {e}")
        print("[DEBUG] run dep checks finished.")
    def _open_signup_window(self):
        print("[DEBUG] Opening signup..."); self.update_idletasks(); login_geo = self.winfo_geometry(); parts = login_geo.split('+'); size_parts = parts[0].split('x')
        login_w = int(size_parts[0]); login_x = int(parts[1]); login_y = int(parts[2]); signup_x = login_x + login_w + 10
        dialog = SignupDialog(self, x=signup_x, y=login_y)
        if hasattr(dialog, 'result') and dialog.result:
            name, username, email, password = dialog.result['name'], dialog.result['username'], dialog.result['email'], dialog.result['password']
            print(f"[DEBUG] Signup data: {name}, ID:{username}, Email:{email}"); self.log_to_console(f"Signing up: {name}({username})")
            result = create_user(name, username, email, password)
            if result is True: messagebox.showinfo("Signup OK", f"Welcome, {name}!\nPending admin approval.", parent=self); self.log_to_console("Signup request sent.")
            else: err_map = {"duplicate_email": "Email exists.", "duplicate_username": "Username taken.", "invalid_email": "Invalid email.", "password_too_short": "Password min 6 chars."}; err_msg = err_map.get(result, f"Server Error: {result}" if isinstance(result, str) else "Unknown error."); messagebox.showerror("Signup Failed", err_msg, parent=self); self.log_to_console(f"Signup failed: {err_msg}")
        else: print("[DEBUG] Signup cancelled.")
    def attempt_login(self):
        print("[DEBUG] attempt_login..."); username, password = self.username_entry.get(), self.password_entry.get()
        if not (username and password): messagebox.showwarning("Login", "Enter username and password.", parent=self); return
        print(f"Login attempt: ID='{username}'"); self.log_to_console(f"Logging in {username}..."); self.update_idletasks()
        role_num = check_user_login(username, password); BANNED, PENDING, REGISTERED, PREMIUM, ADMIN = 0, 1, 2, 3, 4
        if role_num is not None:
            print(f"Login OK! Role: {role_num}"); allowed = [REGISTERED, PREMIUM, ADMIN]
            if role_num in allowed:
                role_map = {2:"reg", 3:"prem", 4:"admin"}; self.log_to_console(f"Login OK ({role_map.get(role_num, '?')})! Starting..."); self.update_idletasks()
                self.dnd_available = "tkinterdnd2" in str(type(self.parent)); print(f"INFO: DND: {self.dnd_available}")
                self.launch_main_app(self.parent)
                try: self.destroy()
                except Exception as e: print(f"[ERROR] Closing login win: {e}")
            elif role_num == PENDING: self.log_to_console("Login failed: Pending approval."); messagebox.showinfo("Login Failed", "Account awaiting approval.", parent=self)
            elif role_num == BANNED: self.log_to_console("Login failed: Banned."); messagebox.showerror("Login Failed", "Access denied.", parent=self)
            else: self.log_to_console(f"Login failed: Unknown role ({role_num})."); messagebox.showerror("Login Error", f"Unknown role ({role_num}).", parent=self)
        else: self.log_to_console("Login failed: Invalid credentials."); messagebox.showerror("Login Failed", "Invalid username or password.", parent=self)
        print("[DEBUG] attempt_login finished.")
    def on_close(self):
        print("Login closed. Exiting.");
        try: self.parent.destroy() if self.parent and self.parent.winfo_exists() else self.destroy()
        except Exception as e: print(f"[ERROR] on_close: {e}")