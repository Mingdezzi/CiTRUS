# 파일 경로: ui/easel_tab.py (이 코드로 완전히 교체하세요)

import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import os
import re

from controllers.main_controller import MainController
from controllers.canvas_controller import CanvasController
from controllers.event_handler import EventHandler
from ui.components.layer_list import LayerList

# --- 라이브러리 가용성 확인 ---
try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


class EaselTab(ttk.Frame):
    GRID_SIZE = 7

    def __init__(self, parent: tk.Misc, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # 컨트롤러 초기화
        self.controller = MainController(self)
        # 그리드 UI 상태 변수 (View가 가지고 있음)
        self.grid_vars = [[tk.BooleanVar(value=False) for _ in range(self.GRID_SIZE)] for _ in range(self.GRID_SIZE)]

        self._build_ui()
        
        # 컨트롤러와 이벤트 핸들러에 위젯 참조 전달
        self.canvas_controller = CanvasController(self.canvas, self.controller)
        self.event_handler = EventHandler(self.controller, self.canvas, self.canvas_controller)
        
        # 컨트롤러에 UI 참조 전달 (로고 미리보기 업데이트용)
        self.controller.set_ui_references(self.logo_preview_label, self.status_label)

        # 변수 변경 감지 (Trace)
        self.controller.settings['background_color'].trace_add("write", self._on_background_color_change)
        self.controller.settings['palette_color'].trace_add("write", self._on_palette_color_change)
        self.controller.settings['zoom'].trace_add("write", self._on_zoom_change)
        self.controller.settings['logo_path'].trace_add("write", lambda *args: self.controller.update_logo_preview())
        self.controller.settings['logo_zone_height'].trace_add("write", self._on_logo_zone_change)
        self.controller.settings['logo_size'].trace_add("write", lambda *args: self.controller.update_logo_object_display())


        self._on_palette_color_change() # 초기 색상 설정
        self.viewport_frame.bind("<Configure>", self._update_canvas_view)
        # 로고 패널 미리보기를 위한 초기 바인딩
        self.logo_preview_label.bind("<Configure>", lambda e: self.controller.update_logo_preview())


    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        content_frame = ttk.Frame(self)
        content_frame.pack(side="top", fill="both", expand=True) 
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=0)
        content_frame.grid_rowconfigure(0, weight=1)

        canvas_container = self._create_canvas_panel(content_frame)
        control_panel = self._create_control_panel(content_frame)
        canvas_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        control_panel.grid(row=0, column=1, sticky="ns", padx=(5, 0))
        
        bottom_frame = self._create_bottom_bar()
        bottom_frame.pack(side="bottom", fill="x", padx=5, pady=2)


    def _create_canvas_panel(self, parent: ttk.Frame) -> ttk.Frame:
        container = ttk.LabelFrame(parent, text="Canvas", bootstyle="primary")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        
        self.viewport_frame = ttk.Frame(container)
        self.viewport_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.viewport_frame.grid_rowconfigure(0, weight=1)
        self.viewport_frame.grid_columnconfigure(0, weight=1)

        self.viewport = tk.Canvas(self.viewport_frame, bd=0, highlightthickness=0, bg=ttk.Style().colors.light)
        v_scroll = ttk.Scrollbar(self.viewport_frame, orient=VERTICAL, command=self.viewport.yview, bootstyle="round")
        h_scroll = ttk.Scrollbar(self.viewport_frame, orient=HORIZONTAL, command=self.viewport.xview, bootstyle="round")
        self.viewport.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.viewport.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas = tk.Canvas(self.viewport, bg=self.controller.settings['background_color'].get(), highlightthickness=0)
        self.canvas_window_id = self.viewport.create_window((0, 0), window=self.canvas, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.viewport.config(scrollregion=self.viewport.bbox("all")))

        zoom_frame = self._create_zoom_panel(container)
        zoom_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 0))
        return container
        
    def _create_zoom_panel(self, parent: ttk.Frame) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=5)
        ttk.Label(frame, text="확대/축소:").pack(side=LEFT, padx=(5, 2))
        scale = ttk.Scale(frame, from_=50, to=200, variable=self.controller.settings['zoom'])
        scale.pack(side=LEFT, fill=X, expand=YES)
        
        zoom_label = ttk.Label(frame, text="100%", width=5)
        zoom_label.pack(side=LEFT, padx=(2, 5))
        def update_zoom_label(value): zoom_label.config(text=f"{int(float(value))}%")
        self.controller.settings['zoom'].trace_add("write", lambda *args: update_zoom_label(self.controller.settings['zoom'].get()))
        return frame

    def _create_control_panel(self, parent: ttk.Frame) -> ttk.Frame:
        container = ttk.Frame(parent)
        container.rowconfigure(0, weight=1)
        
        left_column = ttk.Frame(container)
        left_column.grid(row=0, column=0, sticky="ns", padx=(0, 3))
        left_column.rowconfigure(1, weight=1) 
        
        right_column = ttk.Frame(container)
        right_column.grid(row=0, column=1, sticky="ns")
        right_column.rowconfigure(0, weight=1) # 로고 패널이 늘어나도록

        # --- 누락되었던 패널 호출 추가 ---
        self._create_canvas_settings_panel(left_column).grid(row=0, column=0, sticky="ew")
        self._create_layer_panel(left_column).grid(row=1, column=0, sticky="nsew", pady=(5,0))
        self._create_project_settings_panel(left_column).grid(row=2, column=0, sticky="ew", pady=(5,0))
        
        self._create_logo_panel(right_column).grid(row=0, column=0, sticky='nsew')
        self._create_decoration_panel(right_column).grid(row=1, column=0, sticky='ew', pady=(5,0))
        self._create_auto_layout_panel(right_column).grid(row=2, column=0, sticky='ew', pady=(5,0))
        self._create_image_output_panel(right_column).grid(row=3, column=0, sticky='ew', pady=(5,0))
        # --- 수정 끝 ---
        return container

    def _create_canvas_settings_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Setting >", bootstyle="info")
        res_frame = ttk.Frame(frame, padding=3)
        res_frame.pack(fill="x")
        ttk.Label(res_frame, text="해상도 (가로x세로):").pack(anchor="w")
        inputs_frame = ttk.Frame(res_frame)
        inputs_frame.pack(fill=X, pady=2)
        ttk.Spinbox(inputs_frame, from_=100, to=8000, textvariable=self.controller.settings['output_width'], width=6).pack(side=LEFT, expand=YES, fill=X, padx=(0, 2))
        ttk.Label(inputs_frame, text="x").pack(side=LEFT)
        ttk.Spinbox(inputs_frame, from_=100, to=8000, textvariable=self.controller.settings['output_height'], width=6).pack(side=LEFT, expand=YES, fill=X, padx=(2, 3))
        ttk.Button(inputs_frame, text="적용", command=self._apply_resolution, bootstyle="secondary", width=5).pack(side=LEFT)
        return frame

    # --- 누락되었던 UI 생성 함수 추가 ---
    def _create_logo_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Logo >", bootstyle="info")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1) # 미리보기 영역이 늘어나도록
        
        logo_preview_container = ttk.Frame(frame)
        logo_preview_container.pack(fill="both", expand=True, padx=3, pady=3)
        
        self.logo_preview_label = ttk.Label(logo_preview_container, text="로고 없음\n(파일을 여기로 드래그)", anchor="center", bootstyle="light")
        self.logo_preview_label.pack(fill="both", expand=True)
        
        if DND_AVAILABLE:
            self.logo_preview_label.drop_target_register(DND_FILES)
            self.logo_preview_label.dnd_bind("<<Drop>>", self.controller.on_logo_panel_drop)

        logo_btn_frame = ttk.Frame(frame)
        logo_btn_frame.pack(fill="x", padx=3, pady=(0, 3)) 
        ttk.Button(logo_btn_frame, text="로고 선택", command=self.controller.select_logo, bootstyle="secondary", width=15).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(logo_btn_frame, text="로고 삭제", command=self.controller.delete_logo, bootstyle="danger", width=15).pack(side="left", fill="x", expand=True, padx=2)
        
        logo_controls_frame = ttk.Frame(frame)
        logo_controls_frame.pack(fill='x', padx=3, pady=2)
        logo_controls_frame.columnconfigure((0, 1), weight=1)
        
        logo_zone_frame = ttk.Frame(logo_controls_frame)
        logo_zone_frame.grid(row=0, column=0, sticky='w')
        ttk.Label(logo_zone_frame, text="구역 높이:").pack(side="left")
        ttk.Button(logo_zone_frame, text="-", width=2, command=lambda: self.controller.adjust_logo_zone(-10), bootstyle="secondary").pack(side="left", padx=(3,0))
        ttk.Label(logo_zone_frame, textvariable=self.controller.settings['logo_zone_height'], width=4, anchor="center").pack(side="left")
        ttk.Button(logo_zone_frame, text="+", width=2, command=lambda: self.controller.adjust_logo_zone(10), bootstyle="secondary").pack(side="left")

        logo_size_frame = ttk.Frame(logo_controls_frame)
        logo_size_frame.grid(row=0, column=1, sticky='e')
        ttk.Label(logo_size_frame, text="로고 크기:").pack(side="left")
        ttk.Button(logo_size_frame, text="-", width=2, command=lambda: self.controller.adjust_logo_size(-5), bootstyle="secondary").pack(side="left", padx=(3,0))
        ttk.Label(logo_size_frame, textvariable=self.controller.settings['logo_size'], width=4, anchor="center").pack(side="left")
        ttk.Button(logo_size_frame, text="+", width=2, command=lambda: self.controller.adjust_logo_size(5), bootstyle="secondary").pack(side="left")
        
        return frame
    # --- 누락되었던 UI 생성 함수 추가 ---
    def _create_auto_layout_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Automatic Placement >", bootstyle="info")
        container = ttk.Frame(frame, padding=3)
        container.pack(fill='x')
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=0)
        
        grid_inner_frame = ttk.Frame(container)
        grid_inner_frame.grid(row=0, column=0, sticky='ns')
        
        for r, row_vars in enumerate(self.grid_vars):
            for c, var in enumerate(row_vars):
                ttk.Checkbutton(grid_inner_frame, variable=var, bootstyle="primary").grid(row=r, column=c, padx=1, pady=1) 
        
        right_controls_frame = ttk.Frame(container)
        right_controls_frame.grid(row=0, column=1, sticky='ns', padx=(10,0))
        
        overlap_frame = ttk.Frame(right_controls_frame)
        overlap_frame.pack(fill="x", pady=3) 
        ttk.Label(overlap_frame, text="겹침(%):").pack(side="left")
        ttk.Spinbox(overlap_frame, from_=0, to=100, textvariable=self.controller.settings['grid_overlap'], width=5, increment=5).pack(side="left", padx=3)
        
        ttk.Button(right_controls_frame, text="배치 적용", command=self.controller.apply_grid_layout, bootstyle="primary").pack(fill='x', pady=2) 
        ttk.Button(right_controls_frame, text="초기화", command=self.controller.reset_grid, bootstyle="warning-outline").pack(fill='x', pady=2)
        return frame
    # --- 수정 끝 ---

    def _create_layer_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Layer >", bootstyle="info")
        
        top_controls = ttk.Frame(frame, padding=(3,3,3,0))
        top_controls.pack(fill='x')
        
        check_all_frame = ttk.Frame(top_controls)
        check_all_frame.pack(side='left', padx=(8, 0))
        self.check_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_all_frame, variable=self.check_all_var, command=self._toggle_all_checks).pack(side='left')
        
        self.select_all_button = ttk.Button(check_all_frame, text="전체선택", width=7, command=self.controller.toggle_all_layer_selection, bootstyle="secondary-outline")
        self.select_all_button.pack(side='left', padx=2)
        
        right_controls = ttk.Frame(top_controls)
        right_controls.pack(side='right')
        ttk.Label(right_controls, text="일괄 크기:").pack(side='left')
        ttk.Spinbox(right_controls, from_=10, to=500, textvariable=self.controller.settings['global_scale'], width=5, increment=5.0).pack(side='left', padx=3)
        ttk.Button(right_controls, text="적용", command=self.controller.apply_global_scale, bootstyle="primary", width=5).pack(side='left')
        
        action_buttons = ttk.Frame(frame, padding=3)
        action_buttons.pack(fill='x')
        action_buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(action_buttons, text="이미지 추가", command=self._add_files, bootstyle="secondary").grid(row=0, column=0, sticky="ew", padx=(0,2)) 
        ttk.Button(action_buttons, text="선택 삭제", command=self.controller.delete_selected_layers, bootstyle="danger").grid(row=0, column=1, sticky="ew", padx=(2,0)) 
        
        # LayerList 위젯 추가
        self.layer_list = LayerList(frame, self.controller)
        self.layer_list.pack(fill='both', expand=True)
        
        return frame

    def _create_project_settings_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Project >", bootstyle="info")
        btn_frame = ttk.Frame(frame, padding=3)
        btn_frame.pack(fill="x")
        btn_frame.columnconfigure((0,1), weight=1)
        ttk.Button(btn_frame, text="저장", command=self.controller.save_project, bootstyle="primary").grid(row=0, column=0, sticky="ew", padx=(0,2)) 
        ttk.Button(btn_frame, text="불러오기", command=self.controller.load_project, bootstyle="info").grid(row=0, column=1, sticky="ew", padx=(2,0)) 
        ttk.Button(frame, text="전체 초기화", command=self.controller.clear_all, bootstyle="danger").pack(fill="x", padx=3, pady=(0,3)) 
        return frame
        
    def _create_image_output_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Output Image >", bootstyle="info")
        inner = ttk.Frame(frame, padding=3)
        inner.pack(fill='both', expand=True)
        ttk.Label(inner, text="파일명:").pack(anchor="w")
        ttk.Entry(inner, textvariable=self.controller.settings['style_code'], justify="center").pack(fill="x", pady=(0,3))
        ttk.Label(inner, text="파일 형식:").pack(anchor="w")
        ttk.Combobox(inner, textvariable=self.controller.settings['output_format'], values=["PNG", "JPG"], state="readonly").pack(fill="x", pady=(0,3))
        ttk.Label(inner, text="저장 위치:").pack(anchor="w")
        ttk.Button(inner, text="폴더 선택", command=self._select_save_directory, bootstyle="secondary").pack(fill="x")
        ttk.Button(inner, text="이미지 저장", command=self.controller.save_image, bootstyle="primary").pack(fill="x", pady=(8,0)) 
        return frame
        
    def _create_decoration_panel(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="< Asset >", bootstyle="info")
        inner = ttk.Frame(frame, padding=5)
        inner.pack(fill='both', expand=True)
        
        add_frame = ttk.Frame(inner)
        add_frame.pack(fill='x')
        add_frame.columnconfigure((0,1), weight=1)
        ttk.Button(add_frame, text="텍스트 추가", command=self.controller.add_new_text_layer).grid(row=0, column=0, sticky='ew', padx=(0,1))
        ttk.Button(add_frame, text="도형 추가", command=self.controller.add_new_shape_layer).grid(row=0, column=1, sticky='ew', padx=(1,0))
        
        ttk.Separator(inner, orient=HORIZONTAL).pack(fill='x', pady=8)
        
        palette_frame = ttk.Frame(inner)
        palette_frame.pack(fill='x')
        self.palette_color_preview = tk.Canvas(palette_frame, width=30, height=28, highlightthickness=1, highlightbackground="gray", cursor="hand2")
        self.palette_color_preview.pack(side='left')
        self.palette_color_preview.bind("<Button-1>", self._choose_palette_color)
        ttk.Label(palette_frame, textvariable=self.controller.settings['palette_color'], width=8, anchor='center').pack(side='left', padx=5)
        ttk.Button(palette_frame, text="색상 추출", command=self._enter_color_pick_mode, bootstyle="secondary").pack(side='left', fill='x', expand=True)
        
        apply_frame = ttk.Frame(inner)
        apply_frame.pack(fill='x', pady=(8,0))
        apply_frame.columnconfigure((0,1), weight=1)
        ttk.Button(apply_frame, text="대상색상변경", command=lambda: print("TODO")).grid(row=0, column=0, sticky='ew', padx=(0,1))
        ttk.Button(apply_frame, text="배경색상변경", command=self._apply_color_to_background).grid(row=0, column=1, sticky='ew', padx=(1,0))
        
        return frame

    def _create_bottom_bar(self) -> ttk.Frame:
        frame = ttk.Frame(self)
        frame.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(frame, text="", bootstyle="secondary")
        self.status_label.grid(row=0, column=0, sticky="w")
        return frame
        
    # --- UI Event Handlers & Callbacks ---
    def update_status(self, text: str):
        self.status_label.config(text=text)

    def _on_background_color_change(self, *args):
        color = self.controller.settings['background_color'].get()
        if re.match(r'^#[0-9A-Fa-f]{6}$', color):
            self.canvas.configure(bg=color)

    def _on_palette_color_change(self, *args):
        new_color = self.controller.settings['palette_color'].get()
        if hasattr(self, 'palette_color_preview') and self.palette_color_preview.winfo_exists():
            self.palette_color_preview.config(bg=new_color)

    def _on_zoom_change(self, *args):
        zoom_level = self.controller.get_zoom()
        w, h = self.canvas_controller.get_canvas_size(zoom_level)
        self.canvas.config(width=w, height=h)
        self.canvas_controller.update_all_objects_display(zoom_level)
        self._center_canvas_in_viewport()

    def _on_logo_zone_change(self, *args):
        # 로고 구역이 변경되면 모든 객체를 다시 그려야 할 수 있음 (특히 로고)
        self.controller.update_logo_object_display()
        # TODO: 로고 외 다른 객체들의 위치도 재계산이 필요하다면 여기에 추가
        
    def _update_canvas_view(self, event=None):
        w, h = self.viewport_frame.winfo_width(), self.viewport_frame.winfo_height()
        if w <= 1 or h <= 1: return
        
        logical_w = self.controller.settings['output_width'].get()
        logical_h = self.controller.settings['output_height'].get()
        if logical_w <= 0 or logical_h <= 0: return

        scale_x = (w * 0.9) / logical_w
        scale_y = (h * 0.9) / logical_h
        self.canvas_controller.fit_scale = min(scale_x, scale_y)
        self._on_zoom_change()

    def _center_canvas_in_viewport(self):
        self.viewport.update_idletasks()
        vp_w, vp_h = self.viewport.winfo_width(), self.viewport.winfo_height()
        cv_w, cv_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
        x, y = max(0, (vp_w - cv_w) // 2), max(0, (vp_h - cv_h) // 2)
        self.viewport.coords(self.canvas_window_id, x, y)
    
    def _add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if files:
            self.controller.add_new_image_layers(files)

    def _apply_resolution(self):
        self.controller.settings['zoom'].set(100)
        self._update_canvas_view()
    
    def _toggle_all_checks(self):
        is_checked = self.check_all_var.get()
        for layer in self.controller.get_layers():
            layer.is_visible.set(is_checked)
            self.controller.toggle_layer_visibility(layer)

    def _select_save_directory(self):
        directory = filedialog.askdirectory(initialdir=self.controller.settings['save_directory'].get())
        if directory:
            self.controller.settings['save_directory'].set(directory)
            messagebox.showinfo("저장 위치", f"기본 저장 위치가\n'{directory}'\n(으)로 설정되었습니다.")
    
    def _choose_palette_color(self, event=None):
        color = self.controller.settings['palette_color'].get()
        new_color = colorchooser.askcolor(title="팔레트 색상 선택", initialcolor=color)
        if new_color[1]:
            self.controller.settings['palette_color'].set(new_color[1].upper())
            
    def _apply_color_to_background(self):
        color = self.controller.settings['palette_color'].get()
        self.controller.settings['background_color'].set(color)
        self.update_status(f"배경색 변경 완료: {color}")
        
    def _enter_color_pick_mode(self):
        self.controller.is_color_picking_mode = True
        self.canvas.config(cursor="crosshair")
        self.update_status("🎨 캔버스 위의 항목을 클릭하여 색상을 추출하세요.")
        
    def update_select_all_button_state(self):
        if not hasattr(self, 'select_all_button') or not self.select_all_button.winfo_exists():
            return
            
        layers = self.controller.get_layers()
        if layers and all(l.selected for l in layers):
            self.select_all_button.config(text="선택해제", bootstyle="secondary")
        else:
            self.select_all_button.config(text="전체선택", bootstyle="secondary-outline")