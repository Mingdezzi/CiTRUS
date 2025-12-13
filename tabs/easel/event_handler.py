# 파일 경로: tabs/easel/event_handler.py (Handle Linear Placement Clicks)

import tkinter as tk
import math

class EventHandler:
    """캔버스, 레이어 리스트 등에서 발생하는 모든 사용자 입력을 처리하는 클래스"""
    # [ ★★★★★ MODIFIED: __init__에 view 추가 ★★★★★ ]
    def __init__(self, controller, canvas, canvas_controller, view): # view 추가
        self.controller = controller # EaselController 참조
        self.canvas = canvas
        self.canvas_controller = canvas_controller
        self.view = view # EaselTabView 참조 추가
        self._drag_data = {"x": 0, "y": 0, "item": None}
        self._resize_data = {}
        self._rotation_data = {}

        self._bind_events()

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click) # 더블클릭 이벤트

    def _on_press(self, event: tk.Event):
        # [ ★★★★★ NEW: 직선 배치 모드 클릭 처리 ★★★★★ ]
        if self.controller.is_line_placement_mode:
            handled = self.controller.handle_canvas_click_for_line(event)
            if handled:
                return # 직선 배치 클릭을 처리했으면 여기서 종료

        # --- 기존 색상 추출 모드 처리 ---
        if self.controller.is_color_picking_mode:
            self.controller.pick_color_from_canvas(event)
            return

        # --- 기존 객체/핸들 클릭 처리 ---
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        overlapping = self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1)

        # 핸들러 클릭 확인
        handle = next((i for i in overlapping if "handle" in self.canvas.gettags(i) or "rotate_handle" in self.canvas.gettags(i)), None)
        if handle and self.canvas_controller.active_selection_path:
            self._start_resize_or_rotate(event, handle, x, y)
            return

        topmost_item_id = self._find_topmost_item(event, overlapping)

        path = None
        if topmost_item_id:
            self._drag_data = {"item": topmost_item_id, "x": x, "y": y}
            tags = self.canvas.gettags(topmost_item_id)
            path = "logo" if "logo" in tags else next((tag for tag in tags if tag != "item"), None)

        # 레이어 선택 로직 호출 (Ctrl/Shift 키 상태 전달)
        self.controller.select_layer_from_canvas(path, event.state)

        # 클릭 시 path가 없는데 Ctrl키도 안 눌렀으면 핸들 제거 (선택 해제 시)
        if not path and not ((event.state & 0x0004)): # 0x0004는 Control 키 마스크
             self.canvas_controller.clear_resize_handles()


    def _on_motion(self, event: tk.Event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        # [ ★★★★★ NEW: 직선 배치 중 선 미리보기 (옵션) ★★★★★ ]
        if self.controller.is_line_placement_mode and self.controller.line_start_point:
            start_x, start_y = self.controller.line_start_point
            # 기존 미리보기 선 삭제
            self.canvas.delete("placement_preview_line")
            # 새 미리보기 선 그리기
            self.canvas.create_line(start_x, start_y, x, y,
                                    dash=(4, 2), fill=Colors.DARK_TEAL,
                                    tags="placement_preview_line")
            return # 미리보기 중에는 다른 드래그 동작 안 함

        if self._rotation_data:
            self.canvas_controller.process_rotation(x, y, self._rotation_data)
            return

        if self._resize_data:
            self.canvas_controller.process_resizing(x, y, self._resize_data)
            return

        if self._drag_data.get("item"):
            item_id = self._drag_data["item"]
            dx = x - self._drag_data["x"]
            dy = y - self._drag_data["y"]
            self.canvas.move(item_id, dx, dy)
            self._drag_data.update(x=x, y=y)


    def _on_release(self, event: tk.Event):
        # [ ★★★★★ NEW: 직선 배치 중 선 미리보기 제거 ★★★★★ ]
        if self.controller.is_line_placement_mode:
            self.canvas.delete("placement_preview_line")
            # 클릭 처리는 _on_press에서 하므로 여기서는 할 일 없음
            # return # 일반 릴리즈 로직 실행 방지

        path = self.canvas_controller.active_selection_path

        if self._resize_data or self._rotation_data:
            self.canvas_controller.finalize_resize_or_rotate(path)
            self._resize_data, self._rotation_data = {}, {}
            self.canvas.config(cursor="")
            return

        if self._drag_data.get("item"):
            item_id = self._drag_data["item"]
            tags = self.canvas.gettags(item_id)
            release_path = "logo" if "logo" in tags else next((tag for tag in tags if tag != "item"), None)

            if release_path:
                self.canvas_controller.finalize_object_move(release_path)

            self._drag_data["item"] = None

    def _on_canvas_double_click(self, event: tk.Event):
        # 직선 배치 모드에서는 더블클릭 무시
        if self.controller.is_line_placement_mode:
            return

        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        item_ids = self.canvas.find_closest(x, y)
        path = None
        if item_ids:
            item_id = item_ids[0]
            tags = self.canvas.gettags(item_id)
            # 핸들이나 보더 제외
            if 'border' not in tags and 'handle' not in tags and 'rotate_handle' not in tags:
                path = "logo" if "logo" in tags else next((tag for tag in tags if tag != "item"), None)

        if path:
             self.canvas_controller.activate_resize_handles(path)

             if path != 'logo': # 로고는 속성 편집 없음
                 layer = self.controller.get_layer_by_path(path)
                 if layer:
                     self.controller.edit_layer_properties(layer)
        # 빈 공간 더블클릭 시 아무것도 안 함

    # --- _start_resize_or_rotate, _is_pixel_transparent, _find_topmost_item (변경 없음) ---
    def _start_resize_or_rotate(self, event, handle, x, y):
        path = self.canvas_controller.active_selection_path
        # 로고 핸들 클릭 시에도 리사이즈/회전 안 함
        if not path or path == 'logo':
             if path == 'logo': # 로고 핸들 클릭 시 커서만 변경
                  tags = self.canvas.gettags(handle)
                  if "rotate_handle" in tags: self.canvas.config(cursor="exchange")
                  else: self.canvas.config(cursor="sizing")
             return

        if path not in self.canvas_controller.canvas_objects:
             print(f"경고: 활성 경로 '{path}'가 canvas_objects에 없습니다.")
             return

        item_id = self.canvas_controller.canvas_objects[path]['id']
        tags = self.canvas.gettags(handle)
        layer = self.controller.get_layer_by_path(path)
        if not layer: return

        if "rotate_handle" in tags:
            self.canvas.config(cursor="exchange") # 회전 커서
            bbox = self.canvas.bbox(item_id)
            if not bbox: return
            center_x, center_y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            start_angle = math.degrees(math.atan2(y - center_y, x - center_x))
            self._rotation_data = {
                "item_id": item_id, "center_x": center_x, "center_y": center_y,
                "start_angle": start_angle, "initial_item_angle": layer.angle
            }
        else: # 리사이즈 핸들
            self.canvas.config(cursor="sizing") # 리사이즈 커서
            handle_type = next((t for t in tags if t not in ["handle", "item"]), None)
            if handle_type:
                bbox = self.canvas.bbox(item_id)
                if not bbox: return
                self._resize_data = {
                    "item_id": item_id, "handle_type": handle_type,
                    "start_x": x, "start_y": y, "start_bbox": bbox,
                    "is_cropping": (event.state & 0x0004) != 0 # Ctrl 키 누름 여부
                }

    def _is_pixel_transparent(self, event: tk.Event, item_id: int) -> bool:
        obj_info = self.canvas_controller.get_object_info_by_id(item_id)
        is_checkable = obj_info and (obj_info.get('type') in ['image', 'text', 'logo'] or
                                       (obj_info.get('type') == 'shape' and obj_info.get('shape_type') == '자유곡선'))
        if not is_checkable:
            return False

        pil_img = obj_info.get('pil_for_display')
        if not pil_img or ('A' not in pil_img.mode): # Check if alpha channel exists
             return False # No alpha means not transparent

        try:
            canvas_x, canvas_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            coords = self.canvas.coords(item_id)
            center_x, center_y = coords[0], coords[1]
            img_w, img_h = pil_img.width, pil_img.height

            rel_x, rel_y = canvas_x - center_x, canvas_y - center_y

            angle_rad = math.radians(-obj_info.get('angle', 0.0))
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            unrotated_rel_x = rel_x * cos_a - rel_y * sin_a
            unrotated_rel_y = rel_x * sin_a + rel_y * cos_a

            img_x = unrotated_rel_x + img_w / 2
            img_y = unrotated_rel_y + img_h / 2

            if not (0 <= img_x < img_w and 0 <= img_y < img_h):
                return True # Clicked outside the image bounds (treat as transparent)

            # Get alpha value (last element for RGBA, LA; or use getchannel('A'))
            alpha = pil_img.getpixel((int(img_x), int(img_y)))[-1]
            return alpha < 10 # Consider alpha < 10 as transparent

        except Exception as e:
            print(f"투명도 체크 오류: {e}")
            return True # Error checking, assume transparent

    def _find_topmost_item(self, event, overlapping_items):
        all_items_in_order = self.canvas.find_all()
        for item_id in reversed(all_items_in_order):
            tags = self.canvas.gettags(item_id)
            # 핸들, 보더, 미리보기 선 제외
            if 'item' in tags and "handle" not in tags and "rotate_handle" not in tags and "border" not in tags and "placement_preview_line" not in tags and item_id in overlapping_items:
                 is_logo = "logo" in tags
                 layer_path = next((tag for tag in tags if tag != "item" and tag != "logo"), None)
                 if is_logo or (layer_path and layer_path in self.canvas_controller.canvas_objects):
                    if not self._is_pixel_transparent(event, item_id):
                           return item_id
        return None