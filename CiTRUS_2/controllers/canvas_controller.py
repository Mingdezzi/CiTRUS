# 파일 경로: controllers/canvas_controller.py (이 코드로 완전히 교체하세요)

import tkinter as tk
import math
from PIL import Image, ImageTk, ImageFont
from models.layer import Layer, ImageLayer, TextLayer, ShapeLayer
from services.font_service import FontService

class CanvasController:
    """캔버스 위의 객체(레이어)를 직접 제어하고 상태를 관리하는 클래스"""
    def __init__(self, canvas, controller):
        self.canvas = canvas
        self.controller = controller # MainController 참조
        self.canvas_objects = {}  # {layer.path: {id, rel_x, ...}}
        self.active_selection_path = None
        
        self.fit_scale = 1.0

    def add_layer_to_canvas(self, layer: Layer):
        if layer.path in self.canvas_objects:
            return
        
        w, h = self.get_canvas_size()
        if w <= 1: return
        
        # 기본 위치 계산 (로고 영역 피하기)
        logo_zone_h = h * (self.controller.settings['logo_zone_height'].get() / 1500.0)
        x, y = w / 2, logo_zone_h + (h - logo_zone_h) / 2
        
        # 도형은 create_polygon, 나머지는 create_image 사용
        if isinstance(layer, ShapeLayer) and layer.shape_type != '자유곡선':
            item_id = self.canvas.create_polygon(0, 0, tags=("item", layer.path))
        else:
            item_id = self.canvas.create_image(x, y, tags=("item", layer.path))
        
        self.canvas_objects[layer.path] = {
            'id': item_id,
            'type': layer.type,
            'rel_x': x / w,
            'rel_y': y / h,
            'path': layer.path,
            'tk_img': None,
            'pil_for_display': None,
            'angle': 0.0,
        }
        self.update_object_display(layer, self.controller.get_zoom())
        self.reorder_canvas_layers()

    def remove_layer_from_canvas(self, layer: Layer):
        if self.active_selection_path == layer.path:
            self.clear_resize_handles()
        
        if layer.path in self.canvas_objects:
            obj_info = self.canvas_objects.pop(layer.path)
            self.canvas.delete(obj_info['id'])

    def update_all_objects_display(self, zoom):
        self.canvas.delete('border')
        w, h = self.get_canvas_size(zoom)
        self.canvas.create_rectangle(0, 0, w - 1, h - 1, dash=(5, 3), outline='grey', tags='border')
        
        for layer in self.controller.get_layers():
            if layer.is_visible.get():
                self.update_object_display(layer, zoom)

    def update_object_display(self, layer: Layer, zoom: float):
        if layer.path not in self.canvas_objects: return
        
        obj_info = self.canvas_objects[layer.path]
        canvas_w, canvas_h = self.get_canvas_size(zoom)
        if canvas_w <= 1: return

        x, y = obj_info['rel_x'] * canvas_w, obj_info['rel_y'] * canvas_h
        actual_zoom = self.fit_scale * zoom
        
        # --- 여기가 핵심 수정 부분 ---
        
        # 1. 객체 타입이 '일반 도형'인 경우 (자유곡선 제외)
        if isinstance(layer, ShapeLayer) and layer.shape_type != '자유곡선':
            points = layer._get_shape_points((x, y), layer.scale_var.get() * actual_zoom)
            if layer.angle != 0:
                points = self._rotate_points(points, (x, y), -layer.angle)
            
            self.canvas.coords(obj_info['id'], points)
            # 'fill'과 'outline' 옵션만 사용 (image= 옵션 없음)
            self.canvas.itemconfig(obj_info['id'], fill=layer.color, outline=layer.color) 

        # 2. 객체 타입이 '이미지' 또는 '텍스트' 또는 '자유곡선'인 경우
        else:
            pil_img = self._get_display_pil_for_layer(layer, actual_zoom)
            
            if pil_img:
                obj_info['tk_img'] = ImageTk.PhotoImage(pil_img)
                obj_info['pil_for_display'] = pil_img
                obj_info['angle'] = layer.angle
                
                # 'image' 옵션만 사용 (fill= 옵션 없음)
                self.canvas.itemconfig(obj_info['id'], image=obj_info['tk_img']) 
                self.canvas.coords(obj_info['id'], x, y)
            else:
                # PIL 이미지 생성 실패 시 (e.g., 텍스트가 비어있음)
                self.canvas.coords(obj_info['id'], -100, -100) # 화면 밖으로 이동

        # --- 수정 끝 ---

        if self.active_selection_path == layer.path:
            self.activate_resize_handles(layer.path)

    def _get_display_pil_for_layer(self, layer: Layer, actual_zoom: float) -> Image.Image | None:
        """레이어 타입에 따라 화면 표시용 PIL 이미지를 생성하여 반환"""
        scale = layer.scale_var.get()
        
        if isinstance(layer, TextLayer):
            font_size = int(scale * actual_zoom)
            if font_size < 1: return None
            font = ImageFont.truetype(FontService.get_font_path(layer.font_family), font_size)
            bbox = font.getbbox(layer.text)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if w <= 0 or h <= 0: return None
            
            img = Image.new('RGBA', (w, h))
            draw = ImageDraw.Draw(img)
            draw.text((-bbox[0], -bbox[1]), layer.text, font=font, fill=layer.color)
            return img.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)

        elif isinstance(layer, (ImageLayer, ShapeLayer)): # 이미지 또는 자유곡선
            pil_to_process = None
            if isinstance(layer, ImageLayer):
                pil_to_process = layer.get_pil_image_to_process()
            elif isinstance(layer, ShapeLayer) and layer.shape_type == '자유곡선':
                pil_to_process = layer.pil_image

            if pil_to_process is None: return None
            
            canvas_h = self.controller.settings['output_height'].get()
            logo_zone_h = canvas_h * (self.controller.settings['logo_zone_height'].get() / 1500.0)
            target_h = (canvas_h - logo_zone_h) * (scale / 100.0)
            
            ratio = target_h / pil_to_process.height if pil_to_process.height > 0 else 0
            new_w, new_h = int(pil_to_process.width * ratio), int(target_h)
            display_w, display_h = int(new_w * actual_zoom), int(new_h * actual_zoom)

            if display_w < 1 or display_h < 1: return None
            
            resized = pil_to_process.resize((display_w, display_h), Image.Resampling.LANCZOS)
            return resized.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
            
        return None

    def reorder_canvas_layers(self):
        layers = self.controller.get_layers()
        for layer in reversed(layers):
            if layer.path in self.canvas_objects:
                self.canvas.tag_raise(self.canvas_objects[layer.path]['id'])
        
        # 로고가 있다면 로고를 최상위로
        if self.controller.logo_object:
            self.canvas.tag_raise(self.controller.logo_object['id'])
            
        self.canvas.tag_raise("rotate_handle")
        self.canvas.tag_raise("handle")

    def get_canvas_size(self, zoom=None):
        if zoom is None: zoom = self.controller.get_zoom()
        actual_zoom = self.fit_scale * zoom
        w = int(self.controller.settings['output_width'].get() * actual_zoom)
        h = int(self.controller.settings['output_height'].get() * actual_zoom)
        return w, h

    def get_object_info_by_id(self, item_id):
        # 로고 객체도 확인
        if self.controller.logo_object and self.controller.logo_object['id'] == item_id:
            return self.controller.logo_object
        for info in self.canvas_objects.values():
            if info['id'] == item_id:
                return info
        return None

    def activate_resize_handles(self, path):
        self.clear_resize_handles()
        self.active_selection_path = path
        
        obj_info = None
        if path == 'logo':
            obj_info = self.controller.logo_object
        else:
            obj_info = self.canvas_objects.get(path)
            
        if not obj_info: return

        bbox = self.canvas.bbox(obj_info['id'])
        if not bbox: return
        
        layer = self.controller.get_layer_by_path(path)
        # 로고는 회전/선택 핸들러를 지원하지 않음 (단순화)
        if path == 'logo' or not layer: 
             # 로고 선택 시 파란색 외곽선만 표시
             x0, y0, x1, y1 = bbox
             self.canvas.create_rectangle(x0, y0, x1, y1, outline="blue", width=1, tags="handle")
             return

        x0, y0, x1, y1 = bbox
        center_x, center_y = (x0 + x1) / 2, (y0 + y1) / 2
        w, h = x1 - x0, y1 - y0
        
        unrotated_corners = [center_x-w/2, center_y-h/2, center_x+w/2, center_y-h/2, 
                             center_x+w/2, center_y+h/2, center_x-w/2, center_y+h/2]
        rotated_poly_points = self._rotate_points(unrotated_corners, (center_x, center_y), layer.angle)
        
        self.canvas.create_polygon(rotated_poly_points, outline="blue", width=1, tags="handle", fill="")
        
        x0r, y0r, x1r, y1r, x2r, y2r, x3r, y3r = rotated_poly_points
        coords = [(x0r, y0r, "nw"), (x1r, y1r, "ne"), (x2r, y2r, "se"), (x3r, y3r, "sw")]
        
        h_size = 8
        for x, y, c_type in coords:
            self.canvas.create_rectangle(x-h_size/2, y-h_size/2, x+h_size/2, y+h_size/2, fill="blue", outline="white", width=1, tags=("handle", c_type))

        rh_offset, rh_size = h_size * 2.5, h_size
        rot_handle_center_y = center_y - h/2 - rh_offset
        rotated_rot_handle_point = self._rotate_points([center_x, rot_handle_center_y], (center_x, center_y), layer.angle)
        rx, ry = rotated_rot_handle_point
        self.canvas.create_oval(rx-rh_size/2, ry-rh_size/2, rx+rh_size/2, ry+rh_size/2, fill="orange", outline="white", width=1, tags="rotate_handle")
        
    def clear_resize_handles(self):
        self.canvas.delete("handle")
        self.canvas.delete("rotate_handle")
        self.active_selection_path = None

    def process_rotation(self, x, y, rotation_data):
        d = rotation_data
        current_angle = math.degrees(math.atan2(y - d['center_y'], x - d['center_x']))
        angle_diff = current_angle - d['start_angle']
        
        layer = self.controller.get_layer_by_path(self.active_selection_path)
        if layer:
            layer.angle = d['initial_item_angle'] + angle_diff
            self.update_object_display(layer, self.controller.get_zoom())

    def process_resizing(self, x, y, resize_data):
        path = self.active_selection_path
        layer = self.controller.get_layer_by_path(path)
        if not layer or not isinstance(layer, (ImageLayer, TextLayer, ShapeLayer)): return
        
        d = resize_data
        dx, dy = x - d['start_x'], y - d['start_y']
        
        if d.get("is_cropping") and isinstance(layer, ImageLayer):
            # 자르기 로직 (간소화, 필요시 확장)
            pass 
        else: # 크기 조절
            start_bbox = d["start_bbox"]
            start_w, start_h = start_bbox[2] - start_bbox[0], start_bbox[3] - start_bbox[1]
            if start_w == 0 or start_h == 0: return
            
            rad = -math.radians(layer.angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            dx_rot = dx * cos_a - dy * sin_a
            
            # 비율 유지 (더 큰 쪽의 변화율을 따름)
            scale_change_x = (start_w + dx_rot) / start_w if start_w != 0 else 1.0
            scale_change_y = (start_h + dy) / start_h if start_h != 0 else 1.0 # Y축은 회전 영향 덜 받음
            
            scale_change = scale_change_x # 기본값
            
            handle_type = d.get('handle_type', '')
            if 'n' in handle_type or 's' in handle_type:
                rad_y = -math.radians(layer.angle)
                cos_a_y, sin_a_y = math.cos(rad_y), math.sin(rad_y)
                dy_rot = -dx * sin_a_y + dy * cos_a_y
                scale_change_y = (start_h + dy_rot) / start_h if start_h != 0 else 1.0
                scale_change = scale_change_y
            
            if 'w' in handle_type or 'e' in handle_type:
                scale_change = scale_change_x

            if any(c in handle_type for c in ['nw', 'ne', 'sw', 'se']):
                 scale_change = max(abs(scale_change_x), abs(scale_change_y)) * (1 if scale_change_x > 0 or scale_change_y > 0 else -1)


            initial_scale = getattr(layer, 'initial_scale_on_drag', layer.scale_var.get())
            if not hasattr(layer, 'initial_scale_on_drag'):
                layer.initial_scale_on_drag = initial_scale
            
            new_scale = max(8, initial_scale * scale_change)
            layer.scale_var.set(new_scale)

    def finalize_resize_or_rotate(self, path):
        if path:
            layer = self.controller.get_layer_by_path(path)
            if layer and hasattr(layer, 'initial_scale_on_drag'):
                delattr(layer, 'initial_scale_on_drag')
            if layer and hasattr(layer, 'crop_box_on_drag'):
                delattr(layer, 'crop_box_on_drag')
            
            if layer:
                self.update_object_display(layer, self.controller.get_zoom())

    def finalize_object_move(self, path):
        obj_info = None
        if path == 'logo':
            obj_info = self.controller.logo_object
        else:
            obj_info = self.canvas_objects.get(path)
            
        if not obj_info: return

        canvas_w, canvas_h = self.get_canvas_size(self.controller.get_zoom())
        if canvas_w <= 1: return
        
        item_id = obj_info['id']
        if self.canvas.type(item_id) == 'polygon':
             coords = self.canvas.coords(item_id)
             if not coords: return
             xs, ys = coords[0::2], coords[1::2]
             cur_x, cur_y = sum(xs) / len(xs), sum(ys) / len(ys)
        else:
            coords = self.canvas.coords(item_id)
            if not coords: return
            cur_x, cur_y = coords[0], coords[1]
        
        # --- 로고 영역 제한 ---
        if path == 'logo':
            logo_zone_h = canvas_h * (self.controller.settings['logo_zone_height'].get() / 1500.0)
            bbox = self.canvas.bbox(item_id)
            if bbox:
                item_w, item_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                cur_x = max(item_w/2, min(cur_x, canvas_w - item_w/2))
                cur_y = max(item_h/2, min(cur_y, logo_zone_h - item_h/2))
                self.canvas.coords(item_id, cur_x, cur_y) # 캔버스 위치 보정
        # --- 레이어 영역 제한 ---
        elif path != 'logo':
            logo_zone_h = canvas_h * (self.controller.settings['logo_zone_height'].get() / 1500.0)
            bbox = self.canvas.bbox(item_id)
            if bbox:
                item_w, item_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                cur_x = max(item_w/2, min(cur_x, canvas_w - item_w/2))
                cur_y = max(logo_zone_h + item_h/2, min(cur_y, canvas_h - item_h/2))
                self.canvas.coords(item_id, cur_x, cur_y) # 캔버스 위치 보정
                
        obj_info['rel_x'] = cur_x / canvas_w
        obj_info['rel_y'] = cur_y / canvas_h
        
        if self.active_selection_path == path:
            self.activate_resize_handles(path)

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