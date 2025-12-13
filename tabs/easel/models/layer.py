import tkinter as tk
import os
import random
import math
from PIL import Image, ImageTk, ImageDraw, ImageFont

from ui.theme import Colors

try:
    from tabs.easel.services.font_service import FontService
except ImportError:
    class FontService:
        @staticmethod
        def get_font_path(font_family):
            return "arial.ttf"

THUMBNAIL_SIZE = (48, 48)
DISPLAY_IMG_MAX_SIZE = (800, 800)
SAVE_IMG_MAX_SIZE = (2000, 2000)

class Layer:
    def __init__(self, layer_type: str):
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
    def __init__(self, file_path: str):
        super().__init__('image')
        self.path = file_path
        self.scale_var = tk.DoubleVar(value=30.0)
        self.content_bbox = None
        self.crop_box = None

        try:
            self.pil_img_original = Image.open(file_path).convert("RGBA")

            self.pil_img_save = self.pil_img_original.copy()
            self.pil_img_save.thumbnail(SAVE_IMG_MAX_SIZE, Image.Resampling.LANCZOS)

            self.pil_img_display = self.pil_img_save.copy()
            self.pil_img_display.thumbnail(DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)

            self._update_content_bbox()

            if self.content_bbox and self.content_bbox != (0, 0, self.pil_img_display.width, self.pil_img_display.height):
                save_w, save_h = self.pil_img_save.size
                display_w, display_h = self.pil_img_display.size
                
                try:
                    ratio_w = save_w / display_w if display_w > 0 else 1.0
                    ratio_h = save_h / display_h if display_h > 0 else 1.0
                    save_bbox = (
                        int(self.content_bbox[0] * ratio_w),
                        int(self.content_bbox[1] * ratio_h),
                        int(self.content_bbox[2] * ratio_w),
                        int(self.content_bbox[3] * ratio_h)
                    )
                    save_bbox = (
                        max(0, save_bbox[0]),
                        max(0, save_bbox[1]),
                        min(save_w, save_bbox[2]),
                        min(save_h, save_bbox[3])
                    )
                    
                    self.pil_img_save = self.pil_img_save.crop(save_bbox)

                except Exception:
                     pass

                self.pil_img_display = self.pil_img_display.crop(self.content_bbox)
                self._update_content_bbox()

            self.thumbnail = self.create_thumbnail()
            self._thumbnail_ref = self.thumbnail

        except Exception as e:
            raise RuntimeError(f"Failed to initialize ImageLayer: {e}")

    def _update_content_bbox(self):
        try:
            self.content_bbox = self.pil_img_display.getbbox()
            if not self.content_bbox:
                self.content_bbox = (0, 0, self.pil_img_display.width, self.pil_img_display.height)
        except Exception:
            self.content_bbox = (0, 0, self.pil_img_display.width, self.pil_img_display.height)

    def get_content_dimensions(self) -> tuple[int, int]:
        if self.content_bbox:
            width = self.content_bbox[2] - self.content_bbox[0]
            height = self.content_bbox[3] - self.content_bbox[1]
            return max(1, width), max(1, height)
        else:
            return max(1, self.pil_img_display.width), max(1, self.pil_img_display.height)

    def get_display_name(self) -> str:
        return os.path.basename(self.path)

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        try:
            thumb_img = self.pil_img_display.copy()
            thumb_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            final_thumb = Image.new('RGBA', THUMBNAIL_SIZE, (0,0,0,0))
            paste_x = (THUMBNAIL_SIZE[0] - thumb_img.width) // 2
            paste_y = (THUMBNAIL_SIZE[1] - thumb_img.height) // 2
            final_thumb.paste(thumb_img, (paste_x, paste_y))

            return ImageTk.PhotoImage(final_thumb)
        except Exception:
            empty = Image.new('RGBA', THUMBNAIL_SIZE, Colors.GREY)
            return ImageTk.PhotoImage(empty)

    def get_pil_image_to_process(self):
        return self.pil_img_display.crop(self.crop_box) if self.crop_box else self.pil_img_display

class TextLayer(Layer):
    def __init__(self, text, font_family, font_size, color):
        super().__init__('text')
        self.text = text
        self.font_family = font_family
        self.scale_var = tk.DoubleVar(value=font_size)
        self.color = color
        self.thumbnail = self.create_thumbnail()
        self._thumbnail_ref = self.thumbnail

    def get_display_name(self) -> str:
        return self.text

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        thumb = Image.new('RGBA', THUMBNAIL_SIZE, (255, 255, 255, 0))
        draw = ImageDraw.Draw(thumb)
        try:
            font_path = FontService.get_font_path('malgun.ttf')
            font = ImageFont.truetype(font_path, 32)
            draw.text((8, 4), "T", font=font, fill=Colors.DARK_TEAL)
        except Exception:
            draw.text((8, 4), "T", fill=Colors.DARK_TEAL)
        return ImageTk.PhotoImage(thumb)

class ShapeLayer(Layer):
    def __init__(self, shape_type, color, pil_image=None):
        super().__init__('shape')
        self.shape_type = shape_type
        self.color = color
        self.scale_var = tk.DoubleVar(value=100.0)
        self.pil_image = pil_image
        self.thumbnail = self.create_thumbnail()
        self._thumbnail_ref = self.thumbnail

    def get_display_name(self) -> str:
        return self.shape_type

    def create_thumbnail(self) -> ImageTk.PhotoImage:
        thumb = Image.new('RGBA', THUMBNAIL_SIZE, (255, 255, 255, 0))
        draw = ImageDraw.Draw(thumb)

        if self.shape_type == '자유곡선' and self.pil_image:
            try:
                img = self.pil_image.copy()
                img.thumbnail((40, 40), Image.Resampling.LANCZOS)
                thumb.paste(img, (4, 4), img)
            except Exception:
                draw.line([(5,5), (43,43)], fill=Colors.GREY, width=2)
                draw.line([(5,43), (43,5)], fill=Colors.GREY, width=2)
        else:
            size = 36
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