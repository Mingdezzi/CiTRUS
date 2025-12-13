# 파일 경로: ui/dialogs.py (No ttkbootstrap - Final version)

import tkinter as tk
import tkinter.ttk as ttk # [MODIFIED] 표준 ttk 사용
from tkinter import colorchooser, font, messagebox
# [MODIFIED] ttkbootstrap import 제거
# import ttkbootstrap as ttk
# from PIL import Image, ImageDraw # ShapeDialog에서 사용하므로 유지

# [ ★★★★★ NEW: 테마 임포트 ★★★★★ ]
from ui.theme import Colors


class TextPropertiesDialog(tk.Toplevel): # [MODIFIED] tk.Toplevel 상속
    def __init__(self, parent, initial_values=None):
        super().__init__(parent); self.transient(parent); self.title("텍스트 속성"); self.geometry("350x250"); self.result = None
        self.available_fonts = sorted([f for f in font.families() if not f.startswith('@')])
        self.text_var = tk.StringVar(); self.font_var = tk.StringVar(); self.size_var = tk.IntVar(); self.color_var = tk.StringVar()
        if initial_values:
            self.text_var.set(initial_values.get('text', '')); self.font_var.set(initial_values.get('font_family', "맑은 고딕"))
            self.size_var.set(initial_values.get('font_size', 30)); self.color_var.set(initial_values.get('color', Colors.BLACK)) # Use Colors.BLACK
        else:
            self.text_var.set("텍스트를 입력하세요"); self.font_var.set("맑은 고딕" if "맑은 고딕" in self.available_fonts else self.available_fonts[0])
            self.size_var.set(30); self.color_var.set(Colors.BLACK) # Use Colors.BLACK
        main_frame = tk.Frame(self, bg=Colors.WHITE, padx=10, pady=10); main_frame.pack(fill="both", expand=True); main_frame.columnconfigure(1, weight=1) # Use Colors.WHITE
        tk.Label(main_frame, text="내용:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=0, column=0, sticky="w", pady=2) # Use Colors
        tk.Entry(main_frame, textvariable=self.text_var).grid(row=0, column=1, columnspan=2, sticky="ew", pady=2)
        tk.Label(main_frame, text="글꼴:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=1, column=0, sticky="w", pady=2) # Use Colors
        ttk.Combobox(main_frame, textvariable=self.font_var, values=self.available_fonts, state="readonly").grid(row=1, column=1, columnspan=2, sticky="ew", pady=2)
        tk.Label(main_frame, text="크기:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=2, column=0, sticky="w", pady=2) # Use Colors
        tk.Spinbox(main_frame, from_=8, to=200, textvariable=self.size_var, width=10).grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)
        tk.Label(main_frame, text="색상:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=3, column=0, sticky="w", pady=2) # Use Colors
        self.color_preview = tk.Canvas(main_frame, width=24, height=24, bg=self.color_var.get(), highlightthickness=1, highlightbackground=Colors.GREY, bd=0) # Use Colors.GREY
        self.color_preview.grid(row=3, column=1, sticky="w", pady=2)
        tk.Button(main_frame, text="색상 선택", command=self._choose_color, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).grid(row=3, column=2, sticky="ew", padx=(5,0), pady=2) # Use Colors
        btn_frame = tk.Frame(main_frame, bg=Colors.WHITE); btn_frame.grid(row=4, column=0, columnspan=3, pady=(20, 0)) # Use Colors.WHITE
        tk.Button(btn_frame, text="확인", command=self._on_ok, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).pack(side="left", padx=5) # Use Colors
        tk.Button(btn_frame, text="취소", command=self.destroy, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side="left", padx=5) # Use Colors
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.destroy); self.wait_window(self)

    def _choose_color(self): code = colorchooser.askcolor(title="글자 색상 선택", initialcolor=self.color_var.get()); self.color_var.set(code[1]); self.color_preview.config(bg=code[1]) if code[1] else None
    def _on_ok(self): self.result = {"text": self.text_var.get(), "font_family": self.font_var.get(), "font_size": self.size_var.get(), "color": self.color_var.get()}; self.destroy()

class ShapePropertiesDialog(tk.Toplevel): # [MODIFIED] tk.Toplevel 상속
    def __init__(self, parent, initial_values=None):
        super().__init__(parent); self.transient(parent); self.title("도형 속성"); self.result = None
        self.shape_types = ["사각형", "삼각형", "오각형", "육각형", "자유곡선"]; self.shape_var = tk.StringVar(value=self.shape_types[0]); self.color_var = tk.StringVar(value=Colors.MAIN_RED) # Use Colors.MAIN_RED
        self.drawing_canvas = None; self.pil_image = None; self.pil_draw = None; self.last_x, self.last_y = None, None
        if initial_values: self.shape_var.set(initial_values.get('shape_type', self.shape_types[0])); self.color_var.set(initial_values.get('color', Colors.MAIN_RED)) # Use Colors.MAIN_RED
        main_frame = tk.Frame(self, bg=Colors.WHITE, padx=10, pady=10); main_frame.pack(fill="both", expand=True); main_frame.columnconfigure(1, weight=1) # Use Colors.WHITE
        tk.Label(main_frame, text="종류:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=0, column=0, sticky="w", pady=2) # Use Colors
        combo = ttk.Combobox(main_frame, textvariable=self.shape_var, values=self.shape_types, state="readonly"); combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=2); combo.bind("<<ComboboxSelected>>", self._on_shape_select)
        tk.Label(main_frame, text="색상:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=1, column=0, sticky="w", pady=2) # Use Colors
        self.color_preview = tk.Canvas(main_frame, width=24, height=24, bg=self.color_var.get(), highlightthickness=1, highlightbackground=Colors.GREY, bd=0) # Use Colors.GREY
        self.color_preview.grid(row=1, column=1, sticky="w", pady=2)
        tk.Button(main_frame, text="색상 선택", command=self._choose_color, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).grid(row=1, column=2, sticky="ew", padx=(5,0), pady=2) # Use Colors
        self.drawing_frame = tk.Frame(main_frame, bg=Colors.GREY); self.drawing_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10,0)); main_frame.rowconfigure(2, weight=1) # Use Colors.GREY
        btn_frame = tk.Frame(main_frame, bg=Colors.WHITE); btn_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0)) # Use Colors.WHITE
        tk.Button(btn_frame, text="확인", command=self._on_ok, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).pack(side="left", padx=5) # Use Colors
        tk.Button(btn_frame, text="취소", command=self.destroy, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side="left", padx=5) # Use Colors
        self._on_shape_select(); self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.destroy); self.wait_window(self)

    def _on_shape_select(self, event=None):
        if self.drawing_canvas: self.drawing_canvas.destroy()
        if self.shape_var.get() == "자유곡선":
            self.geometry("400x450")
            self.drawing_canvas = tk.Canvas(self.drawing_frame, bg=Colors.WHITE, highlightthickness=0); self.drawing_canvas.pack(fill="both", expand=True, padx=1, pady=1) # Use Colors.WHITE
            self.drawing_canvas.bind("<Button-1>", self._start_drawing); self.drawing_canvas.bind("<B1-Motion>", self._draw); self.drawing_canvas.bind("<ButtonRelease-1>", self._end_drawing)
            from PIL import Image, ImageDraw # 필요 시점에 import
            self.pil_image = Image.new("RGBA", (380, 280), (0, 0, 0, 0)); self.pil_draw = ImageDraw.Draw(self.pil_image)
        else: self.geometry("")
    def _start_drawing(self, event): self.last_x, self.last_y = event.x, event.y
    def _draw(self, event):
        if self.last_x and self.last_y and self.pil_draw:
            self.drawing_canvas.create_line(self.last_x, self.last_y, event.x, event.y, fill=self.color_var.get(), width=3, capstyle=tk.ROUND, smooth=tk.TRUE)
            self.pil_draw.line([self.last_x, self.last_y, event.x, event.y], fill=self.color_var.get(), width=3, joint="curve"); self.last_x, self.last_y = event.x, event.y
    def _end_drawing(self, event): self.last_x, self.last_y = None, None
    def _choose_color(self): code = colorchooser.askcolor(title="도형 색상 선택", initialcolor=self.color_var.get()); self.color_var.set(code[1]); self.color_preview.config(bg=code[1]) if code[1] else None
    def _on_ok(self):
        self.result = {"shape_type": self.shape_var.get(), "color": self.color_var.get()}
        if self.shape_var.get() == "자유곡선" and self.pil_image: bbox = self.pil_image.getbbox(); self.result["pil_image"] = self.pil_image.crop(bbox) if bbox else None
        self.destroy()

