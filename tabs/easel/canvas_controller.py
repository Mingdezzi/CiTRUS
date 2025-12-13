# 파일 경로: tabs/easel/canvas_controller.py
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont # [ ★★★★★ 수정: ImageDraw 추가 ★★★★★ ]
import math
import os # 로고 경로 확인 위해 추가

# --- import 경로 수정 ---
from .models.layer import Layer, ImageLayer, TextLayer, ShapeLayer
from .services.font_service import FontService
from .services.image_service import ImageService # 도형 회전 계산 위해 추가

# --- 수정 끝 ---

class CanvasController:
    """캔버스 위의 객체(레이어, 로고) 표시 및 상호작용 로직 관리"""
    def __init__(self, canvas: tk.Canvas, controller):
        self.canvas = canvas
        self.controller = controller # EaselController 참조
        self.canvas_objects = {} # { path: {id, type, tk_img, pil_for_display, rel_x, rel_y, angle, ...}, ... }
        self.active_selection_path: str | None = None
        self.fit_scale = 1.0 # 뷰포트에 맞추기 위한 스케일

    def add_layer_to_canvas(self, layer: Layer):
        """레이어를 캔버스에 추가 (기본 위치)"""
        if layer.path in self.canvas_objects: # 이미 있으면 생성 방지
            return

        canvas_w, canvas_h = self.get_canvas_size()
        center_x, center_y = canvas_w / 2, canvas_h / 2

        # create_image는 이미지를 중앙 정렬하므로 중앙 좌표 사용
        item_id = self.canvas.create_image(center_x, center_y, tags=("item", layer.path))

        self.canvas_objects[layer.path] = {
            'id': item_id,
            'type': layer.type,
            'tk_img': None,
            'pil_for_display': None, # 현재 줌 레벨에 맞게 리사이즈된 PIL 이미지 (투명도 체크용)
            'rel_x': 0.5, # 초기 상대 위치
            'rel_y': 0.5, # 초기 상대 위치
            'angle': layer.angle
        }
        # ShapeLayer인 경우 추가 정보 저장
        if isinstance(layer, ShapeLayer):
            self.canvas_objects[layer.path].update({
                'shape_type': layer.shape_type,
                'color': layer.color,
                'pil_image': layer.pil_image # 자유곡선 원본 PIL (필요 시)
            })

        self.update_object_display(layer, self.controller.get_zoom())
        self.reorder_canvas_layers()

    def remove_layer_from_canvas(self, layer: Layer):
        """레이어를 캔버스에서 제거"""
        if layer.path in self.canvas_objects:
            item_id = self.canvas_objects[layer.path]['id']
            self.canvas.delete(item_id)
            del self.canvas_objects[layer.path]
            # 만약 제거된 레이어가 활성 선택이었다면 핸들도 제거
            if self.active_selection_path == layer.path:
                self.clear_resize_handles()


    def update_object_display(self, layer_or_logo: Layer | dict, zoom: float):
        """지정된 레이어 또는 로고 객체의 캔버스 표시 업데이트 (크기, 회전 등)"""
        is_logo = isinstance(layer_or_logo, dict) and layer_or_logo.get('type') == 'logo'
        path = layer_or_logo.get('path') if is_logo else layer_or_logo.path

        if path not in self.canvas_objects and not is_logo: # 로고는 controller에 별도 저장
             print(f"경고: update_object_display - path '{path}'가 canvas_objects에 없음")
             return

        obj_info = self.controller.logo_object if is_logo else self.canvas_objects[path]
        item_id = obj_info['id']

        canvas_w, canvas_h = self.get_canvas_size(zoom)
        if canvas_w <= 1 : return # 캔버스 크기 유효하지 않으면 종료

        # 실제 줌 레벨 (뷰포트 맞춤 + 사용자 줌)
        actual_zoom = self.fit_scale * zoom

        # 1. 표시용 PIL 이미지 생성/가져오기
        pil_img = None
        if is_logo:
             pil_img = self.controller._get_display_pil_for_logo(actual_zoom)
        else:
             pil_img = self._get_display_pil_for_layer(layer_or_logo, actual_zoom)

        if pil_img is None:
             # 이미지 생성 실패 시 (예: 크기가 너무 작음) 캔버스에서 숨김
             self.canvas.itemconfig(item_id, state='hidden')
             return
        else:
             self.canvas.itemconfig(item_id, state='normal') # 다시 보이게 함


        # 2. Tkinter 이미지 업데이트 및 객체 정보 저장
        obj_info['tk_img'] = ImageTk.PhotoImage(pil_img)
        obj_info['pil_for_display'] = pil_img # 투명도 체크용
        self.canvas.itemconfig(item_id, image=obj_info['tk_img'])

        # 3. 위치 업데이트 (상대 좌표 기준)
        x = obj_info['rel_x'] * canvas_w
        y = obj_info['rel_y'] * canvas_h
        self.canvas.coords(item_id, x, y)

        # 4. 활성 선택이면 핸들 업데이트
        if self.active_selection_path == path:
             self.activate_resize_handles(path) # 핸들 위치/크기 갱신

    # [ ★★★★★ 여기가 수정된 함수입니다 ★★★★★ ]
    def _get_display_pil_for_layer(self, layer: Layer, actual_zoom: float) -> Image.Image | None:
        """주어진 레이어와 줌 레벨에 맞는 표시용 PIL 이미지 생성"""
        img = None
        target_w, target_h = 0, 0
        original_pil = None # 리사이즈 및 회전에 사용할 원본 PIL (ImageLayer의 경우 display용)

        if isinstance(layer, ImageLayer):
            # [ ★★★★★ MODIFIED: 내용물 크기 기준으로 크기 계산 ★★★★★ ]
            original_pil = layer.get_pil_image_to_process() # 크롭 적용된 표시용 이미지
            content_w, content_h = layer.get_content_dimensions() # 내용물 크기 가져오기
            
            canvas_h_logical = self.controller.settings['output_height'].get()
            logo_zone_h_logical = canvas_h_logical * (self.controller.settings['logo_zone_height'].get() / 1500.0)
            
            # 논리적 높이 기준으로 이미지 크기 계산 (내용물 높이 기준)
            target_h_logical = (canvas_h_logical - logo_zone_h_logical) * (layer.scale_var.get() / 100.0)

            if content_h > 0:
                # 내용물 높이(content_h) 대비 목표 높이(target_h_logical) 비율 계산
                ratio = target_h_logical / content_h
                # 최종 표시될 너비/높이는 *전체* 이미지(original_pil) 크기에 비율 적용
                # (주의: content_w가 아닌 original_pil.width 사용)
                target_w = int(original_pil.width * ratio * actual_zoom)
                target_h = int(original_pil.height * ratio * actual_zoom)
            else:
                 return None # 내용물 높이가 0이면 표시 불가

        elif isinstance(layer, TextLayer):
            try:
                # 폰트 크기에 줌 레벨 직접 반영
                font_size = int(layer.scale_var.get() * actual_zoom)
                if font_size < 1: return None # 너무 작으면 표시 불가
                font = ImageFont.truetype(FontService.get_font_path(layer.font_family), font_size)
                # Pillow 10.0.0 이후 getsize -> getbbox 권장
                # bbox = font.getsize(layer.text) # (width, height) - Pillow < 10.0.0
                bbox = font.getbbox(layer.text) # (left, top, right, bottom) - Pillow >= 10.0.0
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                if text_w <= 0 or text_h <= 0: return None

                img = Image.new('RGBA', (text_w, text_h), (0, 0, 0, 0)) # 투명 배경
                draw = ImageDraw.Draw(img) # ImageDraw import 필요
                # bbox 기준으로 그리기 (텍스트 시작 위치 조정)
                draw.text((-bbox[0], -bbox[1]), layer.text, font=font, fill=layer.color)
                original_pil = img # 회전 적용 위해 설정
                # 텍스트 레이어는 target_w, target_h가 필요 없음 (img 크기 자체가 최종 크기)

            except Exception as e:
                print(f"텍스트 이미지 생성 오류: {e}")
                return None

        elif isinstance(layer, ShapeLayer):
            if layer.shape_type == '자유곡선':
                original_pil = layer.pil_image # 저장된 PIL 이미지 사용
                if original_pil:
                     scale_factor = layer.scale_var.get() / 100.0
                     target_w = int(original_pil.width * scale_factor * actual_zoom)
                     target_h = int(original_pil.height * scale_factor * actual_zoom)
                else: return None
            else: # 일반 도형 (사각형, 삼각형 등)
                 # 도형 크기에 줌 레벨 직접 반영
                 size = layer.scale_var.get() * actual_zoom
                 if size < 1: return None
                 points = layer._get_shape_points((0, 0), size)
                 if not points: return None

                 # 회전을 여기서 먼저 적용 (리사이즈 전에)
                 if layer.angle != 0:
                    # ImageService의 _rotate_points 사용 (center=(0,0))
                    points = ImageService._rotate_points(points, (0, 0), -layer.angle)

                 xs, ys = zip(*[(points[i], points[i+1]) for i in range(0, len(points), 2)])
                 min_x, max_x = min(xs), max(xs)
                 min_y, max_y = min(ys), max(ys)
                 width, height = int(max_x - min_x) + 1, int(max_y - min_y) + 1
                 if width <= 0 or height <= 0: return None

                 img = Image.new('RGBA', (width, height), (0,0,0,0))
                 shape_draw = ImageDraw.Draw(img)
                 # 평행 이동된 좌표로 폴리곤 그리기
                 shifted_points = [(x - min_x, y - min_y) for x, y in zip(xs, ys)]
                 shape_draw.polygon(shifted_points, fill=layer.color)
                 # 도형은 여기서 최종 이미지 생성 완료 (회전 이미 적용됨)
                 return img # 리사이즈/회전 로직 건너뛰기

        # --- 이미지 리사이즈 및 회전 (이미지, 텍스트, 자유곡선 공통) ---
        if original_pil is None: return None
        
        # 텍스트 레이어는 target_w, target_h가 설정되지 않았으므로 여기서 처리
        if isinstance(layer, TextLayer):
            if layer.angle != 0:
                return original_pil.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
            else:
                return original_pil # 회전 없으면 그대로 반환
        
        # 이미지, 자유곡선 레이어 처리
        if target_w < 1 or target_h < 1: return None

        try:
            # 리사이즈
            resized_img = original_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
            # 회전
            if layer.angle != 0:
                return resized_img.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
            else:
                return resized_img
        except Exception as e:
            print(f"이미지 처리 오류 ({layer.path}): {e}")
            return None


    def update_all_objects_display(self, zoom: float):
        """캔버스의 모든 객체(레이어, 로고) 표시 업데이트"""
        # 레이어 업데이트
        for layer in self.controller.get_layers():
            if layer.is_visible.get():
                self.update_object_display(layer, zoom)
        # 로고 업데이트
        if self.controller.logo_object:
            self.update_object_display(self.controller.logo_object, zoom)


    def reorder_canvas_layers(self):
        """레이어 리스트 순서에 맞게 캔버스 객체 쌓임 순서 변경"""
        # 로고가 있으면 맨 위로
        if self.controller.logo_object:
             self.canvas.lift(self.controller.logo_object['id'])

        # 레이어 리스트의 역순으로 lift (아래쪽 레이어부터 위로 올림)
        for layer in reversed(self.controller.get_layers()):
            if layer.path in self.canvas_objects:
                self.canvas.lift(self.canvas_objects[layer.path]['id'])

    def get_canvas_size(self, zoom: float = None) -> tuple[int, int]:
        """현재 줌 레벨을 적용한 캔버스의 논리적 크기 반환"""
        if zoom is None: zoom = self.controller.get_zoom()
        w = int(self.controller.settings['output_width'].get() * self.fit_scale * zoom)
        h = int(self.controller.settings['output_height'].get() * self.fit_scale * zoom)
        return max(1, w), max(1, h) # 최소 1x1

    def finalize_object_move(self, path: str):
        """객체 이동 완료 후 상대 좌표 업데이트"""
        obj_info = None
        if path == 'logo':
             obj_info = self.controller.logo_object
        elif path in self.canvas_objects:
             obj_info = self.canvas_objects[path]

        if not obj_info: return

        canvas_w, canvas_h = self.get_canvas_size() # 줌 100% 기준 크기
        item_id = obj_info['id']
        coords = self.canvas.coords(item_id)

        # 캔버스 경계 및 로고 존 확인/보정
        img_w, img_h = 0, 0
        pil_img = obj_info.get('pil_for_display') # 현재 표시된 이미지
        if pil_img:
             img_w, img_h = pil_img.width, pil_img.height

        logo_zone_h = canvas_h * (self.controller.settings['logo_zone_height'].get() / 1500.0)
        min_x, max_x = img_w / 2, canvas_w - img_w / 2
        min_y = logo_zone_h + img_h / 2 if path != 'logo' else img_h / 2 # 로고는 로고존 내부 허용
        max_y = canvas_h - img_h / 2

        # 새 좌표 계산 (경계 보정)
        # coords는 현재 줌 레벨 기준이므로, 100% 줌 기준으로 변환 필요 없음
        current_zoom = self.controller.get_zoom()
        current_canvas_w, current_canvas_h = self.get_canvas_size(current_zoom)
        current_logo_zone_h = current_canvas_h * (self.controller.settings['logo_zone_height'].get() / 1500.0)

        current_min_y = current_logo_zone_h + img_h / 2 if path != 'logo' else img_h / 2
        current_max_y = current_canvas_h - img_h / 2
        current_min_x = img_w / 2
        current_max_x = current_canvas_w - img_w / 2

        final_x = max(current_min_x, min(coords[0], current_max_x))
        final_y = max(current_min_y, min(coords[1], current_max_y))

        # 캔버스 객체 위치 업데이트
        if coords[0] != final_x or coords[1] != final_y:
            self.canvas.coords(item_id, final_x, final_y)

        # 상대 좌표 업데이트 (100% 줌 기준 캔버스 크기 사용)
        obj_info['rel_x'] = final_x / current_canvas_w if current_canvas_w > 0 else 0.5
        obj_info['rel_y'] = final_y / current_canvas_h if current_canvas_h > 0 else 0.5


    # --- 리사이즈/회전 핸들 관련 ---
    def activate_resize_handles(self, path: str):
        """지정된 path의 객체 주위에 리사이즈/회전 핸들 표시"""
        self.clear_resize_handles() # 기존 핸들 제거
        self.active_selection_path = path

        obj_info = None
        if path == 'logo':
             obj_info = self.controller.logo_object
        elif path in self.canvas_objects:
             obj_info = self.canvas_objects[path]

        if not obj_info or 'id' not in obj_info:
             self.active_selection_path = None
             return

        item_id = obj_info['id']
        pil_img = obj_info.get('pil_for_display')
        if not pil_img:
             self.active_selection_path = None
             return # 표시 이미지가 없으면 핸들 표시 불가

        angle_degrees = obj_info.get('angle', 0.0) # 로고는 angle 0
        angle_rad = math.radians(angle_degrees)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

        cx, cy = self.canvas.coords(item_id) # 이미지 중심 좌표
        w, h = pil_img.width, pil_img.height
        hw, hh = w / 2, h / 2

        # 8개 핸들 위치 계산 (회전 적용)
        handle_positions = {
            'nw': (-hw, -hh), 'n': (0, -hh), 'ne': (hw, -hh),
            'w':  (-hw, 0),                 'e':  (hw, 0),
            'sw': (-hw, hh), 's': (0, hh), 'se': (hw, hh)
        }
        handle_size = 6

        # 테두리 그리기
        corners = [
            handle_positions['nw'], handle_positions['ne'],
            handle_positions['se'], handle_positions['sw']
        ]
        rotated_corners = []
        for rel_x, rel_y in corners:
            rot_x = rel_x * cos_a - rel_y * sin_a
            rot_y = rel_x * sin_a + rel_y * cos_a
            rotated_corners.extend([cx + rot_x, cy + rot_y])

        self.canvas.create_polygon(rotated_corners, fill='', outline='blue', width=1, tags=('border', path))

        # 리사이즈 핸들 그리기 (로고 제외)
        if path != 'logo':
            for name, (rel_x, rel_y) in handle_positions.items():
                rot_x = rel_x * cos_a - rel_y * sin_a
                rot_y = rel_x * sin_a + rel_y * cos_a
                abs_x, abs_y = cx + rot_x, cy + rot_y
                self.canvas.create_rectangle(
                    abs_x - handle_size/2, abs_y - handle_size/2,
                    abs_x + handle_size/2, abs_y + handle_size/2,
                    fill='white', outline='blue', width=1, tags=('handle', name, path)
                )

            # 회전 핸들 그리기 (로고 제외)
            rotate_handle_y_offset = -hh - 20 # 위쪽 중앙 핸들보다 약간 위에
            rot_x = 0 * cos_a - rotate_handle_y_offset * sin_a
            rot_y = 0 * sin_a + rotate_handle_y_offset * cos_a
            abs_x, abs_y = cx + rot_x, cy + rot_y
            self.canvas.create_oval(
                abs_x - handle_size/2, abs_y - handle_size/2,
                abs_x + handle_size/2, abs_y + handle_size/2,
                fill='lightblue', outline='blue', width=1, tags=('rotate_handle', path)
            )

        self.reorder_canvas_layers() # 핸들이 위로 오도록


    def clear_resize_handles(self):
        """모든 리사이즈/회전 핸들 및 테두리 제거"""
        self.canvas.delete("handle")
        self.canvas.delete("rotate_handle")
        self.canvas.delete("border")
        self.active_selection_path = None


    def process_resizing(self, current_x, current_y, resize_data):
        """리사이즈 중 마우스 움직임 처리"""
        if not resize_data: return

        item_id = resize_data['item_id']
        handle_type = resize_data['handle_type']
        start_x, start_y = resize_data['start_x'], resize_data['start_y']
        start_bbox = resize_data['start_bbox'] # 회전 안된 상태의 bbox (고정점 계산용)
        is_cropping = resize_data['is_cropping']

        path = self.active_selection_path
        if not path or path == 'logo': return # 로고는 리사이즈 안 함
        layer = self.controller.get_layer_by_path(path)
        if not layer: return

        # 객체 정보 가져오기
        obj_info = self.canvas_objects.get(path)
        if not obj_info: return

        # 현재 객체 중심 좌표
        cx, cy = self.canvas.coords(item_id)

        # 현재 객체 각도 (고정)
        angle_degrees = obj_info.get('angle', 0.0)
        angle_rad = math.radians(angle_degrees)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        cos_a_inv, sin_a_inv = math.cos(-angle_rad), math.sin(-angle_rad) # 역회전

        # 마우스 이동량 (캔버스 좌표 기준)
        dx = current_x - start_x
        dy = current_y - start_y

        # 시작 bbox 중심점 (회전 안된 상태 기준)
        start_cx = (start_bbox[0] + start_bbox[2]) / 2
        start_cy = (start_bbox[1] + start_bbox[3]) / 2

        # 마우스 시작점과 현재점을 객체의 회전각만큼 역회전 시켜서,
        # 회전 안된 좌표계에서의 마우스 이동량을 계산
        start_x_rel, start_y_rel = start_x - cx, start_y - cy
        current_x_rel, current_y_rel = current_x - cx, current_y - cy

        unrot_start_x = start_x_rel * cos_a_inv - start_y_rel * sin_a_inv
        unrot_start_y = start_x_rel * sin_a_inv + start_y_rel * cos_a_inv
        unrot_current_x = current_x_rel * cos_a_inv - current_y_rel * sin_a_inv
        unrot_current_y = current_x_rel * sin_a_inv + current_y_rel * cos_a_inv

        unrot_dx = unrot_current_x - unrot_start_x
        unrot_dy = unrot_current_y - unrot_start_y

        # 회전 안된 좌표계 기준 시작 bbox 크기
        start_w = start_bbox[2] - start_bbox[0]
        start_h = start_bbox[3] - start_bbox[1]

        # 핸들 타입에 따라 새 크기 계산 (회전 안된 좌표계 기준)
        new_w, new_h = start_w, start_h
        aspect_ratio = start_w / start_h if start_h != 0 else 1.0

        if 'n' in handle_type:
             new_h = start_h - unrot_dy
             if 'w' not in handle_type and 'e' not in handle_type: new_w = new_h * aspect_ratio
        if 's' in handle_type:
             new_h = start_h + unrot_dy
             if 'w' not in handle_type and 'e' not in handle_type: new_w = new_h * aspect_ratio
        if 'w' in handle_type:
             new_w = start_w - unrot_dx
             if 'n' not in handle_type and 's' not in handle_type: new_h = new_w / aspect_ratio
        if 'e' in handle_type:
             new_w = start_w + unrot_dx
             if 'n' not in handle_type and 's' not in handle_type: new_h = new_w / aspect_ratio

        # 크기가 최소값 이하로 줄어드는 것 방지
        min_size = 10
        new_w = max(min_size, new_w)
        new_h = max(min_size, new_h)

        # 스케일 값 계산
        if start_w > 0 and start_h > 0:
            # [ ★★★★★ TODO: ImageLayer 리사이즈 로직 정교화 필요 ★★★★★ ]
            # 현재: scale_var 변경 -> update_object_display 호출 -> 내용물 크기 기준으로 재계산.
            # 개선 방향: 여기서 직접 마우스 이동량(unrot_dx, unrot_dy)과 핸들 타입에 맞춰
            # 내용물 크기 기준의 새 scale_var 값을 더 정확히 계산해야 함.
            # 예를 들어, 'n' 핸들을 위로 당기면 unrot_dy가 음수 -> new_h 증가.
            # 이 증가 비율을 내용물 높이 기준으로 계산하여 scale_var에 적용.
            
            # 임시 로직 (기존과 유사하게 동작하나, content_bbox 기준으로 update됨)
            if isinstance(layer, ImageLayer):
                # 높이 변경 비율을 기준으로 scale_var 업데이트 시도
                scale_change_h = new_h / start_h
                new_scale = layer.scale_var.get() * scale_change_h
                layer.scale_var.set(max(1.0, new_scale))
            elif isinstance(layer, (TextLayer, ShapeLayer)):
                # 텍스트/도형은 scale_var 자체가 크기이므로, 너비/높이 중 큰 변화율 적용
                 scale_change = max(new_w / start_w, new_h / start_h)
                 new_scale = layer.scale_var.get() * scale_change
                 layer.scale_var.set(max(1.0, new_scale)) # 최소값 1.0


        # 리사이즈 데이터 업데이트 (필요시)
        resize_data.update(start_x=current_x, start_y=current_y) # 다음 motion 이벤트 위해 시작점 갱신


    def process_rotation(self, current_x, current_y, rotation_data):
        """회전 중 마우스 움직임 처리"""
        if not rotation_data: return
        item_id = rotation_data['item_id']
        cx, cy = rotation_data['center_x'], rotation_data['center_y']
        start_angle = rotation_data['start_angle']
        initial_item_angle = rotation_data['initial_item_angle']

        current_angle = math.degrees(math.atan2(current_y - cy, current_x - cx))
        delta_angle = current_angle - start_angle
        new_angle = (initial_item_angle + delta_angle) % 360

        path = self.active_selection_path
        if path and path != 'logo': # 로고는 회전 불가
            layer = self.controller.get_layer_by_path(path)
            if layer:
                layer.angle = new_angle
                # 캔버스 객체 정보에도 각도 업데이트
                if path in self.canvas_objects:
                     self.canvas_objects[path]['angle'] = new_angle
                # 표시 업데이트 (회전된 이미지 재생성)
                self.update_object_display(layer, self.controller.get_zoom())


    def finalize_resize_or_rotate(self, path: str):
        """리사이즈 또는 회전 완료 후 처리"""
        if not path or path == 'logo': return # 로고는 처리 안 함
        layer = self.controller.get_layer_by_path(path)
        if layer:
            # 최종 상태로 캔버스 업데이트 (필요 시 정교한 계산 추가)
            self.update_object_display(layer, self.controller.get_zoom())
            self.controller.update_status(f"'{layer.get_display_name()}' 변형 완료.")
        # 핸들 재표시 (위치/크기 업데이트 위해)
        self.activate_resize_handles(path)


    def get_object_info_by_id(self, item_id: int) -> dict | None:
        """캔버스 item ID로 객체 정보 딕셔너리 찾기"""
        if self.controller.logo_object and self.controller.logo_object.get('id') == item_id:
            return self.controller.logo_object
        for info in self.canvas_objects.values():
            if info.get('id') == item_id:
                return info
        return None