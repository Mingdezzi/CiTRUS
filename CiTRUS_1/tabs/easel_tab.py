# 파일 경로: tabs/easel_tab.py

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import os
import sys
import re
import math
import random
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pickle

# --- 라이브러리 가용성 확인 ---
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# --- 공통 UI 요소 임포트 ---
from ui.dialogs import TextPropertiesDialog, ShapePropertiesDialog


class EaselTab(ttk.Frame):
    SAVE_IMG_MAX_SIZE = (2000, 2000)
    DISPLAY_IMG_MAX_SIZE = (800, 800)
    REFERENCE_CANVAS_HEIGHT = 1500.0
    GRID_SIZE = 7
    THUMBNAIL_SIZE = (48, 48)
    FILENAME_TRUNCATE_LIMIT = 25
    FILENAME_DISPLAY_LIMIT = 22

    def __init__(self, parent: tk.Misc, *args, **kwargs):
        if 'padding' not in kwargs: kwargs['padding'] = 0
        super().__init__(parent, *args, **kwargs)
        
        self.uploaded_images = []
        self.canvas_objects = {}
        self.logo_object = None
        self._drag_data = {"x": 0, "y": 0, "item": None}
        self._list_drag_data = {}
        self.fit_scale = 1.0

        self.active_selection_path = None
        self._resize_data = {}
        self._rotation_data = {}

        self.logo_path = tk.StringVar()
        self.logo_zone_height_var = tk.IntVar(value=90)
        self.logo_size_var = tk.IntVar(value=70)
        self.style_code = tk.StringVar()
        self.global_scale_var = tk.DoubleVar(value=30.0)
        self.grid_vars = []
        self.grid_overlap_var = tk.IntVar(value=70)
        self.output_width_var = tk.IntVar(value=1500)
        self.output_height_var = tk.IntVar(value=1500)
        self.output_format_var = tk.StringVar(value="PNG")
        self.background_color = tk.StringVar(value="#FFFFFF")
        self.check_all_var = tk.BooleanVar(value=False)
        self.save_directory = tk.StringVar(value=os.path.expanduser("~"))
        self.zoom_var = tk.DoubleVar(value=100.0)
        
        self.palette_color = tk.StringVar(value="#FFFFFF")
        
        self.selected_paths = set()
        self.last_selected_anchor_index = None
        self.is_color_picking_mode = False
        
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=0) 
        self._build_ui()
        
        self.background_color.trace_add("write", self._on_background_color_change)

    def _build_ui(self) -> None:
        # 1. 하단 바를 먼저 pack으로 아래에 붙입니다.
        bottom_frame = self._create_bottom_bar()
        # bottom_frame.pack(side="bottom", fill="x", padx=5, pady=2)

        # 2. 캔버스와 컨트롤 패널을 담을 상단 프레임을 만듭니다.
        content_frame = ttk.Frame(self)
        content_frame.pack(side="top", fill="both", expand=True) 
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=0)
        content_frame.grid_rowconfigure(0, weight=1)

        # 3. 상단 프레임 내부에 기존처럼 grid로 배치합니다.
        canvas_container = self._create_canvas_panel(content_frame)
        control_panel = self._create_control_panel(content_frame)
        canvas_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        control_panel.grid(row=0, column=1, sticky="ns", padx=(5, 0))

    def _create_canvas_panel(self, parent: ttk.Frame) -> ttk.Frame:
        canvas_container = ttk.LabelFrame(parent, text="Canvas", bootstyle="primary")
        canvas_container.rowconfigure(0, weight=1); canvas_container.columnconfigure(0, weight=1)
        self.viewport_frame = ttk.Frame(canvas_container)
        self.viewport_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.viewport_frame.grid_rowconfigure(0, weight=1); self.viewport_frame.grid_columnconfigure(0, weight=1)
        self.viewport_frame.bind("<Configure>", self._update_canvas_view)
        self.viewport = tk.Canvas(self.viewport_frame, bd=0, highlightthickness=0, bg=ttk.Style().colors.light)
        v_scroll = ttk.Scrollbar(self.viewport_frame, orient=VERTICAL, command=self.viewport.yview, bootstyle="round")
        h_scroll = ttk.Scrollbar(self.viewport_frame, orient=HORIZONTAL, command=self.viewport.xview, bootstyle="round")
        self.viewport.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.viewport.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns"); h_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas = tk.Canvas(self.viewport, bg=self.background_color.get(), width=self.output_width_var.get(), height=self.output_height_var.get(), highlightthickness=0)
        self.canvas_window_id = self.viewport.create_window((0, 0), window=self.canvas, anchor="nw")
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        if DND_AVAILABLE:
            self.canvas.drop_target_register(DND_FILES); self.canvas.dnd_bind("<<Drop>>", self._on_canvas_drop)
        self.canvas.bind("<Configure>", lambda e: self.viewport.config(scrollregion=self.viewport.bbox("all")))
        zoom_frame = self._create_zoom_panel(canvas_container)
        zoom_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 0))
        return canvas_container
        
    def _create_zoom_panel(self, parent: ttk.Frame) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=5)
        ttk.Label(frame, text="확대/축소:").pack(side=LEFT, padx=(5, 2))
        scale = ttk.Scale(frame, from_=50, to=200, variable=self.zoom_var, command=self._on_zoom_change)
        scale.pack(side=LEFT, fill=X, expand=YES)
        self.zoom_var.set(100)
        zoom_label = ttk.Label(frame, text="100%", width=5)
        zoom_label.pack(side=LEFT, padx=(2, 5))
        def update_zoom_label(value): zoom_label.config(text=f"{int(float(value))}%")
        self.zoom_var.trace_add("write", lambda *args: update_zoom_label(self.zoom_var.get()))
        return frame

    def _create_control_panel(self, parent: ttk.Frame) -> ttk.Frame:
        control_container = ttk.Frame(parent); control_container.rowconfigure(0, weight=1)
        left_column = ttk.Frame(control_container); left_column.grid(row=0, column=0, sticky="ns", padx=(0, 3)); left_column.rowconfigure(1, weight=1) 
        right_column = ttk.Frame(control_container); right_column.grid(row=0, column=1, sticky="ns"); right_column.columnconfigure(0, weight=1); right_column.rowconfigure(0, weight=1)
        self._create_canvas_settings_panel(left_column).grid(row=0, column=0, sticky="ew")
        self._create_layer_panel(left_column).grid(row=1, column=0, sticky="nsew", pady=(5,0))
        self._create_project_settings_panel(left_column).grid(row=2, column=0, sticky="ew", pady=(5,0))
        self._create_logo_panel(right_column).grid(row=0, column=0, sticky='nsew')
        self._create_decoration_panel(right_column).grid(row=1, column=0, sticky='ew', pady=(5,0))
        self._create_auto_layout_panel(right_column).grid(row=2, column=0, sticky='ew', pady=(5,0))
        self._create_image_output_panel(right_column).grid(row=3, column=0, sticky='ew', pady=(5,0))
        return control_container

    def _create_canvas_settings_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Setting >", bootstyle="info"); res_frame = ttk.Frame(frame, padding=3); res_frame.pack(fill="x")
        ttk.Label(res_frame, text="해상도 (가로x세로):").pack(anchor="w"); res_inputs_frame = ttk.Frame(res_frame); res_inputs_frame.pack(fill=X, pady=2)
        ttk.Spinbox(res_inputs_frame, from_=100, to=8000, textvariable=self.output_width_var, width=6).pack(side=LEFT, expand=YES, fill=X, padx=(0, 2))
        ttk.Label(res_inputs_frame, text="x").pack(side=LEFT)
        ttk.Spinbox(res_inputs_frame, from_=100, to=8000, textvariable=self.output_height_var, width=6).pack(side=LEFT, expand=YES, fill=X, padx=(2, 3))
        ttk.Button(res_inputs_frame, text="적용", command=self._apply_resolution, bootstyle="secondary", width=5).pack(side=LEFT)
        return frame
        
    def _create_logo_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Logo >", bootstyle="info"); frame.columnconfigure(0, weight=1); frame.rowconfigure(0, weight=1)
        logo_preview_container = ttk.Frame(frame); logo_preview_container.pack(fill="both", expand=True, padx=3, pady=3)
        self.logo_preview_label = ttk.Label(logo_preview_container, text="로고 없음\n(파일을 여기로 드래그)", anchor="center", bootstyle="light"); self.logo_preview_label.pack(fill="both", expand=True)
        if DND_AVAILABLE: self.logo_preview_label.drop_target_register(DND_FILES); self.logo_preview_label.dnd_bind("<<Drop>>", self._on_logo_panel_drop)
        logo_btn_frame = ttk.Frame(frame); logo_btn_frame.pack(fill="x", padx=3, pady=(0, 3)) 
        ttk.Button(logo_btn_frame, text="로고 선택", command=self._select_logo, bootstyle="secondary", width=15).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(logo_btn_frame, text="로고 삭제", command=self._delete_logo, bootstyle="danger", width=15).pack(side="left", fill="x", expand=True, padx=2)
        logo_controls_frame = ttk.Frame(frame); logo_controls_frame.pack(fill='x', padx=3, pady=2); logo_controls_frame.columnconfigure((0, 1), weight=1)
        logo_zone_frame = ttk.Frame(logo_controls_frame); logo_zone_frame.grid(row=0, column=0, sticky='w')
        ttk.Label(logo_zone_frame, text="구역 높이:").pack(side="left"); ttk.Button(logo_zone_frame, text="-", width=2, command=lambda: self._adjust_logo_zone(-10), bootstyle="secondary").pack(side="left", padx=(3,0))
        ttk.Label(logo_zone_frame, textvariable=self.logo_zone_height_var, width=4, anchor="center").pack(side="left")
        ttk.Button(logo_zone_frame, text="+", width=2, command=lambda: self._adjust_logo_zone(10), bootstyle="secondary").pack(side="left")
        self.logo_zone_height_var.trace_add("write", self._on_logo_zone_change)
        logo_size_frame = ttk.Frame(logo_controls_frame); logo_size_frame.grid(row=0, column=1, sticky='e')
        ttk.Label(logo_size_frame, text="로고 크기:").pack(side="left"); ttk.Button(logo_size_frame, text="-", width=2, command=lambda: self._adjust_logo_size(-5), bootstyle="secondary").pack(side="left", padx=(3,0))
        ttk.Label(logo_size_frame, textvariable=self.logo_size_var, width=4, anchor="center").pack(side="left")
        ttk.Button(logo_size_frame, text="+", width=2, command=lambda: self._adjust_logo_size(5), bootstyle="secondary").pack(side="left")
        self.logo_size_var.trace_add("write", lambda *args: self._update_object_display("logo"))
        return frame

    def _create_auto_layout_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Automatic Placement >", bootstyle="info")
        container = ttk.Frame(frame, padding=3); container.pack(fill='x'); container.columnconfigure(0, weight=1); container.columnconfigure(1, weight=0)
        grid_inner_frame = ttk.Frame(container); grid_inner_frame.grid(row=0, column=0, sticky='ns')
        self.grid_vars = [[tk.BooleanVar(value=False) for _ in range(self.GRID_SIZE)] for _ in range(self.GRID_SIZE)]
        for r, row_vars in enumerate(self.grid_vars):
            for c, var in enumerate(row_vars): ttk.Checkbutton(grid_inner_frame, variable=var, bootstyle="primary").grid(row=r, column=c, padx=1, pady=1) 
        right_controls_frame = ttk.Frame(container); right_controls_frame.grid(row=0, column=1, sticky='ns', padx=(10,0))
        overlap_frame = ttk.Frame(right_controls_frame); overlap_frame.pack(fill="x", pady=3) 
        ttk.Label(overlap_frame, text="겹침(%):").pack(side="left"); ttk.Spinbox(overlap_frame, from_=0, to=100, textvariable=self.grid_overlap_var, width=5, increment=5).pack(side="left", padx=3)
        ttk.Button(right_controls_frame, text="배치 적용", command=self._apply_grid_layout, bootstyle="primary").pack(fill='x', pady=2) 
        ttk.Button(right_controls_frame, text="초기화", command=self._reset_grid, bootstyle="warning-outline").pack(fill='x', pady=2)
        return frame

    def _create_project_settings_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Project >", bootstyle="info"); btn_frame = ttk.Frame(frame, padding=3); btn_frame.pack(fill="x"); btn_frame.columnconfigure((0,1), weight=1)
        ttk.Button(btn_frame, text="저장", command=self._save_project, bootstyle="primary", width=15).grid(row=0, column=0, sticky="ew", padx=(0,2)) 
        ttk.Button(btn_frame, text="불러오기", command=self._load_project, bootstyle="info", width=15).grid(row=0, column=1, sticky="ew", padx=(2,0)) 
        ttk.Button(frame, text="전체 초기화", command=self._clear_all, bootstyle="danger", width=15).pack(fill="x", padx=3, pady=(0,3)) 
        return frame
        
    def _create_image_output_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Output Image >", bootstyle="info"); inner_frame = ttk.Frame(frame, padding=3); inner_frame.pack(fill='both', expand=True)
        ttk.Label(inner_frame, text="파일명:").pack(anchor="w"); ttk.Entry(inner_frame, textvariable=self.style_code, justify="center").pack(fill="x", pady=(0,3))
        ttk.Label(inner_frame, text="파일 형식:").pack(anchor="w"); ttk.Combobox(inner_frame, textvariable=self.output_format_var, values=["PNG", "JPG"], state="readonly").pack(fill="x", pady=(0,3))
        ttk.Label(inner_frame, text="저장 위치:").pack(anchor="w"); ttk.Button(inner_frame, text="폴더 선택", command=self._select_save_directory, bootstyle="secondary", width=15).pack(fill="x")
        ttk.Button(inner_frame, text="이미지 저장", command=self._save_canvas, bootstyle="primary", width=15).pack(fill="x", pady=(8,0)) 
        return frame
        
    ### <-- 변경된 부분 시작 -->
    def _create_layer_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Layer >", bootstyle="info"); top_controls = ttk.Frame(frame, padding=(3,3,3,0)); top_controls.pack(fill='x')
        
        # (1) 체크박스 정렬을 위해 padx 추가
        check_all_frame = ttk.Frame(top_controls); check_all_frame.pack(side='left', padx=(8, 0))
        ttk.Checkbutton(check_all_frame, variable=self.check_all_var, command=self._toggle_all_checks).pack(side='left')
        
        # (2) 버튼 텍스트 변경 및 위젯 참조 저장
        self.select_all_button = ttk.Button(check_all_frame, text="전체선택", width=7, command=self._toggle_select_all_layers, bootstyle="secondary-outline")
        self.select_all_button.pack(side='left', padx=2)
        
        right_controls_frame = ttk.Frame(top_controls); right_controls_frame.pack(side='right')
        ttk.Label(right_controls_frame, text="일괄 크기:").pack(side='left'); ttk.Spinbox(right_controls_frame, from_=10, to=500, textvariable=self.global_scale_var, width=5, increment=5.0).pack(side='left', padx=3)
        ttk.Button(right_controls_frame, text="적용", command=self._apply_global_scale, bootstyle="primary", width=5).pack(side='left')
        
        action_buttons = ttk.Frame(frame, padding=3); action_buttons.pack(fill='x'); action_buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(action_buttons, text="이미지 추가", command=self._add_files, bootstyle="secondary", width=15).grid(row=0, column=0, sticky="ew", padx=(0,2)) 
        ttk.Button(action_buttons, text="선택 삭제", command=self._delete_selected_layers, bootstyle="danger", width=15).grid(row=0, column=1, sticky="ew", padx=(2,0)) 
        
        upload_canvas_container = ttk.Frame(frame); upload_canvas_container.pack(fill='both', expand=True, padx=3, pady=(0,3)); upload_canvas_container.rowconfigure(0, weight=1); upload_canvas_container.columnconfigure(0, weight=1)
        self.upload_canvas = tk.Canvas(upload_canvas_container, bd=0, highlightthickness=0, bg=ttk.Style().colors.bg)
        scrollbar = ttk.Scrollbar(upload_canvas_container, orient="vertical", command=self.upload_canvas.yview, bootstyle="round")
        self.upload_canvas.configure(yscrollcommand=scrollbar.set); self.upload_canvas.grid(row=0, column=0, sticky="nsew"); scrollbar.grid(row=0, column=1, sticky="ns")
        self.upload_list_frame = ttk.Frame(self.upload_canvas)
        self.upload_list_canvas_window = self.upload_canvas.create_window((0, 0), window=self.upload_list_frame, anchor="nw")
        self.upload_canvas.bind("<Configure>", lambda e: (self.upload_canvas.itemconfig(self.upload_list_canvas_window, width=e.width), self.upload_canvas.configure(scrollregion=self.upload_canvas.bbox("all"))))
        if DND_AVAILABLE:
            self.upload_canvas.drop_target_register(DND_FILES); self.upload_canvas.dnd_bind("<<Drop>>", self._on_layer_panel_drop)
            self.upload_list_frame.drop_target_register(DND_FILES); self.upload_list_frame.dnd_bind("<<Drop>>", self._on_layer_panel_drop)
        return frame
    ### <-- 변경된 부분 끝 -->
        
    def _create_decoration_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Asset >", bootstyle="info"); inner_frame = ttk.Frame(frame, padding=5); inner_frame.pack(fill='both', expand=True)
        add_frame = ttk.Frame(inner_frame); add_frame.pack(fill='x'); add_frame.columnconfigure((0,1), weight=1)
        ttk.Button(add_frame, text="텍스트 추가", command=self._add_text).grid(row=0, column=0, sticky='ew', padx=(0,1))
        ttk.Button(add_frame, text="도형 추가", command=self._add_shape).grid(row=0, column=1, sticky='ew', padx=(1,0))
        ttk.Separator(inner_frame, orient=HORIZONTAL).pack(fill='x', pady=8)
        palette_row_frame = ttk.Frame(inner_frame); palette_row_frame.pack(fill='x')
        self.palette_color_preview = tk.Canvas(palette_row_frame, width=30, height=28, highlightthickness=1, highlightbackground="gray", cursor="hand2")
        self.palette_color_preview.pack(side='left'); self.palette_color_preview.bind("<Button-1>", self._choose_palette_color)
        ttk.Label(palette_row_frame, textvariable=self.palette_color, width=8, anchor='center').pack(side='left', padx=5)
        ttk.Button(palette_row_frame, text="색상 추출", command=self._enter_color_pick_mode, bootstyle="secondary").pack(side='left', fill='x', expand=True)
        apply_frame = ttk.Frame(inner_frame); apply_frame.pack(fill='x', pady=(8,0)); apply_frame.columnconfigure((0,1), weight=1)
        ttk.Button(apply_frame, text="대상색상변경", command=self._apply_color_to_selected).grid(row=0, column=0, sticky='ew', padx=(0,1))
        ttk.Button(apply_frame, text="배경색상변경", command=self._apply_color_to_background).grid(row=0, column=1, sticky='ew', padx=(1,0))
        self.palette_color.trace_add("write", self._on_palette_color_change); self._on_palette_color_change()
        return frame

    def _create_bottom_bar(self) -> ttk.Frame:
        bottom_frame = ttk.Frame(self); bottom_frame.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(bottom_frame, text="", bootstyle="secondary"); self.status_label.grid(row=0, column=0, sticky="w")
        return bottom_frame
        
    def _on_palette_color_change(self, *args):
        new_color = self.palette_color.get()
        if hasattr(self, 'palette_color_preview') and self.palette_color_preview.winfo_exists():
            self.palette_color_preview.config(bg=new_color)

    def _choose_palette_color(self, event=None):
        color_code = tk.colorchooser.askcolor(title="팔레트 색상 선택", initialcolor=self.palette_color.get())
        if color_code[1]: self.palette_color.set(color_code[1].upper())

    def _enter_color_pick_mode(self):
        self.is_color_picking_mode = True; self.canvas.config(cursor="crosshair")
        self.status_label.config(text="🎨 캔버스 위의 항목을 클릭하여 색상을 추출하세요.")

    def _exit_color_pick_mode(self):
        self.is_color_picking_mode = False; self.canvas.config(cursor="")
        self.status_label.config(text="색상 추출 모드가 해제되었습니다.")

    def _pick_color_from_object(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        item_ids = self.canvas.find_closest(x, y)
        if not item_ids: self._exit_color_pick_mode(); return
        item_id = item_ids[0]; tags = self.canvas.gettags(item_id)
        if 'border' in tags: self._exit_color_pick_mode(); return
        path = next((tag for tag in tags if tag != "item"), None)
        if path:
            item_data = next((i for i in self.uploaded_images if i['path'] == path), None)
            canvas_obj = self.canvas_objects.get(path)
            if item_data and 'color' in item_data:
                self.palette_color.set(item_data['color']); self.status_label.config(text=f"색상 추출 완료: {item_data['color']}")
            elif canvas_obj and canvas_obj.get('type') == 'image':
                try:
                    pil_img = canvas_obj.get('pil_img_original')
                    img_w, img_h = pil_img.size
                    
                    item = next((i for i in self.uploaded_images if i['path'] == path))
                    temp_pil = self._get_display_pil(item, item['scale_var'].get(), self.fit_scale * (self.zoom_var.get() / 100.0), rotate=False)
                    if not temp_pil: self._exit_color_pick_mode(); return
                    disp_w, disp_h = temp_pil.width, temp_pil.height

                    center_x, center_y = self.canvas.coords(item_id)
                    click_x_rel = x - center_x
                    click_y_rel = y - center_y

                    angle_rad = math.radians(item.get('angle', 0.0))
                    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
                    unrotated_x_rel = click_x_rel * cos_a + click_y_rel * sin_a
                    unrotated_y_rel = -click_x_rel * sin_a + click_y_rel * cos_a

                    top_left_x_rel = -disp_w / 2
                    top_left_y_rel = -disp_h / 2
                    
                    click_x_in_img = unrotated_x_rel - top_left_x_rel
                    click_y_in_img = unrotated_y_rel - top_left_y_rel

                    if not (0 <= click_x_in_img <= disp_w and 0 <= click_y_in_img <= disp_h):
                        self._exit_color_pick_mode(); return
                        
                    orig_click_x = int((click_x_in_img / disp_w) * img_w)
                    orig_click_y = int((click_y_in_img / disp_h) * img_h)
                    orig_click_x = max(0, min(orig_click_x, img_w - 1))
                    orig_click_y = max(0, min(orig_click_y, img_h - 1))

                    pixel = pil_img.convert("RGBA").getpixel((orig_click_x, orig_click_y))
                    hex_color = f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}".upper()
                    self.palette_color.set(hex_color); self.status_label.config(text=f"색상 추출 완료: {hex_color}")

                except Exception as e: self.status_label.config(text=f"⚠️ 이미지 색상 추출 오류: {e}")
            else: self.status_label.config(text="⚠️ 색상 정보가 없는 레이어입니다.")
        self._exit_color_pick_mode()

    def _apply_color_to_selected(self):
        if not self.selected_paths: messagebox.showwarning("알림", "색상을 변경할 레이어를 먼저 선택하세요."); return
        changed_count = 0
        for path in self.selected_paths:
            item = next((i for i in self.uploaded_images if i['path'] == path), None)
            if item and ('color' in item):
                item['color'] = self.palette_color.get(); self._update_canvas_item(path); changed_count += 1
                if item.get('type') == 'shape': self._generate_shape_thumbnail(item)
        if changed_count > 0: self._populate_uploaded_images_list(); self.status_label.config(text=f"{changed_count}개 항목 색상 변경 완료.")
        else: messagebox.showwarning("알림", "선택된 항목 중 색상을 변경할 수 있는 레이어가 없습니다.")

    def _apply_color_to_background(self):
        self.background_color.set(self.palette_color.get()); self.status_label.config(text=f"배경색 변경 완료: {self.palette_color.get()}")

    def _add_text(self):
        dialog = TextPropertiesDialog(self.winfo_toplevel())
        if dialog.result: self._process_new_text(dialog.result)
        
    def _add_shape(self):
        dialog = ShapePropertiesDialog(self.winfo_toplevel())
        if dialog.result: self._process_new_shape(dialog.result)

    def _apply_resolution(self): self.zoom_var.set(100); self._update_canvas_view()
        
    def _update_canvas_view(self, event=None):
        viewport_w, viewport_h = self.viewport_frame.winfo_width(), self.viewport_frame.winfo_height()
        if viewport_w <= 1 or viewport_h <= 1: return
        logical_w, logical_h = self.output_width_var.get(), self.output_height_var.get()
        if logical_w <= 0 or logical_h <= 0: return
        padded_viewport_w, padded_viewport_h = viewport_w * 0.9, viewport_h * 0.9
        scale_x, scale_y = padded_viewport_w / logical_w, padded_viewport_h / logical_h
        self.fit_scale = min(scale_x, scale_y); self._on_zoom_change()

    def _on_zoom_change(self, *args):
        zoom_level = self.zoom_var.get() / 100.0; actual_zoom = self.fit_scale * zoom_level
        new_width, new_height = int(self.output_width_var.get() * actual_zoom), int(self.output_height_var.get() * actual_zoom)
        self.canvas.config(width=new_width, height=new_height)
        self.canvas.delete('border'); self.canvas.create_rectangle(0, 0, new_width-1, new_height-1, dash=(5, 3), outline='grey', tags='border')
        self._redraw_all_objects(); self._center_canvas_in_viewport()
    
    def _center_canvas_in_viewport(self):
        self.viewport.update_idletasks()
        viewport_w, viewport_h = self.viewport.winfo_width(), self.viewport.winfo_height()
        canvas_w, canvas_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
        x, y = max(0, (viewport_w - canvas_w) // 2), max(0, (viewport_h - canvas_h) // 2)
        self.viewport.coords(self.canvas_window_id, x, y)
        
    def _redraw_all_objects(self):
        all_objects = list(self.canvas_objects.values()) + ([self.logo_object] if self.logo_object else [])
        for obj in all_objects:
            if obj: self._update_object_display(obj['path'])
        if self.active_selection_path: self._draw_resize_handles(self.active_selection_path)

    def _save_project(self):
        path = filedialog.asksaveasfilename(title="프로젝트 저장", defaultextension=".wsb", filetypes=[("CiTRUS Project", "*.wsb")])
        if not path: return
        try:
            project_data = {
                'global_settings': { 'style_code': self.style_code.get(), 'logo_path': self.logo_path.get(), 'logo_zone_height': self.logo_zone_height_var.get(), 'logo_size': self.logo_size_var.get(), 'grid_overlap': self.grid_overlap_var.get(), 'output_width': self.output_width_var.get(), 'output_height': self.output_height_var.get(), 'output_format': self.output_format_var.get(), 'background_color': self.background_color.get() }, 
                'layers': [], 'canvas_positions': {}
            }
            for item in self.uploaded_images:
                serializable_item = item.copy()
                serializable_item['var_value'] = item['var'].get()
                if 'scale_var' in item: serializable_item['scale_var_value'] = item['scale_var'].get()
                for key in ['var', 'scale_var', 'widget', 'thumb_img', 'tk_img', 'ctrl_frame', 'btn_frame', 'name_label', 'checkbutton']:
                    serializable_item.pop(key, None)
                project_data['layers'].append(serializable_item)
            for item_path, obj in self.canvas_objects.items():
                project_data['canvas_positions'][item_path] = {'rel_x': obj['rel_x'], 'rel_y': obj['rel_y']}
            if self.logo_object: project_data['canvas_positions']['logo'] = {'rel_x': self.logo_object['rel_x'], 'rel_y': self.logo_object['rel_y']}
            with open(path, 'wb') as f: pickle.dump(project_data, f)
            self.status_label.config(text=f"프로젝트 저장 완료: {os.path.basename(path)}"); messagebox.showinfo("성공", "프로젝트를 성공적으로 저장했습니다.")
        except Exception as e: messagebox.showerror("저장 오류", f"프로젝트 저장 중 오류가 발생했습니다:\n{e}")

    def _load_project(self):
        if not messagebox.askyesno("불러오기 확인", "현재 작업 내용이 모두 사라집니다. 계속하시겠습니까?"): return
        path = filedialog.askopenfilename(title="프로젝트 불러오기", filetypes=[("CiTRUS Project", "*.wsb")])
        if not path: return
        try:
            with open(path, 'rb') as f: project_data = pickle.load(f)
            self._clear_all(confirm=False)
            settings = project_data.get('global_settings', {})
            for key, var in { 'style_code': self.style_code, 'logo_path': self.logo_path, 'logo_zone_height': self.logo_zone_height_var, 'logo_size': self.logo_size_var, 'grid_overlap': self.grid_overlap_var, 'output_width': self.output_width_var, 'output_height': self.output_height_var, 'output_format': self.output_format_var, 'background_color': self.background_color }.items():
                var.set(settings.get(key, var.get()))
            for item_data in project_data.get('layers', []):
                item_data['var'] = tk.BooleanVar(value=item_data.pop('var_value', False))
                if 'scale_var_value' in item_data: item_data['scale_var'] = tk.DoubleVar(value=item_data.pop('scale_var_value'))
                if item_data.get('type') == 'image' and 'pil_img_save' in item_data:
                    display_img = item_data['pil_img_save'].copy(); display_img.thumbnail(self.DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
                    item_data['pil_img_display'] = display_img
                    thumb = display_img.copy(); thumb.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    item_data['thumb_img'] = ImageTk.PhotoImage(thumb)
                self.uploaded_images.append(item_data)
            self._apply_resolution(); self._populate_uploaded_images_list(); self.update_idletasks()
            for item in self.uploaded_images:
                if item['var'].get(): self._on_item_check(item['var'], item['path'])
            if self.logo_path.get(): self._add_image_to_canvas(self.logo_path.get(), is_logo=True)
            self.update_idletasks()
            canvas_w, canvas_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
            for path, pos in project_data.get('canvas_positions', {}).items():
                obj = self.logo_object if path == 'logo' else self.canvas_objects.get(path)
                if obj:
                    obj['rel_x'], obj['rel_y'] = pos['rel_x'], pos['rel_y']
                    new_x, new_y = pos['rel_x'] * canvas_w, pos['rel_y'] * canvas_h
                    coords = self.canvas.coords(obj['id'])
                    if len(coords) == 2: cur_x, cur_y = coords
                    else: xs, ys = coords[0::2], coords[1::2]; cur_x, cur_y = sum(xs) / len(xs), sum(ys) / len(ys)
                    self.canvas.move(obj['id'], new_x - cur_x, new_y - cur_y)
            self.status_label.config(text=f"프로젝트 불러오기 완료: {os.path.basename(path)}"); messagebox.showinfo("성공", "프로젝트를 성공적으로 불러왔습니다.")
        except Exception as e: messagebox.showerror("불러오기 오류", f"프로젝트 파일('.wsb')을 불러오는 중 오류가 발생했습니다:\n{e}")

    def _select_save_directory(self):
        directory = filedialog.askdirectory(initialdir=self.save_directory.get())
        if directory: self.save_directory.set(directory); messagebox.showinfo("저장 위치", f"기본 저장 위치가\n'{directory}'\n(으)로 설정되었습니다.")
    
    def _toggle_all_checks(self):
        for item in self.uploaded_images: item['var'].set(self.check_all_var.get())
            
    def _find_item_widget(self, widget: tk.Widget) -> ttk.Frame | None:
        current = widget
        while current and not (isinstance(current, ttk.Frame) and hasattr(current, "is_draggable_item")): current = current.master
        return current

    def _on_canvas_double_click(self, event: tk.Event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y); item_ids = self.canvas.find_closest(x, y); path = None
        if item_ids:
            item_id = item_ids[0]; tags = self.canvas.gettags(item_id)
            if 'border' not in tags and 'handle' not in tags and 'rotate_handle' not in tags: path = next((tag for tag in tags if tag != "item"), None)
        if path and path in self.canvas_objects: self._draw_resize_handles(path)

    def _on_list_item_double_click(self, event: tk.Event):
        widget = self._find_item_widget(event.widget)
        if not widget: return
        index = widget.grid_info()["row"] // 2; item = self.uploaded_images[index]
        if item['path'] in self.canvas_objects: self._handle_canvas_selection(item['path'], 0); self._draw_resize_handles(item['path'])
        if item.get('type') == 'text':
            init_vals = {'text': item['text'], 'font_family': item['font_family'], 'font_size': int(item['scale_var'].get()), 'color': item['color']}
            dialog = TextPropertiesDialog(self.winfo_toplevel(), initial_values=init_vals)
            if dialog.result:
                item.update({ 'text': dialog.result['text'], 'font_family': dialog.result['font_family'], 'color': dialog.result['color']})
                item['scale_var'].set(dialog.result['font_size']); self._update_canvas_item(item['path']); self._populate_uploaded_images_list()
        elif item.get('type') == 'shape' and item.get('shape_type') != '자유곡선':
            init_vals = {'shape_type': item['shape_type'], 'color': item['color']}
            dialog = ShapePropertiesDialog(self.winfo_toplevel(), initial_values=init_vals)
            if dialog.result: item['color'] = dialog.result['color']; self._update_canvas_item(item['path']); self._populate_uploaded_images_list()

    def _update_canvas_item(self, path):
        if path not in self.canvas_objects: return
        item = next((i for i in self.uploaded_images if i['path'] == path), None); obj = self.canvas_objects[path]
        if not item: return
        
        self._update_object_display(path)
        
        if path == self.active_selection_path: self._draw_resize_handles(path)

    def _on_list_item_press(self, event: tk.Event) -> None:
        widget = self._find_item_widget(event.widget)
        if not widget: return
        clicked_index = widget.grid_info()["row"] // 2; self._handle_list_selection(clicked_index, event.state)
        self._list_drag_data = {"widget": widget, "source_index": clicked_index}
        
    def _on_list_item_drag(self, event: tk.Event) -> None:
        if not self._list_drag_data: return
        source_index = self._list_drag_data["source_index"]
        dest_widget = self._find_item_widget(event.widget.winfo_containing(event.x_root, event.y_root))
        if not dest_widget: return
        dest_index = dest_widget.grid_info()["row"] // 2
        if dest_index != source_index:
            item = self.uploaded_images.pop(source_index); self.uploaded_images.insert(dest_index, item)
            if self.last_selected_anchor_index == source_index: self.last_selected_anchor_index = dest_index
            self._populate_uploaded_images_list()
            new_widget = self.uploaded_images[dest_index].get("widget")
            if new_widget: self._list_drag_data.update({"widget": new_widget, "source_index": dest_index})

    def _on_list_item_release(self, event: tk.Event) -> None: self._list_drag_data = {}; self._reorder_canvas_layers()
        
    def _bind_recursive(self, widget: tk.Widget, event_type: str, command):
        widget.bind(event_type, command)
        for child in widget.winfo_children(): self._bind_recursive(child, event_type, command)
    
    def _populate_uploaded_images_list(self) -> None:
        for child in self.upload_list_frame.winfo_children(): child.destroy()
        text_thumb_img = Image.new('RGBA', self.THUMBNAIL_SIZE, (255, 255, 255, 220)); draw = ImageDraw.Draw(text_thumb_img)
        try: font = ImageFont.truetype(self._get_font_path('malgun.ttf'), 32); draw.text((8, 4), "T", font=font, fill="#555555")
        except: draw.text((8, 4), "T", fill="#555555")
        self.text_icon_photo = ImageTk.PhotoImage(text_thumb_img)
        for i, item in enumerate(self.uploaded_images):
            row_index = i * 2
            widget = ttk.Frame(self.upload_list_frame, style="light.TFrame", padding=5); widget.is_draggable_item = True
            widget.grid(row=row_index, column=0, sticky="ew", padx=2); widget.columnconfigure(1, weight=1)
            if i < len(self.uploaded_images) - 1: ttk.Separator(self.upload_list_frame).grid(row=row_index + 1, column=0, sticky='ew', padx=10, pady=2)
            item['var'].trace_add("write", lambda n, i, m, v=item['var'], p=item['path']: self._on_item_check(v, p))
            checkbutton = ttk.Checkbutton(widget, variable=item['var'], style="light.TCheckbutton"); checkbutton.grid(row=0, column=0, rowspan=2, sticky='ns', padx=(0, 5))
            item_type = item.get('type', 'image')
            if item_type == 'text':
                if 'scale_var' not in item: item['scale_var'] = tk.DoubleVar(value=item.get('font_size', 30))
                name, thumb, bg_state = item['text'], self.text_icon_photo, 'disabled'
            elif item_type == 'shape':
                if 'thumb_img' not in item: self._generate_shape_thumbnail(item)
                if 'scale_var' not in item: item['scale_var'] = tk.DoubleVar(value=100.0)
                name, thumb, bg_state = item['shape_type'], item['thumb_img'], 'disabled'
            else: # image
                if 'scale_var' not in item: item['scale_var'] = tk.DoubleVar(value=30.0)
                name, thumb = os.path.basename(item['path']), item['thumb_img']; bg_state = 'disabled' if not REMBG_AVAILABLE else 'normal'
            item['scale_var'].trace_add("write", lambda n, i, m, p=item['path']: self._on_scale_change(p))
            name = name[:self.FILENAME_DISPLAY_LIMIT] + "..." if len(name) > self.FILENAME_TRUNCATE_LIMIT else name
            name_label = ttk.Label(widget, image=thumb, text=name, compound="left", style="light.TLabel"); name_label.grid(row=0, column=1, rowspan=2, sticky='w')
            ctrl_frame = ttk.Frame(widget, style="light.TFrame"); ctrl_frame.grid(row=0, column=2, rowspan=2, sticky='e', padx=5)
            s_from = 8 if item_type != 'image' else 10; s_inc = 1.0 if item_type != 'image' else 5.0
            ttk.Spinbox(ctrl_frame, from_=s_from, to=500, textvariable=item['scale_var'], width=5, increment=s_inc).pack(pady=2)
            btn_frame = ttk.Frame(ctrl_frame, style="light.TFrame"); btn_frame.pack()
            ttk.Button(btn_frame, text="배경", width=5, command=lambda p=item['path']: self._remove_background(p), state=bg_state, bootstyle="secondary-outline").pack(side='left', padx=(0, 2))
            ttk.Button(btn_frame, text="삭제", width=5, command=lambda p=item['path']: self._delete_single_item(p), bootstyle="danger-outline").pack(side='left')
            item.update({'widget': widget, 'checkbutton': checkbutton, 'name_label': name_label, 'ctrl_frame': ctrl_frame, 'btn_frame': btn_frame})
            for w in [widget, name_label, ctrl_frame]:
                 self._bind_recursive(w, "<ButtonPress-1>", self._on_list_item_press); self._bind_recursive(w, "<B1-Motion>", self._on_list_item_drag)
                 self._bind_recursive(w, "<ButtonRelease-1>", self._on_list_item_release); self._bind_recursive(w, "<Double-Button-1>", self._on_list_item_double_click)
        self.upload_list_frame.update_idletasks(); self.upload_canvas.config(scrollregion=self.upload_canvas.bbox("all")); self._update_list_selection_visuals()

    ### <-- 변경된 부분 시작 -->
    def _update_select_all_button_state(self):
        """모든 항목 선택 여부에 따라 '전체선택/선택해제' 버튼의 상태를 업데이트합니다."""
        if not hasattr(self, 'select_all_button') or not self.select_all_button.winfo_exists():
            return
            
        all_paths = {item['path'] for item in self.uploaded_images}
        # 이미지가 하나라도 있고, 모든 이미지가 선택된 경우
        if all_paths and self.selected_paths == all_paths:
            self.select_all_button.config(text="선택해제", bootstyle="secondary")
        else:
            self.select_all_button.config(text="전체선택", bootstyle="secondary-outline")

    def _update_list_selection_visuals(self):
        for item in self.uploaded_images:
            widget = item.get('widget')
            if not (widget and widget.winfo_exists()): continue
            is_selected = item['path'] in self.selected_paths; base_style = "selected" if is_selected else "light"
            widgets_to_style = { 'widget': f"{base_style}.TFrame", 'ctrl_frame': f"{base_style}.TFrame", 'btn_frame': f"{base_style}.TFrame", 'checkbutton': f"{base_style}.TCheckbutton", 'name_label': f"{base_style}.TLabel" }
            for key, style_name in widgets_to_style.items():
                w = item.get(key)
                if w and w.winfo_exists():
                    try: w.configure(style=style_name)
                    except tk.TclError: pass
        self._update_select_all_button_state() # 버튼 상태 업데이트 함수 호출
    ### <-- 변경된 부분 끝 -->
        
    def _generate_shape_thumbnail(self, item_data):
        thumb = Image.new('RGBA', self.THUMBNAIL_SIZE, (255, 255, 255, 220)); draw = ImageDraw.Draw(thumb)
        if item_data['shape_type'] == '자유곡선' and 'pil_image' in item_data:
            img = item_data['pil_image'].copy(); img.thumbnail((40, 40), Image.Resampling.LANCZOS); thumb.paste(img, (4, 4), img)
        else:
            size, padding = 36, (self.THUMBNAIL_SIZE[0] - 36) // 2
            points = self._get_shape_points((padding, padding), size, item_data['shape_type'])
            if points: draw.polygon(points, fill=item_data['color'], outline=item_data['color'])
        item_data['thumb_img'] = ImageTk.PhotoImage(thumb)

    def _delete_single_item(self, path: str):
        item = next((i for i in self.uploaded_images if i['path'] == path), None)
        if not item: return
        name = item.get('text', item.get('shape_type', os.path.basename(path))); name = name[:27] + '...' if len(name) > 30 else name
        if messagebox.askyesno("삭제 확인", f"'{name}' 항목을 삭제하시겠습니까?"):
            self.uploaded_images.remove(item); self._remove_item_from_canvas(path); self._populate_uploaded_images_list()
            self.status_label.config(text=f"'{name}' 항목 삭제 완료.")
            
    def _delete_selected_layers(self):
        if not self.selected_paths: messagebox.showinfo("알림", "삭제할 항목을 목록이나 캔버스에서 선택해주세요."); return
        if messagebox.askyesno("삭제 확인", f"선택한 {len(self.selected_paths)}개의 항목을 삭제하시겠습니까?"):
            for path in list(self.selected_paths):
                item = next((i for i in self.uploaded_images if i['path'] == path), None)
                if item: self.uploaded_images.remove(item); self._remove_item_from_canvas(path)
            self.selected_paths.clear(); self._populate_uploaded_images_list(); self.status_label.config(text=f"선택한 항목 삭제 완료.")

    def _on_background_color_change(self, *args) -> None:
        color = self.background_color.get()
        if re.match(r'^#[0-9A-Fa-f]{6}$', color): self.canvas.configure(bg=color)
    
    def _adjust_logo_size(self, amount: int) -> None: self.logo_size_var.set(max(10, min(self.logo_size_var.get() + amount, 200)))
    def _adjust_logo_zone(self, amount: int) -> None: self.logo_zone_height_var.set(max(10, min(self.logo_zone_height_var.get() + amount, 500)))
    def _on_canvas_drop(self, event: tk.Event) -> None: self._process_new_files(self.winfo_toplevel().tk.splitlist(event.data))
    def _on_layer_panel_drop(self, event: tk.Event) -> None: self._process_new_files(self.winfo_toplevel().tk.splitlist(event.data))

    def _on_logo_panel_drop(self, event: tk.Event) -> None:
        files = [f.strip('{}') for f in self.winfo_toplevel().tk.splitlist(event.data)]
        if files:
            first_valid_file = next((f for f in files if os.path.isfile(f)), None)
            if first_valid_file: self._set_new_logo(first_valid_file)
            else: messagebox.showwarning("오류", "유효한 파일이 없습니다.")
    
    def _add_files(self) -> None: self._process_new_files(filedialog.askopenfilenames(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")]))
    
    def _process_new_files(self, files: tuple[str, ...]) -> None:
        if not files: return
        new_files_added = False
        for f in [f.strip('{}') for f in files]:
            if os.path.isfile(f) and f not in [d.get('path') for d in self.uploaded_images]:
                try:
                    pil_img = Image.open(f).convert("RGBA")
                    save_img = pil_img.copy(); save_img.thumbnail(self.SAVE_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
                    display_img = save_img.copy(); display_img.thumbnail(self.DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
                    thumb_img = display_img.copy(); thumb_img.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    self.uploaded_images.append({
                        'type': 'image', 'path': f, 'pil_img_save': save_img, 'pil_img_display': display_img,
                        'thumb_img': ImageTk.PhotoImage(thumb_img), 'var': tk.BooleanVar(value=False), 
                        'angle': 0.0, 'crop_box': None 
                    })
                    new_files_added = True
                except Exception as e: print(f"Error loading {f}: {e}")
        if new_files_added: self._populate_uploaded_images_list(); 
        if not self.style_code.get(): self._set_default_style_code()

    def _process_new_text(self, data: dict) -> None:
        uid = f"text_{random.randint(1000, 9999)}_{int(tk._default_root.tk.call('clock', 'milliseconds'))}"
        self.uploaded_images.append({'type': 'text', 'path': uid, 'var': tk.BooleanVar(value=False), 'angle': 0.0, **data})
        self._populate_uploaded_images_list()
        
    def _process_new_shape(self, data: dict) -> None:
        uid = f"shape_{random.randint(1000, 9999)}_{int(tk._default_root.tk.call('clock', 'milliseconds'))}"
        self.uploaded_images.append({'type': 'shape', 'path': uid, 'var': tk.BooleanVar(value=False), 'angle': 0.0, **data})
        self._populate_uploaded_images_list()

    def _clear_all(self, confirm=True) -> None:
        if confirm and not messagebox.askyesno("확인", "모든 작업 내용을 초기화하시겠습니까?"): return
        self.canvas.delete("all"); self.canvas_objects.clear(); self.logo_object = None; self._clear_resize_handles()
        self.active_selection_path = None; self.uploaded_images.clear(); self.logo_path.set(""); self._update_logo_preview()
        self.style_code.set(""); self._reset_grid(); self.selected_paths.clear(); self.last_selected_anchor_index = None
        self._populate_uploaded_images_list(); self.status_label.config(text="모든 항목이 초기화되었습니다.")
    
    def _set_default_style_code(self) -> None:
        files = [d['path'] for d in self.uploaded_images if d.get('type') == 'image']
        if files: self.style_code.set(os.path.commonprefix([os.path.basename(f) for f in files])[:8])

    def _on_item_check(self, var: tk.BooleanVar, path: str) -> None:
        item = next((i for i in self.uploaded_images if i['path'] == path), None)
        if not item: return
        if var.get():
            if path not in self.canvas_objects:
                item_type = item.get('type')
                if item_type == 'text': self._add_text_to_canvas(path)
                elif item_type == 'shape': self._add_shape_to_canvas(path)
                else: self._add_image_to_canvas(path)
        elif path in self.canvas_objects: self._remove_item_from_canvas(path)

# 파일 경로: tabs/easel_tab.py (이 함수만 교체하세요)

    def _add_image_to_canvas(self, path: str, is_logo: bool = False) -> None:
        display_w, display_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
        if display_w <= 1: return
        
        try:
            pil_img = Image.open(path).convert("RGBA")
            pil_img.thumbnail(self.DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
        except Exception as e:
            messagebox.showerror("오류", f"이미지 파일을 여는 데 실패했습니다: {e}")
            return

        actual_zoom = self.fit_scale * (self.zoom_var.get() / 100.0)
        logo_zone_h = self.output_height_var.get() * (self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT) * actual_zoom
        
        if is_logo:
            # --- 핵심 수정 부분 시작 ---
            # 1. 화면에 표시될 PIL 이미지를 미리 계산해서 최종 너비를 가져옵니다.
            temp_data_source = {'pil_img_display': pil_img, 'scale_var': self.logo_size_var, 'angle': 0.0, 'crop_box': None}
            display_pil = self._get_display_pil(temp_data_source, scale=self.logo_size_var.get(), actual_zoom=actual_zoom, is_logo=True, rotate=False)
            
            # 2. 너비를 기반으로 좌측 정렬을 위한 x 좌표를 새로 계산합니다.
            margin = 15  # 캔버스 좌측 여백
            x = margin + (display_pil.width / 2)
            y = logo_zone_h / 2
            # --- 핵심 수정 부분 끝 ---
            obj_path_id = "logo"
        else:
            x, y = (display_w / 2), (logo_zone_h + (display_h - logo_zone_h) / 2)
            obj_path_id = path

        item_id = self.canvas.create_image(x, y, tags=("item", obj_path_id))
        obj_data = {
            'type': 'image', 
            'id': item_id, 
            'pil_img_original': pil_img, 
            'tk_img': None, 
            'pil_for_display': None, 
            'rel_x': x / display_w, 
            'rel_y': y / display_h, 
            'is_logo': is_logo, 
            'path': obj_path_id,
            'original_path': path
        }

        if is_logo:
            self.logo_object = obj_data
        else:
            item = next((i for i in self.uploaded_images if i['path'] == path), None)
            if not item: return
            item['pil_img_display'] = pil_img
            self.canvas_objects[obj_path_id] = obj_data
            
        self._update_object_display(obj_path_id)
        self._reorder_canvas_layers()

    def _add_text_to_canvas(self, path: str) -> None:
        item = next((i for i in self.uploaded_images if i['path'] == path), None)
        if not item: return
        display_w, display_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
        if display_w <= 1: return
        
        logo_zone_h_ratio = self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT
        x = display_w / 2
        y = (display_h * logo_zone_h_ratio) + (display_h * (1 - logo_zone_h_ratio) / 2)
        
        item_id = self.canvas.create_image(x, y, tags=("item", path))
        self.canvas_objects[path] = {'type': 'text', 'id': item_id, 'rel_x': x / display_w, 'rel_y': y / display_h, 'path': path, 'tk_img': None, 'pil_for_display': None}
        self._update_object_display(path)
        self._reorder_canvas_layers()

    def _add_shape_to_canvas(self, path: str) -> None:
        item = next((i for i in self.uploaded_images if i['path'] == path), None);
        if not item: return
        display_w, display_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
        if display_w <= 1: return
        logo_zone_h_ratio = self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT
        x = display_w / 2
        y = (display_h * logo_zone_h_ratio) + (display_h * (1 - logo_zone_h_ratio) / 2)
        
        if item['shape_type'] == '자유곡선':
            item_id = self.canvas.create_image(x, y, tags=("item", path))
            self.canvas_objects[path] = {'type': 'shape', 'shape_type': '자유곡선', 'id': item_id, 
                                        'pil_img_original': item['pil_image'], 'tk_img': None, 'pil_for_display': None,
                                        'rel_x': x/display_w, 'rel_y': y/display_h, 'path': path}
        else:
            item_id = self.canvas.create_polygon(0,0, tags=("item", path))
            self.canvas_objects[path] = {'type': 'shape', 'shape_type': item['shape_type'], 'id': item_id, 
                                        'rel_x': x/display_w, 'rel_y': y/display_h, 'path': path}
        self._update_object_display(path); self._reorder_canvas_layers()
        
    def _get_shape_points(self, center, size, shape_type):
        x, y = center; r = size / 2
        n_map = {'삼각형': 3, '오각형': 5, '육각형': 6}; offset_map = {'삼각형': -90, '오각형': -90, '육각형': -30}
        if shape_type == "사각형": return [x-r, y-r, x+r, y-r, x+r, y+r, x-r, y+r]
        n, offset = n_map.get(shape_type, 0), math.radians(offset_map.get(shape_type, 0))
        return [p for i in range(n) for p in (x + r * math.cos(2*math.pi*i/n + offset), y + r * math.sin(2*math.pi*i/n + offset))]

    def _remove_item_from_canvas(self, path: str) -> None:
        if path == self.active_selection_path: self._clear_resize_handles(); self.active_selection_path = None
        if path in self.canvas_objects: self.canvas.delete(self.canvas_objects.pop(path)['id'])
        if path in self.selected_paths: self.selected_paths.remove(path)
    
    def _is_pixel_transparent(self, event: tk.Event, item_id: int) -> bool:
        """캔버스 아이템의 특정 좌표 픽셀이 투명한지 확인합니다. (회전 보정 포함)"""
        tags = self.canvas.gettags(item_id)
        path = next((tag for tag in tags if tag not in ["item", "handle", "rotate_handle"]), None)
        if not path: return False

        obj = self.logo_object if self.logo_object and self.logo_object.get('path') == path else self.canvas_objects.get(path)
        if not obj: return False
        
        obj_type = obj.get('type')
        if obj_type not in ['image', 'text'] and obj.get('shape_type') != '자유곡선':
            return False

        pil_img = obj.get('pil_for_display')
        if not pil_img or pil_img.mode != 'RGBA':
            return False 

        try:
            canvas_x, canvas_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            center_x, center_y = self.canvas.coords(item_id)
            img_w, img_h = pil_img.width, pil_img.height

            rel_x = canvas_x - center_x
            rel_y = canvas_y - center_y

            item = next((i for i in self.uploaded_images if i['path'] == path), None)
            angle = item.get('angle', 0.0) if item else 0.0
            angle_rad = math.radians(-angle) 
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

            unrotated_rel_x = rel_x * cos_a - rel_y * sin_a
            unrotated_rel_y = rel_x * sin_a + rel_y * cos_a

            img_x = unrotated_rel_x + img_w / 2
            img_y = unrotated_rel_y + img_h / 2

            if not (0 <= img_x < img_w and 0 <= img_y < img_h):
                return True

            pixel = pil_img.getpixel((int(img_x), int(img_y)))
            return pixel[3] < 10

        except Exception:
            return True

    def _on_press(self, event: tk.Event) -> None:
        if self.is_color_picking_mode:
            self._pick_color_from_object(event)
            return

        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        overlapping = self.canvas.find_overlapping(x-1, y-1, x+1, y+1)
        handle = next((i for i in overlapping if "handle" in self.canvas.gettags(i) or "rotate_handle" in self.canvas.gettags(i)), None)
        if handle and self.active_selection_path:
            tags = self.canvas.gettags(handle); item_id = self.canvas_objects[self.active_selection_path]['id']
            if "rotate_handle" in tags:
                bbox = self.canvas.bbox(item_id); center_x, center_y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
                start_angle = math.degrees(math.atan2(y - center_y, x - center_x))
                item = next((i for i in self.uploaded_images if i['path'] == self.active_selection_path), None)
                self._rotation_data = {"item_id": item_id, "center_x": center_x, "center_y": center_y, "start_angle": start_angle, "initial_item_angle": item['angle']}
                return
            handle_type = next((t for t in tags if t not in ["handle", "item"]), None)
            if handle_type:
                bbox = self.canvas.bbox(item_id)
                self._resize_data = {"item_id": item_id, "handle_type": handle_type, "start_x": x, "start_y": y, "start_bbox": bbox, "is_cropping": (event.state & 0x0004) != 0}
                return

        topmost_item_id = None
        all_items_in_order = self.canvas.find_all()
        for item_id in reversed(all_items_in_order):
            if item_id in overlapping and 'item' in self.canvas.gettags(item_id):
                if not self._is_pixel_transparent(event, item_id):
                    topmost_item_id = item_id
                    break 
        
        path = None
        if topmost_item_id:
            self._drag_data = {"item": topmost_item_id, "x": x, "y": y}
            tags = self.canvas.gettags(topmost_item_id)
            path = next((tag for tag in tags if tag != "item"), None)
        
        self._handle_canvas_selection(path, event.state)
        if not path and self.active_selection_path:
            self._clear_resize_handles()
            self.active_selection_path = None

    def _on_motion(self, event: tk.Event) -> None:
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self._rotation_data:
            d = self._rotation_data
            current_angle = math.degrees(math.atan2(y - d['center_y'], x - d['center_x']))
            angle_diff = current_angle - d['start_angle']
            item = next((i for i in self.uploaded_images if i['path'] == self.active_selection_path), None)
            if item: item['angle'] = d['initial_item_angle'] + angle_diff; self._update_object_display(self.active_selection_path)
            return
        if self._resize_data:
            path = self.active_selection_path; item = next((i for i in self.uploaded_images if i['path'] == path), None)
            if not item: return 
            
            d = self._resize_data; handle_type = d['handle_type']
            dx = x - d['start_x']; dy = y - d['start_y']
            
            if d.get("is_cropping") and item.get('type') == 'image':
                if 'crop_box_on_drag' not in item:
                    orig_w, orig_h = item['pil_img_display'].size
                    item['crop_box_on_drag'] = item['crop_box'] or (0, 0, orig_w, orig_h)
                start_bbox = d['start_bbox']; start_w, start_h = start_bbox[2] - start_bbox[0], start_bbox[3] - start_bbox[1]
                if start_w == 0 or start_h == 0: return
                rad = -math.radians(item['angle']); cos_a, sin_a = math.cos(rad), math.sin(rad)
                dx_rot, dy_rot = dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a
                cropped_w, cropped_h = item['crop_box_on_drag'][2] - item['crop_box_on_drag'][0], item['crop_box_on_drag'][3] - item['crop_box_on_drag'][1]
                scale_x, scale_y = cropped_w / start_w, cropped_h / start_h
                l, t, r, b = item['crop_box_on_drag']
                if 'w' in handle_type: l += dx_rot * scale_x
                if 'e' in handle_type: r += dx_rot * scale_x
                if 'n' in handle_type: t += dy_rot * scale_y
                if 's' in handle_type: b += dy_rot * scale_y
                orig_w, orig_h = item['pil_img_display'].size
                l, t = max(0, l), max(0, t); r, b = min(orig_w, r), min(orig_h, b)
                if r > l and b > t: item['crop_box'] = (l, t, r, b); self._update_object_display(path)
            else:
                start_bbox = d["start_bbox"]; start_w, start_h = start_bbox[2] - start_bbox[0], start_bbox[3] - start_bbox[1]
                if start_w == 0 or start_h == 0: return
                rad = -math.radians(item.get('angle', 0.0)); cos_a, sin_a = math.cos(rad), math.sin(rad)
                dx_rot, dy_rot = dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a

                if "e" in handle_type: scale_change_x = (start_w + dx_rot) / start_w
                elif "w" in handle_type: scale_change_x = (start_w - dx_rot) / start_w
                else: scale_change_x = 1.0

                if "s" in handle_type: scale_change_y = (start_h + dy_rot) / start_h
                elif "n" in handle_type: scale_change_y = (start_h - dy_rot) / start_h
                else: scale_change_y = 1.0

                scale_change = max(scale_change_x, scale_change_y)
                is_image_like = item.get('type') == 'image' or item.get('shape_type') == '자유곡선'
                if handle_type in ['nw', 'ne', 'sw', 'se']: scale_change = max(abs(scale_change_x), abs(scale_change_y)) * (1 if scale_change_x>0 or scale_change_y >0 else -1)
                
                initial_scale = item.get('initial_scale_on_drag', item['scale_var'].get())
                if 'initial_scale_on_drag' not in item: item['initial_scale_on_drag'] = initial_scale
                
                new_scale = initial_scale * scale_change
                s_from = 8
                new_scale = max(s_from, min(new_scale, 500))
                item['scale_var'].set(new_scale)
            return

        if self._drag_data.get("item"):
            self.canvas.move(self._drag_data["item"], x - self._drag_data["x"], y - self._drag_data["y"]); self._drag_data.update(x=x, y=y)

    def _on_release(self, event: tk.Event) -> None:
        path = self.active_selection_path
        if self._resize_data or self._rotation_data:
            if path:
                item = next((i for i in self.uploaded_images if i['path'] == path), None)
                if item:
                    item.pop('initial_scale_on_drag', None)
                    item.pop('crop_box_on_drag', None)
            self._resize_data, self._rotation_data = {}, {}
            if path:
                self._update_object_display(path)
            self.canvas.config(cursor="")
            return

        if self._drag_data.get("item"):
            item_id = self._drag_data["item"]
            path = next((tag for tag in self.canvas.gettags(item_id) if tag != "item"), None)
            obj = self.logo_object if self.logo_object and self.logo_object['id'] == item_id else self.canvas_objects.get(path)
            if not obj: self._drag_data["item"] = None; return
            
            canvas_w, canvas_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
            actual_zoom = self.fit_scale * (self.zoom_var.get() / 100.0)
            logo_zone_h = self.output_height_var.get() * (self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT) * actual_zoom
            coords = self.canvas.coords(item_id)
            
            cur_x, cur_y = self.canvas.coords(item_id) if len(coords) == 2 else ( (min(coords[0::2]) + max(coords[0::2]))/2, (min(coords[1::2]) + max(coords[1::2]))/2 )

            bbox = self.canvas.bbox(item_id)
            if not bbox: return
            item_w, item_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if obj.get('is_logo'): new_x = max(item_w/2, min(cur_x, canvas_w - item_w/2)); new_y = max(item_h/2, min(cur_y, logo_zone_h - item_h/2))
            else: new_x = max(item_w/2, min(cur_x, canvas_w - item_w/2)); new_y = max(logo_zone_h + item_h/2, min(cur_y, canvas_h - item_h/2))
            
            self.canvas.move(item_id, new_x - cur_x, new_y - cur_y)
            if canvas_w > 1 and canvas_h > 1: obj.update(rel_x=(new_x/canvas_w), rel_y=(new_y/canvas_h))
            self._drag_data["item"] = None
            if path == self.active_selection_path: self._draw_resize_handles(path)
    
    def _select_logo(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png")])
        if path: self._set_new_logo(path)
        
    def _set_new_logo(self, path: str):
        self.logo_path.set(path)
        if self.logo_object: self.canvas.delete(self.logo_object['id'])
        self._add_image_to_canvas(path, is_logo=True); self._update_logo_preview()
        
    def _update_logo_preview(self):
        path = self.logo_path.get()
        if path and os.path.exists(path):
            try:
                img = Image.open(path); w, h = self.logo_preview_label.winfo_width()-10, self.logo_preview_label.winfo_height()-10
                if w < 1 or h < 1: return self.logo_preview_label.after(100, self._update_logo_preview)
                img.thumbnail((w,h), Image.Resampling.LANCZOS); self.logo_preview_image = ImageTk.PhotoImage(img)
                self.logo_preview_label.config(image=self.logo_preview_image, text="")
            except Exception: self.logo_preview_label.config(image="", text="이미지 오류")
        else: self.logo_preview_label.config(image="", text="로고 없음\n(파일을 여기로 드래그)")

    def _delete_logo(self) -> None:
        if self.logo_object: self.canvas.delete(self.logo_object['id']); self.logo_object = None; self.logo_path.set("")
        self._update_logo_preview(); self.status_label.config(text="로고가 삭제되었습니다.")

    def _on_logo_zone_change(self, *args) -> None: self._redraw_all_objects()
    
    def _reorder_canvas_layers(self) -> None:
        for item in reversed(self.uploaded_images):
            if item['path'] in self.canvas_objects: self.canvas.tag_raise(self.canvas_objects[item['path']]['id'])
        if self.logo_object: self.canvas.tag_raise(self.logo_object['id'])
        self.canvas.tag_raise("rotate_handle"); self.canvas.tag_raise("handle")
            
    def _apply_global_scale(self, target_paths=None) -> None:
        paths_to_scale = target_paths if target_paths is not None else self.selected_paths
        if not paths_to_scale:
            if target_paths is None: messagebox.showwarning("알림", "크기를 변경할 레이어를 먼저 선택하세요.")
            return
        scale_val = self.global_scale_var.get()
        for path in paths_to_scale:
            item = next((i for i in self.uploaded_images if i['path'] == path), None)
            if item : item['scale_var'].set(scale_val)
        if target_paths is None: self.status_label.config(text=f"{len(paths_to_scale)}개 항목 크기 변경 완료.")

    def _handle_list_selection(self, clicked_index, state):
        is_shift, is_ctrl = (state & 0x0001), (state & 0x0004)
        if is_shift and self.last_selected_anchor_index is not None:
            start, end = min(self.last_selected_anchor_index, clicked_index), max(self.last_selected_anchor_index, clicked_index)
            self.selected_paths.clear(); [self.selected_paths.add(self.uploaded_images[i]['path']) for i in range(start, end + 1)]
        elif is_ctrl:
            clicked_path = self.uploaded_images[clicked_index]['path']
            if clicked_path in self.selected_paths: self.selected_paths.remove(clicked_path)
            else: self.selected_paths.add(clicked_path)
            self.last_selected_anchor_index = clicked_index
        else:
            clicked_path = self.uploaded_images[clicked_index]['path']
            if len(self.selected_paths) == 1 and clicked_path in self.selected_paths: self.selected_paths.clear(); self.last_selected_anchor_index = None
            else: self.selected_paths.clear(); self.selected_paths.add(clicked_path); self.last_selected_anchor_index = clicked_index
        self._update_list_selection_visuals()

    def _handle_canvas_selection(self, path, state):
        is_ctrl = (state & 0x0004)
        if is_ctrl:
            if path:
                if path in self.selected_paths: self.selected_paths.remove(path)
                else: self.selected_paths.add(path)
        else:
            if path:
                if len(self.selected_paths) == 1 and path in self.selected_paths: self.selected_paths.clear()
                else: self.selected_paths.clear(); self.selected_paths.add(path)
            else: self.selected_paths.clear()
        try: self.last_selected_anchor_index = [i['path'] for i in self.uploaded_images].index(path) if path else None
        except ValueError: self.last_selected_anchor_index = None
        self._update_list_selection_visuals()

    def _toggle_select_all_layers(self):
        all_paths = {item['path'] for item in self.uploaded_images}
        if self.selected_paths == all_paths: self.selected_paths.clear()
        else: self.selected_paths = all_paths
        self.last_selected_anchor_index = None; self._update_list_selection_visuals()

    def _on_scale_change(self, path: str) -> None: self._update_object_display(path)

    def _rotate_points(self, points, center, angle_degrees):
        angle_rad = math.radians(angle_degrees)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        cx, cy = center
        new_points = []
        for i in range(0, len(points), 2):
            px, py = points[i], points[i+1]
            px_rel, py_rel = px - cx, py - cy
            new_px = px_rel * cos_a - py_rel * sin_a + cx
            new_py = px_rel * sin_a + py_rel * cos_a + cy
            new_points.extend([new_px, new_py])
        return new_points

    def _update_object_display(self, path: str):
        is_logo = (path == "logo")
        obj = self.logo_object if is_logo else self.canvas_objects.get(path)
        if not obj: return
        
        item = None if is_logo else next((i for i in self.uploaded_images if i['path'] == path), None)
        if not is_logo and not item: return

        canvas_w, canvas_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
        if canvas_w <= 1 or canvas_h <= 1: return
        x, y = obj['rel_x'] * canvas_w, obj['rel_y'] * canvas_h
        actual_zoom = self.fit_scale * (self.zoom_var.get() / 100.0)

        obj_type = obj.get('type')
        if obj_type == 'text':
            font_size = int(item['scale_var'].get() * actual_zoom)
            font_to_measure = ImageFont.truetype(self._get_font_path(item['font_family'] + '.ttf'), font_size)
            bbox = font_to_measure.getbbox(item['text'])
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

            txt_img = Image.new('RGBA', (text_w if text_w > 0 else 1, text_h if text_h > 0 else 1))
            d = ImageDraw.Draw(txt_img)
            d.text((-bbox[0], -bbox[1]), item['text'], font=font_to_measure, fill=item['color'])

            rotated_img = txt_img.rotate(item['angle'], expand=True, resample=Image.Resampling.BICUBIC)
            obj['tk_img'] = ImageTk.PhotoImage(rotated_img)
            obj['pil_for_display'] = rotated_img
            self.canvas.itemconfig(obj['id'], image=obj['tk_img']); self.canvas.coords(obj['id'], x, y)

        elif obj_type == 'shape' and obj.get('shape_type') != '자유곡선':
            points = self._get_shape_points((x, y), item['scale_var'].get() * actual_zoom, obj['shape_type'])
            if item.get('angle', 0.0) != 0:
                points = self._rotate_points(points, (x, y), -item.get('angle', 0.0))
            self.canvas.coords(obj['id'], points)
            self.canvas.itemconfig(obj['id'], fill=item['color'], outline=item['color'])
        else:  # Image, Logo, or Free-form Shape
            # is_logo 플래그에 따라 다른 데이터 소스를 사용
            data_source = {'pil_img_display': obj['pil_img_original'], 'scale_var': self.logo_size_var, 'angle': 0.0, 'crop_box': None} if is_logo else item
            scale_value = self.logo_size_var.get() if is_logo else item['scale_var'].get()
            
            pil_img = self._get_display_pil(data_source, scale=scale_value, actual_zoom=actual_zoom, is_logo=is_logo)
            if not pil_img: return
            
            obj['tk_img'] = ImageTk.PhotoImage(pil_img)
            obj['pil_for_display'] = pil_img
            self.canvas.itemconfig(obj['id'], image=obj['tk_img']); self.canvas.coords(obj['id'], x, y)
            
        if path == self.active_selection_path: self._draw_resize_handles(path)

    def _get_font_path(self, font_name: str) -> str:
        font_dir = "C:/Windows/Fonts" if sys.platform == "win32" else "/usr/share/fonts"
        if not font_name.lower().endswith('.ttf'):
            font_name += '.ttf'
        path = os.path.join(font_dir, font_name)
        return path if os.path.exists(path) else 'malgun.ttf'

    def _save_canvas(self) -> None:
        if not self.canvas_objects and not self.logo_object: return messagebox.showwarning("알림", "캔버스에 저장할 항목이 없습니다.")
        save_w, save_h = self.output_width_var.get(), self.output_height_var.get()
        try: bg_color = tuple(int(self.background_color.get().lstrip('#')[i:i+2], 16) for i in (0,2,4)) + (255,)
        except: bg_color = (255, 255, 255, 255)
        final_image = Image.new("RGBA", (save_w, save_h), bg_color);
        all_objs = list(self.canvas_objects.values()) + ([self.logo_object] if self.logo_object else [])
        ordered_ids = self.canvas.find_all(); sorted_objs = sorted([o for o in all_objs if o and 'id' in o], key=lambda o: ordered_ids.index(o['id']))
        for obj in sorted_objs:
            item = next((i for i in self.uploaded_images if i.get('path') == obj.get('path')), None)
            center_x, center_y = obj['rel_x'] * save_w, obj['rel_y'] * save_h
            if obj.get('type') == 'text' and item:
                font = ImageFont.truetype(self._get_font_path(item['font_family']), int(item['scale_var'].get()))
                bbox = font.getbbox(item['text'])
                text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                
                txt_img = Image.new('RGBA', (text_w, text_h), (255,255,255,0))
                d = ImageDraw.Draw(txt_img)
                d.text((-bbox[0], -bbox[1]), item['text'], font=font, fill=item['color'])

                if item.get('angle', 0.0) != 0:
                    txt_img = txt_img.rotate(item.get('angle', 0.0), expand=True, resample=Image.Resampling.BICUBIC)
                
                w, h = txt_img.size
                final_image.paste(txt_img, (int(center_x-w/2), int(center_y-h/2)), txt_img)

            elif obj.get('type') == 'shape' and item:
                shape_img = Image.new('RGBA', (save_w, save_h), (0,0,0,0))
                shape_draw = ImageDraw.Draw(shape_img)
                if obj.get('shape_type') != '자유곡선':
                     points = self._get_shape_points((center_x, center_y), item['scale_var'].get(), obj['shape_type'])
                     if item.get('angle', 0.0) != 0: points = self._rotate_points(points, (center_x, center_y), -item.get('angle', 0.0))
                     shape_draw.polygon(points, fill=item['color'])
                else:
                    pil_img = obj['pil_img_original']; scale = item['scale_var'].get()/100.0; final_w, final_h = int(pil_img.width * scale), int(pil_img.height * scale)
                    if final_w < 1 or final_h < 1: continue
                    img_to_paste = pil_img.resize((final_w, final_h), Image.Resampling.LANCZOS)
                    if item.get('angle', 0.0) != 0: img_to_paste = img_to_paste.rotate(item.get('angle', 0.0), expand=True, resample=Image.Resampling.BICUBIC)
                    w, h = img_to_paste.size; shape_img.paste(img_to_paste, (int(center_x-w/2), int(center_y-h/2)), img_to_paste)
                final_image.alpha_composite(shape_img)

            elif obj.get('type') == 'image':
                pil_to_process = None
                if obj.get('is_logo'): pil_to_process = Image.open(obj['path']).convert("RGBA")
                elif item and 'pil_img_save' in item: pil_to_process = item['pil_img_save']
                if pil_to_process:
                    if item and item.get('crop_box'): pil_to_process = pil_to_process.crop(item['crop_box'])
                    scale_percent = self.logo_size_var.get() if obj.get('is_logo') else (item['scale_var'].get() if item else 30)
                    canvas_h_for_calc = self.output_height_var.get()
                    if obj.get('is_logo'): target_h = canvas_h_for_calc * (self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT) * (scale_percent / 100.0)
                    else: logo_zone_h_abs = canvas_h_for_calc * (self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT); target_h = (canvas_h_for_calc - logo_zone_h_abs) * (scale_percent / 100.0)
                    if pil_to_process.height > 0:
                        ratio = target_h / pil_to_process.height; final_w, final_h = int(pil_to_process.width * ratio), int(target_h)
                        if final_w > 0 and final_h > 0:
                            img_to_paste = pil_to_process.resize((final_w, final_h), Image.Resampling.LANCZOS)
                            if item and item.get('angle'): img_to_paste = img_to_paste.rotate(item['angle'], expand=True, resample=Image.Resampling.BICUBIC)
                            w, h = img_to_paste.size; final_image.paste(img_to_paste, (int(center_x-w/2), int(center_y-h/2)), img_to_paste)

        fname = (self.style_code.get() or "thumbnail") + ('.png' if self.output_format_var.get() == "PNG" else ".jpg")
        save_path = filedialog.asksaveasfilename(initialdir=self.save_directory.get(), initialfile=fname, defaultextension=fname.split('.')[-1])
        if not save_path: return
        try:
            if self.output_format_var.get() == "JPG": final_image.convert("RGB").save(save_path, "JPEG", quality=95)
            else: final_image.save(save_path, "PNG")
            self.status_label.config(text="저장 완료!"); messagebox.showinfo("성공", f"이미지를 저장했습니다.\n{save_path}")
        except Exception as e: messagebox.showerror("저장 오류", f"파일 저장 중 오류 발생:\n{e}"); self.status_label.config(text="저장 실패.")

    def _reset_grid(self) -> None:
        for row in self.grid_vars:
            for var in row: var.set(False)
        self.status_label.config(text="그리드 선택이 초기화되었습니다.")

    def _remove_background(self, path: str) -> None:
        item = next((i for i in self.uploaded_images if i['path'] == path), None)
        if not item: return
        self.status_label.config(text=f"'{os.path.basename(path)}' 배경 제거 중..."); self.update_idletasks()
        try:
            removed_pil = remove(item['pil_img_save'])
            tight_bbox = removed_pil.getbbox()
            
            if tight_bbox:
                final_pil = removed_pil.crop(tight_bbox)
            else:
                final_pil = removed_pil
            
            item['pil_img_save'] = final_pil
            item.update({'crop_box': None, 'angle': 0.0})

            display_img = final_pil.copy()
            display_img.thumbnail(self.DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
            item['pil_img_display'] = display_img
            
            new_thumb = display_img.copy()
            new_thumb.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            item['thumb_img'] = ImageTk.PhotoImage(new_thumb)
            
            self._populate_uploaded_images_list()
            if path in self.canvas_objects:
                self.canvas_objects[path]['pil_img_original'] = display_img
                self._update_object_display(path)
                
            self.status_label.config(text=f"'{os.path.basename(path)}' 배경 제거 완료!")
        except Exception as e:
            messagebox.showerror("오류", f"배경 제거 중 오류 발생: {e}")
            self.status_label.config(text="배경 제거 실패.")
    
    def _apply_grid_layout(self):
        images = [i for i in self.uploaded_images if i.get('var').get() and i.get('type')=='image']
        if not images: return messagebox.showinfo("알림", "캔버스에 배치할 이미지가 없습니다. (레이어 체크 확인)")
        canvas_w, canvas_h = int(self.canvas.cget("width")), int(self.canvas.cget("height")); actual_zoom = self.fit_scale * (self.zoom_var.get() / 100.0)
        logo_zone_h = self.output_height_var.get() * (self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT) * actual_zoom
        work_w, work_h, work_y_start = canvas_w, canvas_h - logo_zone_h, logo_zone_h
        checked = sorted([(r,c) for r,row in enumerate(self.grid_vars) for c,v in enumerate(row) if v.get()])
        if not checked:
            rows = int(math.sqrt(len(images))) or 1; cols = math.ceil(len(images) / rows)
            start_r, start_c = (self.GRID_SIZE-rows)//2, (self.GRID_SIZE-cols)//2
            dests = [(start_r+i//cols, start_c+i%cols) for i in range(len(images))]
        else:
            dests = checked
            if len(images) > len(checked) and len(checked) > 1:
                dr, dc = checked[-1][0]-checked[-2][0], checked[-1][1]-checked[-2][1]; last_r, last_c = checked[-1]
                for _ in range(len(images) - len(checked)): last_r, last_c = last_r+dr, last_c+dc; dests.append((last_r, last_c))
        image_data = [{'item': img, 'grid_r': r, 'grid_c': c} for img, (r, c) in zip(images, dests)]
        if not image_data: return
        min_r, min_c = min(d['grid_r'] for d in image_data), min(d['grid_c'] for d in image_data); spacing = (100-self.grid_overlap_var.get())/100.0
        low, high, optimal_scale = 10.0, 500.0, 10.0
        for _ in range(25):
            scale = (low + high) / 2
            test_sizes = [self._get_display_pil(d['item'], scale, actual_zoom) for d in image_data]
            if not any(s for s in test_sizes if s): high = scale; continue
            avg_w = sum(s.width for s in test_sizes if s) / len([s for s in test_sizes if s]); avg_h = sum(s.height for s in test_sizes if s) / len([s for s in test_sizes if s])
            placements = [{'x':(d['grid_c']-min_c)*avg_w*spacing, 'y':(d['grid_r']-min_r)*avg_h*spacing, 'w':s.width, 'h':s.height} for d, s in zip(image_data, test_sizes) if s]
            if not placements: high=scale; continue
            min_x, max_x = min(p['x']-p['w']/2 for p in placements), max(p['x']+p['w']/2 for p in placements)
            min_y, max_y = min(p['y']-p['h']/2 for p in placements), max(p['y']+p['h']/2 for p in placements)
            if (max_x - min_x) < work_w and (max_y - min_y) < work_h: optimal_scale = scale; low = scale
            else: high = scale
        self.global_scale_var.set(round(optimal_scale, 1)); self._apply_global_scale(target_paths=[img['path'] for img in images]); self.update_idletasks()
        scaled_data = [{'obj': self.canvas_objects[d['item']['path']], 'w': self.canvas_objects[d['item']['path']]['tk_img'].width(), 'h': self.canvas_objects[d['item']['path']]['tk_img'].height(), 'grid_r': d['grid_r'], 'grid_c': d['grid_c']} for d in image_data if d['item']['path'] in self.canvas_objects]
        if not scaled_data: return
        avg_w = sum(s['w'] for s in scaled_data)/len(scaled_data); avg_h = sum(s['h'] for s in scaled_data)/len(scaled_data)
        placements = [{'obj': s['obj'], 'x': (s['grid_c']-min_c)*avg_w*spacing, 'y': (s['grid_r']-min_r)*avg_h*spacing, 'w':s['w'], 'h':s['h']} for s in scaled_data]
        min_x, max_x = min(p['x']-p['w']/2 for p in placements), max(p['x']+p['w']/2 for p in placements)
        min_y, max_y = min(p['y']-p['h']/2 for p in placements), max(p['y']+p['h']/2 for p in placements)
        offset_x, offset_y = work_w/2 - (min_x+(max_x-min_x)/2), (work_y_start + work_h/2) - (min_y+(max_y-min_y)/2)
        for p in placements:
            final_x, final_y = p['x']+offset_x, p['y']+offset_y
            final_x = max(p['w']/2, min(final_x, work_w-p['w']/2)); final_y = max(work_y_start+p['h']/2, min(final_y, canvas_h-p['h']/2))
            self.canvas.coords(p['obj']['id'], final_x, final_y); p['obj']['rel_x'], p['obj']['rel_y'] = final_x/canvas_w, final_y/canvas_h
        self.status_label.config(text=f"자동 배치 완료 (크기: {optimal_scale:.1f}%, 겹침: {self.grid_overlap_var.get()}%)")

    def _get_display_pil(self, item, scale, actual_zoom, is_logo=False, rotate=True):
        pil_img = item['pil_img_display']
        cropped_img = pil_img.crop(item.get('crop_box')) if item.get('crop_box') else pil_img
        if cropped_img.width == 0 or cropped_img.height == 0: return None
        canvas_h_for_calc = self.output_height_var.get()
        if is_logo: target_h = canvas_h_for_calc * (self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT) * (scale / 100.0)
        else:
            logo_zone_h = canvas_h_for_calc * (self.logo_zone_height_var.get() / self.REFERENCE_CANVAS_HEIGHT)
            target_h = (canvas_h_for_calc - logo_zone_h) * (scale / 100.0)
        ratio = target_h / cropped_img.height if cropped_img.height > 0 else 0
        new_w, new_h = int(cropped_img.width * ratio), int(target_h)
        display_w, display_h = int(new_w * actual_zoom), int(new_h * actual_zoom)
        if display_w < 1 or display_h < 1: return None
        resized = cropped_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        return resized.rotate(item.get('angle',0.0), expand=True, resample=Image.Resampling.BICUBIC) if rotate else resized

    def _clear_resize_handles(self): self.canvas.delete("handle"); self.canvas.delete("rotate_handle")

    def _draw_resize_handles(self, path):
        self._clear_resize_handles(); self.active_selection_path = path
        obj = self.canvas_objects.get(path)
        if not obj: return
        
        item = next((i for i in self.uploaded_images if i['path'] == path), None)
        is_rotatable = item is not None
        
        bbox = self.canvas.bbox(obj['id'])
        if not bbox: return
        x0, y0, x1, y1 = bbox
        
        center_x, center_y = (x0+x1)/2, (y0+y1)/2
        angle = item.get('angle', 0.0) if item else 0.0

        w, h = x1-x0, y1-y0
        unrotated_corners = [center_x-w/2, center_y-h/2, center_x+w/2, center_y-h/2, 
                             center_x+w/2, center_y+h/2, center_x-w/2, center_y+h/2]
        
        rotated_poly_points = self._rotate_points(unrotated_corners, (center_x, center_y), angle)
        
        self.canvas.create_polygon(rotated_poly_points, outline="blue", width=1, tags="handle", fill="",)
        
        x0r, y0r, x1r, y1r, x2r, y2r, x3r, y3r = rotated_poly_points
        coords = [(x0r, y0r, "nw"), (x1r, y1r, "ne"), (x2r, y2r, "se"), (x3r, y3r, "sw")]
        
        h_size = 8; cursors = {"nw": "size_nw_se", "ne": "size_ne_sw", "sw": "size_ne_sw", "se": "size_nw_se"}
        for x, y, c_type in coords:
            self.canvas.create_rectangle(x-h_size/2, y-h_size/2, x+h_size/2, y+h_size/2, fill="blue", outline="white", width=1, tags=("handle", c_type))
            self.canvas.tag_bind(c_type, "<Enter>", lambda e, c=cursors[c_type]: self._on_handle_enter(e, c))
            self.canvas.tag_bind(c_type, "<Leave>", self._on_handle_leave)

        if is_rotatable:
            rh_offset = h_size * 2.5; rh_size = h_size
            
            unrotated_rot_handle_corners = [
                center_x - w/2 - rh_offset, center_y - h/2 - rh_offset,
                center_x + w/2 + rh_offset, center_y - h/2 - rh_offset,
                center_x - w/2 - rh_offset, center_y + h/2 + rh_offset,
                center_x + w/2 + rh_offset, center_y + h/2 + rh_offset
            ]
            rotated_rot_handle_points = self._rotate_points(unrotated_rot_handle_corners, (center_x, center_y), angle)
            rot_coords = list(zip(rotated_rot_handle_points[0::2], rotated_rot_handle_points[1::2]))

            for x, y in rot_coords:
                self.canvas.create_oval(x-rh_size/2, y-rh_size/2, x+rh_size/2, y+rh_size/2, fill="orange", outline="white", width=1, tags="rotate_handle")
            self.canvas.tag_bind("rotate_handle", "<Enter>", lambda e: self._on_handle_enter(e, "exchange"))
            self.canvas.tag_bind("rotate_handle", "<Leave>", self._on_handle_leave)

    def _on_handle_enter(self, event, cursor_name):
        if self._resize_data or self._rotation_data: return
        self.canvas.config(cursor=cursor_name)
        
    def _on_handle_leave(self, event):
        if self._resize_data or self._rotation_data: return
        self.canvas.config(cursor="")