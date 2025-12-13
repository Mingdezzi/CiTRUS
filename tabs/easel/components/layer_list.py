# 파일 경로: tabs/easel/components/layer_list.py (Double Click & Checkbutton Fix 2 with Debug)

import tkinter as tk
import tkinter.ttk as ttk # 표준 ttk 사용 (Scrollbar)
# ttkbootstrap import 제거
from ..models.layer import Layer, ImageLayer, TextLayer, ShapeLayer

# [ ★★★★★ NEW: 테마 임포트 ★★★★★ ]
from ui.theme import Colors

# --- 라이브러리 가용성 확인 ---
try: from tkinterdnd2 import DND_FILES; DND_AVAILABLE = True
except ImportError: DND_AVAILABLE = False

class LayerList(tk.Frame): # tk.Frame 상속
    """레이어 목록 UI를 관리하는 클래스"""
    FILENAME_TRUNCATE_LIMIT = 25
    FILENAME_DISPLAY_LIMIT = 22

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=Colors.WHITE, **kwargs) # Use Colors.WHITE
        self.controller = controller # EaselController 참조
        self._list_drag_data = {}
        self._build_widgets()

    def _build_widgets(self):
        container = tk.Frame(self, bg=Colors.WHITE); container.pack(fill='both', expand=True, padx=3, pady=(0,3)); container.rowconfigure(0, weight=1); container.columnconfigure(0, weight=1) # Use Colors.WHITE
        self.canvas = tk.Canvas(container, bd=0, highlightthickness=0, bg=Colors.WHITE) # Use Colors.WHITE
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set); self.canvas.grid(row=0, column=0, sticky="nsew"); scrollbar.grid(row=0, column=1, sticky="ns")
        self.list_frame = tk.Frame(self.canvas, bg=Colors.WHITE) # Use Colors.WHITE
        self.list_canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        if DND_AVAILABLE:
            self.canvas.drop_target_register(DND_FILES); self.canvas.dnd_bind("<<Drop>>", self._on_drop)
            self.list_frame.drop_target_register(DND_FILES); self.list_frame.dnd_bind("<<Drop>>", self._on_drop)

    def _on_canvas_configure(self, event): self.canvas.itemconfig(self.list_canvas_window, width=event.width); self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    def _on_drop(self, event): files = self.winfo_toplevel().tk.splitlist(event.data); self.controller.add_new_image_layers(files)

    def populate_list(self, layers: list[Layer]):
        for child in self.list_frame.winfo_children(): # 이전 위젯 제거
            widget_layer_path = getattr(child, '_layer_path', None)
            if widget_layer_path:
                layer = self.controller.get_layer_by_path(widget_layer_path)
                if layer and hasattr(layer, 'scale_var_trace_id'):
                    try: layer.scale_var.trace_remove('write', layer.scale_var_trace_id)
                    except (AttributeError, tk.TclError): pass
            child.destroy()
        print(f"DEBUG: Populating list with {len(layers)} layers.") # Debug print
        for i, layer in enumerate(layers): self._create_list_item(i, layer) # 새 위젯 생성
        self.list_frame.update_idletasks(); self.canvas.config(scrollregion=self.canvas.bbox("all")); self.update_selection_visuals(layers)

    def _create_list_item(self, index: int, layer: Layer):
        row_index = index * 2
        widget = tk.Frame(self.list_frame, bg=Colors.WHITE, padx=5, pady=5); widget.is_draggable_item = True; widget._layer_path = layer.path # Use Colors.WHITE
        widget.grid(row=row_index, column=0, sticky="ew", padx=2); widget.columnconfigure(1, weight=1); layer.widget_ref = widget
        if index < len(self.controller.get_layers()) - 1:
            separator = tk.Frame(self.list_frame, height=1, bg=Colors.GREY); separator.grid(row=row_index + 1, column=0, sticky='ew', padx=10, pady=2) # Use Colors.GREY

        print(f"DEBUG: Creating Checkbutton for layer {index}: {layer.path}") # Debug print
        checkbutton = tk.Checkbutton(widget, variable=layer.is_visible,
                                      command=lambda l=layer: (print(f"DEBUG: Checkbutton command triggered for layer: {l.path}"), self.controller.toggle_layer_visibility(l)),
                                      bg=Colors.WHITE, activebackground=Colors.WHITE, selectcolor=Colors.WHITE, relief=tk.FLAT, bd=0) # Use Colors
        checkbutton.grid(row=0, column=0, rowspan=2, sticky='ns', padx=(0, 5))

        display_name = layer.get_display_name(); display_name = display_name[:self.FILENAME_DISPLAY_LIMIT] + "..." if len(display_name) > self.FILENAME_TRUNCATE_LIMIT else display_name
        if not hasattr(layer, '_thumbnail_ref'):
             try: layer.thumbnail = layer.create_thumbnail(); layer._thumbnail_ref = layer.thumbnail
             except Exception as e: print(f"썸네일 생성 실패 ({layer.path}): {e}")
        name_label = tk.Label(widget, image=getattr(layer, '_thumbnail_ref', None), text=display_name, compound="left", bg=Colors.WHITE, fg=Colors.DARK_TEAL, anchor=tk.W) # Use Colors
        name_label.grid(row=0, column=1, rowspan=2, sticky='w')
        ctrl_frame = tk.Frame(widget, bg=Colors.WHITE); ctrl_frame.grid(row=0, column=2, rowspan=2, sticky='e', padx=5) # Use Colors.WHITE
        s_from = 8 if isinstance(layer, (TextLayer, ShapeLayer)) else 10; s_inc = 1.0 if isinstance(layer, (TextLayer, ShapeLayer)) else 5.0
        if hasattr(layer, 'scale_var'):
            scale_spinbox = tk.Spinbox(ctrl_frame, from_=s_from, to=500, textvariable=layer.scale_var, width=5, increment=s_inc); scale_spinbox.pack(pady=2)
            layer.scale_var_trace_id = layer.scale_var.trace_add("write", lambda n, i, m, l=layer: self.controller.update_layer_properties(l))
        btn_frame = tk.Frame(ctrl_frame, bg=Colors.WHITE); btn_frame.pack() # Use Colors.WHITE
        bg_state = tk.NORMAL if isinstance(layer, ImageLayer) else tk.DISABLED
        tk.Button(btn_frame, text="배경", width=5, command=lambda l=layer: self.controller.remove_layer_background(l), state=bg_state, bg=Colors.GREY, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARK_GREY).pack(side='left', padx=(0, 2)) # Use Colors
        tk.Button(btn_frame, text="삭제", width=5, command=lambda l=layer: self.controller.delete_layers([l]), bg=Colors.MAIN_RED, fg=Colors.WHITE, relief=tk.FLAT, activebackground=Colors.DARKER_RED).pack(side='left') # Use Colors

        # --- Event Binding Debug ---
        # [ ★★★★★ MODIFIED: Bind specific widgets directly, use _bind_recursive carefully ★★★★★ ]
        # Widgets that should trigger list selection and drag start on ButtonPress-1
        press_drag_widgets = [widget, name_label, ctrl_frame, btn_frame]
        for w in press_drag_widgets:
            if 'scale_spinbox' in locals() and w == scale_spinbox: continue # Skip Spinbox for press/drag/release
            # Bind ButtonPress-1 only to widgets that are NOT the checkbutton
            w.bind("<ButtonPress-1>", lambda e, idx=index: self._on_list_item_press(e, idx))
            # Bind Motion and Release to allow dragging from these widgets
            w.bind("<B1-Motion>", lambda e: self._on_list_item_drag(e))
            w.bind("<ButtonRelease-1>", lambda e: self._on_list_item_release(e))
            # Bind Double-Click
            w.bind("<Double-Button-1>", lambda e, l=layer: self._on_list_item_double_click(e, l))

        # Bind events to the checkbutton itself, but NOT ButtonPress-1 or ButtonRelease-1
        # This allows the checkbutton's default command to work, but still allows dragging *from* it.
        checkbutton.bind("<B1-Motion>", lambda e: self._on_list_item_drag(e))
        # We might need ButtonRelease on checkbutton if drag STARTS on it? Test this.
        # checkbutton.bind("<ButtonRelease-1>", lambda e: self._on_list_item_release(e)) # Potentially add back if needed
        checkbutton.bind("<Double-Button-1>", lambda e, l=layer: self._on_list_item_double_click(e, l))

        # Use _bind_recursive only for events that should apply universally AND don't conflict,
        # or modify _bind_recursive to skip certain widgets/events.
        # For now, binding directly is safer.
        # --- End Event Binding Debug ---

    # [ ★★★★★ REMOVED: _handle_press function is no longer needed ★★★★★ ]
    # def _handle_press(self, event, clicked_index): ...

    def _find_item_widget(self, widget: tk.Widget) -> tk.Frame | None:
        current = widget
        while current and not (isinstance(current, tk.Frame) and hasattr(current, "is_draggable_item")): parent = getattr(current, 'master', None); current = parent if parent else None
        return current if hasattr(current, "is_draggable_item") else None

    def _on_list_item_press(self, event, clicked_index):
        # This function is now only called when ButtonPress-1 happens on widgets OTHER than the checkbutton.
        print(f"DEBUG: _on_list_item_press called for index {clicked_index}, state: {event.state}, widget: {event.widget}") # Debug print
        self.controller.select_layer_from_list(clicked_index, event.state)
        widget = self._find_item_widget(event.widget)
        if widget:
            print(f"DEBUG: Starting potential drag for item at index {clicked_index}") # Debug print
            self._list_drag_data = {"widget": widget, "source_index": clicked_index}
        else:
             print(f"DEBUG: Could not find draggable item widget for press at index {clicked_index}") # Debug print
             self._list_drag_data = {}


    def _on_list_item_drag(self, event):
        if not self._list_drag_data: return
        source_index = self._list_drag_data.get("source_index", -1)
        if source_index == -1: return

        dest_widget_under_mouse = event.widget.winfo_containing(event.x_root, event.y_root)
        if not dest_widget_under_mouse: return

        dest_widget = self._find_item_widget(dest_widget_under_mouse)
        if not dest_widget: return

        dest_index = -1; layers = self.controller.get_layers()
        for i, layer in enumerate(layers):
            if layer.widget_ref == dest_widget: dest_index = i; break

        if dest_index != -1 and dest_index != source_index:
            print(f"DEBUG: Drag moved item from {source_index} to {dest_index}") # Debug print
            self.controller.move_layer_in_list(source_index, dest_index)
            self.populate_list(layers) # Repopulate updates visuals and widget references
            self._list_drag_data["source_index"] = dest_index # Update source index after move
            print(f"DEBUG: Drag source index updated to {dest_index} after repopulate") # Debug print

    def _on_list_item_release(self, event):
        if self._list_drag_data:
            print(f"DEBUG: Releasing drag, finalizing order.") # Debug print
            self.controller.finalize_layer_reorder()
            self._list_drag_data = {}
        # else:
            # print("DEBUG: _on_list_item_release called without active drag data.") # Debug print needed?


    def _on_list_item_double_click(self, event, layer: Layer):
        print(f"DEBUG: Double click detected for layer: {layer.path}") # Debug print
        if layer:
            if layer.is_visible.get():
                try:
                    print(f"DEBUG: Activating handles for {layer.path}") # Debug print
                    self.controller.view.canvas_controller.activate_resize_handles(layer.path)
                except Exception as e: print(f"Error activating handles on double click: {e}")
            print(f"DEBUG: Editing properties for {layer.path}") # Debug print
            self.controller.edit_layer_properties(layer)

    def update_selection_visuals(self, layers):
        for layer in layers:
            widget = layer.widget_ref
            if not (widget and widget.winfo_exists()): continue
            is_selected = layer.selected
            target_bg = Colors.SELECTED_BG if is_selected else Colors.WHITE # Use Colors
            try:
                widget.configure(bg=target_bg)
                for child in widget.winfo_children():
                    if isinstance(child, (tk.Checkbutton, tk.Label, tk.Frame)):
                        is_button_frame = isinstance(child, tk.Frame) and any(isinstance(gc, tk.Button) for gc in child.winfo_children())
                        is_spinbox_frame = isinstance(child, tk.Frame) and any(isinstance(gc, tk.Spinbox) for gc in child.winfo_children())
                        if not is_button_frame and not is_spinbox_frame :
                             try:
                                child.configure(bg=target_bg)
                                if isinstance(child, tk.Frame):
                                    for grandchild in child.winfo_children():
                                        if isinstance(grandchild, tk.Label):
                                            try: grandchild.configure(bg=target_bg)
                                            except tk.TclError: pass
                             except tk.TclError: pass
            except tk.TclError: pass

    # [ ★★★★★ MODIFIED: _bind_recursive to skip certain events/widgets ★★★★★ ]
    def _bind_recursive(self, widget, event_type, command):
        # Binds event ONLY if it doesn't conflict with widget's primary action
        if widget:
            # Skip ButtonPress/Release for Checkbutton to allow its command to work
            if isinstance(widget, tk.Checkbutton) and event_type in ["<ButtonPress-1>", "<ButtonRelease-1>"]:
                print(f"DEBUG: Skipping binding '{event_type}' for Checkbutton {widget}") # Debug print
                pass # Skip binding
            # Skip ButtonPress/Release for Button? (Generally OK, but consider if needed)
            # Skip for Spinbox/Entry/Combobox to allow text selection/editing
            elif isinstance(widget, (tk.Spinbox, tk.Entry, ttk.Combobox, tk.Button)) and event_type in ["<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"]:
                 print(f"DEBUG: Skipping binding '{event_type}' for Input/Button widget {widget}") # Debug print
                 pass # Skip binding these potentially conflicting events
            else:
                # print(f"DEBUG: Binding '{event_type}' to {widget} ({type(widget)})") # Frequent print
                widget.bind(event_type, command)

            # Recurse for children, applying the same logic
            for child in widget.winfo_children():
                 # Don't recurse into input widgets' internal parts
                 if not isinstance(child, (tk.Spinbox, tk.Entry, ttk.Combobox)):
                    self._bind_recursive(child, event_type, command)