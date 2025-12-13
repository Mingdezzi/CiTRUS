import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import math
import traceback
from PIL import Image, ImageTk, ImageDraw, ImageFont

from ui.theme import Colors
from .models.layer import Layer, ImageLayer, TextLayer, ShapeLayer, DISPLAY_IMG_MAX_SIZE
from ui.dialogs import TextPropertiesDialog, ShapePropertiesDialog
from .services.project_service import ProjectService
from .services.image_service import ImageService
from .services.font_service import FontService

class EaselController:
    def __init__(self, view):
        self.view = view
        self.layers: list[Layer] = []
        self.logo_object = None
        self.last_selected_anchor_index = None
        self.is_color_picking_mode = False
        self.logo_preview_label = None
        self.status_label = None
        self._logo_preview_tkimg = None
        self.settings = {
            'logo_path': tk.StringVar(), 'logo_zone_height': tk.IntVar(value=90),
            'logo_size': tk.IntVar(value=70), 'style_code': tk.StringVar(),
            'global_scale': tk.DoubleVar(value=30.0),
            'grid_overlap': tk.IntVar(value=70),
            'output_width': tk.IntVar(value=1500), 'output_height': tk.IntVar(value=1500),
            'output_format': tk.StringVar(value="PNG"), 'background_color': tk.StringVar(value="#FFFFFF"),
            'save_directory': tk.StringVar(value=os.path.expanduser("~")),
            'zoom': tk.DoubleVar(value=100.0), 'palette_color': tk.StringVar(value="#FFFFFF"),
        }

        self.is_line_placement_mode = False
        self.line_start_point = None
        self.line_end_point = None

    def set_ui_references(self, logo_preview_label, status_label):
        self.logo_preview_label, self.status_label = logo_preview_label, status_label

    def get_layers(self) -> list[Layer]:
        return self.layers

    def get_layer_by_path(self, path: str) -> Layer | None:
        return next((l for l in self.layers if l.path == path), None)

    def get_zoom(self) -> float:
        return self.settings['zoom'].get() / 100.0

    def get_settings_values(self) -> dict:
        return {key: var.get() for key, var in self.settings.items()}

    def update_status(self, text: str):
        if self.status_label:
            self.status_label.config(text=text)

    def add_new_image_layers(self, files: list[str]):
        new_files_added = False
        for f in [f.strip('{}') for f in files]:
            normalized_path = os.path.normpath(f)
            if os.path.isfile(normalized_path) and normalized_path not in [l.path for l in self.layers if isinstance(l, ImageLayer)]:
                try:
                    self.layers.append(ImageLayer(file_path=normalized_path))
                    new_files_added = True
                except Exception as e:
                    messagebox.showerror("Image Load Error", f"Failed to load image:\n{normalized_path}\n\nError: {e}")
        if new_files_added:
            self.view.layer_list.populate_list(self.layers)
            if not self.settings['style_code'].get():
                self._set_default_style_code()

    def add_new_text_layer(self):
        dialog = TextPropertiesDialog(self.view.winfo_toplevel())
        if dialog.result:
            self.layers.append(TextLayer(**dialog.result))
            self.view.layer_list.populate_list(self.layers)

    def add_new_shape_layer(self):
        dialog = ShapePropertiesDialog(self.view.winfo_toplevel())
        if dialog.result:
            self.layers.append(ShapeLayer(**dialog.result))
            self.view.layer_list.populate_list(self.layers)

    def edit_layer_properties(self, layer: Layer):
        if isinstance(layer, TextLayer):
            init_vals = {'text': layer.text, 'font_family': layer.font_family, 'font_size': int(layer.scale_var.get()), 'color': layer.color}
            dialog = TextPropertiesDialog(self.view.winfo_toplevel(), initial_values=init_vals)
            if dialog.result:
                layer.text, layer.font_family, layer.color = dialog.result['text'], dialog.result['font_family'], dialog.result['color']
                layer.scale_var.set(dialog.result['font_size'])
                self.view.canvas_controller.update_object_display(layer, self.get_zoom())
                self.view.layer_list.populate_list(self.layers)

    def delete_layers(self, layers_to_delete: list[Layer]):
        if not layers_to_delete:
            messagebox.showinfo("알림", "삭제할 항목을 선택해주세요.")
            return
        layer_names = ", ".join([l.get_display_name()[:20] for l in layers_to_delete])
        if messagebox.askyesno("삭제 확인", f"{len(layers_to_delete)}개 항목 삭제?\n({layer_names})"):
            for layer in layers_to_delete:
                if layer in self.layers:
                    layer.is_visible.set(False)
                    self.toggle_layer_visibility(layer)
                    self.layers.remove(layer)
            self.view.layer_list.populate_list(self.layers)
            self.update_status(f"{len(layers_to_delete)}개 삭제 완료.")

    def delete_selected_layers(self):
        self.delete_layers([l for l in self.layers if l.selected])

    def toggle_layer_visibility(self, layer: Layer):
        if layer.is_visible.get():
            self.view.canvas_controller.add_layer_to_canvas(layer)
        else:
            self.view.canvas_controller.remove_layer_from_canvas(layer)
            if self.view.canvas_controller.active_selection_path == layer.path:
                self.view.canvas_controller.clear_resize_handles()

    def update_layer_properties(self, layer: Layer):
        if layer.is_visible.get():
            self.view.canvas_controller.update_object_display(layer, self.get_zoom())

    def clear_all(self):
        if not messagebox.askyesno("확인", "모든 작업 내용을 초기화하시겠습니까?"):
            return
        for layer in self.layers:
            layer.is_visible.set(False)
            self.toggle_layer_visibility(layer)
        self.layers.clear()
        self.view.canvas_controller.canvas_objects.clear()
        self.view.canvas_controller.clear_resize_handles()
        self.delete_logo(confirm=False)
        self.settings['style_code'].set("")
        self.reset_grid()
        self.view.layer_list.populate_list(self.layers)
        self.update_status("모든 항목 초기화.")

    def select_layer_from_list(self, clicked_index, event_state):
        is_shift, is_ctrl = (event_state & 0x0001), (event_state & 0x0004)
        if not (0 <= clicked_index < len(self.layers)):
            if not is_ctrl and not is_shift:
                for l in self.layers:
                    l.selected = False
                self.view.canvas_controller.clear_resize_handles()
            self.view.layer_list.update_selection_visuals(self.layers)
            self.view.update_select_all_button_state()
            return

        layer_clicked = self.layers[clicked_index]
        if is_shift and self.last_selected_anchor_index is not None:
            start, end = min(self.last_selected_anchor_index, clicked_index), max(self.last_selected_anchor_index, clicked_index)
            for i, layer in enumerate(self.layers):
                layer.selected = (start <= i <= end)
            self.view.canvas_controller.clear_resize_handles()
        elif is_ctrl:
            layer_clicked.selected = not layer_clicked.selected
            self.last_selected_anchor_index = clicked_index
            self.view.canvas_controller.clear_resize_handles()
        else:
            is_already_solely_selected = sum(1 for l in self.layers if l.selected) == 1 and layer_clicked.selected
            for l in self.layers:
                l.selected = False
            if not is_already_solely_selected:
                layer_clicked.selected = True
                self.last_selected_anchor_index = clicked_index
            else:
                self.last_selected_anchor_index = None
            self.view.canvas_controller.clear_resize_handles()
        self.view.layer_list.update_selection_visuals(self.layers)
        self.view.update_select_all_button_state()

    def select_layer_from_canvas(self, path, event_state):
        is_ctrl = (event_state & 0x0004)
        target_layer = self.get_layer_by_path(path) if path and path != 'logo' else None
        is_logo = (path == 'logo')

        if not is_ctrl:
            is_already_solely_selected = (is_logo and self.logo_object_is_selected() and sum(1 for l in self.layers if l.selected)==0) or \
                                         (target_layer and target_layer.selected and sum(1 for l in self.layers if l.selected)==1 and not self.logo_object_is_selected())
            for l in self.layers:
                l.selected = False
            if not is_already_solely_selected:
                if is_logo:
                    self.view.canvas_controller.activate_resize_handles('logo')
                elif target_layer:
                    target_layer.selected = True
                    self.view.canvas_controller.clear_resize_handles()
                else:
                    self.view.canvas_controller.clear_resize_handles()
            else:
                self.view.canvas_controller.clear_resize_handles()
        else:
            if is_logo:
                pass
            elif target_layer:
                target_layer.selected = not target_layer.selected
                self.view.canvas_controller.clear_resize_handles()
        self.view.layer_list.update_selection_visuals(self.layers)
        self.view.update_select_all_button_state()

    def logo_object_is_selected(self):
        return self.view.canvas_controller.active_selection_path == 'logo'

    def toggle_all_layer_selection(self):
        if not self.layers: return
        are_all_selected = all(l.selected for l in self.layers)
        new_state = not are_all_selected
        for l in self.layers:
            l.selected = new_state
        self.view.layer_list.update_selection_visuals(self.layers)
        self.view.update_select_all_button_state()
        self.view.canvas_controller.clear_resize_handles()

    def move_layer_in_list(self, source_index, dest_index):
        if 0 <= source_index < len(self.layers) and 0 <= dest_index < len(self.layers):
            layer = self.layers.pop(source_index)
            self.layers.insert(dest_index, layer)

    def finalize_layer_reorder(self):
        self.view.canvas_controller.reorder_canvas_layers()
        self.view.layer_list.populate_list(self.layers)

    def save_project(self):
        canvas_objects_data = {}
        for path, obj_info in self.view.canvas_controller.canvas_objects.items():
            if 'rel_x' in obj_info and 'rel_y' in obj_info:
                canvas_objects_data[path] = {'rel_x': obj_info['rel_x'], 'rel_y': obj_info['rel_y']}
        if self.logo_object:
            canvas_objects_data['logo'] = {'rel_x': self.logo_object['rel_x'], 'rel_y': self.logo_object['rel_y']}
        status = ProjectService.save_project(self.get_settings_values(), self.layers, canvas_objects_data)
        if status:
            self.update_status(status)

    def load_project(self):
        if not messagebox.askyesno("불러오기 확인", "현재 작업 내용 사라짐. 계속?"):
            return

        project_data = ProjectService.load_project()
        if not project_data:
            return

        self.clear_all()
        settings_data = project_data.get('settings', {})
        for key, var in self.settings.items():
            if key in settings_data:
                try:
                    var.set(settings_data[key])
                except Exception:
                    pass
        self.layers = project_data.get('layers', [])
        self.view.layer_list.populate_list(self.layers)
        canvas_positions = project_data.get('canvas_positions', {})
        initial_positions = {}
        for layer in self.layers:
            if layer.path in canvas_positions:
                initial_positions[layer.path] = canvas_positions[layer.path]
        initial_logo_pos = canvas_positions.get('logo') if self.settings['logo_path'].get() else None
        self.view.update_idletasks()
        self.view._update_canvas_view()
        if initial_logo_pos:
            self._add_logo_to_canvas()
            if self.logo_object:
                self.logo_object.update(initial_logo_pos)
        for layer in self.layers:
            if layer.is_visible.get():
                self.view.canvas_controller.add_layer_to_canvas(layer)
                if layer.path in initial_positions and layer.path in self.view.canvas_controller.canvas_objects:
                    self.view.canvas_controller.canvas_objects[layer.path].update(initial_positions[layer.path])
        self.view.canvas_controller.update_all_objects_display(self.get_zoom())
        self.view.canvas_controller.reorder_canvas_layers()
        self.update_status(f"프로젝트 로드: {os.path.basename(project_data.get('path', ''))}")

    def save_image(self):
        settings = self.get_settings_values()
        settings['logo_info'] = self.logo_object if self.logo_object else None
        status = ImageService.save_canvas_as_image(settings, self.layers, self.view.canvas_controller.canvas_objects)
        if status:
            self.update_status(status)

    def remove_layer_background(self, layer: Layer):
        if not isinstance(layer, ImageLayer):
            return
        self.update_status(f"'{layer.get_display_name()}' 배경 제거 중...")
        self.view.update_idletasks()
        success = ImageService.remove_background(layer)
        if success:
            self.view.layer_list.populate_list(self.layers)
            if layer.is_visible.get():
                self.view.canvas_controller.update_object_display(layer, self.get_zoom())
            self.update_status("배경 제거 완료!")
        else:
            self.update_status("배경 제거 실패.")

    def _set_default_style_code(self):
        image_layers = [l for l in self.layers if isinstance(l, ImageLayer)]
        if image_layers:
            self.settings['style_code'].set(os.path.commonprefix([os.path.basename(l.path) for l in image_layers])[:8])

    def apply_global_scale(self):
        selected = [l for l in self.layers if l.selected]
        if not selected:
            messagebox.showwarning("알림", "크기 변경 레이어 선택.")
            return

        scale_val = self.settings['global_scale'].get()
        for l in selected:
            if hasattr(l, 'scale_var'):
                l.scale_var.set(scale_val)

        self.update_status(f"{len(selected)}개 크기 변경 완료.")

    def select_logo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png")])
        if path:
            self.settings['logo_path'].set(os.path.normpath(path))
            self._add_logo_to_canvas()

    def delete_logo(self, confirm=True):
        if confirm and not self.logo_object:
            return
        if confirm and not messagebox.askyesno("확인", "로고 삭제?"):
            return
        if self.logo_object:
            self.view.canvas.delete(self.logo_object['id'])
            self.logo_object = None
            if self.view.canvas_controller.active_selection_path == 'logo':
                self.view.canvas_controller.clear_resize_handles()
        self.settings['logo_path'].set("")
        self.update_logo_preview()
        if confirm:
            self.update_status("로고 삭제.")

    def on_logo_panel_drop(self, event):
        files = [f.strip('{}') for f in self.view.winfo_toplevel().tk.splitlist(event.data)]
        first = next((f for f in files if os.path.isfile(f) and f.lower().endswith('.png')), None)
        if first:
            self.settings['logo_path'].set(os.path.normpath(first))
            self._add_logo_to_canvas()
        else:
            messagebox.showwarning("오류", ".png 파일 없음.")

    def _add_logo_to_canvas(self):
        path = self.settings['logo_path'].get()
        if not path or not os.path.exists(path):
            self.delete_logo(confirm=False)
            return

        if self.logo_object:
            self.view.canvas.delete(self.logo_object['id'])
            self.logo_object = None

        try:
            pil_img_original = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("오류", f"로고 로드 실패: {e}")
            self.settings['logo_path'].set("")
            self.update_logo_preview()
            return

        lw, lh = self.settings['output_width'].get(), self.settings['output_height'].get()
        if lw <= 1 or lh <= 1:
            self.view.after(50, self._add_logo_to_canvas)
            return

        margin = 15
        zone_h_log = lh * (self.settings['logo_zone_height'].get() / 1500.0)
        temp_logo_disp = self._get_display_pil_for_logo(self.view.canvas_controller.fit_scale, pil_img_to_process=pil_img_original)
        logo_w_at_100 = temp_logo_disp.width if temp_logo_disp else 20
        rel_x = (margin + logo_w_at_100 / 2) / lw if lw > 0 else 0.1
        rel_y = (zone_h_log / 2) / lh if lh > 0 else 0.1
        item_id = self.view.canvas.create_image(0, 0, tags=("item", "logo"))
        self.logo_object = {'id': item_id, 'type': 'logo', 'pil_img_original': pil_img_original, 'tk_img': None, 'pil_for_display': None, 'rel_x': rel_x, 'rel_y': rel_y, 'path': 'logo', 'original_path': path, 'angle': 0.0}
        self.update_logo_object_display()
        self.view.canvas_controller.reorder_canvas_layers()

    def update_logo_object_display(self):
        if not self.logo_object:
            return
        obj_info = self.logo_object
        zoom = self.get_zoom()
        cw, ch = self.view.canvas_controller.get_canvas_size(zoom)
        if cw <= 1:
            return
        actual_zoom = self.view.canvas_controller.fit_scale * zoom
        pil_img = self._get_display_pil_for_logo(actual_zoom)
        if pil_img:
            x, y = obj_info['rel_x'] * cw, obj_info['rel_y'] * ch
            obj_info['tk_img'] = ImageTk.PhotoImage(pil_img)
            obj_info['pil_for_display'] = pil_img
            self.view.canvas.itemconfig(obj_info['id'], image=obj_info['tk_img'], state='normal')
            self.view.canvas.coords(obj_info['id'], x, y)
            if self.view.canvas_controller.active_selection_path == 'logo':
                self.view.canvas_controller.activate_resize_handles('logo')
        else:
            self.view.canvas.itemconfig(obj_info['id'], state='hidden')

    def _get_display_pil_for_logo(self, actual_zoom: float, pil_img_to_process=None) -> Image.Image | None:
        if pil_img_to_process is None:
            pil_img_to_process = self.logo_object.get('pil_img_original') if self.logo_object else None
        if not pil_img_to_process:
            return None

        scale = self.settings['logo_size'].get()
        lh = self.settings['output_height'].get()
        zone_h_log = lh * (self.settings['logo_zone_height'].get() / 1500.0)

        target_h_log = zone_h_log * (scale / 100.0)
        if pil_img_to_process.height <= 0:
            return None

        ratio = target_h_log / pil_img_to_process.height
        w_log, h_log = int(pil_img_to_process.width * ratio), int(target_h_log)

        dw, dh = int(w_log * actual_zoom), int(h_log * actual_zoom)
        if dw < 1 or dh < 1:
            return None

        try:
            return pil_img_to_process.resize((dw, dh), Image.Resampling.LANCZOS)
        except Exception:
            return None

    def update_logo_preview(self):
        if not self.logo_preview_label or not self.logo_preview_label.winfo_exists():
            return
        path = self.settings['logo_path'].get()
        if path and os.path.exists(path):
            try:
                img = Image.open(path)
                self.logo_preview_label.update_idletasks()
                w = self.logo_preview_label.winfo_width() - 10
                h = self.logo_preview_label.winfo_height() - 10

                if w < 1 or h < 1:
                    self.view.after(50, self.update_logo_preview)
                    return

                img.thumbnail((w,h), Image.Resampling.LANCZOS)
                self._logo_preview_tkimg = ImageTk.PhotoImage(img)
                self.logo_preview_label.config(image=self._logo_preview_tkimg, text="")
            except Exception:
                traceback.print_exc()
                self.logo_preview_label.config(image="", text="오류")
        else:
            self.logo_preview_label.config(image="", text="로고 없음\n(드래그)")

    def adjust_logo_zone(self, amount: int):
        current = self.settings['logo_zone_height'].get()
        self.settings['logo_zone_height'].set(max(10, min(current + amount, 500)))

    def adjust_logo_size(self, amount: int):
        current = self.settings['logo_size'].get()
        self.settings['logo_size'].set(max(10, min(current + amount, 200)))

    def apply_grid_layout(self):
        images_to_layout = [l for l in self.layers if l.is_visible.get() and isinstance(l, ImageLayer)]
        if not images_to_layout:
            messagebox.showinfo("알림", "자동 배치할 이미지가 없습니다.\n(레이어 목록에서 이미지를 체크해주세요)")
            return

        canvas_w, canvas_h = self.view.canvas_controller.get_canvas_size()
        actual_zoom = self.view.canvas_controller.fit_scale * self.get_zoom()
        logo_zone_h = canvas_h * (self.settings['logo_zone_height'].get() / 1500.0)
        work_w, work_h, work_y_start = canvas_w, canvas_h - logo_zone_h, logo_zone_h
        if work_w <= 1 or work_h <= 1:
            messagebox.showerror("오류", "캔버스 작업 영역 계산 오류.")
            return

        checked_cells = sorted([(r,c) for r, row in enumerate(self.view.grid_vars) for c, var in enumerate(row) if var.get()])
        num_images = len(images_to_layout)
        dests = []

        if not checked_cells:
            rows = int(math.sqrt(num_images)) or 1
            cols = math.ceil(num_images / rows)
            start_r = (self.view.GRID_SIZE - rows) // 2
            start_c = (self.view.GRID_SIZE - cols) // 2
            dests = [(start_r + i // cols, start_c + i % cols) for i in range(num_images)]
        else:
            dests = list(checked_cells)
            num_cells = len(dests)
            if num_images > num_cells:
                num_to_add = num_images - num_cells
                interpolated_cells = []
                if num_cells > 1:
                    for i in range(num_cells - 1):
                        r1, c1 = dests[i]; r2, c2 = dests[i+1]
                        interpolated_cells.append(((r1 + r2) / 2.0, (c1 + c2) / 2.0))
                elif num_cells == 1:
                    r, c = dests[0]
                    interpolated_cells = [(r, c+1), (r, c-1), (r+1, c), (r-1, c), (r+1, c+1), (r-1, c-1), (r+1, c-1), (r-1, c+1)]
                if interpolated_cells:
                    for j in range(num_to_add):
                        dests.append(interpolated_cells[j % len(interpolated_cells)])

        image_data = [{'layer': img, 'grid_r': r, 'grid_c': c} for img, (r, c) in zip(images_to_layout, dests)]
        if not image_data: return

        min_r = min(d['grid_r'] for d in image_data)
        min_c = min(d['grid_c'] for d in image_data)
        spacing = (100 - self.settings['grid_overlap'].get()) / 100.0
        optimal_scale = 10.0
        low = 1.0
        high = 500.0
        iterations = 25

        for i in range(iterations):
            current_scale = (low + high) / 2
            test_sizes = [self._get_temp_display_size(d['layer'], current_scale, actual_zoom) for d in image_data]
            valid_sizes = [s for s in test_sizes if s and s[0] > 0 and s[1] > 0]
            if not valid_sizes or len(valid_sizes) != len(image_data):
                high = current_scale
                continue
            avg_w = sum(s[0] for s in valid_sizes) / len(valid_sizes)
            avg_h = sum(s[1] for s in valid_sizes) / len(valid_sizes)
            avg_w, avg_h = max(1, avg_w), max(1, avg_h)
            placements = [{'x':(d['grid_c']-min_c)*avg_w*spacing, 'y':(d['grid_r']-min_r)*avg_h*spacing, 'w':s[0], 'h':s[1]} for d, s in zip(image_data, valid_sizes)]
            min_x = min(p['x']-p['w']/2 for p in placements)
            max_x = max(p['x']+p['w']/2 for p in placements)
            min_y = min(p['y']-p['h']/2 for p in placements)
            max_y = max(p['y']+p['h']/2 for p in placements)
            req_w, req_h = max_x - min_x, max_y - min_y
            if req_w < work_w and req_h < work_h:
                optimal_scale = current_scale
                low = current_scale
            else:
                high = current_scale

        self.settings['global_scale'].set(round(optimal_scale, 1))
        original_selection = {l.path for l in self.layers if l.selected}
        layers_to_scale = {d['layer'] for d in image_data}
        for l in self.layers:
            l.selected = (l in layers_to_scale)
        self.view.layer_list.update_selection_visuals(self.layers)
        self.apply_global_scale()
        for l in self.layers:
            l.selected = (l.path in original_selection)
        self.view.layer_list.update_selection_visuals(self.layers)
        self.view.update_idletasks()

        scaled_data = []
        for d in image_data:
            obj_info = self.view.canvas_controller.canvas_objects.get(d['layer'].path)
            if obj_info and obj_info.get('pil_for_display'):
                 pil_img = obj_info['pil_for_display']
                 scaled_data.append({'obj': obj_info, 'w': pil_img.width, 'h': pil_img.height, 'grid_r': d['grid_r'], 'grid_c': d['grid_c']})

        if not scaled_data:
            messagebox.showwarning("배치 오류", "스케일 적용 후 이미지 크기 정보를 얻지 못했습니다.")
            return

        avg_w = sum(s['w'] for s in scaled_data) / len(scaled_data) if scaled_data else 1
        avg_h = sum(s['h'] for s in scaled_data) / len(scaled_data) if scaled_data else 1
        avg_w, avg_h = max(1, avg_w), max(1, avg_h)
        placements = [{'obj': s['obj'], 'x': (s['grid_c']-min_c)*avg_w*spacing, 'y': (s['grid_r']-min_r)*avg_h*spacing, 'w':s['w'], 'h':s['h']} for s in scaled_data]
        min_x = min(p['x']-p['w']/2 for p in placements)
        max_x = max(p['x']+p['w']/2 for p in placements)
        min_y = min(p['y']-p['h']/2 for p in placements)
        max_y = max(p['y']+p['h']/2 for p in placements)
        offset_x = work_w/2 - (min_x + (max_x - min_x) / 2)
        offset_y = (work_y_start + work_h/2) - (min_y + (max_y - min_y) / 2)

        for p in placements:
            final_x = p['x'] + offset_x
            final_y = p['y'] + offset_y
            final_x = max(p['w']/2, min(final_x, work_w - p['w']/2))
            final_y = max(work_y_start + p['h']/2, min(final_y, canvas_h - p['h']/2))
            self.view.canvas.coords(p['obj']['id'], final_x, final_y)
            p['obj']['rel_x'] = final_x / canvas_w if canvas_w > 0 else 0.5
            p['obj']['rel_y'] = final_y / canvas_h if canvas_h > 0 else 0.5
        self.update_status(f"그리드 자동 배치 완료 (크기: {optimal_scale:.1f}%)")

    def apply_linear_layout(self, start_point, end_point):
        images_to_layout = [l for l in self.layers if l.is_visible.get() and isinstance(l, ImageLayer)]
        if not images_to_layout:
            messagebox.showinfo("알림", "자동 배치할 이미지가 없습니다.\n(레이어 목록에서 이미지를 체크해주세요)")
            return

        num_images = len(images_to_layout)
        if num_images == 0: return

        canvas_w, canvas_h = self.view.canvas_controller.get_canvas_size()
        logo_zone_h = canvas_h * (self.settings['logo_zone_height'].get() / 1500.0)
        work_w = canvas_w
        work_h = canvas_h - logo_zone_h
        work_y_start = logo_zone_h

        start_x, start_y = start_point
        end_x, end_y = end_point
        dx = end_x - start_x
        dy = end_y - start_y

        for i, layer in enumerate(images_to_layout):
            obj_info = self.view.canvas_controller.canvas_objects.get(layer.path)
            if not obj_info: continue

            t = 0.5
            if num_images > 1:
                t = i / (num_images - 1)

            current_x = start_x + dx * t
            current_y = start_y + dy * t

            pil_img = obj_info.get('pil_for_display')
            img_w, img_h = (pil_img.width, pil_img.height) if pil_img else (10, 10)

            final_x = max(img_w / 2, min(current_x, work_w - img_w / 2))
            final_y = max(work_y_start + img_h / 2, min(current_y, canvas_h - img_h / 2))

            self.view.canvas.coords(obj_info['id'], final_x, final_y)
            obj_info['rel_x'] = final_x / canvas_w if canvas_w > 0 else 0.5
            obj_info['rel_y'] = final_y / canvas_h if canvas_h > 0 else 0.5

        self.update_status(f"직선 배치 완료 (이미지 {num_images}개)")

    def _get_temp_display_size(self, layer: Layer, scale: float, actual_zoom: float) -> tuple[int, int] | None:
        if isinstance(layer, ImageLayer):
            content_w, content_h = layer.get_content_dimensions()
            pil_w, pil_h = layer.pil_img_display.size
            if content_h <= 0: return None
            lh = self.settings['output_height'].get()
            zone_h_log = lh * (self.settings['logo_zone_height'].get() / 1500.0)
            target_h_log = (lh - zone_h_log) * (scale / 100.0)
            ratio = target_h_log / content_h
            dw, dh = int(pil_w * ratio * actual_zoom), int(pil_h * ratio * actual_zoom)
            if dw < 1 or dh < 1: return None
            if layer.angle != 0:
                rad = math.radians(layer.angle)
                cos, sin = abs(math.cos(rad)), abs(math.sin(rad))
                bw, bh = dw*cos + dh*sin, dw*sin + dh*cos
                return int(bw), int(bh)
            else:
                return dw, dh
        elif isinstance(layer, TextLayer):
             try:
                 font = ImageFont.truetype(FontService.get_font_path(layer.font_family), int(scale * actual_zoom))
             except IOError:
                 font = ImageFont.truetype(FontService.get_font_path('malgun.ttf'), int(scale*actual_zoom))
             bbox = font.getbbox(layer.text)
             w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
             if layer.angle != 0:
                 rad = math.radians(layer.angle)
                 cos, sin = abs(math.cos(rad)), abs(math.sin(rad))
                 bw, bh = w*cos + h*sin, w*sin + h*cos
                 return max(1,int(bw)), max(1,int(bh))
             else:
                 return max(1,w), max(1,h)
        elif isinstance(layer, ShapeLayer):
             size = scale * actual_zoom
             if layer.angle != 0:
                 return int(size * 1.414), int(size * 1.414)
             else:
                 return int(size), int(size)
        return None

    def reset_grid(self):
        for row in self.view.grid_vars:
            for var in row:
                var.set(False)
        self.update_status("그리드 선택 초기화.")

    def start_linear_placement_mode(self):
        if self.is_line_placement_mode:
            self.cancel_linear_placement_mode()
            return

        self.is_line_placement_mode = True
        self.line_start_point = None
        self.line_end_point = None
        self.view.canvas.config(cursor="crosshair")
        self.view.linear_layout_button.config(text="배치 취소", command=self.cancel_linear_placement_mode)
        self.update_status("직선 배치: 시작점을 클릭하세요.")

    def cancel_linear_placement_mode(self):
        self.is_line_placement_mode = False
        self.line_start_point = None
        self.line_end_point = None
        self.view.canvas.config(cursor="")
        self.view.linear_layout_button.config(text="직선 배치 시작", command=self.start_linear_placement_mode)
        self.update_status("직선 배치 취소됨.")
        self.view.canvas.delete("placement_preview_line")
        self.view.canvas.delete("placement_marker")

    def handle_canvas_click_for_line(self, event):
        if not self.is_line_placement_mode:
            return False

        x = self.view.canvas.canvasx(event.x)
        y = self.view.canvas.canvasy(event.y)

        if self.line_start_point is None:
            self.line_start_point = (x, y)
            self.update_status("직선 배치: 끝점을 클릭하세요.")
            self.view.canvas.delete("placement_marker")
            self.view.canvas.create_oval(x-3, y-3, x+3, y+3, fill=Colors.MAIN_RED, outline="", tags="placement_marker")
        else:
            self.line_end_point = (x, y)
            self.update_status("직선 배치 적용 중...")
            self.view.canvas.delete("placement_marker")
            self.view.canvas.delete("placement_preview_line")
            self.apply_linear_layout(self.line_start_point, self.line_end_point)
            self.cancel_linear_placement_mode()

        return True

    def pick_color_from_canvas(self, event):
        x, y = self.view.canvas.canvasx(event.x), self.view.canvas.canvasy(event.y)
        items = self.view.canvas.find_overlapping(x-1,y-1,x+1,y+1)

        top_id = self.view.event_handler._find_topmost_item(event, items)
        if not top_id:
            self._exit_color_pick_mode("⚠️ 객체 없음.")
            return

        tags = self.view.canvas.gettags(top_id)
        if any(t in tags for t in ['border', 'handle', 'rotate_handle']):
            self._exit_color_pick_mode("⚠️ 핸들/테두리 불가.")
            return

        path = next((t for t in tags if t not in ["item"]), None)
        obj_info = self.view.canvas_controller.get_object_info_by_id(top_id)
        color = None
        if obj_info:
            layer = self.get_layer_by_path(path) if path != 'logo' else None
            if layer and hasattr(layer, 'color'):
                color = layer.color
            elif obj_info.get('pil_for_display'):
                pil = obj_info['pil_for_display']
                try:
                    cx, cy = self.view.canvas.coords(top_id)
                    w, h = pil.width, pil.height
                    rx, ry = x-cx, y-cy
                    angle = obj_info.get('angle',0)
                    rad = math.radians(-angle)
                    cos, sin = math.cos(rad), math.sin(rad)
                    urx, ury = rx*cos - ry*sin, rx*sin + ry*cos
                    ix, iy = int(urx + w/2), int(ury + h/2)
                    if 0 <= ix < w and 0 <= iy < h:
                        p = pil.convert("RGBA").getpixel((ix,iy))
                        color = f"#{p[0]:02x}{p[1]:02x}{p[2]:02x}".upper() if p[3]>10 else None
                except Exception as e:
                    self.update_status(f"⚠️ 추출 오류: {e}")
                    traceback.print_exc()

        if color:
            self.settings['palette_color'].set(color)
            self._exit_color_pick_mode(f"색상 추출: {color}")
        else:
            self._exit_color_pick_mode("⚠️ 색상 정보 없거나 투명함.")

    def _exit_color_pick_mode(self, msg=""):
        self.is_color_picking_mode = False
        self.view.canvas.config(cursor="")
        self.update_status(msg or "색상 추출 모드 해제.")