# 파일 경로: controllers/main_controller.py (이 코드로 완전히 교체하세요)

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import math
from PIL import Image, ImageTk
from models.layer import Layer, ImageLayer, TextLayer, ShapeLayer
from ui.dialogs import TextPropertiesDialog, ShapePropertiesDialog
from services.project_service import ProjectService
from services.image_service import ImageService

class MainController:
    """
    EaselTab의 모든 로직을 관장하는 메인 컨트롤러.
    데이터(Model)와 UI(View) 사이의 중재자 역할을 함.
    """
    def __init__(self, view):
        self.view = view # EaselTab 참조
        self.layers: list[Layer] = []
        self.logo_object = None # 캔버스 위의 로고 객체
        self.last_selected_anchor_index = None
        self.is_color_picking_mode = False

        # UI 참조 (나중에 set_ui_references로 설정됨)
        self.logo_preview_label = None
        self.status_label = None

        # 설정값들을 딕셔너리로 관리
        self.settings = {
            'logo_path': tk.StringVar(),
            'logo_zone_height': tk.IntVar(value=90),
            'logo_size': tk.IntVar(value=70),
            'style_code': tk.StringVar(),
            'global_scale': tk.DoubleVar(value=30.0),
            'grid_overlap': tk.IntVar(value=70),
            'output_width': tk.IntVar(value=1500),
            'output_height': tk.IntVar(value=1500),
            'output_format': tk.StringVar(value="PNG"),
            'background_color': tk.StringVar(value="#FFFFFF"),
            'save_directory': tk.StringVar(value=os.path.expanduser("~")),
            'zoom': tk.DoubleVar(value=100.0),
            'palette_color': tk.StringVar(value="#FFFFFF")
        }

    def set_ui_references(self, logo_preview_label, status_label):
        """View로부터 UI 위젯 참조를 받음"""
        self.logo_preview_label = logo_preview_label
        self.status_label = status_label

    def get_layers(self) -> list[Layer]:
        return self.layers

    def get_layer_by_path(self, path: str) -> Layer | None:
        return next((l for l in self.layers if l.path == path), None)

    def get_zoom(self) -> float:
        return self.settings['zoom'].get() / 100.0

    def get_settings_values(self) -> dict:
        """저장용: 모든 설정 값을 .get()으로 추출하여 딕셔너리로 반환"""
        return {key: var.get() for key, var in self.settings.items()}

    def update_status(self, text: str):
        if self.status_label:
            self.status_label.config(text=text)

    # --- Layer 데이터 관리 ---
    def add_new_image_layers(self, files: list[str]):
        new_files_added = False
        for f in [f.strip('{}') for f in files]:
            if os.path.isfile(f) and f not in [l.path for l in self.layers if isinstance(l, ImageLayer)]:
                try:
                    self.layers.append(ImageLayer(file_path=f))
                    new_files_added = True
                except Exception as e:
                    print(f"Error creating ImageLayer for {f}: {e}")

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
                layer.text = dialog.result['text']
                layer.font_family = dialog.result['font_family']
                layer.color = dialog.result['color']
                layer.scale_var.set(dialog.result['font_size'])
                self.view.canvas_controller.update_object_display(layer, self.get_zoom())
                self.view.layer_list.populate_list(self.layers)
        # TODO: 도형 속성 편집도 추가 가능

    def delete_layers(self, layers_to_delete: list[Layer]):
        if not layers_to_delete:
            messagebox.showinfo("알림", "삭제할 항목을 선택해주세요.")
            return

        layer_names = ", ".join([l.get_display_name()[:20] for l in layers_to_delete])
        if messagebox.askyesno("삭제 확인", f"{len(layers_to_delete)}개 항목을 삭제하시겠습니까?\n({layer_names})"):
            for layer in layers_to_delete:
                if layer in self.layers:
                    layer.is_visible.set(False) # 캔버스에서 먼저 제거
                    self.toggle_layer_visibility(layer)
                    self.layers.remove(layer)

            self.view.layer_list.populate_list(self.layers)
            self.update_status(f"{len(layers_to_delete)}개 항목 삭제 완료.")

    def delete_selected_layers(self):
        selected = [l for l in self.layers if l.selected]
        self.delete_layers(selected)

    def toggle_layer_visibility(self, layer: Layer):
        if layer.is_visible.get():
            self.view.canvas_controller.add_layer_to_canvas(layer)
        else:
            self.view.canvas_controller.remove_layer_from_canvas(layer)

    def update_layer_properties(self, layer: Layer):
        """레이어 속성 (e.g. 크기) 변경 시 호출"""
        if layer.is_visible.get():
            self.view.canvas_controller.update_object_display(layer, self.get_zoom())

    def clear_all(self):
        if not messagebox.askyesno("확인", "모든 작업 내용을 초기화하시겠습니까?"):
            return
        self.layers.clear()
        self.view.canvas_controller.canvas_objects.clear()
        self.view.canvas_controller.clear_resize_handles()
        self.view.canvas.delete("all")
        self.delete_logo(confirm=False) # 로고도 삭제
        self.settings['style_code'].set("")
        self.reset_grid()

        self.view.layer_list.populate_list(self.layers)
        self.update_status("모든 항목이 초기화되었습니다.")

    # --- 레이어 목록(List) 관련 로직 ---
    def select_layer_from_list(self, clicked_index, event_state):
        is_shift = (event_state & 0x0001)
        is_ctrl = (event_state & 0x0004)

        if is_shift and self.last_selected_anchor_index is not None:
            start, end = min(self.last_selected_anchor_index, clicked_index), max(self.last_selected_anchor_index, clicked_index)
            for i, layer in enumerate(self.layers):
                layer.selected = (start <= i <= end)
        elif is_ctrl:
            self.layers[clicked_index].selected = not self.layers[clicked_index].selected
            self.last_selected_anchor_index = clicked_index
        else:
            clicked_path = self.layers[clicked_index].path
            is_already_solely_selected = sum(1 for l in self.layers if l.selected) == 1 and self.layers[clicked_index].selected

            for l in self.layers: l.selected = False

            if not is_already_solely_selected:
                self.layers[clicked_index].selected = True
                self.last_selected_anchor_index = clicked_index
            else: # 이미 단독 선택된 항목을 다시 클릭 -> 선택 해제
                self.last_selected_anchor_index = None

        self.view.layer_list.update_selection_visuals(self.layers)
        self.view.update_select_all_button_state()

    def select_layer_from_canvas(self, path, event_state):
        is_ctrl = (event_state & 0x0004)

        target_layer = self.get_layer_by_path(path)

        # 로고 선택 처리
        if path == 'logo':
            # 컨트롤키 없이 로고 클릭 시 다른 모든 레이어 선택 해제
            if not is_ctrl:
                for l in self.layers: l.selected = False
            # 로고는 선택/해제 토글 불가 (단순 활성화만)
            # 여기서는 로고가 선택되었다는 시각적 표시만 함 (파란 테두리)
        else: # 일반 레이어 선택 처리
            if not is_ctrl:
                is_already_solely_selected = sum(1 for l in self.layers if l.selected) == 1 and (target_layer and target_layer.selected)
                for l in self.layers:
                    l.selected = False
                if is_already_solely_selected:
                    target_layer = None # 선택 해제

            if target_layer:
                target_layer.selected = not target_layer.selected if is_ctrl else True

        # 선택된 레이어(또는 로고)가 있으면 핸들러 활성화
        if path:
            self.view.canvas_controller.activate_resize_handles(path)
        else: # 캔버스 빈 곳 클릭 시 핸들러 제거
            self.view.canvas_controller.clear_resize_handles()
            if not is_ctrl: # 컨트롤 키 없이 빈 곳 클릭 시 모든 선택 해제
                for l in self.layers: l.selected = False

        self.view.layer_list.update_selection_visuals(self.layers)
        self.view.update_select_all_button_state()


    def toggle_all_layer_selection(self):
        are_all_selected = all(l.selected for l in self.layers)
        for l in self.layers:
            l.selected = not are_all_selected
        self.view.layer_list.update_selection_visuals(self.layers)
        self.view.update_select_all_button_state()

    def move_layer_in_list(self, source_index, dest_index):
        layer = self.layers.pop(source_index)
        self.layers.insert(dest_index, layer)
        self.view.layer_list.populate_list(self.layers)

    def finalize_layer_reorder(self):
        self.view.canvas_controller.reorder_canvas_layers()

    # --- 서비스 연동 ---
    def save_project(self):
        # 로고 객체는 캔버스 컨트롤러에 없으므로 별도 처리
        canvas_objects_data = self.view.canvas_controller.canvas_objects.copy()
        if self.logo_object:
            canvas_objects_data['logo'] = {
                'rel_x': self.logo_object['rel_x'],
                'rel_y': self.logo_object['rel_y']
            }

        status = ProjectService.save_project(
            self.get_settings_values(),
            self.layers,
            canvas_objects_data
        )
        if status: self.update_status(status)

    def load_project(self):
        if not messagebox.askyesno("불러오기 확인", "현재 작업 내용이 모두 사라집니다. 계속하시겠습니까?"):
            return

        project_data = ProjectService.load_project()
        if not project_data:
            return

        self.clear_all() # UI 및 데이터 초기화

        # 설정 적용
        settings_data = project_data.get('settings', {})
        for key, var in self.settings.items():
            if key in settings_data:
                var.set(settings_data[key])

        # 레이어 로드
        self.layers = project_data.get('layers', [])
        self.view.layer_list.populate_list(self.layers)

        canvas_positions = project_data.get('canvas_positions', {})

        # 캔버스 객체 복원 (위치 설정은 나중에 일괄 업데이트)
        initial_canvas_objects = {}
        for layer in self.layers:
            if layer.is_visible.get():
                # self.toggle_layer_visibility(layer) # 아이템 생성은 여기서 안함
                if layer.path in canvas_positions:
                    pos = canvas_positions[layer.path]
                    # 임시로 위치 정보만 저장
                    initial_canvas_objects[layer.path] = {'rel_x': pos['rel_x'], 'rel_y': pos['rel_y']}

        # 로고 복원 (위치 설정은 나중에 일괄 업데이트)
        initial_logo_pos = None
        if self.settings['logo_path'].get() and 'logo' in canvas_positions:
            initial_logo_pos = canvas_positions['logo']


        # UI 업데이트 및 캔버스 아이템 생성 강제
        self.view.update_idletasks()
        self.view._update_canvas_view() # 캔버스 크기 계산

        # 실제 캔버스 아이템 생성 및 위치 설정
        for layer in self.layers:
             if layer.is_visible.get():
                self.view.canvas_controller.add_layer_to_canvas(layer)
                if layer.path in initial_canvas_objects:
                    self.view.canvas_controller.canvas_objects[layer.path].update(initial_canvas_objects[layer.path])

        if initial_logo_pos:
            self._add_logo_to_canvas()
            if self.logo_object:
                 self.logo_object.update(initial_logo_pos)


        # 모든 객체 위치 및 표시 최종 업데이트
        self.view.canvas_controller.update_all_objects_display(self.get_zoom())
        self.update_status(f"프로젝트 불러오기 완료: {os.path.basename(project_data.get('path', ''))}") # 경로 정보 추가 필요


    def save_image(self):
        # 로고 객체 정보 추가
        layers_with_logo = self.layers.copy()
        canvas_objects_with_logo = self.view.canvas_controller.canvas_objects.copy()

        if self.logo_object:
            # TODO: 로고를 'Layer'처럼 취급하여 렌더링 파이프라인에 태우는 것이 더 좋음
            # 임시로 settings에 로고 정보를 전달
            settings = self.get_settings_values()
            settings['logo_info'] = self.logo_object
        else:
            settings = self.get_settings_values()

        status = ImageService.save_canvas_as_image(
            settings,
            layers_with_logo,
            canvas_objects_with_logo
        )
        if status: self.update_status(status)

    def remove_layer_background(self, layer: Layer):
        if not isinstance(layer, ImageLayer): return

        self.update_status(f"'{layer.get_display_name()}' 배경 제거 중...")
        success = ImageService.remove_background(layer)
        if success:
            self.view.layer_list.populate_list(self.layers)
            if layer.is_visible.get():
                self.view.canvas_controller.update_object_display(layer, self.get_zoom())
            self.update_status("배경 제거 완료!")
        else:
            self.update_status("배경 제거 실패.")

    # --- 유틸리티 ---
    def _set_default_style_code(self):
        image_layers = [l for l in self.layers if isinstance(l, ImageLayer)]
        if image_layers:
            common_prefix = os.path.commonprefix([os.path.basename(l.path) for l in image_layers])
            self.settings['style_code'].set(common_prefix[:8])

    def apply_global_scale(self):
        selected_layers = [l for l in self.layers if l.selected]
        if not selected_layers:
            messagebox.showwarning("알림", "크기를 변경할 레이어를 먼저 선택하세요.")
            return

        scale_val = self.settings['global_scale'].get()
        for layer in selected_layers:
            layer.scale_var.set(scale_val)

        self.update_status(f"{len(selected_layers)}개 항목 크기 변경 완료.")

    # --- 누락되었던 로고 관련 로직 ---
    def select_logo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png")])
        if path:
            self.settings['logo_path'].set(path)
            self._add_logo_to_canvas() # 캔버스에도 추가

    def delete_logo(self, confirm=True):
        if confirm and not messagebox.askyesno("확인", "로고를 삭제하시겠습니까?"):
            return

        if self.logo_object:
            self.view.canvas.delete(self.logo_object['id'])
            self.logo_object = None
        self.settings['logo_path'].set("")
        self.update_logo_preview()
        self.update_status("로고가 삭제되었습니다.")

    def on_logo_panel_drop(self, event):
        files = [f.strip('{}') for f in self.view.winfo_toplevel().tk.splitlist(event.data)]
        if files:
            first_valid_file = next((f for f in files if os.path.isfile(f) and f.endswith('.png')), None)
            if first_valid_file:
                self.settings['logo_path'].set(first_valid_file)
                self._add_logo_to_canvas()
            else:
                messagebox.showwarning("오류", "유효한 .png 파일이 없습니다.")

    def _add_logo_to_canvas(self):
        path = self.settings['logo_path'].get()
        if not path: return

        if self.logo_object:
            self.view.canvas.delete(self.logo_object['id'])
            self.logo_object = None

        try:
            pil_img_original = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("오류", f"로고 파일을 여는 데 실패했습니다: {e}")
            return

        # --- 로고 위치 계산 수정 ---
        # 캔버스 크기 및 실제 줌 레벨 가져오기
        canvas_w, canvas_h = self.view.canvas_controller.get_canvas_size()
        actual_zoom = self.view.canvas_controller.fit_scale * self.get_zoom()
        if canvas_w <= 1 : return # 캔버스가 아직 그려지지 않음

        # 화면에 표시될 PIL 이미지를 미리 계산해서 최종 너비 가져오기
        display_pil = self._get_display_pil_for_logo(actual_zoom, pil_img_original)
        if not display_pil: return

        # 너비를 기반으로 좌측 정렬 x 좌표 계산
        margin = 15 * actual_zoom # 확대/축소 고려한 여백
        x = margin + (display_pil.width / 2)

        # y 좌표 계산
        logo_zone_h = canvas_h * (self.settings['logo_zone_height'].get() / 1500.0)
        y = logo_zone_h / 2
        # --- 수정 끝 ---

        item_id = self.view.canvas.create_image(x, y, tags=("item", "logo"))

        self.logo_object = {
            'id': item_id,
            'type': 'logo',
            'pil_img_original': pil_img_original, # 원본 PIL 이미지 참조 저장
            'tk_img': None,
            'pil_for_display': None,
            'rel_x': x / canvas_w if canvas_w > 0 else 0.5,
            'rel_y': y / canvas_h if canvas_h > 0 else 0.1,
            'path': 'logo',
            'original_path': path,
            'angle': 0.0 # 로고는 회전 없음
        }
        self.update_logo_object_display()
        self.view.canvas_controller.reorder_canvas_layers()


    def update_logo_object_display(self):
        if not self.logo_object: return

        obj_info = self.logo_object
        zoom = self.get_zoom()
        canvas_w, canvas_h = self.view.canvas_controller.get_canvas_size(zoom)
        if canvas_w <= 1: return

        x, y = obj_info['rel_x'] * canvas_w, obj_info['rel_y'] * canvas_h
        actual_zoom = self.view.canvas_controller.fit_scale * zoom

        pil_img = self._get_display_pil_for_logo(actual_zoom) # 원본 이미지 참조 필요 없음

        if pil_img:
            # Tkinter PhotoImage가 GC되지 않도록 참조 유지
            obj_info['tk_img'] = ImageTk.PhotoImage(pil_img)
            obj_info['pil_for_display'] = pil_img
            self.view.canvas.itemconfig(obj_info['id'], image=obj_info['tk_img'])
            self.view.canvas.coords(obj_info['id'], x, y)


    def _get_display_pil_for_logo(self, actual_zoom: float, pil_img_to_process=None) -> Image.Image | None:
        """로고 표시용 PIL 이미지를 생성 (로고 추가 시 원본 이미지를 받아 처리)"""
        if pil_img_to_process is None:
            if not self.logo_object: return None
            pil_img_to_process = self.logo_object['pil_img_original']

        scale = self.settings['logo_size'].get()
        canvas_h = self.settings['output_height'].get()

        target_h = canvas_h * (self.settings['logo_zone_height'].get() / 1500.0) * (scale / 100.0)

        ratio = target_h / pil_img_to_process.height if pil_img_to_process.height > 0 else 0
        new_w, new_h = int(pil_img_to_process.width * ratio), int(target_h)
        display_w, display_h = int(new_w * actual_zoom), int(new_h * actual_zoom)

        if display_w < 1 or display_h < 1: return None

        return pil_img_to_process.resize((display_w, display_h), Image.Resampling.LANCZOS)


    def update_logo_preview(self):
        if not self.logo_preview_label or not self.logo_preview_label.winfo_exists():
            # UI가 아직 준비되지 않았으면 나중에 다시 시도
            self.view.after(100, self.update_logo_preview)
            return

        path = self.settings['logo_path'].get()
        if path and os.path.exists(path):
            try:
                img = Image.open(path)
                # 라벨 크기가 0이면 업데이트 연기
                w, h = self.logo_preview_label.winfo_width()-10, self.logo_preview_label.winfo_height()-10
                if w < 1 or h < 1:
                    self.view.after(100, self.update_logo_preview)
                    return
                img.thumbnail((w,h), Image.Resampling.LANCZOS)
                # logo_preview_image를 인스턴스 변수로 만들어 참조 유지
                self.logo_preview_image = ImageTk.PhotoImage(img)
                self.logo_preview_label.config(image=self.logo_preview_image, text="")
            except Exception as e:
                print(f"로고 미리보기 오류: {e}")
                self.logo_preview_label.config(image="", text="이미지 오류")
        else:
            self.logo_preview_label.config(image="", text="로고 없음\n(파일을 여기로 드래그)")


    def adjust_logo_zone(self, amount: int):
        current = self.settings['logo_zone_height'].get()
        self.settings['logo_zone_height'].set(max(10, min(current + amount, 500)))

    def adjust_logo_size(self, amount: int):
        current = self.settings['logo_size'].get()
        self.settings['logo_size'].set(max(10, min(current + amount, 200)))

    # --- 누락되었던 그리드 관련 로직 ---
    def apply_grid_layout(self):
        images_to_layout = [l for l in self.layers if l.is_visible.get() and isinstance(l, ImageLayer)]
        if not images_to_layout:
            messagebox.showinfo("알림", "캔버스에 배치할 이미지가 없습니다. (레이어 체크 확인)")
            return

        canvas_w, canvas_h = self.view.canvas_controller.get_canvas_size()
        actual_zoom = self.view.canvas_controller.fit_scale * self.get_zoom()
        logo_zone_h = canvas_h * (self.settings['logo_zone_height'].get() / 1500.0)

        work_w, work_h, work_y_start = canvas_w, canvas_h - logo_zone_h, logo_zone_h

        checked_cells = sorted([(r,c) for r, row in enumerate(self.view.grid_vars) for c, var in enumerate(row) if var.get()])

        # --- 목적지 계산 로직 수정 ---
        if not checked_cells:
            # 그리드 선택이 없으면 자동 계산
            num = len(images_to_layout)
            rows = int(math.sqrt(num)) or 1
            cols = math.ceil(num / rows)
            start_r, start_c = (self.view.GRID_SIZE - rows) // 2, (self.view.GRID_SIZE - cols) // 2
            dests = [(start_r + i // cols, start_c + i % cols) for i in range(num)]
        else:
            # 체크된 셀이 있으면 패턴으로 사용
            dests = checked_cells
            # 이미지가 체크된 셀보다 많으면 패턴 반복/외삽 (원본 코드 로직)
            if len(images_to_layout) > len(checked_cells):
                 if len(checked_cells) > 1:
                     dr, dc = checked_cells[-1][0]-checked_cells[-2][0], checked_cells[-1][1]-checked_cells[-2][1]
                     last_r, last_c = checked_cells[-1]
                     for _ in range(len(images_to_layout) - len(checked_cells)):
                         last_r, last_c = last_r+dr, last_c+dc
                         dests.append((last_r, last_c))
                 else: # 체크된 셀이 하나면 그 위치에 모두 배치 (겹침)
                      dests = dests * len(images_to_layout)

        image_data = [{'layer': img, 'grid_r': r, 'grid_c': c} for img, (r, c) in zip(images_to_layout, dests)]
        # --- 수정 끝 ---

        if not image_data: return

        min_r, min_c = min(d['grid_r'] for d in image_data), min(d['grid_c'] for d in image_data)
        spacing = (100 - self.settings['grid_overlap'].get()) / 100.0

        # TODO: 이진 탐색으로 최적 스케일 찾는 로직... (원본 코드 참조)
        # 이 로직은 매우 복잡하며, _get_display_pil을 직접 호출해야 합니다.
        # 지금은 임시로 현재 글로벌 스케일을 적용합니다.
        optimal_scale = self.settings['global_scale'].get()
        # self.apply_global_scale() # 선택된 이미지에 일괄 적용 -> 모든 이미지에 적용해야 함
        target_paths = [img['layer'].path for img in image_data]
        scale_val = self.settings['global_scale'].get()
        for path in target_paths:
             layer = self.get_layer_by_path(path)
             if layer: layer.scale_var.set(scale_val)

        self.view.update_idletasks() # UI 업데이트 강제

        # 스케일 적용 후 크기 다시 계산
        scaled_data = []
        for d in image_data:
            obj_info = self.view.canvas_controller.canvas_objects.get(d['layer'].path)
            if obj_info:
                # update_object_display를 호출하여 최신 PIL 이미지 정보 가져오기
                self.view.canvas_controller.update_object_display(d['layer'], self.get_zoom())
                pil_img = obj_info.get('pil_for_display')
                if pil_img:
                    scaled_data.append({
                        'obj': obj_info,
                        'w': pil_img.width,
                        'h': pil_img.height,
                        'grid_r': d['grid_r'],
                        'grid_c': d['grid_c']
                    })

        if not scaled_data: return

        avg_w = sum(s['w'] for s in scaled_data) / len(scaled_data) if scaled_data else 1
        avg_h = sum(s['h'] for s in scaled_data) / len(scaled_data) if scaled_data else 1
        if avg_w == 0: avg_w = 1 # 0으로 나누기 방지
        if avg_h == 0: avg_h = 1

        placements = [{'obj': s['obj'], 'x': (s['grid_c']-min_c)*avg_w*spacing, 'y': (s['grid_r']-min_r)*avg_h*spacing, 'w':s['w'], 'h':s['h']} for s in scaled_data]

        min_x = min(p['x']-p['w']/2 for p in placements) if placements else 0
        max_x = max(p['x']+p['w']/2 for p in placements) if placements else 0
        min_y = min(p['y']-p['h']/2 for p in placements) if placements else 0
        max_y = max(p['y']+p['h']/2 for p in placements) if placements else 0

        offset_x = work_w/2 - (min_x + (max_x - min_x) / 2)
        offset_y = (work_y_start + work_h/2) - (min_y + (max_y - min_y) / 2)

        for p in placements:
            final_x = p['x'] + offset_x
            final_y = p['y'] + offset_y

            # 캔버스 경계 및 로고 영역 침범 방지
            final_x = max(p['w']/2, min(final_x, work_w - p['w']/2))
            final_y = max(work_y_start + p['h']/2, min(final_y, canvas_h - p['h']/2))

            self.view.canvas.coords(p['obj']['id'], final_x, final_y)
            p['obj']['rel_x'], p['obj']['rel_y'] = final_x / canvas_w, final_y / canvas_h

        self.update_status(f"자동 배치 완료 (크기: {optimal_scale:.1f}%)")


    def reset_grid(self):
        for row in self.view.grid_vars:
            for var in row:
                var.set(False)
        self.update_status("그리드 선택이 초기화되었습니다.")

    def pick_color_from_canvas(self, event):
        # TODO: EventHandler로 이관 고려
        x, y = self.view.canvas.canvasx(event.x), self.view.canvas.canvasy(event.y)
        item_ids = self.view.canvas.find_closest(x, y)
        if not item_ids:
            self._exit_color_pick_mode()
            return

        item_id = item_ids[0]
        tags = self.view.canvas.gettags(item_id)
        if 'border' in tags or 'handle' in tags or 'rotate_handle' in tags:
            self._exit_color_pick_mode()
            return

        path = next((tag for tag in tags if tag not in ["item", "logo"]), None)
        is_logo = "logo" in tags

        color_found = None

        if is_logo and self.logo_object:
            obj_info = self.logo_object
            layer_info = None # 로고는 Layer 객체가 아님
        elif path:
            obj_info = self.view.canvas_controller.canvas_objects.get(path)
            layer_info = self.get_layer_by_path(path)
        else:
            self._exit_color_pick_mode()
            return

        if obj_info and (obj_info['type'] in ['image', 'logo', 'text'] or (obj_info['type']=='shape' and obj_info.get('shape_type')=='자유곡선')):
            pil_img = obj_info.get('pil_for_display')
            if pil_img:
                try:
                    center_x, center_y = self.view.canvas.coords(item_id)
                    img_w, img_h = pil_img.width, pil_img.height

                    rel_x = x - center_x
                    rel_y = y - center_y

                    angle = layer_info.angle if layer_info else 0.0 # 로고는 0도
                    angle_rad = math.radians(-angle)
                    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

                    unrotated_rel_x = rel_x * cos_a - rel_y * sin_a
                    unrotated_rel_y = rel_x * sin_a + rel_y * cos_a

                    img_x = unrotated_rel_x + img_w / 2
                    img_y = unrotated_rel_y + img_h / 2

                    if 0 <= img_x < img_w and 0 <= img_y < img_h:
                        pixel = pil_img.convert("RGBA").getpixel((int(img_x), int(img_y)))
                        if pixel[3] > 10: # 투명하지 않은 부분만 추출
                             color_found = f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}".upper()

                except Exception as e:
                    self.update_status(f"⚠️ 색상 추출 오류: {e}")

        elif layer_info and hasattr(layer_info, 'color'): # 도형 또는 텍스트의 기본 색상
            color_found = layer_info.color

        if color_found:
            self.settings['palette_color'].set(color_found)
            self.update_status(f"색상 추출 완료: {color_found}")
        else:
            self.update_status("⚠️ 색상 정보를 추출할 수 없거나 투명한 영역입니다.")

        self._exit_color_pick_mode()


    def _exit_color_pick_mode(self):
        self.is_color_picking_mode = False
        self.view.canvas.config(cursor="")
        # self.update_status("색상 추출 모드가 해제되었습니다.") # 상태 메시지는 추출 성공/실패 시 업데이트됨