# 파일 경로: tabs/easel/easel_tab_view.py (Restore 9x9 Grid + Linear)

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox, colorchooser
import os
import re
import tkinter.scrolledtext as tkst
# import math # math 모듈 더 이상 필요 없음

from .easel_controller import EaselController
from .canvas_controller import CanvasController
from .event_handler import EventHandler
from .components.layer_list import LayerList
from ui.theme import Colors

try: from tkinterdnd2 import DND_FILES; DND_AVAILABLE = True
except ImportError: DND_AVAILABLE = False

class EaselTabView(tk.Frame):
    # [ ★★★★★ MODIFIED: GRID_SIZE 9로 변경 ★★★★★ ]
    GRID_SIZE = 9

    def __init__(self, parent: tk.Misc, *args, **kwargs):
        super().__init__(parent, *args, bg=Colors.WHITE, **kwargs)
        self.controller = EaselController(self)
        # [ ★★★★★ RESTORED: grid_vars 초기화 (9x9) ★★★★★ ]
        self.grid_vars = [[tk.BooleanVar(value=False) for _ in range(self.GRID_SIZE)] for _ in range(self.GRID_SIZE)]
        self._build_ui()
        self.canvas_controller = CanvasController(self.canvas, self.controller)
        self.event_handler = EventHandler(self.controller, self.canvas, self.canvas_controller, self) # view 전달
        self.controller.set_ui_references(self.logo_preview_label, self.status_label)
        self.controller.settings['background_color'].trace_add("write", self._on_background_color_change)
        self.controller.settings['palette_color'].trace_add("write", self._on_palette_color_change)
        self.controller.settings['zoom'].trace_add("write", self._on_zoom_change)
        self.controller.settings['logo_path'].trace_add("write", lambda *args: self.controller.update_logo_preview())
        self.controller.settings['logo_zone_height'].trace_add("write", self._on_logo_zone_change)
        self.controller.settings['logo_size'].trace_add("write", lambda *args: self.controller.update_logo_object_display())

        # --- 각도 관련 trace 제거됨 ---

        self._on_palette_color_change()
        self.viewport_frame.bind("<Configure>", self._update_canvas_view)
        self.logo_preview_label.bind("<Configure>", lambda e: self.controller.update_logo_preview())

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=0)
        content_frame = tk.Frame(self, bg=Colors.WHITE); content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
        content_frame.grid_columnconfigure(0, weight=1); content_frame.grid_columnconfigure(1, weight=0); content_frame.grid_rowconfigure(0, weight=1)
        canvas_container = self._create_canvas_panel(content_frame)
        control_panel = self._create_control_panel(content_frame)
        canvas_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        control_panel.grid(row=0, column=1, sticky="ns", padx=(5, 0))
        bottom_frame = self._create_bottom_bar(); bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

    # --- _create_canvas_panel, _create_zoom_panel (변경 없음) ---
    def _create_canvas_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        container = tk.LabelFrame(parent, text="Canvas", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=5, pady=5)
        container.rowconfigure(0, weight=1); container.columnconfigure(0, weight=1)
        self.viewport_frame = tk.Frame(container, bg=Colors.WHITE); self.viewport_frame.grid(row=0, column=0, sticky="nsew")
        self.viewport_frame.grid_rowconfigure(0, weight=1); self.viewport_frame.grid_columnconfigure(0, weight=1)
        self.viewport = tk.Canvas(self.viewport_frame, bd=0, highlightthickness=0, bg=Colors.WHITE)
        v_scroll = ttk.Scrollbar(self.viewport_frame, orient=tk.VERTICAL, command=self.viewport.yview)
        h_scroll = ttk.Scrollbar(self.viewport_frame, orient=tk.HORIZONTAL, command=self.viewport.xview)
        self.viewport.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.viewport.grid(row=0, column=0, sticky="nsew"); v_scroll.grid(row=0, column=1, sticky="ns"); h_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas = tk.Canvas(self.viewport, bg=self.controller.settings['background_color'].get(), highlightthickness=0)
        self.canvas_window_id = self.viewport.create_window((0, 0), window=self.canvas, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.viewport.config(scrollregion=self.viewport.bbox("all")))
        zoom_frame = self._create_zoom_panel(container); zoom_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        return container

    def _create_zoom_panel(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=Colors.WHITE, pady=5)
        tk.Label(frame, text="확대/축소:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT, padx=(0, 2))
        scale = tk.Scale(frame, from_=50, to=200, variable=self.controller.settings['zoom'], orient=tk.HORIZONTAL, bg=Colors.WHITE, fg=Colors.DARK_TEAL, highlightthickness=0, bd=0, sliderlength=15, length=100, troughcolor=Colors.GREY)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)
        zoom_label = tk.Label(frame, text="100%", width=5, bg=Colors.WHITE, fg=Colors.DARK_TEAL); zoom_label.pack(side=tk.LEFT, padx=(2, 0))
        def update_zoom_label(value): zoom_label.config(text=f"{int(float(value))}%")
        self.controller.settings['zoom'].trace_add("write", lambda *args: update_zoom_label(self.controller.settings['zoom'].get()))
        return frame

    def _create_control_panel(self, parent: tk.Frame) -> tk.Frame:
        container = tk.Frame(parent, bg=Colors.WHITE); container.rowconfigure(0, weight=1)
        left_column = tk.Frame(container, bg=Colors.WHITE); left_column.grid(row=0, column=0, sticky="ns", padx=(0, 3)); left_column.rowconfigure(1, weight=1)
        right_column = tk.Frame(container, bg=Colors.WHITE); right_column.grid(row=0, column=1, sticky="ns"); right_column.rowconfigure(0, weight=1)
        self._create_canvas_settings_panel(left_column).grid(row=0, column=0, sticky="ew")
        self._create_layer_panel(left_column).grid(row=1, column=0, sticky="nsew", pady=(5,0))
        self._create_project_settings_panel(left_column).grid(row=2, column=0, sticky="ew", pady=(5,0))
        self._create_logo_panel(right_column).grid(row=0, column=0, sticky='nsew')
        self._create_decoration_panel(right_column).grid(row=1, column=0, sticky='ew', pady=(5,0))
        # [ ★★★★★ MODIFIED: 그리드 패널과 직선 패널 모두 추가 ★★★★★ ]
        self._create_grid_layout_panel(right_column).grid(row=2, column=0, sticky='ew', pady=(5,0)) # 그리드 패널 추가
        self._create_linear_layout_panel(right_column).grid(row=3, column=0, sticky='ew', pady=(5,0)) # 직선 패널 추가 (row=3)
        self._create_image_output_panel(right_column).grid(row=4, column=0, sticky='ew', pady=(5,0)) # 이미지 출력 패널 (row=4)
        return container

    # --- _create_canvas_settings_panel, _create_logo_panel (변경 없음) ---
    def _create_canvas_settings_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        frame = tk.LabelFrame(parent, text="< Setting >", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=3, pady=3)
        res_frame = tk.Frame(frame, bg=Colors.WHITE); res_frame.pack(fill=tk.X)
        tk.Label(res_frame, text="해상도 (가로x세로):", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(anchor=tk.W)
        inputs_frame = tk.Frame(res_frame, bg=Colors.WHITE); inputs_frame.pack(fill=tk.X, pady=2)
        tk.Spinbox(inputs_frame, from_=100, to=8000, textvariable=self.controller.settings['output_width'], width=6).pack(side=tk.LEFT, expand=tk.YES, fill=tk.X, padx=(0, 2))
        tk.Label(inputs_frame, text="x", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT)
        tk.Spinbox(inputs_frame, from_=100, to=8000, textvariable=self.controller.settings['output_height'], width=6).pack(side=tk.LEFT, expand=tk.YES, fill=tk.X, padx=(2, 3))
        tk.Button(inputs_frame, text="적용", command=self._apply_resolution, width=5, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side=tk.LEFT)
        return frame

    def _create_logo_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        frame = tk.LabelFrame(parent, text="< Logo >", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=3, pady=3)
        frame.columnconfigure(0, weight=1); frame.rowconfigure(0, weight=1)
        logo_preview_container = tk.Frame(frame, bg=Colors.GREY); logo_preview_container.pack(fill=tk.BOTH, expand=True, pady=(0,3))
        self.logo_preview_label = tk.Label(logo_preview_container, text="로고 없음\n(파일을 여기로 드래그)", anchor=tk.CENTER, bg=Colors.GREY, fg=Colors.WHITE); self.logo_preview_label.pack(fill=tk.BOTH, expand=True)
        if DND_AVAILABLE: self.logo_preview_label.drop_target_register(DND_FILES); self.logo_preview_label.dnd_bind("<<Drop>>", self.controller.on_logo_panel_drop)
        logo_btn_frame = tk.Frame(frame, bg=Colors.WHITE); logo_btn_frame.pack(fill=tk.X, pady=(0, 3))
        tk.Button(logo_btn_frame, text="로고 선택", command=self.controller.select_logo, width=15, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,1))
        tk.Button(logo_btn_frame, text="로고 삭제", command=self.controller.delete_logo, width=15, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(1,0))
        logo_controls_frame = tk.Frame(frame, bg=Colors.WHITE); logo_controls_frame.pack(fill=tk.X, pady=2); logo_controls_frame.columnconfigure((0, 1), weight=1)
        logo_zone_frame = tk.Frame(logo_controls_frame, bg=Colors.WHITE); logo_zone_frame.grid(row=0, column=0, sticky='w')
        tk.Label(logo_zone_frame, text="구역 높이:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT)
        tk.Button(logo_zone_frame, text="-", width=2, command=lambda: self.controller.adjust_logo_zone(-10), bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side=tk.LEFT, padx=(3,0))
        tk.Label(logo_zone_frame, textvariable=self.controller.settings['logo_zone_height'], width=4, anchor=tk.CENTER, bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT)
        tk.Button(logo_zone_frame, text="+", width=2, command=lambda: self.controller.adjust_logo_zone(10), bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side=tk.LEFT)
        logo_size_frame = tk.Frame(logo_controls_frame, bg=Colors.WHITE); logo_size_frame.grid(row=0, column=1, sticky='e')
        tk.Label(logo_size_frame, text="로고 크기:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT)
        tk.Button(logo_size_frame, text="-", width=2, command=lambda: self.controller.adjust_logo_size(-5), bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side=tk.LEFT, padx=(3,0))
        tk.Label(logo_size_frame, textvariable=self.controller.settings['logo_size'], width=4, anchor=tk.CENTER, bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT)
        tk.Button(logo_size_frame, text="+", width=2, command=lambda: self.controller.adjust_logo_size(5), bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side=tk.LEFT)
        return frame

    # [ ★★★★★ RESTORED & MODIFIED: 9x9 그리드 UI 생성 함수 ★★★★★ ]
    def _create_grid_layout_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        frame = tk.LabelFrame(parent, text="< Grid Placement >", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=3, pady=3)
        container = tk.Frame(frame, bg=Colors.WHITE); container.pack(fill=tk.X); container.columnconfigure(0, weight=1);
        container.columnconfigure(1, weight=0)
        grid_inner_frame = tk.Frame(container, bg=Colors.WHITE);
        grid_inner_frame.grid(row=0, column=0, sticky='ns')
        # 9x9 그리드 생성
        for r, row_vars in enumerate(self.grid_vars):
            for c, var in enumerate(row_vars):
                cb = tk.Checkbutton(grid_inner_frame, variable=var, bg=Colors.WHITE, activebackground=Colors.WHITE, selectcolor=Colors.WHITE, relief=tk.FLAT, bd=0);
                # 패딩 조정하여 더 작게 보이도록
                cb.grid(row=r, column=c, padx=0, pady=0)
        right_controls_frame = tk.Frame(container, bg=Colors.WHITE);
        right_controls_frame.grid(row=0, column=1, sticky='ns', padx=(10,0))
        overlap_frame = tk.Frame(right_controls_frame, bg=Colors.WHITE);
        overlap_frame.pack(fill=tk.X, pady=3)
        tk.Label(overlap_frame, text="겹침(%):", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT)
        tk.Spinbox(overlap_frame, from_=0, to=100, textvariable=self.controller.settings['grid_overlap'], width=5, increment=5).pack(side=tk.LEFT, padx=3)
        # command 수정
        tk.Button(right_controls_frame, text="그리드 배치", command=self.controller.apply_grid_layout, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).pack(fill=tk.X, pady=2)
        tk.Button(right_controls_frame, text="그리드 초기화", command=self.controller.reset_grid, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(fill=tk.X, pady=2)
        return frame

    # [ ★★★★★ RENAMED & MODIFIED: 직선 배치 UI ★★★★★ ]
    def _create_linear_layout_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        frame = tk.LabelFrame(parent, text="< Linear Placement >", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=5, pady=5)

        # 직선 배치 시작 버튼
        self.linear_layout_button = tk.Button(frame, text="직선 배치 시작",
                                              command=self.controller.start_linear_placement_mode, # 컨트롤러 함수 연결
                                              bg=Colors.DARK_TEAL, fg=Colors.WHITE, relief=tk.FLAT,
                                              activebackground=Colors.DARK_TEAL_ACTIVE)
        self.linear_layout_button.pack(fill=tk.X, pady=(5, 5))

        return frame

    # --- _create_layer_panel, _create_project_settings_panel 등 (변경 없음) ---
    def _create_layer_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        frame = tk.LabelFrame(parent, text="< Layer >", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=3, pady=3)
        top_controls = tk.Frame(frame, bg=Colors.WHITE); top_controls.pack(fill=tk.X)
        check_all_frame = tk.Frame(top_controls, bg=Colors.WHITE); check_all_frame.pack(side=tk.LEFT, padx=(8, 0))
        self.check_all_var = tk.BooleanVar(value=False)
        tk.Checkbutton(check_all_frame, variable=self.check_all_var, command=self._toggle_all_checks, bg=Colors.WHITE, activebackground=Colors.WHITE, selectcolor=Colors.MAIN_RED, relief=tk.FLAT, bd=0).pack(side=tk.LEFT)
        self.select_all_button = tk.Button(check_all_frame, text="전체선택", width=7, command=self.controller.toggle_all_layer_selection, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY); self.select_all_button.pack(side=tk.LEFT, padx=2)
        right_controls = tk.Frame(top_controls, bg=Colors.WHITE); right_controls.pack(side=tk.RIGHT)
        tk.Label(right_controls, text="일괄 크기:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT)
        tk.Spinbox(right_controls, from_=10, to=500, textvariable=self.controller.settings['global_scale'], width=5, increment=5.0).pack(side=tk.LEFT, padx=3)
        tk.Button(right_controls, text="적용", command=self.controller.apply_global_scale, width=5, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).pack(side=tk.LEFT)
        action_buttons = tk.Frame(frame, bg=Colors.WHITE, pady=3); action_buttons.pack(fill=tk.X); action_buttons.columnconfigure((0, 1), weight=1)
        tk.Button(action_buttons, text="이미지 추가", command=self._add_files, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).grid(row=0, column=0, sticky="ew", padx=(0,1))
        tk.Button(action_buttons, text="선택 삭제", command=self.controller.delete_selected_layers, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).grid(row=0, column=1, sticky="ew", padx=(1,0))
        self.layer_list = LayerList(frame, self.controller); self.layer_list.pack(fill=tk.BOTH, expand=True, pady=(0,3))
        return frame

    def _create_project_settings_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        frame = tk.LabelFrame(parent, text="< Project >", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=3, pady=3)
        btn_frame = tk.Frame(frame, bg=Colors.WHITE); btn_frame.pack(fill=tk.X); btn_frame.columnconfigure((0,1), weight=1)
        tk.Button(btn_frame, text="저장", command=self.controller.save_project, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).grid(row=0, column=0, sticky="ew", padx=(0,1))
        tk.Button(btn_frame, text="불러오기", command=self.controller.load_project, bg=Colors.DARK_TEAL, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_TEAL_ACTIVE).grid(row=0, column=1, sticky="ew", padx=(1,0))
        tk.Button(frame, text="전체 초기화", command=self.controller.clear_all, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).pack(fill=tk.X, pady=(3,0))
        return frame

    def _create_image_output_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        frame = tk.LabelFrame(parent, text="< Output Image >", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=3, pady=3)
        inner = tk.Frame(frame, bg=Colors.WHITE); inner.pack(fill=tk.BOTH, expand=True)
        tk.Label(inner, text="파일명:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(anchor=tk.W)
        tk.Entry(inner, textvariable=self.controller.settings['style_code'], justify=tk.CENTER).pack(fill=tk.X, pady=(0,3))
        tk.Label(inner, text="파일 형식:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(anchor=tk.W)
        ttk.Combobox(inner, textvariable=self.controller.settings['output_format'], values=["PNG", "JPG"], state="readonly").pack(fill=tk.X, pady=(0,3))
        tk.Label(inner, text="저장 위치:", bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(anchor=tk.W)
        tk.Button(inner, text="폴더 선택", command=self._select_save_directory, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(fill=tk.X)
        tk.Button(inner, text="이미지 저장", command=self.controller.save_image, bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).pack(fill=tk.X, pady=(8,0))
        return frame

    def _create_decoration_panel(self, parent: tk.Frame) -> tk.LabelFrame:
        frame = tk.LabelFrame(parent, text="< Asset >", bg=Colors.WHITE, fg=Colors.DARK_TEAL, bd=1, relief=tk.SOLID, padx=3, pady=3)
        inner = tk.Frame(frame, bg=Colors.WHITE, pady=5); inner.pack(fill=tk.BOTH, expand=True)
        add_frame = tk.Frame(inner, bg=Colors.WHITE); add_frame.pack(fill=tk.X); add_frame.columnconfigure((0,1), weight=1)
        tk.Button(add_frame, text="텍스트 추가", command=self.controller.add_new_text_layer, bg=Colors.DARK_TEAL, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_TEAL_ACTIVE).grid(row=0, column=0, sticky='ew', padx=(0,1))
        tk.Button(add_frame, text="도형 추가", command=self.controller.add_new_shape_layer, bg=Colors.DARK_TEAL, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_TEAL_ACTIVE).grid(row=0, column=1, sticky='ew', padx=(1,0))
        separator = tk.Frame(inner, height=1, bg=Colors.GREY); separator.pack(fill=tk.X, pady=8)
        palette_frame = tk.Frame(inner, bg=Colors.WHITE); palette_frame.pack(fill=tk.X)
        self.palette_color_preview = tk.Canvas(palette_frame, width=30, height=28, highlightthickness=1, highlightbackground=Colors.GREY, cursor="hand2", bd=0); self.palette_color_preview.pack(side=tk.LEFT); self.palette_color_preview.bind("<Button-1>", self._choose_palette_color)
        tk.Label(palette_frame, textvariable=self.controller.settings['palette_color'], width=8, anchor=tk.CENTER, bg=Colors.WHITE, fg=Colors.DARK_TEAL).pack(side=tk.LEFT, padx=5)
        tk.Button(palette_frame, text="색상 추출", command=self._enter_color_pick_mode, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side=tk.LEFT, fill=tk.X, expand=True)
        apply_frame = tk.Frame(inner, bg=Colors.WHITE); apply_frame.pack(fill=tk.X, pady=(8,0)); apply_frame.columnconfigure((0,1), weight=1)
        tk.Button(apply_frame, text="대상색상변경", command=lambda: print("TODO"), bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).grid(row=0, column=0, sticky='ew', padx=(0,1))
        tk.Button(apply_frame, text="배경색상변경", command=self._apply_color_to_background, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).grid(row=0, column=1, sticky='ew', padx=(1,0))
        return frame

    def _create_bottom_bar(self) -> tk.Frame:
        frame = tk.Frame(self, bg=Colors.WHITE); frame.columnconfigure(0, weight=1)
        self.status_label = tk.Label(frame, text="", bg=Colors.WHITE, fg=Colors.GREY); self.status_label.grid(row=0, column=0, sticky="w")
        return frame

    # --- UI Event Handlers & Callbacks (다이얼 관련 함수 삭제됨) ---
    def update_status(self, text: str): self.status_label.config(text=text)
    def _on_background_color_change(self, *args): color = self.controller.settings['background_color'].get(); self.canvas.configure(bg=color)
    def _on_palette_color_change(self, *args): color = self.controller.settings['palette_color'].get(); self.palette_color_preview.config(bg=color)
    def _on_zoom_change(self, *args): self._update_canvas_size_and_redraw()
    def _on_logo_zone_change(self, *args): self.controller.update_logo_object_display(); self._update_canvas_size_and_redraw()

    def _update_canvas_view(self, event=None):
        w, h = self.viewport_frame.winfo_width(), self.viewport_frame.winfo_height()
        if w <= 1 or h <= 1: return
        lw, lh = self.controller.settings['output_width'].get(), self.controller.settings['output_height'].get()
        if lw <= 0 or lh <= 0: return
        sx, sy = (w * 0.9) / lw, (h * 0.9) / lh
        self.canvas_controller.fit_scale = min(sx, sy); self._update_canvas_size_and_redraw()

    def _update_canvas_size_and_redraw(self):
        zoom = self.controller.get_zoom()
        w, h = self.canvas_controller.get_canvas_size(zoom)
        self.canvas.config(width=w, height=h)
        self.canvas.delete('border')
        if w > 1 and h > 1:
            border_id = self.canvas.create_rectangle(1, 1, w-2, h-2, dash=(5, 3), outline=Colors.GREY, tags='border')
            self.canvas.tag_lower(border_id)
        self.canvas_controller.update_all_objects_display(zoom)
        self._center_canvas_in_viewport()

    def _center_canvas_in_viewport(self):
        self.viewport.update_idletasks()
        vp_w, vp_h = self.viewport.winfo_width(), self.viewport.winfo_height()
        cv_w, cv_h = int(self.canvas.cget("width")), int(self.canvas.cget("height"))
        x, y = max(0, (vp_w - cv_w) // 2), max(0, (vp_h - cv_h) // 2)
        self.viewport.coords(self.canvas_window_id, x, y)
    def _add_files(self): files = filedialog.askopenfilenames(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")]); self.controller.add_new_image_layers(files)
    def _apply_resolution(self): self.controller.settings['zoom'].set(100); self._update_canvas_view()
    def _toggle_all_checks(self): checked = self.check_all_var.get(); [l.is_visible.set(checked) for l in self.controller.get_layers()]; [self.controller.toggle_layer_visibility(l) for l in self.controller.get_layers()]
    def _select_save_directory(self): directory = filedialog.askdirectory(initialdir=self.controller.settings['save_directory'].get()); self.controller.settings['save_directory'].set(directory); messagebox.showinfo("저장 위치", f"저장 위치가\n'{directory}'\n로 설정됨.")
    def _choose_palette_color(self, event=None): color = colorchooser.askcolor(title="색상 선택", initialcolor=self.controller.settings['palette_color'].get()); self.controller.settings['palette_color'].set(color[1].upper())
    def _apply_color_to_background(self): color = self.controller.settings['palette_color'].get(); self.controller.settings['background_color'].set(color); self.update_status(f"배경색 변경: {color}")
    def _enter_color_pick_mode(self): self.controller.is_color_picking_mode = True; self.canvas.config(cursor="crosshair"); self.update_status("🎨 색상 추출 모드: 캔버스 클릭")
    def update_select_all_button_state(self): layers = self.controller.get_layers(); all_selected = layers and all(l.selected for l in layers); self.select_all_button.config(text="선택해제" if all_selected else "전체선택", bg=Colors.DARK_GREY if all_selected else Colors.GREY)