# 파일 경로: tabs/easel/models/layer.py

import tkinter as tk
import os
import random
import math
from PIL import Image, ImageTk, ImageDraw, ImageFont
# --- import 경로 수정 ---
from ..services.font_service import FontService
# --- 수정 끝 ---

# --- 상수 정의 ---
THUMBNAIL_SIZE = (48, 48)
DISPLAY_IMG_MAX_SIZE = (800, 800)
SAVE_IMG_MAX_SIZE = (2000, 2000)

class Layer:
    """모든 레이어 타입의 기본이 되는 추상 기본 클래스"""
    def __init__(self, layer_type: str):
        # 고유 ID 생성 방식 변경 (더 짧게)
        self.path = f"{layer_type}_{random.randint(1000, 9999)}_{hex(int(tk._default_root.tk.call('clock', 'milliseconds')))[-4:]}"
        self.type = layer_type
        self.is_visible = tk.BooleanVar(value=False)
        self.angle = 0.0
        self.selected = False
        self.widget_ref = None

    def get_display_name(self) -> str:
        raise NotImplementedError

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        raise NotImplementedError

class ImageLayer(Layer):
    """이미지 레이어를 위한 데이터 클래스"""
    def __init__(self, file_path: str):
        super().__init__('image')
        self.path = file_path # 이미지 레이어는 파일 경로를 고유 ID로 사용
        self.scale_var = tk.DoubleVar(value=30.0)
        self.content_bbox = None # 내용물 경계 상자

        try:
            self.pil_img_original = Image.open(file_path).convert("RGBA")

            # 1. 초기 Save/Display 이미지 생성 (썸네일 적용)
            self.pil_img_save = self.pil_img_original.copy()
            self.pil_img_save.thumbnail(SAVE_IMG_MAX_SIZE, Image.Resampling.LANCZOS)

            self.pil_img_display = self.pil_img_save.copy()
            self.pil_img_display.thumbnail(DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)

            # 2. 초기 내용물 경계 상자 계산
            self._update_content_bbox() # based on pil_img_display

            # [ ★★★★★ NEW: 초기 이미지 자르기(Crop) 로직 ★★★★★ ]
            if self.content_bbox and self.content_bbox != (0, 0, self.pil_img_display.width, self.pil_img_display.height):
                print(f"DEBUG [{os.path.basename(self.path)}]: Cropping initial image to bbox: {self.content_bbox}")
                # Save 이미지도 동일한 비율로 잘라내기 위해 원본 bbox 계산
                save_w, save_h = self.pil_img_save.size
                display_w, display_h = self.pil_img_display.size
                
                # pil_img_save 크기에 맞는 bbox 계산 (비율 사용)
                # content_bbox는 display 이미지 기준 좌표임
                try:
                    ratio_w = save_w / display_w if display_w > 0 else 1.0
                    ratio_h = save_h / display_h if display_h > 0 else 1.0
                    save_bbox = (
                        int(self.content_bbox[0] * ratio_w),
                        int(self.content_bbox[1] * ratio_h),
                        int(self.content_bbox[2] * ratio_w),
                        int(self.content_bbox[3] * ratio_h)
                    )
                    # 계산된 save_bbox가 이미지 경계를 벗어나지 않도록 조정
                    save_bbox = (
                        max(0, save_bbox[0]),
                        max(0, save_bbox[1]),
                        min(save_w, save_bbox[2]),
                        min(save_h, save_bbox[3])
                    )
                    
                    # pil_img_save 자르기
                    self.pil_img_save = self.pil_img_save.crop(save_bbox)
                    print(f"DEBUG [{os.path.basename(self.path)}]: Cropped pil_img_save size: {self.pil_img_save.size}")

                except Exception as e:
                     print(f"ERROR calculating save_bbox or cropping pil_img_save for {self.path}: {e}")
                     # 오류 발생 시 pil_img_save는 자르지 않고 진행 (display만 자름)

                # pil_img_display 자르기
                self.pil_img_display = self.pil_img_display.crop(self.content_bbox)
                print(f"DEBUG [{os.path.basename(self.path)}]: Cropped pil_img_display size: {self.pil_img_display.size}")

                # 3. 잘라낸 이미지를 기준으로 content_bbox 다시 계산 (이제 0,0 시작)
                self._update_content_bbox() # Reset bbox relative to the new cropped image
            # [ ★★★★★ Crop 로직 끝 ★★★★★ ]

            self.crop_box = None # crop_box는 사용자가 UI에서 설정하는 것
            
            # 4. 최종 썸네일 생성 (잘라낸 이미지 기준)
            self.thumbnail = self.create_thumbnail()
            self._thumbnail_ref = self.thumbnail # GC 방지

        except Exception as e:
            print(f"Error loading image {file_path}: {e}")
            raise

    def _update_content_bbox(self):
        """pil_img_display 기준으로 내용물 경계 상자(content_bbox) 업데이트"""
        try:
            self.content_bbox = self.pil_img_display.getbbox()
            if self.content_bbox:
                # bbox가 있으면 (0,0) 시작하도록 조정할 필요 없음. getbbox 자체가 내용물 경계 반환
                print(f"DEBUG [{os.path.basename(self.path)}]: Updated content_bbox: {self.content_bbox}")
            else:
                self.content_bbox = (0, 0, self.pil_img_display.width, self.pil_img_display.height)
                print(f"DEBUG [{os.path.basename(self.path)}]: Image fully transparent, using full bbox: {self.content_bbox}")
        except Exception as e:
            print(f"ERROR calculating content_bbox for {self.path}: {e}")
            self.content_bbox = (0, 0, self.pil_img_display.width, self.pil_img_display.height)

    def get_content_dimensions(self) -> tuple[int, int]:
        """content_bbox 기준 내용물의 너비와 높이 반환"""
        if self.content_bbox:
            width = self.content_bbox[2] - self.content_bbox[0]
            height = self.content_bbox[3] - self.content_bbox[1]
            # 이미지가 crop되어 content_bbox가 (0,0,w,h) 형태일 것이므로, 이 계산이 맞음.
            # 만약 crop 안 하고 원본 bbox 좌표를 쓴다면 다르게 계산해야 함.
            return max(1, width), max(1, height)
        else:
            # bbox 없으면 display 이미지 크기 반환 (이미 crop된 상태일 수 있음)
            return max(1, self.pil_img_display.width), max(1, self.pil_img_display.height)

    def get_display_name(self) -> str:
        return os.path.basename(self.path)

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        # 이제 pil_img_display 자체가 crop된 상태일 수 있음
        thumb_img = self.pil_img_display.copy()
        
        # 썸네일 크기 조절
        thumb_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # 투명 배경 유지를 위해 빈 썸네일 중앙에 붙여넣기
        final_thumb = Image.new('RGBA', THUMBNAIL_SIZE, (0,0,0,0)) # 투명 배경 썸네일
        paste_x = (THUMBNAIL_SIZE[0] - thumb_img.width) // 2
        paste_y = (THUMBNAIL_SIZE[1] - thumb_img.height) // 2
        final_thumb.paste(thumb_img, (paste_x, paste_y))

        return ImageTk.PhotoImage(final_thumb)

    def get_pil_image_to_process(self):
        """크롭 박스를 적용한 표시용 이미지를 반환"""
        # 이제 self.pil_img_display는 이미 초기 여백이 crop된 상태일 수 있음
        return self.pil_img_display.crop(self.crop_box) if self.crop_box else self.pil_img_display

