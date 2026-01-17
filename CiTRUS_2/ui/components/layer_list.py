# 파일 경로: ui/components/layer_list.py

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from models.layer import Layer, ImageLayer, TextLayer, ShapeLayer

# --- 라이브러리 가용성 확인 ---
try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    
try:
    import rembg
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False


class LayerList(ttk.Frame):
    """레이어 목록 UI를 관리하는 클래스"""
    FILENAME_TRUNCATE_LIMIT = 25
    FILENAME_DISPLAY_LIMIT = 22

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self._list_drag_data = {}
        self._build_widgets()

    def _build_widgets(self):
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True, padx=3, pady=(0,3))
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(container, bd=0, highlightthickness=0, bg=ttk.Style().colors.bg)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview, bootstyle="round")
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.list_frame = ttk.Frame(self.canvas)
        self.list_canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        if DND_AVAILABLE:
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind("<<Drop>>", self._on_drop)
            self.list_frame.drop_target_register(DND_FILES)
            self.list_frame.dnd_bind("<<Drop>>", self._on_drop)
            
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.list_canvas_window, width=event.width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_drop(self, event):
        files = self.winfo_toplevel().tk.splitlist(event.data)
        self.controller.add_new_image_layers(files)

    def populate_list(self, layers: list[Layer]):
        for child in self.list_frame.winfo_children():
            child.destroy()

        for i, layer in enumerate(layers):
            self._create_list_item(i, layer)

        self.list_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.update_selection_visuals(layers)

    def _create_list_item(self, index: int, layer: Layer):
        row_index = index * 2
        widget = ttk.Frame(self.list_frame, style="light.TFrame", padding=5)
        widget.is_draggable_item = True
        widget.grid(row=row_index, column=0, sticky="ew", padx=2)
        widget.columnconfigure(1, weight=1)
        layer.widget_ref = widget # Layer 객체에 위젯 참조 저장

        if index < len(self.controller.get_layers()) - 1:
            ttk.Separator(self.list_frame).grid(row=row_index + 1, column=0, sticky='ew', padx=10, pady=2)

        # 체크박스
        checkbutton = ttk.Checkbutton(widget, variable=layer.is_visible, style="light.TCheckbutton", 
                                      command=lambda l=layer: self.controller.toggle_layer_visibility(l))
        checkbutton.grid(row=0, column=0, rowspan=2, sticky='ns', padx=(0, 5))

        # 이름과 썸네일
        display_name = layer.get_display_name()
        if len(display_name) > self.FILENAME_TRUNCATE_LIMIT:
            display_name = display_name[:self.FILENAME_DISPLAY_LIMIT] + "..."

        name_label = ttk.Label(widget, image=layer.thumbnail, text=display_name, compound="left", style="light.TLabel")
        name_label.grid(row=0, column=1, rowspan=2, sticky='w')

        # 컨트롤 (크기 조절, 버튼)
        ctrl_frame = ttk.Frame(widget, style="light.TFrame")
        ctrl_frame.grid(row=0, column=2, rowspan=2, sticky='e', padx=5)

        s_from = 8 if isinstance(layer, (TextLayer, ShapeLayer)) else 10
        s_inc = 1.0 if isinstance(layer, (TextLayer, ShapeLayer)) else 5.0
        
        scale_spinbox = ttk.Spinbox(ctrl_frame, from_=s_from, to=500, textvariable=layer.scale_var, width=5, increment=s_inc)
        scale_spinbox.pack(pady=2)
        # scale_var 변경 시 컨트롤러에 알림
        layer.scale_var.trace_add("write", lambda *args, l=layer: self.controller.update_layer_properties(l))


        btn_frame = ttk.Frame(ctrl_frame, style="light.TFrame")
        btn_frame.pack()
        
        bg_state = 'disabled' if not REMBG_AVAILABLE or not isinstance(layer, ImageLayer) else 'normal'
        ttk.Button(btn_frame, text="배경", width=5, command=lambda l=layer: self.controller.remove_layer_background(l), state=bg_state, bootstyle="secondary-outline").pack(side='left', padx=(0, 2))
        ttk.Button(btn_frame, text="삭제", width=5, command=lambda l=layer: self.controller.delete_layers([l]), bootstyle="danger-outline").pack(side='left')

        # 이벤트 바인딩
        for w in [widget, name_label, ctrl_frame, checkbutton, scale_spinbox, btn_frame]:
            self._bind_recursive(w, "<ButtonPress-1>", lambda e, idx=index: self._on_list_item_press(e, idx))
            self._bind_recursive(w, "<B1-Motion>", self._on_list_item_drag)
            self._bind_recursive(w, "<ButtonRelease-1>", self._on_list_item_release)
            self._bind_recursive(w, "<Double-Button-1>", lambda e, l=layer: self.controller.edit_layer_properties(l))

    def _find_item_widget(self, widget: tk.Widget) -> ttk.Frame | None:
        current = widget
        while current and not (isinstance(current, ttk.Frame) and hasattr(current, "is_draggable_item")):
            current = current.master
        return current

    def _on_list_item_press(self, event, clicked_index):
        self.controller.select_layer_from_list(clicked_index, event.state)
        widget = self._find_item_widget(event.widget)
        if widget:
            self._list_drag_data = {"widget": widget, "source_index": clicked_index}

    def _on_list_item_drag(self, event):
        if not self._list_drag_data: return
        
        source_index = self._list_drag_data["source_index"]
        dest_widget = self._find_item_widget(event.widget.winfo_containing(event.x_root, event.y_root))
        if not dest_widget: return

        dest_index = -1
        for i, layer in enumerate(self.controller.get_layers()):
            if layer.widget_ref == dest_widget:
                dest_index = i
                break
        
        if dest_index != -1 and dest_index != source_index:
            self.controller.move_layer_in_list(source_index, dest_index)
            self._list_drag_data["source_index"] = dest_index


    def _on_list_item_release(self, event):
        if self._list_drag_data:
            self.controller.finalize_layer_reorder()
            self._list_drag_data = {}

    def update_selection_visuals(self, layers):
        for layer in layers:
            widget = layer.widget_ref
            if not (widget and widget.winfo_exists()): continue

            is_selected = layer.selected
            base_style = "selected" if is_selected else "light"
            style_name = f"{base_style}.TFrame"
            
            try:
                widget.configure(style=style_name)
                for child in widget.winfo_children():
                    if isinstance(child, (ttk.Label, ttk.Checkbutton, ttk.Frame)):
                        child_style = f"{base_style}.{child.winfo_class()}"
                        child.configure(style=child_style)
                        if isinstance(child, ttk.Frame):
                             for grandchild in child.winfo_children():
                                if isinstance(grandchild, (ttk.Frame)):
                                    grandchild.configure(style=f"{base_style}.TFrame")

            except tk.TclError as e:
                # 스타일 적용 중 오류가 발생할 수 있으나 무시
                pass

    def _bind_recursive(self, widget, event_type, command):
        widget.bind(event_type, command)
        for child in widget.winfo_children():
            self._bind_recursive(child, event_type, command)