# 파일 경로: controllers/event_handler.py

import tkinter as tk
import math

class EventHandler:
    """캔버스, 레이어 리스트 등에서 발생하는 모든 사용자 입력을 처리하는 클래스"""
    def __init__(self, controller, canvas, canvas_controller):
        self.controller = controller
        self.canvas = canvas
        self.canvas_controller = canvas_controller
        self._drag_data = {"x": 0, "y": 0, "item": None}
        self._resize_data = {}
        self._rotation_data = {}
        
        self._bind_events()

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)

    def _on_press(self, event: tk.Event):
        if self.controller.is_color_picking_mode:
            self.controller.pick_color_from_canvas(event)
            return

        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        overlapping = self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1)
        
        # 리사이즈/회전 핸들러 클릭 확인
        handle = next((i for i in overlapping if "handle" in self.canvas.gettags(i) or "rotate_handle" in self.canvas.gettags(i)), None)
        if handle and self.canvas_controller.active_selection_path:
            self._start_resize_or_rotate(event, handle, x, y)
            return

        # 투명하지 않은 최상단 객체 찾기
        topmost_item_id = self._find_topmost_item(event, overlapping)
        
        path = None
        if topmost_item_id:
            self._drag_data = {"item": topmost_item_id, "x": x, "y": y}
            tags = self.canvas.gettags(topmost_item_id)
            path = next((tag for tag in tags if tag != "item"), None)
        
        self.controller.select_layer_from_canvas(path, event.state)
        
        if not path and self.canvas_controller.active_selection_path:
            self.canvas_controller.clear_resize_handles()

    def _on_motion(self, event: tk.Event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        if self._rotation_data:
            self.canvas_controller.process_rotation(x, y, self._rotation_data)
            return
            
        if self._resize_data:
            self.canvas_controller.process_resizing(x, y, self._resize_data)
            return

        if self._drag_data.get("item"):
            self.canvas.move(self._drag_data["item"], x - self._drag_data["x"], y - self._drag_data["y"])
            self._drag_data.update(x=x, y=y)

    def _on_release(self, event: tk.Event):
        path = self.canvas_controller.active_selection_path
        
        if self._resize_data or self._rotation_data:
            self.canvas_controller.finalize_resize_or_rotate(path)
            self._resize_data, self._rotation_data = {}, {}
            self.canvas.config(cursor="")
            return

        if self._drag_data.get("item"):
            item_id = self._drag_data["item"]
            tags = self.canvas.gettags(item_id)
            path = next((tag for tag in tags if tag != "item"), None)
            
            if path:
                self.canvas_controller.finalize_object_move(path)
            
            self._drag_data["item"] = None

    def _on_canvas_double_click(self, event: tk.Event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        item_ids = self.canvas.find_closest(x, y)
        path = None
        if item_ids:
            item_id = item_ids[0]
            tags = self.canvas.gettags(item_id)
            if 'border' not in tags and 'handle' not in tags and 'rotate_handle' not in tags:
                path = next((tag for tag in tags if tag != "item"), None)
        
        if path:
            self.canvas_controller.activate_resize_handles(path)

    def _start_resize_or_rotate(self, event, handle, x, y):
        path = self.canvas_controller.active_selection_path
        item_id = self.canvas_controller.canvas_objects[path]['id']
        tags = self.canvas.gettags(handle)
        
        if "rotate_handle" in tags:
            bbox = self.canvas.bbox(item_id)
            center_x, center_y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            start_angle = math.degrees(math.atan2(y - center_y, x - center_x))
            layer = self.controller.get_layer_by_path(path)
            self._rotation_data = {
                "item_id": item_id, 
                "center_x": center_x, 
                "center_y": center_y, 
                "start_angle": start_angle, 
                "initial_item_angle": layer.angle
            }
        else: # 리사이즈 핸들
            handle_type = next((t for t in tags if t not in ["handle", "item"]), None)
            if handle_type:
                bbox = self.canvas.bbox(item_id)
                self._resize_data = {
                    "item_id": item_id, 
                    "handle_type": handle_type, 
                    "start_x": x, 
                    "start_y": y, 
                    "start_bbox": bbox,
                    "is_cropping": (event.state & 0x0004) != 0 # Ctrl 키 누름 여부
                }
    
    def _is_pixel_transparent(self, event: tk.Event, item_id: int) -> bool:
        """캔버스 아이템의 특정 좌표 픽셀이 투명한지 확인합니다."""
        obj_info = self.canvas_controller.get_object_info_by_id(item_id)
        if not obj_info or obj_info.get('type') not in ['image', 'text']:
             # 도형은 투명도 체크 안함
            return False

        pil_img = obj_info.get('pil_for_display')
        if not pil_img or pil_img.mode != 'RGBA':
            return False

        try:
            canvas_x, canvas_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            center_x, center_y = self.canvas.coords(item_id)
            img_w, img_h = pil_img.width, pil_img.height

            # 클릭 좌표를 객체 중심으로 변환
            rel_x, rel_y = canvas_x - center_x, canvas_y - center_y

            # 객체의 회전을 반대로 적용하여 클릭 좌표를 회전시킴
            angle_rad = math.radians(-obj_info.get('angle', 0.0))
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            unrotated_rel_x = rel_x * cos_a - rel_y * sin_a
            unrotated_rel_y = rel_x * sin_a + rel_y * cos_a

            # 회전된 좌표를 이미지 내 좌표로 변환
            img_x = unrotated_rel_x + img_w / 2
            img_y = unrotated_rel_y + img_h / 2

            if not (0 <= img_x < img_w and 0 <= img_y < img_h):
                return True # 이미지 바깥을 클릭한 경우 투명으로 처리

            # 픽셀의 알파 값 확인
            return pil_img.getpixel((int(img_x), int(img_y)))[3] < 10

        except Exception:
            return True # 오류 발생 시 투명으로 간주하여 선택 방지
            
    def _find_topmost_item(self, event, overlapping_items):
        all_items_in_order = self.canvas.find_all()
        for item_id in reversed(all_items_in_order):
            if item_id in overlapping_items and 'item' in self.canvas.gettags(item_id):
                if not self._is_pixel_transparent(event, item_id):
                    return item_id
        return None