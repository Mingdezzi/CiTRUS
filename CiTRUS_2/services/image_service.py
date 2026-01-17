# 파일 경로: services/image_service.py (이 코드로 완전히 교체하세요)

from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont
import math
from models.layer import Layer, ImageLayer, TextLayer, ShapeLayer, SAVE_IMG_MAX_SIZE, DISPLAY_IMG_MAX_SIZE
from services.font_service import FontService

# --- 라이브러리 가용성 확인 ---
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False


class ImageService:
    """최종 이미지 생성, 저장 및 배경 제거 등 이미지 관련 서비스를 제공"""

    @staticmethod
    def save_canvas_as_image(settings, layers, canvas_objects):
        # 캔버스에 보이는 레이어가 하나도 없고 로고도 없으면 저장할 게 없음
        if not any(l.is_visible.get() for l in layers) and 'logo_info' not in settings:
            messagebox.showwarning("알림", "캔버스에 저장할 항목이 없습니다.")
            return

        save_w = settings['output_width']
        save_h = settings['output_height']
        bg_color_hex = settings['background_color']

        try:
            bg_color = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        except:
            bg_color = (255, 255, 255, 255)

        final_image = Image.new("RGBA", (save_w, save_h), bg_color)

        # 캔버스에 표시된 순서대로 레이어 정렬 (로고 제외)
        visible_layers = [l for l in layers if l.is_visible.get()]

        # --- 여기가 핵심 수정 부분 (로고 렌더링 추가) ---
        
        # 1. 로고 정보 가져오기
        logo_info = settings.get('logo_info')
        
        # 2. 로고 먼저 렌더링 (보통 로고가 맨 위에 있음)
        if logo_info and 'pil_img_original' in logo_info:
            try:
                logo_pil_original = logo_info['pil_img_original']
                logo_scale = settings['logo_size']
                
                # 로고 렌더링 크기 계산
                logo_target_h = save_h * (settings['logo_zone_height'] / 1500.0) * (logo_scale / 100.0)
                if logo_pil_original.height > 0:
                    logo_ratio = logo_target_h / logo_pil_original.height
                    logo_final_w, logo_final_h = int(logo_pil_original.width * logo_ratio), int(logo_target_h)
                    
                    if logo_final_w > 0 and logo_final_h > 0:
                        logo_to_paste = logo_pil_original.resize((logo_final_w, logo_final_h), Image.Resampling.LANCZOS)
                        
                        # 로고 위치 계산
                        logo_center_x, logo_center_y = logo_info['rel_x'] * save_w, logo_info['rel_y'] * save_h
                        logo_paste_pos = (int(logo_center_x - logo_final_w / 2), int(logo_center_y - logo_final_h / 2))
                        
                        # 최종 이미지에 로고 붙여넣기
                        final_image.paste(logo_to_paste, logo_paste_pos, logo_to_paste)
            except Exception as e:
                 print(f"로고 렌더링 중 오류 발생: {e}")

        # --- 수정 끝 ---

        # 3. 나머지 레이어 렌더링 (기존 코드)
        for layer in visible_layers:
            obj_info = canvas_objects.get(layer.path)
            if not obj_info: continue

            center_x, center_y = obj_info['rel_x'] * save_w, obj_info['rel_y'] * save_h
            layer_img = ImageService._render_layer_to_pil(layer, save_w, save_h, settings)

            if layer_img:
                w, h = layer_img.size
                paste_pos = (int(center_x - w / 2), int(center_y - h / 2))
                # final_image.paste(layer_img, paste_pos, layer_img)
                # Paste 대신 alpha_composite 사용 (투명도 처리 개선)
                temp_layer_image = Image.new("RGBA", final_image.size, (0, 0, 0, 0))
                temp_layer_image.paste(layer_img, paste_pos, layer_img)
                final_image = Image.alpha_composite(final_image, temp_layer_image)


        # 파일 저장
        output_format = settings['output_format']
        fname = (settings['style_code'] or "thumbnail") + ('.png' if output_format == "PNG" else ".jpg")
        save_path = filedialog.asksaveasfilename(
            initialdir=settings['save_directory'],
            initialfile=fname,
            defaultextension=fname.split('.')[-1]
        )
        if not save_path:
            return "저장 취소."

        try:
            if output_format == "JPG":
                final_image.convert("RGB").save(save_path, "JPEG", quality=95)
            else:
                final_image.save(save_path, "PNG")
            messagebox.showinfo("성공", f"이미지를 저장했습니다.\n{save_path}")
            return "저장 완료!"
        except Exception as e:
            messagebox.showerror("저장 오류", f"파일 저장 중 오류 발생:\n{e}")
            return "저장 실패."

    @staticmethod
    def _render_layer_to_pil(layer: Layer, canvas_w, canvas_h, settings) -> Image.Image | None:
        """개별 레이어를 최종 저장용 PIL 이미지로 렌더링"""
        scale = layer.scale_var.get()

        if isinstance(layer, TextLayer):
            font = ImageFont.truetype(FontService.get_font_path(layer.font_family), int(scale))
            bbox = font.getbbox(layer.text)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if text_w <= 0 or text_h <= 0: return None

            txt_img = Image.new('RGBA', (text_w, text_h), (255, 255, 255, 0))
            d = ImageDraw.Draw(txt_img)
            d.text((-bbox[0], -bbox[1]), layer.text, font=font, fill=layer.color)

            if layer.angle != 0:
                return txt_img.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
            return txt_img

        elif isinstance(layer, ShapeLayer):
            # 도형은 바로 그리지 않고, 큰 임시 이미지에 그린 후 알파 컴포지트
            # shape_img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
            # shape_draw = ImageDraw.Draw(shape_img)

            if layer.shape_type != '자유곡선':
                # get_shape_points는 중심 기준 좌표 반환, 렌더링 시에는 bounding box 필요
                points = layer._get_shape_points((0, 0), scale)
                if not points: return None

                if layer.angle != 0:
                    points = ImageService._rotate_points(points, (0, 0), -layer.angle)

                xs, ys = points[0::2], points[1::2]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                width, height = int(max_x - min_x), int(max_y - min_y)
                if width <=0 or height <=0: return None

                shape_img = Image.new('RGBA', (width, height), (0,0,0,0))
                shape_draw = ImageDraw.Draw(shape_img)
                # 바운딩 박스 기준으로 좌표 재계산
                shifted_points = [(x - min_x, y - min_y) for x, y in zip(xs, ys)]
                shape_draw.polygon(shifted_points, fill=layer.color)
                return shape_img

            else: # 자유곡선
                if not layer.pil_image: return None
                img = layer.pil_image
                final_w, final_h = int(img.width * (scale/100.0)), int(img.height * (scale/100.0))
                if final_w < 1 or final_h < 1: return None

                img_to_paste = img.resize((final_w, final_h), Image.Resampling.LANCZOS)
                if layer.angle != 0:
                    img_to_paste = img_to_paste.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
                return img_to_paste
            # return shape_img # 도형은 바로 렌더링된 이미지 반환

        elif isinstance(layer, ImageLayer):
            pil_to_process = layer.pil_img_save.crop(layer.crop_box) if layer.crop_box else layer.pil_img_save

            logo_zone_h = canvas_h * (settings['logo_zone_height'] / 1500.0)
            target_h = (canvas_h - logo_zone_h) * (scale / 100.0)

            if pil_to_process.height > 0:
                ratio = target_h / pil_to_process.height
                final_w, final_h = int(pil_to_process.width * ratio), int(target_h)
                if final_w > 0 and final_h > 0:
                    img_to_paste = pil_to_process.resize((final_w, final_h), Image.Resampling.LANCZOS)
                    if layer.angle != 0:
                        img_to_paste = img_to_paste.rotate(layer.angle, expand=True, resample=Image.Resampling.BICUBIC)
                    return img_to_paste
        return None

    @staticmethod
    def remove_background(layer: ImageLayer) -> bool:
        """rembg를 사용하여 이미지 레이어의 배경을 제거"""
        if not REMBG_AVAILABLE or not isinstance(layer, ImageLayer):
            return False
        try:
            # 원본 대신 저장용 이미지(축소됨)를 사용해야 메모리/시간 효율적
            removed_pil = remove(layer.pil_img_save)
            tight_bbox = removed_pil.getbbox()

            final_pil = removed_pil.crop(tight_bbox) if tight_bbox else removed_pil

            # 원본 이미지는 그대로 두고, 저장용/표시용만 업데이트
            layer.pil_img_save = final_pil.copy()
            layer.pil_img_save.thumbnail(SAVE_IMG_MAX_SIZE, Image.Resampling.LANCZOS)
            layer.pil_img_display = layer.pil_img_save.copy()
            layer.pil_img_display.thumbnail(DISPLAY_IMG_MAX_SIZE, Image.Resampling.LANCZOS)

            layer.crop_box = None
            layer.angle = 0.0
            layer.thumbnail = layer.create_thumbnail() # 썸네일 재생성
            return True
        except Exception as e:
            messagebox.showerror("배경 제거 오류", f"배경 제거 중 오류가 발생했습니다: {e}")
            return False

    @staticmethod
    def _rotate_points(points, center, angle_degrees):
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