class SignupDialog(tk.Toplevel): # [MODIFIED] tk.Toplevel 상속
    def __init__(self, parent, x=None, y=None):
        super().__init__(parent); self.transient(parent); self.title("회원가입"); self.result = None
        self.name_var = tk.StringVar(); self.id_var = tk.StringVar(); self.email_var = tk.StringVar(); self.pass_var = tk.StringVar()
        main_frame = tk.Frame(self, bg=Colors.WHITE, padx=15, pady=15); main_frame.pack(fill="both", expand=True); main_frame.columnconfigure(1, weight=1) # Use Colors.WHITE
        tk.Label(main_frame, text="이름:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=0, column=0, sticky="w", pady=5) # Use Colors
        self.name_entry = tk.Entry(main_frame, textvariable=self.name_var); self.name_entry.grid(row=0, column=1, sticky="ew", pady=5)
        tk.Label(main_frame, text="아이디:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=1, column=0, sticky="w", pady=5) # Use Colors
        self.id_entry = tk.Entry(main_frame, textvariable=self.id_var); self.id_entry.grid(row=1, column=1, sticky="ew", pady=5)
        tk.Label(main_frame, text="이메일:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=2, column=0, sticky="w", pady=5) # Use Colors
        tk.Entry(main_frame, textvariable=self.email_var).grid(row=2, column=1, sticky="ew", pady=5)
        tk.Label(main_frame, text="비밀번호:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).grid(row=3, column=0, sticky="w", pady=5) # Use Colors
        tk.Entry(main_frame, textvariable=self.pass_var, show="*").grid(row=3, column=1, sticky="ew", pady=5)
        btn_frame = tk.Frame(main_frame, bg=Colors.WHITE); btn_frame.grid(row=4, column=0, columnspan=2, pady=(20, 0)); btn_frame.columnconfigure((0, 1), weight=1) # Use Colors.WHITE
        tk.Button(btn_frame, text="회원가입", command=self._on_ok, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).grid(row=0, column=0, sticky="e", padx=5) # Use Colors
        tk.Button(btn_frame, text="취소", command=self.destroy, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).grid(row=0, column=1, sticky="w", padx=5) # Use Colors
        self.update_idletasks(); width = self.winfo_reqwidth(); height = self.winfo_reqheight()
        if x is not None and y is not None: self.geometry(f'{width}x{height}+{x}+{y}')
        else: screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight(); center_x, center_y = (screen_w - width) // 2, (screen_h - height) // 2; self.geometry(f'{width}x{height}+{center_x}+{center_y}')
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.destroy); self.after(50, self.focus_force); self.after(100, self.name_entry.focus_set); self.wait_window(self)

    def _on_ok(self):
        name = self.name_var.get(); user_id = self.id_var.get(); email = self.email_var.get(); password = self.pass_var.get()
        if not (name and user_id and email and password): messagebox.showwarning("입력 오류", "모든 항목 입력.", parent=self); return
        self.result = {"name": name, "username": user_id, "email": email, "password": password}; self.destroy()