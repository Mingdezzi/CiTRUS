# 파일 경로: models/layer.py

import tkinter as tk
import os
import random
import math
from PIL import Image, ImageTk, ImageDraw, ImageFont
from services.font_service import FontService

# --- 상수 정의 ---
THUMBNAIL_SIZE = (48, 48)
DISPLAY_IMG_MAX_SIZE = (800, 800)
SAVE_IMG_MAX_SIZE = (2000, 2000)

class Layer:
    """모든 레이어 타입의 기본이 되는 추상 기본 클래스"""
    def __init__(self, layer_type: str):
        self.path = f"{layer_type}_{random.randint(1000, 9999)}_{int(tk._default_root.tk.call('clock', 'milliseconds'))}"
        self.type = layer_type
        self.is_visible = tk.BooleanVar(value=False)
        self.angle = 0.0
        self.selected = False
        
        # UI 위젯 참조 (나중에 LayerList에서 할당)
        self.widget_ref = None

    def get_display_name(self) -> str:
        raise NotImplementedError

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        raise NotImplementedError

    def get_pil_for_display(self, scale_percent: float, zoom: float) -> Image.Image | None:
        raise NotImplementedError
    
    def get_pil_for_save(self, scale_percent: float) -> Image.Image | None:
        raise NotImplementedError

class ImageLayer(Layer):
    """이미지 레이어를 위한 데이터 클래스"""
    def __init__(self, file_path: str):
        super().__init__('image')
        self.path = file_path # 이미지 레이어는 파일 경로를 고유 ID로 사용
        self.scale_var = tk.DoubleVar(value=30.0)
        
        try:
            self.pil_img_original = Image.open(file_path).convert("RGBA")
            
            # 저장용, 표시용 이미지 생성
            self.pil_img_save = self.pil_img_original.copy()
            self.pil_img_save.thumbnail(SAVE_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
            
            self.pil_img_display = self.pil_img_save.copy()
            self.pil_img_display.thumbnail(DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
            
            self.crop_box = None
            self.thumbnail = self.create_thumbnail()

        except Exception as e:
            print(f"Error loading image {file_path}: {e}")
            raise

    def get_display_name(self) -> str:
        return os.path.basename(self.path)

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        thumb_img = self.pil_img_display.copy()
        thumb_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(thumb_img)
    
    def get_pil_image_to_process(self):
        """크롭 박스를 적용한 원본 이미지를 반환"""
        return self.pil_img_display.crop(self.crop_box) if self.crop_box else self.pil_img_display
    
class TextLayer(Layer):
    """텍스트 레이어를 위한 데이터 클래스"""
    def __init__(self, text, font_family, font_size, color):
        super().__init__('text')
        self.text = text
        self.font_family = font_family
        self.scale_var = tk.DoubleVar(value=font_size) # 텍스트에서는 크기가 scale_var
        self.color = color
        self.thumbnail = self.create_thumbnail()

    def get_display_name(self) -> str:
        return self.text

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        thumb = Image.new('RGBA', THUMBNAIL_SIZE, (255, 255, 255, 220))
        draw = ImageDraw.Draw(thumb)
        try:
            font = ImageFont.truetype(FontService.get_font_path('malgun.ttf'), 32)
            draw.text((8, 4), "T", font=font, fill="#555555")
        except IOError:
            draw.text((8, 4), "T", fill="#555555")
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

    def get_display_name(self) -> str:
        return self.shape_type

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        thumb = Image.new('RGBA', THUMBNAIL_SIZE, (255, 255, 255, 220))
        draw = ImageDraw.Draw(thumb)
        
        if self.shape_type == '자유곡선' and self.pil_image:
            img = self.pil_image.copy()
            img.thumbnail((40, 40), Image.Resampling.LANCZOS)
            thumb.paste(img, (4, 4), img)
        else:
            size, padding = 36, (THUMBNAIL_SIZE[0] - 36) // 2
            points = self._get_shape_points((padding, padding), size)
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