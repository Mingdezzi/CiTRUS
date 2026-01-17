# 파일 경로: ui/dialogs.py

import tkinter as tk
from tkinter import colorchooser, font
import ttkbootstrap as ttk
from PIL import Image, ImageDraw

class TextPropertiesDialog(ttk.Toplevel):
    def __init__(self, parent, initial_values=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("텍스트 속성")
        self.geometry("350x250")
        self.result = None

        self.available_fonts = sorted([f for f in font.families() if not f.startswith('@')])

        self.text_var = tk.StringVar()
        self.font_var = tk.StringVar()
        self.size_var = tk.IntVar()
        self.color_var = tk.StringVar()

        if initial_values:
            self.text_var.set(initial_values.get('text', ''))
            self.font_var.set(initial_values.get('font_family', "맑은 고딕"))
            self.size_var.set(initial_values.get('font_size', 30))
            self.color_var.set(initial_values.get('color', '#000000'))
        else:
            self.text_var.set("텍스트를 입력하세요")
            self.font_var.set("맑은 고딕" if "맑은 고딕" in self.available_fonts else self.available_fonts[0])
            self.size_var.set(30)
            self.color_var.set("#000000")

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="내용:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(main_frame, textvariable=self.text_var).grid(row=0, column=1, columnspan=2, sticky="ew", pady=2)
        ttk.Label(main_frame, text="글꼴:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Combobox(main_frame, textvariable=self.font_var, values=self.available_fonts, state="readonly").grid(row=1, column=1, columnspan=2, sticky="ew", pady=2)
        ttk.Label(main_frame, text="크기:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Spinbox(main_frame, from_=8, to=200, textvariable=self.size_var, width=10).grid(row=2, column=1, columnspan=2, sticky="ew", pady=2)
        ttk.Label(main_frame, text="색상:").grid(row=3, column=0, sticky="w", pady=2)
        self.color_preview = tk.Canvas(main_frame, width=24, height=24, bg=self.color_var.get(), highlightthickness=1)
        self.color_preview.grid(row=3, column=1, sticky="w", pady=2)
        ttk.Button(main_frame, text="색상 선택", command=self._choose_color, bootstyle="secondary").grid(row=3, column=2, sticky="ew", padx=(5,0), pady=2)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=(20, 0))
        ttk.Button(btn_frame, text="확인", command=self._on_ok, bootstyle="primary").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="취소", command=self.destroy, bootstyle="secondary").pack(side="left", padx=5)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def _choose_color(self):
        color_code = colorchooser.askcolor(title="글자 색상 선택", initialcolor=self.color_var.get())
        if color_code[1]:
            self.color_var.set(color_code[1])
            self.color_preview.config(bg=color_code[1])

    def _on_ok(self):
        self.result = {"text": self.text_var.get(), "font_family": self.font_var.get(), "font_size": self.size_var.get(), "color": self.color_var.get()}
        self.destroy()

class ShapePropertiesDialog(ttk.Toplevel):
    def __init__(self, parent, initial_values=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("도형 속성")
        self.result = None
        
        self.shape_types = ["사각형", "삼각형", "오각형", "육각형", "자유곡선"]
        self.shape_var = tk.StringVar(value=self.shape_types[0])
        self.color_var = tk.StringVar(value="#FF0000")
        
        self.drawing_canvas = None
        self.pil_image = None
        self.pil_draw = None
        self.last_x, self.last_y = None, None

        if initial_values:
            self.shape_var.set(initial_values.get('shape_type', self.shape_types[0]))
            self.color_var.set(initial_values.get('color', '#FF0000'))

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="종류:").grid(row=0, column=0, sticky="w", pady=2)
        shape_combo = ttk.Combobox(main_frame, textvariable=self.shape_var, values=self.shape_types, state="readonly")
        shape_combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=2)
        shape_combo.bind("<<ComboboxSelected>>", self._on_shape_select)

        ttk.Label(main_frame, text="색상:").grid(row=1, column=0, sticky="w", pady=2)
        self.color_preview = tk.Canvas(main_frame, width=24, height=24, bg=self.color_var.get(), highlightthickness=1)
        self.color_preview.grid(row=1, column=1, sticky="w", pady=2)
        ttk.Button(main_frame, text="색상 선택", command=self._choose_color, bootstyle="secondary").grid(row=1, column=2, sticky="ew", padx=(5,0), pady=2)

        self.drawing_frame = ttk.Frame(main_frame, bootstyle="light")
        self.drawing_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10,0))
        main_frame.rowconfigure(2, weight=1)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))
        ttk.Button(btn_frame, text="확인", command=self._on_ok, bootstyle="primary").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="취소", command=self.destroy, bootstyle="secondary").pack(side="left", padx=5)

        self._on_shape_select()
        
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def _on_shape_select(self, event=None):
        if self.drawing_canvas: self.drawing_canvas.destroy()
        
        if self.shape_var.get() == "자유곡선":
            self.geometry("400x450")
            self.drawing_canvas = tk.Canvas(self.drawing_frame, bg="white", highlightthickness=0)
            self.drawing_canvas.pack(fill="both", expand=True, padx=1, pady=1)
            self.drawing_canvas.bind("<Button-1>", self._start_drawing)
            self.drawing_canvas.bind("<B1-Motion>", self._draw)
            self.drawing_canvas.bind("<ButtonRelease-1>", self._end_drawing)
            self.pil_image = Image.new("RGBA", (380, 280), (0, 0, 0, 0))
            self.pil_draw = ImageDraw.Draw(self.pil_image)
        else:
            self.geometry("")

    def _start_drawing(self, event):
        self.last_x, self.last_y = event.x, event.y
    
    def _draw(self, event):
        if self.last_x and self.last_y:
            self.drawing_canvas.create_line(self.last_x, self.last_y, event.x, event.y, fill=self.color_var.get(), width=3, capstyle=tk.ROUND, smooth=tk.TRUE)
            self.pil_draw.line([self.last_x, self.last_y, event.x, event.y], fill=self.color_var.get(), width=3, joint="curve")
            self.last_x, self.last_y = event.x, event.y
    
    def _end_drawing(self, event):
        self.last_x, self.last_y = None, None

    def _choose_color(self):
        color_code = colorchooser.askcolor(title="도형 색상 선택", initialcolor=self.color_var.get())
        if color_code[1]: self.color_var.set(color_code[1]); self.color_preview.config(bg=color_code[1])

    def _on_ok(self):
        self.result = {"shape_type": self.shape_var.get(), "color": self.color_var.get()}
        if self.shape_var.get() == "자유곡선" and self.pil_image:
            bbox = self.pil_image.getbbox()
            if bbox: self.result["pil_image"] = self.pil_image.crop(bbox)
        self.destroy()