# --- TextLayer, ShapeLayer 클래스는 변경 없음 ---
class TextLayer(Layer):
    """텍스트 레이어를 위한 데이터 클래스"""
    def __init__(self, text, font_family, font_size, color):
        super().__init__('text')
        self.text = text
        self.font_family = font_family
        self.scale_var = tk.DoubleVar(value=font_size) # 텍스트에서는 크기가 scale_var
        self.color = color
        self.thumbnail = self.create_thumbnail()
        self._thumbnail_ref = self.thumbnail # GC 방지

    def get_display_name(self) -> str:
        return self.text

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        thumb = Image.new('RGBA', THUMBNAIL_SIZE, (255, 255, 255, 220))
        draw = ImageDraw.Draw(thumb)
        try:
            # FontService 사용
            font = ImageFont.truetype(FontService.get_font_path('malgun.ttf'), 32)
            draw.text((8, 4), "T", font=font, fill="#555555")
        except IOError:
            draw.text((8, 4), "T", fill="#555555") # 폴백
        return ImageTk.PhotoImage(thumb)

class ShapeLayer(Layer):
    """도형 레이어를 위한 데이터 클래스"""
    def __init__(self, shape_type, color, pil_image=None):
        super().__init__('shape')
        self.shape_type = shape_type
        self.color = color
        self.scale_var = tk.DoubleVar(value=100.0)
        self.pil_image = pil_image # 자유곡선인 경우에만 사용
        self.thumbnail = self.create_thumbnail()
        self._thumbnail_ref = self.thumbnail # GC 방지

    def get_display_name(self) -> str:
        return self.shape_type

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        thumb = Image.new('RGBA', THUMBNAIL_SIZE, (255, 255, 255, 220))
        draw = ImageDraw.Draw(thumb)

        if self.shape_type == '자유곡선' and self.pil_image:
            try:
                img = self.pil_image.copy()
                img.thumbnail((40, 40), Image.Resampling.LANCZOS)
                thumb.paste(img, (4, 4), img)
            except Exception as e:
                print(f"자유곡선 썸네일 생성 오류: {e}")
                draw.line([(5,5), (43,43)], fill="#555555", width=2)
                draw.line([(5,43), (43,5)], fill="#555555", width=2)
        else:
            size, padding = 36, (THUMBNAIL_SIZE[0] - 36) // 2
            center_x = THUMBNAIL_SIZE[0] / 2
            center_y = THUMBNAIL_SIZE[1] / 2
            points = self._get_shape_points((center_x, center_y), size)
            if points:
                draw.polygon(points, fill=self.color, outline=self.color)

        return ImageTk.PhotoImage(thumb)

    def _get_shape_points(self, center, size):
        x, y = center; r = size / 2
        n_map = {'삼각형': 3, '오각형': 5, '육각형': 6}
        offset_map = {'삼각형': -90, '오각형': -90, '육각형': -30}

        if self.shape_type == "사각형":
            return [x-r, y-r, x+r, y-r, x+r, y+r, x-r, y+r]

        n = n_map.get(self.shape_type)
        offset = math.radians(offset_map.get(self.shape_type, 0))

        if n:
            return [p for i in range(n) for p in (x + r * math.cos(2*math.pi*i/n + offset), y + r * math.sin(2*math.pi*i/n + offset))]
        return []